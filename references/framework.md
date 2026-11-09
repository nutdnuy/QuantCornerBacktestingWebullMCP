# Backtesting Research Framework

Purpose: understand a strategy's behavior, economic mechanism, sensitivities, failure modes, and uncertainty. A backtest is an experiment, not an automatic approval to deploy capital or a binary verdict that a strategy works forever.

This framework is an original synthesis of Arnott, Harvey & Markowitz (2018) and Deutsche Bank (2014). AI-agent roles, the reproducibility bundle, engine checks, and version-control mechanics are practical additions, not verbatim recommendations or a diagram copied from either paper.

## 1. Define the research question

**Owner:** human; Agent helps formalize it.

- State the economic or behavioral mechanism before looking for a favorable result.
- State what behavior is expected, when the mechanism may be weak, and which observations would challenge the explanation.
- Identify what the experiment is designed to learn. Do not set “find parameters with the highest backtest return” as the sole objective.
- Exploratory findings are allowed, but mark hypotheses discovered after seeing data as exploratory; they require new evidence.

**Output:** versioned hypothesis and intended learning, with criteria for reviewing the hypothesis.

## 2. Freeze an experiment plan

**Owner:** human chooses scope; Agent records the specification.

Specify the historical universe, instruments, signal, information availability, rebalance/execution rules, benchmark, exposure constraints, financing assumptions, costs, and sample dates. Choose time-ordered development and held-out evaluation windows before inspecting their results. Define planned robustness checks and metrics. Any scaling, normalization, or parameter estimation must use only information available at that point; overlapping feature/label windows require an explicit split design to avoid leakage.

Cost assumptions must be supplied or documented as assumptions, not silently fabricated by an Agent. Plan sensitivity scenarios where estimates are uncertain. Do not promise one universal train/test ratio or a universal Sharpe threshold: these depend on horizon, data volume, and the research question.

**Output:** immutable plan version, data split, execution specification, and initial trial record.

## 3. Pass the data and engine integrity gate

**Owner:** Agent checks and reports; human reviews exceptions.

Check:

- Historical constituents, delistings, and unavailable or failed securities; do not substitute today's universe for the historical universe.
- Point-in-time information, publication lags, revisions, timestamps, and corporate actions. Keep signal data conventions consistent with executable prices and cash-flow accounting.
- Signal availability before order/fill timing. A signal calculated from the close does not automatically justify a fill at that same close.
- Missing observations, duplicates, time zones/calendars, and outliers. Distinguish bad data from genuine extreme events; record treatment rather than deleting inconvenient observations.
- Basic engine consistency: simple hand-checkable trades, cash/position accounting, fees, and a no-trade case. Validate the mechanics before interpreting any performance result.
- Execution constraints, including liquidity, turnover, board lots and available cash. This package is long-only; short availability and borrowing are outside its supported scope.

**Gate:** if invalid, stop interpretation; correct the data or engine, record the reason and affected runs, then repeat the audit. Good-looking returns do not override an invalid gate. If a defect is discovered after holdout inspection, disclose that fact and re-assess whether the evaluation remains independent.

**Output:** data/engine audit and reproducible data snapshot identifiers; unresolved material defects block progression.

## 4. Develop and study behavior

**Owner:** Agent runs the approved plan; human reviews interpretation and proposed changes.

- Start with a simple baseline and a relevant benchmark.
- Study parameter sensitivity without silently selecting only the peak; preserve the complete set of planned trials and failed runs.
- Examine behavior across pre-specified periods/conditions, costs, turnover, exposures, drawdowns/recovery, concentration, outlier dependence, and time invested versus cash.
- Use the planned development validation method. Do not use the final held-out evaluation window to choose parameters or preprocessing.
- Describe uncertainty and sample limitations. Do not treat all trades or adjacent observations as independent, or a favorable result from many correlated trials as a single unselected test.
- Any expanded search or revised hypothesis becomes an explicit plan version; the complete search history stays visible. Record comparisons and transformations, not just the final model.

**Development loop:** step 4 → step 2 (or step 1 if the question changes) → integrity check → new trial. All of this uses development information only.

**Output:** behavior profile, robustness comparisons, and complete trial log. A negative or inconclusive finding is a valid research output.

## 5. Lock the candidate and evaluate held-out data

**Owner:** human locks the candidate and plan; Agent evaluates the locked version.

