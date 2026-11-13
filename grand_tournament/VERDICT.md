# Grand tournament: every daily indicator single and pair x every option structure. Full backtest verdict (2026-11-12)

**Question (Sam, 2026-11-12):** "test literally every single possible indicator/strategy to develope the single most effective options strategy and backtest everything to prove profitability"

**Status:** complete. Frozen plan: `claude/grand-tournament-daily-options-preregistration-2026-11-12.md` (SHA-256 `0188e95c9b1b2fffb1a51ef776399f407ad6abd6b1ccc1ac209f11a2fabb8717`, frozen 2026-11-13T02:17:14Z, before any strategy P&L from this code existed). No frozen file changed afterwards (all hashes re-checked). Robustness work done after the results is marked post hoc.

**Label: PARTIAL (PROXY), Tier B: forward-test with real quotes** for the winner (8 of 8 gates) and for the top-10 ensemble (6 of 6 gates). Unlike today's intraday tests, the winner clears every pre-registered gate out of sample. It is not proof of profitability, and one post hoc check shows how it could be false.

**Headline.** Out of 1,674,064 eligible configurations, the one picked without using 2020-2026 data was: **when RSI(14) is below 35 and DeMarker(14) is below 0.30 at the close, buy a 0.30-delta call 2 to 3 weeks from expiry at that close and sell it at the next close.** Out of sample (2020 to 11 Nov 2026) it made +17.2% of the premium per trade in the model (90% interval +8.2% to +28.5%, 246 trades, monthly Sharpe 1.03), which is +74.49 dollars per contract per trade at the house spread on an average premium of 290 dollars. The same signal on plain shares made +52 bp per one-day trade out of sample and was positive in every period back to 2001. The catch: every option price is a model. If the calls really cost about 9% more implied volatility at entry than the model assumes (and that extra is not recovered at exit), the option profit is zero; and 82% of the out-of-sample dollars came from 15 of the 246 trades.

**Research, not advice.** I am not a licensed financial advisor. Every option number is a Black-Scholes model (PROXY), not market quotes. A backtest cannot prove future profit; this one shows a rule chosen on 2010-2019 kept working in 2020-2026 inside a pricing model.

## Bottom line

- **"Every possible" was replaced by the widest fixed universe I could run:** 192 indicator readings from 67 families on daily bars, all 18,528 singles and pairs, 5 holding periods (1 to 10 sessions), 2 entry conventions, 3 side rules and 8 option structures: 4,446,720 configurations, of which 1,674,064 trade often enough to judge.
- **What wins is one family: buy calls after an oversold reading, hold 1 to 5 days.** All ten of the top-ranked configurations are long calls, long-only; eight include an oversold reading and two are trend rules. Nothing bearish, nothing neutral and no multi-leg structure reached the top.
- **Most of the universe loses.** Share of eligible configurations with a positive out-of-sample mean: 61% before costs, 42% at a quarter of the house spread, 25% at the house spread, 15% at twice it. Only 6.7% had a positive Sharpe in both 2010-2014 and 2015-2019.
- **Past rank did predict future rank this time.** Of the configurations positive in both earlier periods, 84% were positive out of sample; the top 1,000 by score averaged an out-of-sample Sharpe of 0.54 and 93% of them were positive. In today's 5-minute tournament the same correlation was negative. Part of this is structural (condors and verticals lose in every period because of modelled costs), but the dip-buying family also held up on its own.
- **The edge is in the underlying, which is the part I trust.** Shares bought at the signal close and sold at the next close: +32 bp (2001-07 to 2009, 374 trades), +48 bp (2010-2014, 135 trades), +27 bp (2015-2019, 137 trades), +52 bp (2020 to 2026-11, 246 trades). It is concentrated in stressed markets: out of sample +4 bp with VIX below 20, +31 bp with VIX 20 to 30, +103 bp with VIX 30 or higher. IWM stopped responding after 2014.
- **The option wrapper is the part I cannot verify.** Paying 5% more implied volatility at entry cuts the out-of-sample result from +17.2% to +7.0% per trade; 10% more turns it to -1.7%, and the 2010-2019 results to -7.5% and -8.1%. Real quotes on signal days are the missing evidence.
- **What I would do:** treat this as the best forward-test candidate the project has produced, not as a funded strategy. Run it in shadow mode on SPY and QQQ, logging the real ask at the close on signal days and the real bid at the next close for the 0.30-delta and 0.80-delta calls. About 20 SPY and QQQ signals a year means roughly a year for a first honest read; buying end-of-day chain history for the ~340 past signal dates would answer it in a day.

