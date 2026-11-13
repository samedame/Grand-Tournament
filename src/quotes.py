"""Real-quote shadow log via the Tradier market-data API. READ-ONLY: only quote endpoints are called, no order endpoints.

Entry (alert run, ~15:50 ET): for each ticker with the signal ON, log the real bid/ask/IV of the call nearest 0.30 delta and
nearest 0.80 delta in the first Friday expiry >= 14 calendar days out. On roughly 1 in 10 no-signal days (deterministic by date) log a
0.30-delta baseline for SPY so model-vs-real pricing can be compared without waiting for signals.
Exit (confirm run, ~16:25 ET): re-quote every contract that has an entry row and no exit row, dated before today.

Env: TRADIER_TOKEN (required, else this module does nothing), FORCE_BASELINE=1 (log a baseline today, for testing), TRADIER_ENV = production (default) | sandbox.
Sandbox data is delayed ~15 min: fine for plumbing tests, NOT a valid fill-quality measurement.
Ledger: ledger/quotes.csv
"""
import csv, hashlib, json, os, time, urllib.parse, urllib.request
from datetime import date, datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(ROOT, "ledger", "quotes.csv")
COLS = ["date", "ticker", "kind", "target_delta", "event", "contract", "expiry", "strike", "delta", "iv", "bid", "ask", "mid",
        "underlying", "entry_date", "env"]
TARGETS = (0.30, 0.80)
MIN_DTE = 14
BASELINE_EVERY = 8          # ~1 in 8 no-signal days
BASELINE_TICKER = "SPY"


def enabled():
    return bool(os.environ.get("TRADIER_TOKEN"))


def env_name():
    return os.environ.get("TRADIER_ENV", "production").lower()


def http_get(path, params):
    base = "https://sandbox.tradier.com/v1" if env_name() == "sandbox" else "https://api.tradier.com/v1"
    url = f"{base}{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {os.environ['TRADIER_TOKEN']}", "Accept": "application/json"})
    err = None
    for k in range(3):
        try:
            return json.loads(urllib.request.urlopen(req, timeout=30).read())
        except Exception as e:
            err = e; time.sleep(2 + 2 * k)
    raise err


def _as_list(x):
    return [] if x is None else x if isinstance(x, list) else [x]


def pick_expiry(today, expirations):
    """First Friday expiry at least MIN_DTE calendar days out (same rule as src/options.py)."""
    for s in sorted(expirations):
        d = date.fromisoformat(s)
        if d.weekday() == 4 and (d - today).days >= MIN_DTE:
            return s
    return None


def pick_call(chain, target):
    best = None
    for o in chain:
        if o.get("option_type") != "call" or not o.get("bid") and not o.get("ask"):
            continue
        g = o.get("greeks") or {}
        if g.get("delta") is None:
            continue
        gap = abs(float(g["delta"]) - target)
        if best is None or gap < best[0]:
            best = (gap, o)
    return best[1] if best else None


def _row(d, ticker, kind, target, event, o, underlying, entry_date):
    g = o.get("greeks") or {}
    bid, ask = o.get("bid"), o.get("ask")
    mid = round((float(bid) + float(ask)) / 2, 4) if bid is not None and ask is not None else ""
    return dict(date=d.isoformat(), ticker=ticker, kind=kind, target_delta=target, event=event, contract=o["symbol"],
                expiry=o.get("expiration_date", ""), strike=o.get("strike", ""), delta=g.get("delta", ""),
                iv=g.get("mid_iv", g.get("smv_vol", "")), bid=bid, ask=ask, mid=mid, underlying=underlying,
                entry_date=entry_date, env=env_name())


def underlying_price(ticker):
    q = _as_list(http_get("/markets/quotes", {"symbols": ticker}).get("quotes", {}).get("quote"))
    return q[0].get("last") if q else ""


def log_entries(today, ticker, kind):
    exps = _as_list(http_get("/markets/options/expirations", {"symbol": ticker}).get("expirations", {}).get("date"))
    exp = pick_expiry(today, exps)
    if not exp:
        return []
    chain = _as_list(http_get("/markets/options/chains", {"symbol": ticker, "expiration": exp, "greeks": "true"}).get("options", {}).get("option"))
    und = underlying_price(ticker)
    out = []
    for tgt in (TARGETS if kind == "signal" else (0.30,)):
        o = pick_call(chain, tgt)
        if o:
            out.append(_row(today, ticker, kind, tgt, "entry", o, und, today.isoformat()))
    return out


def read_ledger():
    if not os.path.exists(LEDGER):
        return []
    with open(LEDGER, newline="") as f:
        return list(csv.DictReader(f))


def pending(rows, today):
    done = {(r["contract"], r["entry_date"]) for r in rows if r["event"] == "exit"}
    return [r for r in rows if r["event"] == "entry" and r["entry_date"] < today.isoformat() and (r["contract"], r["entry_date"]) not in done]


def log_exits(today, rows):
    out = []
    for e in pending(rows, today):
        q = _as_list(http_get("/markets/quotes", {"symbols": e["contract"], "greeks": "true"}).get("quotes", {}).get("quote"))
        if not q:
            continue
        und = underlying_price(e["ticker"])
        out.append(_row(today, e["ticker"], e["kind"], e["target_delta"], "exit", q[0], und, e["entry_date"]))
    return out


def is_baseline_day(today):
    return int(hashlib.sha256(today.isoformat().encode()).hexdigest(), 16) % BASELINE_EVERY == 0


def append(new_rows):
    if not new_rows:
        return
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    new = not os.path.exists(LEDGER)
    with open(LEDGER, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        if new:
            w.writeheader()
        w.writerows(new_rows)


def run(mode, today, signal_tickers, no_signal_any):
    """Never raises: the quote log must not break the signal alert. Returns a one-line status string."""
    if not enabled():
        return "quotes: TRADIER_TOKEN not set, skipped"
    try:
        rows = []
        if mode == "alert":
            for t in signal_tickers:
                rows += log_entries(today, t, "signal")
            if os.environ.get("FORCE_BASELINE") == "1" or (not signal_tickers and no_signal_any and is_baseline_day(today)):
                rows += log_entries(today, BASELINE_TICKER, "baseline")
        else:
            rows += log_exits(today, read_ledger())
        append(rows)
        return f"quotes: logged {len(rows)} row(s) ({env_name()})"
    except Exception as e:
        return f"quotes: FAILED {type(e).__name__}: {e}"
