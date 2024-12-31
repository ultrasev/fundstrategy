import os


def generate_markdown_table(results: dict, output_path: str):
    """Generate markdown table comparing strategy returns across funds with averages"""
    if not results:
        return "No results to display"

    strategies = list(next(iter(results.values())).keys())

    header = "| Fund Code | " + " | ".join(strategies) + " |"
    separator = "|-----------|" + "|".join(["-" * 15] * len(strategies)) + "|"

    rows = []
    strategy_sums = {strategy: 0.0 for strategy in strategies}
    fund_count = len(results)

    for fund_code, fund_results in results.items():
        row_values = []
        for strategy in strategies:
            profit_rate = fund_results[strategy]['profit_rate']
            strategy_sums[strategy] += profit_rate
            row_values.append(f"{profit_rate:.2f}%")
        rows.append(f"| {fund_code} | " + " | ".join(row_values) + " |")

    # Add average row
    avg_values = [f"{strategy_sums[strategy] /
                     fund_count:.2f}%" for strategy in strategies]
    avg_row = "| Average | " + " | ".join(avg_values) + " |"

    # Combine all parts
    markdown_table = "\n".join([
        header,
        separator,
        "\n".join(rows),
        separator,  # Add separator before average row
        avg_row
    ])

    # Save to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("# Strategy Comparison Results\n\n")
        f.write(markdown_table)

    return markdown_table
