import asyncio
from app.data.fetch import fetch_fund_data
from typing import List, Dict, Tuple
from decimal import Decimal
import codefast as cf


def calculate_strategy(data: List[Dict],
                       initial_shares: int = 3000,
                       threshold_rate: float = 1.0) -> Tuple[Decimal, int]:
    """
    Calculate the final cost and shares based on the investment strategy.

    Args:
        data: List of daily fund data
        threshold_rate: Threshold percentage for buying/selling decisions

    Returns:
        Tuple of (total_cost, total_shares)
    """
    if not data:
        return 0, 0

    # Initialize portfolio
    total_shares = initial_shares  # Initial shares
    total_cost = float(data[0]['DWJZ']) * total_shares  # Initial cost
    cf.info(
        f"Initial cost: {total_cost}, shares: {total_shares} , date: {data[0]['FSRQ']}")
    # Process each day after the first day
    for i in range(1, len(data)):
        current_price = float(data[i]['DWJZ'])
        change_rate = float(data[i]['JZZZL'])
        date = data[i]['FSRQ']

        if change_rate < -threshold_rate:
            shares_to_buy = 1000
            total_shares += shares_to_buy
            total_cost += current_price * shares_to_buy
            cf.info(f"Buy {shares_to_buy} shares at {current_price} on {date}")

        elif change_rate > threshold_rate and total_shares > initial_shares:
            shares_to_sell = 1000
            total_shares -= shares_to_sell
            total_cost -= current_price * shares_to_sell
            fee = round(current_price * shares_to_sell * 0.005, 2)
            total_cost += fee
            cf.info(
                f"Sell {shares_to_sell} shares at {current_price} on {date}, fee: {fee}")

    return total_cost, total_shares


async def main():
    data = await fetch_fund_data("002810", 100)
    total_cost, total_shares = calculate_strategy(
        data,  initial_shares=2000, threshold_rate=1.0)
    avg_cost = total_cost / total_shares if total_shares else Decimal('0')

    print("Strategy Results:")
    print("Total Cost: {:.4f}".format(total_cost))
    print("Total Shares: {}".format(total_shares))
    print("Average Cost per Share: {:.4f}".format(avg_cost))

if __name__ == "__main__":
    asyncio.run(main())
