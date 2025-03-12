import asyncio
from app.data.fetch import fetch_fund_data
from typing import List, Dict, Tuple
from decimal import Decimal
import codefast as cf
from datetime import datetime, timedelta
from abc import ABC, abstractmethod


class AbstractStrategy(ABC):
    def __init__(self,
                 data: List[Dict],
                 initial_shares: int = 3000,
                 max_shares: int = 10000,
                 sell_holds: int = 1000,
                 threshold_rate: float = 1.0) -> None:
        self.data = data
        self.initial_shares = initial_shares
        self.max_shares = max_shares
        self.sell_holds = sell_holds
        self.threshold_rate = threshold_rate

    @abstractmethod
    def calculate(self, ) -> Tuple[Decimal, int]:
        pass


class TStrategy(AbstractStrategy):
    def __init__(self, data: List[Dict], initial_shares: int = 3000,
                 sell_holds: int = 1000,
                 max_shares: int = 10000,
                 threshold_rate: float = 1) -> None:
        super().__init__(data, initial_shares, max_shares, sell_holds, threshold_rate)

    def _can_sell(self, current_date: str, holds: List[Tuple[str, int]]) -> bool:
        """
        Check if there are any holdings older than 7 days that can be sold
        """
        current_dt = datetime.strptime(current_date, '%Y-%m-%d')
        seven_days_ago = current_dt - timedelta(days=7)

        for hold_date, _ in holds:
            hold_dt = datetime.strptime(hold_date, '%Y-%m-%d')
            if hold_dt <= seven_days_ago:
                return True
        return False

    def calculate(self, ) -> Tuple[Decimal, int]:
        date = self.data[0]['FSRQ']
        minimal_holds = self.initial_shares // self.sell_holds
        holds = [
            (date, self.sell_holds)
            for _ in range(minimal_holds)
        ]
        total_shares = self.initial_shares
        total_cost = float(self.data[0]['DWJZ']) * total_shares
        cf.info({
            'date': date,
            'total_cost': total_cost,
            'total_shares': total_shares,
            'minimal_holds': minimal_holds,
            'price': float(self.data[0]['DWJZ'])
        })

        for i, item in enumerate(self.data[1:]):
            current_price = float(item['DWJZ'])
            change_rate = float(item['JZZZL'])
            date = item['FSRQ']

            if change_rate < -self.threshold_rate:
                shares_to_buy = 1000
                total_shares += shares_to_buy
                total_cost += current_price * shares_to_buy
                holds.append((date, shares_to_buy))
                msg = 'Buy {} shares at {} on {}, total_shares: {}'.format(
                    shares_to_buy,
                    current_price,
                    date,
                    total_shares
                )
                cf.info(msg)

            elif change_rate > self.threshold_rate and total_shares > self.initial_shares:
                # Check if we have any holdings older than 7 days
                if not self._can_sell(date, holds):
                    cf.info(
                        'Skip selling on {} - no holdings older than 7 days'.format(date))
                    continue

                shares_to_sell = 1000
                holds.pop(0)
                total_shares -= shares_to_sell
                total_cost -= current_price * shares_to_sell
                fee = round(current_price * shares_to_sell * 0.005, 2)
                total_cost += fee
                msg = 'Sell {} shares at {} on {}, total_shares: {}, fee: {}'.format(
                    shares_to_sell,
                    current_price,
                    date,
                    total_shares,
                    fee
                )
                cf.info(msg)

        return total_cost, total_shares, float(self.data[-1]['DWJZ'])


async def main():
    data = await fetch_fund_data("002810", 100)
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
    print("Profit Rate: {:.4f}%".format(profit_rate * 100))


if __name__ == "__main__":
    asyncio.run(main())