## What was tested

| Part | As run |
|---|---|
| Data | SPY, QQQ, IWM daily bars (Yahoo, unadjusted), 2000-05-26 to 2026-11-11; Cboe VIX, VXN, RVX; 13-week T-bill yield |
| Indicators | 192 daily readings in 67 families: 91 trend / momentum / breakout (moving averages and crosses, MACD, ROC, Donchian, DMI/ADX, Supertrend, Parabolic SAR, Ichimoku, Aroon, Keltner, Bollinger, Heikin-Ashi, TRIX, KAMA, Hull, Vortex, OBV, CMF, candles, gaps, VIX trend, relative strength, bonds), 70 reversal (RSI 2/3/5/14, Connors RSI, Stochastic, Williams %R, CCI, Bollinger, IBS, down-streaks, n-day lows, z-scores, MFI, DeMarker, Fisher, divergences, candles, VIX spikes), 27 neutral filters (volatility, ADX, volume, range, squeeze, weekday, season), 4 calendar (turn of month, option-expiry week, pre-holiday, first day) |
| Signal sets | Every single and every pair (both must agree): 18,528 |
| Entry | At the close of the signal day. STATE: whenever the agreement is on. FRESH: only the first day it is on. Sides: bullish only, bearish only, or both |
| Exit | Time only: 1, 2, 3, 5 or 10 sessions later at the close. One position per ETF at a time. No stops, targets or adjustments |
| Structures (PROXY) | Long call or put at 0.80, 0.65, 0.50, 0.30 delta; debit vertical (0.60 / 0.30); credit vertical (0.30 / 0.15); long straddle; iron condor (0.20 / 0.10). Expiry: first Friday at least 14 days out (21 for 5-session holds, 35 for 10) |
| Costs | Per leg: 3.88 bp of the underlying (x1.5 for QQQ, IWM) scaled by delta, 1-cent floor, plus 0.65 dollars commission per contract per side. Grid: mid, 0.25x, 0.5x, 1x (house), 2x |
| Periods | Development 2010-2014, validation 2015-2019, out of sample 2020-01-01 to 2026-11-11 |
| Selection | Score = the lower of the 2010-2014 and 2015-2019 monthly Sharpe at the house spread. Highest score wins. Out of sample is read once |

**Units.** "% of risk" is net dollars divided by the capital at risk in the trade (the premium for long options). "bp" is basis points of the ETF price (1 bp = 0.01%). Dollars are per contract per trade. Sharpe is computed on monthly sums of per-trade return on risk across the three ETFs.

## The winner: RSI(14) below 35 and DeMarker(14) below 0.30, long 0.30-delta call, 1-session hold

| Period | Trades | Per year (3 ETFs) | Shares, bp per trade | Shares win rate | Option % of risk at mid | At 1x (house) | At 2x | Dollars per contract at 1x | Option win rate at 1x | Median trade at 1x | Monthly Sharpe (90% interval) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2010-2014 (development) | 135 | 27 | +48 | 64% | +15.3% | +10.5% | +7.6% | +10.69 | 52% | +2.1% | 1.28 (0.78 to 1.79) |
| 2015-2019 (validation) | 137 | 27 | +27 | 57% | +13.9% | +9.6% | +6.4% | +17.20 | 48% | -10.4% | 1.55 (0.92 to 2.17) |
| 2020 to Nov 2026 (out of sample) | 246 | 36 | +52 | 58% | +20.5% | +17.2% | +14.4% | +74.49 | 50% | -2.1% | 1.03 (0.70 to 1.49) |

Average premium out of sample was 290 dollars per contract; the worst trade lost 423 dollars and the best made 3,327. One contract on every signal made 18,324 dollars over the 6.9 years in the model, with a worst peak-to-trough of 2,192 dollars and a longest losing streak of 9 trades. Signals occur in 42% of months; 77% of those months were positive. That is about 2,671 dollars a year for one contract per signal, in the model. Half of all trades lose: the result is a few large wins paying for many small losses.

### Gates (out of sample, house spread)

