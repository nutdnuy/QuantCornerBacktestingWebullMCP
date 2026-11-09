#!/usr/bin/env python3
"""Auditable single-asset, daily, long-only reference simulator (stdlib only).

No provider calls, optimization, order routing, or implicit dividend/corporate-action
adjustment. Signals are computed at close and execute no earlier than next open.
"""
import argparse
import datetime as dt
import json
import math
import statistics
from pathlib import Path
from analytics import drawdown_analysis, cost_statistics

DEFAULTS = {
    "strategy": "sma", "fast": 20, "slow": 200, "currency": "USD",
    "initial_cash": 100000.0, "fee_bps": 10.0, "slippage_bps": 0.0,
    "lot_size": 1, "annual_rf": 0.0, "annual_mar": 0.0,
    "periods_per_year": 252, "terminal_liquidation": False,
    "evaluation_start": None,
}


def number(value, label, lower=None, strict=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    if lower is not None and (value <= lower if strict else value < lower):
        raise ValueError(f"{label} is below its allowed range")
    return float(value)


def iso_date(value, label):
    if not isinstance(value, str):
        raise ValueError(f"{label} must be an ISO YYYY-MM-DD string")
    try:
        date = dt.date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{label} must be ISO YYYY-MM-DD") from exc
    if date.isoformat() != value:
        raise ValueError(f"{label} must be ISO YYYY-MM-DD")
    return date


def validated(bars, config):
    if not isinstance(config, dict):
        raise ValueError("config must be an object")
    unknown = set(config) - set(DEFAULTS)
    if unknown:
        raise ValueError(f"Unsupported config keys: {sorted(unknown)}")
    cfg = {**DEFAULTS, **config}
    if not isinstance(cfg["currency"], str) or len(cfg["currency"]) != 3 or not cfg["currency"].isascii() or not cfg["currency"].isalpha() or cfg["currency"] != cfg["currency"].upper():
        raise ValueError("currency must be a three-letter uppercase code")
    if cfg["strategy"] not in ("sma", "targets"):
        raise ValueError("strategy must be sma or targets; Short is unsupported")
    for key in ("fast", "slow", "lot_size", "periods_per_year"):
        if isinstance(cfg[key], bool) or not isinstance(cfg[key], int) or cfg[key] < 1:
            raise ValueError(f"{key} must be a positive integer")
    if cfg["fast"] >= cfg["slow"]:
        raise ValueError("fast must be smaller than slow")
    for key in ("fee_bps", "slippage_bps"):
        number(cfg[key], key, 0)
        if cfg[key] >= 10000:
            raise ValueError(f"{key} must be below 10000")
    number(cfg["initial_cash"], "initial_cash", 0, strict=True)
    number(cfg["annual_rf"], "annual_rf", -1, strict=True)
    number(cfg["annual_mar"], "annual_mar", -1, strict=True)
    if not isinstance(cfg["terminal_liquidation"], bool):
        raise ValueError("terminal_liquidation must be boolean")
    if not isinstance(bars, list) or not bars:
        raise ValueError("bars must be a nonempty array")
    clean, dates = [], []
    for i, bar in enumerate(bars):
        if not isinstance(bar, dict):
            raise ValueError(f"bar {i} must be an object")
        date = iso_date(bar.get("date"), f"bar {i} date")
        if dates and date <= dates[-1]:
            raise ValueError("bar dates must be unique and strictly ascending")
        row = {"date": date.isoformat()}
        for field in ("open", "high", "low", "close"):
            row[field] = number(bar.get(field), f"bar {i} {field}", 0, strict=True)
        row["volume"] = number(bar.get("volume"), f"bar {i} volume", 0)
        if row["low"] > min(row["open"], row["close"]) or row["high"] < max(row["open"], row["close"]):
            raise ValueError(f"bar {i} has inconsistent OHLC bounds")
        if cfg["strategy"] == "targets":
            target = bar.get("target")
            if isinstance(target, bool) or target not in (0, 1):
                raise ValueError(f"bar {i} target must be numeric 0 or 1; Short/leverage is unsupported")
            row["target"] = int(target)
        clean.append(row)
        dates.append(date)
    start = iso_date(cfg["evaluation_start"], "evaluation_start") if cfg["evaluation_start"] else dates[0]
    idx = next((i for i, date in enumerate(dates) if date >= start), None)
    if idx is None:
        raise ValueError("evaluation_start leaves no bars")
    return clean, cfg, dates, idx


def _finite(value):
    return value if value is not None and math.isfinite(value) else None


def metrics(values, initial, dates, initial_date, trades, cfg):
    returns = [b / a - 1 for a, b in zip([initial] + values[:-1], values)]
    n = len(returns)
    periods = cfg["periods_per_year"]
    vol_daily = statistics.stdev(returns) if n > 1 else None
    volatility = vol_daily * math.sqrt(periods) if vol_daily is not None else None
    rf = (1 + cfg["annual_rf"]) ** (1 / periods) - 1
    mar = (1 + cfg["annual_mar"]) ** (1 / periods) - 1
    downside = math.sqrt(sum(min(r - mar, 0) ** 2 for r in returns) / n)
    sharpe = (statistics.mean(returns) - rf) / vol_daily * math.sqrt(periods) if vol_daily else None
    sortino = (statistics.mean(returns) - mar) / downside * math.sqrt(periods) if downside else None
    peak, max_dd = initial, 0.0
    for value in values:
        peak = max(peak, value)
        max_dd = min(max_dd, value / peak - 1)
    years = (dates[-1] - initial_date).days / 365.25
    try:
        cagr = (values[-1] / initial) ** (1 / years) - 1 if years > 0 else None
    except OverflowError:
        cagr = None
    pnls = [t["net_pnl"] for t in trades]
    wins, losses = [x for x in pnls if x > 0], [-x for x in pnls if x < 0]
    dd = drawdown_analysis(values, initial, dates, initial_date)
    worst = dd['worst_episode'] or {}
    payoff = statistics.mean(wins) / statistics.mean(losses) if wins and losses else None
    result = {
        "winning_trades": len(wins), "losing_trades": len(losses),
        "breakeven_trades": sum(x == 0 for x in pnls),
        "loss_rate": len(losses) / len(pnls) if pnls else None,
        "breakeven_rate": sum(x == 0 for x in pnls) / len(pnls) if pnls else None,
        "average_win": statistics.mean(wins) if wins else None,
        "average_loss": statistics.mean(losses) if losses else None,
        "breakeven_win_rate": 1 / (1 + payoff) if payoff is not None and 0 not in pnls else None,
        "mean_daily_return": statistics.mean(returns),
        "annualized_arithmetic_return": statistics.mean(returns) * periods,
        "daily_volatility": vol_daily, "downside_deviation": downside,
        "mdd_drawdown_period": worst.get('drawdown_period'),
        "mdd_recovery_period": worst.get('recovery_period'),
        "mdd_underwater_period": worst.get('underwater_period'),
        "recovery_return_required": worst.get('recovery_return_required'),
        "current_underwater_period": (dd['current_episode'] or {}).get('elapsed_underwater', 0),
        "longest_completed_underwater": dd['longest_completed_underwater'],
        "longest_observed_underwater": dd['longest_observed_underwater'],
        "total_return": values[-1] / initial - 1, "cagr": _finite(cagr),
        "annualized_volatility": _finite(volatility), "max_drawdown": max_dd,
        "sharpe": _finite(sharpe), "sortino": _finite(sortino),
        "win_rate": len(wins) / len(pnls) if pnls else None,
        "payoff": statistics.mean(wins) / statistics.mean(losses) if wins and losses else None,
        "expectancy": statistics.mean(pnls) if pnls else None,
        "profit_factor": sum(wins) / sum(losses) if losses else None,
        "closed_trades": len(pnls),
    }
    return result


def run(bars, config=None):
    bars, cfg, dates, start = validated(bars, {} if config is None else config)
    initial = float(cfg["initial_cash"])
    fee, slip, lot = cfg["fee_bps"] / 10000, cfg["slippage_bps"] / 10000, cfg["lot_size"]
    # Prefix sums only use closes through each signal timestamp.
    signals, prefix = [], [0.0]
    for i, row in enumerate(bars):
        prefix.append(prefix[-1] + row["close"])
        if not math.isfinite(prefix[-1]):
            raise ValueError("price series exceeds numeric range")
        if cfg["strategy"] == "targets":
            signals.append(row["target"])
        elif i + 1 < cfg["slow"]:
            signals.append(0)
        else:
            fast = (prefix[i + 1] - prefix[i + 1 - cfg["fast"]]) / cfg["fast"]
            slow = (prefix[i + 1] - prefix[i + 1 - cfg["slow"]]) / cfg["slow"]
            signals.append(int(fast > slow))
    cash, shares, entry = initial, 0, None
    benchmark_cash, benchmark_shares, benchmark_entry = initial, 0, None
    benchmark_started = False
    equity, trades, benchmark_trades, orders = [], [], [], []
    peak = initial

    def buy(balance, price, date):
        fill = price * (1 + slip)
        unit_cost = fill * (1 + fee)
        qty = math.floor(balance / (unit_cost * lot)) * lot
        total = qty * unit_cost
        record = {"entry_date": date, "quantity": qty, "entry_price": fill,
                  "entry_cost": total, "entry_fee": qty * fill * fee,
                  "entry_slippage": qty * (fill - price)} if qty else None
        return max(0.0, balance - total), qty, record

    def sell(balance, qty, position, price, date, terminal=False):
        fill = price * (1 - slip)
        proceeds = qty * fill * (1 - fee)
        record = {**position, "exit_date": date, "exit_price": fill,
                  "exit_fee": qty * fill * fee, "exit_slippage": qty * (price - fill), "net_pnl": proceeds - position["entry_cost"],
                  "terminal_liquidation": terminal}
        return balance + proceeds, record

    for i in range(start, len(bars)):
        row = bars[i]
        target = signals[i - 1] if i else 0
        if row["volume"] > 0 and shares and target == 0:
            cash, trade = sell(cash, shares, entry, row["open"], row["date"])
            trades.append(trade)
            orders.append({"date": row["date"], "side": "sell", "quantity": shares, "price": trade["exit_price"]})
            shares, entry = 0, None
        elif row["volume"] > 0 and not shares and target == 1:
            cash, shares, entry = buy(cash, row["open"], row["date"])
            if shares:
                orders.append({"date": row["date"], "side": "buy", "quantity": shares, "price": entry["entry_price"]})
        if not benchmark_started and row["volume"] > 0:
            benchmark_cash, benchmark_shares, benchmark_entry = buy(initial, row["open"], row["date"])
            benchmark_started = True
        if i == len(bars) - 1 and cfg["terminal_liquidation"]:
            if row["volume"] == 0 and (shares or benchmark_shares):
                raise ValueError("cannot terminal-liquidate on a zero-volume bar")
            if shares:
                cash, trade = sell(cash, shares, entry, row["close"], row["date"], terminal=True)
                trades.append(trade)
                orders.append({"date": row["date"], "side": "sell", "quantity": shares, "price": trade["exit_price"], "terminal": True})
                shares, entry = 0, None
            if benchmark_shares:
                benchmark_cash, trade = sell(benchmark_cash, benchmark_shares, benchmark_entry, row["close"], row["date"], terminal=True)
                benchmark_trades.append(trade)
                benchmark_shares = 0
        value = cash + shares * row["close"]
        benchmark = benchmark_cash + benchmark_shares * row["close"]
        if not math.isfinite(value) or not math.isfinite(benchmark) or value <= 0 or benchmark <= 0:
            raise ValueError("nonfinite or nonpositive equity; inputs exceed numeric range")
        peak = max(peak, value)
        equity.append({"date": row["date"], "equity": value, "benchmark_equity": benchmark,
                       "drawdown": value / peak - 1, "position": shares, "cash": cash})
    initial_date = dates[start - 1] if start else dates[start] - dt.timedelta(days=1)
    values = [r["equity"] for r in equity]
    open_pnl = shares * bars[-1]["close"] - entry["entry_cost"] if entry else 0.0
    realized = sum(t["net_pnl"] for t in trades)
    warnings = ["Daily bars cannot establish intraday liquidity or fills; volume is not a fill guarantee.",
                "Input adjustment, dividends and corporate actions must be audited externally; no cash dividends are added.",
                "This is a single-asset long-only research reference, not a production execution simulator.",
                "Benchmark is buy-and-hold at the first positive-volume evaluation open with identical fee, slippage and lot conventions."]
    if cfg["strategy"] == "sma" and start < cfg["slow"]:
        warnings.append("Insufficient pre-evaluation SMA warmup: strategy stays in cash until a full slow window exists.")
    if cfg["terminal_liquidation"]:
        warnings.append("Final-close liquidation is an explicit accounting convention, not a next-open strategy signal.")
    if len(trades) < 30:
        warnings.append("Few closed trades: trading ratios describe this sample and are not reliable future probability estimates.")
    result = {
        "equity": equity, "trades": trades, "orders": orders,
        "metrics": metrics(values, initial, dates[start:], initial_date, trades, cfg),
        "benchmark_metrics": metrics([r["benchmark_equity"] for r in equity], initial, dates[start:], initial_date, benchmark_trades, cfg),
        "config": cfg, "initial_date": initial_date.isoformat(),
        "open_position": {"quantity": shares, "entry": entry, "marked_pnl": open_pnl},
        "reconciliation": {"initial_cash": initial, "final_equity": values[-1],
                           "realized_pnl": realized, "open_marked_pnl": open_pnl,
                           "residual": values[-1] - initial - realized - open_pnl},
        "validation": {"bars": len(bars), "evaluation_bars": len(equity), "warmup_bars": start,
                       "start": equity[0]["date"], "end": equity[-1]["date"]},
        "assumptions": ["Signals at close execute at the following observed bar open; no shorting or leverage.",
                        "Zero-volume bars prohibit fills; existing positions remain marked at close. Verify suspensions and stale marks externally.",
                        "Uninvested cash earns zero; no deposits, withdrawals, tax, financing, or participation model.",
                        "Fees and slippage apply per side; slippage increases buy prices and decreases sell prices.",
                        "CAGR uses actual days from the previous observed bar date (or previous calendar day) to the final mark.",
                        "Volatility and Sharpe use sample standard deviation; ratios use arithmetic daily excess returns and sqrt(periods_per_year).",
                        "Sortino downside deviation divides by all observations, relative to the daily-converted annual MAR.",
                        "Trade ratios use closed-trade net currency P&L; undefined ratios are null, never infinity.",
                        "SMA means fast above slow is long; equal/below is cash. Missing sessions are not interpolated."],
        "warnings": warnings,
    }
    result['metrics'].update(cost_statistics(trades, entry))
    result['benchmark_metrics'].update(cost_statistics(benchmark_trades, benchmark_entry if benchmark_shares else None))
    result['drawdown_analysis'] = drawdown_analysis(values, initial, dates[start:], initial_date)
    result['benchmark_drawdown_analysis'] = drawdown_analysis([r['benchmark_equity'] for r in equity], initial, dates[start:], initial_date)
    # Refuse invalid JSON numerics rather than publishing an attractive corrupt result.
    json.dumps(result, allow_nan=False)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Normalized bars JSON array")
    parser.add_argument("--config", required=True, help="Experiment config JSON object")
    parser.add_argument("--output", required=True, help="Result JSON; existing files are not overwritten")
    args = parser.parse_args()
    result = run(json.loads(Path(args.input).read_text()), json.loads(Path(args.config).read_text()))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n")


if __name__ == "__main__":
    main()
