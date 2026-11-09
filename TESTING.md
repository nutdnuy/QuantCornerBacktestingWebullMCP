# Verification evidence

Webull edition 0.1.0, checked 2026-11-09. The upstream Efin test history is not evidence of Webull behavior; this file records checks actually run for this edition.

## Automated verification

Run from the checkout:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/demo.py --output /tmp/quantcorner-webull-demo
```

Coverage includes the inherited long-only engine, next-open causality, future-data perturbation, fees/slippage and affordability, lot rounding, zero-volume fills, drawdown/recovery, trade metrics, reconciliation, audit gates, held-out access reservation, failed runs, locking, report escaping and portability. The suite installer tests fresh installs, upgrades with backups, refusal of symlinks/unknown destinations, rollback and cross-skill handoffs.

Webull-specific tests use synthetic formatted responses. They cover MCP text/structured envelopes, multi-symbol selection, multiple pages, timezone/DST conversion, hashes, overlap, missing symbols, malformed/truncated/nonfinite/inconsistent prices, currency/category/frequency mismatch, millisecond bounds, request counts and session consistency. Missing completeness is preserved as unresolved. Research refuses missing collection/calendar evidence and labels unknown or adjusted prices as limited diagnostics unless the raw-price/no-action contract is supported.

The coexistence check installs all nine Webull entries beside existing Efin-name folders and verifies that those folders are unchanged. The bundled public report is regenerated from the synthetic demo in USD with one-share rounding. No live payload is included in it.

GitHub Actions runs the tests and synthetic demo on Python 3.9 and 3.12. Local results and remote CI status are separate observations; inspect the Actions run for the published commit.

## Live Webull smoke checks

An existing authenticated host was used for read-only market-data calls:

- `get_stock_bars_single`: three recent daily AAPL bars returned in the observed formatted-text envelope.
- `get_stock_bars`: AAPL and MSFT, requested 2025-01-02 through 2025-01-10; count 3 returned the newest three bars per symbol.
- Backward paging with `end_time` set to the earliest returned timestamp minus 1 ms returned three earlier bars per symbol, without duplicate session dates.
- The new normalizer produced six sorted rows per symbol, from 2025-01-02 through 2025-01-10. Both paged results matched the count-200 request exactly after normalization.
- `collection_complete` remained false in these smoke artifacts: a small retrieval comparison is not a full calendar/corporate-action audit or evidence of investment performance.

Licensed payloads were kept in a local temporary directory outside the package. No account, balance, position, order, preview or trading tool was called. New-account authorization, every entitlement/market, five-year coverage, fundamental publication timing and live execution were not tested. No empirical strategy claim is made.

## Skill validation limits

Frontmatter/name checks, local links, suite manifest, installed entry points and canonical Codex symlinks are checked separately from code tests. These are structural and integration checks. No independent model-behavior evaluation or measured improvement in strategy research is claimed. The report layout is inherited; this edition does not claim a new visual design review.