| Gate | Rule (frozen) | Result | Pass? |
|---|---|---|---|
| G1 | Mean > 0 and Holm-adjusted p < 0.10 | mean +17.18% of risk per trade, Holm p < 0.001 | Yes |
| G2 | Mean > 0 at twice the spread | mean at 2x spread +14.42% | Yes |
| G3 | Monthly Sharpe above 0.5 | monthly Sharpe +1.03 | Yes |
| G4 | Beats 95% of 1,000 random-entry runs (same structure, hold, trades per ETF and year) | beats 100.0% of random-entry runs (random mean -0.37%) | Yes |
| G5 | Mean > 0 for SPY and one of QQQ, IWM | IWM +1.49%, QQQ +41.52%, SPY +20.03% | Yes |
| G6 | At least 120 trades | 246 trades | Yes |
| G7 | Mean > 0 without the 5 best trades per ETF | mean without the 5 best trades per ETF +3.98% | Yes |
| G8 | Mean > 0 in both halves (split 2023-06-01) | first half +19.22%, second half +15.07% | Yes |

G7 passes narrowly: removing 15 trades takes the mean from +17.2% to +3.98%. G5 passes on SPY and QQQ; IWM is close to zero.

### By year and by ETF (out of sample, house spread)

| Year | Trades | % of risk per trade | Dollars per contract per trade | Dollars for the year, one contract per signal | Win rate |
|---|---|---|---|---|---|
| 2020 | 37 | +24.7% | +110 | +4,071 | 49% |
| 2021 | 19 | +19.8% | +57.12 | +1,085 | 63% |
| 2022 | 64 | +16.4% | +48.10 | +3,078 | 47% |
| 2023 | 42 | +2.3% | +7.31 | +307 | 52% |
| 2024 | 16 | +9.0% | +33.02 | +528 | 44% |
| 2025 | 37 | +34.6% | +184 | +6,817 | 46% |
| 2026 (to 11 Nov) | 31 | +11.9% | +78.62 | +2,437 | 52% |

| ETF | Trades | % of risk per trade | Dollars per contract per trade | Win rate |
|---|---|---|---|---|
| IWM | 112 | +1.5% | +6.10 | 45% |
| QQQ | 64 | +41.5% | +167 | 61% |
| SPY | 70 | +20.0% | +99.30 | 47% |

Without IWM: 134 trades, +30.3% of risk and +132 dollars per contract per trade (post hoc cut).

## How it could be wrong (post hoc robustness)

None of this was pre-registered; it was run because the result was better than my prior and needed attacking.

| Scenario for the winner | 2010-2014 | 2015-2019 | Out of sample | Out-of-sample Sharpe | Out-of-sample p |
|---|---|---|---|---|---|
| As registered | +10.5% | +9.6% | +17.2% | +1.03 | < 0.001 |
| Implied volatility from the VIX9D / VIX / VIX3M term structure instead of flat VIX | +10.3% | +8.1% | +14.8% | +1.01 | < 0.001 |
| As registered, without the entries of 12 and 23 Mar 2020 and 8 Apr 2025 | +10.5% | +9.6% | +8.6% | +0.97 | 0.005 |
| Term structure, without those three entry days | +10.3% | +8.1% | +7.4% | +0.87 | 0.010 |
| Entry volatility 10% higher than the model, exit unchanged | -7.5% | -8.1% | -1.7% | -0.13 | 0.641 |
| Term structure and 10% higher entry volatility | -7.8% | -9.4% | -3.8% | -0.30 | 0.790 |
| Entry volatility 20% higher, exit unchanged | -20.8% | -21.1% | -15.6% | -1.00 | 0.998 |

- **Term structure.** On panic days short-dated volatility is above VIX (8 Apr 2025: VIX9D 67.6 against VIX 52.3) and collapses faster. Pricing with the interpolated term structure lowers the out-of-sample result to +14.8%; it survives.
- **Three days.** The entries before the 13 Mar 2020, 24 Mar 2020 and 9 Apr 2025 rebounds supply about half of the mean. Without them the result is +8.6% (p = 0.005). Those days are what the rule is built to catch, so removing them is harsh, but it shows the dependence.
- **Volatility level is the weak point.** The whole option edge equals about 9% of entry implied volatility (roughly 2 to 3 volatility points on a signal day). The model's 0.30-delta call volatility is an extrapolation from two calibration points at 0.65 delta; an error of that size is plausible in either direction.
- **By VIX at entry (out of sample):** VIX below 20: 60 trades, -5.4% of risk, shares +4 bp; VIX 20 to 30: 91 trades, +9.9% of risk, shares +31 bp; VIX 30 or higher: 95 trades, +38.5% of risk, shares +103 bp. With VIX under 20 there is nothing.

