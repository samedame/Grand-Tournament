"""Tournament engine. Signal sets = every unordered pair (i <= j; i == j is a single) of indicator states.
Entry at the close of the signal day, time exit at the close h sessions later, one position per ETF at a time."""
import numpy as np, pandas as pd
import prep, ind, options as op

MODES = ("STATE", "FRESH")       # enter whenever the agreement is on / only on the first day it is on
SIDES = ("L", "S", "LS")         # take bullish agreements only / bearish only / both
NS = len(op.STRUCTS) + 1         # + shares reference (column NS-1)
C1X = op.COSTS.index(1.0)


def pair_index(K):
    i, j = np.triu_indices(K); return i.astype(np.int32), j.astype(np.int32)


def scan(sigL, sigS, h, t0, valid):
    """sigL/sigS: (T, P) bool. Returns entry matrices (T, P) bool under the one-position rule."""
    T, P = sigL.shape; EL = np.zeros((T, P), bool); ES = np.zeros((T, P), bool); busy = np.zeros(P, np.int16)
    for t in range(t0, T - h):
        if valid[t]:
            free = busy == 0
            eL = sigL[t] & free; eS = sigS[t] & free & ~eL
            EL[t] = eL; ES[t] = eS
            busy[eL | eS] = h
        np.subtract(busy, 1, out=busy, where=busy > 0)
    return EL, ES


def fresh(x):
    y = x.copy(); y[1:] &= ~x[:-1]; y[0] = False; return y


class Market:
    def __init__(self, tickers=None, with_options=True):
        self.tickers = tickers or prep.CORE
        self.D = prep.load(self.tickers)
        self.dates = pd.DatetimeIndex(self.D[self.tickers[0]]["dates"]); self.T = len(self.dates)
        self.cal = ind.calendar(self.dates)
        self.t0 = int(self.dates.searchsorted(pd.Timestamp(prep.OPT_START)))
        self.seg = segments(self.dates)
        self.month = np.array(self.dates.year * 12 + self.dates.month); self.month = self.month - self.month[self.t0]
        self.nm = int(self.month[-1]) + 1
        self.mseg = np.array([self.seg[np.where(self.month == m)[0][0]] for m in range(self.nm)])
        self.states = {}; self.opt = {}; self.W = {}
        for t in self.tickers:
            names, kinds, fams, L, S = ind.states(self.D[t], self.cal)
            self.names, self.kinds, self.fams = names, np.array(kinds), fams
            self.states[t] = (L, S)
            if with_options:
                self.opt[t] = op.build(self.D[t], t)
                for h in op.HOLDS:
                    o = self.opt[t][h]; w = np.zeros((2, len(op.COSTS), self.T, NS), np.float32)
                    for side in (0, 1):
                        for ci in range(len(op.COSTS)):
                            w[side, ci, :, :NS - 1] = np.nan_to_num(o["ror"][side, :, ci, :].T)
                            w[side, ci, :, NS - 1] = np.nan_to_num(o["stock"]) * (1 if side == 0 else -1)
                    self.W[t, h] = w
        self.K = len(self.names); self.pi, self.pj = pair_index(self.K); self.P = len(self.pi)
        isF = self.kinds == "F"; self.ff = isF[self.pi] & isF[self.pj]      # neutral-filter-only sets: no direction

    def pair_signals(self, t, lo, hi):
        L, S = self.states[t]; i, j = self.pi[lo:hi], self.pj[lo:hi]
        sl = L[:, i] & L[:, j]; ss = S[:, i] & S[:, j]; ss[:, self.ff[lo:hi]] = False
        return sl, ss

    def entries(self, t, h, mode, side, sl, ss):
        if mode == "FRESH": sl, ss = fresh(sl), fresh(ss)
        if side == "L": ss = np.zeros_like(ss)
        elif side == "S": sl = np.zeros_like(sl)
        return scan(sl, ss, h, self.t0, self.opt[t][h]["valid"])


