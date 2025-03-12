import asyncio
from app.data.fetch import fetch_fund_data
from typing import List, Dict, Tuple
from decimal import Decimal
import codefast as cf

from abc import ABC, abstractmethod


class AbstractStrategy(ABC):
    def __init__(self,
                 data: List[Dict],
                 initial_shares: int = 3000,
                 max_shares: int = 10000,
                 threshold_rate: float = 1.0) -> None:
        self.data = data
        self.initial_shares = initial_shares
        self.max_shares = max_shares
        self.threshold_rate = threshold_rate

    @abstractmethod
    def calculate(self, ) -> Tuple[Decimal, int]:
        pass


class TStrategy(AbstractStrategy):
    def __init__(self, data: List[Dict], initial_shares: int = 3000, max_shares: int = 10000, threshold_rate: float = 1) -> None:
        super().__init__(data, initial_shares, max_shares, threshold_rate)

    def calculate(self, ) -> Tuple[Decimal, int]:
        total_shares = self.initial_shares  # Initial shares
        total_cost = float(self.data[0]['DWJZ']) * total_shares  # Initial cost
        cf.info(
            f"Initial cost: {total_cost}, shares: {total_shares} , date: {self.data[0]['FSRQ']}")
        # Process each day after the first day
        for i in range(1, len(self.data)):
            current_price = float(self.data[i]['DWJZ'])
            change_rate = float(self.data[i]['JZZZL'])
            date = self.data[i]['FSRQ']

            if change_rate < -self.threshold_rate:
                shares_to_buy = 1000
                total_shares += shares_to_buy
                total_cost += current_price * shares_to_buy
                cf.info(
                    f"Buy {shares_to_buy} shares at {current_price} on {date}")

            elif change_rate > self.threshold_rate and total_shares > self.initial_shares:
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
    strategy = TStrategy(
        data,
        initial_shares=10000,
        threshold_rate=1.0
    )
    cost, shares = strategy.calculate()
    avg_cost = cost / shares if shares else Decimal('0')

    print("Strategy Results:")
    print("Total Cost: {:.4f}".format(cost))
    print("Total Shares: {}".format(shares))
    print("Average Cost per Share: {:.4f}".format(avg_cost))

if __name__ == "__main__":
    asyncio.run(main())
