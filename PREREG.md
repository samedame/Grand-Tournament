# Pre-registration: grand tournament of daily indicators and option structures (2026-11-12)

Written and hashed BEFORE any strategy P&L from this code existed. Done beforehand, none of it a strategy return: data download; indicator library; option pricing layer; unit tests (trade scan against a pure-Python reference, look-ahead truncation of all 192 indicator states on real data at 6 cut points per ETF, Black-Scholes parity, expiry and risk checks, matrix engine against per-trade ledgers with only the size of the difference printed); a sanity print of model prices, strikes and deltas on one date; and trade COUNTS for every configuration (`counts.log`).

**Question (Sam, 2026-11-12).** "Test literally every single possible indicator/strategy to develop the single most effective options strategy and backtest everything to prove profitability."

**What can and cannot be done.** The set of possible indicators and parameters is infinite, so "every possible" is replaced by a fixed, written-down universe that is as wide as I can run: 192 indicator readings from 67 families on daily bars, every single and every pair, 5 holding periods, 2 entry conventions, 3 side rules and 8 option structures. A backtest cannot prove future profit; it can show whether a rule chosen without hindsight made money in years it was not chosen on. That is the test here.

**Why daily bars.** About 130 earlier tests in this project, including today's 5-minute tournament, found intraday indicator edges of 1 to 5 basis points against an option round-trip cost of 6 to 10 basis points. A 1 to 10 day hold moves the underlying 100 to 300 basis points, so the same spread is a much smaller hurdle. Daily holds are where an indicator-driven option strategy has the best chance, and they have not been run as a full tournament in this project.

**Prior.** Low to moderate. I expect the top of the 2010-2019 ranking to be dominated by structures that are long the market or short volatility (credit put spreads, condors, long calls on dips), because 2010-2019 rewarded both. Probability that the winner passes every gate out of sample (2020 to November 2026, which contains the 2020 crash and the 2022 bear market): about 10 to 15%.

## 1. Data (frozen)
Yahoo daily bars, raw (unadjusted) open/high/low/close/volume, SPY, QQQ, IWM, 2000-05-26 to 2026-11-11 (6,655 sessions, identical calendars; no splits in the window). Cboe VIX, VXN, RVX daily history; Yahoo ^VIX3M and ^IRX (13-week T-bill yield; FRED was unreachable). Indicators use the full history for warm-up. **Option window: 2010-01-04 to 2026-11-11. Development 2010-2014 (60 months, 1,258 sessions), validation 2015-2019 (60 months, 1,258 sessions), out of sample (OOS) 2020-01-01 to 2026-11-11 (83 months, 1,725 sessions).**

## 2. Indicator universe (frozen; daily bars; every reading at day t uses data through the close of day t)
192 readings, 67 families. Exact definitions are in `src/ind.py` (hash below).

**Trend / momentum / breakout readings (bullish and bearish mirror) (91):** `PX_SMA5`, `PX_SMA10`, `PX_SMA20`, `PX_SMA50`, `PX_SMA100`, `PX_SMA200`, `SMAX_5_20`, `SMAX_10_50`, `SMAX_20_100`, `SMAX_50_200`, `EMAX_9_21`, `EMAX_12_26`, `EMAX_20_50`, `EMAX_50_200`, `MACD_SIG`, `MACD_ZERO`, `MACD_HISTUP`, `ROC5`, `ROC10`, `ROC21`, `ROC63`, `ROC126`, `ROC252`, `DON10`, `DON20`, `DONSTATE20`, `DON55`, `DONSTATE55`, `DON100`, `DMI_20`, `DMI_25`, `DMI_RISE`, `ST_10_3`, `ST_7_2`, `ST_14_4`, `PSAR`, `ICHI_CLOUD`, `ICHI_TK`, `AROON`, `AROON_70`, `KELT_B`, `BB_B`, `HA2`, `HA3`, `LRS20`, `LRS50`, `TRIX_ZERO`, `TRIX_SIG`, `KAMA_UP`, `HMA_UP`, `VORTEX`, `OBV_SMA`, `CMF`, `AD_SMA`, `FORCE13`, `HI252`, `RSI14_M60`, `RSI14_M50`, `CCI_B`, `AO_ZERO`, `AO_UP`, `KST_SIG`, `TSI_ZERO`, `ELDER`, `CHAND`, `GAP_F`, `BIG_F`, `UP3_F`, `VOLTHRUST`, `OUTSIDE`, `ENGULF`, `SOLDIERS3`, `STRONGCLOSE`, `VIX_TR`, `VIXTERM_T`, `PWHL`, `PMHL`, `PIVOT`, `ELDERRAY`, `DON5`, `ROC21_5`, `MOM12_1`, `RELSTR`, `BOND_TR`, `OVN_M`, `INTRA_M`, `HHHL3`, `FRACTAL`, `TTM_SQZ`, `RIBBON`, `VWMA20`

