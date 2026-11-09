"""Normalize saved Webull MCP daily-bar collections, without inferring completeness."""
import argparse
import hashlib
import json
import math
import re
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def iso_day(value):
    if not isinstance(value, str) or date.fromisoformat(value).isoformat() != value:
        raise ValueError('Expected ISO YYYY-MM-DD date')
    return value


def response_text(payload):
    if isinstance(payload, str):
        return payload
    if not isinstance(payload, dict) or payload.get('isError'):
        raise ValueError('Invalid response or provider error')
    structured = payload.get('structuredContent', payload)
    if isinstance(structured, dict) and structured.get('isError'):
        raise ValueError('Provider error')
    result = structured.get('result') if isinstance(structured, dict) else None
    blocks = payload.get('content')
    if blocks is not None:
        if (not isinstance(blocks, list) or len(blocks) != 1
                or not isinstance(blocks[0], dict) or blocks[0].get('type') != 'text'
                or not isinstance(blocks[0].get('text'), str)):
            raise ValueError('Ambiguous MCP text envelope')
        if result is not None and result != blocks[0]['text']:
            raise ValueError('Conflicting MCP text and structured result')
        result = blocks[0]['text']
    if not isinstance(result, str):
        raise ValueError('Expected Webull formatted result text; inspect changed schema')
    return result


ROW = re.compile(r'(\S+)\s+O:\s*(\S+)\s+H:\s*(\S+)\s+L:\s*(\S+)\s+C:\s*(\S+)\s+Vol:\s*(\S+)')
SECTION = re.compile(r'---\s+(\S+)\s+---')


def parse_page(payload, symbol, exchange_timezone):
    text = response_text(payload)
    header = '=== Stock Bars (OHLCV) ==='
    if text.count(header) != 1:
        raise ValueError('Missing/ambiguous bars header; provider error or unsupported response')
    prefix, body = text.split(header)
    if re.search(r'\berror\b|\bfailed\b|\bmock\b', prefix, re.I):
        raise ValueError('Provider error/mock marker')
    current, sections, rows = None, set(), []
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        section = SECTION.fullmatch(line)
        if section:
            current = section[1]
            if current in sections:
                raise ValueError('Repeated symbol section')
            sections.add(current)
            continue
        match = ROW.fullmatch(line)
        if not match or current is None:
            raise ValueError('Malformed/truncated bar row or missing symbol section')
        if current != symbol:
            continue
        timestamp = re.sub(r'([+-]\d{2})(\d{2})$', r'\1:\2', match[1].replace('Z', '+00:00'))
        stamp = datetime.fromisoformat(timestamp)
        if stamp.tzinfo is None:
            raise ValueError('Timestamp must include timezone')
        local = stamp.astimezone(ZoneInfo(exchange_timezone))
        bar = {'date': local.date().isoformat()}
        for field, raw in zip(('open', 'high', 'low', 'close', 'volume'), match.groups()[1:]):
            value = float(raw)
            if not math.isfinite(value) or value < 0 or (field != 'volume' and value == 0):
                raise ValueError('Invalid ' + field)
            bar[field] = value
        if not bar['low'] <= min(bar['open'], bar['close']) <= max(bar['open'], bar['close']) <= bar['high']:
            raise ValueError('Inconsistent OHLC; audit source, do not repair prices silently')
        rows.append((int(stamp.timestamp() * 1000), bar))
    if symbol not in sections or not rows:
        raise ValueError('Requested symbol missing or empty')
    return rows


