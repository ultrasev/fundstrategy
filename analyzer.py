import duckdb
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

class StockAnalyzer:
    def __init__(self):
        self.conn = duckdb.connect('a.duckdb')

    def get_potential_stocks(self):
        # Get data from the last 30 minutes
        query = """
            WITH recent_data AS (
                SELECT
                    code,
                    name,
                    price,
                    change_percentage,
                    main_inflow,
                    main_inflow_ratio,
                    large_inflow,
                    large_inflow_ratio,
                    big_inflow,
                    big_inflow_ratio,
                    created_at,
                    ROW_NUMBER() OVER (PARTITION BY code ORDER BY created_at DESC) as rn
                FROM stocks
                WHERE created_at >= (CURRENT_TIMESTAMP - INTERVAL '30 minutes')
            )
            SELECT
                code,
                name,
                price,
                change_percentage,
                main_inflow,
                main_inflow_ratio,
                large_inflow,
                large_inflow_ratio,
                big_inflow,
                big_inflow_ratio,
                created_at
            FROM recent_data
            WHERE rn = 1
            """

        df = self.conn.execute(query).df()

        if df.empty:
            print("没有找到最近30分钟的数据，尝试获取最新数据...")
            query = """
                WITH recent_data AS (
                    SELECT
                        code,
                        name,
                        price,
                        change_percentage,
                        main_inflow,
                        main_inflow_ratio,
                        large_inflow,
                        large_inflow_ratio,
                        big_inflow,
                        big_inflow_ratio,
                        created_at,
                        ROW_NUMBER() OVER (PARTITION BY code ORDER BY created_at DESC) as rn
                    FROM stocks
                )
                SELECT
                    code,
                    name,
                    price,
                    change_percentage,
                    main_inflow,
                    main_inflow_ratio,
                    large_inflow,
                    large_inflow_ratio,
                    big_inflow,
                    big_inflow_ratio,
                    created_at
                FROM recent_data
                WHERE rn = 1
                """
            df = self.conn.execute(query).df()

        if df.empty:
            print("数据库中没有找到任何数据！")
            return pd.DataFrame()

        # Calculate composite score
        df['inflow_score'] = (
            df['main_inflow_ratio'] * 0.4 +  # 主力净流入占比权重最大
            df['large_inflow_ratio'] * 0.3 +  # 超大单净流入占比次之
            df['big_inflow_ratio'] * 0.3      # 大单净流入占比
        )

        # Filter potential stocks
        potential_stocks = df[
            (df['change_percentage'] > 2) &    # 已经有上涨趋势
            (df['change_percentage'] < 9) &    # 还没到涨停，有上涨空间
            (df['main_inflow'] > 1000000) &   # 主力净流入大于100万
            (df['inflow_score'] > 0)          # 综合资金流入为正
        ].copy()

        # Sort by potential (综合排名)
        potential_stocks['final_score'] = (
            potential_stocks['inflow_score'] * 0.6 +
            (potential_stocks['change_percentage'] / 10) * 0.4  # 归一化涨跌幅
        )

        return potential_stocks.sort_values('final_score', ascending=False).head(10)

    def get_stock_trend(self, stock_code):
        """分析单个股票的资金流向趋势"""
        query = """
            SELECT
                code,
                name,
                price,
                change_percentage,
                main_inflow,
                main_inflow_ratio,
                created_at
            FROM stocks
            WHERE code = ?
            AND created_at >= (CURRENT_TIMESTAMP - INTERVAL '120 minutes')
            ORDER BY created_at ASC
        """

        df = self.conn.execute(query, [stock_code]).df()
        return df

    def __del__(self):
        if hasattr(self, 'conn'):
            self.conn.close()

def main():
    analyzer = StockAnalyzer()

    # 获取潜在的强势股
    potential_stocks = analyzer.get_potential_stocks()

    if potential_stocks.empty:
        print("未找到符合条件的股票")
        return

    print("\n=== 潜在强势股票 (前10名) ===")
    print("排名依据：主力资金流入、超大单流入、大单流入、涨跌幅综合评分")
    print("-" * 80)

    for _, stock in potential_stocks.iterrows():
        print(
            f"股票：{stock['name']}({stock['code']}) "
            f"当前价：{stock['price']:.2f} "
            f"涨跌幅：{stock['change_percentage']:.2f}% "
            f"主力净流入：{stock['main_inflow']/10000:.2f}万 "
            f"主力净占比：{stock['main_inflow_ratio']:.2f}% "
            f"综合评分：{stock['final_score']:.2f}"
        )

        # 获取该股票的近期走势
        trend = analyzer.get_stock_trend(stock['code'])
        if not trend.empty:
            print(f"近2小时主力资金流入趋势：", end=" ")
            flow_trend = trend['main_inflow'].diff().fillna(0)
            trend_str = "".join(['↑' if x > 0 else '↓' if x < 0 else '-' for x in flow_trend])
            print(trend_str)
        print("-" * 80)

if __name__ == '__main__':
    main()