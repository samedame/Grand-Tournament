"""Option layer (PROXY: Black-Scholes on index-vol-derived IV with a linear skew). No market quotes.
build(a, ticker, dates) -> dict hold -> {"ror": [side, struct, cost, T], "pnl": same ($/structure), "risk": [side, struct, T], "valid": [T]}
side 0 = bullish version, 1 = bearish version (neutral structures are identical on both sides)."""
import numpy as np, pandas as pd
from scipy.special import ndtr, ndtri
import prep

HOLDS = (1, 2, 3, 5, 10)
DTE_TARGET = {1: 14, 2: 14, 3: 14, 5: 21, 10: 35}      # minimum calendar days to expiry at entry
COSTS = (0.0, 0.25, 0.5, 1.0, 2.0)                      # multiples of the house spread; 0.0 = mid, no commission
HOUSE = 3.88e-4                                          # full quoted spread per leg as a fraction of the underlying price (0.65-delta calibration)
COMM = 0.65                                              # dollars per contract per side (all cost levels except mid)
ATM_K, SKEW = 0.8565, -0.240                             # IV(K) = index_vol * clip(ATM_K + SKEW * m, 0.60, 1.45), m = ln(K/S) / (atm_iv * sqrt(T))
STRUCTS = ["LONG80", "LONG65", "LONG50", "LONG30", "DEBIT_V", "CREDIT_V", "STRADDLE", "CONDOR"]
NEUTRAL = {"STRADDLE", "CONDOR"}
# legs for the bullish version: (cp, |delta| target, qty); bearish version flips cp
LEGS = {"LONG80": [(1, .80, 1)], "LONG65": [(1, .65, 1)], "LONG50": [(1, .50, 1)], "LONG30": [(1, .30, 1)],
        "DEBIT_V": [(1, .60, 1), (1, .30, -1)], "CREDIT_V": [(-1, .30, -1), (-1, .15, 1)],
        "STRADDLE": [(1, None, 1), (-1, None, 1)],
        "CONDOR": [(-1, .20, -1), (-1, .10, 1), (1, .20, -1), (1, .10, 1)]}


def iv_at(K, S, idx, T):
    atm = ATM_K * idx / 100.0
    with np.errstate(divide="ignore", invalid="ignore"):
        m = np.where(T > 0, np.log(K / S) / (atm * np.sqrt(np.maximum(T, 1e-9))), 0.0)
    return idx / 100.0 * np.clip(ATM_K + SKEW * m, 0.60, 1.45)


def bs(S, K, T, sig, r, q, cp):
    """Price and delta; T == 0 gives intrinsic value."""
    Tp = np.maximum(T, 1e-9); sq = sig * np.sqrt(Tp)
    d1 = (np.log(S / K) + (r - q + 0.5 * sig * sig) * Tp) / sq; d2 = d1 - sq
    px = cp * (S * np.exp(-q * Tp) * ndtr(cp * d1) - K * np.exp(-r * Tp) * ndtr(cp * d2))
    dl = cp * np.exp(-q * Tp) * ndtr(cp * d1)
    intr = np.maximum(cp * (S - K), 0.0)
    return np.where(T > 0, px, intr), np.where(T > 0, dl, np.where(intr > 0, cp * 1.0, 0.0))


def expiries(dates):
    """Listed expiry for every (entry date, DTE target): Fridays (previous session if the Friday is a holiday);
    only third Fridays before prep.WEEKLY_START."""
    d = pd.DatetimeIndex(dates); tset = set(d)
    fr = pd.date_range(d[0], d[-1] + pd.Timedelta(days=90), freq="W-FRI")
    monthly = np.array([15 <= x.day <= 21 for x in fr])
    ok = monthly | (fr >= pd.Timestamp(prep.WEEKLY_START))
    fr = fr[ok]
    adj = []
    for x in fr:
        if x <= d[-1] and x not in tset:
            k = d.searchsorted(x) - 1; adj.append(d[k])
        else: adj.append(x)
    ex = pd.DatetimeIndex(adj)
    out = {}
    for tgt in sorted(set(DTE_TARGET.values())):
        j = ex.searchsorted(d + pd.Timedelta(days=tgt))
        out[tgt] = ex[j]
    return out


def tyears(d0, d1):
    return np.busday_count(pd.DatetimeIndex(d0).values.astype("datetime64[D]"), pd.DatetimeIndex(d1).values.astype("datetime64[D]")) / 252.0


