import matplotlib.pyplot as plt
import numpy as np

def draw_strategy_comparison(results: dict, output_path: str):
    """Draw comparison chart for different strategies

    Args:
        results: Dictionary containing results for each fund and strategy
        output_path: Path to save the output image
    """
    funds = list(results.keys())
    strategies = list(results[funds[0]].keys())  # Get strategy names from first fund

    # Sort funds by the first strategy's profit rate
    funds.sort(key=lambda x: results[x][strategies[0]]['profit_rate'], reverse=True)

    # Set up the plot
    plt.figure(figsize=(15, 8))
    x = np.arange(len(funds))
    width = 0.8 / len(strategies)

    # Plot bars for each strategy
    for i, strategy in enumerate(strategies):
        profit_rates = [results[fund][strategy]['profit_rate'] for fund in funds]
        plt.bar(x + i * width, profit_rates, width, label=strategy)

    plt.xlabel('Funds')
    plt.ylabel('Profit Rate (%)')
    plt.title('Strategy Comparison Across Funds')
    plt.xticks(x + width * (len(strategies) - 1) / 2, funds, rotation=45)
    plt.legend()
    plt.tight_layout()

    # Save the plot
    plt.savefig(output_path)
    plt.close()
