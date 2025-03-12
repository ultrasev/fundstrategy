import asyncio
from app.data.fetch import fetch_fund_data
from decimal import Decimal

from app.fund.strategies import TStrategy, DynamicTStrategy


async def main(code: str = "010003"):
    data = await fetch_fund_data(code, 100)
    strategy = TStrategy(
        data,
        initial_shares=10000,
        sell_holds=1000,
        threshold_rate=1.0
    )
    cost, shares, last_price = strategy.calculate()
    avg_cost = cost / shares if shares else Decimal('0')
    profit = (last_price - avg_cost) * shares
    profit_rate = profit / cost

    print("Strategy Results:")
    print("Total Cost: {:.4f}".format(cost))
    print("Total Shares: {}".format(shares))
    print("Initial price: {:.4f}".format(float(data[0]['DWJZ'])))
    print("Average Cost per Share: {:.4f}".format(avg_cost))
    print("Profit: {:.4f}".format(profit))
    print("Profit Rate: \033[91m{:.4f}%\033[0m".format(profit_rate * 100))
    print("Default profit rate: \033[93m{:.4f}%\033[0m".format(
        (last_price / float(data[0]['DWJZ']) - 1) * 100
    ))


async def compare_strategies(code: str = "010003"):
    data = await fetch_fund_data(code, 100)

    # Initialize strategies
    t_strategy = TStrategy(
        data,
        initial_shares=10000,
        sell_holds=1000,
        threshold_rate=1.0
    )
    dynamic_strategy = DynamicTStrategy(
        data,
        initial_shares=10000,
        sell_holds=1000,
        threshold_rate=1.0
    )

    # Calculate results for both strategies
    t_cost, t_shares, t_last_price = t_strategy.calculate()
    dynamic_cost, dynamic_shares, dynamic_last_price = dynamic_strategy.calculate()

    # Calculate metrics for TStrategy
    t_avg_cost = t_cost / t_shares if t_shares else Decimal('0')
    t_profit = (t_last_price - t_avg_cost) * t_shares
    t_profit_rate = t_profit / t_cost

    # Calculate metrics for DynamicTStrategy
    dynamic_avg_cost = dynamic_cost / \
        dynamic_shares if dynamic_shares else Decimal('0')
    dynamic_profit = (dynamic_last_price - dynamic_avg_cost) * dynamic_shares
    dynamic_profit_rate = dynamic_profit / dynamic_cost

    # Calculate default profit
    initial_price = float(data[0]['DWJZ'])
    final_price = float(data[-1]['DWJZ'])
    default_profit_rate = (final_price / initial_price - 1) * 100

    # Print comparison results
    print("\nStrategy Comparison Results:")
    print("{:<20} {:<15} {:<15}".format(
        "Metric", "TStrategy", "DynamicTStrategy"))
    print("{:<20} {:<15.4f} {:<15.4f}".format(
        "Total Cost", t_cost, dynamic_cost))
    print("{:<20} {:<15} {:<15}".format(
        "Total Shares", t_shares, dynamic_shares))
    print("{:<20} {:<15.4f} {:<15.4f}".format(
        "Average Cost", t_avg_cost, dynamic_avg_cost))
    print("{:<20} {:<15.4f} {:<15.4f}".format(
        "Profit", t_profit, dynamic_profit))
    print("{:<20} {:<15.4f}% {:<15.4f}%".format(
        "Profit Rate", t_profit_rate * 100, dynamic_profit_rate * 100))
    print("{:<20} {:<15} {:<15}".format(
        "Default Profit", "", "{:.4f}%".format(default_profit_rate)))


if __name__ == "__main__":
    # asyncio.run(main(code="016530"))
    asyncio.run(compare_strategies(code="009707"))
