# Command reference

## Focused skill entry points

Install the complete suite once. Use `$ask-quantcorner-webull` when unsure where to start, or invoke the specific skill directly. These are real skill folders discovered by the host, distinct from the natural-language requests for the core entry point below.

| Skill | Purpose |
|---|---|
| `ask-quantcorner-webull` | Choose the next step from the request and existing evidence. |
| `qc-webull-setup` | Prepare a private project and verify the existing Webull MCP connection. |
| `qc-webull-design-strategy` | Interview with grill-me and record the agreed research plan. |
| `qc-webull-audit-data` | Retrieve Webull data and audit coverage, timing, and price basis. |
| `qc-webull-backtest` | Run and record an approved development experiment. |
| `qc-webull-validate` | Orchestrate planned sensitivity trials and locked held-out evaluation. |
| `qc-webull-explain-results` | Explain ratios, costs, drawdown recovery and strategy behavior. |
| `qc-webull-report` | Render a standalone QuantCorner HTML report from an existing result. |

```text
$ask-quantcorner-webull Help me choose the next step. Webull MCP is already connected.
$qc-webull-setup Prepare my research workspace using my existing Webull connection.
$qc-webull-design-strategy Interview me with grill-me about my long-only strategy.
$qc-webull-audit-data Audit AAPL data for the dates in my plan.
$qc-webull-backtest Run the approved development experiment.
$qc-webull-validate Evaluate the locked candidate on the pre-specified holdout.
$qc-webull-explain-results Explain the metrics from my latest completed trial.
$qc-webull-report Create a QuantCorner report from this result.json.
```

These prompts invoke instructions; the AI host must support skill discovery or read the corresponding installed SKILL.md directly. They are not shell commands. All empirical work uses the single project registry specified in project.json.

## Legacy entry-point requests

Invoke `$quantcorner-backtesting-webull-mcp`, followed by one of the requests below. These are natural-language instructions to the agent, not registered slash commands or shell subcommands. You can add a symbol, dates, or an existing plan to make a request more specific.

| Request | What the agent does |
|---|---|
| `Show available commands` | Explain the available requests, terminal commands, required inputs, and outputs. |
| `Set up my workspace` | Check Python and bundled assets, initialize private research files, and verify the existing Webull MCP connection. Reuse an authenticated connection; only guide connection setup when it is missing. |
| `Define my strategy with grill-me` | Ask one question at a time to clarify the hypothesis, instruments, dates, trading rules, costs, and intended learning. |
| `Audit Webull data for AAPL` | Retrieve data through the connected Webull MCP and inspect schemas, pagination, coverage, calendar gaps, and corporate-action metadata. Report unresolved issues. |
| `Run the approved backtest` | Validate the agreed plan and audited data, run the experiment, and preserve its assumptions, costs, results, and trial history. |
| `Explain the performance metrics` | Interpret returns, trade statistics, costs, risk ratios, and drawdown recovery together using the chapter-14 definitions. |
| `Generate a QuantCorner report` | Create an offline HTML report with the QuantCorner logo, charts, metric explanations, provenance, and limitations. |
| `Run the synthetic demo` | Exercise the complete pipeline with generated data, without a Webull connection or claims about actual investment performance. |

Examples:

```text
$quantcorner-backtesting-webull-mcp Set up my workspace. Webull MCP is already connected.
$quantcorner-backtesting-webull-mcp Define my strategy with grill-me. Long-only US equities, daily bars.
$quantcorner-backtesting-webull-mcp Audit Webull data for AAPL from 2023-01-01 to 2025-12-31.
$quantcorner-backtesting-webull-mcp Generate a QuantCorner report from my latest completed experiment.
```

The agent calls the existing Webull MCP directly when connected; users do not need to download provider responses manually. The terminal helpers below process the private snapshots saved by the agent. English command examples do not change the conversation language: respond in the user's preferred language.

## Terminal commands

Run from the cloned skill directory. Replace example paths with your own. Research files must stay outside the public checkout. Every CLI script supports `--help`; analytics.py is an imported module. Webull tool calls happen through the AI host, not a hidden downloader in these Python scripts.