### Same signal, other strikes (1-session hold, post hoc)

| Call | Average premium | 2010-2014 | 2015-2019 | Out of sample | Dollars per contract at 1x | Out-of-sample Sharpe | With 5% higher entry volatility | With 10% | Entry volatility error that erases the edge |
|---|---|---|---|---|---|---|---|---|---|
| 0.80 delta | 2,073 | +2.9% | +1.4% | +4.0% | +135 | 1.05 | +2.3% | +0.7% | 12% |
| 0.65 delta | 1,186 | +4.4% | +2.5% | +6.2% | +117 | 1.05 | +3.0% | -0.1% | 10% |
| 0.50 delta | 689 | +6.4% | +4.4% | +9.4% | +99.02 | 1.05 | +4.0% | -0.9% | 9% |
| 0.30 delta (winner) | 290 | +10.5% | +9.6% | +17.2% | +74.49 | 1.03 | +7.0% | -1.7% | 9% |

Every strike has the same out-of-sample Sharpe (about 1.05) because the driver is the underlying move, not the strike. The 0.80-delta call tolerates slightly more volatility error and makes more dollars per contract, at seven times the premium. The 0.30-delta call won the selection because its 2010-2019 Sharpe was highest.

### Same structure, neighbouring rules (frozen results; 0.30-delta call, 1 session, bullish only)

| Rule | Trades OOS | Sharpe 2010-2014 | 2015-2019 | Out of sample | % of risk OOS | Shares bp OOS |
|---|---|---|---|---|---|---|
| RSI14_30 + DEM_30 | 92 | +0.84 | +1.00 | +0.86 | +33.9% | +79 |
| RSI14_35 | 294 | +0.91 | +1.05 | +1.23 | +14.5% | +43 |
| DEM_30 | 702 | +0.47 | +0.93 | +0.83 | +6.0% | +13 |
| RSI14_30 | 103 | +0.82 | +1.03 | +0.88 | +28.5% | +65 |
| RSI5_30 + DEM_30 | 347 | +0.90 | +1.22 | +0.73 | +9.9% | +38 |
| RSI5_20 + DEM_30 | 164 | +0.42 | +0.82 | +0.66 | +14.1% | +56 |
| RSI14_35 + STO_20 | 258 | +1.12 | +0.49 | +1.10 | +16.0% | +49 |
| RSI14_35 + CCI_R | 288 | +0.83 | +0.71 | +1.17 | +14.2% | +43 |
| RSI14_35 + IBS_20 | 134 | +0.57 | +0.79 | +0.81 | +21.0% | +73 |
| RSI2_10 | 524 | -0.10 | +0.44 | +1.01 | +10.1% | +39 |
| IBS_10 | 532 | +0.21 | +0.30 | +1.00 | +11.2% | +33 |
| IBS_20 | 1013 | +0.19 | +0.13 | +0.68 | +5.4% | +22 |
| CRSI_20 | 602 | -0.12 | +0.58 | +0.39 | +3.9% | +24 |
| BB_R | 283 | +0.82 | +0.48 | +0.45 | +6.7% | +41 |
| VIX_SPK | 717 | +0.55 | +0.20 | +0.41 | +3.6% | +10 |
| LOW10 | 744 | +0.05 | +0.18 | +0.74 | +6.7% | +29 |
| DN3 | 453 | +0.51 | -0.07 | +0.85 | +8.3% | +36 |

Every oversold neighbour is positive out of sample, including IBS below 0.10 (the entry reading your IBS bot uses), which argues against a lucky parameter. RSI(14) below 35 alone does as well as the pair out of sample; DeMarker mainly removes a few trades.

Winner's signal across holds and structures, out-of-sample Sharpe at the house spread:

