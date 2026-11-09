#!/usr/bin/env python3
"""Render a self-contained QuantCorner research report. Python standard library only."""
from __future__ import annotations
import argparse
import base64
import datetime as dt
import html
import json
import math
import re
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
METRICS = [
 ('total_return', 'Total return', 'Change in portfolio value over this sample.', 'pct'),
 ('cagr', 'CAGR', 'Annual compound growth; not a return earned every year.', 'pct'),
 ('annualized_volatility', 'Annualized volatility', 'Dispersion of periodic returns, including gains and losses.', 'pct'),
 ('max_drawdown', 'Maximum drawdown', 'Largest decline from a prior equity peak; not annualized.', 'pct'),
 ('sharpe', 'Sharpe ratio', 'Excess return versus the specified risk-free rate per unit of total volatility.', 'ratio'),
 ('sortino', 'Sortino ratio', 'Return above the specified target per unit of downside deviation.', 'ratio'),
 ('win_rate', 'Win rate', 'Winning closed trades divided by all closed trades.', 'pct'),
 ('payoff', 'Payoff ratio', 'Average winning P&L divided by the magnitude of average losing P&L.', 'ratio'),
 ('expectancy', 'Expectancy / closed trade', 'Mean realized net P&L in account currency; position sizes may differ.', 'money'),
 ('profit_factor', 'Profit factor', 'Sum of winning net P&L divided by the magnitude of losing net P&L.', 'ratio'),
 ('loss_rate', 'Loss rate', 'Losing closed trades / all closed trades.', 'pct'),
 ('breakeven_rate', 'Breakeven rate', 'Zero net P&L trades / all closed trades.', 'pct'),
 ('average_win', 'Average win', 'Mean positive net P&L, winning trades only.', 'money'),
 ('average_loss', 'Average loss', 'Mean loss magnitude, losing trades only; positive amount.', 'money'),
 ('breakeven_win_rate', 'Breakeven win rate', '1 / (1 + payoff), only when both groups exist and no flat trades; descriptive, not a forecast.', 'pct'),
 ('winning_trades', 'Winning trades', 'Number of profitable closed trades.', 'count'),
 ('losing_trades', 'Losing trades', 'Number of losing closed trades.', 'count'),
 ('breakeven_trades', 'Breakeven trades', 'Number of closed trades with zero net P&L.', 'count'),
 ('mean_daily_return', 'Mean daily return', 'Arithmetic mean, including cash days.', 'pct'),
 ('annualized_arithmetic_return', 'Annualized arithmetic return', 'Mean daily return × periods/year; distinct from CAGR.', 'pct'),
 ('daily_volatility', 'Daily volatility', 'Sample standard deviation of daily returns.', 'pct'),
 ('downside_deviation', 'Daily downside deviation', 'RMS downside below daily MAR across all periods.', 'pct'),
 ('filled_orders', 'Filled orders', 'Buy/sell fills; a closed round trip is two fills.', 'count'),
 ('total_fees', 'Total fees paid', 'Includes entry fee of any open position. Already deducted.', 'money'),
 ('modeled_slippage', 'Modeled slippage', 'Price impact against reference prices for actual quantities; already reflected in equity.', 'money'),
 ('total_modeled_cost', 'Total modeled costs', 'Fees plus modeled slippage; do not deduct again.', 'money'),
 ('closed_gross_pnl', 'Closed P&L before modeled costs', 'Actual closed quantities at reference prices; not a zero-cost rerun.', 'money'),
 ('closed_trade_cost', 'Closed-trade costs', 'Fees and modeled slippage allocated to closed trades only.', 'money'),
 ('closed_net_pnl', 'Closed net P&L', 'Closed gross P&L minus closed-trade costs; excludes open marks.', 'money'),
 ('mdd_drawdown_period', 'MDD: peak to trough', 'Observed session intervals to worst trough.', 'count'),
 ('mdd_recovery_period', 'MDD: trough to recovery', 'N/A until the worst episode recovers.', 'count'),
 ('mdd_underwater_period', 'MDD: peak to recovery', 'Drawdown + recovery intervals; N/A if unrecovered.', 'count'),
 ('current_underwater_period', 'Current underwater age', 'Observed intervals since latest peak; zero when at peak.', 'count'),
 ('longest_completed_underwater', 'Longest completed underwater period', 'May differ from the deepest drawdown episode.', 'count'),
 ('longest_observed_underwater', 'Longest observed underwater age', 'Includes censored, still-open episodes.', 'count'),
 ('recovery_return_required', 'Return needed from MDD trough', 'Peak / trough − 1; based on worst episode.', 'pct'),
 ('closed_trades', 'Closed trades', 'Sample size behind trade statistics; excludes an open position.', 'count'),
]

