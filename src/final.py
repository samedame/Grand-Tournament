"""Post-freeze analysis of the finalists (reads frozen code and saved results; changes nothing frozen)."""
import json, os, numpy as np, pandas as pd, scipy.stats as ss
import prep, options as op, engine as en, stats as st, run as rn

M = en.Market(); RES = rn.RES; sel = json.load(open(os.path.join(RES, "select.json"))); blocks = rn.load_blocks(); out = {}
NSO = len(op.STRUCTS); SEGN = ("dev", "val", "oos")

# ---------- A. the whole universe ----------
sc, so, mo, st_i, hold_i = [], [], [], [], []
best_struct = {}
for (h, mode, side), b in blocks.items():
    n = b["n"]; el = (n[:, 0] >= rn.MIN_N[0]) & (n[:, 1] >= rn.MIN_N[1]) & (n[:, 2] >= rn.MIN_N[2])
    sh = b["sharpe"][el][:, :NSO]; score = np.minimum(sh[:, :, 0], sh[:, :, 1])
    sc.append(score.ravel()); so.append(sh[:, :, 2].ravel())
    mo.append((b["tot"][el][:, :NSO, :, 2] / n[el][:, None, None, 2]).reshape(-1, len(op.COSTS)))
    st_i.append(np.tile(np.arange(NSO), el.sum())); hold_i.append(np.full(score.size, h))
    idx = np.where(el)[0]
    for si in range(NSO):
        k = int(np.argmax(score[:, si])); p = idx[k]
        if si not in best_struct or score[k, si] > best_struct[si]["score"]:
            best_struct[si] = {"struct": op.STRUCTS[si], "score": float(score[k, si]), "a": M.names[M.pi[p]], "b": M.names[M.pj[p]] if M.pi[p] != M.pj[p] else "",
                               "i": int(M.pi[p]), "j": int(M.pj[p]), "hold": h, "mode": mode, "side": side,
                               **{f"n_{s}": int(n[p, g]) for g, s in enumerate(SEGN)}, **{f"sharpe_{s}": float(b["sharpe"][p, si, g]) for g, s in enumerate(SEGN)},
                               **{f"mean_{s}": float(b["tot"][p, si, en.C1X, g] / n[p, g]) for g, s in enumerate(SEGN)}}
sc, so, mo, st_i = np.concatenate(sc), np.concatenate(so), np.vstack(mo), np.concatenate(st_i)
U = {"eligible": int(len(sc)), "spearman_score_vs_oos_sharpe": float(ss.spearmanr(sc, so)[0]),
     "share_pos_oos_mean_by_cost": {str(c): float((mo[:, ci] > 0).mean()) for ci, c in enumerate(op.COSTS)},
     "share_pos_dev_val_and_oos": float(((sc > 0) & (so > 0)).mean()), "share_score_pos": float((sc > 0).mean()),
     "oos_sharpe_given_score_pos": float(so[sc > 0].mean()), "share_oos_pos_given_score_pos": float((so[sc > 0] > 0).mean())}
q = np.quantile(sc, np.linspace(0, 1, 11)); U["deciles"] = [{"decile": d + 1, "score_lo": float(q[d]), "score_hi": float(q[d + 1]),
     "oos_sharpe_mean": float(so[(sc >= q[d]) & (sc <= q[d + 1])].mean()), "share_oos_pos": float((so[(sc >= q[d]) & (sc <= q[d + 1])] > 0).mean())} for d in range(10)]
top = np.argsort(-sc)[:1000]; U["top1000_oos_sharpe_mean"] = float(so[top].mean()); U["top1000_share_oos_pos"] = float((so[top] > 0).mean())
top = np.argsort(-sc)[:100]; U["top100_oos_sharpe_mean"] = float(so[top].mean()); U["top100_share_oos_pos"] = float((so[top] > 0).mean())
U["by_struct"] = [{"struct": op.STRUCTS[si], "eligible": int((st_i == si).sum()), "share_score_pos": float((sc[st_i == si] > 0).mean()),
                   "share_oos_mean_pos_1x": float((mo[st_i == si, en.C1X] > 0).mean()), "share_oos_mean_pos_mid": float((mo[st_i == si, 0] > 0).mean()),
                   "median_oos_mean_1x": float(np.median(mo[st_i == si, en.C1X])), "best": best_struct[si]} for si in range(NSO)]
