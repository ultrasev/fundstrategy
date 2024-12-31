import os
import pandas as pd
from app.models.strategy import (FundData, Investment, fixed_drop_strategy, dynamic_drop_strategy,
                                 periodic_strategy, ma_cross_strategy, rsi_strategy, enhanced_rsi_strategy,
                                 calculate_investment,
                                 value_averaging_strategy)

from app.workers.draw import draw_strategy_comparison
from app.workers.text import generate_markdown_table
from app.data.fetch import fetch_fund_data
from typing import List


async def load_fund_data_from_csv(file_path: str) -> List[FundData]:
    """Load fund data from CSV file"""
    df = pd.read_csv(file_path)
    # Convert DataFrame to List[FundData]
    fund_data = []
    for _, row in df.iterrows():
        fund_data.append({
            'FSRQ': row['FSRQ'],
            'DWJZ': str(row['DWJZ']),
            'JZZZL': str(row['JZZZL'])
        })
    return fund_data


async def profits():
    # Replace with your fund data directory
    fund_dir = 'data'
    results = {}

    # Process each fund file
    for file_name in os.listdir(fund_dir):
        if not file_name.endswith('.csv'):
            continue

        fund_code = file_name.split('.')[0]
        file_path = os.path.join(fund_dir, file_name)

        print(f"\nProcessing fund: {fund_code}")
        fund_data = await load_fund_data_from_csv(file_path)

        # Convert price history for MA and RSI calculations
        price_history = [float(day['DWJZ']) for day in fund_data]

        strategies = {
            "Fixed Drop": fixed_drop_strategy,
            "Dynamic Drop": dynamic_drop_strategy,
            "Periodic": periodic_strategy,
            "MA Cross": lambda c, p, i: ma_cross_strategy(c, p, i, price_history),
            "RSI": lambda c, p, i: rsi_strategy(c, p, i, price_history),
            "Enhanced RSI": lambda c, p, i: enhanced_rsi_strategy(c, p, i, price_history),
            "Value Avg": value_averaging_strategy,
        }

        results[fund_code] = {}

        for strategy_name, strategy_func in strategies.items():
            investment = calculate_investment(fund_data, strategy_func)
            final_value = float(fund_data[-1]['DWJZ']) * investment.total_units
            profit = final_value - investment.total_cost
            profit_rate = (profit / investment.total_cost) * \
                100 if investment.total_cost > 0 else 0

            results[fund_code][strategy_name] = {
                'total_cost': investment.total_cost,
                'total_units': investment.total_units,
                'final_value': final_value,
                'profit': profit,
                'profit_rate': profit_rate
            }

            print(f"\n{strategy_name}:")
            print(f"总投入: {investment.total_cost:.2f} 元")
            print(f"收益率: {profit_rate:.2f}%")

    # Plot results
    draw_strategy_comparison(results, 'results/comparison/profit.png')
    print("\n Image saved to 'results/comparison/profit.png'")

    # Generate markdown table
    generate_markdown_table(results, 'results/comparison/profit.md')
    print("\nMarkdown table has been generated and saved to 'results/comparison/profit.md'")
