"""Chapter-14 companion statistics. Durations count observed session intervals."""

def drawdown_analysis(values, initial, dates, initial_date):
    levels = [initial] + list(values)
    labels = [initial_date.isoformat()] + [d.isoformat() for d in dates]
    peak = 0
    active = None
    episodes = []
    for i in range(1, len(levels)):
        if levels[i] >= levels[peak]:
            if active is not None:
                active['recovery'] = i
                episodes.append(active)
                active = None
            peak = i
        else:
            if active is None:
                active = {'peak': peak, 'trough': i, 'recovery': None}
            if levels[i] < levels[active['trough']]:
                active['trough'] = i
    if active is not None:
        episodes.append(active)
    records = []
    for e in episodes:
        p, t, rec = e['peak'], e['trough'], e['recovery']
        records.append({
            'peak_date': labels[p], 'trough_date': labels[t],
            'recovery_date': labels[rec] if rec is not None else None,
            'depth': levels[t] / levels[p] - 1,
            'drawdown_period': t - p,
            'recovery_period': rec - t if rec is not None else None,
            'underwater_period': rec - p if rec is not None else None,
            'elapsed_underwater': (rec if rec is not None else len(levels)-1) - p,
            'recovery_return_required': levels[p] / levels[t] - 1,
            'status': 'recovered' if rec is not None else 'unrecovered',
        })
    worst = min(records, key=lambda e:e['depth']) if records else None
    completed = [e['underwater_period'] for e in records if e['status']=='recovered']
    current = records[-1] if active is not None else None
    return {'worst_episode': worst, 'current_episode': current,
            'longest_completed_underwater': max(completed) if completed else None,
            'longest_observed_underwater': max((e['elapsed_underwater'] for e in records), default=0),
            'episodes': records,
            'duration_unit': 'observed session intervals, not calendar days; initial capital is session 0'}


def cost_statistics(trades, open_entry=None):
    fees = sum(t['entry_fee'] + t['exit_fee'] for t in trades)
    slippage = sum(t['entry_slippage'] + t['exit_slippage'] for t in trades)
    closed_cost = fees + slippage
    net = sum(t['net_pnl'] for t in trades)
    if open_entry:
        fees += open_entry['entry_fee']
        slippage += open_entry['entry_slippage']
    return {'filled_orders': 2*len(trades) + bool(open_entry),
            'total_fees': fees, 'modeled_slippage': slippage,
            'total_modeled_cost': fees + slippage,
            'closed_gross_pnl': net + closed_cost, 'closed_net_pnl': net,
            'closed_trade_cost': closed_cost}
