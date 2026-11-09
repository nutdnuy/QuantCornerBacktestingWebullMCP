"""Synthetic fixtures prove collection gates and trial accounting; no provider data."""
import copy
import datetime as dt
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import normalize_webull
import research


def rows(count=5):
    return [{'date': (dt.date(2025, 1, 1) + dt.timedelta(days=i)).isoformat(),
             'open': 10 + i, 'high': 10 + i, 'low': 10 + i,
             'close': 10 + i, 'volume': 1000} for i in range(count)]


from test_normalize_webull import collection

def dataset():
    return {'bars': rows(), 'provenance': {'data_kind': 'synthetic', 'symbol': 'FIXTURE',
            'currency': 'USD', 'source': 'Deterministic unit test, not market data'}}


def plan(**extra):
    return {'approved': True, 'question': 'Understand the synthetic trend behavior',
            'symbol': 'FIXTURE', 'data_audit_passed': True, 'phase': 'development',
            'benchmark': 'same-asset buy-and-hold', 'limitations': [],
            'engine': {'strategy': 'sma', 'fast': 1, 'slow': 2, 'initial_cash': 1000,
                       'fee_bps': 10, 'slippage_bps': 5, 'lot_size': 1, 'currency': 'USD'}, **extra}


class ResearchTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.workspace = Path(temporary.name) / 'research'

    def execute(self, data=None, research_plan=None, trial='test'):
        return research.execute(data or dataset(), research_plan or plan(), self.workspace, trial)

    def events(self):
        return [json.loads(line) for line in (self.workspace / 'trials.jsonl').read_text().splitlines()]

    def webull_fixture(self):
        data = normalize_webull.normalize(collection(rows()), 'FIXTURE')
        data['provenance']['calendar_audit'] = 'passed'
        data['provenance']['calendar_audit_evidence'] = 'Synthetic unit-test date grid; not a real market calendar'
        return data

    def test_hash_record_matches_private_snapshots_and_result(self):
        result = self.execute()
        records = self.events()
        self.assertEqual([record['event'] for record in records], ['started', 'completed'])
        trial = self.workspace / 'test'
        for key, filename in [('plan_hash', 'plan.json'), ('data_hash', 'dataset.json')]:
            self.assertEqual(records[0][key], research.digest(json.loads((trial / filename).read_text())))
            self.assertEqual(result['research'][key], records[0][key])
        self.assertEqual(records[1]['result_hash'], research.digest(result))
        engine_path = Path(research.__file__).with_name('engine.py')
        self.assertEqual(result['research']['engine_hash'], hashlib.sha256(engine_path.read_bytes()).hexdigest())
        self.assertFalse((self.workspace / '.research.lock').exists())

    def test_validation_rejects_bad_config_before_reserving_or_running(self):
        for key, value in [('initial_cash', -1), ('fee_bps', -1), ('slippage_bps', float('nan')),
                           ('lot_size', 0), ('strategy', 'short'), ('evaluation_start', 'tomorrow')]:
            candidate = plan()
            candidate['engine'][key] = value
            with self.subTest(key=key), patch.object(research, 'run') as mocked:
                with self.assertRaises(ValueError):
                    self.execute(research_plan=candidate)
                mocked.assert_not_called()
                self.assertFalse(self.workspace.exists())

    def test_approval_audit_benchmark_and_assumptions_required(self):
        candidates = [plan(approved=False), plan(data_audit_passed=False), plan(question=''),
                      plan(benchmark='SET'), plan(phase='future'), plan(limitations='not a list')]
        missing = plan()
        del missing['engine']['fee_bps']
        candidates.append(missing)
        for candidate in candidates:
            with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                self.execute(research_plan=candidate)
        self.assertFalse(self.workspace.exists())

    def test_missing_or_arbitrary_price_basis_never_bypasses_acknowledgement(self):
        for basis in [None, '', 'unknown', 'probably-adjusted']:
            data = self.webull_fixture()
            data['provenance']['corporate_actions'] = 'audited'
            if basis is None:
                del data['provenance']['price_basis']
            else:
                data['provenance']['price_basis'] = basis
            with self.subTest(basis=basis), self.assertRaisesRegex(ValueError, 'diagnostic acknowledgement'):
                self.execute(data=data)
        self.assertFalse(self.workspace.exists())

    def test_explicit_unknown_basis_diagnostic_is_labeled(self):
        result = self.execute(data=self.webull_fixture(), research_plan=plan(price_only_diagnostic_acknowledged=True))
        self.assertTrue(any('LIMITED PRICE-ONLY DIAGNOSTIC' in warning for warning in result['warnings']))
        self.assertEqual(result['provenance']['price_basis'], 'unknown')

    def test_only_documented_raw_no_action_window_qualifies(self):
        data = self.webull_fixture()
        data['provenance'].update(price_basis='raw', price_basis_evidence='Synthetic provider-basis attestation',
                                  corporate_actions='audited', corporate_action_policy='no_actions_in_window',
                                  corporate_actions_evidence='Synthetic no-action fixture, including warmup')
        result = self.execute(data=data, trial='qualified')
        self.assertFalse(any('LIMITED PRICE-ONLY DIAGNOSTIC' in warning for warning in result['warnings']))
        for key, value in [('price_basis', 'split_adjusted'), ('price_basis', 'total_return_adjusted'),
                           ('price_basis_evidence', ''), ('corporate_actions_evidence', None),
                           ('corporate_action_policy', 'events_audited')]:
            changed = copy.deepcopy(data)
            changed['provenance'][key] = value
            with self.subTest(key=key, value=value), self.assertRaisesRegex(ValueError, 'diagnostic acknowledgement'):
                self.execute(data=changed, trial='limited')

    def test_webull_hash_metadata_calendar_and_currency_gates(self):
        candidate = plan(price_only_diagnostic_acknowledged=True)
        changes = [('bars_sha256', '0' * 64), ('bars', 500), ('actual_start', '2020-01-01'),
                   ('actual_end', '2099-01-01'), ('collection_complete', False),
                   ('calendar_audit', 'not_performed'), ('currency', 'EUR'), ('symbol', 'OTHER')]
        changes.extend([('calendar_audit_evidence', ''), ('collection_evidence', '')])
        for key, value in changes:
            data = self.webull_fixture()
            data['provenance'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.execute(data=data, research_plan=candidate)
        changed = self.webull_fixture()
        changed['bars'][0]['volume'] = 999
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            self.execute(data=changed, research_plan=candidate)

    def test_holdout_cannot_follow_overlapping_development(self):
        self.execute(trial='development')
        with self.assertRaisesRegex(ValueError, 'already accessed'):
            self.execute(research_plan=plan(phase='holdout', candidate_locked=True), trial='renamed')
        self.assertEqual(len(self.events()), 2)
        self.assertFalse((self.workspace / 'renamed').exists())

    def test_disjoint_holdout_after_development_and_no_repeat(self):
        data = dataset()
        data['bars'] = data['bars'][:3]
        self.execute(data=data, trial='development')
        candidate = plan(phase='holdout', candidate_locked=True)
        candidate['engine']['evaluation_start'] = '2025-01-04'
        result = self.execute(research_plan=candidate, trial='holdout')
        self.assertEqual(result['equity'][0]['date'], '2025-01-04')
        with self.assertRaisesRegex(ValueError, 'already accessed'):
            self.execute(research_plan=candidate, trial='another_name')

    def test_holdout_is_reserved_before_run_and_failure_consumes_access(self):
        candidate = plan(phase='holdout', candidate_locked=True)
        def fail_after_observing_reservation(*unused):
            self.assertEqual([record['event'] for record in self.events()], ['started'])
            raise RuntimeError('Synthetic execution failure')
        with patch.object(research, 'run', side_effect=fail_after_observing_reservation):
            with self.assertRaises(RuntimeError):
                self.execute(research_plan=candidate)
        self.assertEqual([record['event'] for record in self.events()], ['started', 'failed'])
        self.assertFalse((self.workspace / '.research.lock').exists())
        with self.assertRaisesRegex(ValueError, 'already accessed'):
            self.execute(research_plan=candidate, trial='retry')

    def test_workspace_lock_prevents_concurrent_trial_access(self):
        self.workspace.mkdir()
        (self.workspace / '.research.lock').touch()
        with patch.object(research, 'run') as mocked:
            with self.assertRaisesRegex(ValueError, 'locked'):
                self.execute()
            mocked.assert_not_called()
        self.assertTrue((self.workspace / '.research.lock').exists())

    def test_existing_trial_and_corrupt_registry_preserved(self):
        self.execute()
        saved = (self.workspace / 'trials.jsonl').read_text()
        with self.assertRaisesRegex(ValueError, 'already exists'):
            self.execute()
        self.assertEqual((self.workspace / 'trials.jsonl').read_text(), saved)
        (self.workspace / 'trials.jsonl').write_text(saved + '{bad json\n')
        with self.assertRaises(ValueError):
            self.execute(trial='new')
        self.assertFalse((self.workspace / 'new').exists())

    def test_trial_path_traversal_rejected(self):
        for trial in ['../escape', '/absolute', '', 'with/slash']:
            with self.subTest(trial=trial), self.assertRaises(ValueError):
                self.execute(trial=trial)
        self.assertFalse(self.workspace.exists())


if __name__ == '__main__':
    unittest.main()