def escape(value):
    return html.escape(str(value), quote=True)

def finite_number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{name} must be a finite number')
    return float(value)

def check_finite(value, name='result'):
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f'{name} contains a non-finite number')
    if isinstance(value, dict):
        for key, item in value.items(): check_finite(item, f'{name}.{key}')
    if isinstance(value, list):
        for index, item in enumerate(value): check_finite(item, f'{name}[{index}]')

def validate(result):
    if not isinstance(result, dict): raise ValueError('result must be an object')
    check_finite(result)
    rows = result.get('equity')
    if not isinstance(rows, list) or not rows: raise ValueError('equity must contain at least one observation')
    last = None
    for row in rows:
        if not isinstance(row, dict): raise ValueError('equity rows must be objects')
        try: date = dt.date.fromisoformat(row['date'])
        except (KeyError, TypeError, ValueError): raise ValueError('equity date must be YYYY-MM-DD') from None
        if last and date <= last: raise ValueError('equity dates must be unique and ascending')
        last = date
        for key in ['equity', 'benchmark_equity', 'drawdown']:
            value = finite_number(row.get(key), key)
            if key != 'drawdown' and value < 0: raise ValueError(f'{key} cannot be negative')
            if key == 'drawdown' and not -1.00000001 <= value <= 0.00000001:
                raise ValueError('drawdown must be a decimal fraction between -1 and 0')
    for key in ['metrics', 'config']:
        if not isinstance(result.get(key, {}), dict): raise ValueError(f'{key} must be an object')
    if result.get('benchmark_metrics') is not None and not isinstance(result['benchmark_metrics'], dict):
        raise ValueError('benchmark_metrics must be an object or null')
    if not isinstance(result.get('trades', []), list): raise ValueError('trades must be a list')
    for row in result.get('trades', []):
        if not isinstance(row, dict): raise ValueError('trades must contain objects')
        finite_number(row.get('net_pnl'), 'trade.net_pnl')
    for obj in [result.get('metrics', {}), result.get('benchmark_metrics') or {}]:
        for key, *_ in METRICS:
            if obj.get(key) is not None: finite_number(obj[key], 'metrics.'+key)
    return rows

def asset_data(asset_dir):
    logo_path = asset_dir / 'quantcorner-mark-light.svg'
    if not logo_path.exists(): raise ValueError('Approved QuantCorner logo asset is missing')
    raw = logo_path.read_bytes()
    try: root = ET.fromstring(raw)
    except ET.ParseError: raise ValueError('Logo must be valid SVG') from None
    for element in root.iter():
        if element.tag.rsplit('}', 1)[-1] in {'script','foreignObject','image','use'}:
            raise ValueError('Logo contains an unsupported external or active element')
        if any(k.lower().startswith('on') or k.rsplit('}',1)[-1] == 'href' for k in element.attrib):
            raise ValueError('Logo contains an active or linked attribute')
    fonts = []
    for file in sorted((asset_dir / 'fonts').glob('*.woff2')):
        name = file.name.lower()
        family = 'Noto Sans Thai' if ('thai' in name or 'noto' in name) else 'Roboto' if 'roboto' in name else None
        if family:
            weight_match = re.search(r'(?:^|[-_])([1-9]00)(?:[-_.]|$)', name)
            weight = int(weight_match.group(1)) if weight_match else 700 if 'bold' in name else 400
            fonts.append("@font-face{font-family:'%s';font-style:normal;font-weight:%s;font-display:swap;src:url(data:font/woff2;base64,%s) format('woff2')}" % (family,weight,base64.b64encode(file.read_bytes()).decode()))
    return 'data:image/svg+xml;base64,'+base64.b64encode(raw).decode(), ''.join(fonts)

def fmt(value, kind):
    if value is None: return 'N/A'
    if kind == 'pct': return f'{value*100:,.2f}%'
    if kind == 'count': return f'{value:,.0f}'
    return f'{value:,.2f}'

