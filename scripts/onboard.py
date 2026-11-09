"""Check the local runtime and initialize a private draft without claiming MCP access."""
import argparse,json,sys
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from handoff import initialize

def setup(workspace):
    if sys.version_info < (3,9):raise ValueError('Python 3.9+ required')
    try: ZoneInfo('America/New_York')
    except ZoneInfoNotFoundError as exc: raise ValueError('Install the host IANA timezone database before normalizing Webull bars') from exc
    root=Path(__file__).resolve().parents[1]
    if not (root/'assets/quantcorner-mark-light.svg').is_file():raise ValueError('Missing authentic logo')
    w=Path(workspace).expanduser().resolve();w.mkdir(parents=True,exist_ok=True)
    initialize(w)
    state={'schema_version':1,'local_runtime':'ready','webull_connection':'not_checked','capabilities':{},'grill_me':'discover_in_host','secrets_stored':False}
    plan={'plan_version':1,'hypothesis':None,'development_start':None,'development_end':None,'holdout_start':None,'holdout_end':None,'robustness_scenarios':[],'candidate_identity':None,'candidate_locked':False,'approved':False,'question':None,'symbol':None,'phase':'development','data_audit_passed':False,'price_only_diagnostic_acknowledged':False,'engine':{'strategy':'sma','fast':20,'slow':200,'initial_cash':None,'fee_bps':None,'slippage_bps':None,'lot_size':None,'annual_rf':0,'annual_mar':0,'terminal_liquidation':False,'currency':'USD'},'benchmark':'same-asset buy-and-hold','limitations':[]}
    for name,obj in [('onboarding.json',state),('plan.json',plan)]:
        path=w/name
        if not path.exists():path.write_text(json.dumps(obj,indent=2)+'\n')
    if not (w/'.gitignore').exists():(w/'.gitignore').write_text('*\n')
    return {'workspace':str(w),'local_runtime':'ready','webull_connection':'not_checked','next':'Discover host Webull tools, run smoke test, then grill-me interview; complete plan.json.'}
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--workspace',required=True);a=p.parse_args()
    try:print(json.dumps(setup(a.workspace),indent=2))
    except (ValueError,OSError) as e:p.exit(2,str(e)+'\n')