U["hindsight_best_oos_sharpe"] = float(so.max()); U["oos_sharpe_q"] = {str(k): float(np.quantile(so, k)) for k in (0.5, 0.9, 0.99, 0.999)}
out["universe"] = U

# ---------- B. finalists ----------
def tables(L, h, struct):
    T = {"periods": [], "years": [], "tickers": [], "sides": []}
    for g, nm in enumerate(SEGN):
        x = L[L.seg == g]; ms, nn = st.month_sums(L, M, g, "ror_1.0"); b = st.boot(ms, nn); yrs = (M.seg == g).sum() / 252
        row = {"period": nm, "n": len(x), "trades_per_year": len(x) / yrs, "win_rate_1x": float((x["pnl_1.0"] > 0).mean()), "avg_risk": float(x.risk.mean()),
               "sharpe": b["sharpe"], "sh_lo": b["sh_lo"], "sh_hi": b["sh_hi"], "mean_lo": b["lo"], "mean_hi": b["hi"], "p_pos": b["p_pos"],
               "shares_bp": float(1e4 * x.shares_ret.mean()), "shares_win": float((x.shares_ret > 0).mean()),
               "worst_trade_dollars": float(x["pnl_1.0"].min()), "best_trade_dollars": float(x["pnl_1.0"].max()), "median_ror": float(x["ror_1.0"].median())}
        for c in op.COSTS: row[f"ror_{c}"] = float(x[f"ror_{c}"].mean()); row[f"usd_{c}"] = float(x[f"pnl_{c}"].mean())
        T["periods"].append(row)
    x = L[L.seg == 2]
    for y, z in x.groupby(x.entry.dt.year): T["years"].append({"year": int(y), "n": len(z), "ror_1x": float(z["ror_1.0"].mean()), "usd_1x": float(z["pnl_1.0"].mean()), "sum_usd_1x": float(z["pnl_1.0"].sum()), "win": float((z["pnl_1.0"] > 0).mean())})
    for t, z in x.groupby("ticker"): T["tickers"].append({"ticker": t, "n": len(z), "ror_1x": float(z["ror_1.0"].mean()), "usd_1x": float(z["pnl_1.0"].mean()), "win": float((z["pnl_1.0"] > 0).mean())})
    for s, z in x.groupby("side"): T["sides"].append({"side": s, "n": len(z), "ror_1x": float(z["ror_1.0"].mean()), "usd_1x": float(z["pnl_1.0"].mean())})
    return T

w = sel["winner"]; Lw = en.ledger(M, w["i"], w["j"], w["hold"], w["mode"], w["side"], w["struct"]); Lw.to_csv(os.path.join(RES, "ledger_winner.csv"), index=False)
members = []
for k, m in enumerate(sel["top10"]):
    L = en.ledger(M, m["i"], m["j"], m["hold"], m["mode"], m["side"], m["struct"]); L["member"] = k; members.append(L)
Le = pd.concat(members, ignore_index=True); Le.to_csv(os.path.join(RES, "ledger_ensemble.csv"), index=False)
msw, nnw = st.month_sums(Lw, M, 2, "ror_1.0"); mse, nne = st.month_sums(Le, M, 2, "ror_1.0")
p1, p2 = st.boot(msw, nnw)["p_pos"], st.boot(mse, nne)["p_pos"]
ps = sorted([("H1", p1), ("H2", p2)], key=lambda x: x[1]); holm = {ps[0][0]: min(1, 2 * ps[0][1]), ps[1][0]: min(1, max(2 * ps[0][1], ps[1][1]))}
gw, bw, plw = st.gates(M, Lw, w["hold"], w["struct"], holm["H1"])
out["winner"] = {"config": w, "raw_p": p1, "holm_p": holm["H1"], "gates": {k: [bool(v[0]), v[1]] for k, v in gw.items()}, "label": st.label(gw, bw), "boot_oos": bw, "placebo": plw, "tables": tables(Lw, w["hold"], w["struct"])}
# ensemble: G1 G2 G3 G6 G7 G8 on pooled trades; G4 and G5 per member
x = Le[Le.seg == 2]; be = st.boot(mse, nne); ms2, _ = st.month_sums(Le, M, 2, "ror_2.0")
y = x.sort_values("ror_1.0", ascending=False); z = x.drop(y.groupby("ticker").head(5).index)
a_, c_ = x[x.entry < "2023-06-01"]["ror_1.0"].mean(), x[x.entry >= "2023-06-01"]["ror_1.0"].mean()
ge = {"G1": [bool(be["mean"] > 0 and holm["H2"] < 0.10), f"mean {100*be['mean']:+.2f}% of risk per trade, Holm p = {holm['H2']:.3f}"],
      "G2": [bool(ms2.sum() > 0), f"mean at 2x spread {100*ms2.sum()/nne.sum():+.2f}%"], "G3": [bool(be["sharpe"] > 0.5), f"monthly Sharpe {be['sharpe']:+.2f}"],
      "G6": [bool(len(x) >= 120), f"{len(x)} trades"], "G7": [bool(z["ror_1.0"].mean() > 0), f"mean without the 5 best trades per ETF {100*z['ror_1.0'].mean():+.2f}%"],
      "G8": [bool(a_ > 0 and c_ > 0), f"first half {100*a_:+.2f}%, second half {100*c_:+.2f}%"]}
