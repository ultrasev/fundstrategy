from pydantic import BaseModel
import codefast as cf


class Position(BaseModel):
    price: float
    quantity: int
    purchase_date: str


class BaseTrader:
    def __init__(self, cash: int = 100000,
                 min_quantity: int = 200,
                 transaction_fee_buy: int = 6,
                 transaction_fee_sell: int = 5):
        self.positions: list[Position] = []
        self.cash = cash
        self.min_quantity = min_quantity
        self.transaction_fee_buy = transaction_fee_buy
        self.transaction_fee_sell = transaction_fee_sell
        self.current_price = 0

    def trade(self, low, high, open_price, close, date):
        self.buy(low, high, open_price, close, date)
        self.sell(low, high, date)


class HighLowTrader(BaseTrader):
    def __init__(self, cash: int = 100000,
                 min_quantity: int = 200,
                 transaction_fee_buy: int = 6,
                 transaction_fee_sell: int = 5):
        super().__init__(cash, min_quantity, transaction_fee_buy, transaction_fee_sell)

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