def pick_strike(S, idx, T, r, q, cp, tgt):
    """$1-grid strike whose |delta| is closest to tgt."""
    d1 = cp * ndtri(np.clip(tgt * np.exp(q * T), 1e-6, 1 - 1e-6))
    sig = ATM_K * idx / 100.0; K = S.copy()
    for _ in range(4):
        K = S * np.exp(-d1 * sig * np.sqrt(T) + (r - q + 0.5 * sig * sig) * T); sig = iv_at(K, S, idx, T)
    base = np.round(K); best = base.copy(); err = np.full(len(S), np.inf)
    for off in range(-3, 4):
        k = np.maximum(base + off, 1.0)
        _, dl = bs(S, k, T, iv_at(k, S, idx, T), r, q, cp)
        e = np.abs(np.abs(dl) - tgt); upd = e < err; best[upd] = k[upd]; err[upd] = e[upd]
    return best


def build(a, ticker):
    dates = pd.DatetimeIndex(a["dates"]); n = len(dates)
    S, idx, r = a["close"], a["iv_close"], a["rate"]; q = prep.DIVY[ticker]; sm = prep.SPREAD_MULT[ticker]
    ex = expiries(dates); first = dates.searchsorted(pd.Timestamp(prep.OPT_START))
    out = {}
    for h in HOLDS:
        tgt = DTE_TARGET[h]; e = ex[tgt]
        t0 = np.arange(n); t1 = np.minimum(t0 + h, n - 1)
        valid = (t0 >= first) & (t0 + h <= n - 1) & ~np.isnan(idx) & ~np.isnan(idx[t1]) & ~np.isnan(r)
        T0 = tyears(dates, e); T1 = tyears(dates[t1], e)
        assert (T1[valid] >= 0).all() and (T0[valid] > 0).all()
        S0, S1, i0, i1, r0, r1 = S, S[t1], np.nan_to_num(idx, nan=20.0), np.nan_to_num(idx[t1], nan=20.0), np.nan_to_num(r), np.nan_to_num(r[t1])
        ror = np.full((2, len(STRUCTS), len(COSTS), n), np.nan); pnl = ror.copy(); risk = np.full((2, len(STRUCTS), n), np.nan)
        for side in (0, 1):
            flip = 1 if side == 0 else -1
            for si, name in enumerate(STRUCTS):
                if side == 1 and name in NEUTRAL:
                    ror[1, si] = ror[0, si]; pnl[1, si] = pnl[0, si]; risk[1, si] = risk[0, si]; continue
                v0 = np.zeros(n); v1 = np.zeros(n); cost = np.zeros((len(COSTS), n)); Ks = []
                for cp, tg, qty in LEGS[name]:
                    cp = cp * flip
                    K = np.round(S0) if tg is None else pick_strike(S0, i0, T0, r0, q, cp, tg)
                    Ks.append((cp, qty, tg, K))
                # keep the legs of a vertical / condor wing at least $1 apart (long leg further out of the money)
                for j in range(1, len(Ks)):
                    cp, qty, tg, K = Ks[j]; cpp, qp, tgp, Kp = Ks[j - 1]
                    if cp == cpp and tg is not None:
                        Ks[j] = (cp, qty, tg, np.where(cp > 0, np.maximum(K, Kp + 1), np.minimum(K, Kp - 1)))
                for cp, qty, tg, K in Ks:
                    p0, d0 = bs(S0, K, T0, iv_at(K, S0, i0, T0), r0, q, cp)
                    p1, _ = bs(S1, K, T1, iv_at(K, S1, i1, T1), r1, q, cp)
                    v0 += qty * p0; v1 += qty * p1
                    sp = HOUSE * S0 * sm * np.clip(np.abs(d0) / 0.65, 0.25, 1.25)
                    for ci, c in enumerate(COSTS):
                        if c > 0: cost[ci] += 100 * np.maximum(0.01, c * sp) + 2 * COMM
                if name in ("CREDIT_V", "CONDOR"):
                    w = np.zeros(n)
                    for j in range(1, len(Ks), 2): w = np.maximum(w, np.abs(Ks[j][3] - Ks[j - 1][3]))
                    rk = (w + v0) * 100          # v0 is negative (credit received)
                else:
                    rk = v0 * 100
                good = valid & (rk > 5.0)
                rk = np.where(good, rk, np.nan); risk[side, si] = rk
                for ci in range(len(COSTS)):
                    p = (v1 - v0) * 100 - cost[ci]
                    pnl[side, si, ci] = np.where(good, p, np.nan); ror[side, si, ci] = p / rk
        allok = valid & ~np.isnan(ror[:, :, 0, :]).any(axis=(0, 1))
        stock = np.where(allok, S1 / S0 - 1, np.nan)
        out[h] = {"ror": ror, "pnl": pnl, "risk": risk, "valid": allok, "stock": stock, "expiry": e, "T0": T0}
    return out
