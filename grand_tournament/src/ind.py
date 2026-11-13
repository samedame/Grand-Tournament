"""Daily indicator states. Every state at day t uses data through the close of day t only.
states(a, cal) -> (names, kinds, fams, L, S): L/S are (T x K) bool arrays (bullish / bearish reading).
kind: T trend/momentum, R reversal, F neutral filter (L == S), C calendar (long only)."""
import numpy as np, pandas as pd

_s = lambda x: pd.Series(x)
def sma(x, n): return _s(x).rolling(n).mean().to_numpy(copy=True)
def sd(x, n): return _s(x).rolling(n).std(ddof=0).to_numpy(copy=True)
def ema(x, n): return _s(x).ewm(span=n, adjust=False, min_periods=n).mean().to_numpy(copy=True)
def rma(x, n): return _s(x).ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean().to_numpy(copy=True)
def hh(x, n): return _s(x).rolling(n).max().to_numpy(copy=True)
def ll(x, n): return _s(x).rolling(n).min().to_numpy(copy=True)
def rsum(x, n): return _s(x).rolling(n).sum().to_numpy(copy=True)
def lag(x, k=1): return _s(x).shift(k).to_numpy(copy=True)
def wma(x, n):
    w = np.arange(1, n + 1, dtype=float); w /= w.sum()
    out = np.full(len(x), np.nan); out[n - 1:] = np.convolve(x, w[::-1], "valid"); return out
def slope(x, n):
    i = np.arange(n, dtype=float); k = (i - i.mean()) / ((i - i.mean()) ** 2).sum()
    out = np.full(len(x), np.nan); out[n - 1:] = np.convolve(x, k[::-1], "valid"); return out
def rsi(c, n):
    d = np.diff(c, prepend=c[0]); up = np.maximum(d, 0); dn = np.maximum(-d, 0)
    au = rma(up, n); ad = rma(dn, n)
    with np.errstate(divide="ignore", invalid="ignore"):
        r = 100 - 100 / (1 + au / ad)
    r[(ad == 0) & (au > 0)] = 100; r[(ad == 0) & (au == 0)] = 50
    return r
def true_range(h, l, c):
    pc = lag(c); return np.nanmax(np.vstack([h - l, np.abs(h - pc), np.abs(l - pc)]), axis=0)
def pct_rank(x, n):  # share of the previous n values that are below the current value
    return _s(x).rolling(n + 1).apply(lambda w: (w[:-1] < w[-1]).mean(), raw=True).to_numpy(copy=True)
def streak(c):
    out = np.zeros(len(c)); d = np.diff(c, prepend=c[0])
    for i in range(1, len(c)):
        out[i] = (out[i - 1] + 1 if out[i - 1] > 0 else 1) if d[i] > 0 else ((out[i - 1] - 1 if out[i - 1] < 0 else -1) if d[i] < 0 else 0)
    return out
def supertrend(h, l, c, n, m):
    atr = rma(true_range(h, l, c), n); mid = (h + l) / 2; ub = mid + m * atr; lb = mid - m * atr
    d = np.zeros(len(c)); fu = np.full(len(c), np.nan); fl = np.full(len(c), np.nan)
    for i in range(len(c)):
        if np.isnan(atr[i]): continue
        if np.isnan(fu[i - 1]) if i else True:
            fu[i], fl[i], d[i] = ub[i], lb[i], 1; continue
        fu[i] = ub[i] if (ub[i] < fu[i - 1] or c[i - 1] > fu[i - 1]) else fu[i - 1]
        fl[i] = lb[i] if (lb[i] > fl[i - 1] or c[i - 1] < fl[i - 1]) else fl[i - 1]
        d[i] = 1 if c[i] > fu[i - 1] else (-1 if c[i] < fl[i - 1] else d[i - 1])
    return d
def psar(h, l, af0=0.02, afm=0.2):
    n = len(h); d = np.zeros(n); sar = l[0]; ep = h[0]; af = af0; up = True
    for i in range(1, n):
        sar = sar + af * (ep - sar)
        if up:
            sar = min(sar, l[i - 1], l[i - 2] if i > 1 else l[i - 1])
            if l[i] < sar: up, sar, ep, af = False, ep, l[i], af0
            elif h[i] > ep: ep = h[i]; af = min(af + af0, afm)
        else:
            sar = max(sar, h[i - 1], h[i - 2] if i > 1 else h[i - 1])
            if h[i] > sar: up, sar, ep, af = True, ep, h[i], af0
            elif l[i] < ep: ep = l[i]; af = min(af + af0, afm)
        d[i] = 1 if up else -1
    return d
