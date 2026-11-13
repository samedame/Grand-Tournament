"""Load raw files into aligned per-ticker arrays. No strategy logic here."""
import os, numpy as np, pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
CORE = ["SPY", "QQQ", "IWM"]
XFER = ["DIA", "GLD", "TLT", "EFA", "EEM"]
VOLIDX = {"SPY": "VIX", "QQQ": "VXN", "IWM": "RVX"}
DIVY = {"SPY": 0.016, "QQQ": 0.006, "IWM": 0.012}
SPREAD_MULT = {"SPY": 1.0, "QQQ": 1.5, "IWM": 1.5}
FIRST = "2000-05-26"          # first IWM bar; all core tickers start here
LAST = "2026-11-11"
TRADE_START = "2001-07-02"    # after 252+ bar warm-up
SEG_EDGES = ["2015-01-01", "2020-01-01"]   # option window: dev 2010-2014, val 2015-2019, oos 2020 to 2026-11-11
OPT_START = "2010-01-01"      # RVX/VXN official Cboe histories start 2009-09
WEEKLY_START = "2012-01-01"   # Friday weeklies assumed listed from here; 3rd-Friday monthlies before


def _yahoo(t):
    d = pd.read_csv(os.path.join(RAW, f"{t}.csv"), parse_dates=["date"])
    return d[(d.date >= FIRST) & (d.date <= LAST)].reset_index(drop=True)


def _cboe(name):
    d = pd.read_csv(os.path.join(RAW, f"{name}_History.csv"))
    d.columns = [c.strip().lower() for c in d.columns]
    d["date"] = pd.to_datetime(d["date"])
    return d.drop_duplicates("date").set_index("date").sort_index()


def load(tickers=None):
    tickers = tickers or CORE
    spy = _yahoo("SPY")
    dates = spy.date.values
    vix = _cboe("VIX"); vix3m = pd.read_csv(os.path.join(RAW, "^VIX3M.csv"), parse_dates=["date"]).set_index("date")
    irx = pd.read_csv(os.path.join(RAW, "^IRX.csv"), parse_dates=["date"]).set_index("date")["close"]
    tlt = pd.read_csv(os.path.join(RAW, "TLT.csv"), parse_dates=["date"]).set_index("date")
    out = {}
    for t in tickers:
        d = _yahoo(t)
        if t in CORE:
            assert len(d) == len(spy) and (d.date.values == dates).all(), f"{t} calendar mismatch"
        else:  # transfer tickers keep their own (shorter) history
            assert d.date.isin(spy.date).all(), f"{t} has dates SPY lacks"
        a = {k: d[k].values.astype(float) for k in ["open", "high", "low", "close", "volume"]}
        a["dates"] = d.date.values
        a["vix"] = vix["close"].reindex(d.date).ffill().values
        a["vix3m"] = vix3m["close"].reindex(d.date).values
        a["rate"] = (irx.reindex(d.date).ffill().values) / 100.0
        a["bench"] = spy.set_index("date")["close"].reindex(d.date).values if t != "SPY" else np.full(len(d), np.nan)
        a["tlt"] = tlt["close"].reindex(d.date).values
        if t in VOLIDX:
            v = _cboe(VOLIDX[t]).reindex(d.date)
            a["iv_close"] = v["close"].ffill(limit=2).values
            a["iv_open"] = v["open"].values
        out[t] = a
    return out


def segments_long(dates):
    d = pd.DatetimeIndex(dates)
    seg = np.full(len(d), -1)
    seg[d >= TRADE_START] = 0
    seg[d >= SEG_EDGES[0]] = 1
    seg[d >= SEG_EDGES[1]] = 2
    return seg


if __name__ == "__main__":
    D = load(CORE + XFER)
    for t, a in D.items():
        c = a["close"]; r = c[1:] / c[:-1] - 1
        print(t, len(c), str(a["dates"][0])[:10], str(a["dates"][-1])[:10], "nan", int(np.isnan(c).sum()),
              "max|r|", round(float(np.abs(r).max()), 3), "iv nan from 2010",
              int(np.isnan(a["iv_close"][pd.DatetimeIndex(a["dates"]) >= OPT_START]).sum()) if "iv_close" in a else "-")
    s = segments(D["SPY"]["dates"]); print("segment days", [(k, int((s == k).sum())) for k in (-1, 0, 1, 2)])
