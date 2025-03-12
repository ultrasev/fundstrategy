import asyncio
from app.data.fetch import fetch_fund_data
from decimal import Decimal

from app.fund.strategies import TStrategy, DynamicTStrategy
from app.data.fetch import HistoryReader


async def main(code: str = "110022"):
    reader = HistoryReader(code, 100)
    data = await reader.read()
    strategy = TStrategy(
        data,
        initial_shares=10000,
        sell_holds=1000,
        threshold_rate=1.0
    )
    cost, shares, last_price = strategy.calculate()
    avg_cost = cost / shares if shares else Decimal('0')
    profit = (last_price - avg_cost) * shares
    profit_rate = profit / cost

    print("Strategy Results:")
    print("Total Cost: {:.4f}".format(cost))
    print("Total Shares: {}".format(shares))
    print("Initial price: {:.4f}".format(float(data[0]['DWJZ'])))
    print("Average Cost per Share: {:.4f}".format(avg_cost))
    print("Profit: {:.4f}".format(profit))
    print("Profit Rate: \033[91m{:.4f}%\033[0m".format(profit_rate * 100))
    print("Default profit rate: \033[93m{:.4f}%\033[0m".format(
        (last_price / float(data[0]['DWJZ']) - 1) * 100
    ))


async def compare_strategies(code: str = "010003"):
    data = await fetch_fund_data(code, 100)

    # Initialize strategies
    t_strategy = TStrategy(
        data,
        initial_shares=10000,
        sell_holds=1000,
        threshold_rate=1.0
    )
    dynamic_strategy = DynamicTStrategy(
        data,
        initial_shares=10000,
        sell_holds=1000,
        threshold_rate=1.0
    )

    # Calculate results for both strategies
    t_cost, t_shares, t_last_price = t_strategy.calculate()
    dynamic_cost, dynamic_shares, dynamic_last_price = dynamic_strategy.calculate()

    # Calculate metrics for TStrategy
    t_avg_cost = t_cost / t_shares if t_shares else 0
    t_profit = (t_last_price - t_avg_cost) * t_shares
    t_profit_rate = t_profit / t_cost

    # Calculate metrics for DynamicTStrategy
    dynamic_avg_cost = dynamic_cost / \
        dynamic_shares if dynamic_shares else 0
    dynamic_profit = (dynamic_last_price - dynamic_avg_cost) * dynamic_shares
    dynamic_profit_rate = dynamic_profit / dynamic_cost

    # Calculate default profit
    initial_price = float(data[0]['DWJZ'])
    final_price = float(data[-1]['DWJZ'])
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


async def process_single_code(code: str):
    reader = HistoryReader(code, 100)
    data = await reader.read()

    # Initialize strategies
    t_strategy = TStrategy(
        data,
        initial_shares=10000,
        sell_holds=1000,
        threshold_rate=1.0
    )
    dynamic_strategy = DynamicTStrategy(
        data,
        initial_shares=10000,
        sell_holds=1000,
        threshold_rate=1.0
    )

    # Calculate results for both strategies
    t_cost, t_shares, t_last_price = t_strategy.calculate()
    dynamic_cost, dynamic_shares, dynamic_last_price = dynamic_strategy.calculate()

    # Calculate metrics
    t_avg_cost = t_cost / t_shares if t_shares else Decimal('0')
    t_profit = (t_last_price - t_avg_cost) * t_shares
    t_profit_rate = t_profit / t_cost

    dynamic_avg_cost = dynamic_cost / \
        dynamic_shares if dynamic_shares else Decimal('0')
    dynamic_profit = (dynamic_last_price - dynamic_avg_cost) * dynamic_shares
    dynamic_profit_rate = dynamic_profit / dynamic_cost

    # Default profit
    initial_price = float(data[0]['DWJZ'])
    final_price = float(data[-1]['DWJZ'])
    default_profit_rate = (final_price / initial_price - 1) * 100

    return {
        'code': code,
        'default': default_profit_rate,
        't_strategy': t_profit_rate * 100,
        'dynamic_strategy': dynamic_profit_rate * 100
    }


async def compare_strategies(codes: list[str]):
    results = []
    for code in codes:
        try:
            print(f"Processing {code}...")
            result = await process_single_code(code)
            results.append(result)
        except:
            pass
    markdown_table = """
| Code   | Default | TStrategy | DynamicT |
|--------|---------------------|------------------|--------------------------|
"""
    for result in results:
        markdown_table += "| {code} | {default:.4f} | {t_strategy:.4f} | {dynamic_strategy:.4f} |\n".format(
            code=result['code'],
            default=result['default'],
            t_strategy=result['t_strategy'],
            dynamic_strategy=result['dynamic_strategy']
        )

    print(markdown_table)


if __name__ == "__main__":
    # asyncio.run(main(code="016530"))
    codes = [
        "014127", "460002", "015839", "019863", "166002", "160323", "014157", "008480", "013183", "010729", "012445", "014130", "007471", "011326", "750002", "011611", "022895", "009604", "011555", "001891", "016068", "011587", "016199", "014028", "003863", "004750", "012970", "008842", "010430", "014084", "004453", "009726", "009421", "005039", "013250", "013402", "008715", "007605", "018103", "018178", "012060", "001230", "012636", "005143", "008477", "009006", "017526", "011971", "501076", "519704", "004522", "501301", "020592", "008714", "000471", "001444", "001285", "010310", "019573", "016952", "015916", "011149", "011221", "004959", "008399", "013068", "011241", "000928", "008571", "008894", "017745", "019767", "002810", "005632", "161723", "009908", "011288", "003547", "002820", "012607", "015707", "006786", "009422", "460010", "019151", "018818", "006692", "257050", "009024", "015821", "001382", "011350", "002214", "010657", "012884", "016617", "010038"]

    asyncio.run(compare_strategies(codes))