**Reversal / mean-reversion readings (bullish = oversold, bearish = overbought) (70):** `RSI2_5`, `RSI2_10`, `RSI2_15`, `RSI3_10`, `RSI3_20`, `RSI5_20`, `RSI5_30`, `RSI14_30`, `RSI14_35`, `CRSI_10`, `CRSI_20`, `STO_20`, `STO_X`, `WR14_10`, `WR5_10`, `CCI_R`, `CCI_R150`, `BB_R`, `BB_R10`, `KELT_R`, `IBS_10`, `IBS_20`, `IBS3_25`, `DN2`, `DN3`, `DN4`, `LOW3`, `LOW5`, `LOW7`, `LOW10`, `Z5_1.5`, `Z10_1.5`, `Z10_2.0`, `Z20_2.0`, `GAP_R`, `BIG_R`, `MFI_20`, `UO_30`, `DEM_30`, `FISHER_R`, `CMO_50`, `PCTL5`, `HAMMER`, `VIX_SPK`, `VIX_BB`, `VIX_RSI2`, `VIX_UP3`, `VIXTERM_R`, `VIX_PCT`, `RSI_DIV`, `MACD_DIV`, `CUMRSI2`, `LO252_R`, `DIST200`, `RET3_3`, `RET5_5`, `STRETCH`, `BB_R25`, `STOCHRSI`, `WVF`, `DOJI_R`, `HARAMI`, `STAR3`, `PIERCE`, `GAP_R1`, `INTRA_R`, `VOLCLIMAX`, `VIX_SPK20`, `VIX_JUMP`, `VIX_GT30`

**Neutral filters (no direction) (27):** `F_RV_LOW`, `F_RV_HIGH`, `F_VIX_LT15`, `F_VIX_15_25`, `F_VIX_GT25`, `F_ADX_LT20`, `F_ADX_GT25`, `F_VOL_HI`, `F_VOL_LO`, `F_NR7`, `F_NR4`, `F_INSIDE`, `F_WIDE`, `F_CHOP_HI`, `F_CHOP_LO`, `F_SQUEEZE`, `F_MON`, `F_TUE`, `F_WED`, `F_THU`, `F_FRI`, `F_NOVAPR`, `F_MAYOCT`, `F_ATR_HI`, `F_ATR_LO`, `F_DOM_H1`, `F_DOM_H2`

**Calendar readings (bullish only) (4):** `CAL_TOM`, `CAL_OPEXWK`, `CAL_PREHOL`, `CAL_FIRSTDAY`

**Signal sets:** all 192 singles and all 18,336 pairs = 18,528 sets. A pair is bullish when both readings are bullish and bearish when both are bearish. A neutral filter passes whatever direction its partner has. Sets made only of neutral filters (378) have no bearish side: they trade the bullish version of directional structures, and the neutral structures.

## 3. Trade rules (frozen; identical for every configuration)
| # | Rule |
| --- | --- |
| T1 | The signal is read at the close of day t and the position is opened at that close (the convention of the IBS bot: compute a few minutes before the bell) |
| T2 | Entry mode STATE: enter whenever the set's agreement is on and the ETF has no open position. Entry mode FRESH: enter only on the first day the agreement is on |
| T3 | Side rule L: bullish agreements only. S: bearish only. LS: both |
| T4 | Exit by time only, at the close 1, 2, 3, 5 or 10 sessions after entry. No stop, no target, no adjustment |
| T5 | One position per ETF at a time; a new entry is allowed at the close on which the previous position exits |

## 4. Option structures (PROXY; frozen)
| Code | Bullish version (bearish version swaps calls and puts) |
| --- | --- |
| LONG80, LONG65, LONG50, LONG30 | Long call at 0.80, 0.65, 0.50, 0.30 delta |
| DEBIT_V | Long 0.60-delta call, short 0.30-delta call |
| CREDIT_V | Short 0.30-delta put, long 0.15-delta put |
| STRADDLE (neutral) | Long call and long put at the strike nearest the close |
| CONDOR (neutral) | Short 0.20-delta put and call, long 0.10-delta put and call (iron condor) |

