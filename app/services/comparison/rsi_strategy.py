from typing import List, Dict, TypedDict
from app.models.strategy import FundData
import pandas as pd
import matplotlib.pyplot as plt
import os
from pathlib import Path


class TradeResult(TypedDict):
    date: str          # Trade date
    action: str        # 'BUY' or 'SELL'
    units: float       # Number of units traded
    price: float       # Price per unit
    amount: float      # Total amount
    remaining_cash: float  # Cash left after trade
    total_value: float    # Portfolio value after trade


class Portfolio:
    def __init__(self, initial_cash: float = 100000.0):
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.units = 0.0
        self.trades: List[TradeResult] = []

    def can_buy(self, amount: float) -> bool:
        return self.cash >= amount

    def buy(self, date: str, price: float, amount: float) -> None:
        if not self.can_buy(amount):
            return

        units = amount / price
        self.units += units
        self.cash -= amount

        self.trades.append({
            'date': date,
            'action': 'BUY',
            'units': units,
            'price': price,
            'amount': amount,
            'remaining_cash': self.cash,
            'total_value': self.get_total_value(price)
        })

    def sell(self, date: str, price: float, units: float) -> None:
        if units > self.units:
            units = self.units

        amount = units * price
        self.units -= units
        self.cash += amount

        self.trades.append({
            'date': date,
            'action': 'SELL',
            'units': units,
            'price': price,
            'amount': amount,
            'remaining_cash': self.cash,
            'total_value': self.get_total_value(price)
        })

    def get_total_value(self, current_price: float) -> float:
        return self.cash + (self.units * current_price)


def calculate_rsi(prices: List[float], period: int = 14) -> List[float]:
    """Calculate RSI values for the price series"""
    rsi_values = []
    if len(prices) <= period:
        return [50.0] * len(prices)  # Default neutral RSI

    # Calculate price changes
    changes = [prices[i+1] - prices[i] for i in range(len(prices)-1)]

    # Calculate initial averages
    gains = []
    losses = []

    for change in changes[:period]:
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    # Calculate RSI for the first period
    if avg_loss == 0:
        rsi = 100
    else:
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

    rsi_values.extend([50.0] * period)  # Pad initial values
    rsi_values.append(rsi)

    # Calculate RSI for remaining periods
    for i in range(period, len(changes)):
        change = changes[i]
        gain = change if change > 0 else 0
        loss = abs(change) if change < 0 else 0

        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

        rsi_values.append(rsi)

    return rsi_values


def basic_rsi_strategy(data: List[FundData], initial_cash: float = 100000.0) -> Portfolio:
    """Basic RSI strategy - only buy when RSI < 30"""
    portfolio = Portfolio(initial_cash)
    prices = [float(day['DWJZ']) for day in data]
    rsi_values = calculate_rsi(prices)

    for idx, (day_data, rsi) in enumerate(zip(data, rsi_values)):
        price = float(day_data['DWJZ'])

        # Buy signal: RSI < 30
        if rsi < 40:
            investment = 1000.0  # Fixed investment amount
            if portfolio.can_buy(investment):
                portfolio.buy(day_data['FSRQ'], price, investment)

    return portfolio


def advanced_rsi_strategy(data: List[FundData], initial_cash: float = 100000.0) -> Portfolio:
    """Advanced RSI strategy with both buy and sell signals"""
    portfolio = Portfolio(initial_cash)
    prices = [float(day['DWJZ']) for day in data]
    rsi_values = calculate_rsi(prices)

    for idx, (day_data, rsi) in enumerate(zip(data, rsi_values)):
        price = float(day_data['DWJZ'])

        # Buy signal: RSI < 30
        if rsi < 40:
            # Dynamic investment based on RSI
            investment = 1000
            if portfolio.can_buy(investment):
                portfolio.buy(day_data['FSRQ'], price, investment)

        # Sell signal: RSI > 70
        elif rsi > 75 and portfolio.units > 0:
            # Sell 30% of holdings when RSI is high
            units_to_sell = portfolio.units * 0.25
            portfolio.sell(day_data['FSRQ'], price, units_to_sell)

    return portfolio


