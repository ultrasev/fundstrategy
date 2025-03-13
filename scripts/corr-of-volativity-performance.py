import numpy as np
import pandas as pd

# Read the JSON file
df = pd.read_json('/tmp/fund-performance.json')

# Calculate correlation matrix
correlation_matrix = df[['default', 't_strategy',
                         'dynamic_strategy', 'volatility']].corr()

# Format correlation matrix for markdown
def format_correlation_matrix_markdown(corr_matrix):
    header = "| 指标 | " + " | ".join(corr_matrix.columns) + " |"
    separator = "|---" + "|---" * len(corr_matrix.columns) + "|"
    rows = []
    for idx, row in corr_matrix.iterrows():
        formatted_values = ["{:.4f}".format(val) for val in row]
        rows.append("| {} | {} |".format(idx, " | ".join(formatted_values)))
    return "\n".join([header, separator] + rows)

print("\n## 相关性分析结果\n")
print(format_correlation_matrix_markdown(correlation_matrix))

# Save correlation matrix to CSV for further analysis
correlation_matrix.to_csv('correlation_analysis.csv')

print("\n## 分析说明\n")
print("相关系数解读：")
print("* 接近 1: 强正相关")
print("* 接近 -1: 强负相关")
print("* 接近 0: 相关性较弱")
