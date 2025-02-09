import random
import numpy as np


def generate_daily_change(is_upward: bool) -> float:
    """
    Generate daily price change based on trend direction

    Args:
        is_upward: Whether the stock is in an upward trend

    Returns:
        Daily price change percentage
    """
    if is_upward:
        # Upward trend: 0% to +10%
        return random.uniform(0, 0.1)
    else:
        # Downward trend: -10% to 0%
        return random.uniform(-0.1, 0)


def simulate_single_trade(
    success_rate: float = 0.4,
    profit_target: float = 0.12,
    stop_loss: float = -0.06
) -> float:
    """
    Simulate a single trade with proper handling of daily price limits

    Args:
        success_rate: Probability of choosing the correct trend direction
        profit_target: Percentage to take profit (e.g., 0.1 for 10%)
        stop_loss: Percentage to stop loss (e.g., -0.05 for -5%)

    Returns:
        Return percentage of the trade
    """
    # Initialize trade
    current_stock_value = 100
    daily_change = generate_daily_change(is_upward_trend)
    while True:
        is_upward_trend = random.random() < success_rate
        potential_profit_loss = (
            current_stock_value * (1 + daily_change) - 100) / 100

        # Check if the daily change would exceed our limits
        if potential_profit_loss >= profit_target:
            return profit_target
        elif potential_profit_loss <= stop_loss:
            return stop_loss
        else:
            current_stock_value *= (1 + daily_change)

# Run multiple simulations


def analyze_strategy(
    num_simulations: int = 10000,
    success_rate: float = 0.4,
    profit_target: float = 0.2,
    stop_loss: float = -0.05
) -> dict:
    """
    Analyze trading strategy through multiple simulations

    Args:
        num_simulations: Number of trades to simulate
        success_rate: Probability of choosing the correct trend direction
        profit_target: Percentage to take profit (e.g., 0.1 for 10%)
        stop_loss: Percentage to stop loss (e.g., -0.05 for -5%)

    Returns:
        Dictionary containing:
        - average_return: Average return per trade
        - win_rate: Percentage of profitable trades
        - all_returns: List of all trade returns
    """
    all_returns = []
    profitable_trades = 0

    for _ in range(num_simulations):
        trade_return = simulate_single_trade(
            success_rate, profit_target, stop_loss)
        all_returns.append(trade_return)
        if trade_return > 0:
            profitable_trades += 1

    average_return = sum(all_returns) / num_simulations
    win_rate = profitable_trades / num_simulations

    return {
        'average_return': average_return,
        'win_rate': win_rate,
        'all_returns': all_returns
    }


# Example usage
results = analyze_strategy(num_simulations=2000000)
print("Average return per trade: {:.2%}".format(results['average_return']))
print("Win rate: {:.2%}".format(results['win_rate']))
