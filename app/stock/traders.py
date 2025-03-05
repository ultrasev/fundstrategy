from .dataloader import KlimeItem
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

    def trade(self, item: KlimeItem):
        self.buy(item)
        self.sell(item)


class HighLowTrader(BaseTrader):
    def __init__(self, cash: int = 30000,
                 min_quantity: int = 230,
                 transaction_fee_buy: int = 6,
                 transaction_fee_sell: int = 5):
        super().__init__(cash, min_quantity, transaction_fee_buy, transaction_fee_sell)

    @property
    def total(self):
        if self.cash < 0:
            raise ValueError("Cash is negative")
        return self.cash + sum(self.current_price * p.quantity for p in self.positions)

    def buy(self, item: KlimeItem):
        potential_buy_price = round((item.low + 0.1) * 10) / 10
        if potential_buy_price <= item.high:
            if not self.positions or potential_buy_price < min(p.price for p in self.positions):
                # Store purchase date for T+1 rule
                self.positions.append(Position(price=potential_buy_price,
                                               quantity=self.min_quantity,
                                               purchase_date=item.date))
                self.cash -= potential_buy_price * self.min_quantity
                self.cash -= self.transaction_fee_buy
                self.current_price = potential_buy_price
                cf.info(
                    f"Buy at {potential_buy_price} {item.date}, cash: {self.cash}, total: {self.total}")
                return potential_buy_price

        return None

    def sell(self, item: KlimeItem):
        if not self.positions:
            return 0

        remaining_positions = []
        sell_price = int(item.high * 100 / 10) / 10
        any_deal = False

        for position in self.positions:
            if position.purchase_date == item.date:
                remaining_positions.append(position)
                continue

            if position.price < sell_price:
                any_deal = True
                self.cash += sell_price * position.quantity
                self.current_price = sell_price
                x = self.total - sell_price * position.quantity
                cf.info(
                    f"Sell at {sell_price} {item.date}, cash: {self.cash}, total: {x}")
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

    def trade(self, item: KlimeItem):
        self.price_history.append(item.close)

        # Update T+1 sell restriction
        if self.positions and not self.can_sell:
            self.can_sell = True

        if len(self.price_history) >= self.long_window:
            short_ma = self.calculate_ma(self.short_window)
            long_ma = self.calculate_ma(self.long_window)
            momentum = self.calculate_momentum()

            # Check stop loss first
            if self.positions and self.can_sell:
                current_return = (item.close - self.last_buy_price) / \
                    self.last_buy_price
                if current_return <= self.stop_loss:
                    self.sell(item)
                    self.can_sell = False
                    return

            # Buy conditions:
            # 1. Short MA > Long MA (上升趋势)
            # 2. Recent momentum > threshold (短期动能)
            # 3. No positions
            if (short_ma > long_ma and
                momentum >= self.buy_threshold and
                    not self.positions):
                self.buy(item)
                self.last_buy_price = item.close
                self.can_sell = False

            # Sell conditions:
            # 1. Short MA < Long MA (下降趋势) or
            # 2. Momentum < sell_threshold (动能减弱)
            elif self.positions and self.can_sell and (
                    short_ma < long_ma or
                    momentum <= self.sell_threshold):
                self.sell(item)
                self.can_sell = False

    def buy(self, item: KlimeItem) -> float | None:
        """
        Buy at close price if conditions are met
        Returns the buy price if successful, None otherwise
        """
        # if self.cash < (close * self.min_quantity + self.transaction_fee_buy):
        #     return None

        self.positions.append(Position(
            price=item.close,
            quantity=self.min_quantity,
            purchase_date=item.date
        ))

        self.cash -= item.close * self.min_quantity
        self.cash -= self.transaction_fee_buy
        self.current_price = item.close

        cf.info("Buy at {:.2f} {}, cash: {:.2f}, total: {:.2f}".format(
            item.close, item.date, self.cash, self.total))

        return item.close

    def sell(self, item: KlimeItem) -> float | None:
        """
        Sell at close price if conditions are met
        Returns the sell price if successful, None otherwise
        """
        if not self.positions:
            return None

        remaining_positions = []
        any_deal = False

        for position in self.positions:
            if position.purchase_date == item.date:  # T+1 rule check
                remaining_positions.append(position)
                continue

            any_deal = True
            self.current_price = item.close
            _cash = self.cash + item.close * position.quantity
            cf.info("Sell at {:.2f} {}, cash: {:.2f}, total: {:.2f}".format(
                item.close, item.date, _cash, self.total))
            self.cash += item.close * position.quantity

        if any_deal:
            self.cash -= self.transaction_fee_sell

        self.positions = remaining_positions
        return item.close if any_deal else None

    @property
    def total(self) -> float:
        """Calculate total assets including cash and positions"""
        if self.cash < 0:
            raise ValueError("Cash is negative")
        return self.cash + sum(self.current_price * p.quantity for p in self.positions)


