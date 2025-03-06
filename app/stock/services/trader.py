from app.stock.traders import EnhancedGridTrader
from app.stock.dataloader import KlineReader


class AutoTrader(EnhancedGridTrader):
    def __init__(self,
                 cash: int = 30000,
                 min_quantity: int = 100,
                 transaction_fee_buy: int = 6,
                 transaction_fee_sell: int = 5,
                 grid_size: float = 0.1,
                 volatility_window: int = 12,
                 volatility_multiplier: float = 1.5,
                 stop_loss_rate: float = -0.05):
        super().__init__(cash, min_quantity, transaction_fee_buy, transaction_fee_sell,
                         grid_size, volatility_window, volatility_multiplier, stop_loss_rate)
        self.last_close = None

    def load_positions(self):
        pass

    def signal(self, open_price: float) -> bool:
        predicted_low, predicted_high = self.predict_price_range(open_price)

        if open_price > self.last_close:
            sell_order = self.get_sell_orders(predicted_high)
            buy_order = self.get_buy_order(open_price * 0.99)
        else:
            sell_order = self.get_sell_orders(open_price * 1.01)
            buy_order = self.get_buy_order(predicted_low)

        print({
            'sell_order': sell_order,
            'buy_order': buy_order
        })


def test():
    reader = KlineReader('000001')
    kline = reader.read()
    data = kline.klines
    trader = AutoTrader()
    for item in data:
        trader.trade(item)

    trader.signal(11.8)


if __name__ == "__main__":
    test()
