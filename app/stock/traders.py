from .dataloader import KlimeItem
from pydantic import BaseModel
import codefast as cf
import random
import math


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
    '''Trade 时不是在收盘做，而是盘中做，假设我能拿到实时价格。
    首先计算一下移动平均波动率，然后根据开盘价来预测今天涨幅，然后挂单交易（未必能成交）。
    比如今天开盘比昨天收盘高，我认为今天可能上涨，开盘价格 6.1，假设波动率为 3%，也就是说今天价格可能（只是可能）在 6.1～6.39 之间，那在这个区间可卖出的最高价格为 6.2（假设 gird size=0.2)，那么找可以出售的筹码，如果之前买入的有低于这个价格的就可以出售。当然，当天的价格未必真实在 6.1 ～ 6.39 之间，如果预设的价格 6.2 没有出现，就不成交。
    反之，如果开盘价比较低，买入策略也是类似的。

    策略可以直接用当天的最高价最低价来判断是否成交，毕竟我们在用历史数据回测。'''

    def __init__(self, cash: int = 30000,
                 min_quantity: int = 100,
                 transaction_fee_buy: int = 6,
                 transaction_fee_sell: int = 5,
                 grid_size: float = 0.2,
                 volatility_window: int = 12,
                 volatility_multiplier: float = 1.5,
                 stop_loss_rate: float = -0.03):  # 5%止损
        super().__init__(cash, min_quantity, transaction_fee_buy, transaction_fee_sell)
        self.grid_size = grid_size
        self.price_history = []
        self.volatility_window = volatility_window
        self.volatility_multiplier = volatility_multiplier
        self.last_close = None
        self.stop_loss_rate = stop_loss_rate

    def get_grid_price(self, price: float) -> float:
        """Calculate the grid price level"""
        return round(price / self.grid_size) * self.grid_size

    def calculate_price_ranges(self) -> tuple[float, float]:
        """
        Calculate average daily price ranges based on historical data.
        Returns:
            tuple[float, float]: (avg_down_range, avg_up_range)
            - avg_down_range: average (open - low) / open
            - avg_up_range: average (high - open) / open
        """
        if len(self.price_history) < self.volatility_window:
            return 0.01, 0.01  # Default 1% if not enough history

        up_ranges = []
        down_ranges = []

        # Calculate recent price ranges relative to open
        for i in range(-self.volatility_window, 0):
            open_price = self.price_history[i]['open']
            high_price = self.price_history[i]['high']
            low_price = self.price_history[i]['low']

            up_range = (high_price - open_price) / open_price
            down_range = (open_price - low_price) / open_price

            up_ranges.append(up_range)
            down_ranges.append(down_range)

        # Use exponential weights for more recent data
        decay = 0.94
        weights = [decay ** i for i in range(len(up_ranges))]
        weights = [w / sum(weights) for w in weights]

        avg_up_range = sum(r * w for r, w in zip(up_ranges, weights))
        avg_down_range = sum(r * w for r, w in zip(down_ranges, weights))

        return avg_down_range, avg_up_range

    def predict_price_range(self, open_price: float) -> tuple[float, float]:
        """
        Predict likely price range based on historical price movements.

        Args:
            open_price: Today's opening price

        Returns:
            tuple[float, float]: (predicted_low, predicted_high)
        """
        down_range, up_range = self.calculate_price_ranges()

        # Add a small buffer (10%) to the ranges
        buffer = 1.1

        predicted_low = open_price * (1 - down_range * buffer)
        predicted_high = open_price * (1 + up_range * buffer)

        return predicted_low, predicted_high

    def get_sell_orders(self, predicted_high: float) -> tuple[float, list[Position]]:
        """
        Generate one optimal sell order based on predicted high price
        Returns: (target_sell_price, positions_to_sell)
        """
        # Get the highest possible grid price below predicted high
        target_sell_price = self.get_grid_price(predicted_high)
        positions_to_sell = []

        # Find all positions that can be sold at this price
        for position in self.positions:
            if position.price < target_sell_price:
                positions_to_sell.append(position)

        return target_sell_price, positions_to_sell

    def get_buy_order(self, predicted_low: float) -> float | None:
        """
        Generate one optimal buy order based on predicted low price
        Returns the target buy price or None if we shouldn't buy
        """
        # If no positions, buy at predicted low
        if not self.positions:
            return self.get_grid_price(predicted_low)

        # Get the lowest position price we currently hold
        lowest_position = min(p.price for p in self.positions)

        # Only buy if predicted low is at least one grid lower than our lowest position
        grid_diff = (lowest_position - predicted_low) / self.grid_size
        if grid_diff >= 1.0:
            return self.get_grid_price(predicted_low)

        return None

    def check_stop_loss(self, item: KlimeItem) -> list[Position]:
        """Check if any positions need to be stopped out"""
        positions_to_stop = []
        for position in self.positions:
            if position.purchase_date == item.date:  # Skip T+1
                continue
            # Calculate current loss rate
            loss_rate = (item.close - position.price) / position.price
            if loss_rate <= self.stop_loss_rate:
                positions_to_stop.append(position)
        return positions_to_stop

    def execute_stop_loss(self, item: KlimeItem, positions_to_stop: list[Position]) -> None:
        """Execute stop loss orders"""
        if not positions_to_stop:
            return

        remaining_positions = []
        for position in self.positions:
            if position in positions_to_stop:
                sell_price = position.price * (1 + self.stop_loss_rate)
                x = self.cash + sell_price * position.quantity
                cf.info("Stop Loss at {:.2f} {}, cash: {:.2f}, total: {:.2f}, loss: {:.2%}".format(
                    sell_price, item.date, x, self.total,
                    self.stop_loss_rate))
                self.cash += sell_price * position.quantity
            else:
                remaining_positions.append(position)

        if positions_to_stop:
            self.cash -= self.transaction_fee_sell

        self.positions = remaining_positions

    def execute_orders(self, item: KlimeItem,
                       buy_order: float | None,
                       sell_order: tuple[float, list[Position]]) -> None:
        """Execute orders if price hits the target levels"""
        # Check stop loss first
        positions_to_stop = self.check_stop_loss(item)
        if positions_to_stop:
            self.execute_stop_loss(item, positions_to_stop)
            return  # Skip normal trading if stop loss triggered

        # Process sell order
        target_sell_price, positions_to_sell = sell_order
        remaining_positions = []
        any_sell = False

        # Only execute if price reached our target
        if item.high >= target_sell_price:
            _total = self.total
            for position in self.positions:
                if position.purchase_date == item.date:  # T+1 rule
                    remaining_positions.append(position)
                    continue

                if position in positions_to_sell:
                    any_sell = True
                    self.current_price = target_sell_price
                    self.cash += target_sell_price * position.quantity
                    cf.info("Sell at {:.2f} {}, cash: {:.2f}, total: {:.2f}".format(
                        target_sell_price, item.date, self.cash, _total))
                else:
                    remaining_positions.append(position)

            if any_sell:
                self.cash -= self.transaction_fee_sell

            self.positions = remaining_positions

        # Process buy order
        if buy_order and item.low <= buy_order <= item.high:
            if self.cash >= (buy_order * self.min_quantity + self.transaction_fee_buy):
                self.positions.append(Position(
                    price=buy_order,
                    quantity=self.min_quantity,
                    purchase_date=item.date
                ))

                self.cash -= buy_order * self.min_quantity
                self.cash -= self.transaction_fee_buy
                self.current_price = buy_order

                cf.info("Buy at {:.2f} {}, cash: {:.2f}, total: {:.2f}".format(
                    buy_order, item.date, self.cash, self.total))

    def trade(self, item: KlimeItem) -> KlimeItem:
        self.current_price = item.close  # Update current price first
        self.price_history.append({
            'open': item.open,
            'high': item.high,
            'low': item.low,
            'close': item.close,
            'date': item.date
        })

        if len(self.price_history) < 2:
            self.last_close = item.close
            return

        predicted_low, predicted_high = self.predict_price_range(item.open)

        if item.open > self.last_close:
            # Uptrend: focus on selling at higher price
            sell_order = self.get_sell_orders(predicted_high)
            # More conservative buying in uptrend
            buy_order = self.get_buy_order(item.open * 0.99)
        else:
            # Downtrend: focus on buying at lower price
            sell_order = self.get_sell_orders(item.open * 1.01)
            # More aggressive buying in downtrend
            buy_order = self.get_buy_order(predicted_low)

        # print({
        #     'date': item.date,
        #     'open': item.open,
        #     'close': item.close,
        #     'high': item.high,
        #     'low': item.low,
        #     'predicted_low': predicted_low,
        #     'predicted_high': predicted_high,
        #     'buy_order': buy_order,
        #     'sell_order': sell_order,
        #     'positions': self.positions,
        # })
        # # Execute orders
        self.execute_orders(item, buy_order, sell_order)
        self.last_close = item.close
        return item

    @property
    def total(self) -> float:
        """Calculate total assets including cash and positions"""
        if self.cash < 0:
            raise ValueError("Cash is negative")
        return self.cash + sum(self.current_price * p.quantity for p in self.positions)
