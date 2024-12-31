import matplotlib.pyplot as plt


def draw_strategy_comparison(results: dict, output_path: str):
    """Plot strategy comparison across different funds using line plots"""
    # Prepare data for plotting
    strategies = list(next(iter(results.values())).keys())
    funds = list(results.keys())
    funds.sort(key=lambda x: results[x]
               ['Enhanced RSI']['profit_rate'], reverse=True)

    plt.figure(figsize=(15, 8))

    # Plot a line for each strategy
    for strategy in strategies:
        returns = [results[fund][strategy]['profit_rate'] for fund in funds]
        plt.plot(funds, returns, marker='.',
                 label=strategy, linewidth=2, markersize=8)

    plt.title('Strategy Performance Comparison Across Funds')
    plt.xlabel('Fund Code')
    plt.ylabel('Return Rate (%)')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.xticks(rotation=45)
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches='tight', dpi=300)
    plt.close()