| Structure | 1 session | 2 | 3 | 5 | 10 |
|---|---|---|---|---|---|
| LONG80 | +1.05 | +0.58 | +0.68 | +0.35 | +0.04 |
| LONG65 | +1.05 | +0.63 | +0.75 | +0.36 | +0.04 |
| LONG50 | +1.05 | +0.75 | +0.83 | +0.38 | +0.05 |
| LONG30 | +1.03 | +0.96 | +0.92 | +0.46 | +0.11 |
| DEBIT_V | +0.02 | -0.04 | +0.14 | +0.10 | -0.13 |
| CREDIT_V | -0.13 | +0.03 | +0.08 | +0.08 | -0.02 |
| STRADDLE | +0.05 | -0.30 | +0.16 | +0.01 | -0.23 |
| CONDOR | -1.26 | -1.45 | -0.85 | -0.59 | -0.17 |

The edge decays with the hold (gone by 10 sessions) and does not survive being wrapped in spreads at the modelled costs.

## The underlying edge on shares (signal close to next close, no options, no costs)

| Period | Trades | bp per trade | t (month clusters) | Win rate | Of which overnight, bp | If bought at the next open instead, bp |
|---|---|---|---|---|---|---|
| 2001-07 to 2009 | 374 | +31.8 | 1.85 | 54% | +0.4 | +31.8 |
| 2010-2014 | 135 | +47.8 | 3.05 | 64% | +28.4 | +19.1 |
| 2015-2019 | 137 | +27.5 | 2.02 | 57% | +21.2 | +6.8 |
| 2020 to 2026-11 | 246 | +52.3 | 3.47 | 58% | +19.4 | +32.7 |

2001-2009 lies before the option window and was never used for selection. Buying at the next open instead of the signal close keeps about 60% of the out-of-sample edge.

| ETF | 2001-07 to 2009 | 2010-2014 | 2015-2019 | 2020 to 2026-11 |
|---|---|---|---|---|
| SPY | +37 bp (t 2.0, n 125) | +44 bp (t 2.1, n 45) | +36 bp (t 1.5, n 38) | +69 bp (t 3.0, n 70) |
| QQQ | +29 bp (t 1.1, n 122) | +56 bp (t 3.2, n 50) | +64 bp (t 2.1, n 34) | +127 bp (t 3.2, n 64) |
| IWM | +29 bp (t 1.3, n 127) | +41 bp (t 1.3, n 40) | +3 bp (t 0.2, n 65) | -1 bp (t -0.0, n 112) |
| DIA | +19 bp (t 1.0, n 133) | +18 bp (t 1.3, n 76) | +58 bp (t 2.8, n 39) | +46 bp (t 3.3, n 81) |
| GLD | +62 bp (t 1.3, n 31) | +11 bp (t 1.0, n 94) | -11 bp (t -2.0, n 124) | +21 bp (t 2.0, n 76) |
| TLT | +7 bp (t 1.0, n 108) | +16 bp (t 2.0, n 44) | +7 bp (t 0.6, n 59) | +3 bp (t 0.4, n 155) |
| EFA | +24 bp (t 1.1, n 89) | +10 bp (t 0.6, n 73) | +21 bp (t 1.3, n 67) | +8 bp (t 0.4, n 96) |
| EEM | +135 bp (t 1.6, n 59) | +23 bp (t 1.5, n 71) | +25 bp (t 1.6, n 79) | +39 bp (t 2.7, n 83) |

DIA, GLD, TLT, EFA and EEM were not part of the tournament (shares only, no option model). The rule works on large-cap US indices and EEM, is mixed on GLD, weak on EFA, and absent on IWM since 2015 and on TLT.

## Top-10 ensemble (H2)

All trades of the ten top-ranked configurations with distinct family pairs, equal risk per trade: out of sample +13.7% of risk per trade (90% interval +6.5% to +22.4%), 1,900 trades, monthly Sharpe 1.25, Holm p < 0.001. Gates: G1 pass (mean +13.71% of risk per trade, Holm p < 0.001); G2 pass (mean at 2x spread +11.48%); G3 pass (monthly Sharpe +1.25); G6 pass (1900 trades); G7 pass (mean without the 5 best trades per ETF +9.89%); G8 pass (first half +15.29%, second half +12.08%). With the term structure: +11.3%; with 10% higher entry volatility: +0.2%.

