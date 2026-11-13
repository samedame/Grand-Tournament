"""Download daily bars (Yahoo v8 chart), Cboe volatility indices, FRED T-bill. Raw (unadjusted) OHLCV."""
import json, os, sys, time, urllib.request, urllib.parse, io
import pandas as pd, numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw"); os.makedirs(RAW, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0"}
TICKERS = ["SPY", "QQQ", "IWM", "DIA", "GLD", "TLT", "EFA", "EEM"]
CBOE = ["VIX", "VXN", "RVX", "VIX3M", "VXD"]
END = int(pd.Timestamp("2026-11-12", tz="UTC").timestamp())  # bars through 2026-11-11


def get(url, tries=4):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            return urllib.request.urlopen(req, timeout=60).read()
        except Exception as e:
            err = e; time.sleep(2 + 2 * k)
    raise err


def yahoo(t):
    u = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(t)}?period1=0&period2={END}&interval=1d&events=div%2Csplit"
    r = json.loads(get(u))["chart"]["result"][0]
    q = r["indicators"]["quote"][0]
    df = pd.DataFrame({"date": pd.to_datetime(r["timestamp"], unit="s", utc=True).tz_convert("America/New_York").normalize().tz_localize(None),
                       "open": q["open"], "high": q["high"], "low": q["low"], "close": q["close"], "volume": q["volume"],
                       "adjclose": r["indicators"]["adjclose"][0]["adjclose"]})
    df = df.dropna(subset=["open", "high", "low", "close"]).drop_duplicates("date").sort_values("date")
    ev = r.get("events", {})
    json.dump({"splits": ev.get("splits", {}), "ndiv": len(ev.get("dividends", {}))}, open(os.path.join(RAW, f"{t}_events.json"), "w"))
    df.to_csv(os.path.join(RAW, f"{t}.csv"), index=False)
    return df


if __name__ == "__main__":
    for t in TICKERS:
        d = yahoo(t); print(t, len(d), d.date.iloc[0].date(), d.date.iloc[-1].date(), round(d.close.iloc[-1], 2))
    for c in CBOE:
        b = get(f"https://cdn.cboe.com/api/global/us_indices/daily_prices/{c}_History.csv")
        open(os.path.join(RAW, f"{c}_History.csv"), "wb").write(b)
        d = pd.read_csv(io.BytesIO(b)); print(c, len(d), list(d.columns), d.iloc[0, 0], d.iloc[-1, 0])
    for t in ["^VIX", "^VXN", "^VIX3M", "^IRX"]:
        d = yahoo(t); print(t, len(d), d.date.iloc[0].date(), d.date.iloc[-1].date())
    sys.exit(0)  # FRED DTB3 unreachable from this sandbox on 2026-11-12; ^IRX used instead
    b = get("https://fred.stlouisfed.org/graph/fredgraph.csv?id=DTB3")
    open(os.path.join(RAW, "DTB3.csv"), "wb").write(b)
    d = pd.read_csv(io.BytesIO(b)); print("DTB3", len(d), d.iloc[-1].tolist())
