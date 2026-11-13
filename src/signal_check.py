"""Daily signal check for the Grand Tournament winner: RSI(14) < 35 AND DeMarker(14) < 0.30 on SPY / QQQ.
Alert-only (never places orders). Uses the same indicator code as the backtest (src/ind.py: rsi, sma).

  python src/signal_check.py alert     # ~15:50 ET: today's partial bar stands in for the close (approximate)
  python src/signal_check.py confirm   # ~16:25 ET: final close; appends a row to ledger/signals.csv
Env: DISCORD_WEBHOOK_URL (optional; prints if unset). TICKERS (default SPY,QQQ).
"""
import csv, json, os, sys, time, urllib.parse, urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo
import numpy as np
import ind, quotes

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(ROOT, "ledger", "signals.csv")
TICKERS = os.environ.get("TICKERS", "SPY,QQQ").split(",")
RSI_MAX, DEM_MAX = 35.0, 0.30


def bars(t):
    u = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(t)}?period1=0&period2={int(time.time()) + 86400}&interval=1d"
    for k in range(4):
        try:
            r = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read())["chart"]["result"][0]
            break
        except Exception as e:
            err = e; time.sleep(2 + 2 * k)
    else:
        raise err
    q = r["indicators"]["quote"][0]
    d = [datetime.fromtimestamp(x, ZoneInfo("America/New_York")).date() for x in r["timestamp"]]
    a = np.array([q["high"], q["low"], q["close"]], dtype=float)
    ok = ~np.isnan(a).any(axis=0)
    return [x for x, m in zip(d, ok) if m], a[0][ok], a[1][ok], a[2][ok]


def reading(t):
    d, h, l, c = bars(t)
    lag = lambda x: np.concatenate([[np.nan], x[:-1]])
    r = ind.rsi(c, 14)[-1]
    dmx = np.maximum(np.nan_to_num(h - lag(h)), 0); dmn = np.maximum(np.nan_to_num(lag(l) - l), 0)
    dem = (ind.sma(dmx, 14) / (ind.sma(dmx, 14) + ind.sma(dmn, 14)))[-1]
    return d[-1], float(c[-1]), float(r), float(dem)


def main(mode):
    today = datetime.now(ZoneInfo("America/New_York")).date()
    rows, lines = [], []
    for t in TICKERS:
        d, px, r, dem = reading(t)
        if d != today:
            lines.append(f"{t}: last bar is {d}, not {today} (market closed or data late) - skipped"); continue
        on = r < RSI_MAX and dem < DEM_MAX
        rows.append([d.isoformat(), t, f"{px:.2f}", f"{r:.1f}", f"{dem:.3f}", int(on), mode])
        lines.append(f"{t} {px:.2f}  RSI14 {r:.1f}  DeMarker {dem:.2f}  -> {'SIGNAL ON' if on else 'off'}")
    any_on = any(x[5] for x in rows)
    qstat = quotes.run(mode, today, [x[1] for x in rows if x[5]], bool(rows))
    print(qstat)
    if mode == "alert" and not any_on and rows:
        print("\n".join(lines)); return  # quiet on no-signal days
    tag = "SIGNAL" if any_on else "no signal"
    note = ("Grand Tournament | RESEARCH / SHADOW - NOT A TRADE RECOMMENDATION\n"
            f"{'ALERT (partial bar, ~10 min before close)' if mode == 'alert' else 'CONFIRM (final close)'}: {tag}\n" + "\n".join(lines))
    if any_on and mode == "alert":
        note += ("\nRule: buy one ~0.30-delta call, first weekly expiry >= 14 days out, at the close; sell at next close. "
                 "Log the real ask now and the real bid tomorrow (shadow test).")
    if "FAILED" in qstat:
        note += "\n" + qstat
    print(note)
    hook = os.environ.get("DISCORD_WEBHOOK_URL")
    if hook:
        req = urllib.request.Request(hook, data=json.dumps({"content": note[:1900]}).encode(), headers={"Content-Type": "application/json", "User-Agent": "grand-tournament"})
        try: urllib.request.urlopen(req, timeout=30)
        except Exception as e: print("discord post failed:", e)
    if mode == "confirm" and rows:
        os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
        new = not os.path.exists(LEDGER)
        with open(LEDGER, "a", newline="") as f:
            w = csv.writer(f)
            if new: w.writerow(["date", "ticker", "close", "rsi14", "demarker14", "signal", "mode"])
            w.writerows(rows)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "alert")