def chart(rows, keys, name, unit, drawdown=False, compact=False):
    width, height = (350, 245) if compact else (1140, 340)
    left, right, top, bottom = (58, 12, 30, 40) if compact else (110, 28, 34, 54)
    w, h = width-left-right, height-top-bottom
    all_values=[r[key] * (100 if drawdown else 1) for r in rows for key in keys]
    low, high = min(all_values), max(all_values)
    if drawdown: high = 0.0
    if high == low:
        padding = max(abs(high)*.05, 1.0); low -= padding; high += 0 if drawdown else padding
    else:
        pad=(high-low)*.08; low-=pad
        if not drawdown: high+=pad
    raw_step = (high-low)/4
    magnitude = 10**math.floor(math.log10(raw_step))
    step = next(n*magnitude for n in (1, 2, 2.5, 5, 10) if n*magnitude >= raw_step)
    low = math.floor(low/step)*step
    high = math.ceil(high/step)*step
    x=lambda i:left + (w*i/(len(rows)-1) if len(rows)>1 else w/2)
    y=lambda v:top + h*(high-v)/(high-low)
    chart_class = 'chart-compact' if compact else 'chart-wide'
    parts=[f'<svg viewBox="0 0 {width} {height}" class="{chart_class}" role="img" aria-label="{escape(name)}"><title>{escape(name)}</title><desc>{escape(unit)}. {escape(rows[0]["date"])} to {escape(rows[-1]["date"])}; {len(rows)} observations. All observations plotted.</desc>']
    parts.append(f'<text x="{left}" y="19" class="axis-label">{escape(unit)}</text>')
    for i in range(round((high-low)/step)+1):
        value=low+step*i; yy=y(value)
        label=f'{value:,.1f}%' if drawdown else f'{value/1000:,.0f}k' if compact and abs(value) >= 1000 else f'{value:,.0f}'
        parts.append(f'<line x1="{left}" x2="{width-right}" y1="{yy:.2f}" y2="{yy:.2f}" class="gridline"/><text x="{left-12}" y="{yy+6:.2f}" text-anchor="end" class="axis-label">{label}</text>')
    tick_count = 3 if compact else 5
    indices=sorted({round(i*(len(rows)-1)/(tick_count-1)) for i in range(tick_count)})
    for i in indices:
        anchor = 'start' if i == 0 else 'end' if i == len(rows)-1 else 'middle'
        parts.append(f'<text x="{x(i):.2f}" y="{height-17}" text-anchor="{anchor}" class="axis-label">{escape(rows[i]["date"])}</text>')
    for n,key in enumerate(keys):
        points=[(x(i),y(r[key]*(100 if drawdown else 1))) for i,r in enumerate(rows)]
        color='primary-line' if n==0 else 'benchmark-line'
        if drawdown:
            polygon=[(points[0][0],y(0))]+points+[(points[-1][0],y(0))]
            parts.append('<polygon class="drawdown-fill" points="'+' '.join(f'{a:.2f},{b:.2f}' for a,b in polygon)+'"/>')
        if len(points)==1:
            parts.append(f'<circle cx="{points[0][0]:.2f}" cy="{points[0][1]:.2f}" r="4" class="{color}"/>')
        else:
            parts.append('<polyline class="'+color+'" points="'+' '.join(f'{a:.2f},{b:.2f}' for a,b in points)+'"/>')
    return ''.join(parts)+'</svg>'

def responsive_chart(rows, keys, name, unit, drawdown=False):
    return chart(rows, keys, name, unit, drawdown) + chart(rows, keys, name, unit, drawdown, compact=True)

def metadata(value):
    if value is None or value == {} or value == []: return '<p class="muted">Not supplied.</p>'
    if isinstance(value, dict):
        return '<dl class="metadata">'+''.join('<dt>'+escape(k.replace('_',' '))+'</dt><dd>'+escape(json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v)+'</dd>' for k,v in value.items())+'</dl>'
    if isinstance(value,list): return '<ul>'+''.join('<li>'+escape(json.dumps(x,ensure_ascii=False) if isinstance(x,(dict,list)) else x)+'</li>' for x in value)+'</ul>'
    return '<p>'+escape(value)+'</p>'

