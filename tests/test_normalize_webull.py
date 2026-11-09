"""Synthetic Webull-format fixtures; no licensed market prices."""
import copy
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import normalize_webull as adapter


def response(rows, symbol='FIXTURE'):
    return '=== Stock Bars (OHLCV) ===\n  --- ' + symbol + ' ---\n' + '\n'.join(
        f"  {b['date']}T05:00:00.000+0000  O: {b['open']}  H: {b['high']}  L: {b['low']}  C: {b['close']}  Vol: {b['volume']}"
        for b in rows)


def collection(rows=None):
    rows = rows or [{'date': '2025-01-02', 'open': 10, 'high': 12, 'low': 9, 'close': 11, 'volume': 1000},
                    {'date': '2025-01-03', 'open': 11, 'high': 13, 'low': 10, 'close': 12, 'volume': 1200}]
    return {'schema_version': 1, 'provider': 'webull', 'category': 'US_STOCK', 'currency': 'USD',
            'exchange_timezone': 'America/New_York', 'timespan': 'D',
            'requested_start': rows[0]['date'], 'requested_end': rows[-1]['date'],
            'collection_complete': True, 'collection_evidence': 'Synthetic fixture only; all generated rows retained.',
            'pages': [{'request': {'symbol': 'FIXTURE', 'category': 'US_STOCK', 'timespan': 'D',
                                  'count': len(rows), 'real_time_required': False},
                       'response': {'structuredContent': {'result': response(rows[::-1])}}}]}


class NormalizationTests(unittest.TestCase):
    def test_envelopes_sort_and_hash_without_inventing_audits(self):
        source = collection()
        raw = source['pages'][0]['response']['structuredContent']['result']
        variants = [raw, {'result': raw}, {'structuredContent': {'result': raw}},
                    {'content': [{'type': 'text', 'text': raw}]},
                    {'structuredContent': {'result': raw}, 'content': [{'type': 'text', 'text': raw}]}]
        for variant in variants:
            source['pages'][0]['response'] = variant
            result = adapter.normalize(source, 'fixture')
            self.assertEqual([b['date'] for b in result['bars']], ['2025-01-02', '2025-01-03'])
            p = result['provenance']
            self.assertEqual(p['bars_sha256'], adapter.digest(result['bars']))
            self.assertEqual(p['raw_pages_sha256'], adapter.digest(source))
            self.assertEqual(p['price_basis'], 'unknown')
            self.assertEqual(p['calendar_audit'], 'not_performed')
            self.assertEqual(p['corporate_actions'], 'not_audited')

    def test_multiple_pages_and_batch_select_one_symbol(self):
        c = collection()
        rows = adapter.normalize(c, 'FIXTURE')['bars']
        one = c['pages'][0]
        one['response'] = response(rows[:1]) + '\n  --- OTHER ---\n  2025-01-02T05:00:00+0000 O: 3 H: 3 L: 3 C: 3 Vol: 20'
        one['request']['symbols'] = 'FIXTURE,OTHER'
        del one['request']['symbol']
        two = copy.deepcopy(one)
        two['response'] = response(rows[1:])
        c['pages'].append(two)
        result = adapter.normalize(c, 'FIXTURE')
        self.assertEqual(result['bars'], rows)
        self.assertEqual(result['provenance']['page_count'], 2)

    def test_missing_completeness_is_not_assumed(self):
        c = collection()
        del c['collection_complete']
        self.assertFalse(adapter.normalize(c, 'FIXTURE')['provenance']['collection_complete'])
        c['collection_complete'] = True
        c['collection_evidence'] = ''
        with self.assertRaises(ValueError): adapter.normalize(c, 'FIXTURE')

    def test_overlap_and_missing_symbol_fail(self):
        c = collection(); c['pages'].append(copy.deepcopy(c['pages'][0]))
        with self.assertRaisesRegex(ValueError, 'Duplicate'): adapter.normalize(c, 'FIXTURE')
        c = collection(); c['pages'][0]['response'] = c['pages'][0]['response']['structuredContent']['result'].replace('FIXTURE','OTHER')
        with self.assertRaisesRegex(ValueError, 'missing'): adapter.normalize(c, 'FIXTURE')

    def test_invalid_rows_errors_and_truncation_fail(self):
        raw = collection()['pages'][0]['response']['structuredContent']['result']
        cases = [raw.replace('H: 13', 'H: 1'), raw.replace('C: 12', 'C: nan'),
                 raw.replace('Vol: 1200', 'Vol: -1'), raw.replace('O: 11', 'O: 0'),
                 raw.replace('Vol: 1200', 'Vol: ...'), raw + '\ntruncated',
                 raw.replace('.000+0000', ''), raw.replace('2025-01-03', '2025-02-31'),
                 'Error: denied', {'isError': True, 'result': raw},
                 {'content': []}, {'structuredContent': {'result': raw}, 'content': [{'type':'text','text':'different'}]}]
        for case in cases:
            c = collection(); c['pages'][0]['response'] = case
            with self.subTest(case=str(case)[:40]), self.assertRaises(ValueError): adapter.normalize(c, 'FIXTURE')

    def test_wrong_market_frequency_currency_and_request_fail(self):
        for key,value in [('category','HK_STOCK'),('currency','THB'),('timespan','M1'),
                          ('exchange_timezone','UTC'),('requested_start','20250102')]:
            c = collection(); c[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): adapter.normalize(c, 'FIXTURE')
        for key,value in [('symbol','OTHER'),('count',True),('count',1),('real_time_required',True),
                          ('timespan','M1'),('start_time',1735776000),('end_time',1735776000000)]:
            c = collection(); c['pages'][0]['request'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): adapter.normalize(c, 'FIXTURE')

    def test_dates_use_exchange_timezone_and_dst(self):
        c = collection()
        c['requested_start'] = c['requested_end'] = '2025-07-01'
        c['pages'][0]['response'] = '=== Stock Bars (OHLCV) ===\n--- FIXTURE ---\n2025-07-02T02:00:00+0000 O: 10 H: 12 L: 9 C: 11 Vol: 0'
        result = adapter.normalize(c,'FIXTURE')
        self.assertEqual(result['bars'][0]['date'],'2025-07-01')
        self.assertEqual(result['bars'][0]['volume'],0)

    def test_inconsistent_sessions_fail(self):
        c = collection(); second = copy.deepcopy(c['pages'][0])
        # Separate dates avoid overlap so the session-contract check is exercised.
        c['pages'][0]['response'] = response(adapter.normalize(c,'FIXTURE')['bars'][:1])
        second['response'] = second['response']['structuredContent']['result'].splitlines()[:3]
        second['response'] = '\n'.join(second['response'])
        second['request']['trading_sessions'] = 'RTH'
        c['pages'].append(second)
        with self.assertRaisesRegex(ValueError,'sessions'): adapter.normalize(c,'FIXTURE')

if __name__ == '__main__': unittest.main()
