from typing import Dict, Any, List
import pandas as pd
import matplotlib.pyplot as plt
from app.models.strategy import (
    fixed_drop_strategy, dynamic_drop_strategy,
    periodic_strategy, ma_cross_strategy, rsi_strategy,
    enhanced_rsi_strategy, value_averaging_strategy,
    calculate_investment
)
from app.data.fetch import FundData
from pathlib import Path
import os


def analyze_investment_frequency(fund_data: list[FundData], strategy_results: Dict[str, Any]) -> dict:
    """Analyze investment frequency and amounts for a strategy"""
    total_days = len(fund_data)
    transactions = strategy_results.transactions

    if not transactions:
        return {
            'total_investments': 0,
            'avg_amount': 0,
            'max_amount': 0,
            'frequency_rate': 0,
        }

    amounts = [amount for _, _, amount in transactions]

    return {
        'total_investments': len(transactions),
        'avg_amount': sum(amounts) / len(transactions),
        'max_amount': max(amounts),
        'frequency_rate': (len(transactions) / total_days) * 100
    }


def plot_frequency_comparison(results: dict, output_path: str):
    """Plot investment frequency comparison"""
    strategies = list(next(iter(results.values())).keys())
    funds = list(results.keys())

    # Create subplots
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(20, 16))

    # Plot total investments
    plot_metric(ax1, results, funds, strategies, 'total_investments',
                'Total Number of Investments')

    # Plot average investment amount
    plot_metric(ax2, results, funds, strategies, 'avg_amount',
                'Average Investment Amount (¥)')

    # Plot maximum investment amount
    plot_metric(ax3, results, funds, strategies, 'max_amount',
                'Maximum Single Investment (¥)')

    # Plot investment frequency rate
    plot_metric(ax4, results, funds, strategies, 'frequency_rate',
                'Investment Frequency Rate (%)')

    plt.tight_layout()
    plt.savefig(output_path, bbox_inches='tight', dpi=300)
    plt.close()


def plot_metric(ax, results, funds, strategies, metric, title):
    """Helper function to plot individual metrics"""
    for strategy in strategies:
        values = [results[fund][strategy][metric] for fund in funds]
        ax.plot(funds, values, marker='.',
                label=strategy, linewidth=2, markersize=8)

    ax.set_title(title)
    ax.set_xlabel('Fund Code')
    ax.grid(True, linestyle='--', alpha=0.7)
    ax.tick_params(axis='x', rotation=45)
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')


def generate_frequency_tables(results: dict, output_dir: str):
    """Generate separate markdown tables for frequency and total investment"""
    strategies = list(next(iter(results.values())).keys())
    funds = list(results.keys())

    # Frequency table
    freq_lines = [
        "# Investment Frequency Analysis\n",
        "## Number of Investments by Strategy\n",
        "| Fund Code | " + " | ".join(strategies) + " |",
        "|" + "---|" * (len(strategies) + 1)
    ]

    # Calculate averages for frequency
    freq_sums = {strategy: 0 for strategy in strategies}

    for fund in funds:
        line = [fund]
        for strategy in strategies:
            freq = results[fund][strategy]['total_investments']
            freq_sums[strategy] += freq
            line.append(f"{freq}")
        freq_lines.append("| " + " | ".join(line) + " |")

    # Add average row for frequency
    avg_line = ["Average"]
    for strategy in strategies:
        avg = freq_sums[strategy] / len(funds)
        avg_line.append(f"{avg:.1f}")
    freq_lines.append("| " + " | ".join(avg_line) + " |")

    # Total investment table
    invest_lines = [
        "# Total Investment Analysis\n",
        "## Total Investment Amount by Strategy (¥)\n",
        "| Fund Code | " + " | ".join(strategies) + " |",
        "|" + "---|" * (len(strategies) + 1)
    ]

    # Calculate averages for total investment
    invest_sums = {strategy: 0 for strategy in strategies}

    for fund in funds:
        line = [fund]
        for strategy in strategies:
            total_amount = results[fund][strategy]['total_investments'] * results[fund][strategy]['avg_amount']
            invest_sums[strategy] += total_amount
            line.append(f"{total_amount:.2f}")
        invest_lines.append("| " + " | ".join(line) + " |")

    # Add average row for total investment
    avg_line = ["Average"]
    for strategy in strategies:
        avg = invest_sums[strategy] / len(funds)
        avg_line.append(f"{avg:.2f}")
    invest_lines.append("| " + " | ".join(avg_line) + " |")

    # Save tables
    with open(os.path.join(output_dir, 'frequency_count.md'), 'w', encoding='utf-8') as f:
        f.write("\n".join(freq_lines))

    with open(os.path.join(output_dir, 'total_investment.md'), 'w', encoding='utf-8') as f:
        f.write("\n".join(invest_lines))

