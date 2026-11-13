"""Offline tests for src/quotes.py with a fake Tradier (no network, no token needed). Run: python src/test_quotes.py"""
import os, sys, tempfile
from datetime import date
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quotes as q

def opt(sym, k, delta, bid, ask, typ="call"):
    return {"symbol": sym, "strike": k, "option_type": typ, "expiration_date": "2026-12-04", "bid": bid, "ask": ask,
            "greeks": {"delta": delta, "mid_iv": 0.2}}
CHAIN = [opt("SPY261204C00700000", 700, 0.82, 12.0, 12.2), opt("SPY261204C00720000", 720, 0.31, 3.0, 3.1),
         opt("SPY261204C00730000", 730, 0.18, 1.2, 1.3), opt("SPY261204P00700000", 700, -0.2, 1, 1.1)]
state = {"bid": 3.4}
def fake(path, params):
    if path.endswith("expirations"):
        return {"expirations": {"date": ["2026-11-20", "2026-11-25", "2026-11-27", "2026-12-04", "2026-12-11"]}}
    if path.endswith("chains"):
        assert params["expiration"] == "2026-11-27" and params["greeks"] == "true"
        return {"options": {"option": CHAIN}}
    if path.endswith("quotes"):
        s = params["symbols"]
        if s == "SPY": return {"quotes": {"quote": {"symbol": "SPY", "last": 715.5}}}
        return {"quotes": {"quote": {"symbol": s, "strike": 720, "expiration_date": "2026-12-04", "bid": state["bid"], "ask": 3.5, "greeks": {"delta": 0.35, "mid_iv": 0.21}}}}
    raise AssertionError(path)
q.http_get = fake
q.LEDGER = os.path.join(tempfile.mkdtemp(), "quotes.csv")
os.environ["TRADIER_TOKEN"] = "x"

t0, t1 = date(2026, 11, 13), date(2026, 11, 16)   # Friday signal day; Monday confirm (next close)
# expiry rule: first Friday >= 14 days out
assert q.pick_expiry(t0, ["2026-11-20", "2026-11-27", "2026-12-04"]) == "2026-11-27"
assert q.pick_expiry(date(2026, 11, 12), ["2026-11-20", "2026-11-27", "2026-12-04"]) == "2026-11-27"
assert q.pick_expiry(date(2026, 11, 13), ["2026-11-20", "2026-11-25", "2026-12-04"]) == "2026-12-04"
print("PASS expiry rule")
assert q.pick_call(CHAIN, 0.30)["strike"] == 720 and q.pick_call(CHAIN, 0.80)["strike"] == 700
assert q.pick_call([opt("P", 1, -0.3, 1, 1, "put")], 0.3) is None
print("PASS strike pick")
# no-signal, non-baseline day logs nothing; signal day logs 2 entries (0.30 + 0.80)
rows_before = len(q.read_ledger())
msg = q.run("alert", t0, ["SPY"], True); assert "logged 2" in msg, msg
rows = q.read_ledger(); assert len(rows) - rows_before == 2 and all(r["event"] == "entry" for r in rows[-2:])
print("PASS signal entries:", [(r["target_delta"], r["strike"], r["ask"]) for r in rows[-2:]])
# exit: not on same day, yes next day, only once
assert "logged 0" in q.run("confirm", t0, [], True)
assert "logged 2" in q.run("confirm", t1, [], True)
assert "logged 0" in q.run("confirm", t1, [], True)
ex = [r for r in q.read_ledger() if r["event"] == "exit"]
assert len(ex) == 2 and all(r["entry_date"] == "2026-11-13" for r in ex) and ex[0]["bid"] == "3.4"
print("PASS exits once, matched to entry")
# baseline cadence ~1/8 and deterministic
n = sum(q.is_baseline_day(date(2026, 1, 1).fromordinal(date(2026, 1, 1).toordinal() + i)) for i in range(400))
assert 30 <= n <= 70, n
print("PASS baseline cadence", n, "/ 400 days")
# failure must not raise
def boom(*a): raise RuntimeError("down")
q.http_get = boom; m = q.run("alert", t0, ["QQQ"], True); assert m.startswith("quotes: FAILED"), m
del os.environ["TRADIER_TOKEN"]; assert q.run("alert", t0, ["SPY"], True).endswith("skipped")
print("PASS failure isolation and no-token skip")