| Command | Purpose and result |
|---|---|
| `python3 scripts/install.py --target codex` | Install all eight focused skills plus the shared legacy runtime into the Codex skills directory. Use `--target claude` for Claude, or `--destination /path/to/skills` for another host. Existing installation is refused by default; --upgrade backs up recognized copied folders before replacement. Symlinks and unrelated folders are never replaced. No MCP credentials/config are changed. |
| `python3 scripts/onboard.py --workspace "$HOME/quantcorner-research"` | Create missing private `onboarding.json`, draft `plan.json`, `project.json`, `CONTEXT.md`, `handoff.json`, and workspace `.gitignore`. Preserve existing files. Local readiness does not prove Webull authentication. |
| `python3 scripts/demo.py --output "$HOME/quantcorner-demo"` | Produce synthetic `result.json`, `report.html`, and private research records. Use a fresh output folder for another demo; existing trial IDs are preserved. |
| `python3 scripts/normalize_webull.py --input /private-work/collection.json --symbol AAPL --output /private-work/data.json` | Validate a saved Webull collection manifest with exact requests/responses and normalize daily US bars/provenance. See references/webull.md for the envelope. Refuse existing output. Does not establish calendar completeness or adjusted prices. |
| `python3 scripts/research.py --data /private-work/data.json --plan /private-work/plan.json --workspace /private-work/runs --trial-id baseline-001` | Execute an agreed audited plan; save `baseline-001/plan.json`, `dataset.json`, `result.json` and append `trials.jsonl`. Reused trial IDs and previously accessed holdout windows are rejected. |
| `python3 scripts/report.py --input /private-work/runs/baseline-001/result.json --output /private-work/report.html --title "Strategy Behavior Report"` | Render the result as standalone HTML. Existing HTML at the output path is overwritten; choose a new filename to preserve earlier reports. |
| `python3 -m unittest discover -s tests -v` | Run offline deterministic tests. No licensed data or credentials are required. |

`/private-work` is a placeholder, not a required operating-system directory. Use your actual absolute workspace path. Never change audit/approval flags merely to bypass a failed gate; record the evidence and user-agreed assumptions first.

## Advanced helper

`python3 scripts/engine.py --input /private-work/bars.json --config /private-work/config.json --output /private-work/raw-result.json`

This low-level simulator expects a **bare bars array** and an **engine config object**, unlike `research.py`, which expects a dataset object (`bars` plus `provenance`) and a full plan (including `engine`). It refuses existing output. Use it for mechanic tests; empirical work uses `research.py` because the engine alone does not enforce research gates. `analytics.py` is an imported calculation module, not a CLI command.

## Reading results

Read the source/data basis and assumptions first, then compare strategy with benchmark over the same dates. Read Win Rate together with Average Win/Loss, Payoff and Expectancy. Separate filled orders from closed trades and open marks from realized P&L. Costs are already deducted. An unrecovered drawdown has unknown completed recovery/underwater duration, displayed N/A, plus its elapsed age. Report observations and remaining questions, not a binary works/does-not-work verdict.

For an update, `git pull --ff-only` updates a clean clone. Use `python3 scripts/install.py --target codex --upgrade` to replace recognized copied installations while retaining a backup; use --target claude for Claude. Unrecognized folders and symlinks are refused. Owner-managed canonical symlinks already follow canonical updates.

## Cross-skill handoff

After writing/reviewing artifacts in an existing project, record the next step:

```sh
python3 scripts/handoff.py --workspace /private-work --skill qc-webull-design-strategy --status ready --next-skill qc-webull-audit-data --artifact plan.json --artifact CONTEXT.md --note "Plan agreed; data audit is next."
```

`--artifact` is repeatable and must name an existing file relative to the project; `--next-skill` can be omitted at completion. `--status` is ready, blocked, or complete. This helper updates handoff.json and appends handoffs.jsonl; it does not approve the plan or mark the data audit passed. For research.py, use the directory recorded in project.json: new projects use /private-work/runs; migrated root-level registries use /private-work itself. The old low-level engine CLI and report CLI remain compatible.