async def compare_rsi_strategies():
    """Compare the two RSI strategies across all funds"""
    fund_dir = 'data'
    results = {}

    # Create results directory if it doesn't exist
    output_dir = Path('results/rsi_comparison')
    output_dir.mkdir(parents=True, exist_ok=True)

    for file_name in os.listdir(fund_dir):
        if not file_name.endswith('.csv'):
            continue

        fund_code = file_name.split('.')[0]
        file_path = os.path.join(fund_dir, file_name)

        print(f"\nAnalyzing fund: {fund_code}")

        # Load fund data
        df = pd.read_csv(file_path)
        fund_data = [
            {'FSRQ': row['FSRQ'], 'DWJZ': str(
                row['DWJZ']), 'JZZZL': str(row['JZZZL'])}
            for _, row in df.iterrows()
        ]

        # Run both strategies
        basic_portfolio = basic_rsi_strategy(fund_data)
        advanced_portfolio = advanced_rsi_strategy(fund_data)

        # Calculate final results
        final_price = float(fund_data[-1]['DWJZ'])

        basic_final_value = basic_portfolio.get_total_value(final_price)
        basic_return = ((basic_final_value - basic_portfolio.initial_cash) /
                        basic_portfolio.initial_cash * 100)

        advanced_final_value = advanced_portfolio.get_total_value(final_price)
        advanced_return = ((advanced_final_value - advanced_portfolio.initial_cash) /
                           advanced_portfolio.initial_cash * 100)

        results[fund_code] = {
            'Basic RSI': {
                'final_value': basic_final_value,
                'return_rate': basic_return,
                'trades': len(basic_portfolio.trades)
            },
            'Advanced RSI': {
                'final_value': advanced_final_value,
                'return_rate': advanced_return,
                'trades': len(advanced_portfolio.trades)
            }
        }

        print(f"\nBasic RSI Strategy:")
        print(f"最终价值: {basic_final_value:.2f} 元")
        print(f"收益率: {basic_return:.2f}%")
        print(f"交易次数: {len(basic_portfolio.trades)}")

        print(f"\nAdvanced RSI Strategy:")
        print(f"最终价值: {advanced_final_value:.2f} 元")
        print(f"收益率: {advanced_return:.2f}%")
        print(f"交易次数: {len(advanced_portfolio.trades)}")

    # Generate visualization
    plot_strategy_comparison(results, output_dir / 'rsi_comparison.png')
    generate_markdown_report(results, output_dir / 'rsi_comparison.md')


def plot_strategy_comparison(results: dict, output_path: str):
    """Create visualization comparing the two strategies"""
    funds = list(results.keys())
    basic_returns = [results[fund]['Basic RSI']['return_rate']
                     for fund in funds]
    advanced_returns = [results[fund]['Advanced RSI']
                        ['return_rate'] for fund in funds]

    plt.figure(figsize=(15, 8))
    x = range(len(funds))

    plt.plot(x, basic_returns, 'b.-', label='Basic RSI',
             linewidth=2, markersize=8)
    plt.plot(x, advanced_returns, 'r.-',
             label='Advanced RSI', linewidth=2, markersize=8)

    plt.title('RSI Strategy Comparison Across Funds')
    plt.xlabel('Fund Code')
    plt.ylabel('Return Rate (%)')
    plt.xticks(x, funds, rotation=45)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()


def generate_markdown_report(results: dict, output_path: str):
    """Generate detailed markdown report"""
    lines = ["# RSI Strategy Comparison Report\n"]

    # Summary table
    lines.extend([
        "## Performance Summary\n",
        "| Fund Code | Basic RSI Return | Advanced RSI Return | Basic Trades | Advanced Trades |",
        "|-----------|------------------|-------------------|--------------|-----------------|"
    ])

    # Calculate averages
    total_basic_return = 0
    total_advanced_return = 0
    total_basic_trades = 0
    total_advanced_trades = 0

    for fund, data in results.items():
        basic = data['Basic RSI']
        advanced = data['Advanced RSI']

        lines.append(
            f"| {fund} | {basic['return_rate']:.2f}% | {
                advanced['return_rate']:.2f}% | "
            f"{basic['trades']} | {advanced['trades']} |"
        )

        total_basic_return += basic['return_rate']
        total_advanced_return += advanced['return_rate']
        total_basic_trades += basic['trades']
        total_advanced_trades += advanced['trades']

    # Add averages
    fund_count = len(results)
    lines.extend([
        "|-----------|------------------|-------------------|--------------|-----------------|",
        f"| Average | {total_basic_return/fund_count:.2f}% | "
        f"{total_advanced_return/fund_count:.2f}% | "
        f"{total_basic_trades/fund_count:.1f} | {total_advanced_trades/fund_count:.1f} |"
    ])

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


if __name__ == "__main__":
    import asyncio
    asyncio.run(compare_rsi_strategies())