Expiry: first listed Friday at least 14 calendar days out for 1, 2 and 3-session holds, 21 days for 5 sessions, 35 days for 10 sessions (third-Friday monthlies only before 2012; previous session if the Friday is a holiday). Strikes on the 1-dollar grid closest to the target delta, vertical legs at least 1 dollar apart. Pricing: Black-Scholes; implied volatility of a strike = same-day index-vol close (VIX for SPY, VXN for QQQ, RVX for IWM) / 100 x clip(0.8565 - 0.240 x m, 0.60, 1.45), m = ln(K/S) / (0.8565 x index vol x sqrt(T)); this is the straight line through the two calibration points used in the earlier studies (0.949 for 0.65-delta calls, 0.764 for 0.65-delta puts). T in business days / 252; 13-week T-bill rate; dividend yields 1.6% / 0.6% / 1.2%. No early exercise. Exit priced the same way with the exit day's close and index vol.

Costs: full quoted spread per leg = 3.88 bp of the underlying price (x1.5 for QQQ and IWM) x clip(|delta| / 0.65, 0.25, 1.25), floor 1 cent, paid once per leg per round trip; 0.65 dollars commission per contract per side. Cost grid: mid (no spread, no commission), 0.25x, 0.5x, **1x (house; the level used for selection and gates)**, 2x. The delta scaling of the spread for legs other than 0.65 delta is an assumption, not a measurement.

**Unit:** return on risk per trade = net dollars / capital at risk, where capital at risk is the premium paid at mid for debit structures and (width - credit at mid) x 100 for CREDIT_V and CONDOR. The monthly series of a configuration is the sum of its trades' return on risk by entry month over the three ETFs (one unit of risk per trade); Sharpe = mean / standard deviation of that monthly series x sqrt(12), months without trades counted as zero.

## 5. Configurations and selection (mechanical; no discretion)
Configurations = 18,528 sets x 5 holds x 2 entry modes x 3 side rules x 8 structures = 4,446,720. By the count check 502,154 set-hold-mode-side combinations ever trade and **209,258 are eligible (at least 100 development, 100 validation and 120 OOS trades, 3 ETFs pooled), giving 1,674,064 eligible configurations.**
1. **Score** = min(development Sharpe, validation Sharpe) at the 1x cost. OOS data is not used.
2. **Winner (H1)** = the eligible configuration with the highest score; ties go to a single over a pair, then to the order in `run.py`.
3. **Top-10 ensemble (H2)** = walking down the ranking, the first 10 configurations whose (pair of indicator families, structure) has not already been taken; the ensemble takes every trade of all ten with equal risk per trade.
4. OOS is read once for H1 and H2. Also reported, with no confirmatory weight: the best-scoring configuration for each of the 8 structures, and the always-on baseline (roll the structure every h sessions) for each structure, hold and side.

## 6. Hypotheses, gates, labels
H1: the winner's OOS mean return on risk per trade at 1x cost is above zero. H2: the same for the ensemble. Month-cluster bootstrap (ratio estimator, B = 10,000, seed 20261112), one-sided; Holm across the two at 0.10.

| Gate | Rule |
| --- | --- |
| G1 | OOS mean > 0 and Holm-adjusted p < 0.10 |
| G2 | OOS mean > 0 at twice the house spread |
| G3 | OOS monthly Sharpe above 0.5 |
| G4 | OOS mean beats at least 95% of 1,000 random-entry runs with the same structure, hold, and number of trades per ETF, year and side |
| G5 | OOS mean > 0 for SPY and for at least one of QQQ, IWM |
| G6 | At least 120 OOS trades |
| G7 | OOS mean > 0 after removing the five best trades of each ETF |
| G8 | OOS mean > 0 in both halves (before and from 2023-06-01) |

