# First-install onboarding

## Installation (no account configuration edits)

Clone/download the public repository. Run `python3 scripts/install.py --target codex` or `--target claude`, or `--destination /path/to/skills`. The installer deploys eight focused skills and the shared core entry point as sibling folders. It refuses existing destinations by default; --upgrade backs up recognized copied skill folders before replacement. Symlinks and unrelated folders are never replaced. It does not touch MCP credentials or client config. Restart/reload skill discovery as required by your host. Other hosts can load `SKILL.md` directly.

Required: Python 3.9+ with a system IANA timezone database (standard on macOS/Linux) and an AI host able to call the user's licensed Webull MCP tools. Helpers use the Python standard library only. Optional: installed grill-me skill and a local browser for report inspection. The bundled interview works without external skill installs. Installing this skill does not install Webull or grant data access.

## Setup conversation

1. Discover get_stock_bars, get_stock_bars_single and get_instruments; inspect optional company/fundamental tools only if needed. If missing, ask which host is used, then have the user enable their provider-supplied Webull connection through that host. This package intentionally has no unverified endpoint or universal auth recipe.
2. Run `python3 <skill-dir>/scripts/onboard.py --workspace <absolute-private-workspace>` with a caller-selected workspace outside the skill installation and repository. It creates `onboarding.json`, `plan.json`, `project.json`, `CONTEXT.md` and `handoff.json` without overwriting existing files, checks Python and assets, and makes the workspace Git-ignored.
3. Use `references/webull.md` for a small fixed-date read-only probe. Validate actual response envelope, pagination and requested symbol. Distinguish missing tools, authentication, entitlement, no observations, pagination errors, and unsupported data coverage.
4. Save capabilities to `onboarding.json`, excluding raw payloads and secrets. Record check date, tool names, available span, adjustment/PIT limitations and any connection failure. A local Python check is not proof of MCP readiness.
5. Start the grill-me interview. Populate plan/provenance from confirmed inputs. Keep `approved=false` until the user's requirements/assumptions are agreed; routine execution then needs no repeated permission prompt.

Offline demo: `python3 scripts/demo.py --output ./demo-output` creates synthetic bars, exercises the engine and emits a standalone report. It does not call Webull and is never an empirical strategy finding.

Known limitations: the integrated adapter is US_STOCK daily USD only. Webull documents daily bars as forward-adjusted and history up to five years; entitlement and actual coverage vary. Use completed sessions. Default USD is a draft assumption; confirm cash, fees, slippage and whole-share lot size with the plan. Audit fields require supporting evidence; see the evidence-field contract in `references/webull.md`. Unknown or forward-adjusted price basis blocks an unqualified raw-price research run. A deliberately limited price-only diagnostic is possible only with the explicit plan acknowledgement and an explanation that corporate actions can distort it.
