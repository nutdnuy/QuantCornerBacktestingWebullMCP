import sys,unittest,datetime as dt
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from analytics import drawdown_analysis
from engine import metrics,DEFAULTS,run

class Chapter14Tests(unittest.TestCase):
    def dd(self,values):
        first=dt.date(2024,1,1)
        return drawdown_analysis(values,100,[first+dt.timedelta(days=i+1) for i in range(len(values))],first)
    def test_recovery_intervals_and_return(self):
        d=self.dd([90,80,90,100])['worst_episode']
        self.assertEqual((d['drawdown_period'],d['recovery_period'],d['underwater_period']),(2,2,4))
        self.assertAlmostEqual(d['recovery_return_required'],.25)
        self.assertEqual(d['recovery_date'],'2024-01-05')
    def test_unrecovered_is_censored(self):
        d=self.dd([80,90,85]);w=d['worst_episode']
        self.assertIsNone(w['recovery_period']);self.assertIsNone(w['underwater_period'])
        self.assertEqual(w['elapsed_underwater'],3);self.assertIsNone(d['longest_completed_underwater'])
    def test_deepest_not_longest(self):
        d=self.dd([70,100,90,95,92,96,100])
        self.assertEqual(d['worst_episode']['underwater_period'],2)
        self.assertEqual(d['longest_completed_underwater'],5)
        self.assertIsNone(d['current_episode'])
    def test_no_drawdown(self):
        d=self.dd([100,110,110]);self.assertIsNone(d['worst_episode'])
        self.assertEqual(d['longest_observed_underwater'],0)
    def test_flat_trades_rates_and_expectancy(self):
        dates=[dt.date(2024,1,2),dt.date(2024,1,3)]
        m=metrics([100,110],100,dates,dt.date(2024,1,1),[{'net_pnl':p} for p in [30,-10,0]],DEFAULTS)
        self.assertAlmostEqual(m['win_rate']+m['loss_rate']+m['breakeven_rate'],1)
        self.assertEqual(m['average_win'],30);self.assertEqual(m['average_loss'],10)
        self.assertEqual(m['payoff'],3);self.assertEqual(m['profit_factor'],3)
        self.assertAlmostEqual(m['expectancy'],20/3);self.assertIsNone(m['breakeven_win_rate'])
    def test_breakeven_threshold_and_missing_loss(self):
        args=([100],100,[dt.date(2024,1,2)],dt.date(2024,1,1))
        m=metrics(*args,[{'net_pnl':30},{'net_pnl':-10}],DEFAULTS)
        self.assertEqual(m['breakeven_win_rate'],.25)
        m=metrics(*args,[{'net_pnl':30}],DEFAULTS)
        self.assertIsNone(m['average_loss']);self.assertIsNone(m['profit_factor'])
    def result(self,liquidate):
        bars=[{'date':f'2024-01-0{i+1}','open':p,'high':p,'low':p,'close':p,'volume':10000,'target':1} for i,p in enumerate([100,100,110])]
        return run(bars,{'strategy':'targets','initial_cash':1000,'fee_bps':100,'slippage_bps':100,'terminal_liquidation':liquidate})
    def test_closed_costs_reconcile_actual_quantities(self):
        r=self.result(True);m=r['metrics']
        self.assertEqual(m['filled_orders'],2)
        self.assertAlmostEqual(m['closed_gross_pnl'],90)
        self.assertAlmostEqual(m['modeled_slippage'],18.9)
        self.assertAlmostEqual(m['total_fees'],18.891)
        self.assertAlmostEqual(m['closed_gross_pnl']-m['closed_trade_cost'],m['closed_net_pnl'])
        self.assertAlmostEqual(m['closed_net_pnl'],r['equity'][-1]['equity']-1000)
    def test_open_costs_not_closed_pnl(self):
        r=self.result(False);m=r['metrics']
        self.assertEqual(m['filled_orders'],1);self.assertEqual(m['closed_trade_cost'],0)
        self.assertAlmostEqual(m['total_fees'],9.09);self.assertAlmostEqual(m['modeled_slippage'],9)
        self.assertEqual(m['closed_net_pnl'],0)
        self.assertGreater(r['open_position']['marked_pnl'],0)

if __name__=='__main__':unittest.main()