Labels: all gates pass -> "PARTIAL (PROXY), Tier B: forward-test with real quotes" (a model-priced backtest cannot earn more than that under the project's standing rule); G6 fails -> "INCONCLUSIVE"; OOS mean negative with one-sided p (mean below zero) under 0.10 -> "NEGATIVE EXPECTANCY (PROXY)"; anything else -> "NO EDGE DEMONSTRATED (PROXY)". For the ensemble, G4 and G5 are evaluated per member and reported; the ensemble label uses G1, G2, G3, G6, G7, G8.

## 7. Also reported (descriptive, no gating weight)
Rank correlation between the selection score and the OOS Sharpe across all eligible configurations; OOS Sharpe by score decile; share of eligible configurations with a positive OOS mean at each cost level; hindsight-best OOS configuration; winner and ensemble by year, ETF, side and cost level, dollars per trade, trades per year; the winner's signal on shares 2001-07 to 2009-12 (before the option window, includes 2008) and with a next-open fill; win rate and average premium.

## 8. Not tested (stated up front: "not tested", not "no")
Real option quotes and fills (every option number is a model); indicators, parameters and timeframes outside section 2 (weekly and intraday bars, three-way combinations, machine-learned rules, discretionary chart reading); stops, profit targets, rolling and adjustments; calendars, diagonals, butterflies, ratio spreads, naked short options and 0-2 DTE; single stocks, earnings, news and order flow; early exercise and assignment; position sizing and compounding; taxes.

## 9. Verification plan
After the run: independent pure-Python re-implementation of the winner's indicators, trade list and option prices; full rerun reproduces the selection file; headline statistics recomputed from saved trades by separate code; look-ahead check repeated on the winner's readings; mirror / mutation checks. Deviations are logged in the verdict with times.

## 10. Freeze record (hashes taken before any strategy P&L was computed)

- Frozen at (UTC): 2026-11-13T02:17:14Z
- SHA-256 of the text above (sections 1-9, exactly as hashed): `0188e95c9b1b2fffb1a51ef776399f407ad6abd6b1ccc1ac209f11a2fabb8717`
- code:
  - `src/engine.py`: `1f054c27b56ddc0eb77c54d84084296ff103fb7f49707dda20a9e420ca9958fa`
  - `src/ind.py`: `906e6c31482a0d0f678431131f9c1053c867a396fdf12a2409d5520583f043c8`
  - `src/options.py`: `aa2620b98e3c056c46f9b7643fccff34c40b12b3c48dc49d4b674f883cad00b8`
  - `src/prep.py`: `b32cf041d684cf410b8be02edc97fc92f157cc333f76ee6e237a0966a879154f`
  - `src/pull.py`: `850a9c495532dcde84dd20efbb11fc3b0827e1556d575fc3b7417d7d903ba363`
  - `src/run.py`: `d5012078c4a470efd6dea0905a1028ebe1ee766269a46b6a360bb0d017103f4d`
  - `src/stats.py`: `924668c3002be8171452c552220700def04c628b2678c9d31ac992e6357dfc65`
  - `src/tests.py`: `daf7db53362db92120781bf4d7d42e6ff562f64b5e0e0be3ad817e4931751729`
- data:
  - `data/raw/DIA.csv`: `6867e5d1ca9dd39b664afdce0199b47f426bbb972085c491193e29750155a41f`
  - `data/raw/EEM.csv`: `209d172402fc9d83718331d25cf3800c157cdb95a168d9b105fdfd19229f80b3`
  - `data/raw/EFA.csv`: `5bc247016b1c5395ca7e838f0a6203d6e8a07c97c1a2006086c74611eec9bc07`
  - `data/raw/GLD.csv`: `afa351b28f3d764a8fc376cf1c96102c6f05b11716903fe7f1b4b115dde6267b`
  - `data/raw/IWM.csv`: `392d6e7232cc1b8a810d987e0fb3f9b738af9a50172bdf8ed5f69619170e225c`
  - `data/raw/QQQ.csv`: `d7e2a2d05f72a46fcaf65581dd8899853e5f6a61b7bc34db1ce27ba52253cf10`
  - `data/raw/RVX_History.csv`: `c9aa622fbc81b9408800d0b2208eb39147fd821423cd01c0bd858163174f0a7f`
  - `data/raw/SPY.csv`: `04f8ef4807734b9ef56be89b099b8adc752aa5e754a19301bd750b11c3d24242`
  - `data/raw/TLT.csv`: `ad8116bf5a2f32a828df03abf5853468c5f0948a6fb64c414e1f6f0eafbc7d85`
  - `data/raw/VIX3M_History.csv`: `5c6192a48ce614e8847377653c31cb00bb99a450f0a2348d34d409b05d331700`
  - `data/raw/VIX_History.csv`: `325e7d361a452cfeb94152f6d39ee4db28a8c0838357936b329137b61a063fc2`
  - `data/raw/VXD_History.csv`: `cc7b8dbf0a2245dfec065066a17c6e65f70aa0e0c5afa0507e5b4e64df0a7de0`
  - `data/raw/VXN_History.csv`: `1075f36a0946542b2867b37806937e57f20bb0d8cd0f16c4d04b17f127eeac9e`
  - `data/raw/^IRX.csv`: `51db3afdfe3bf045129c55366cbf9aa99a9ab1d8fa615604d92fb2fe2cf782e6`
  - `data/raw/^VIX.csv`: `b0e9f44759b9488fe4da2251fffcec076c0d52bf13245de28c6d800ea853c0fa`
  - `data/raw/^VIX3M.csv`: `6a96a69bd4bd8ec68518d50dea42a8a7227cb8af274d93f2f2f2ef343a550263`
  - `data/raw/^VXN.csv`: `69f8625debd0cc7a7200aa1a13e57c7cb1b081669b1bf80ae9f98be9bbec8ffd`
- count log `counts.log`: `cd4993f6791a75e4e4d2ae0f1e5b84c9deaef4ac7c0d056ab5abe3f4f16becc9`
