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
        self.total_units = 0.0  # Total fund units
        self.total_cost = 0.0   # Total investment amount
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


def ma_cross_strategy(current_value: float, prev_value: float | None, date_index: int,
                      price_history: List[float], ma_short: int = 5, ma_long: int = 20) -> float:
    """Strategy 4:
    Moving Average Crossover Strategy
    Invest when short MA crosses above long MA (Golden Cross)"""
    if date_index < ma_long:  # Not enough data
        return 0.0

    short_ma = sum(price_history[date_index-ma_short:date_index]) / ma_short
    long_ma = sum(price_history[date_index-ma_long:date_index]) / ma_long

    # Previous day's MAs
    prev_short_ma = sum(
        price_history[date_index-ma_short-1:date_index-1]) / ma_short
    prev_long_ma = sum(
        price_history[date_index-ma_long-1:date_index-1]) / ma_long

    # Golden Cross: Short MA crosses above Long MA
    if prev_short_ma <= prev_long_ma and short_ma > long_ma:
        return 2000.0
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
    """ Strategy 7: Enhanced RSI Strategy
    Non-linear investment based on RSI level and daily price change

    Investment amount is determined by:
    1. RSI level (lower RSI = higher base investment)
    2. Daily price drop (bigger drop = higher multiplier)
    """
    if date_index < period:
        return 0.0

    # Calculate RSI (same as before)
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

    # Early exit if RSI is too high
    if rsi >= 40:
        return 0.0

    # Calculate base investment from RSI
    rsi_score = (40 - rsi) / 40  # RSI 40->0, RSI 0->1
    base_investment = 1000 * math.exp(rsi_score * 1.6)

    # Calculate daily price change multiplier
    if prev_value:
        daily_drop = (prev_value - current_value) / prev_value * 100
        if daily_drop > 0:  # Only increase investment on price drops
            # Exponential multiplier based on daily drop
            # 1% drop -> 1.1x, 2% -> 1.2x, 3% -> 1.35x, 5% -> 1.7x
            drop_multiplier = 1 + math.exp(daily_drop/5) / 10
            base_investment *= drop_multiplier

    return min(base_investment, 5000.0)  # Still cap at 5000


def calculate_investment(data: List[FundData], strategy_func: Callable) -> Investment:
    """Calculate investment results based on given strategy"""
    inv = Investment()
    prev_value = None

    for idx, day_data in enumerate(data):
        current_value = float(day_data['DWJZ'])

        # Get investment amount from strategy
        investment_amount = strategy_func(current_value, prev_value, idx)

        if investment_amount > 0:
            units = investment_amount / current_value
            inv.total_units += units
            inv.total_cost += investment_amount
            inv.transactions.append(
                (day_data['FSRQ'], units, investment_amount))

        prev_value = current_value

    return inv
