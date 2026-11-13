"""Post-freeze extras: rerun comparison, mutation checks, delta ladder for the winner's signal with IV sensitivity."""
import json, os, numpy as np, pandas as pd, hashlib
import prep, options as op, engine as en, stats as st, run as rn
import robust as rb          # reuses the Market and the repricing helpers (re-runs robust.py output as a side effect)
M = rb.M; RES = rn.RES; sel = rb.sel; w = sel["winner"]; out = {}
# V3 rerun
same = True; worst = 0.0
for h, mode, side in rn.BLOCKS:
    a = np.load(os.path.join(RES, "blocks", f"h{h}_{mode}_{side}.npz")); b = np.load(os.path.join(RES, "blocks_run1", f"h{h}_{mode}_{side}.npz"))
    for k in a.files: same &= bool(np.array_equal(a[k], b[k]))
s1 = json.load(open(os.path.join(RES, "select.json"))); s2 = json.load(open(os.path.join(RES, "select_run1.json")))
out["V3"] = {"pass": bool(same and s1 == s2), "detail": f"30 result blocks identical: {same}; selection file identical: {s1 == s2}"}
# V5 look-ahead on the winner's two readings at 40 cuts
import ind
bad = 0; chk = 0; rng = np.random.default_rng(11); full = M.dates; cal = ind.calendar(full)
for t in prep.CORE:
    L0 = M.states[t][0]
    for c in rng.integers(2600, len(full) - 2, 40):
        a = {k: (v[:c] if isinstance(v, np.ndarray) and len(v) == len(full) else v) for k, v in M.D[t].items()}
        cal2 = {k: (v[:c] if hasattr(v, "__len__") and len(v) == len(full) else v) for k, v in cal.items()}
        L1 = ind.states(a, cal2)[3]
        for i in (w["i"], w["j"]): bad += int((L1[:, i] != L0[:c, i]).sum()); chk += c
out["V5"] = {"pass": bad == 0, "detail": f"{chk} values of the winner's two readings recomputed on truncated data at 120 cut points, changed: {bad}"}
# V6 mutations
Lw = pd.read_csv(os.path.join(RES, "ledger_winner.csv"), parse_dates=["entry", "exit"]); x = Lw[Lw.seg == 2]; si = op.STRUCTS.index("LONG30"); puts = []
for t in M.tickers:
    k = M.dates.searchsorted(pd.DatetimeIndex(x.entry[x.ticker == t])); puts += list(M.opt[t][1]["ror"][1, si, en.C1X, k])
mut = {}
for nm, args in (("hold 2", (w["i"], w["j"], 2, "STATE", "L", "LONG30")), ("fresh entries only", (w["i"], w["j"], 1, "FRESH", "L", "LONG30")), ("RSI reading alone", (w["i"], w["i"], 1, "STATE", "L", "LONG30")), ("bearish side", (w["i"], w["j"], 1, "STATE", "S", "LONG30"))):
    L = en.ledger(M, *args); mut[nm] = bool(len(L) != len(Lw) or not np.array_equal(L.entry.values, Lw.entry.values))
out["V6"] = {"pass": bool(np.mean(puts) < 0 and all(mut.values())), "detail": f"same entry days with 0.30-delta puts instead of calls: {100*np.mean(puts):+.2f}% of risk per trade OOS (calls {100*x['ror_1.0'].mean():+.2f}%); rule mutations change the trade table: {mut}"}
# delta ladder for the winner's signal, 1-session hold
lad = []
for struct in ("LONG80", "LONG65", "LONG50", "LONG30"):
    L = en.ledger(M, w["i"], w["j"], 1, "STATE", "L", struct); L = L.copy()
    for nm, kw in (("base", {}), ("ts", {"ts": True}), ("over5", {"entry_mult": 1.05}), ("over10", {"entry_mult": 1.10}), ("ts_over10", {"ts": True, "entry_mult": 1.10}), ("over20", {"entry_mult": 1.20})):
        L[nm] = rb.reprice(L, 1, struct, **kw)
    # break-even entry overpay (bisection on the OOS mean)
    lo, hi = 0.0, 0.6; o = L[L.seg == 2]
    for _ in range(20):
        mid = (lo + hi) / 2; v = rb.reprice(o.reset_index(drop=True), 1, struct, entry_mult=1 + mid).mean(); lo, hi = (mid, hi) if v > 0 else (lo, mid)
    row = {"struct": struct, "breakeven_entry_iv_overpay": lo, "avg_premium_oos": float(o.risk.mean()), "usd_1x_oos": float(o["pnl_1.0"].mean()), "win_oos": float((o["pnl_1.0"] > 0).mean()),
           "worst_usd": float(o["pnl_1.0"].min()), "usd_mid_oos": float(o["pnl_0.0"].mean()), "usd_2x_oos": float(o["pnl_2.0"].mean())}
    for nm in ("base", "ts", "over5", "over10", "ts_over10", "over20"):
        for g, sg in enumerate(("dev", "val", "oos")):
            ms, nn = st.month_sums(L, M, g, nm); b = st.boot(ms, nn); row[f"{nm}_{sg}"] = b["mean"]; row[f"{nm}_{sg}_sh"] = b["sharpe"]; row[f"{nm}_{sg}_p"] = b["p_pos"]
    noev = L[~L.entry.isin(rb.EVENTS)]; ms, nn = st.month_sums(noev, M, 2, "ts"); b = st.boot(ms, nn); row["ts_noev_oos"] = b["mean"]; row["ts_noev_oos_p"] = b["p_pos"]
    o2 = o[o.ticker != "IWM"]; row["base_oos_ex_iwm"] = float(o2["ror_1.0"].mean()); row["usd_oos_ex_iwm"] = float(o2["pnl_1.0"].mean()); row["n_oos_ex_iwm"] = int(len(o2))
    lad.append(row)
out["ladder"] = lad
# drawdown / streak facts for the winner (one contract per signal, OOS, 1x)
o = Lw[Lw.seg == 2].sort_values("entry"); eq = o["pnl_1.0"].cumsum().values; dd = (eq - np.maximum.accumulate(eq)).min()
ls = 0; cur = 0
for v in o["pnl_1.0"].values:
    cur = cur + 1 if v <= 0 else 0; ls = max(ls, cur)
ms, nn = st.month_sums(Lw, M, 2, "pnl_1.0")
out["winner_path"] = {"total_usd_oos": float(eq[-1]), "max_drawdown_usd": float(dd), "longest_losing_streak": int(ls), "share_months_with_trades": float((nn > 0).mean()), "share_positive_months_of_traded": float((ms[nn > 0] > 0).mean()),
                      "worst_month_usd": float(ms.min()), "best_month_usd": float(ms.max()), "top15_share": float(o["pnl_1.0"].nlargest(15).sum() / o["pnl_1.0"].sum()), "avg_premium": float(o.risk.mean()), "max_same_day_positions": 3}
json.dump(out, open(os.path.join(RES, "extras.json"), "w"), indent=1, default=float)
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 80)
for k in ("V3", "V5", "V6"): print("PASS" if out[k]["pass"] else "FAIL", k, out[k]["detail"])
print(pd.DataFrame(lad).set_index("struct").round(3).T.to_string()); print(out["winner_path"])
