# QuantCornerBacktestingWebullMCP

A portable **suite of eight focused AI skills** for understanding long-only strategy behavior with Webull MCP. The `quantcorner-backtesting-webull-mcp` core entry point owns the shared engine, metrics, gates and branded report assets. Install once to get all **nine discoverable entry points**.

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

Start with:

```text
$ask-quantcorner-webull I have Webull MCP connected and want to understand my long-only strategy.
```

Or invoke a focused skill directly, for example `$qc-webull-report Generate a report from this result.json`. English skill names do not restrict the conversation language.

Derived from [QuantCornerBacktestingEfinMCP](https://github.com/nutdnuy/QuantCornerBacktestingEfinMCP), preserving its research workflow. All entry-point names are distinct, so both suites can coexist. This package is an AI skill suite, not a Webull MCP server.

## Install

```sh
git clone https://github.com/nutdnuy/QuantCornerBacktestingWebullMCP.git
cd QuantCornerBacktestingWebullMCP
python3 scripts/install.py --target codex  # installs the complete suite
# or: python3 scripts/install.py --target claude
```

Reload skill discovery in your host after installation. For a previous copied installation, pull the updated repository and run `python3 scripts/install.py --target codex --upgrade` (or `--target claude`). Upgrades retain previous folders under `.quantcorner-backups/<id>/` in the selected skills directory; inspect backups for any local customizations. Unrecognized folders and symlinks are preserved/refused. Canonical symlink users update the canonical sources and links instead. `--destination /path/to/skills` supports other clients; load each installed SKILL.md using that client's supported mechanism.

The display/repository name is **QuantCornerBacktestingWebullMCP**. The portable skill slug is `quantcorner-backtesting-webull-mcp` (lowercase skill naming convention).

Invoke `$quantcorner-backtesting-webull-mcp Set up my workspace. Webull MCP is already connected.` The agent reuses your existing connection and asks only for missing setup or research details.

Python 3.9+ with a system IANA timezone database (standard on macOS/Linux); no pip dependencies. Webull must already be connected in your AI host using your own licensed account. The installer never reads secrets or edits MCP configuration. Missing grill-me? The skill discloses and uses its bundled equivalent interview protocol; no extra dependency is needed. Read [onboarding](references/onboarding.md).

## Commands and usage

Read the [command reference with examples](references/commands.md) for agent requests and terminal commands, including each command's purpose, input format, and output files.

Start with `$quantcorner-backtesting-webull-mcp Show available commands`, or use `Define my strategy with grill-me`, `Audit Webull data for AAPL`, `Run the approved backtest`, `Explain the performance metrics`, `Generate a QuantCorner report`, or `Run the synthetic demo`.

Version 0.1.0 adapts the Efin suite to Webull: a verified tool map, a dedicated daily-bar normalizer, USD defaults and distinct skill names for side-by-side installation. It retains the shared engine, research gates, trade statistics and reports. See [metric definitions and interpretation](references/metrics.md).

## Try without Webull

```sh
python3 scripts/demo.py --output /tmp/quantcorner-demo
python3 -m unittest discover -s tests -v
```

Open `report.html` in that output directory. The demo is **synthetic**, not an investment result. Reports are a single offline HTML with embedded fonts/logo, equity and drawdown, metric definitions and visible assumptions. Share the package freely; sharing licensed Webull data requires separate rights.

## Research workflow

`ask-quantcorner-webull` routes into setup → strategy design → data audit → development → validation → explanation → report, skipping stages whose evidence already exists. All stages share one private project and use its configured trial registry. CONTEXT.md retains decisions, plan.json defines the experiment, and handoff.json points to the next step and exact artifacts. See the [shared suite contract](references/suite.md).

Question → plan → data/engine audit → development experiments → locked held-out evaluation → behavior report. Preserve all experiments, including poor outcomes. Once a holdout influences revisions, it is development data and requires new evidence for confirmation.

```mermaid
flowchart LR
 Q[Understand behavior] --> P[Freeze plan]
 P --> A[Audit data and timing]
 A --> D[Development experiments]
 D --> L[Lock candidate]
 L --> H[Unseen evaluation]
 H --> R[Explain behavior and limits]
 D -->|New version, record every trial| P
```

The bundled reference engine supports a **single stock, daily, long-only** SMA crossover or supplied 0/1 targets, next-open execution, fees/slippage, board-lot rounding and same-asset buy/hold comparison. It is not a multi-stock factor portfolio engine, walk-forward optimizer, live broker or automatic corporate-action processor. No short selling, leverage or order placement.

The adapter supports US stocks/ETFs with daily USD bars. Webull documents daily bars as forward-adjusted; the engine treats these as a limited price-series diagnostic requiring explicit acknowledgement, not executable raw-price or dividend-inclusive total-return evidence. Current instruments and financial statements do not establish historical index membership or point-in-time fundamentals. See [Webull adapter](references/webull.md) and [framework](references/framework.md).

## Example report

The [standalone synthetic example](examples/report.html) can be downloaded and opened offline. The interview and narrative response follow the user’s language; fixed report labels are English, with Thai fonts embedded for user-provided titles and notes.

## Files and privacy

Keep research workspaces outside the repository. Plans, trial logs and provider data remain local. The public example report uses generated data only. Never commit MCP settings, API keys, downloaded histories or reports containing licensed data. All paths are relative to the installation or caller-selected workspace.

Code/instructions: MIT. QuantCorner logo: separate limited brand permission in [ASSETS_LICENSE.md](ASSETS_LICENSE.md). Fonts: their bundled OFL licenses. Do not claim brand endorsement of a strategy. [Sources](references/sources.md) and [test evidence](TESTING.md).