class GridTrader(BaseTrader):
    def __init__(self, cash: int = 30000,
                 min_quantity: int = 100,
                 transaction_fee_buy: int = 6,
                 transaction_fee_sell: int = 5,
                 grid_size: float = 0.2):  # Grid interval size
        super().__init__(cash, min_quantity, transaction_fee_buy, transaction_fee_sell)
        self.grid_size = grid_size
        self.base_price = None  # Will be set on first trade

    def get_grid_price(self, price: float) -> float:
        """Calculate the grid price level"""
        return round(price / self.grid_size) * self.grid_size

    def should_buy(self, current_price: float) -> bool:
        """Check if we should buy at current grid level"""
        if not self.positions:
            return True

        # Get the highest price we bought at
        highest_buy = max(p.price for p in self.positions)
        grid_diff = (highest_buy - current_price) / self.grid_size

        # Buy if price is at least one grid lower than our highest buy
        return grid_diff >= 1.0

    def should_sell(self, current_price: float, position_price: float) -> bool:
        """Check if we should sell positions bought at position_price"""
        grid_diff = (current_price - position_price) / self.grid_size
        return grid_diff >= 1.0

    def trade(self, item: KlimeItem):
        # Initialize base price if not set
        if self.base_price is None:
            self.base_price = self.get_grid_price(item.close)
            return

        current_grid_price = self.get_grid_price(item.close)

        # Try to buy if price hits lower grid levels
        if self.should_buy(current_grid_price):
            self.buy(item)

        # Try to sell positions that hit profit target
        self.sell(item)

    def buy(self, item: KlimeItem) -> float | None:
        """Buy at current price if conditions are met"""
        if self.cash < (item.close * self.min_quantity + self.transaction_fee_buy):
            return None

        self.positions.append(Position(
            price=item.close,
            quantity=self.min_quantity,
            purchase_date=item.date
        ))

        self.cash -= item.close * self.min_quantity
        self.cash -= self.transaction_fee_buy
        self.current_price = item.close

        cf.info("Buy at {:.2f} {}, cash: {:.2f}, total: {:.2f}".format(
            item.close, item.date, self.cash, self.total))

        return item.close

    def sell(self, item: KlimeItem) -> float | None:
        """Sell positions that meet profit target"""
        if not self.positions:
            return None

        remaining_positions = []
        any_deal = False

        for position in self.positions:
            if position.purchase_date == item.date:  # T+1 rule
                remaining_positions.append(position)
                continue

            # Check if this position should be sold
            if self.should_sell(item.close, position.price):
                any_deal = True
                self.current_price = item.close
                _cash = self.cash + item.close * position.quantity
                cf.info("Sell at {:.2f} {}, cash: {:.2f}, total: {:.2f}".format(
                    item.close, item.date, _cash, self.total))
                self.cash += item.close * position.quantity
            else:
                remaining_positions.append(position)

        if any_deal:
            self.cash -= self.transaction_fee_sell

        self.positions = remaining_positions
        return item.close if any_deal else None

    @property
    def total(self) -> float:
        """Calculate total assets including cash and positions"""
        if self.cash < 0:
            raise ValueError("Cash is negative")
        return self.cash + sum(self.current_price * p.quantity for p in self.positions)


