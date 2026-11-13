# Grand Tournament: daily-bar options strategy search (SPY / QQQ / IWM)

**Not financial advice. Research from model prices, not market quotes.**

A pre-registered search over 192 daily indicator readings (67 families), all 18,528 single and pair signal sets, 5 holding periods and 8 option structures (4.45M configurations, 1.67M with enough trades to judge). The rule was picked on 2010-2019 only and read once on 2020-01-01 to 2026-11-11.

## Result

**Label: PARTIAL (PROXY), Tier B.** Forward-test candidate, not proven and not a funded strategy.

Winner: when RSI(14) < 35 and DeMarker(14) < 0.30 at the close, buy a 0.30-delta call 2-3 weeks from expiry and sell it at the next close.

| Period | Trades | Shares, per trade | Call, % of premium per trade |
|---|---|---|---|
| 2010-2014 | 135 | +0.48% | +10.5% |
| 2015-2019 | 137 | +0.27% | +9.6% |
| 2020 to 2026-11-11 (selection-blind) | 246 | +0.52% | +17.2% (90% CI +8.2% to +28.5%) |

It passed 8 of 8 pre-registered gates. Read these before trusting it:

- **Every option price is a Black-Scholes proxy.** If real calls cost about 9% more implied volatility at entry than modelled, the option profit is zero.
- **82% of out-of-sample dollars came from 15 of 246 trades** (mostly March 2020 and April 2025). Half of all trades lose.
- **The edge is in stressed markets.** About nil when VIX < 20; IWM adds nothing since 2015.
- **Most of the universe loses:** only 25% of configurations were positive out of sample at the modelled costs.
- The underlying edge (shares, same signal) is positive in every period back to 2001. That is the part with the most support.

Full detail: [`VERDICT.md`](VERDICT.md). Frozen plan: [`PREREG.md`](PREREG.md) (hash in `freeze.json`; the hashed text is `PREREG_text_as_hashed.md`). Do not edit these files.

## Layout

| Path | What |
|---|---|
| `src/pull.py` | Downloads daily bars (Yahoo) and Cboe volatility indices |
| `src/prep.py`, `ind.py` | Data prep and the 192 indicators |
| `src/options.py` | Black-Scholes proxy pricing, costs, structures |
| `src/engine.py`, `run.py`, `stats.py` | Tournament engine, selection, bootstrap, gates |
| `src/final.py`, `robust.py`, `extras.py` | Post-selection gates and stress tests (post hoc) |
| `src/tests.py`, `verify.py` | Unit tests and an independent re-implementation |
| `results/` | JSON results, leaderboard, baselines, trade ledgers |
| `data/raw/` | Input data snapshot through 2026-11-11 |

## Run

```
pip install -r requirements.txt
python src/tests.py            # pre-freeze unit tests
python src/run.py counts       # also: full | select
python src/final.py
python src/verify.py
```

The full scan writes about 260 MB to `results/blocks/` (git-ignored). `src/pull.py` refreshes the raw data; results in this repo used the snapshot in `data/raw/`.

## Data

`data/raw/` holds Yahoo Finance and Cboe downloads for reproducibility. Check those providers' terms before redistributing, and delete the folder from a public fork if unsure.

## Next step

Shadow-forward-test on SPY and QQQ: log the real ask at the close on signal days and the real bid at the next close (0.30 and 0.80 delta). Or buy historical end-of-day option chains for the ~340 past signal dates.