def segments(dates):
    """0 = development, 1 = validation, 2 = out of sample, -1 = before the option window."""
    d = pd.DatetimeIndex(dates); seg = np.full(len(d), -1)
    seg[d >= prep.OPT_START] = 0; seg[d >= prep.SEG_EDGES[0]] = 1; seg[d >= prep.SEG_EDGES[1]] = 2
    return seg


def run_block(M, h, mode, side, chunk=3000, counts_only=False):
    """All signal sets for one (hold, mode, side). Returns dict of arrays:
    n[P, 3]; tot[P, NS, n_costs, 3] (sum of return on risk); sharpe[P, NS, 3] (monthly, 1x cost)."""
    P = M.P; n = np.zeros((P, 3), np.float32); tot = np.zeros((P, NS, len(op.COSTS), 3), np.float32)
    msum = None if counts_only else np.zeros((M.nm, P, NS), np.float32)
    mb = [np.where(M.month == m)[0] for m in range(M.nm)]
    for lo in range(0, P, chunk):
        hi = min(P, lo + chunk)
        for t in M.tickers:
            sl, ss = M.pair_signals(t, lo, hi)
            EL, ES = M.entries(t, h, mode, side, sl, ss)
            for g in range(3):
                rows = M.seg == g
                n[lo:hi, g] += EL[rows].sum(0) + ES[rows].sum(0)
            if counts_only: continue
            ELf, ESf = EL.astype(np.float32), ES.astype(np.float32); w = M.W[t, h]
            for g in range(3):
                rows = M.seg == g
                for ci in range(len(op.COSTS)):
                    tot[lo:hi, :, ci, g] += ELf[rows].T @ w[0, ci, rows] + ESf[rows].T @ w[1, ci, rows]
            for m in range(M.nm):
                r = mb[m]; msum[m, lo:hi] += ELf[r].T @ w[0, C1X, r] + ESf[r].T @ w[1, C1X, r]
    out = {"n": n, "tot": tot}
    if not counts_only:
        sh = np.zeros((P, NS, 3), np.float32)
        for g in range(3):
            x = msum[M.mseg == g]; mu = x.mean(0); sd = x.std(0, ddof=1)
            with np.errstate(divide="ignore", invalid="ignore"): sh[:, :, g] = np.where(sd > 0, mu / sd * np.sqrt(12.0), 0.0)
        out["sharpe"] = sh
    return out


def ledger(M, i, j, h, mode, side, struct):
    """Trade list for one configuration (used for finalists): DataFrame with one row per trade."""
    p = int(np.where((M.pi == min(i, j)) & (M.pj == max(i, j)))[0][0]); rows = []
    si = op.STRUCTS.index(struct) if struct != "SHARES" else None
    for t in M.tickers:
        sl, ss = M.pair_signals(t, p, p + 1); EL, ES = M.entries(t, h, mode, side, sl, ss); o = M.opt[t][h]
        for sd_, E in ((0, EL[:, 0]), (1, ES[:, 0])):
            for k in np.where(E)[0]:
                rec = {"ticker": t, "entry": M.dates[k], "exit": M.dates[k + h], "side": "bull" if sd_ == 0 else "bear", "seg": int(M.seg[k]),
                       "month": int(M.month[k]), "S0": M.D[t]["close"][k], "S1": M.D[t]["close"][k + h],
                       "shares_ret": (M.D[t]["close"][k + h] / M.D[t]["close"][k] - 1) * (1 if sd_ == 0 else -1)}
                if si is not None:
                    rec["risk"] = o["risk"][sd_, si, k]
                    for ci, c in enumerate(op.COSTS):
                        rec[f"pnl_{c}"] = o["pnl"][sd_, si, ci, k]; rec[f"ror_{c}"] = o["ror"][sd_, si, ci, k]
                rows.append(rec)
    return pd.DataFrame(rows).sort_values(["entry", "ticker"]).reset_index(drop=True)
