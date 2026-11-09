"""Auditable local runner; the local registry is a convention, not tamper-proof storage.

Audit flags are supplied attestations, not a substitute for inspecting source data.
All experiments for one research project must share a workspace. A new workspace
cannot establish that historical data were never inspected elsewhere.
"""
import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from engine import iso_date, run, validated


def digest(value):
    """Stable hash for the exact JSON value; shared with the normalizer."""
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def text_field(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(label + ' must be a nonempty string')
    return value


def text_list(value, label):
    if not isinstance(value, list) or any(not isinstance(s, str) for s in value):
        raise ValueError(label + ' must be an array of strings')
    return value


def preflight(dataset, plan):
    """Validate inputs without calculating strategy signals, orders, or returns."""
    if not isinstance(dataset, dict) or not isinstance(plan, dict):
        raise ValueError('Dataset and plan must be objects')
    if plan.get('approved') is not True:
        raise ValueError('Resolve/agree the research plan first')
    text_field(plan.get('question'), 'Research question')
    if plan.get('data_audit_passed') is not True:
        raise ValueError('Integrity gate has not passed')
    text_list(plan.get('limitations', []), 'Plan limitations')
    config = plan.get('engine')
    if not isinstance(config, dict):
        raise ValueError('Explicit engine config required')
    for key in ('initial_cash', 'fee_bps', 'slippage_bps', 'lot_size'):
        if config.get(key) is None:
            raise ValueError('Explicit assumption required: ' + key)
    bars = dataset.get('bars')
    _, cfg, dates, start_index = validated(bars, config)
    prov = dataset.get('provenance')
    if not isinstance(prov, dict) or prov.get('data_kind') not in ('synthetic', 'webull'):
        raise ValueError('Missing supported data provenance')
    text_field(prov.get('source'), 'Data source')
    text_list(prov.get('limitations', []), 'Provenance limitations')
    symbol = text_field(plan.get('symbol'), 'Plan symbol')
    if prov.get('symbol') != symbol:
        raise ValueError('Plan/data symbol mismatch')
    if prov.get('currency') != cfg['currency']:
        raise ValueError('Plan/data currency mismatch; no currency conversion is implemented')
    diagnostic = False
    if prov['data_kind'] == 'webull':
        if 'mock' in prov['source'].lower():
            raise ValueError('Mock data cannot be labeled Webull market history')
        if prov.get('collection_complete') is not True:
            raise ValueError('Incomplete provider collection')
        text_field(prov.get('collection_evidence'), 'Collection evidence')
        if prov.get('calendar_audit') != 'passed':
            raise ValueError('Exchange calendar coverage must be audited')
        text_field(prov.get('calendar_audit_evidence'), 'Calendar audit evidence')
        if prov.get('bars_sha256') != digest(bars):
            raise ValueError('Normalized bars hash mismatch; re-audit changed data')
        if (type(prov.get('bars')) is not int or prov['bars'] != len(bars)
                or prov.get('actual_start') != dates[0].isoformat()
                or prov.get('actual_end') != dates[-1].isoformat()):
            raise ValueError('Normalized range/count metadata does not match bars')
        # Adjusted OHLC is not necessarily executable. This engine cannot book
        # share changes or cash distributions, even when an event is audited.
        def has_evidence(key):
            return isinstance(prov.get(key), str) and bool(prov[key].strip())
        qualified = (prov.get('price_basis') in ('raw', 'unadjusted')
                     and has_evidence('price_basis_evidence')
                     and prov.get('corporate_actions') == 'audited'
                     and prov.get('corporate_action_policy') == 'no_actions_in_window'
                     and has_evidence('corporate_actions_evidence'))
        diagnostic = not qualified
        if diagnostic and plan.get('price_only_diagnostic_acknowledged') is not True:
            raise ValueError('Unknown adjustment/corporate actions; requires explicit limited diagnostic acknowledgement')
    if plan.get('benchmark') != 'same-asset buy-and-hold':
        raise ValueError('Reference engine supports same-asset benchmark only; implement and validate the requested benchmark separately')
    phase = plan.get('phase')
    if phase not in ('development', 'holdout'):
        raise ValueError('Unknown phase')
    if phase == 'holdout' and plan.get('candidate_locked') is not True:
        raise ValueError('Lock candidate before holdout access')
    return bars, prov, dates[start_index].isoformat(), dates[-1].isoformat(), diagnostic


def read_events(registry):
    if not registry.exists():
        return []
    events = []
    for line in registry.read_text().splitlines():
        if not line.strip():
            raise ValueError('Malformed trial registry; inspect without discarding history')
        event = json.loads(line)
        if not isinstance(event, dict) or event.get('event') not in ('started', 'completed', 'failed'):
            raise ValueError('Malformed trial registry; inspect without discarding history')
        first = iso_date(event.get('start'), 'Registry start')
        last = iso_date(event.get('end'), 'Registry end')
        if first > last:
            raise ValueError('Invalid registry date range')
        events.append(event)
    return events


def execute(dataset, plan, workspace, trial_id):
    if not isinstance(trial_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', trial_id):
        raise ValueError('Unsafe trial id')
    bars, prov, start, end, diagnostic = preflight(dataset, plan)
    phase = plan['phase']
    base = {'trial_id': trial_id, 'phase': phase, 'start': start, 'end': end,
            'symbol': plan['symbol'], 'plan_hash': digest(plan), 'data_hash': digest(dataset),
            'engine_hash': hashlib.sha256(Path(__file__).with_name('engine.py').read_bytes()).hexdigest(),
            'analytics_hash': hashlib.sha256(Path(__file__).with_name('analytics.py').read_bytes()).hexdigest(),
            'runner_hash': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    w = Path(workspace)
    w.mkdir(parents=True, exist_ok=True)
    registry, dest, lock = w / 'trials.jsonl', w / trial_id, w / '.research.lock'
    try:
        lock_fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise ValueError('Research workspace is locked; wait for its run or inspect an interrupted run before removing the lock') from exc
    os.close(lock_fd)
    try:
        if dest.exists():
            raise ValueError('Trial id already exists; preserve original')
        events = read_events(registry)
        accessed = [e for e in events if e['event'] == 'started' and start <= e['end'] and end >= e['start']]
        if phase == 'holdout' and accessed:
            raise ValueError('Held-out window already accessed by research: cannot claim independent evaluation again')

        def event(name, **extra):
            record = dict(base, event=name, time=datetime.now(timezone.utc).isoformat(), **extra)
            with registry.open('a') as stream:
                stream.write(json.dumps(record, allow_nan=False) + '\n')
                stream.flush()
                os.fsync(stream.fileno())

        dest.mkdir()
        # Local private snapshots make both hashes reproducible; never publish these.
        (dest / 'plan.json').write_text(json.dumps(plan, indent=2, allow_nan=False) + '\n')
        (dest / 'dataset.json').write_text(json.dumps(dataset, indent=2, allow_nan=False) + '\n')
        event('started')  # Reserve access before computing a single strategy result.
        try:
            result = run(bars, plan['engine'])
            result['provenance'] = prov
            result['research'] = dict(base, question=plan['question'], benchmark=plan['benchmark'])
            result.setdefault('warnings', []).extend(plan.get('limitations', []))
            result['warnings'].extend(prov.get('limitations', []))
            if prov['data_kind'] == 'webull':
                result['warnings'].append('Calendar and corporate-action audit status are operator attestations. The reference engine does not independently verify them or book dividend/split cash flows.')
            if diagnostic:
                result['warnings'].append('LIMITED PRICE-ONLY DIAGNOSTIC: executable raw prices and absence of corporate actions across the supplied window are not established. Not dividend-inclusive total return; adjusted OHLC, cash distributions, or share changes may distort all metrics.')
            if phase == 'development':
                result['warnings'].append('Development result, not independent held-out evidence.')
                if any(e.get('phase') == 'holdout' for e in accessed):
                    result['warnings'].append('This development run revisits a previously accessed holdout; that window is now development information.')
            else:
                result['warnings'].append('The local registry only tracks this workspace. Historical holdouts may already be known or accessed elsewhere; candidate_locked is a supplied attestation.')
            (dest / 'result.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
            event('completed', result_hash=digest(result))
            return result
        except Exception as exc:
            event('failed', error=str(exc))
            raise
    finally:
        lock.unlink()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('data', 'plan', 'workspace', 'trial-id'):
        parser.add_argument('--' + key, required=True)
    args = parser.parse_args()
    try:
        execute(json.loads(Path(args.data).read_text()), json.loads(Path(args.plan).read_text()), args.workspace, args.trial_id)
        print(str(Path(args.workspace) / args.trial_id / 'result.json'))
    except (ValueError, TypeError, KeyError, OSError) as exc:
        parser.exit(2, str(exc) + '\n')
