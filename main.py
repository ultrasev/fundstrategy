import httpx
import asyncio
from datetime import datetime
from typing import TypedDict, List, Callable
import json
from abc import ABC, abstractmethod
import math
import pandas as pd
import os
import matplotlib.pyplot as plt
import seaborn as sns
from app.data.fetch import fetch_fund_data
from app.models.strategy import (FundData, Investment, fixed_drop_strategy, dynamic_drop_strategy,
                                 periodic_strategy, ma_cross_strategy, rsi_strategy, enhanced_rsi_strategy,
                                 calculate_investment,
                                 value_averaging_strategy)


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


def plot_strategy_comparison(results: dict):
    """Plot strategy comparison across different funds using line plots"""
    # Prepare data for plotting
    strategies = list(next(iter(results.values())).keys()
                      )  # Get strategy names
    funds = list(results.keys())
    funds.sort(key=lambda x: results[x]
               ['Enhanced RSI']['profit_rate'], reverse=True)

    plt.figure(figsize=(15, 8))

    # Plot a line for each strategy
    for strategy in strategies:
        returns = [results[fund][strategy]['profit_rate'] for fund in funds]
        plt.plot(funds, returns, marker='.',
                 label=strategy, linewidth=2, markersize=8)

    plt.title('Strategy Performance Comparison Across Funds')
    plt.xlabel('Fund Code')
    plt.ylabel('Return Rate (%)')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.xticks(rotation=45)
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig('strategy_comparison.png', bbox_inches='tight', dpi=300)
    plt.close()


def generate_markdown_table(results: dict):
    """Generate markdown table comparing strategy returns across funds with averages"""
    if not results:
        return "No results to display"

    # Get strategy names from first fund's results
    strategies = list(next(iter(results.values())).keys())

    # Create header
    header = "| Fund Code | " + " | ".join(strategies) + " |"
    separator = "|-----------|" + "|".join(["-" * 15] * len(strategies)) + "|"

    # Create rows and calculate averages
    rows = []
    strategy_sums = {strategy: 0.0 for strategy in strategies}
    fund_count = len(results)

    for fund_code, fund_results in results.items():
        row_values = []
        for strategy in strategies:
            profit_rate = fund_results[strategy]['profit_rate']
            strategy_sums[strategy] += profit_rate
            row_values.append(f"{profit_rate:.2f}%")
        rows.append(f"| {fund_code} | " + " | ".join(row_values) + " |")

    # Add average row
    avg_values = [f"{strategy_sums[strategy] /
                     fund_count:.2f}%" for strategy in strategies]
    avg_row = "| Average | " + " | ".join(avg_values) + " |"

    # Combine all parts
    markdown_table = "\n".join([
        header,
        separator,
        "\n".join(rows),
        separator,  # Add separator before average row
        avg_row
    ])

    # Save to file
    with open('strategy_comparison.md', 'w', encoding='utf-8') as f:
        f.write("# Strategy Comparison Results\n\n")
        f.write(markdown_table)

    return markdown_table


async def main():
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
    plot_strategy_comparison(results)
    print("\n Image saved to 'strategy_comparison.png'")

    # Generate markdown table
    markdown_table = generate_markdown_table(results)
    print("\nMarkdown table has been generated and saved to 'strategy_comparison.md'")
    print("\nTable preview:")
    print(markdown_table)


if __name__ == "__main__":
    asyncio.run(main())