mem = []
for k, m in enumerate(sel["top10"]):
    L = members[k]; g, b, pl = st.gates(M, L, m["hold"], m["struct"], 1.0)
    mem.append({**{kk: m[kk] for kk in ("a", "b", "hold", "mode", "side", "struct", "score", "n_dev", "n_val", "n_oos", "sharpe_dev", "sharpe_val", "sharpe_oos", "mean_dev", "mean_val", "mean_oos")},
                "oos_p": b["p_pos"], "oos_lo": b["lo"], "oos_hi": b["hi"], "placebo_pct": pl["pctile"], "placebo_mean": pl["placebo_mean"], "G5": bool(g["G5"][0]), "G2": bool(g["G2"][0]), "G7": bool(g["G7"][0]), "G8": bool(g["G8"][0]),
                "usd_1x_oos": float(L[L.seg == 2]["pnl_1.0"].mean()), "ror_mid_oos": float(L[L.seg == 2]["ror_0.0"].mean()), "ror_2x_oos": float(L[L.seg == 2]["ror_2.0"].mean()),
                "shares_bp_oos": float(1e4 * L[L.seg == 2].shares_ret.mean()), "win_oos": float((L[L.seg == 2]["pnl_1.0"] > 0).mean())})
lab = "PARTIAL (PROXY), Tier B: forward-test with real quotes" if all(v[0] for v in ge.values()) else ("NEGATIVE EXPECTANCY (PROXY)" if be["mean"] < 0 and be["p_neg"] < 0.10 else "NO EDGE DEMONSTRATED (PROXY)")
out["ensemble"] = {"raw_p": p2, "holm_p": holm["H2"], "gates": ge, "label": lab, "boot_oos": be, "members": mem, "tables": tables(Le, None, None)}
# best per structure: OOS bootstrap
ps_ = []
for bsx in [u["best"] for u in U["by_struct"]]:
    L = en.ledger(M, bsx["i"], bsx["j"], bsx["hold"], bsx["mode"], bsx["side"], bsx["struct"]); ms, nn = st.month_sums(L, M, 2, "ror_1.0"); b = st.boot(ms, nn)
    x = L[L.seg == 2]; ps_.append({**bsx, "oos_p": b["p_pos"], "oos_lo": b["lo"], "oos_hi": b["hi"], "usd_1x_oos": float(x["pnl_1.0"].mean()), "ror_mid_oos": float(x["ror_0.0"].mean()), "win_oos": float((x["pnl_1.0"] > 0).mean())})
out["per_struct"] = ps_
json.dump(out, open(os.path.join(RES, "final.json"), "w"), indent=1, default=float)
print(json.dumps({k: out[k] for k in ("universe",)}, indent=0, default=float)[:6000])
print(json.dumps({"winner": {k: out["winner"][k] for k in ("raw_p", "holm_p", "gates", "label", "boot_oos", "placebo")}, "ens": {k: out["ensemble"][k] for k in ("raw_p", "holm_p", "gates", "label", "boot_oos")}}, indent=0, default=float))
