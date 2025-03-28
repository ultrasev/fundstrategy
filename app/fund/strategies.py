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

    def _can_sell(self, current_date: str,
                  holds: List[Tuple[str, int]],
                  current_price: float) -> bool:
        """
        Check if there are any holdings older than 7 days that can be sold
        and if the current price is higher than the purchase price.
        """
        current_dt = datetime.strptime(current_date, '%Y-%m-%d')
        seven_days_ago = current_dt - timedelta(days=7)
        holds.sort(key=lambda x: x[1])

        for date, price in holds:
            hold_dt = datetime.strptime(date, '%Y-%m-%d')
            if hold_dt <= seven_days_ago and current_price > price:
                return True
        return False

    def calculate(self, ) -> Tuple[Decimal, int]:
        date = self.data[0]['FSRQ']
        minimal_holds = self.initial_shares // self.sell_holds
        holds = [
            # Store the price along with the date
            (date, float(self.data[0]['DWJZ']))
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
                # Store the price along with the date
                holds.append((date, current_price))
                msg = 'Buy {} shares at {} on {}, total_shares: {}'.format(
                    shares_to_buy,
                    current_price,
                    date,
                    total_shares
                )
                cf.info(msg)

            elif change_rate > self.threshold_rate and total_shares > self.initial_shares:
                # Check if we have any holdings older than 7 days and the price is higher
                if not self._can_sell(date, holds, current_price):
                    cf.info(
                        'Skip selling on {} - no holdings older than 7 days or price not higher'.format(date))
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


class DynamicTStrategy(AbstractStrategy):
    def __init__(self, data: List[Dict], initial_shares: int = 3000,
                 sell_holds: int = 1000,
                 max_shares: int = 10000,
                 threshold_rate: float = 1) -> None:
        super().__init__(data, initial_shares, max_shares, sell_holds, threshold_rate)

    def calculate(self, ) -> Tuple[Decimal, int]:
        date = self.data[0]['FSRQ']
        minimal_holds = self.initial_shares // self.sell_holds
        holds = [
            (date, float(self.data[0]['DWJZ']))
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

        for item in self.data[1:]:
            current_price, change_rate, date = float(
                item['DWJZ']), float(item['JZZZL']), item['FSRQ']

            multiple = int(
                round(abs(change_rate) / self.threshold_rate, 0))
            if multiple < 1:
                continue
            if change_rate < 0:
                # Calculate the multiple based on how much the rate exceeds the threshold
                _shares = 0
                for _ in range(multiple):
                    shares_to_buy = 1000
                    total_shares += shares_to_buy
                    total_cost += current_price * shares_to_buy
                    holds.append((date, current_price))
                    _shares += shares_to_buy
                if _shares:
                    msg = 'Buy {} shares at {} on {}, total_shares: {}'.format(
                        _shares,
                        current_price,
                        date,
                        total_shares
                    )
                    cf.info(msg)

            elif change_rate > 0 and total_shares > self.initial_shares:
                multiple = int(round(change_rate / self.threshold_rate))
                eligible_holds = [
                    (idx, hold_date, hold_price)
                    for idx, (hold_date, hold_price) in enumerate(holds)
                    if datetime.strptime(hold_date, '%Y-%m-%d') <= (datetime.strptime(date, '%Y-%m-%d') - timedelta(days=7))
                    and current_price > hold_price
                ]
                if not eligible_holds:
                    cf.info('No eligible holds to sell on {}'.format(date))
                    continue

                sold_indexes = []
                for idx, _, _ in eligible_holds:
                    if len(sold_indexes) >= min(multiple, len(holds)-minimal_holds):
                        break
                    sold_indexes.append(idx)
                    total_shares -= 1000
                    total_cost -= current_price * 1000
                    fee = round(current_price * 1000 * 0.005, 2)
                    total_cost += fee
                if sold_indexes:
                    msg = 'Sell {} shares at {} on {}, total_shares: {}, fee: {}'.format(
                        1000 * len(sold_indexes),
                        current_price,
                        date,
                        total_shares,
                        round(fee * len(sold_indexes), 2)
                    )
                    cf.info(msg)

                holds = [hold for idx, hold in enumerate(
                    holds) if idx not in sold_indexes]

        return total_cost, total_shares, float(self.data[-1]['DWJZ'])