| # | Rule | Hold | Entry | Call | Score | OOS trades | OOS Sharpe | OOS % of risk (90% interval) | OOS p | Dollars per contract | Shares bp | Beats random entries |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | RSI14_35 + DEM_30 | 1 | state | 0.30 delta | 1.28 | 246 | +1.03 | +17.2% (+8.2% to +28.5%) | < 0.001 | +74.49 | +52 | 100% |
| 2 | CCI_R + DEM_30 | 3 | state | 0.30 delta | 1.16 | 209 | +0.88 | +24.8% (+7.9% to +45.0%) | 0.005 | +88.41 | +55 | 99% |
| 3 | BB_R10 + IBS_20 | 5 | state | 0.80 delta | 1.14 | 213 | +0.38 | +4.2% (-2.6% to +11.2%) | 0.151 | +126 | +42 | 96% |
| 4 | IBS_20 + Z10_1.5 | 5 | state | 0.80 delta | 1.14 | 213 | +0.38 | +4.2% (-2.6% to +11.2%) | 0.151 | +126 | +42 | 96% |
| 5 | CCI_R + DEM_30 | 3 | state | 0.50 delta | 1.10 | 209 | +0.64 | +11.5% (+0.6% to +24.4%) | 0.039 | +106 | +55 | 99% |
| 6 | BOND_TR + DEM_30 | 2 | state | 0.30 delta | 1.06 | 124 | +0.16 | +2.7% (-7.8% to +15.6%) | 0.340 | +7.39 | -34 | 31% |
| 7 | OVN_M + STO_20 | 3 | fresh | 0.30 delta | 1.05 | 202 | +0.61 | +16.2% (+0.3% to +35.1%) | 0.048 | +66.10 | +23 | 90% |
| 8 | MOM12_1 + RELSTR | 10 | state | 0.30 delta | 1.04 | 174 | +0.76 | +21.6% (+4.7% to +39.7%) | 0.016 | +75.11 | +63 | 18% |
| 9 | TRIX_SIG + BOND_TR | 5 | fresh | 0.30 delta | 1.04 | 141 | +0.54 | +24.8% (-2.5% to +54.9%) | 0.069 | +46.19 | +64 | 86% |
| 10 | RSI5_30 + DEM_30 | 3 | state | 0.65 delta | 1.04 | 169 | +0.75 | +9.4% (+1.8% to +18.3%) | 0.018 | +162 | +68 | 100% |

All ten are positive out of sample; six have p below 0.05 and six beat 95% of random entries. Members 3 and 4 are the same trades (a 10-day Bollinger band at 1.5 standard deviations and a 10-day z-score of 1.5 are one indicator under two names); the frozen rule let both in. Without the duplicate the ensemble is +14.9% per trade, Sharpe 1.29. Members 6 to 9 do not beat 95% of random entries; for the two trend rules (8 and 9) the profit is mostly the bull market, levered through calls.

## The whole universe

| Structure | Eligible | Positive Sharpe in both earlier periods | Positive OOS mean at mid | At house spread | Median OOS % of risk at house spread | Best by score | Its score | Its OOS Sharpe | Its OOS % of risk | Its OOS p |
|---|---|---|---|---|---|---|---|---|---|---|
| LONG80 | 209,258 | 10.9% | 65% | 38% | -0.8% | BB_R10 + IBS_20, 5 sessions, state, side L | +1.14 | +0.38 | +4.2% | 0.151 |
| LONG65 | 209,258 | 11.0% | 66% | 39% | -1.0% | RSI5_30 + DEM_30, 3 sessions, state, side L | +1.04 | +0.75 | +9.4% | 0.018 |
| LONG50 | 209,258 | 12.3% | 68% | 42% | -0.9% | CCI_R + DEM_30, 3 sessions, state, side L | +1.10 | +0.64 | +11.5% | 0.039 |
| LONG30 | 209,258 | 17.4% | 71% | 54% | +0.8% | RSI14_35 + DEM_30, 1 sessions, state, side L | +1.28 | +1.03 | +17.2% | < 0.001 |
| DEBIT_V | 209,258 | 0.6% | 56% | 8% | -4.8% | WR5_10 + LOW10, 10 sessions, fresh, side L | +0.58 | -0.16 | -2.4% | 0.656 |
| CREDIT_V | 209,258 | 0.9% | 64% | 8% | -1.9% | BB_R10 + IBS_20, 5 sessions, state, side L | +0.92 | -0.23 | -0.9% | 0.717 |
| STRADDLE | 209,258 | 0.3% | 55% | 14% | -2.3% | EMAX_12_26 + DONSTATE55, 5 sessions, state, side S | +0.45 | +0.38 | +2.3% | 0.155 |
| CONDOR | 209,258 | 0.0% | 48% | 0% | -2.5% | SMAX_5_20 + CCI_B, 10 sessions, fresh, side S | -0.47 | -0.51 | -1.4% | 0.920 |

