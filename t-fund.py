from app.fund.configs import STRATEGY_CODES
import asyncio
from app.data.fetch import fetch_fund_data
from decimal import Decimal

from app.fund.strategies import TStrategy, DynamicTStrategy
from app.data.fetch import HistoryReader


class Experiments:
    def __init__(self, code: str):
        self.code = code
        self.reader = HistoryReader(code, 100)

    async def single_strategy(self, strategy: TStrategy | DynamicTStrategy):
        data = await self.reader.read()
        cost, shares, last_price = strategy.calculate()
        initial_price = float(data[0]['DWJZ'])
        avg_cost = cost / shares if shares else 0
        profit = (last_price - avg_cost) * shares
        profit_rate = profit / (initial_price * shares)

        print("Strategy Results:")
        print("Total Cost: {:.4f}".format(cost))
        print("Total Shares: {}".format(shares))
        print("Initial price: {:.4f}".format(initial_price))
        print("Average Cost per Share: {:.4f}".format(avg_cost))
        print("Profit: {:.4f}".format(profit))
        print("Profit Rate: \033[91m{:.4f}%\033[0m".format(profit_rate * 100))
        print("Default profit rate: \033[93m{:.4f}%\033[0m".format(
            (last_price / initial_price - 1) * 100
        ))

    async def compare_strategies(self):
        data = await self.reader.read()
        initial_price = float(data[0]['DWJZ'])
        final_price = float(data[-1]['DWJZ'])
        initial_shares = 10000

        t_strategy = TStrategy(
            data,
            initial_shares=initial_shares,
            sell_holds=1000,
            threshold_rate=1.0
        )

        dynamic_strategy = DynamicTStrategy(
            data,
            initial_shares=initial_shares,
            sell_holds=1000,
            threshold_rate=1.0
        )

        # Calculate results for both strategies
        t_cost, t_shares, t_last_price = t_strategy.calculate()

        dynamic_cost, dynamic_shares, dynamic_last_price = dynamic_strategy.calculate()

        # Calculate metrics for TStrategy
        t_avg_cost = t_cost / t_shares if t_shares else 0
        t_profit = (t_last_price - t_avg_cost) * t_shares
        t_profit_rate = t_profit / (initial_price * initial_shares)

        # Calculate metrics for DynamicTStrategy
        dynamic_avg_cost = dynamic_cost / \
            dynamic_shares if dynamic_shares else 0
        dynamic_profit = (dynamic_last_price -
                          dynamic_avg_cost) * dynamic_shares
        dynamic_profit_rate = dynamic_profit / (initial_price * initial_shares)

        default_profit_rate = (final_price / initial_price - 1) * 100

        # Print comparison results
        print("\nStrategy Comparison Results:")
        print("{:<20} {:<15} {:<15}".format(
            "Metric", "TStrategy", "DynamicTStrategy"))
        print("{:<20} {:<15.4f} {:<15.4f}".format(
            "Total Cost", t_cost, dynamic_cost))
        print("{:<20} {:<15} {:<15}".format(
            "Total Shares", t_shares, dynamic_shares))
        print("{:<20} {:<15.4f} {:<15.4f}".format(
            "Average Cost", t_avg_cost, dynamic_avg_cost))
        print("{:<20} {:<15.4f} {:<15.4f}".format(
            "Profit", t_profit, dynamic_profit))
        print("{:<20} {:<15.4f}% {:<15.4f}%".format(
            "Profit Rate", t_profit_rate * 100, dynamic_profit_rate * 100))
        print("{:<20} {:<15} {:<15}".format(
            "Default Profit", "", "{:.4f}%".format(default_profit_rate)))


class MultiExperiments:
    def __init__(self, codes: list[str]):
        self.codes = codes

    async def process_single_code(self, code: str):
        reader = HistoryReader(code, 100)
        data = await reader.read()
        initial_price = float(data[0]['DWJZ'])
        final_price = float(data[-1]['DWJZ'])
        initial_shares = 10000

        # Initialize strategies
        t_strategy = TStrategy(
            data,
            initial_shares=initial_shares,
            sell_holds=1000,
            threshold_rate=1.0
        )
        dynamic_strategy = DynamicTStrategy(
            data,
            initial_shares=initial_shares,
            sell_holds=1000,
            threshold_rate=1.0
        )

        # Calculate results for both strategies
        t_cost, t_shares, t_last_price = t_strategy.calculate()
        dynamic_cost, dynamic_shares, dynamic_last_price = dynamic_strategy.calculate()

        # Calculate metrics
        t_avg_cost = t_cost / t_shares if t_shares else Decimal('0')
        t_profit = (t_last_price - t_avg_cost) * t_shares
        t_profit_rate = t_profit / (initial_price * initial_shares)

        dynamic_avg_cost = dynamic_cost / \
            dynamic_shares if dynamic_shares else Decimal('0')
        dynamic_profit = (dynamic_last_price -
                          dynamic_avg_cost) * dynamic_shares
        dynamic_profit_rate = dynamic_profit / (initial_price * initial_shares)

        # Default profit
        default_profit_rate = (final_price / initial_price - 1) * 100

        return {
            'code': code,
            'default': default_profit_rate,
            't_strategy': t_profit_rate * 100,
            'dynamic_strategy': dynamic_profit_rate * 100
        }

    async def compare_strategies(self):
        results = []
        for code in self.codes:
            try:
                print(f"Processing {code}...")
                result = await self.process_single_code(code)
                results.append(result)
            except Exception as e:
                pass
        results.sort(key=lambda x: x['default'])

        # Calculate averages
        default_avg = sum(result['default']
                          for result in results) / len(results)
        t_strategy_avg = sum(result['t_strategy']
                             for result in results) / len(results)
        dynamic_strategy_avg = sum(result['dynamic_strategy']
                                   for result in results) / len(results)

        markdown_table = """
    | Code   | Default | TStrategy | DynamicT |
    |--------|---------|-----------|----------|
    """
        for result in results:
            markdown_table += "| {code} | {default:.4f} | {t_strategy:.4f} | {dynamic_strategy:.4f} |\n".format(
                code=result['code'],
                default=result['default'],
                t_strategy=result['t_strategy'],
                dynamic_strategy=result['dynamic_strategy']
            )

        # Add average row
        markdown_table += "| **Average** | **{default_avg:.4f}** | **{t_strategy_avg:.4f}** | **{dynamic_strategy_avg:.4f}** |\n".format(
            default_avg=default_avg,
            t_strategy_avg=t_strategy_avg,
            dynamic_strategy_avg=dynamic_strategy_avg
        )

        print(markdown_table)


if __name__ == "__main__":
    asyncio.run(Experiments(code="009994").compare_strategies())
    # asyncio.run(MultiExperiments(STRATEGY_CODES).compare_strategies())
