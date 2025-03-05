from app.stock.dataloader import KlimeItem
from app.stock.dataloader import KlineReader, Kline
from app.stock.traders import (HighLowTrader,
                               MomentumTrader,
                               Position,
                               EnhancedGridTrader)

from pydantic import BaseModel
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
        text = (
            f'Stock: {self.name} ({self.code})\n'
            f'Price Movement:\n'
            f'    Start: ¥{self.start_price:.2f}\n'
            f'    End:   ¥{self.end_price:.2f}\n'
            f'Performance:\n'
            f'    Initial Cash: ¥{self.initial_cash:.2f}\n'
            f'    Final Total:  ¥{self.final_total:.2f}\n'
            f'    Return Rate:  {self.return_rate:+.2f}%\n'
            f'Positions:\n'
            f'    {self.positions}'
        )
        return indent(text, '    ')


def simulate(code):
    trader = MomentumTrader(cash=20000,
                            min_quantity=1000,
                            transaction_fee_buy=6,
                            transaction_fee_sell=5)
    # trader = HighLowTrader(cash=20000,
    #                        min_quantity=100,
    #                        transaction_fee_buy=6,
    #                        transaction_fee_sell=5)
    trader = EnhancedGridTrader(cash=20000,
                                min_quantity=1800,
                                transaction_fee_buy=6,
                                transaction_fee_sell=5)
    reader = KlineReader(code)
    kline = reader.read()
    data = kline.klines

    for item in data:
        trader.trade(item)

    for p in trader.positions:
        print(p)
    info = {
        'name': kline.name,
        'code': kline.code,
        'start_price': kline.klines[0].open,
        'end_price': kline.klines[-1].close,
        'return rate': (trader.total / trader.initial_cash - 1) * 100,
        'positions': trader.positions,
        'initial_cash': trader.initial_cash,
        'final_total': trader.total,
    }
    reporter = Reporter(**info)
    return reporter


stocks = {
    '000001': {
        'min_quantity': 1000,
        'name': '平安银行',
    },
    '600916': {
        'min_quantity': 1800,
        'name': '中国黄金',

    },
    '002253': {
        'min_quantity': 1200,
        'name': '川大智胜',
    },
}

if __name__ == "__main__":
    code = '002253'
    trader = simulate(code)
    print(trader)
