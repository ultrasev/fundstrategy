from app.stock.dataloader import KlineReader, Kline
from app.stock.traders import HighLowTrader, MomentumTrader, Position

from pydantic import BaseModel
from pprint import pprint
from textwrap import indent


class Reporter(BaseModel):
    name: str
    code: str
    start_price: float
    end_price: float
    positions: list[Position]
    initial_cash: float
    final_total: float

    @property
    def return_rate(self) -> float:
        """Calculate return rate as percentage"""
        return (self.final_total / self.initial_cash - 1) * 100

    def __str__(self):
        return indent(f'''
    name: {self.name}
    code: {self.code}
    start_price: {self.start_price}
    end_price: {self.end_price}
    return_rate: {self.return_rate:.2f}%
    positions: {self.positions}
    initial_cash: {self.initial_cash}
    final_total: {self.final_total}
    ''', '    ')


def simulate(code):
    trader = MomentumTrader(cash=20000,
                            min_quantity=100,
                            transaction_fee_buy=6,
                            transaction_fee_sell=5)
    reader = KlineReader(code)
    kline = reader.read()
    data = kline.klines

    for line in data:
        date, open_price, close, high, low, *_ = line
        open_price = float(open_price)
        close = float(close)
        high = float(high)
        low = float(low)

        trader.trade(low, high, open_price, close, date)

    for p in trader.positions:
        print(p)
    info = {
        'name': kline.name,
        'code': kline.code,
        'start_price': data[0][1],
        'end_price': data[-1][2],
        'return rate': (trader.total / trader.initial_cash - 1) * 100,
        'positions': trader.positions,
        'initial_cash': trader.initial_cash,
        'final_total': trader.total,
    }
    reporter = Reporter(**info)
    return reporter


if __name__ == "__main__":
    trader = simulate("603887")
    print(trader)
