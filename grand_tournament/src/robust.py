"""Post-freeze robustness (descriptive, post hoc): term-structure repricing, IV overpay, event-day removal,
shares before the option window, next-open fill, neighbours, other ETFs. Reads frozen code; changes nothing frozen."""
import json, os, numpy as np, pandas as pd
import prep, ind, options as op, engine as en, stats as st, run as rn

M = en.Market(); RES = rn.RES; sel = json.load(open(os.path.join(RES, "select.json"))); out = {}
v9 = pd.read_csv(os.path.join(prep.RAW, "extra_VIX9D_cboe.csv")); v9.columns = [c.strip().lower() for c in v9.columns]
v9["date"] = pd.to_datetime(v9["date"]); v9 = v9.set_index("date")["close"].reindex(M.dates).to_numpy()
vix = M.D["SPY"]["iv_close"]; v3m = M.D["SPY"]["vix3m"]

def ts_ratio(k, T):
    """SPX implied vol at maturity T (total-variance interpolation of VIX9D / VIX / VIX3M) divided by VIX, on day index k."""
    d = np.maximum(T * 252 * 1.4, 1.0); a, b, c = v9[k], vix[k], v3m[k]
    a = np.where(np.isnan(a), b, a); c = np.where(np.isnan(c), b, c)
    w9, w30, w93 = a * a * 9, b * b * 30, c * c * 93
    w = np.where(d <= 9, a * a * d, np.where(d <= 30, w9 + (w30 - w9) * (d - 9) / 21, w30 + (w93 - w30) * (np.minimum(d, 93) - 30) / 63))
    return np.sqrt(np.maximum(w, 1e-6) / np.minimum(d, 93)) / b

def reprice(L, h, struct, ts=False, entry_mult=1.0):
    """Re-price single-leg long-call trades of a ledger. Returns return on risk at 1x cost per trade."""
    tg = {"LONG80": .80, "LONG65": .65, "LONG50": .50, "LONG30": .30}[struct]; res = np.zeros(len(L))
    for t in M.tickers:
        m = (L.ticker == t).to_numpy(); k = M.dates.searchsorted(pd.DatetimeIndex(L.entry[m])); a = M.D[t]; o = M.opt[t][h]
        e = o["expiry"][k]; T0 = op.tyears(M.dates[k], e); T1 = op.tyears(M.dates[k + h], e); q = prep.DIVY[t]
        S0, S1, r0, r1 = a["close"][k], a["close"][k + h], a["rate"][k], a["rate"][k + h]
        i0 = a["iv_close"][k] * (ts_ratio(k, T0) if ts else 1.0); i1 = a["iv_close"][k + h] * (ts_ratio(k + h, T1) if ts else 1.0)
        K = op.pick_strike(S0, i0, T0, r0, q, 1, tg)
        p0, d0 = op.bs(S0, K, T0, op.iv_at(K, S0, i0, T0) * entry_mult, r0, q, 1); p1, _ = op.bs(S1, K, T1, op.iv_at(K, S1, i1, T1), r1, q, 1)
        sp = op.HOUSE * S0 * prep.SPREAD_MULT[t] * np.clip(np.abs(d0) / 0.65, 0.25, 1.25)
        res[m] = ((p1 - p0) * 100 - (100 * np.maximum(0.01, sp) + 2 * op.COMM)) / (p0 * 100)
    return res

def summ(L, col):
    r = {}
    for g, nm in enumerate(("dev", "val", "oos")):
        ms, nn = st.month_sums(L, M, g, col); b = st.boot(ms, nn); r[nm] = {"mean": b["mean"], "sharpe": b["sharpe"], "p": b["p_pos"], "lo": b["lo"], "hi": b["hi"], "n": b["n"], "median": float(L[L.seg == g][col].median()), "win": float((L[L.seg == g][col] > 0).mean())}
    return r

EVENTS = pd.to_datetime(["2020-03-12", "2020-03-23", "2025-04-08"])
def scenarios(L, h, struct):
    L = L.copy(); S = {}
    L["base"] = reprice(L, h, struct); S["check_max_abs_diff_vs_ledger"] = float(np.abs(L["base"] - L["ror_1.0"]).max())
    L["ts"] = reprice(L, h, struct, ts=True); L["ts_over10"] = reprice(L, h, struct, ts=True, entry_mult=1.10); L["over10"] = reprice(L, h, struct, entry_mult=1.10); L["over20"] = reprice(L, h, struct, entry_mult=1.20)
    for c in ("base", "ts", "over10", "ts_over10", "over20"): S[c] = summ(L, c)
    S["ts_no_events"] = summ(L[~L.entry.isin(EVENTS)], "ts"); S["base_no_events"] = summ(L[~L.entry.isin(EVENTS)], "base")
    x = L[L.seg == 2]; k = M.dates.searchsorted(pd.DatetimeIndex(x.entry)); vx = vix[k]
    S["by_vix_oos"] = [{"bucket": nm, "n": int(mk.sum()), "base": float(x["base"][mk].mean()), "ts": float(x["ts"][mk].mean()), "shares_bp": float(1e4 * x.shares_ret[mk].mean())}
                       for nm, mk in (("VIX below 20", vx < 20), ("VIX 20 to 30", (vx >= 20) & (vx < 30)), ("VIX 30 or higher", vx >= 30))]
    S["avg_ts_ratio_at_entry_oos"] = float(np.mean([ts_ratio(np.array([kk]), np.array([15 / 252]))[0] for kk in k]))
    return S, L