Record code/config/data versions before opening the final held-out evaluation. Run the pre-specified evaluation, report every planned result, and compare it with the expected behavior. “One evaluation” means one pre-specified assessment of a locked candidate, not an arbitrary prohibition on multiple pre-planned diagnostics.

If the result is used to modify the strategy, the prior holdout becomes development information. Any revised candidate requires newly independent evidence, potentially future observations. Renaming or resplitting a previously inspected period does not restore independence. Historical holdouts also are not perfectly independent of a researcher's prior knowledge of history.

Do not iterate until this window passes. Do not interpret disappointing held-out performance as an instruction to fit it away.

**Output:** held-out evaluation report, contamination disclosure, and uncertainty/limitations.

## 6. Report understanding and observe new data

**Owner:** human interprets and decides the next research action; Agent reproduces, summarizes, and monitors to the specified plan.

The report should answer:

1. What did we learn about the proposed mechanism?
2. In which conditions did the strategy benefit or struggle, and how strong is the evidence?
3. How much do costs, turnover, position sizing, parameter choices, and particular observations affect that description?
4. Which findings contradict the hypothesis or remain uncertain?
5. What new information would justify changing the conclusion?

Possible next steps are further research with a new version, shelving the idea, or forward/paper observation under a defined monitoring plan. Paper observation tests operational behavior but does not reproduce all live execution conditions. A backtest or paper test is not an automatic permission to deploy funds.

**New research loop:** step 6 → step 1/2. Keep the old report, explain why the question/version changes, and track which data are already contaminated by earlier investigation.

**Output:** an evidence-linked behavior report and next-step decision; optional forward monitoring with predefined review triggers and a log of subsequent changes.

## Minimum reproducibility bundle

The helper stores the canonical runtime plan as `plan.json`, events as `trials.jsonl`, and trial outputs as `<trial-id>/result.json`. Keep the input dataset privately alongside its provenance/hash. The agent also authors `hypothesis.md`, `data-audit.md`, `behavior-report.md`, and (when relevant) `holdout-report.md`; the helpers do not fabricate these narrative findings. Suggested additional fields for every trial:

- `experiment_id`, `parent_id`, `hypothesis_version`, `plan_version`
- code/config version, data snapshot ID, sample dates and split role
- parameter/transformation changes and the reason for them
- execution, cost, and long-only exposure assumptions
- success/failure status, warnings, and all output artifact paths
- whether holdout data were accessed, when, and whether they influenced later choices

Agent behavior: run within the recorded plan, retain unfavorable results and errors, propose rather than silently enact material scope changes, and identify missing assumptions. Human behavior: own the research question, interpret exceptions, and judge the evidence rather than reward only attractive returns.

## Coverage of the Seven Sins

| Original category | Main control |
|---|---|
| Survivorship bias | Point-in-time historical universe and delisting audit in step 3 |
| Look-ahead bias | Information timing, split design, and signal/fill alignment in steps 2–3 |
| Storytelling | Ex-ante hypothesis and explicit exploratory labels in steps 1 and 6 |
| Data mining / snooping | Full trial history, versioned changes, development-only tuning, held-out evaluation in steps 2, 4–5 |
| Signal decay / turnover | Pre-specified execution/cost assumptions and sensitivity analysis in steps 2–4 |
| Outliers | Documented data treatment and dependence checks in steps 3–4 |
| Asymmetric payoff / shorting costs | Long-only scope enforced; short availability and borrow costs are not modeled |

## Sources

- Arnott, R., Harvey, C. R., & Markowitz, H. (2018), *A Backtesting Protocol in the Era of Machine Learning*, version October 29, 2018. Research Motivation pp. 8–9; Multiple Testing pp. 9–10; Sample Choice and Data pp. 10–11; Cross-Validation pp. 11–12; Model Dynamics pp. 12–13; Model Complexity pp. 13–14; Research Culture p. 14; Conclusions p. 15. https://ssrn.com/abstract=3275654
- Deutsche Bank Markets Research (2014), *Seven Sins of Quantitative Investing*, September 8, 2014. Seven categories summarized on p. 3, discussed on pp. 5–39. https://hudsonthames.org/wp-content/uploads/2022/01/DB-201409-Seven_Sins_of_Quantitative_Investing.pdf


## Runtime boundaries
The bundled engine is single-asset, daily, long-only. No shorting or leverage. Multi-stock portfolio research requires a separately validated allocator and historical universe; do not imply it is built in. Use the local state wrapper for a timestamped record of trial and held-out access. This is an auditable convention, not a tamper-proof security barrier.
