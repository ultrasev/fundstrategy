from app.stock.dataloader import KlineReader
from app.stock.traders import HighLowTrader


def simulate(code):
    trader = HighLowTrader(cash=20000,
                           min_quantity=100,
                           transaction_fee_buy=6,
                           transaction_fee_sell=5)
    reader = KlineReader(code)
    lines = reader.read()
    for line in lines:
        date, open_price, close, high, low, *_ = line.split(",")
        open_price = float(open_price)
        close = float(close)
        high = float(high)
        low = float(low)

        trader.trade(low, high, open_price, close, date)

    return trader


if __name__ == "__main__":
    trader = simulate("601900")
    for p in trader.positions:
        print(p)
    print(f"Final cash: {trader.cash}, Final total: {trader.total}")
