from app.fund.configs import STRATEGY_CODES
from app.data.fetch import read_history
import numpy as np
import asyncio
from typing import List, Dict
import pandas as pd


async def calculate_volatility(fund_code: str) -> float:
    """Calculate volatility for a single fund"""
    try:
        # Fetch historical data
        data = await read_history(fund_code)

        if not data or len(data) < 2:
            return 0.0

        # Extract and process change rates
        change_rates = [float(entry['JZZZL'])
                        for entry in data if entry['JZZZL']]

        if len(change_rates) < 2:
            return 0.0

        # Calculate standard deviation
        return np.std(change_rates, ddof=1)

    except Exception as e:
        print(f"Error calculating volatility for fund {fund_code}: {str(e)}")
        return 0.0


async def analyze_volatility(fund_codes: List[str]) -> Dict[str, float]:
    """Analyze volatility for multiple funds"""
    results = {}

    # Process funds in chunks
    chunk_size = 5
    for i in range(0, len(fund_codes), chunk_size):
        print(f"Processing {i} of {len(fund_codes)}")
        chunk = fund_codes[i:i + chunk_size]
        chunk_results = await asyncio.gather(*(calculate_volatility(code) for code in chunk))
        results.update(dict(zip(chunk, chunk_results)))
        await asyncio.sleep(1)  # Rate limiting

    return results


def generate_markdown_report(volatility_results: Dict[str, float]) -> str:
    """Generate a markdown formatted report"""
    # Convert results to DataFrame for easier manipulation
    df = pd.DataFrame(list(volatility_results.items()),
                      columns=['Fund Code', 'Volatility'])
    df = df.sort_values('Volatility')

    # Generate markdown report
    report = []
    report.append("# Fund Volatility Analysis Report\n")

    # Summary Statistics
    report.append("## Summary Statistics")
    stats = {
        "Average Volatility": f"{np.mean(df['Volatility']):.2f}%",
        "Median Volatility": f"{np.median(df['Volatility']):.2f}%",
        "Minimum Volatility": f"{df['Volatility'].min():.2f}%",
        "Maximum Volatility": f"{df['Volatility'].max():.2f}%"
    }
    report.append("\n| Metric | Value |")
    report.append("|--------|--------|")
    for metric, value in stats.items():
        report.append(f"| {metric} | {value} |")

    # Detailed Fund Analysis
    report.append("\n## Detailed Fund Analysis")
    report.append("\n| Fund Code | Volatility |")
    report.append("|-----------|------------|")
    for _, row in df.iterrows():
        report.append(f"| {row['Fund Code']} | {row['Volatility']:.2f}% |")

    return "\n".join(report)


async def main():
    # Calculate volatility for all strategy codes
    volatility_results = await analyze_volatility(STRATEGY_CODES)

    # Generate and save markdown report
    report = generate_markdown_report(volatility_results)
    print(report)


if __name__ == "__main__":
    asyncio.run(main())