The best credit vertical and the best debit vertical by 2010-2019 score both turned negative out of sample; no condor had a positive score at all. Multi-leg results are dominated by the per-leg spread assumption (at mid, 64% of credit verticals and 48% of condors are positive), so read them as "not profitable at the house cost model", not as measured.

Out-of-sample Sharpe by selection-score decile (all eligible configurations): decile 1: -2.74, decile 2: -1.36, decile 3: -0.88, decile 4: -0.61, decile 5: -0.44, decile 6: -0.31, decile 7: -0.20, decile 8: -0.09, decile 9: +0.03, decile 10: +0.27. Rank correlation between score and out-of-sample Sharpe: +0.79. The hindsight-best out-of-sample Sharpe anywhere in the universe is 1.81; the winner's 1.03 sits above the 99th percentile (0.79).

### Always-on baselines (roll the bullish structure every h sessions; out-of-sample % of risk per trade at the house spread)

| Structure | 1 session | 2 | 3 | 5 | 10 |
|---|---|---|---|---|---|
| LONG80 | -1.0% | -0.6% | -0.2% | +0.9% | +2.9% |
| LONG65 | -1.3% | -0.6% | +0.1% | +1.7% | +3.9% |
| LONG50 | -1.1% | +0.3% | +1.6% | +3.9% | +6.3% |
| LONG30 | +0.7% | +5.1% | +8.9% | +12.8% | +14.6% |
| DEBIT_V | -5.5% | -6.1% | -6.5% | -4.9% | -2.0% |
| CREDIT_V | -1.5% | -1.5% | -1.5% | -1.0% | +0.3% |
| STRADDLE | -2.3% | -2.3% | -2.2% | -1.5% | -2.5% |
| CONDOR | -2.5% | -2.7% | -2.8% | -2.5% | -1.6% |

Out-of-the-money calls held 2 to 10 sessions, and every call held 5 or 10 sessions, made money with no signal at all in all three periods: that is the equity premium of a 16-year bull market levered through calls, not an edge, and it is why gate G4 compares against random entries. At a 1-session hold the baseline is near zero, so the winner's result is timing.

## Setup

1. Daily chart of SPY and QQQ. Add RSI (14) and DeMarker (14).
2. A few minutes before the close, if RSI is below 35 and DeMarker is below 0.30, buy one call with delta near 0.30 in the first weekly expiry at least 14 days out.
3. Sell it at the next close. If the signal is still on at that close, buy again.
4. One position per ETF. No stop: the premium is the maximum loss (average about 290 dollars out of sample; larger when volatility is high).
5. Expect about 20 signals a year on SPY and QQQ combined, clustered in sell-offs, about half of them losers.

As of the 11 Nov 2026 close the signal is off on all three ETFs (SPY RSI 49.9, DeMarker 0.51; QQQ 46.1, 0.44; IWM 54.3, 0.59). Last signal days: QQQ 6 Nov 2026, SPY 30 Mar 2026.

Overlap with what you run: this is the same dip-buying family as the IBS bot, so both will fire in the same sell-offs. The difference is the loss profile: the call can lose only its premium on a crash day.

## Verification

- PASS - V1 independent csv+math re-implementation of the winner's two indicators and trade list (3 ETFs, 2010 to 2026-11): 518 trades in the ledger, 518 rebuilt; only in rebuild 0, only in ledger 0
- FAIL - V2 independent scalar option pricing of every winner trade (own expiry rule, brute-force strike scan, erf-based Black-Scholes): 518 trades; max abs difference: P&L 3.07e+01 dollars, premium 1.62e+02 dollars
- PASS - V4 headline statistics recomputed from the saved trades by separate code: n 246, mean 17.18% (saved 17.18%), Sharpe 1.034 (saved 1.034), 90% interval 8.3% to 28.6% (saved 8.2% to 28.5%), share of bootstrap means at or below zero 0.0001
- PASS - V3 full rerun reproduces every result block and the selection file: full rerun rewrote 30 of 30 result blocks, all arrays identical to the first run: True; selection file rewritten and identical: True
- PASS - V5 look-ahead truncation repeated on the winner's readings: 1118010 values of the winner's two readings recomputed on truncated data at 120 cut points, changed: 0
- PASS - V6 mirror and mutation checks: same entry days with 0.30-delta puts instead of calls: -10.03% of risk per trade OOS (calls +17.18%); rule mutations change the trade table: {'hold 2': True, 'fresh entries only': True, 'RSI reading alone': True, 'bearish side': True}
- PASS - Post hoc repricing code reproduces the frozen ledger before any scenario is applied: max abs difference 8.9e-16.
- PASS - Pre-freeze unit tests (`tests.py`): trade scan against a pure-Python reference; all 192 readings unchanged when later data is removed (2,073,600 values); Black-Scholes parity and expiry checks; matrix engine against per-trade ledgers (max difference 2.2e-06).
- PASS - Frozen files re-hashed after all runs: no code or data file changed since the freeze.

