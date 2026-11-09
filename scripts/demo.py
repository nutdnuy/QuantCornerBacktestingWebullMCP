"""Deterministic synthetic integration test; no Webull data, no internet."""
import argparse,json,math
from datetime import date,timedelta
from pathlib import Path
from research import execute
from report import render_report

def demo(output):
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    rows=[];d=date(2021,1,1);i=0;prev=100
    while len(rows)<800:
        if d.weekday()<5:
            close=100+0.018*i+12*math.sin(i/38)+3*math.sin(i/9)
            op=prev*(1+0.002*math.sin(i/3))
            rows.append({'date':d.isoformat(),'open':op,'high':max(op,close)*1.006,'low':min(op,close)*0.994,'close':close,'volume':1000000});prev=close;i+=1
        d+=timedelta(days=1)
    data={'bars':rows,'provenance':{'data_kind':'synthetic','source':'Deterministic sine-wave fixture; NOT market prices','currency':'USD','symbol':'SYNTHETIC','price_basis':'generated','limitations':['Synthetic weekdays are not a real exchange calendar.']}}
    plan={'approved':True,'question':'Does this synthetic trend rule miss reversals and pay turnover costs?','symbol':'SYNTHETIC','phase':'development','data_audit_passed':True,'benchmark':'same-asset buy-and-hold','engine':{'strategy':'sma','fast':10,'slow':40,'initial_cash':100000,'fee_bps':10,'slippage_bps':5,'lot_size':1,'evaluation_start':rows[50]['date'],'currency':'USD','terminal_liquidation':True},'limitations':['SYNTHETIC DEMO. No conclusion about any actual security.']}
    result=execute(data,plan,out/'research','demo')
    (out/'result.json').write_text(json.dumps(result,indent=2,allow_nan=False))
    (out/'report.html').write_text(render_report(result,title='QuantCorner · Backtesting Research'))
    return out/'report.html'
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);a=p.parse_args()
    try:print(demo(a.output))
    except (ValueError,OSError) as e:p.exit(2,str(e)+'\n')