w = sel["winner"]; Lw = pd.read_csv(os.path.join(RES, "ledger_winner.csv"), parse_dates=["entry", "exit"])
out["winner"], Lw2 = scenarios(Lw, w["hold"], w["struct"]); Lw2.to_csv(os.path.join(RES, "ledger_winner_scenarios.csv"), index=False)
Le = pd.read_csv(os.path.join(RES, "ledger_ensemble.csv"), parse_dates=["entry", "exit"]); parts = []; out["members"] = []
for kk, m in enumerate(sel["top10"]):
    S, L2 = scenarios(Le[Le.member == kk].reset_index(drop=True), m["hold"], m["struct"]); parts.append(L2)
    out["members"].append({"a": m["a"], "b": m["b"], "hold": m["hold"], "struct": m["struct"], "base_oos": S["base"]["oos"], "ts_oos": S["ts"]["oos"], "ts_over10_oos": S["ts_over10"]["oos"], "ts_no_events_oos": S["ts_no_events"]["oos"]})
P = pd.concat(parts, ignore_index=True)
out["ensemble"] = {c: summ(P, c) for c in ("base", "ts", "over10", "ts_over10")}; out["ensemble"]["ts_no_events"] = summ(P[~P.entry.isin(EVENTS)], "ts")

# ---- shares: before the option window, next-open fill, other ETFs ----
def shares(tickers, i, j, h, mode, side):
    D = prep.load(tickers); rows = []
    for t in tickers:
        a = D[t]; d = pd.DatetimeIndex(a["dates"]); cal = ind.calendar(d); names, kinds, fams, Ls, Ss = ind.states(a, cal)
        sl = (Ls[:, i] & Ls[:, j])[:, None]; ss = (Ss[:, i] & Ss[:, j])[:, None]
        if mode == "FRESH": sl, ss = en.fresh(sl), en.fresh(ss)
        if side == "L": ss = np.zeros_like(ss)
        if side == "S": sl = np.zeros_like(sl)
        t0 = max(int(d.searchsorted(pd.Timestamp(prep.TRADE_START))), 260); EL, ES = en.scan(sl, ss, h, t0, np.ones(len(d), bool))
        for sgn, E in ((1, EL[:, 0]), (-1, ES[:, 0])):
            for k in np.where(E)[0]:
                rows.append({"ticker": t, "entry": d[k], "cc": sgn * (a["close"][k + h] / a["close"][k] - 1), "oc": sgn * (a["close"][k + h] / a["open"][k + 1] - 1), "ovn": sgn * (a["open"][k + 1] / a["close"][k] - 1)})
    return pd.DataFrame(rows)
def per(x):
    r = []
    for nm, lo, hi in (("2001-07 to 2009", "2001-07-01", "2010-01-01"), ("2010-2014", "2010-01-01", "2015-01-01"), ("2015-2019", "2015-01-01", "2020-01-01"), ("2020 to 2026-11", "2020-01-01", "2027-01-01")):
        z = x[(x.entry >= lo) & (x.entry < hi)]
        if len(z) == 0: continue
        mu = z.groupby(z.entry.dt.to_period("M")).cc.agg(["sum", "count"]); se = np.sqrt(((mu["sum"] - z.cc.mean() * mu["count"]) ** 2).sum()) / mu["count"].sum() * np.sqrt(len(mu) / max(len(mu) - 1, 1))
        r.append({"period": nm, "n": len(z), "cc_bp": float(1e4 * z.cc.mean()), "t_month_cluster": float(z.cc.mean() / se) if se > 0 else 0.0, "win": float((z.cc > 0).mean()), "overnight_bp": float(1e4 * z.ovn.mean()), "next_open_fill_bp": float(1e4 * z.oc.mean())})
    return r