def render_report(result, title='Understand the strategy.', asset_dir=None):
    rows=validate(result);asset_dir=Path(asset_dir) if asset_dir else ROOT/'assets'
    logo,fonts=asset_data(asset_dir)
    config=result.get('config',{});metrics=result.get('metrics',{});benchmark=result.get('benchmark_metrics') or {}
    provenance=result.get('provenance') or {}
    if not isinstance(provenance,dict): raise ValueError('provenance must be an object')
    data_kind=str(provenance.get('data_kind','unknown')).lower()
    synthetic=data_kind in {'synthetic','synthetic_demo','demo','fixture'}
    if synthetic: label='Synthetic demonstration — not Webull market data';description='Illustrative pipeline output. These figures describe generated data and are not evidence about a real strategy.'
    elif data_kind in {'webull','webull_mcp','market','real','real_market'}:
        label='Historical research · source details below';description='Read the sample, data basis, execution assumptions, and limitations before interpreting performance.'
    else: label='Data provenance unknown';description='The input does not establish the source or nature of the data. Verify provenance before using these results.'
    currency=str(config.get('currency') or provenance.get('currency') or 'account units; currency unspecified')
    unit='Portfolio value ('+currency+')'
    baseline_note = ' Total return uses starting cash before the first marked observation.' if config.get('initial_cash') is not None else ''
    metric_rows=''.join('<tr><th scope="row">'+escape(name)+'<small>'+escape(explanation)+'</small></th><td data-label="Strategy">'+fmt(metrics.get(key),kind)+'</td><td data-label="Benchmark">'+fmt(benchmark.get(key),kind)+'</td></tr>' for key,name,explanation,kind in METRICS)
    trades=result.get('trades',[])
    trade_rows=''.join('<tr><td>'+escape(t.get('entry_date','Not supplied'))+'</td><td>'+escape(t.get('exit_date','Not supplied'))+'</td><td>'+fmt(t['net_pnl'],'money')+'</td></tr>' for t in trades)
    if not trades: trade_rows='<tr><td colspan="3">No closed trades. An open position can still affect portfolio results.</td></tr>'
    css='''
:root{--canvas:#FAFAF7;--surface:#FFFFFF;--ink:#212121;--muted:#616161;--line:#DDDCD5;--primary:#6200EE;--secondary:#00796B;--soft:#F0ECEF;--font:Roboto,'Noto Sans Thai',Arial,sans-serif;--mono:ui-monospace,SFMono-Regular,Consolas,monospace}
*{box-sizing:border-box}html,body{margin:0;overflow-x:clip}body{background:var(--canvas);color:var(--ink);font:16px/1.6 var(--font)}main{max-width:1240px;margin:auto;padding:48px 36px 56px}header{border-bottom:1px solid var(--line);padding-bottom:30px}.masthead{display:flex;justify-content:space-between;align-items:center;gap:24px;margin-bottom:45px}.brand{font-size:20px;font-weight:700;letter-spacing:-.4px}.logo{width:52px;height:52px}.context{font-size:14px;color:var(--muted)}h1{font-size:clamp(34px,5vw,60px);line-height:1.1;letter-spacing:-1.8px;max-width:950px;margin:0 0 18px;overflow-wrap:break-word;min-width:0}h2{font-size:27px;line-height:1.3;margin:0 0 8px;letter-spacing:-.6px}h3{font-size:19px;margin:0 0 12px}p{margin:0 0 12px}.intro{max-width:840px;color:var(--muted);font-size:18px}.provenance-notice{padding:16px 20px;border:1px solid var(--line);margin-top:25px;background:var(--surface)}.provenance-notice strong{font-size:16px}.provenance-notice p{font-size:14px;margin:5px 0 0}.summary{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:32px;margin-top:30px}.summary div{border-top:2px solid var(--ink);padding-top:12px}.summary span{color:var(--muted);font-size:14px;display:block}.summary strong{display:block;font-size:34px;line-height:1.4;font-weight:500;font-variant-numeric:tabular-nums}.summary small{color:var(--muted)}section{padding:35px 0;border-bottom:1px solid var(--line)}.section-head{display:flex;justify-content:space-between;gap:20px;align-items:baseline;flex-wrap:wrap}.muted{color:var(--muted)}.legend{display:flex;gap:23px;flex-wrap:wrap;font-size:14px}.legend span:before{content:'';display:inline-block;width:25px;border-top:3px solid var(--primary);vertical-align:middle;margin-right:8px}.legend .benchmark:before{border-color:var(--secondary);border-top-style:dashed}.chart-wrap{overflow:auto;margin-top:20px}.chart-wrap:focus-visible,.table-wrap:focus-visible{outline:3px solid var(--primary);outline-offset:4px}.chart-wrap svg{width:100%;display:block;height:auto}.chart-wrap .chart-compact{display:none}.axis-label{font:16px var(--font);fill:var(--muted)}.gridline{stroke:var(--line);stroke-width:1}.primary-line{vector-effect:non-scaling-stroke;stroke:var(--primary);stroke-width:2.7;fill:none;stroke-linejoin:round}.benchmark-line{vector-effect:non-scaling-stroke;stroke:var(--secondary);stroke-width:2.3;fill:none;stroke-dasharray:7 5;stroke-linejoin:round}.drawdown-fill{fill:var(--primary);opacity:.08}.chart-note{font-size:13px;color:var(--muted);margin:8px 0 0}.table-wrap{overflow:auto}table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}th,td{border-bottom:1px solid var(--line);padding:16px 12px;text-align:left;vertical-align:top}thead th{font-size:14px;color:var(--muted);font-weight:500}tbody th{font-weight:500;width:56%}td{white-space:nowrap}th small{display:block;font-size:13px;font-weight:400;color:var(--muted);max-width:600px;line-height:1.5;margin-top:3px}.research-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:40px;margin-top:23px}.metadata{display:grid;grid-template-columns:minmax(110px,1fr) minmax(0,2fr);gap:10px 16px;margin:0;font-size:14px}.metadata dt{color:var(--muted)}.metadata dd{margin:0;overflow-wrap:anywhere}ul{margin:0;padding-left:20px}li{margin:0 0 7px}.scope-note{font-size:14px;max-width:930px;margin-top:14px}.endnote{font-size:13px;color:var(--muted);padding-top:25px;max-width:900px}a{color:var(--secondary)}a:focus-visible{outline:3px solid var(--primary);outline-offset:3px}@media(max-width:640px){main{padding:24px 20px 35px}.masthead{margin-bottom:32px}h1{letter-spacing:-1px}.summary{gap:14px}.summary strong{font-size:26px}.summary small{font-size:12px}.research-grid{grid-template-columns:1fr;gap:28px}.metadata{grid-template-columns:minmax(90px,1fr) minmax(0,1.8fr)}section{padding:27px 0}th,td{padding:12px 8px}.chart-wrap .chart-wide{display:none}.chart-wrap .chart-compact{display:block}.chart-compact .axis-label{font-size:11px}.metrics-table thead{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%)}.metrics-table,.metrics-table tbody{display:block}.metrics-table tr{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));padding:15px 0;border-bottom:1px solid var(--line)}.metrics-table th{display:block;grid-column:1/-1;width:auto;padding:0 0 10px;border:0}.metrics-table td{display:block;padding:0;border:0;font-size:20px}.metrics-table td:before{content:attr(data-label);display:block;color:var(--muted);font-size:12px}.ledger-table{font-size:12px}.ledger-table th,.ledger-table td{padding:12px 3px;white-space:normal;overflow-wrap:anywhere}.ledger-table td:last-child{text-align:right}.context{max-width:180px}.intro{font-size:16px}}@media print{main{padding:0;max-width:none}.chart-wrap .chart-wide{display:block}.chart-wrap .chart-compact{display:none}.table-wrap,.chart-wrap{overflow:visible}section,header{break-inside:avoid}.summary strong{font-size:28px}.research-grid{gap:24px}h1{font-size:38px}body{font-size:12px}}@media(prefers-reduced-motion:reduce){*,*:before,*:after{animation:none!important;transition:none!important}}
'''
    return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+escape(title)+' · QuantCorner</title><style>'+fonts+css+'</style></head><body><main><header><div class="masthead"><div><div class="brand">QuantCorner</div><div class="context">Backtesting research report</div></div><img class="logo" src="'+logo+'" alt="QuantCorner approved mark" width="52" height="52"></div><h1>'+escape(title)+'</h1><p class="intro">Understand returns, risk, and trading behavior together. A favorable backtest is a research observation, not a verdict on future performance.</p><div class="provenance-notice"><strong>'+escape(label)+'</strong><p>'+escape(description)+'</p></div><div class="summary"><div><span>Total return</span><strong>'+fmt(metrics.get('total_return'),'pct')+'</strong><small>Over this sample</small></div><div><span>Maximum drawdown</span><strong>'+fmt(metrics.get('max_drawdown'),'pct')+'</strong><small>From a previous equity peak</small></div><div><span>Closed trades</span><strong>'+fmt(metrics.get('closed_trades'),'count')+'</strong><small>Open trades excluded</small></div></div></header><section><div class="section-head"><h2>The path of the portfolio</h2><div class="legend"><span>Strategy</span><span class="benchmark">Buy and hold</span></div></div><p class="muted">'+escape(rows[0]['date'])+' to '+escape(rows[-1]['date'])+' · '+str(len(rows))+' observed sessions</p><div class="chart-wrap" tabindex="0" role="region" aria-label="Portfolio value chart">'+responsive_chart(rows,['equity','benchmark_equity'],'Strategy and benchmark portfolio value',unit)+'</div><p class="chart-note">All supplied observations plotted; k = thousand. The benchmark series comes from the same result file; confirm its cost and execution assumptions below.'+baseline_note+'</p></section><section><h2>Time below a previous peak</h2><p class="muted">Daily drawdown shows the depth and persistence of losses. It cannot reveal every intraday decline.</p><div class="chart-wrap" tabindex="0" role="region" aria-label="Drawdown chart">'+responsive_chart(rows,['drawdown'],'Strategy drawdown','Drawdown (%)',True)+'</div><p class="chart-note">A value of −20% means equity is 20% below its running peak. This chart is not annualized.</p></section><section><h2>Read the metrics in context</h2><p class="muted">Ratios need consistent periods and definitions. N/A means undefined or not supplied, not zero.</p><div class="table-wrap" tabindex="0" role="region" aria-label="Metric definitions and comparison"><table class="metrics-table"><thead><tr><th>Metric and purpose</th><th>Strategy</th><th>Benchmark</th></tr></thead><tbody>'+metric_rows+'</tbody></table></div><p class="scope-note">Money-valued statistics use '+escape(currency)+'. Trade statistics describe closed positions only; portfolio statistics include marked open positions. Averages can depend on changing position sizes.</p></section><section><h2>What this experiment assumes</h2><div class="research-grid"><div><h3>Execution and model configuration</h3>'+metadata(config)+'</div><div><h3>Assumptions</h3>'+metadata(result.get('assumptions'))+'</div></div></section><section><h2>Evidence and limitations</h2><div class="research-grid"><div><h3>Data provenance and coverage</h3>'+metadata(provenance)+'</div><div><h3>Warnings</h3>'+metadata(result.get('warnings'))+'<h3 style="margin-top:25px">Validation</h3>'+metadata(result.get('validation'))+'<h3 style="margin-top:25px">Research record</h3>'+metadata(result.get('research'))+'</div></div><div class="research-grid"><div><h3>Drawdown episodes · strategy</h3>'+metadata(result.get('drawdown_analysis'))+'<h3>Drawdown episodes · benchmark</h3>'+metadata(result.get('benchmark_drawdown_analysis'))+'<h3>Reconciliation</h3>'+metadata(result.get('reconciliation'))+'</div><div><h3>Open position</h3>'+metadata(result.get('open_position'))+'</div></div></section><section><h2>Closed-trade ledger</h2><div class="table-wrap" tabindex="0" role="region" aria-label="Closed-trade ledger"><table class="ledger-table"><thead><tr><th>Entry date</th><th>Exit date</th><th>Net P&amp;L ('+escape(currency)+')</th></tr></thead><tbody>'+trade_rows+'</tbody></table></div></section><p class="endnote">QuantCornerBacktestingWebullMCP · Local, self-contained report. No remote fonts, analytics, or data requests. Sharing this HTML also shares its embedded observations and metadata; check data entitlements and remove private information before distributing it. The report does not establish that a holdout remained independent.</p></main></body></html>'

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--title',default='Understand the strategy.')
    args=parser.parse_args()
    try:
        result=json.loads(args.input.read_text(encoding='utf-8'))
        report=render_report(result,args.title)
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(report,encoding='utf-8')
    except (ValueError,OSError,KeyError,TypeError) as exc:
        parser.exit(2,f'Report error: {exc}\n')
    print(args.output)

if __name__=='__main__': main()