def normalize(collection, symbol):
    if not isinstance(symbol, str) or not symbol.strip():
        raise ValueError('Symbol must be a nonempty string')
    symbol = symbol.strip().upper()
    if not isinstance(collection, dict) or collection.get('schema_version') != 1 or collection.get('provider') != 'webull':
        raise ValueError('Expected schema_version=1 Webull collection manifest')
    # Only this market has been integrated and smoke-tested. Other categories
    # need their currency, session-date and calendar contracts validated first.
    if (collection.get('category') != 'US_STOCK' or collection.get('currency') != 'USD'
            or collection.get('exchange_timezone') != 'America/New_York'
            or collection.get('timespan') != 'D'):
        raise ValueError('This adapter supports US_STOCK daily bars in USD / America/New_York')
    start, end = iso_day(collection.get('requested_start')), iso_day(collection.get('requested_end'))
    if start > end:
        raise ValueError('Inverted requested window')
    complete = collection.get('collection_complete', False)
    evidence = collection.get('collection_evidence', '')
    if type(complete) is not bool or not isinstance(evidence, str) or (complete and not evidence.strip()):
        raise ValueError('Collection completeness requires explicit collection evidence')
    pages = collection.get('pages')
    if not isinstance(pages, list) or not pages:
        raise ValueError('Pages must be a nonempty array')
    bars, seen, requests = [], set(), []
    sessions = set()
    for page in pages:
        if not isinstance(page, dict) or not isinstance(page.get('request'), dict):
            raise ValueError('Every page requires original request and response')
        req = page['request']
        if 'symbol' in req and 'symbols' in req:
            raise ValueError('Use symbol or symbols, not both')
        names = req.get('symbols', req.get('symbol'))
        if not isinstance(names, str) or symbol not in [s.strip() for s in names.split(',')]:
            raise ValueError('Request does not include selected symbol')
        if req.get('category') != 'US_STOCK' or req.get('timespan') != 'D' or req.get('real_time_required') is not False:
            raise ValueError('Record explicit US_STOCK, D, real_time_required=false request')
        count = req.get('count')
        if type(count) is not int or count < 1:
            raise ValueError('Invalid request count')
        for key in ('start_time', 'end_time'):
            value = req.get(key)
            if value is not None and (type(value) is not int or not 100_000_000_000 <= value <= 9_999_999_999_999):
                raise ValueError(key + ' must be a Unix timestamp in milliseconds')
        if req.get('start_time') is not None and req.get('end_time') is not None and req['start_time'] > req['end_time']:
            raise ValueError('Inverted request timestamps')
        session = req.get('trading_sessions')
        if session is not None and not isinstance(session, str):
            raise ValueError('Invalid trading_sessions')
        sessions.add(session)
        rows = parse_page(page.get('response'), symbol, collection['exchange_timezone'])
        if len(rows) > count:
            raise ValueError('Response exceeds requested count')
        for stamp, bar in rows:
            if (req.get('start_time') is not None and stamp < req['start_time']) or (req.get('end_time') is not None and stamp > req['end_time']):
                raise ValueError('Response lies outside recorded request bounds')
            day = bar['date']
            if not start <= day <= end:
                raise ValueError('Bar outside requested session dates; audit collection bounds')
            if day in seen:
                raise ValueError('Duplicate date across pages; audit overlap before normalizing')
            seen.add(day)
            bars.append(bar)
        requests.append(req)
    if len(sessions) != 1:
        raise ValueError('Inconsistent trading sessions across pages')
    bars.sort(key=lambda bar: bar['date'])
    return {'bars': bars, 'provenance': {
        'data_kind': 'webull', 'symbol': symbol, 'source': 'Webull MCP historical stock bars',
        'currency': 'USD', 'category': 'US_STOCK', 'timespan': 'D',
        'exchange_timezone': 'America/New_York', 'price_basis': 'unknown',
        'collection_complete': complete, 'collection_evidence': evidence,
        'calendar_audit': 'not_performed', 'corporate_actions': 'not_audited',
        'requested_start': start, 'requested_end': end,
        'actual_start': bars[0]['date'], 'actual_end': bars[-1]['date'],
        'bars': len(bars), 'bars_sha256': digest(bars), 'raw_pages_sha256': digest(collection),
        'page_count': len(pages), 'requests': requests,
        'normalized_at': datetime.now(timezone.utc).isoformat(),
        'limitations': [
            'Collection completeness is a collector attestation; Webull text has no total_count or has_more.',
            'Calendar gaps, completed sessions and corporate actions require a separate evidence-backed audit.',
            'Webull documents daily bars as forward-adjusted; confirm the connected endpoint and record basis evidence.',
            'Formatted MCP text may round numeric values; original timestamps remain in the saved collection.',
        ],
    }}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('input', 'symbol', 'output'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    try:
        result = normalize(json.loads(Path(args.input).read_text()), args.symbol)
        with Path(args.output).open('x') as stream:
            json.dump(result, stream, indent=2, allow_nan=False)
    except (ValueError, TypeError, KeyError, OSError) as exc:
        parser.exit(2, str(exc) + '\n')
