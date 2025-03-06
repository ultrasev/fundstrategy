from app.stock.traders import TraderFactory
from app.stock.dataloader import KlineReader, Kline
from app.stock.traders import Position

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


def get_max_quantity(code: str, cash: int = 20000):
    reader = KlineReader(code)
    kline = reader.read()
    data = kline.klines
    initial_price = data[0].open
    return int(round(cash / initial_price / 100)) * 100 - 100


def simulate(code, min_quantity, n_days=40, strategy='momentum'):
    trader = TraderFactory.create_trader(strategy,
                                         cash=20000,
                                         min_quantity=min_quantity,
                                         transaction_fee_buy=6,
                                         transaction_fee_sell=5)
    reader = KlineReader(code)
    kline = reader.read()
    data = kline.klines

    for item in data[-n_days:]:
        trader.trade(item)

    for p in trader.positions:
        print(p)
    info = {
        'name': kline.name,
        'code': kline.code,
        'start_price': data[-n_days].open if n_days < len(data) else data[0].open,
        'end_price': data[-1].close,
        'return rate': (trader.total / trader.initial_cash - 1) * 100,
        'positions': trader.positions,
        'initial_cash': trader.initial_cash,
        'final_total': trader.total,
    }
    reporter = Reporter(**info)
    return reporter


stocks = {
    '000001': {
        'min_quantity': 700,
        'name': '平安银行',
    },
    '600916': {
        'min_quantity': 1800,
        'name': '中国黄金',

    },
    '002253': {
        'min_quantity': 400,
        'name': '川大智胜',
    },
    '002273': {
        'min_quantity': 600,
        'name': '水晶光电',
    },
    '600505': {
        'min_quantity': 300,
        'name': '西昌电力',
    },
}


def print_summary(reports: list[Reporter]) -> None:
    """Print performance summary for all reports"""
    if not reports:
        print("No reports available")
        return

    # Sort reports by return rate in descending order
    sorted_reports = sorted(reports, key=lambda x: x.return_rate, reverse=True)

    # Calculate statistics
    return_rates = [r.return_rate for r in reports]
    avg_return = sum(return_rates) / len(return_rates)
    max_return = max(return_rates)
    min_return = min(return_rates)

    print("\n=== Performance Summary ===")
    print("Individual Stock Performance (Sorted by Return Rate):")
    print("\n{:<12} {:<8} {:>10} {:>10} {:>12} {:>10}".format(
        "Stock", "Code", "Start", "End", "Final", "Return(%)"
    ))
    print("-" * 70)

    for report in sorted_reports:
        print("{:<12} {:<8} {:>10.2f} {:>10.2f} {:>12.2f} {:>+10.2f}".format(
            report.name,
            report.code,
            report.start_price,
            report.end_price,
            report.final_total,
            report.return_rate
        ))

    print("\nStatistics:")
    print(f"    Average Return: {avg_return:+.2f}%")
    print(f"    Best Return:    {max_return:+.2f}% ({sorted_reports[0].name})")
    print(
        f"    Worst Return:   {min_return:+.2f}% ({sorted_reports[-1].name})")


def test_performance():
    n_days = 300
    strategy = 'egrid'
    reports = []
    for code, info in stocks.items():
        print(f'Testing {info["name"]} ({code})')
        max_quantity = get_max_quantity(code, cash=20000)
        print(f'Max quantity: {max_quantity}')
        while max_quantity > 0:
            reporter = simulate(code, max_quantity, n_days, strategy)
            if reporter.return_rate == 0:
                max_quantity -= 100
                continue
            else:
                reports.append(reporter)
                break
    return reports


if __name__ == "__main__":
    reports = test_performance()
    print_summary(reports)
