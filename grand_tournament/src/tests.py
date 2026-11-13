"""Pre-freeze tests. None of them prints a strategy return."""
import numpy as np, pandas as pd, time, sys
import prep, ind, options as op, engine as en

def t_scan():
    rng = np.random.default_rng(1); T, P = 400, 60; bad = 0
    for h in op.HOLDS:
        sl = rng.random((T, P)) < 0.15; ss = (rng.random((T, P)) < 0.15) & ~sl; valid = rng.random(T) < 0.95
        EL, ES = en.scan(sl, ss, h, 10, valid)
        for p in range(P):                       # pure-Python reference
            nxt = 10; el = []; es = []
            for t in range(10, T - h):
                if t >= nxt and valid[t]:
                    if sl[t, p]: el.append(t); nxt = t + h
                    elif ss[t, p]: es.append(t); nxt = t + h
            bad += (list(np.where(EL[:, p])[0]) != el) + (list(np.where(ES[:, p])[0]) != es)
    return "scan vs pure-Python reference (5 holds x 60 random sets)", bad == 0, f"mismatching sets: {bad}"

def t_lookahead():
    D = prep.load(prep.CORE); full = pd.DatetimeIndex(D["SPY"]["dates"]); cal = ind.calendar(full); bad = 0; chk = 0
    rng = np.random.default_rng(2); cuts = sorted(rng.integers(3000, len(full) - 5, 6))
    for t in prep.CORE:
        n0, k0, f0, L0, S0 = ind.states(D[t], cal)
        for c in cuts:
            a = {k: (v[:c] if isinstance(v, np.ndarray) and len(v) == len(full) else v) for k, v in D[t].items()}
            cal2 = {k: (v[:c] if hasattr(v, "__len__") and len(v) == len(full) else v) for k, v in cal.items()}   # calendar is known in advance
            n1, k1, f1, L1, S1 = ind.states(a, cal2)
            bad += int((L1[c - 300:] != L0[c - 300:c]).sum() + (S1[c - 300:] != S0[c - 300:c]).sum()); chk += 2 * 300 * L0.shape[1]
    return "indicator states unchanged when later data is removed (3 ETFs x 6 cuts x last 300 days)", bad == 0, f"{chk} state values checked, changed: {bad}"

def t_options():
    rng = np.random.default_rng(3); S = rng.uniform(50, 700, 500); K = np.round(S * rng.uniform(0.8, 1.2, 500)); T = rng.uniform(1, 60, 500) / 252
    sig = rng.uniform(0.08, 0.8, 500); r = rng.uniform(0, 0.05, 500)
    c, dc = op.bs(S, K, T, sig, r, 0.01, 1); p, dp = op.bs(S, K, T, sig, r, 0.01, -1)
    e1 = np.abs(c - p - (S * np.exp(-0.01 * T) - K * np.exp(-r * T))).max(); e2 = np.abs(dc - dp - np.exp(-0.01 * T)).max()
    c0, _ = op.bs(S, K, np.zeros(500), sig, r, 0.01, 1); e3 = np.abs(c0 - np.maximum(S - K, 0)).max()
    D = prep.load(["SPY"]); o = op.build(D["SPY"], "SPY"); d = pd.DatetimeIndex(D["SPY"]["dates"]); ok = True
    for h in op.HOLDS:
        v = o[h]["valid"]; e = o[h]["expiry"]; ex = d[np.minimum(np.arange(len(d)) + h, len(d) - 1)]
        ok &= bool((e[v] >= ex[v]).all()) and bool(((e[v] - d[v]).days >= op.DTE_TARGET[h]).all()) and bool((e[v].weekday <= 4).all())
        ok &= bool((o[h]["risk"][:, :, v] > 5).all())
        # cost monotone: pnl falls as the spread multiple rises
        ok &= bool((np.diff(o[h]["pnl"][:, :, :, v], axis=2) <= 1e-9).all()) and bool((o[h]["pnl"][:, :, 3, v] < o[h]["pnl"][:, :, 0, v]).all())
    return "Black-Scholes parity, delta parity, intrinsic at expiry; expiry after exit; risk > 0; P&L falls with cost", (e1 < 1e-9) and (e2 < 1e-12) and (e3 < 1e-12) and ok, f"parity {e1:.1e}, delta {e2:.1e}, intrinsic {e3:.1e}, structure checks {ok}"

def t_block_vs_ledger():
    M = en.Market(); rng = np.random.default_rng(4); worst = 0.0; nbad = 0
    for h, mode, side in ((1, "STATE", "LS"), (3, "FRESH", "L"), (10, "STATE", "S"), (5, "FRESH", "LS")):
        B = en.run_block(M, h, mode, side)
        for p in rng.choice(M.P, 6, replace=False):
            for struct in ("LONG65", "CREDIT_V", "CONDOR"):
                L = en.ledger(M, M.pi[p], M.pj[p], h, mode, side, struct); si = op.STRUCTS.index(struct)
                for g in range(3):
                    x = L[L.seg == g] if len(L) else L
                    nbad += int(len(x) != int(B["n"][p, g]))
                    if len(x):
                        worst = max(worst, abs(float(x["ror_1.0"].sum()) - float(B["tot"][p, si, en.C1X, g])) / max(1.0, len(x)))
                        ms = np.zeros(M.nm); np.add.at(ms, x.month.values, x["ror_1.0"].values); ms = ms[M.mseg == g]
                        sh = ms.mean() / ms.std(ddof=1) * np.sqrt(12) if ms.std(ddof=1) > 0 else 0.0
                        worst = max(worst, abs(sh - float(B["sharpe"][p, si, g])) if abs(sh) < 50 else 0.0)
    return "matrix engine == per-trade ledger (4 blocks x 6 random sets x 3 structures x 3 periods)", nbad == 0 and worst < 2e-3, f"count mismatches {nbad}, max abs difference {worst:.1e}"

if __name__ == "__main__":
    allok = True
    for f in (t_scan, t_lookahead, t_options, t_block_vs_ledger):
        t0 = time.time(); name, ok, msg = f(); allok &= ok
        print(("PASS" if ok else "FAIL"), "-", name, "|", msg, f"({time.time() - t0:.0f}s)")
    sys.exit(0 if allok else 1)
