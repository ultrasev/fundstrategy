from pydantic import BaseModel
import codefast as cf
import random


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
        self.initial_cash = cash
        self.min_quantity = min_quantity
        self.transaction_fee_buy = transaction_fee_buy
        self.transaction_fee_sell = transaction_fee_sell
        self.current_price = 0

    def trade(self, low, high, open_price, close, date):
        self.buy(low, high, open_price, close, date)
        self.sell(low, high, date)


class HighLowTrader(BaseTrader):
    def __init__(self, cash: int = 30000,
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


class MomentumTrader(BaseTrader):
    def __init__(self, cash: int = 30000,
                 min_quantity: int = 100,
                 transaction_fee_buy: int = 6,
                 transaction_fee_sell: int = 5,
                 short_window: int = 5,    # 5天短期均线
                 long_window: int = 10,    # 10天长期均线
                 momentum_days: int = 3,   # 3天动量
                 buy_threshold: float = 0.02,  # 2%的上涨动量
                 sell_threshold: float = -0.015,  # 1.5%的下跌动量
                 stop_loss: float = -0.03):  # 3%止损
        super().__init__(cash, min_quantity, transaction_fee_buy, transaction_fee_sell)
        self.price_history = []
        self.short_window = short_window
        self.long_window = long_window
        self.momentum_days = momentum_days
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        self.stop_loss = stop_loss
        self.last_buy_price = 0
        self.can_sell = False

    def calculate_ma(self, window: int) -> float:
        """Calculate moving average"""
        if len(self.price_history) < window:
            return 0.0
        return sum(self.price_history[-window:]) / window

    def calculate_momentum(self) -> float:
        """Calculate short-term momentum"""
        if len(self.price_history) < self.momentum_days:
            return 0.0
        start_price = self.price_history[-self.momentum_days]
        end_price = self.price_history[-1]
        return (end_price - start_price) / start_price

    def trade(self, low: float, high: float, open_price: float, close: float, date: str):
        self.price_history.append(close)

        # Update T+1 sell restriction
        if self.positions and not self.can_sell:
            self.can_sell = True

        if len(self.price_history) >= self.long_window:
            short_ma = self.calculate_ma(self.short_window)
            long_ma = self.calculate_ma(self.long_window)
            momentum = self.calculate_momentum()

            # Check stop loss first
            if self.positions and self.can_sell:
                current_return = (close - self.last_buy_price) / \
                    self.last_buy_price
                if current_return <= self.stop_loss:
                    self.sell(low, high, date)
                    self.can_sell = False
                    return

            # Buy conditions:
            # 1. Short MA > Long MA (上升趋势)
            # 2. Recent momentum > threshold (短期动能)
            # 3. No positions
            if (short_ma > long_ma and
                momentum >= self.buy_threshold and
                    not self.positions):
                self.buy(low, high, open_price, close, date)
                self.last_buy_price = close
                self.can_sell = False

            # Sell conditions:
            # 1. Short MA < Long MA (下降趋势) or
            # 2. Momentum < sell_threshold (动能减弱)
            elif self.positions and self.can_sell and (
                    short_ma < long_ma or
                    momentum <= self.sell_threshold):
                self.sell(low, high, date)
                self.can_sell = False

    def buy(self, low: float, high: float, open_price: float, close: float, date: str) -> float | None:
        """
        Buy at close price if conditions are met
        Returns the buy price if successful, None otherwise
        """
        # if self.cash < (close * self.min_quantity + self.transaction_fee_buy):
        #     return None

        self.positions.append(Position(
            price=close,
            quantity=self.min_quantity,
            purchase_date=date
        ))

        self.cash -= close * self.min_quantity
        self.cash -= self.transaction_fee_buy
        self.current_price = close

        cf.info("Buy at {:.2f} {}, cash: {:.2f}, total: {:.2f}".format(
            close, date, self.cash, self.total))

        return close

    def sell(self, low: float, high: float, date: str) -> float | None:
        """
        Sell at close price if conditions are met
        Returns the sell price if successful, None otherwise
        """
        if not self.positions:
            return None

        remaining_positions = []
        any_deal = False

        for position in self.positions:
            if position.purchase_date == date:  # T+1 rule check
                remaining_positions.append(position)
                continue

            any_deal = True
            self.current_price = high
            _cash = self.cash + high * position.quantity
            cf.info("Sell at {:.2f} {}, cash: {:.2f}, total: {:.2f}".format(
                high, date, _cash, self.total))
            self.cash += high * position.quantity

        if any_deal:
            self.cash -= self.transaction_fee_sell

        self.positions = remaining_positions
        return high if any_deal else None

    @property
    def total(self) -> float:
        """Calculate total assets including cash and positions"""
        if self.cash < 0:
            raise ValueError("Cash is negative")
        return self.cash + sum(self.current_price * p.quantity for p in self.positions)
