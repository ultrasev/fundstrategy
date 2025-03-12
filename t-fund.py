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
    results.sort(key=lambda x: x['default'])

    # Calculate averages
    default_avg = sum(result['default'] for result in results) / len(results)
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
    # asyncio.run(main(code="016530"))
    codes = [
        "001765", "001770", "019457", "016530", "016531", "019458", "018124", "018125", "017968", "001691",
        "016308", "009994", "003993", "012584", "217021", "015143", "009995", "016243", "021489", "017627",
        "016244", "015144", "021490", "018122", "007713", "018123", "011924", "014673", "007343", "020434",
        "011925", "012371", "501081", "015739", "012372", "014674", "017126", "013345", "017125", "017461",
        "013346", "002810", "015740", "018207", "017512", "011160", "000649", "018710", "017513", "016495",
        "017290", "016496", "018208", "011161", "005541", "014317", "018993", "001194", "020315", "005542",
        "012585", "019313", "018994", "019314", "003092", "001864", "012586", "001407", "009537", "017515",
        "017484", "018128", "017483", "012587", "017516", "009538", "008997", "013224", "018129", "001148",
        "017434", "009993", "009092", "010377", "010378", "017050", "017435", "001724", "014543", "017519",
        "017517", "019392", "014243", "017821", "018103", "010371", "008998", "006477", "019361", "018104",
        "019393", "004450", "019362", "015849", "017520", "014544", "017518", "010372", "006718", "019281",
        "017832", "019993", "018835", "016953", "019780", "006719", "011188", "019994", "018836", "016952",
        "019865", "017833", "007132", "010350", "018241", "018240", "021358", "009707", "020722", "015967",
        "021377", "501077", "017521", "020723", "015968", "011223", "017525", "004604", "017523", "017522",
        "009708", "004223", "004605", "008638", "017559", "021378", "017560", "017526", "017524", "017469",
        "012379", "017527", "006355", "018112", "003598", "519029", "100035", "501311", "017528", "021093",
        "020362", "017612", "017470", "018113", "019933", "009601", "015884", "007509", "021092", "021465",
        "021464", "019934", "011969", "018114", "002085", "013533", "006614", "017751", "016067", "012650",
        "018120", "011970", "020592", "017752", "018121", "015751", "160727", "016068", "018115", "012651",
        "004206", "009602", "019347", "015820", "004351", "017746", "001170", "017051", "501301", "017993",
        "019348", "015821", "001048", "017747", "020670", "015412", "012380", "017994", "020671", "019265",
        "021295", "021891", "021298", "021892", "018934", "005164", "015413", "021294", "003835", "005165",
        "022069", "014418", "167002", "022070", "021299", "015504", "671030", "006923", "021957", "000534",
        "019266", "290011", "018002", "019171", "020255", "001167", "161628", "013465", "020256", "012348",
        "001068", "010925", "006924", "210009", "019170", "020335", "010926", "013466", "015043", "020988",
        "016477", "015456", "020336", "012321", "022364", "005914", "020828", "014419", "519767", "022365",
        "015044", "014130", "018094", "013402", "012349", "020829", "018095", "012322", "005255", "015641",
        "018344", "014880", "018134", "018000", "020481", "017653", "014881", "018463", "018362", "018345",
        "018135", "008842", "018363", "020482", "018001", "020607", "018933", "016478", "020893"
    ]
    asyncio.run(compare_strategies(codes))