def plot_separate_comparisons(results: dict, output_dir: str):
    """Create separate plots for frequency and total investment"""
    strategies = list(next(iter(results.values())).keys())
    funds = list(results.keys())

    # Plot investment frequency
    plt.figure(figsize=(12, 6))
    for strategy in strategies:
        values = [results[fund][strategy]['total_investments'] for fund in funds]
        plt.plot(funds, values, marker='.', label=strategy, linewidth=2, markersize=8)

    plt.title('Investment Frequency by Strategy')
    plt.xlabel('Fund Code')
    plt.ylabel('Number of Investments')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.xticks(rotation=45)
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'frequency_count.png'), bbox_inches='tight', dpi=300)
    plt.close()

    # Plot total investment amount
    plt.figure(figsize=(12, 6))
    for strategy in strategies:
        values = [results[fund][strategy]['total_investments'] * results[fund][strategy]['avg_amount']
                 for fund in funds]
        plt.plot(funds, values, marker='.', label=strategy, linewidth=2, markersize=8)

    plt.title('Total Investment Amount by Strategy')
    plt.xlabel('Fund Code')
    plt.ylabel('Total Investment (¥)')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.xticks(rotation=45)
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'total_investment.png'), bbox_inches='tight', dpi=300)
    plt.close()

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


async def analyze_frequencies():
    """Main function to analyze investment frequencies"""
    fund_dir = 'data'
    results = {}

    # Process each fund file
    for file_name in os.listdir(fund_dir):
        if not file_name.endswith('.csv'):
            continue

        fund_code = file_name.split('.')[0]
        file_path = os.path.join(fund_dir, file_name)

        print(f"\nAnalyzing fund: {fund_code}")

        # Read fund data using the same method as profit.py
        fund_data = await load_fund_data_from_csv(file_path)
        price_history = [float(day['DWJZ']) for day in fund_data]

        results[fund_code] = {}

        strategies = {
            "Fixed Drop": fixed_drop_strategy,
            "Dynamic Drop": dynamic_drop_strategy,
            "Periodic": periodic_strategy,
            "MA Cross": lambda c, p, i: ma_cross_strategy(c, p, i, price_history),
            "RSI": lambda c, p, i: rsi_strategy(c, p, i, price_history),
            "Enhanced RSI": lambda c, p, i: enhanced_rsi_strategy(c, p, i, price_history),
            "Value Avg": value_averaging_strategy,
        }

        for strategy_name, strategy_func in strategies.items():
            investment = calculate_investment(fund_data, strategy_func)
            results[fund_code][strategy_name] = analyze_investment_frequency(
                fund_data, investment)

            print(f"\n{strategy_name}:")
            print(f"投资次数: {results[fund_code][strategy_name]['total_investments']}")
            print(f"平均投资额: {results[fund_code][strategy_name]['avg_amount']:.2f} 元")

    # Create results directory if it doesn't exist
    output_dir = 'results/comparison'
    os.makedirs(output_dir, exist_ok=True)

    # Generate new visualizations and reports
    plot_separate_comparisons(results, output_dir)
    generate_frequency_tables(results, output_dir)

    print("\nAnalysis complete!")
    print("Results saved to:")
    print("- results/comparison/frequency_count.png")
    print("- results/comparison/frequency_count.md")
    print("- results/comparison/total_investment.png")
    print("- results/comparison/total_investment.md")


if __name__ == "__main__":
    import asyncio
    asyncio.run(analyze_frequencies())
