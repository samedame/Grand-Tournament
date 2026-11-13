"""run.py counts | full | select"""
import sys, os, json, time, itertools, numpy as np, pandas as pd
import prep, options as op, engine as en

RES = os.path.join(prep.ROOT, "results"); BLK = os.path.join(RES, "blocks"); os.makedirs(BLK, exist_ok=True)
MIN_N = (100, 100, 120)            # trades needed in development, validation, out of sample (3 ETFs pooled)
BLOCKS = list(itertools.product(op.HOLDS, en.MODES, en.SIDES))


def baselines(M):
    """Always-on reference: roll the structure every h sessions, bullish (L) or bearish (S) version."""
    rows = []
    for h in op.HOLDS:
        for side in ("L", "S"):
            ms = np.zeros((M.nm, en.NS)); n = np.zeros(3); tot = np.zeros((en.NS, len(op.COSTS), 3))
            for t in M.tickers:
                one = np.ones((M.T, 1), bool); zero = np.zeros((M.T, 1), bool)
                EL, ES = en.scan(one if side == "L" else zero, zero if side == "L" else one, h, M.t0, M.opt[t][h]["valid"])
                E = (EL if side == "L" else ES)[:, 0]; w = M.W[t, h][0 if side == "L" else 1]
                for g in range(3):
                    r = E & (M.seg == g); n[g] += r.sum()
                    for ci in range(len(op.COSTS)): tot[:, ci, g] += w[ci, r].sum(0)
                for m in range(M.nm):
                    r = E & (M.month == m); ms[m] += w[en.C1X, r].sum(0)
            for si in range(en.NS):
                rec = {"hold": h, "side": side, "struct": (op.STRUCTS + ["SHARES"])[si]}
                for g, nm in enumerate(("dev", "val", "oos")):
                    x = ms[M.mseg == g, si]; rec[f"n_{nm}"] = int(n[g]); rec[f"mean_{nm}"] = tot[si, en.C1X, g] / n[g]
                    rec[f"sharpe_{nm}"] = x.mean() / x.std(ddof=1) * np.sqrt(12)
                    rec[f"mean_mid_{nm}"] = tot[si, 0, g] / n[g]; rec[f"mean_2x_{nm}"] = tot[si, 4, g] / n[g]
                rows.append(rec)
    return pd.DataFrame(rows)


def load_blocks():
    out = {}
    for h, mode, side in BLOCKS:
        z = np.load(os.path.join(BLK, f"h{h}_{mode}_{side}.npz")); out[h, mode, side] = {k: z[k] for k in z.files}
    return out


def select(M, blocks):
    NSO = len(op.STRUCTS); recs = []; summary = {"configs_total": 0, "eligible": 0}
    isF = M.kinds == "F"
    for (h, mode, side), b in blocks.items():
        n = b["n"]; elig = (n[:, 0] >= MIN_N[0]) & (n[:, 1] >= MIN_N[1]) & (n[:, 2] >= MIN_N[2])
        sh = b["sharpe"][:, :NSO, :]; score = np.minimum(sh[:, :, 0], sh[:, :, 1])
        summary["configs_total"] += int((n.sum(1) > 0).sum()) * NSO; summary["eligible"] += int(elig.sum()) * NSO
        score = np.where(elig[:, None], score, -np.inf)
        flat = np.argsort(-score, axis=None)[:3000]
        for f in flat:
            p, si = np.unravel_index(f, score.shape)
            if not np.isfinite(score[p, si]): break
            recs.append((float(score[p, si]), int(M.pi[p] != M.pj[p]), h, mode, side, int(p), int(si)))
    recs.sort(key=lambda r: (-r[0], r[1], r[2], r[3], r[4], r[5], r[6]))
    rows = []
    for sc, ispair, h, mode, side, p, si in recs[:3000]:
        b = blocks[h, mode, side]; i, j = int(M.pi[p]), int(M.pj[p])
        row = {"score": sc, "a": M.names[i], "b": M.names[j] if i != j else "", "fam_a": M.fams[i], "fam_b": M.fams[j], "hold": h, "mode": mode, "side": side,
               "struct": op.STRUCTS[si], "i": i, "j": j}
        for g, nm in enumerate(("dev", "val", "oos")):
            row[f"n_{nm}"] = int(b["n"][p, g]); row[f"sharpe_{nm}"] = float(b["sharpe"][p, si, g])
            row[f"mean_{nm}"] = float(b["tot"][p, si, en.C1X, g] / max(b["n"][p, g], 1))
        rows.append(row)
    lb = pd.DataFrame(rows)
    winner = lb.iloc[0].to_dict()
    top, seen = [], set()
    for _, r in lb.iterrows():
        key = (frozenset((r.fam_a, r.fam_b)), r.struct)
        if key in seen: continue
        seen.add(key); top.append(r.to_dict())
        if len(top) == 10: break
    per_struct = [lb[lb.struct == s].iloc[0].to_dict() for s in op.STRUCTS if (lb.struct == s).any()]
    return lb, {"winner": winner, "top10": top, "per_struct": per_struct, "summary": summary}


if __name__ == "__main__":
    cmd = sys.argv[1]; t0 = time.time(); M = en.Market()
    if cmd == "counts":
        tot = 0; el = 0
        for h, mode, side in BLOCKS:
            n = en.run_block(M, h, mode, side, counts_only=True)["n"]
            np.save(os.path.join(RES, f"counts_h{h}_{mode}_{side}.npy"), n)
            e = (n[:, 0] >= MIN_N[0]) & (n[:, 1] >= MIN_N[1]) & (n[:, 2] >= MIN_N[2]); tot += int((n.sum(1) > 0).sum()); el += int(e.sum())
            print(h, mode, side, "sets with trades", int((n.sum(1) > 0).sum()), "eligible", int(e.sum()), f"{time.time()-t0:.0f}s", flush=True)
        print("signal-set x hold x mode x side with trades:", tot, "eligible:", el, "x", len(op.STRUCTS), "structures =", el * len(op.STRUCTS))
    elif cmd == "full":
        for h, mode, side in BLOCKS:
            b = en.run_block(M, h, mode, side); np.savez_compressed(os.path.join(BLK, f"h{h}_{mode}_{side}.npz"), **b)
            print("block", h, mode, side, f"{time.time()-t0:.0f}s", flush=True)
        baselines(M).to_csv(os.path.join(RES, "baselines.csv"), index=False)
    elif cmd == "select":
        lb, sel = select(M, load_blocks()); lb.to_csv(os.path.join(RES, "leaderboard_top3000.csv"), index=False)
        json.dump(sel, open(os.path.join(RES, "select.json"), "w"), indent=1, default=str)
        print(json.dumps(sel["summary"]))