def kama(c, n=10, f=2, s=30):
    out = np.full(len(c), np.nan); fs, ss = 2 / (f + 1), 2 / (s + 1)
    vol = rsum(np.abs(np.diff(c, prepend=c[0])), n)
    for i in range(n, len(c)):
        er = abs(c[i] - c[i - n]) / vol[i] if vol[i] > 0 else 0
        sc = (er * (fs - ss) + ss) ** 2
        out[i] = c[i] if np.isnan(out[i - 1]) else out[i - 1] + sc * (c[i] - out[i - 1])
    return out
def flipstate(up_evt, dn_evt):
    d = np.zeros(len(up_evt)); cur = 0
    for i in range(len(d)):
        if up_evt[i]: cur = 1
        elif dn_evt[i]: cur = -1
        d[i] = cur
    return d
def fisher(h, l, n=10):
    m = (h + l) / 2; mx = hh(m, n); mn = ll(m, n); v = 0.0; f = np.full(len(m), np.nan); pf = 0.0
    for i in range(len(m)):
        if np.isnan(mx[i]) or mx[i] == mn[i]: continue
        v = 0.33 * 2 * ((m[i] - mn[i]) / (mx[i] - mn[i]) - 0.5) + 0.67 * v
        v = max(min(v, 0.999), -0.999); pf = 0.5 * np.log((1 + v) / (1 - v)) + 0.5 * pf; f[i] = pf
    return f


def calendar(all_dates):
    """Exchange-calendar features from the full list of trading dates (known in advance)."""
    d = pd.DatetimeIndex(all_dates)
    ext = pd.bdate_range(d[-1] + pd.Timedelta(days=1), d[-1] + pd.Timedelta(days=45))
    full = d.append(ext); ym = full.year * 12 + full.month
    dom = pd.Series(1, index=range(len(full))).groupby(ym).cumsum().to_numpy(copy=True)           # trading day of month, 1-based
    rev = pd.Series(1, index=range(len(full)))[::-1].groupby(ym[::-1]).cumsum()[::-1].to_numpy(copy=True)  # 1 = last trading day
    tom = (rev == 1) | (dom <= 3)
    third_fri = np.array([(x.weekday() == 4) and (15 <= x.day <= 21) for x in full])
    wk = full.isocalendar().week.to_numpy(copy=True).astype(int) + full.isocalendar().year.to_numpy(copy=True).astype(int) * 100
    opex_weeks = set(wk[third_fri]); opexwk = np.array([w in opex_weeks for w in wk])
    n = len(d); nxt = np.arange(1, n + 1)
    gap = np.array([np.busday_count(full[i].date(), full[i + 1].date()) for i in range(n)])
    first = dom == 1
    return {"first_next": first[nxt], "dow": d.weekday.to_numpy(copy=True), "tom_next": tom[nxt], "opex_next": opexwk[nxt], "prehol": gap > 1,
            "novapr": np.isin(d.month.to_numpy(copy=True), [11, 12, 1, 2, 3, 4]), "dom": dom[:n], "dates": d}


