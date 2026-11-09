# Read ratios as a behavior profile

Use the metrics together; do not declare that a strategy works because one ratio crosses a fixed threshold. Compare identical samples, units, execution assumptions and price bases. Inspect the full paths and the number of observations first.

| Metric | What it helps explain | What can mislead |
|---|---|---|
| Sample return / CAGR | Capital growth over the observed period; calendar-time annualization | Short samples, endpoint choice, omitted dividends, and annualizing exceptional periods |
| Volatility | Dispersion of daily portfolio returns | Treats upside and downside alike; square-root annualization is a convention, not proof of independence |
| Maximum drawdown | Worst observed peak-to-trough loss | Depends on the observed sample; daily marks omit intraday extremes; not the worst loss possible |
| Underwater path | Depth and persistence below prior peaks | A single maximum hides long recovery periods; unrecovered drawdowns are censored |
| Sharpe | Mean return above specified risk-free rate per unit of total volatility | Serial dependence, non-normal returns, short samples and many tested variants |
| Sortino | Mean return above the specified target per unit of downside deviation | The target and downside denominator conventions matter; no downside does not prove no risk |
| Win rate + payoff | How often closed trades win and their average gain/loss balance | A high win rate can coexist with large rare losses; variable position size affects P&L ratios |
| Expectancy / closed trade | Mean realized net P&L in account currency | Not a normalized return; excludes current open-position P&L |
| Profit factor | Total winning net P&L divided by absolute losing net P&L | A few outcomes dominate; no losses produces N/A, not a safe or infinite-quality strategy |
| Closed trades | How much realized trade evidence exists | Trades are not necessarily independent; open trades still affect equity |

The bundled engine computes sample return, CAGR, volatility, drawdown, Sharpe, Sortino, win rate, payoff, expectancy, profit factor and closed-trade count. The report computes numeric drawdown/recovery/underwater durations, dates and censoring status. Exposure, turnover, concentration, regime breakdowns and sensitivity studies should be calculated from retained ledgers through separately checked analysis when required by the question, and reported as unavailable until computed. Never invent missing metrics or auto-label market regimes retrospectively.

## Definitions in this implementation

Daily return is current marked equity / preceding marked equity − 1, including the initial cash-to-first-mark return. Volatility uses sample standard deviation and the configured periods per year (default252). Sharpe uses geometric conversion of the annual risk-free rate to a daily rate, then annualizes the mean daily excess / daily standard deviation. Sortino uses the configured minimum acceptable return and root mean square downside across **all** periods, including zero downside on periods above the target. The assumed risk-free rate is a comparison threshold; cash earns no interest in this engine.

CAGR uses elapsed calendar days /365.25 and the recorded initial date. Drawdown includes initial capital in the running peak. Closed-trade P&L is after modeled fees and slippage; open mark-to-market is reconciled separately. The same-asset benchmark uses the same starting capital, lot constraint, costs and liquidation policy. Benchmark trade ratios can therefore be N/A when there are no closed positions.

Read [the QuantCorner evaluation chapter](https://www.quant-corner.com/library/robo-trade-notes/chapter-14.html) for the workshop context; the exact implementation definitions above are governed by this package's code and tests.

## Chapter 14 coverage

[QuantCorner chapter14](https://www.quant-corner.com/library/robo-trade-notes/chapter-14.html) was checked on2026-11-05. Existing Total Return, CAGR, Sharpe, Sortino, volatility, MDD, Win Rate, Payoff, Expectancy and Profit Factor remain. Additional fields:

| Fields | Definition and purpose |
|---|---|
| Winning / losing / breakeven trades and rates | Count net P&L above / below / equal to zero. Each rate divides by ALL closed trades; the three rates sum to1 when trades exist. |
| Average Win / Average Loss | Mean gain of winners and positive mean loss magnitude of losers; N/A if that group is absent. Read trade size alongside these money amounts. |
| Breakeven win rate | 1/(1+Payoff), only for a sample with both groups and no flat trades. A descriptive threshold under unchanged payoff, not a forecast. |
| Mean daily / annualized arithmetic return | Mean of all daily returns, and that mean × periods/year; neither is CAGR. |
| Daily volatility / downside deviation | Sample SD and RMS downside relative to daily MAR across all observations, including cash days. |
| Filled orders, fees, modeled slippage | Count fills, distinguish them from round trips. Include entry costs of open positions; costs are already in equity. |
| Closed gross P&L / closed costs / closed net P&L | For actual executed quantities, gross reference-price P&L − fees − modeled slippage = realized net P&L. This is not a rerun with different position sizes and no costs. Open position marks remain separate. |
| MDD drawdown / recovery / underwater periods | Peak→trough, trough→recovered peak, peak→recovered peak. Count observed session intervals, excluding a duplicate start day; holidays are not inserted. Recovery and complete underwater durations are N/A until recovery. |
| Longest completed / longest observed underwater | Distinguish completed episodes from elapsed durations including unresolved episodes. The deepest episode need not be the longest. |
| Current underwater age | Intervals since latest peak as of last observation; zero when at the peak. |
| Recovery return required | Peak/trough−1 for the worst episode; a20% drawdown needs25% recovery from its trough. |

Initial capital is session0, preceding the first evaluated mark. Equal highs reset the peak date; equal-depth worst episodes select the first. Worst-episode dates/status and current unresolved episode are retained for both strategy and benchmark. Missing calendar sessions must be audited upstream; durations describe supplied observations. No drawdowns means no episode and N/A episode durations. No losses means Profit Factor N/A, not infinity.

The chapter explicitly does not cover Alpha or Value at Risk; this update does not fabricate them or copy its SPY/EMA results into Webull research. The reference strategy remains SMA or supplied targets; adding ratios does not silently switch it to the chapter's EMA example.