sh = shares(prep.CORE, w["i"], w["j"], w["hold"], w["mode"], w["side"]); out["shares_core"] = per(sh)
out["shares_core_by_ticker"] = {t: per(sh[sh.ticker == t]) for t in prep.CORE}
xf = shares(prep.XFER, w["i"], w["j"], w["hold"], w["mode"], w["side"]); out["shares_other_etfs"] = {t: per(xf[xf.ticker == t]) for t in prep.XFER}

# ---- neighbours of the winner inside the frozen results ----
blocks = rn.load_blocks(); nb = []; names = M.names
def cfg_row(i, j, h, mode, side, si):
    b = blocks[h, mode, side]; p = int(np.where((M.pi == min(i, j)) & (M.pj == max(i, j)))[0][0])
    return {"a": names[min(i, j)], "b": names[max(i, j)] if i != j else "", "hold": h, "mode": mode, "side": side, "struct": op.STRUCTS[si], **{f"n_{s}": int(b["n"][p, g]) for g, s in enumerate(("dev", "val", "oos"))},
            **{f"sharpe_{s}": float(b["sharpe"][p, si, g]) for g, s in enumerate(("dev", "val", "oos"))}, **{f"mean_{s}": float(b["tot"][p, si, en.C1X, g] / max(b["n"][p, g], 1)) for g, s in enumerate(("dev", "val", "oos"))},
            "shares_bp_oos": float(1e4 * b["tot"][p, en.NS - 1, en.C1X, 2] / max(b["n"][p, 2], 1))}
i, j = w["i"], w["j"]
for h in op.HOLDS:
    for si in range(len(op.STRUCTS)): nb.append(cfg_row(i, j, h, "STATE", "L", si))
out["neighbours_hold_struct"] = nb
alt = []
for a_, b_ in (("RSI14_30", "DEM_30"), ("RSI14_35", "RSI14_35"), ("DEM_30", "DEM_30"), ("RSI14_30", "RSI14_30"), ("RSI5_30", "DEM_30"), ("RSI5_20", "DEM_30"), ("RSI14_35", "STO_20"), ("RSI14_35", "CCI_R"), ("RSI14_35", "IBS_20"), ("RSI2_10", "RSI2_10"), ("IBS_10", "IBS_10"), ("IBS_20", "IBS_20"), ("CRSI_20", "CRSI_20"), ("BB_R", "BB_R"), ("VIX_SPK", "VIX_SPK"), ("LOW10", "LOW10"), ("DN3", "DN3")):
    alt.append(cfg_row(names.index(a_), names.index(b_), 1, "STATE", "L", op.STRUCTS.index("LONG30")))
out["neighbours_signal"] = alt
json.dump(out, open(os.path.join(RES, "robust.json"), "w"), indent=1, default=float)
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 50)
W = out["winner"]; print("repricing check", W["check_max_abs_diff_vs_ledger"], "avg TS ratio at entry", round(W["avg_ts_ratio_at_entry_oos"], 3))
print(pd.DataFrame({c: {f"{s}_{k}": W[c][s][k] for s in ("dev", "val", "oos") for k in ("mean", "sharpe", "p")} for c in ("base", "ts", "over10", "ts_over10", "over20", "base_no_events", "ts_no_events")}).round(3).T.to_string())
print(pd.DataFrame(W["by_vix_oos"]).round(3).to_string())
print("ENS", pd.DataFrame({c: {f"{s}_{k}": out["ensemble"][c][s][k] for s in ("dev", "val", "oos") for k in ("mean", "sharpe", "p")} for c in out["ensemble"]}).round(3).T.to_string())
print(pd.DataFrame([{**{k: m[k] for k in ("a", "b", "hold", "struct")}, "base": m["base_oos"]["mean"], "ts": m["ts_oos"]["mean"], "ts_p": m["ts_oos"]["p"], "ts_sh": m["ts_oos"]["sharpe"], "ts_over10": m["ts_over10_oos"]["mean"], "ts_noev": m["ts_no_events_oos"]["mean"], "ts_noev_p": m["ts_no_events_oos"]["p"]} for m in out["members"]]).round(3).to_string())
print(pd.DataFrame(out["shares_core"]).round(2).to_string()); 
for t, v in {**out["shares_core_by_ticker"], **out["shares_other_etfs"]}.items(): print(t, [(r["period"][:7], r["n"], round(r["cc_bp"], 1), round(r["t_month_cluster"], 2)) for r in v])
print(pd.DataFrame(nb).pivot(index="struct", columns="hold", values="sharpe_oos").round(2).to_string()); print(pd.DataFrame(nb).pivot(index="struct", columns="hold", values="mean_oos").round(3).to_string())
print(pd.DataFrame(alt)[["a", "b", "n_dev", "n_val", "n_oos", "sharpe_dev", "sharpe_val", "sharpe_oos", "mean_dev", "mean_val", "mean_oos", "shares_bp_oos"]].round(3).to_string())
