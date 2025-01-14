import httpx
from typing import TypedDict, List, Callable
from abc import ABC, abstractmethod
import math


class FundData(TypedDict):
    FSRQ: str  # Date
    DWJZ: str  # Net Value
    JZZZL: str  # Change Rate


class Investment:
    def __init__(self):
        self.total_units = 0.0          # Current holding units
        self.total_cost = 0.0           # Current cost basis
        self.loss = 0.0  # Total loss
        # Date, units, cost
        self.transactions: List[tuple[str, float, float]] = []


def fixed_drop_strategy(current_value: float, prev_value: float | None, _: int) -> float:
    """Strategy 1: Invest 1000 whenever price drops"""
    if prev_value and current_value < prev_value:
        return 1000.0
    return 0.0


def dynamic_drop_strategy(current_value: float, prev_value: float | None, _: int) -> float:
    """Strategy 2: Invest based on drop percentage, max 3000"""
    if not prev_value:
        return 0.0

    drop_percent = (prev_value - current_value) / prev_value * 100
    if drop_percent <= 0:
        return 0.0

    # Non-linear investment function: more drop = more investment
    investment = 1000 * (1 + math.pow(drop_percent/2, 1.5))
    return min(investment, 3000.0)


def periodic_strategy(current_value: float, prev_value: float | None, date_index: int) -> float:
    """Strategy 3: Invest 1000 every 5 days"""
    return 1000.0 if date_index % 5 == 0 else 0.0


def ma_5_strategy(current_value: float, prev_value: float | None, date_index: int,
                  price_history: List[float], ma_short: int = 5, ma_long: int = 20) -> float:
    """Strategy 4:
    Buy when current price is below or equal to 5-day moving average
    This helps catch more buying opportunities at support levels
    """
    if date_index < ma_short:  # Need at least 5 days of data
        return 0.0

    # Calculate 5-day MA
    short_ma = sum(price_history[date_index-ma_short:date_index]) / ma_short

    # Buy signal: current price <= 5-day MA
    if current_value <= short_ma:
        return 1000.0
    return 0.0


def value_averaging_strategy(current_value: float, prev_value: float | None, date_index: int,
                             target_monthly_growth: float = 1000.0) -> float:
    """Strategy 5: Value Averaging
    Aims to grow portfolio by fixed amount each month"""
    # Assuming 20 trading days per month
    if date_index % 20 != 0:
        return 0.0

    month_number = date_index // 20
    target_value = target_monthly_growth * (month_number + 1)
    # You might want to track actual portfolio value
    current_portfolio_value = current_value

    needed_investment = target_value - current_portfolio_value
    return max(needed_investment, 0)  # Don't allow negative investments


def rsi_strategy(current_value: float, prev_value: float | None, date_index: int,
                 price_history: List[float], period: int = 14) -> float:
    """ Strategy 6: RSI Strategy
    Original RSI Strategy: Fixed investment when RSI < 30"""
    if date_index < period:
        return 0.0

    # Calculate RSI
    gains, losses = [], []
    for i in range(date_index - period, date_index):
        change = price_history[i+1] - price_history[i]
        if change >= 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    if avg_loss == 0:
        return 0.0

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    # Simple threshold-based investment
    if rsi < 30:
        return 1000.0
    elif rsi < 40:
        return 500.0

    return 0.0


def enhanced_rsi_strategy(current_value: float, prev_value: float | None, date_index: int,
                          price_history: List[float], period: int = 14) -> float:
    """Enhanced RSI Strategy focusing on core strengths:
    1. Aggressive buying at key RSI levels
    2. Simple but effective position sizing
    3. Quick response to oversold conditions
    """
    if date_index < period:
        return 0.0

    # Calculate RSI
    changes = [price_history[i+1] - price_history[i]
               for i in range(date_index - period, date_index)]
    gains = [change if change > 0 else 0 for change in changes]
    losses = [abs(change) if change < 0 else 0 for change in changes]

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    if avg_loss == 0:
        return 0.0

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    # Simplified but more aggressive position sizing
    if rsi < 15:
        return 8000.0
    elif rsi <= 20:  # Extremely oversold - go all in
        return 4000.0
    elif rsi <= 25:  # Heavily oversold
        return 2000.0
    elif rsi <= 30:  # Classic oversold
        return 1000.0

    return 0.0


def calculate_investment(data: List[FundData], strategy_func: Callable, stop_loss_threshold: float = 0.08) -> Investment:
    """Calculate investment results based on given strategy with stop-loss logic

    Args:
        data: List of fund data points
        strategy_func: Investment strategy function
        stop_loss_threshold: Liquidate position when loss exceeds this percentage (default 5%)

    Tracks both current position and historical cumulative amounts:
    - cumulative_investment: Total money invested over all periods
    - cumulative_redemption: Total money redeemed from liquidations
    """
    inv = Investment()
    prev_value = None

    for idx, day_data in enumerate(data):
        is_redeemed = False
        current_value = float(day_data['DWJZ'])

        # Check if loss exceeds threshold and clear position if true
        current_portfolio_value = inv.total_units * current_value
        if inv.total_cost > 0:
            loss_percentage = (
                inv.total_cost - current_portfolio_value) / inv.total_cost
            if loss_percentage > stop_loss_threshold:
                # total cost = total cost + loss
                inv.loss += inv.total_cost - current_portfolio_value
                inv.total_units = 0.0
                inv.total_cost = 0.0
                is_redeemed = True

        if not is_redeemed:
            # Get investment amount from strategy
            investment_amount = strategy_func(current_value, prev_value, idx)
            if investment_amount > 0:
                units = investment_amount / current_value
                inv.total_units += units
                inv.total_cost += investment_amount
                inv.transactions.append(
                    (day_data['FSRQ'], units, investment_amount)
                )

        prev_value = current_value

    inv.total_cost += inv.loss
    return inv
