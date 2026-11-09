"""Hand-computable invariants, not checks for implementation wording."""
import datetime as dt
import importlib.util
import math
import pathlib
import unittest
import sys

PATH = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "engine.py"
sys.path.insert(0, str(PATH.parent))
spec = importlib.util.spec_from_file_location("engine", PATH)
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)


def bars(prices, targets=None, opens=None):
    result = []
    for i, close in enumerate(prices):
        op = opens[i] if opens else close
        row = {"date": (dt.date(2025, 1, 1) + dt.timedelta(days=i)).isoformat(),
               "open": op, "close": close, "high": max(op, close), "low": min(op, close), "volume": 1000}
        if targets is not None:
            row["target"] = targets[i]
        result.append(row)
    return result


def config(**extra):
    return {"strategy": "targets", "initial_cash": 1000, "fee_bps": 0, **extra}


class EngineTests(unittest.TestCase):
    def test_next_open_and_last_signal(self):
        data = bars([10, 14, 16, 18], [1, 0, 0, 1], [10, 12, 15, 18])
        result = engine.run(data, config())
        self.assertEqual(result["equity"][0]["position"], 0)
        self.assertEqual(result["orders"][0]["date"], "2025-01-02")
        self.assertEqual(result["orders"][0]["price"], 12)
        self.assertEqual(result["trades"][0]["net_pnl"], 249)
        self.assertEqual(result["equity"][-1]["equity"], 1249)
        self.assertEqual(len(result["orders"]), 2)
        self.assertEqual(result["metrics"]["closed_trades"], 1)
        self.assertIsNone(result["metrics"]["profit_factor"])
        self.assertAlmostEqual(result["reconciliation"]["residual"], 0)

    def test_costs_and_affordability(self):
        result = engine.run(bars([10, 10, 12], [1, 0, 0]), config(fee_bps=100, slippage_bps=100))
        self.assertEqual(result["orders"][0]["quantity"], 98)
        self.assertAlmostEqual(result["equity"][-1]["equity"], 1152.8996)
        self.assertTrue(all(r["cash"] >= 0 for r in result["equity"]))
        self.assertAlmostEqual(result["trades"][0]["net_pnl"], 152.8996)

    def test_board_lot_can_make_trade_unaffordable(self):
        result = engine.run(bars([10, 10], [1, 1]), config(initial_cash=999, lot_size=100))
        self.assertEqual(result["orders"], [])
        self.assertEqual(result["metrics"]["total_return"], 0)

    def test_open_position_reconciles_without_fake_closed_trade(self):
        result = engine.run(bars([10, 10, 15], [1, 1, 0]), config())
        self.assertEqual(result["metrics"]["closed_trades"], 0)
        self.assertIsNone(result["metrics"]["win_rate"])
        self.assertEqual(result["open_position"]["quantity"], 100)
        self.assertEqual(result["open_position"]["marked_pnl"], 500)
        self.assertAlmostEqual(result["reconciliation"]["residual"], 0)

    def test_terminal_liquidation_is_explicit_and_costed(self):
        result = engine.run(bars([10, 10, 15], [1, 1, 1]), config(terminal_liquidation=True, fee_bps=100))
        self.assertEqual(result["metrics"]["closed_trades"], 1)
        self.assertTrue(result["trades"][0]["terminal_liquidation"])
        self.assertEqual(result["open_position"]["quantity"], 0)
        self.assertAlmostEqual(result["equity"][-1]["equity"], 1470.25)
        self.assertAlmostEqual(result["reconciliation"]["residual"], 0)

    def test_initial_cost_drawdown_and_benchmark(self):
        result = engine.run(bars([10, 10, 10], [1, 1, 1]), config(fee_bps=100, terminal_liquidation=True))
        self.assertAlmostEqual(result["metrics"]["max_drawdown"], -0.0198)
        self.assertAlmostEqual(result["benchmark_metrics"]["max_drawdown"], -0.0198)

    def test_drawdown_and_loss_only_ratios(self):
        result = engine.run(bars([10, 10, 5, 5], [1, 1, 0, 0]), config())
        self.assertEqual(result["metrics"]["max_drawdown"], -0.5)
        self.assertEqual(result["metrics"]["win_rate"], 0)
        self.assertEqual(result["metrics"]["profit_factor"], 0)
        self.assertIsNone(result["metrics"]["payoff"])
        self.assertEqual(result["metrics"]["expectancy"], -500)

    def test_undefined_ratios(self):
        result = engine.run(bars([10, 10, 10], [0, 0, 0]), config())
        self.assertIsNone(result["metrics"]["sharpe"])
        self.assertIsNone(result["metrics"]["sortino"])
        self.assertIsNone(result["metrics"]["expectancy"])
        self.assertEqual(result["metrics"]["annualized_volatility"], 0)

    def test_warmup_is_not_a_return_period(self):
        result = engine.run(bars([5, 10, 12, 15]), {"strategy": "sma", "fast": 1, "slow": 2,
                            "evaluation_start": "2025-01-03", "initial_cash": 1200, "fee_bps": 0})
        self.assertEqual(len(result["equity"]), 2)
        self.assertEqual(result["orders"][0]["date"], "2025-01-03")
        self.assertEqual(result["metrics"]["total_return"], 0.25)
        self.assertEqual(result["initial_date"], "2025-01-02")

    def test_future_price_changes_do_not_change_prior_trades(self):
        a = bars([10, 11, 12, 11, 10, 13])
        b = bars([10, 11, 12, 11, 10, 999])
        cfg = {"fast": 1, "slow": 2, "fee_bps": 0}
        ra, rb = engine.run(a, cfg), engine.run(b, cfg)
        self.assertEqual(ra["equity"][:-1], rb["equity"][:-1])
        self.assertEqual(ra["orders"], rb["orders"])

    def test_zero_volume_no_fill(self):
        data = bars([10, 10, 12], [1, 1, 0]); data[1]["volume"] = 0
        result = engine.run(data, config())
        self.assertEqual(result["orders"][0]["date"], "2025-01-03")
        self.assertEqual(result["equity"][1]["position"], 0)
        data[-1]["volume"] = 0
        self.assertEqual(engine.run(data, config())["orders"], [])

    def test_ohlc_date_and_config_rejections(self):
        invalid = [config(lot_size=0), config(fee_bps=-1), config(slippage_bps=10000),
                   config(strategy="short"), config(annual_rf=-1), config(initial_cash=math.nan),
                   config(terminal_liquidation="yes"), config(unknown=True), config(fast=5, slow=2)]
        for cfg in invalid:
            with self.subTest(cfg=cfg), self.assertRaises(ValueError):
                engine.run(bars([10, 12], [1, 0]), cfg)
        data = bars([10, 12], [1, 0]);data[1]["date"] = data[0]["date"]
        with self.assertRaises(ValueError):engine.run(data, config())
        data = bars([10], [-1])
        with self.assertRaises(ValueError):engine.run(data, config())
        data = bars([10], [0]);data[0]["high"] = 9
        with self.assertRaises(ValueError):engine.run(data, config())
        data = bars([10], [0]);data[0]["volume"] = -1
        with self.assertRaises(ValueError):engine.run(data, config())


if __name__ == "__main__":
    unittest.main()