class EnhancedGridTrader(BaseTrader):
    def __init__(self, cash: int = 30000,
                 min_quantity: int = 100,
                 transaction_fee_buy: int = 6,
                 transaction_fee_sell: int = 5,
                 grid_size: float = 0.2,
                 volatility_window: int = 10,  # 计算波动率的窗口
                 volatility_multiplier: float = 1.5):  # 波动率调整系数
        super().__init__(cash, min_quantity, transaction_fee_buy, transaction_fee_sell)
        self.grid_size = grid_size
        self.price_history = []
        self.volatility_window = volatility_window
        self.volatility_multiplier = volatility_multiplier
        self.last_close = None

    def get_grid_price(self, price: float) -> float:
        """Calculate the grid price level"""
        return round(price / self.grid_size) * self.grid_size

    def calculate_volatility(self) -> float:
        """Calculate historical volatility"""
        if len(self.price_history) < self.volatility_window:
            return 0.03  # Default 3% if not enough history

        returns = [(self.price_history[i] - self.price_history[i-1]) / self.price_history[i-1]
                   for i in range(1, len(self.price_history))]
        recent_returns = returns[-self.volatility_window:]
        return (max(recent_returns) - min(recent_returns)) * self.volatility_multiplier

    def predict_price_range(self, open_price: float, volatility: float) -> tuple[float, float]:
        """Predict today's trading range based on open price and volatility"""
        return (
            open_price * (1 - volatility),
            open_price * (1 + volatility)
        )

    def get_sell_orders(self, predicted_high: float) -> list[tuple[Position, float]]:
        """Generate sell orders based on predicted high price"""
        sell_orders = []
        highest_grid = self.get_grid_price(predicted_high)

        for position in self.positions:
            # Find the next grid level above position price
            sell_price = self.get_grid_price(position.price + self.grid_size)
            if sell_price <= highest_grid:
                sell_orders.append((position, sell_price))

        return sell_orders

    def get_buy_orders(self, predicted_low: float) -> list[float]:
        """Generate buy orders based on predicted low price"""
        buy_orders = []
        lowest_grid = self.get_grid_price(predicted_low)

        if not self.positions:
            # If no positions, place first buy order
            buy_orders.append(predicted_low)
        else:
            # Find all grid levels below our highest position
            highest_position = max(p.price for p in self.positions)
            current_grid = self.get_grid_price(
                highest_position - self.grid_size)

            while current_grid >= lowest_grid:
                buy_orders.append(current_grid)
                current_grid = self.get_grid_price(
                    current_grid - self.grid_size)

        return buy_orders

    def execute_orders(self, item: KlimeItem,
                       buy_orders: list[float],
                       sell_orders: list[tuple[Position, float]]) -> None:
        """Execute orders if price hits the order levels"""
        # Process sell orders
        remaining_positions = []
        any_sell = False

        for position in self.positions:
            if position.purchase_date == item.date:  # T+1 rule
                remaining_positions.append(position)
                continue

            # Find matching sell order
            matching_sell = next((order for order in sell_orders
                                  if order[0] == position and order[1] <= item.high), None)

            if matching_sell:
                any_sell = True
                sell_price = matching_sell[1]
                self.current_price = sell_price
                self.cash += sell_price * position.quantity
                cf.info("Sell at {:.2f} {}, cash: {:.2f}, total: {:.2f}".format(
                    sell_price, item.date, self.cash, self.total))
            else:
                remaining_positions.append(position)

        if any_sell:
            self.cash -= self.transaction_fee_sell

        self.positions = remaining_positions

        # Process buy orders
        # Buy from highest price first
        for buy_price in sorted(buy_orders, reverse=True):
            if buy_price >= item.low and buy_price <= item.high:
                if self.cash >= (buy_price * self.min_quantity + self.transaction_fee_buy):
                    self.positions.append(Position(
                        price=buy_price,
                        quantity=self.min_quantity,
                        purchase_date=item.date
                    ))

                    self.cash -= buy_price * self.min_quantity
                    self.cash -= self.transaction_fee_buy
                    self.current_price = buy_price

                    cf.info("Buy at {:.2f} {}, cash: {:.2f}, total: {:.2f}".format(
                        buy_price, item.date, self.cash, self.total))

    def trade(self, item: KlimeItem):
        self.price_history.append(item.close)

        if len(self.price_history) < 2:
            self.last_close = item.close
            return

        volatility = self.calculate_volatility()
        predicted_low, predicted_high = self.predict_price_range(
            item.open, volatility)

        if item.open > self.last_close:
            sell_orders = self.get_sell_orders(predicted_high)
            buy_orders = self.get_buy_orders(
                item.open * 0.99)  # Limited buying below open
        else:
            # Downtrend: focus on buying
            sell_orders = self.get_sell_orders(
                item.open * 1.01)  # Limited selling above open
            buy_orders = self.get_buy_orders(predicted_low)

        # Execute orders
        self.execute_orders(item, buy_orders, sell_orders)
        self.last_close = item.close

    @property
    def total(self) -> float:
        """Calculate total assets including cash and positions"""
        if self.cash < 0:
            raise ValueError("Cash is negative")
        return self.cash + sum(self.current_price * p.quantity for p in self.positions)
