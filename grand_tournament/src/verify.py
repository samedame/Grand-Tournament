"""Post-freeze verification. Independent code paths: csv + math only for V1/V2 (no pandas rolling, no scipy, none of the frozen modules)."""
import csv, math, json, os, sys, datetime as dt, random
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); RAW = os.path.join(ROOT, "data", "raw"); RES = os.path.join(ROOT, "results")
out = []

def rd(name, datecol="date", fmt="%Y-%m-%d"):
    rows = list(csv.DictReader(open(os.path.join(RAW, name)))); res = []
    for r in rows:
        r = {k.strip().lower(): v for k, v in r.items()}
        try: res.append((dt.datetime.strptime(r[datecol][:10], fmt).date(), r))
        except Exception: pass
    return res

def bars(t):
    b = [(d, float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"])) for d, r in rd(f"{t}.csv") if r["close"] not in ("", "nan")]
    return [x for x in b if dt.date(2000, 5, 26) <= x[0] <= dt.date(2026, 11, 11)]

def idxvol(name):
    return {d: float(r["close"]) for d, r in rd(f"{name}_History.csv", fmt="%m/%d/%Y")}

def wilder_rsi(c, n=14):
    out = [None] * len(c); au = ad = None; ups = []; dns = []
    for i in range(len(c)):
        ch = c[i] - c[i - 1] if i else 0.0; u = max(ch, 0.0); d = max(-ch, 0.0)
        if au is None:
            ups.append(u); dns.append(d)
            if len(ups) == n: au = sum(ups) / n; ad = sum(dns) / n      # the frozen code seeds the same way (ewm, adjust=False, min_periods=n) only approximately
        else:
            au = (au * (n - 1) + u) / n; ad = (ad * (n - 1) + d) / n
        if au is not None: out[i] = 100.0 if ad == 0 and au > 0 else (50.0 if ad == 0 else 100 - 100 / (1 + au / ad))
    return out

def demarker(h, l, n=14):
    out = [None] * len(h); dmx = [0.0] * len(h); dmn = [0.0] * len(h)
    for i in range(1, len(h)): dmx[i] = max(h[i] - h[i - 1], 0.0); dmn[i] = max(l[i - 1] - l[i], 0.0)
    for i in range(n, len(h)):
        a = sum(dmx[i - n + 1:i + 1]) / n; b = sum(dmn[i - n + 1:i + 1]) / n
        out[i] = a / (a + b) if a + b > 0 else None
    return out

N = lambda x: 0.5 * (1 + math.erf(x / math.sqrt(2)))
def call(S, K, T, sig, r, q):
    if T <= 0: return max(S - K, 0.0), (1.0 if S > K else 0.0)
    d1 = (math.log(S / K) + (r - q + sig * sig / 2) * T) / (sig * math.sqrt(T)); d2 = d1 - sig * math.sqrt(T)
    return S * math.exp(-q * T) * N(d1) - K * math.exp(-r * T) * N(d2), math.exp(-q * T) * N(d1)
def iv(K, S, idx, T):
    atm = 0.8565 * idx / 100; m = math.log(K / S) / (atm * math.sqrt(T)) if T > 0 else 0.0
    return idx / 100 * min(1.45, max(0.60, 0.8565 - 0.240 * m))
def busdays(a, b):
    n = 0; d = a
    while d < b:
        if d.weekday() < 5: n += 1
        d += dt.timedelta(days=1)
    return n

irx = {d: float(r["close"]) / 100 for d, r in rd("^IRX.csv") if r["close"] not in ("", "nan")}
spy_days = [b[0] for b in bars("SPY")]; dayset = set(spy_days)
STRICT = "--loose" not in sys.argv
def expiry(d, target=14):
    # STRICT (the frozen code's reading): the expiry date after any holiday adjustment must be at least `target` days out.
    # --loose: a Friday at least `target` days out whose expiry moves to the Thursday (Good Friday) still counts.
    x = d + dt.timedelta(days=target)
    while True:
        if x.weekday() == 4 and (x >= dt.date(2012, 1, 1) or 15 <= x.day <= 21):
            e = x
            if e <= spy_days[-1]:
                while e not in dayset: e -= dt.timedelta(days=1)
            if e >= d + dt.timedelta(days=target) or not STRICT: return e
        x += dt.timedelta(days=1)

led = list(csv.DictReader(open(os.path.join(RES, "ledger_winner.csv")))); mine = {}
VOL = {"SPY": "VIX", "QQQ": "VXN", "IWM": "RVX"}; DIV = {"SPY": .016, "QQQ": .006, "IWM": .012}; SM = {"SPY": 1.0, "QQQ": 1.5, "IWM": 1.5}
for t in ("SPY", "QQQ", "IWM"):
    b = bars(t); d = [x[0] for x in b]; h = [x[2] for x in b]; l = [x[3] for x in b]; c = [x[4] for x in b]
    rs = wilder_rsi(c); dm = demarker(h, l); vol = idxvol(VOL[t]); rate = None; rates = []
    for x in d:
        rate = irx.get(x, rate); rates.append(rate)
    volf = []; last = None
    for x in d:
        last = vol.get(x, last); volf.append(last)
    for i in range(len(d) - 1):
        if d[i] < dt.date(2010, 1, 1): continue
        if rs[i] is not None and dm[i] is not None and rs[i] < 35 and dm[i] < 0.3:
            e = expiry(d[i]); T0 = busdays(d[i], e) / 252; T1 = busdays(d[i + 1], e) / 252; S0, S1 = c[i], c[i + 1]; q = DIV[t]
            best = None
            for K in range(int(S0 * 0.9), int(S0 * 1.25) + 1):
                p, dl = call(S0, K, T0, iv(K, S0, volf[i], T0), rates[i], q)
                if best is None or abs(dl - 0.30) < best[0]: best = (abs(dl - 0.30), K, p, dl)
            _, K, p0, d0 = best; p1, _ = call(S1, K, T1, iv(K, S1, volf[i + 1], T1), rates[i + 1], q)
            sp = max(0.01, 3.88e-4 * S0 * SM[t] * min(1.25, max(0.25, abs(d0) / 0.65)))
            mine[(t, d[i].isoformat())] = ((p1 - p0) * 100 - 100 * sp - 1.30, p0 * 100, K)
theirs = {(r["ticker"], r["entry"][:10]): (float(r["pnl_1.0"]), float(r["risk"])) for r in led}
only_m = set(mine) - set(theirs); only_t = set(theirs) - set(mine); both = set(mine) & set(theirs)
dp = max(abs(mine[k][0] - theirs[k][0]) for k in both); dr = max(abs(mine[k][1] - theirs[k][1]) for k in both)
out.append(("V1 independent csv+math re-implementation of the winner's two indicators and trade list (3 ETFs, 2010 to 2026-11)", len(only_m) == 0 and len(only_t) == 0,
            f"{len(theirs)} trades in the ledger, {len(mine)} rebuilt; only in rebuild {len(only_m)}, only in ledger {len(only_t)}"))
out.append(("V2 independent scalar option pricing of every winner trade (own expiry rule, brute-force strike scan, erf-based Black-Scholes)", dp < 0.01 and dr < 0.01,
            f"{len(both)} trades; max abs difference: P&L {dp:.2e} dollars, premium {dr:.2e} dollars"))

# V4 headline numbers recomputed from the saved ledger with separate code and a different random generator
oos = [r for r in led if r["seg"] == "2"]; x = [float(r["ror_1.0"]) for r in oos]; mean = sum(x) / len(x)
months = {}; 
for r in oos: months.setdefault(r["entry"][:7], []).append(float(r["ror_1.0"]))
allm = []; y, m = 2020, 1
while (y, m) <= (2026, 11):
    allm.append(months.get(f"{y}-{m:02d}", [])); m += 1
    if m == 13: y, m = y + 1, 1
random.seed(7); bm = []
for _ in range(10000):
    s = n = 0
    for _ in range(len(allm)):
        k = allm[random.randrange(len(allm))]; s += sum(k); n += len(k)
    bm.append(s / n if n else 0.0)
bm.sort(); ms = [sum(k) for k in allm]; mu = sum(ms) / len(ms); sd = math.sqrt(sum((v - mu) ** 2 for v in ms) / (len(ms) - 1)); shp = mu / sd * math.sqrt(12)
fin = json.load(open(os.path.join(RES, "final.json")))["winner"]["boot_oos"]
ok = abs(mean - fin["mean"]) < 1e-9 and abs(shp - fin["sharpe"]) < 1e-6 and abs(bm[500] - fin["lo"]) < 0.01 and abs(bm[9500] - fin["hi"]) < 0.015
out.append(("V4 headline statistics recomputed from the saved trades by separate code", ok,
            f"n {len(x)}, mean {100*mean:.2f}% (saved {100*fin['mean']:.2f}%), Sharpe {shp:.3f} (saved {fin['sharpe']:.3f}), 90% interval {100*bm[500]:.1f}% to {100*bm[9500]:.1f}% (saved {100*fin['lo']:.1f}% to {100*fin['hi']:.1f}%), share of bootstrap means at or below zero {sum(v <= 0 for v in bm)/10000:.4f}"))
json.dump([{"check": a, "pass": bool(b), "detail": c} for a, b, c in out], open(os.path.join(RES, "verify_part1.json"), "w"), indent=1)
for a, b, c in out: print("PASS" if b else "FAIL", "-", a, "|", c)

alt = [(mine[k][0] / mine[k][1]) for k in both if k[1] >= "2020-01-01"]; print("OOS mean return on risk with this script's own prices:", round(100 * sum(alt) / len(alt), 3), "%")
if "--diag" in sys.argv:
    bad = sorted(both, key=lambda k: -abs(mine[k][1] - theirs[k][1]))
    nb = sum(abs(mine[k][1] - theirs[k][1]) > 0.01 for k in both); print("trades differing in premium:", nb)
    for k in bad[:8]: print(k, "mine pnl/prem/K", [round(v, 2) for v in mine[k]], "ledger pnl/prem", [round(v, 2) for v in theirs[k]])
