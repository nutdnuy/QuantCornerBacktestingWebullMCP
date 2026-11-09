# Webull MCP adapter

Tool schemas and live text envelopes checked on 2026-11-09. Discover the current host's tools before use; namespace prefixes vary. The implemented normalizer supports **US_STOCK daily stock/ETF bars, USD, America/New_York**. Other markets and intraday strategies require a validated adapter and engine extension.

## Tools and boundaries

| Purpose | Actual tool suffix | Boundary |
|---|---|---|
| Batch OHLCV | `get_stock_bars` | Comma-separated `symbols`; per-symbol coverage must be checked |
| Single-symbol OHLCV | `get_stock_bars_single` | Uses `symbol`, not `symbols` |
| Instrument metadata | `get_instruments` | Current metadata; not historical index membership |
| Current quotes | `get_stock_snapshot`, `get_stock_quotes` | Not historical bars or past execution evidence |
| Fundamentals | `get_income_statement`, `get_balance_sheet`, `get_cash_flow`, `get_financial_indicators` | Fiscal period/end date is not the publication date; do not infer point-in-time availability |
| Company context | `get_company_profile` | Current context, not an auditable historical universe |

The connected tool inventory did not expose a historical index-constituent service or a dedicated split/dividend history tool. Do not invent an Efin-equivalent benefits endpoint. External corporate-action evidence must be identified separately when needed. This workflow uses market data only; account access, order preview, placement, replacement and cancellation are unnecessary and outside its scope.

## Read-only probe and acquisition

A small request accepted by the connected MCP:

```json
{"symbols":"AAPL,MSFT","category":"US_STOCK","timespan":"D","count":3,"start_time":1735776000000,"end_time":1736553600000,"real_time_required":false}
```

`get_stock_bars_single` accepts the same fields with `symbol: "AAPL"`. `start_time` and `end_time` are Unix **milliseconds**. `count` limits recent bars; it does not guarantee the complete requested interval. Inspect current limits/entitlements rather than inheriting Efin's ten-year or cursor rules. The [current Webull bars reference](https://developer.webull.com/apis/docs/reference/historical-bars/) documents daily history up to five years, minute history up to 180 days, and daily-or-longer bars as forward-adjusted. These are provider documentation limits, not proof of any particular account's delivered coverage.

For longer windows, keep the symbol/category/timespan/session settings stable and move `end_time` backward to the earliest returned timestamp minus 1 ms. Check strict progress, overlap and gaps; stop on repeated pages or provider errors. Batch symbols can have different histories, so continue each missing symbol separately. A short or empty page alone does not prove completeness. Check the requested span including warmup against an exchange calendar, listing/delisting dates and entitlement limits. Do not repeatedly retry authentication or entitlement errors unchanged.

Use completed daily sessions only. `real_time_required=false` alone is not proof that today's daily bar is final. Record explicit date bounds and inspect timestamps in the exchange timezone with DST; do not use the computer's local date. Missing sessions are not zero returns. Zero volume is retained for audit, not treated as a fill opportunity. Never append a current snapshot as a historical daily bar.

## Saved response contract

Observed responses contain formatted text in `structuredContent.result` and/or a single `content[].text` block. This is **not JSON OHLCV in `data.data`**. Text has a `=== Stock Bars (OHLCV) ===` header, `--- SYMBOL ---` sections and rows such as the synthetic example below:

```text
=== Stock Bars (OHLCV) ===
  --- SYNTHETIC ---
  2025-01-02T05:00:00.000+0000  O: 10  H: 12  L: 9  C: 11  Vol: 1000
```

Save each exact response together with its exact request. Use this collection envelope (replace the placeholder response with the complete tool return):

```json
{
  "schema_version": 1,
  "provider": "webull",
  "category": "US_STOCK",
  "currency": "USD",
  "exchange_timezone": "America/New_York",
  "timespan": "D",
  "requested_start": "2025-01-02",
  "requested_end": "2025-01-10",
  "collection_complete": false,
  "collection_evidence": "",
  "pages": [{
    "request": {"symbol":"AAPL","category":"US_STOCK","timespan":"D","count":200,"start_time":1735776000000,"end_time":1736553600000,"real_time_required":false},
    "response": "REPLACE_WITH_COMPLETE_TOOL_RESPONSE"
  }]
}
```

Run `python3 scripts/normalize_webull.py --input /private-work/collection.json --symbol AAPL --output /private-work/data.json`. Save one normalized file per symbol. Batch retrieval does not make the bundled engine a portfolio engine.

The helper validates symbol selection, request bounds, daily market/currency contract, timezone conversion, numeric/OHLC consistency and duplicate dates. It sorts bars and hashes the original collection and normalized rows. It rejects malformed/truncated rows rather than silently dropping or repairing them. It does not fill missing sessions, deduplicate conflicting prices, fetch data, or infer request completeness. Format changes require inspection and a tested parser update. Full licensed responses stay private; test fixtures are synthetic.

## Evidence required by the runner

Audit fields are operator attestations backed by reviewable evidence. The parser leaves audit statuses unresolved. Never set flags simply to bypass a gate.

- `collection_complete=true` with `collection_evidence`: collection range, per-symbol paging progress and any documented exclusions. No Webull `has_more`, cursor or `total_count` was present in the observed text.
- `calendar_audit="passed"` with `calendar_audit_evidence`: requested span including warmup, checked exchange sessions, completed bars and gap resolution.
- `price_basis` with `price_basis_evidence`: confirm the connected endpoint against current provider documentation. Daily bars are documented as forward-adjusted; record `forward_adjusted` when applicable. The normalizer starts at `unknown` because the text itself does not declare the basis.
- For qualified raw-price execution: `corporate_actions="audited"`, `corporate_action_policy="no_actions_in_window"` and `corporate_actions_evidence`, plus documented raw/unadjusted basis for the entire input window.

The inherited reference engine does not book splits, share changes or cash dividends. **Forward-adjusted daily Webull bars therefore require `price_only_diagnostic_acknowledged=true`** and remain a limited price-series diagnostic, even after the basis is documented. Do not describe adjusted OHLC as actual executable historical prices or add dividend cash flows a second time. Corporate-action accounting requires a separately implemented and tested engine.

The runner checks `bars_sha256`, count/range, symbol, currency and required evidence. Altering bars or adding target signals requires a new documented derived snapshot with a new hash and parent provenance. All trials for one research project share one registry; a new folder does not restore holdout independence.
