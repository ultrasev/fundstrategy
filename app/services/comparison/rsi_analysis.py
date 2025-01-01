import os
import pandas as pd
from typing import List, Dict, Callable
from app.models.strategy import FundData, Investment
from app.workers.draw import draw_strategy_comparison
from app.workers.text import generate_markdown_table


def create_rsi_strategy(threshold: int) -> Callable:
    """Factory function to create RSI strategy with different thresholds

    Args:
        threshold: RSI threshold to trigger investment
    Returns:
        Strategy function with specified RSI threshold
    """
    def strategy(current_value: float, prev_value: float | None, date_index: int,
                price_history: List[float], period: int = 14) -> float:
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

        # Invest based on threshold
        if rsi < threshold:
            return 1000.0
        return 0.0

    return strategy


def calculate_investment(data: List[FundData], strategy_func: Callable) -> Investment:
    """Calculate investment results based on given strategy"""
    inv = Investment()
    prev_value = None
    price_history = [float(day['DWJZ']) for day in data]

    for idx, day_data in enumerate(data):
        current_value = float(day_data['DWJZ'])
        investment_amount = strategy_func(current_value, prev_value, idx, price_history)

        if investment_amount > 0:
            units = investment_amount / current_value
            inv.total_units += units
            inv.total_cost += investment_amount
            inv.transactions.append((day_data['FSRQ'], units, investment_amount))

        prev_value = current_value

    return inv


async def analyze_rsi_thresholds():
    """Analyze different RSI thresholds and compare their performance"""
    fund_dir = 'data'
    results = {}

    # Define RSI thresholds to test
    thresholds = [20, 25, 30, 35, 40, 45, 50, 55, 60]

    # Process each fund file
    for file_name in os.listdir(fund_dir):
        if not file_name.endswith('.csv'):
            continue

        fund_code = file_name.split('.')[0]
        file_path = os.path.join(fund_dir, file_name)

        print("Processing fund: {}".format(fund_code))

        # Load fund data
        df = pd.read_csv(file_path)
        fund_data = []
        for _, row in df.iterrows():
            fund_data.append({
                'FSRQ': row['FSRQ'],
                'DWJZ': str(row['DWJZ']),
                'JZZZL': str(row['JZZZL'])
            })

        results[fund_code] = {}

        # Test each threshold
        for threshold in thresholds:
            strategy_name = "RSI_{}".format(threshold)
            strategy_func = create_rsi_strategy(threshold)

            investment = calculate_investment(fund_data, strategy_func)
            final_value = float(fund_data[-1]['DWJZ']) * investment.total_units
            profit = final_value - investment.total_cost
            profit_rate = (profit / investment.total_cost) * 100 if investment.total_cost > 0 else 0

            results[fund_code][strategy_name] = {
                'total_cost': investment.total_cost,
                'total_units': investment.total_units,
                'final_value': final_value,
                'profit': profit,
                'profit_rate': profit_rate
            }

            print("\nRSI Threshold {}: ".format(threshold))
            print("Total Investment: {:.2f}".format(investment.total_cost))
            print("Profit Rate: {:.2f}%".format(profit_rate))

    # Save results
    draw_strategy_comparison(results, 'results/comparison/rsi_threshold_analysis.png')
    print("\nImage saved to 'results/comparison/rsi_threshold_analysis.png'")

    generate_markdown_table(results, 'results/comparison/rsi_threshold_analysis.md')
    print("\nMarkdown table saved to 'results/comparison/rsi_threshold_analysis.md'")