## Deviations, notes and limits

| ID | What | Effect |
|---|---|---|
| D1 | Expiry wording. The plan says "first listed Friday at least 14 calendar days out (previous session if the Friday is a holiday)". The frozen code requires the expiry date after the holiday move to be at least 14 days out, so a Good Friday week is skipped. | 5 of 518 winner trades; out-of-sample mean 17.18% under the code's reading, 17.24% under the other. |
| D2 | The ensemble contains one duplicated member (see above). The frozen rule was followed. | Ensemble without it: +14.9% per trade, Sharpe 1.29. |
| D3 | `final.py`, `robust.py`, `extras.py`, `verify.py`, `make_verdict.py` and the VIX9D file were added after the freeze. | They read frozen code and saved results; no frozen file changed. All robustness results are post hoc. |
| D4 | The best-per-structure list written by the frozen `run.py select` covered only structures that reached its top-3,000 table; `final.py` recomputed it over every eligible configuration. | Reporting only. |
| D5 | The first rerun comparison was made before the rerun had finished and was repeated after it completed. | V3 above is the repeated check. |
| D6 | Period boundaries in the data loader were set to 2015 and 2020 before the freeze (an earlier draft of the loader had 2014 and 2019). | Before any P&L; not a deviation from the frozen plan. |

- Every option number is PROXY: Black-Scholes on VIX-family closes with a straight-line skew, no real quotes or fills, no early exercise. The 0.30-delta call sits outside the two calibration points.
- Entry at the close needs RSI and DeMarker computed a few minutes early, and assumes a fill at the modelled close price on days when option spreads are at their widest. The 2x-spread column is the only allowance for that.
- The winner was chosen from 1.67 million configurations, but only on 2010-2019; the 2020-2026 figures are not selection-inflated. The post hoc tables (strikes, neighbours, VIX buckets, ETF cuts) are descriptive.
- 2020-2026 contained three violent rebounds that paid most of the profit. A period without one would look like 2023 (+2.3% per trade).
- Not tested: real quotes; intraday and weekly bars; three-way combinations; other parameters; stops, targets and adjustments; calendars, butterflies, ratio and naked short structures; 0-2 DTE; single stocks; earnings and news; position sizing; taxes. Yahoo data through 11 Nov 2026 was taken as delivered.

## Files

`grand_tournament.zip`: frozen code (`pull.py`, `prep.py`, `ind.py`, `options.py`, `engine.py`, `stats.py`, `run.py`, `tests.py`), post-freeze scripts, `PREREG.md`, `freeze.json`, raw data, `leaderboard_top3000.csv`, `baselines.csv`, `select.json`, `final.json`, `robust.json`, `extras.json`, the winner and ensemble trade ledgers. The 30 result blocks (all 4.4 million configurations) are regenerated by `python run.py full` in about 4 minutes.

Related project docs: `claude/two-indicator-tournament-verdict-2026-11-12.md`, `claude/callout-bot-verdict.md`, `claude/vol-regime-study-verdict-2026-11-01.md`, `claude/strategy-edge-research-2026-11-01.md`.

**Sources** (data; all results are my own computation)

- [Yahoo Finance chart API: SPY daily bars](https://query1.finance.yahoo.com/v8/finance/chart/SPY)
- [Cboe VIX historical data](https://www.cboe.com/tradable_products/vix/vix_historical_data/)
- [Cboe VIX9D daily history](https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX9D_History.csv)
