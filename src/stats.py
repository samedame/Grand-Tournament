"""Statistics for finalists: month-cluster bootstrap, monthly Sharpe, random-entry placebo, gates."""
import numpy as np, pandas as pd
import options as op, engine as en

SEED = 20261112; B = 10000


def month_sums(L, M, seg, col):
    ms = np.zeros(M.nm); nn = np.zeros(M.nm); x = L[L.seg == seg]
    np.add.at(ms, x.month.values, x[col].values); np.add.at(nn, x.month.values, 1.0)
    keep = M.mseg == seg
    return ms[keep], nn[keep]


def sharpe(ms):
    return float(ms.mean() / ms.std(ddof=1) * np.sqrt(12)) if ms.std(ddof=1) > 0 else 0.0


def boot(ms, nn, seed=SEED, b=B):
    """Month-cluster bootstrap of the per-trade mean (ratio estimator) and of the monthly Sharpe."""
    rng = np.random.default_rng(seed); k = len(ms); idx = rng.integers(0, k, (b, k))
    s = ms[idx].sum(1); n = nn[idx].sum(1); mean = np.where(n > 0, s / np.maximum(n, 1), 0.0)
    x = ms[idx]; sd = x.std(1, ddof=1); sh = np.where(sd > 0, x.mean(1) / np.where(sd > 0, sd, 1) * np.sqrt(12), 0.0)
    return {"mean": float(ms.sum() / max(nn.sum(), 1)), "lo": float(np.quantile(mean, 0.05)), "hi": float(np.quantile(mean, 0.95)),
            "p_pos": float((mean <= 0).mean()), "p_neg": float((mean >= 0).mean()), "sharpe": sharpe(ms),
            "sh_lo": float(np.quantile(sh, 0.05)), "sh_hi": float(np.quantile(sh, 0.95)), "n": int(nn.sum())}


def placebo(M, L, h, struct, seg=2, runs=1000, seed=SEED):
    """Random entry days with the same number of trades per ETF, calendar year and side, same hold and structure.
    Returns the share of random runs whose mean return on risk (1x cost) is below the real one."""
    rng = np.random.default_rng(seed); x = L[L.seg == seg]; si = op.STRUCTS.index(struct); real = x["ror_1.0"].mean()
    yr = M.dates.year.to_numpy(); plan = []
    for t in M.tickers:
        o = M.opt[t][h]; ok = o["valid"] & (M.seg == seg)
        xt = x[x.ticker == t]
        for y in sorted(set(yr[ok])):
            days = np.where(ok & (yr == y))[0]
            kb = int(((xt.entry.dt.year == y) & (xt.side == "bull")).sum()); ks = int(((xt.entry.dt.year == y) & (xt.side == "bear")).sum())
            if kb + ks: plan.append((t, days, kb, ks))
    out = np.zeros(runs)
    for r in range(runs):
        tot = 0.0; cnt = 0
        for t, days, kb, ks in plan:
            o = M.opt[t][h]["ror"]; perm = rng.permutation(days); taken = []; k = kb + ks; blocked = set()
            for d in perm:
                if d not in blocked:
                    taken.append(d); blocked.update(range(d - h + 1, d + h))
                    if len(taken) == k: break
            for q, d in enumerate(taken):
                tot += o[0 if q < kb else 1, si, en.C1X, d]; cnt += 1
        out[r] = tot / max(cnt, 1)
    return {"real": float(real), "pctile": float((out < real).mean()), "placebo_mean": float(out.mean()), "placebo_p95": float(np.quantile(out, 0.95))}


def gates(M, L, h, struct, holm_p, split="2023-06-01"):
    x = L[L.seg == 2]; g = {}
    ms, nn = month_sums(L, M, 2, "ror_1.0"); b1 = boot(ms, nn)
    ms2, _ = month_sums(L, M, 2, "ror_2.0")
    g["G1"] = (b1["mean"] > 0 and holm_p < 0.10, f"mean {100*b1['mean']:+.2f}% of risk per trade, Holm p = {holm_p:.3f}")
    g["G2"] = (ms2.sum() > 0, f"mean at 2x spread {100*ms2.sum()/max(nn.sum(),1):+.2f}%")
    g["G3"] = (b1["sharpe"] > 0.5, f"monthly Sharpe {b1['sharpe']:+.2f}")
    pl = placebo(M, L, h, struct); g["G4"] = (pl["pctile"] >= 0.95, f"beats {100*pl['pctile']:.1f}% of random-entry runs (random mean {100*pl['placebo_mean']:+.2f}%)")
    bt = x.groupby("ticker")["ror_1.0"].mean(); spy = bt.get("SPY", -1); oth = max(bt.get("QQQ", -1), bt.get("IWM", -1))
    g["G5"] = (spy > 0 and oth > 0, ", ".join(f"{k} {100*v:+.2f}%" for k, v in bt.items()))
    g["G6"] = (len(x) >= 120, f"{len(x)} trades")
    y = x.sort_values("ror_1.0", ascending=False); drop = y.groupby("ticker").head(5).index; z = x.drop(drop)
    g["G7"] = (len(z) > 0 and z["ror_1.0"].mean() > 0, f"mean without the 5 best trades per ETF {100*z['ror_1.0'].mean():+.2f}%")
    a = x[x.entry < split]["ror_1.0"].mean(); c = x[x.entry >= split]["ror_1.0"].mean()
    g["G8"] = (a > 0 and c > 0, f"first half {100*a:+.2f}%, second half {100*c:+.2f}%")
    return g, b1, pl


def label(g, b1):
    if all(v[0] for v in g.values()): return "PARTIAL (PROXY), Tier B: forward-test with real quotes"
    if not g["G6"][0]: return "INCONCLUSIVE"
    if b1["mean"] < 0 and b1["p_neg"] < 0.10: return "NEGATIVE EXPECTANCY (PROXY)"
    return "NO EDGE DEMONSTRATED (PROXY)"
