import json
from pydantic import BaseModel
import random
import codefast as cf
from app.stock.dataloader import KlineReader


class Position(BaseModel):
    price: float
    quantity: int
    purchase_date: str


class BaseTrader:
    def __init__(self):
        self.positions: list[Position] = []
        self.cash = 100000
        self.transaction_fee_buy = 6
        self.transaction_fee_sell = 5
        self.current_price = 0

    def trade(self, low, high, open_price, close, date):
        self.buy(low, high, open_price, close, date)
        self.sell(low, high, date)


class HighLowTrader(BaseTrader):
    def __init__(self):
        super().__init__()
        self.min_quantity = 200
        self.cash = 20000

    @property
    def total(self):
        if self.cash < 0:
            raise ValueError("Cash is negative")
        return self.cash + sum(self.current_price * p.quantity for p in self.positions)

    def buy(self, low, high, open_price, close, date):
        potential_buy_price = round((low + 0.1) * 10) / 10
        if potential_buy_price <= high:
            if not self.positions or potential_buy_price < min(p.price for p in self.positions):
                # Store purchase date for T+1 rule
                self.positions.append(Position(price=potential_buy_price,
                                               quantity=self.min_quantity,
                                               purchase_date=date))
                self.cash -= potential_buy_price * self.min_quantity
                self.cash -= self.transaction_fee_buy
                self.current_price = potential_buy_price
                cf.info(
                    f"Buy at {potential_buy_price} {date}, cash: {self.cash}, total: {self.total}")
                return potential_buy_price

        return None

    def sell(self, low, high, current_date):
        if not self.positions:
            return 0

        remaining_positions = []
        sell_price = int(high * 100 / 10) / 10
        any_deal = False

        for position in self.positions:
            if position.purchase_date == current_date:
                remaining_positions.append(position)
                continue

            if position.price < sell_price:
                any_deal = True
                self.cash += sell_price * position.quantity
                self.current_price = sell_price
                x = self.total - sell_price * position.quantity
                cf.info(
                    f"Sell at {sell_price} {current_date}, cash: {self.cash}, total: {x}")
            else:
                remaining_positions.append(position)

        if any_deal:
            self.cash -= self.transaction_fee_sell

        self.positions = remaining_positions


def simulate_trading(code):
    trader = HighLowTrader()
    reader = KlineReader(code)
    lines = reader.read()
    for line in lines['data']['klines']:
        date, open_price, close, high, low, *_ = line.split(",")
        open_price = float(open_price)
        close = float(close)
        high = float(high)
        low = float(low)

        trader.trade(low, high, open_price, close, date)

    return trader


if __name__ == "__main__":
    trader = simulate_trading("000001")
    print(trader.positions)
    print(f"Final cash: {trader.cash}, Final total: {trader.total}")