def states(a, cal):
    o, h, l, c, v = a["open"], a["high"], a["low"], a["close"], a["volume"]
    T = len(c); vix = a["vix"]; vix3m = a["vix3m"]
    pc = lag(c); ret = c / pc - 1; tr = true_range(h, l, c); atr14 = rma(tr, 14); rng = h - l
    out = []  # (name, kind, family, L, S)
    def add(name, kind, fam, L, S=None):
        L = np.nan_to_num(np.asarray(L, dtype=float)) > 0
        S = L.copy() if S is None else (np.nan_to_num(np.asarray(S, dtype=float)) > 0)
        out.append((name, kind, fam, L, S))
    with np.errstate(divide="ignore", invalid="ignore"):
        # ---------------- trend / momentum ----------------
        for n in (5, 10, 20, 50, 100, 200):
            m = sma(c, n); add(f"PX_SMA{n}", "T", "MA", c > m, c < m)
        for f, s_ in ((5, 20), (10, 50), (20, 100), (50, 200)):
            add(f"SMAX_{f}_{s_}", "T", "MA", sma(c, f) > sma(c, s_), sma(c, f) < sma(c, s_))
        for f, s_ in ((9, 21), (12, 26), (20, 50), (50, 200)):
            add(f"EMAX_{f}_{s_}", "T", "MA", ema(c, f) > ema(c, s_), ema(c, f) < ema(c, s_))
        macd = ema(c, 12) - ema(c, 26); sig = ema(np.nan_to_num(macd), 9); sig[:34] = np.nan; hist = macd - sig
        add("MACD_SIG", "T", "MACD", macd > sig, macd < sig); add("MACD_ZERO", "T", "MACD", macd > 0, macd < 0)
        add("MACD_HISTUP", "T", "MACD", hist > lag(hist), hist < lag(hist))
        for n in (5, 10, 21, 63, 126, 252):
            r = c / lag(c, n) - 1; add(f"ROC{n}", "T", "ROC", r > 0, r < 0)
        for n in (10, 20, 55, 100):
            up = c > lag(hh(h, n)); dn = c < lag(ll(l, n)); add(f"DON{n}", "T", "DONCH", up, dn)
            if n in (20, 55):
                st = flipstate(np.nan_to_num(up) > 0, np.nan_to_num(dn) > 0); add(f"DONSTATE{n}", "T", "DONCH", st > 0, st < 0)
        upm = h - lag(h); dnm = lag(l) - l
        pdm = np.where((upm > dnm) & (upm > 0), upm, 0.0); mdm = np.where((dnm > upm) & (dnm > 0), dnm, 0.0)
        pdi = 100 * rma(pdm, 14) / atr14; mdi = 100 * rma(mdm, 14) / atr14
        adx = rma(np.nan_to_num(100 * np.abs(pdi - mdi) / (pdi + mdi)), 14); adx[:28] = np.nan
        add("DMI_20", "T", "DMI", (pdi > mdi) & (adx >= 20), (mdi > pdi) & (adx >= 20))
        add("DMI_25", "T", "DMI", (pdi > mdi) & (adx >= 25), (mdi > pdi) & (adx >= 25))
        add("DMI_RISE", "T", "DMI", (pdi > mdi) & (adx > lag(adx)), (mdi > pdi) & (adx > lag(adx)))
        for n, m in ((10, 3), (7, 2), (14, 4)):
            st = supertrend(h, l, c, n, m); add(f"ST_{n}_{m}", "T", "SUPERT", st > 0, st < 0)
        ps = psar(h, l); add("PSAR", "T", "PSAR", ps > 0, ps < 0)
        ten = (hh(h, 9) + ll(l, 9)) / 2; kij = (hh(h, 26) + ll(l, 26)) / 2
        spa = lag((ten + kij) / 2, 26); spb = lag((hh(h, 52) + ll(l, 52)) / 2, 26)
        add("ICHI_CLOUD", "T", "ICHI", c > np.maximum(spa, spb), c < np.minimum(spa, spb)); add("ICHI_TK", "T", "ICHI", ten > kij, ten < kij)
        aup = 100 * (25 - (25 - _s(h).rolling(26).apply(np.argmax, raw=True).to_numpy(copy=True))) / 25
        adn = 100 * (25 - (25 - _s(l).rolling(26).apply(np.argmin, raw=True).to_numpy(copy=True))) / 25
        add("AROON", "T", "AROON", aup > adn, adn > aup); add("AROON_70", "T", "AROON", (aup > 70) & (adn < 30), (adn > 70) & (aup < 30))
        e20 = ema(c, 20); atr10 = rma(tr, 10)
        add("KELT_B", "T", "KELT", c > e20 + 2 * atr10, c < e20 - 2 * atr10)
        m20 = sma(c, 20); s20 = sd(c, 20)
        add("BB_B", "T", "BB", c > m20 + 2 * s20, c < m20 - 2 * s20)
        hac = (o + h + l + c) / 4; hao = np.empty(T); hao[0] = (o[0] + c[0]) / 2
        for i in range(1, T): hao[i] = (hao[i - 1] + hac[i - 1]) / 2
        g = (hac > hao).astype(float); r_ = (hac < hao).astype(float)
        add("HA2", "T", "HEIKIN", rsum(g, 2) == 2, rsum(r_, 2) == 2); add("HA3", "T", "HEIKIN", rsum(g, 3) == 3, rsum(r_, 3) == 3)
        for n in (20, 50):
            sl = slope(c, n); add(f"LRS{n}", "T", "LINREG", sl > 0, sl < 0)
        lc = np.log(c); t3 = ema(np.nan_to_num(ema(np.nan_to_num(ema(lc, 15)), 15)), 15); t3[:45] = np.nan; trix = t3 - lag(t3)
        tsg = ema(np.nan_to_num(trix), 9); tsg[:55] = np.nan
        add("TRIX_ZERO", "T", "TRIX", trix > 0, trix < 0); add("TRIX_SIG", "T", "TRIX", trix > tsg, trix < tsg)
        km = kama(c); add("KAMA_UP", "T", "KAMA", km > lag(km), km < lag(km))
        hma = wma(np.nan_to_num(2 * wma(c, 10) - wma(c, 20)), 4); hma[:24] = np.nan; add("HMA_UP", "T", "HMA", hma > lag(hma), hma < lag(hma))
        vip = rsum(np.abs(h - lag(l)), 14) / rsum(tr, 14); vim = rsum(np.abs(l - lag(h)), 14) / rsum(tr, 14)
        add("VORTEX", "T", "VORTEX", vip > vim, vim > vip)
        obv = np.cumsum(np.sign(np.nan_to_num(c - pc)) * v); add("OBV_SMA", "T", "VOLUME", obv > sma(obv, 20), obv < sma(obv, 20))
        mfm = np.where(rng > 0, ((c - l) - (h - c)) / rng, 0.0); cmf = rsum(mfm * v, 20) / rsum(v, 20)
        add("CMF", "T", "VOLUME", cmf > 0.05, cmf < -0.05)
        adl = np.cumsum(mfm * v); add("AD_SMA", "T", "VOLUME", adl > sma(adl, 20), adl < sma(adl, 20))
        fi = ema(np.nan_to_num(c - pc) * v, 13); add("FORCE13", "T", "VOLUME", fi > 0, fi < 0)
        add("HI252", "T", "HILO", c >= 0.98 * hh(h, 252), c <= 1.02 * ll(l, 252))
        r14 = rsi(c, 14); add("RSI14_M60", "T", "RSI_MOM", r14 > 60, r14 < 40); add("RSI14_M50", "T", "RSI_MOM", r14 > 50, r14 < 50)
        tp = (h + l + c) / 3; mad = _s(tp).rolling(20).apply(lambda w: np.abs(w - w.mean()).mean(), raw=True).to_numpy(copy=True)
        cci = (tp - sma(tp, 20)) / (0.015 * mad); add("CCI_B", "T", "CCI", cci > 100, cci < -100)
        hl2 = (h + l) / 2; ao = sma(hl2, 5) - sma(hl2, 34); add("AO_ZERO", "T", "AO", ao > 0, ao < 0); add("AO_UP", "T", "AO", ao > lag(ao), ao < lag(ao))
        rc = lambda n, m: sma(c / lag(c, n) - 1, m)
        kst = rc(10, 10) + 2 * rc(15, 10) + 3 * rc(20, 10) + 4 * rc(30, 15); add("KST_SIG", "T", "KST", kst > sma(kst, 9), kst < sma(kst, 9))
        dc_ = np.nan_to_num(c - pc); e2 = lambda x: ema(np.nan_to_num(ema(x, 25)), 13)
        tsi = 100 * e2(dc_) / e2(np.abs(dc_)); tsi[:40] = np.nan; add("TSI_ZERO", "T", "TSI", tsi > 0, tsi < 0)
        e13 = ema(c, 13); add("ELDER", "T", "ELDER", (e13 > lag(e13)) & (hist > lag(hist)), (e13 < lag(e13)) & (hist < lag(hist)))
        atr22 = rma(tr, 22); ch = flipstate(np.nan_to_num(c > lag(ll(l, 22) + 3 * atr22)) > 0, np.nan_to_num(c < lag(hh(h, 22) - 3 * atr22)) > 0)
        add("CHAND", "T", "CHAND", ch > 0, ch < 0)
        gap = o / pc - 1; add("GAP_F", "T", "GAP", gap >= 0.005, gap <= -0.005)
        big = (c - pc) / lag(atr14); add("BIG_F", "T", "BIGDAY", big >= 1.5, big <= -1.5)
        sk = streak(c); add("UP3_F", "T", "STREAK_MOM", sk >= 3, sk <= -3)
        vr = v / lag(sma(v, 20)); add("VOLTHRUST", "T", "VOLUME", (vr >= 1.5) & (c > pc), (vr >= 1.5) & (c < pc))
        outside = (h > lag(h)) & (l < lag(l)); add("OUTSIDE", "T", "CANDLE", outside & (c > o), outside & (c < o))
        body = np.abs(c - o); po, pcl = lag(o), lag(c)
        add("ENGULF", "T", "CANDLE", (pcl < po) & (c > o) & (o <= pcl) & (c >= po), (pcl > po) & (c < o) & (o >= pcl) & (c <= po))
        ibs = np.where(rng > 0, (c - l) / rng, 0.5)
        gs = ((c > o) & (c > pc) & (ibs > 0.7)).astype(float); bs = ((c < o) & (c < pc) & (ibs < 0.3)).astype(float)
        add("SOLDIERS3", "T", "CANDLE", rsum(gs, 3) == 3, rsum(bs, 3) == 3)
        add("STRONGCLOSE", "T", "CANDLE", (ibs > 0.9) & (rng > lag(atr14)), (ibs < 0.1) & (rng > lag(atr14)))
        add("VIX_TR", "T", "VIX_TREND", vix < sma(vix, 20), vix > sma(vix, 20))
        vt = vix / vix3m; add("VIXTERM_T", "T", "VIX_TREND", vt < 0.90, vt > 1.0)
        # ---- additional trend / momentum readings ----
        wk = pd.DatetimeIndex(cal["dates"]).to_period("W").asi8; mo = pd.DatetimeIndex(cal["dates"]).to_period("M").asi8
        def prior_period(x, per, fn):
            g = _s(x).groupby(per).agg(fn); return _s(per).map(g.shift(1)).to_numpy(copy=True)
        add("PWHL", "T", "PRIORHL", c > prior_period(h, wk, "max"), c < prior_period(l, wk, "min"))
        add("PMHL", "T", "PRIORHL", c > prior_period(h, mo, "max"), c < prior_period(l, mo, "min"))
        pv = (lag(h) + lag(l) + pc) / 3; add("PIVOT", "T", "PIVOT", c > 2 * pv - lag(l), c < 2 * pv - lag(h))
        bpw = h - e13; brp = l - e13
        add("ELDERRAY", "T", "ELDER", (e13 > lag(e13)) & (brp < 0) & (brp > lag(brp)), (e13 < lag(e13)) & (bpw > 0) & (bpw < lag(bpw)))
        add("DON5", "T", "DONCH", c > lag(hh(h, 5)), c < lag(ll(l, 5)))
        r21 = c / lag(c, 21) - 1; add("ROC21_5", "T", "ROC", r21 > 0.05, r21 < -0.05)
        m121 = lag(c, 21) / lag(c, 252) - 1; add("MOM12_1", "T", "ROC", m121 > 0, m121 < 0)
        rs = (c / lag(c, 63)) / (a["bench"] / lag(a["bench"], 63)) - 1; add("RELSTR", "T", "RELSTR", rs > 0, rs < 0)
        tl = a["tlt"]; add("BOND_TR", "T", "INTERMKT", tl > sma(tl, 50), tl < sma(tl, 50))
        add("OVN_M", "T", "SESSION", gap > 0, gap < 0); add("INTRA_M", "T", "SESSION", c > o, c < o)
        hhhl = ((h > lag(h)) & (l > lag(l))).astype(float); lllh = ((h < lag(h)) & (l < lag(l))).astype(float)
        add("HHHL3", "T", "SWING", rsum(hhhl, 3) == 3, rsum(lllh, 3) == 3)
        fu = np.full(T, np.nan); fd = np.full(T, np.nan)
        for i in range(4, T):
            fu[i] = h[i - 2] if h[i - 2] == max(h[i - 4:i + 1]) else fu[i - 1]
            fd[i] = l[i - 2] if l[i - 2] == min(l[i - 4:i + 1]) else fd[i - 1]
        add("FRACTAL", "T", "SWING", c > fu, c < fd)
        atr20 = rma(tr, 20); sq = (2 * s20 < 1.5 * atr20).astype(float); rsq = hh(sq, 5) > 0
        mom = c - ((hh(h, 20) + ll(l, 20)) / 2 + m20) / 2
        add("TTM_SQZ", "T", "SQUEEZE", rsq & (mom > 0) & (mom > lag(mom)), rsq & (mom < 0) & (mom < lag(mom)))
        e8, e13_, e21, e55 = ema(c, 8), ema(c, 13), ema(c, 21), ema(c, 55)
        add("RIBBON", "T", "MA", (e8 > e13_) & (e13_ > e21) & (e21 > e55), (e8 < e13_) & (e13_ < e21) & (e21 < e55))
        vwma = rsum(c * v, 20) / rsum(v, 20); add("VWMA20", "T", "MA", c > vwma, c < vwma)
        # ---------------- reversal ----------------
        r2 = rsi(c, 2); r3 = rsi(c, 3); r5 = rsi(c, 5)
        for th in (5, 10, 15): add(f"RSI2_{th}", "R", "RSI_REV", r2 < th, r2 > 100 - th)
        for th in (10, 20): add(f"RSI3_{th}", "R", "RSI_REV", r3 < th, r3 > 100 - th)
        for th in (20, 30): add(f"RSI5_{th}", "R", "RSI_REV", r5 < th, r5 > 100 - th)
        for th in (30, 35): add(f"RSI14_{th}", "R", "RSI_REV", r14 < th, r14 > 100 - th)
        crsi = (r3 + rsi(sk, 2) + 100 * pct_rank(ret, 100)) / 3
        for th in (10, 20): add(f"CRSI_{th}", "R", "CRSI", crsi < th, crsi > 100 - th)
        fk = 100 * (c - ll(l, 14)) / (hh(h, 14) - ll(l, 14)); sk_ = sma(fk, 3); sdd = sma(sk_, 3)
        add("STO_20", "R", "STOCH", sk_ < 20, sk_ > 80); add("STO_X", "R", "STOCH", (sk_ < 20) & (sk_ > sdd), (sk_ > 80) & (sk_ < sdd))
        add("WR14_10", "R", "STOCH", fk < 10, fk > 90)
        fk5 = 100 * (c - ll(l, 5)) / (hh(h, 5) - ll(l, 5)); add("WR5_10", "R", "STOCH", fk5 < 10, fk5 > 90)
        add("CCI_R", "R", "CCI", cci < -100, cci > 100); add("CCI_R150", "R", "CCI", cci < -150, cci > 150)
        add("BB_R", "R", "BB", c < m20 - 2 * s20, c > m20 + 2 * s20)
        m10 = sma(c, 10); s10 = sd(c, 10); add("BB_R10", "R", "BB", c < m10 - 1.5 * s10, c > m10 + 1.5 * s10)
        add("KELT_R", "R", "KELT", c < e20 - 2 * atr10, c > e20 + 2 * atr10)
        add("IBS_10", "R", "IBS", ibs < 0.1, ibs > 0.9); add("IBS_20", "R", "IBS", ibs < 0.2, ibs > 0.8)
        ib3 = sma(ibs, 3); add("IBS3_25", "R", "IBS", ib3 < 0.25, ib3 > 0.75)
        for n in (2, 3, 4): add(f"DN{n}", "R", "STREAK_REV", sk <= -n, sk >= n)
        for n in (3, 5, 7, 10): add(f"LOW{n}", "R", "NDAYLOW", c <= ll(c, n), c >= hh(c, n))
        for n, k in ((5, 1.5), (10, 1.5), (10, 2.0), (20, 2.0)):
            z = (c - sma(c, n)) / sd(c, n); add(f"Z{n}_{k}", "R", "ZSCORE", z < -k, z > k)
        add("GAP_R", "R", "GAP", gap <= -0.005, gap >= 0.005)
        add("BIG_R", "R", "BIGDAY", big <= -1.5, big >= 1.5)
        pos = np.where(tp > lag(tp), tp * v, 0.0); neg = np.where(tp < lag(tp), tp * v, 0.0)
        mfi = 100 - 100 / (1 + rsum(pos, 14) / rsum(neg, 14)); add("MFI_20", "R", "MFI", mfi < 20, mfi > 80)
        bp = c - np.minimum(l, pc); uo = 100 * (4 * rsum(bp, 7) / rsum(tr, 7) + 2 * rsum(bp, 14) / rsum(tr, 14) + rsum(bp, 28) / rsum(tr, 28)) / 7
        add("UO_30", "R", "UO", uo < 30, uo > 70)
        dmx = np.maximum(np.nan_to_num(h - lag(h)), 0); dmn = np.maximum(np.nan_to_num(lag(l) - l), 0)
        dem = sma(dmx, 14) / (sma(dmx, 14) + sma(dmn, 14)); add("DEM_30", "R", "DEMARK", dem < 0.3, dem > 0.7)
        fs = fisher(h, l); add("FISHER_R", "R", "FISHER", fs < -1.5, fs > 1.5)
        d1 = np.nan_to_num(c - pc); su = rsum(np.maximum(d1, 0), 9); sdn = rsum(np.maximum(-d1, 0), 9); cmo = 100 * (su - sdn) / (su + sdn)
        add("CMO_50", "R", "CMO", cmo < -50, cmo > 50)
        pr5 = pct_rank(c / lag(c, 5) - 1, 252); add("PCTL5", "R", "PCTL", pr5 < 0.10, pr5 > 0.90)
        lsh = np.minimum(o, c) - l; ush = h - np.maximum(o, c)
        add("HAMMER", "R", "CANDLE", (lsh >= 2 * body) & (ush <= 0.5 * body) & (body > 0) & (c < lag(c, 3)),
            (ush >= 2 * body) & (lsh <= 0.5 * body) & (body > 0) & (c > lag(c, 3)))
        vs = sma(vix, 10); add("VIX_SPK", "R", "VIX_REV", vix >= 1.10 * vs, vix <= 0.90 * vs)
        vm = sma(vix, 20); vsd = sd(vix, 20); add("VIX_BB", "R", "VIX_REV", vix > vm + 2 * vsd, vix < vm - 2 * vsd)
        vr2 = rsi(vix, 2); add("VIX_RSI2", "R", "VIX_REV", vr2 > 90, vr2 < 10)
        vsk = streak(vix); add("VIX_UP3", "R", "VIX_REV", vsk >= 3, vsk <= -3)
        add("VIXTERM_R", "R", "VIX_REV", vt > 1.0, vt < 0.82)
        vp = pct_rank(vix, 252); add("VIX_PCT", "R", "VIX_REV", vp > 0.90, vp < 0.10)
        # ---- additional reversal readings ----
        add("RSI_DIV", "R", "DIVERG", (c <= ll(c, 20)) & (r14 > lag(ll(r14, 20))), (c >= hh(c, 20)) & (r14 < lag(hh(r14, 20))))
        add("MACD_DIV", "R", "DIVERG", (c <= ll(c, 20)) & (hist > lag(ll(hist, 20))), (c >= hh(c, 20)) & (hist < lag(hh(hist, 20))))
        cr2 = r2 + lag(r2); add("CUMRSI2", "R", "RSI_REV", cr2 < 35, cr2 > 165)
        add("LO252_R", "R", "HILO", c <= 1.02 * ll(l, 252), c >= 0.98 * hh(h, 252))
        s200 = sma(c, 200); add("DIST200", "R", "STRETCH", c < 0.90 * s200, c > 1.10 * s200)
        r3d = c / lag(c, 3) - 1; r5d = c / lag(c, 5) - 1
        add("RET3_3", "R", "STRETCH", r3d < -0.03, r3d > 0.03); add("RET5_5", "R", "STRETCH", r5d < -0.05, r5d > 0.05)
        add("STRETCH", "R", "STRETCH", c < m10 - 1.5 * atr14, c > m10 + 1.5 * atr14)
        add("BB_R25", "R", "BB", c < m20 - 2.5 * s20, c > m20 + 2.5 * s20)
        srsi = (r14 - ll(r14, 14)) / (hh(r14, 14) - ll(r14, 14)); add("STOCHRSI", "R", "STOCH", srsi < 0.1, srsi > 0.9)
        wvf = 100 * (hh(c, 22) - l) / hh(c, 22); add("WVF", "R", "WVF", wvf > sma(wvf, 20) + 2 * sd(wvf, 20), np.zeros(T))
        small = body <= 0.1 * rng
        add("DOJI_R", "R", "CANDLE", small & (c <= ll(c, 5)), small & (c >= hh(c, 5)))
        pb = np.abs(pcl - po); p2o, p2c = lag(o, 2), lag(c, 2); b2 = np.abs(p2c - p2o)
        add("HARAMI", "R", "CANDLE", (pcl < po) & (pb > lag(atr14) * 0.7) & (c > o) & (c < po) & (o > pcl),
            (pcl > po) & (pb > lag(atr14) * 0.7) & (c < o) & (c > po) & (o < pcl))
        add("STAR3", "R", "CANDLE", (p2c < p2o) & (b2 > lag(atr14, 2) * 0.7) & (pb < 0.3 * b2) & (c > o) & (c > (p2o + p2c) / 2),
            (p2c > p2o) & (b2 > lag(atr14, 2) * 0.7) & (pb < 0.3 * b2) & (c < o) & (c < (p2o + p2c) / 2))
        add("PIERCE", "R", "CANDLE", (pcl < po) & (o < lag(l)) & (c > (po + pcl) / 2) & (c < po), (pcl > po) & (o > lag(h)) & (c < (po + pcl) / 2) & (c > po))
        add("GAP_R1", "R", "GAP", gap <= -0.01, gap >= 0.01)
        intra = c / o - 1; add("INTRA_R", "R", "SESSION", intra < -0.01, intra > 0.01)
        add("VOLCLIMAX", "R", "VOLUME", (c < pc) & (vr >= 2) & (ibs < 0.25), (c > pc) & (vr >= 2) & (ibs > 0.75))
        add("VIX_SPK20", "R", "VIX_REV", vix >= 1.20 * vs, vix <= 0.85 * vs)
        vch = vix / lag(vix) - 1; add("VIX_JUMP", "R", "VIX_REV", vch >= 0.15, vch <= -0.10)
        add("VIX_GT30", "R", "VIX_REV", vix > 30, vix < 12)
        # ---------------- neutral filters ----------------
        lr = np.log(c / pc); rv = sd(lr, 20); rvm = _s(rv).rolling(252).median().to_numpy(copy=True)
        add("F_RV_LOW", "F", "F_RVOL", rv < rvm); add("F_RV_HIGH", "F", "F_RVOL", rv > rvm)
        add("F_VIX_LT15", "F", "F_VIX", vix < 15); add("F_VIX_15_25", "F", "F_VIX", (vix >= 15) & (vix < 25)); add("F_VIX_GT25", "F", "F_VIX", vix >= 25)
        add("F_ADX_LT20", "F", "F_ADX", adx < 20); add("F_ADX_GT25", "F", "F_ADX", adx > 25)
        add("F_VOL_HI", "F", "F_VOLUME", vr >= 1.5); add("F_VOL_LO", "F", "F_VOLUME", vr <= 0.7)
        add("F_NR7", "F", "F_RANGE", rng <= ll(rng, 7)); add("F_NR4", "F", "F_RANGE", rng <= ll(rng, 4))
        add("F_INSIDE", "F", "F_RANGE", (h < lag(h)) & (l > lag(l))); add("F_WIDE", "F", "F_RANGE", rng >= 1.5 * lag(atr14))
        chop = 100 * np.log10(rsum(tr, 14) / (hh(h, 14) - ll(l, 14))) / np.log10(14)
        add("F_CHOP_HI", "F", "F_CHOP", chop > 61.8); add("F_CHOP_LO", "F", "F_CHOP", chop < 38.2)
        bbw = 4 * s20 / m20; add("F_SQUEEZE", "F", "F_SQUEEZE", bbw <= ll(bbw, 126))
        for k, nm in enumerate(("MON", "TUE", "WED", "THU", "FRI")): add(f"F_{nm}", "F", "F_DOW", cal["dow"] == k)
        add("F_NOVAPR", "F", "F_SEASON", cal["novapr"]); add("F_MAYOCT", "F", "F_SEASON", ~cal["novapr"])
        atrp = atr14 / c; ap = pct_rank(atrp, 252); add("F_ATR_HI", "F", "F_ATR", ap > 0.75); add("F_ATR_LO", "F", "F_ATR", ap < 0.25)
        add("F_DOM_H1", "F", "F_DOM", cal["dom"] <= 10); add("F_DOM_H2", "F", "F_DOM", cal["dom"] > 10)
        # ---------------- calendar (long only) ----------------
        Z = np.zeros(T, bool)
        add("CAL_TOM", "C", "CAL", cal["tom_next"], Z); add("CAL_OPEXWK", "C", "CAL", cal["opex_next"], Z); add("CAL_PREHOL", "C", "CAL", cal["prehol"], Z)
        add("CAL_FIRSTDAY", "C", "CAL", cal["first_next"], Z)
    names = [x[0] for x in out]; assert len(set(names)) == len(names)
    return names, [x[1] for x in out], [x[2] for x in out], np.column_stack([x[3] for x in out]), np.column_stack([x[4] for x in out])
