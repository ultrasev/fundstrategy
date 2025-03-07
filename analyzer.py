import duckdb
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

class StockAnalyzer:
    def __init__(self):
        self.conn = duckdb.connect('a.duckdb')

    def analyze_stock_momentum(self, code=None, minutes=10):
        """分析个股资金流入和价格的动量"""

        # 先获取最新时间
        latest_time_query = """
            SELECT MAX(created_at) as latest_time
            FROM stocks
        """
        latest_time = self.conn.execute(latest_time_query).fetchone()[0]

        base_query = """
            SELECT
                code,
                name,
                price,
                change_percentage,
                main_inflow,
                main_inflow_ratio,
                created_at
            FROM stocks
            WHERE created_at >= (? - INTERVAL '{} minutes')
            {}
            ORDER BY code, created_at ASC
        """

        where_clause = f"AND code = '{code}'" if code else ""
        query = base_query.format(minutes, where_clause)

        df = self.conn.execute(query, [latest_time]).df()
        if df.empty:
            return pd.DataFrame()

        # 按股票分组分析
        results = []
        for name, group in df.groupby('code'):
            if len(group) < 3:  # 至少需要3个数据点来计算加速度
                continue

            # 计算时间间隔（秒）
            group['time_diff'] = group['created_at'].diff().dt.total_seconds()

            # 计算主力资金变化速度 (万元/秒)
            group['inflow_speed'] = group['main_inflow'].diff() / group['time_diff'] / 10000

            # 计算主力资金加速度 (万元/秒²)
            group['inflow_acceleration'] = group['inflow_speed'].diff() / group['time_diff']

            # 计算价格变化速度 (%/秒)
            group['price_speed'] = group['change_percentage'].diff() / group['time_diff']

            # 计算价格加速度 (%/秒²)
            group['price_acceleration'] = group['price_speed'].diff() / group['time_diff']

            # 获取最新状态
            latest = group.iloc[-1]

            # 计算趋势得分
            inflow_trend = np.mean(group['inflow_acceleration'].tail(3))  # 最近3个周期的平均加速度
            price_trend = np.mean(group['price_acceleration'].tail(3))

            # 计算综合得分 (归一化后的加权平均)
            momentum_score = (
                (inflow_trend / group['inflow_acceleration'].std() if group['inflow_acceleration'].std() != 0 else 0) * 0.6 +
                (price_trend / group['price_acceleration'].std() if group['price_acceleration'].std() != 0 else 0) * 0.4
            )

            results.append({
                'code': latest['code'],
                'name': latest['name'],
                'price': latest['price'],
                'change_percentage': latest['change_percentage'],
                'current_inflow_speed': group['inflow_speed'].iloc[-1],
                'avg_inflow_acceleration': inflow_trend,
                'current_price_speed': group['price_speed'].iloc[-1],
                'avg_price_acceleration': price_trend,
                'momentum_score': momentum_score,
                'samples_count': len(group)
            })

        return pd.DataFrame(results)

    def get_potential_stocks(self):
        """获取有潜力的股票"""
        # 分析最近10分钟的动量
        df = self.analyze_stock_momentum(minutes=10)

        if df.empty:
            print("没有足够的数据来分析动量")
            return pd.DataFrame()

        # 筛选有潜力的股票
        potential_stocks = df[
            (df['change_percentage'] < 9) &     # 还没到涨停
            (df['current_inflow_speed'] > 0) &  # 当前资金流入速度为正
            (df['avg_inflow_acceleration'] > 0) & # 资金流入在加速
            (df['avg_price_acceleration'] > 0)    # 价格在加速上涨
        ].copy()

        return potential_stocks.sort_values('momentum_score', ascending=False).head(10)

    def get_stock_detail(self, stock_code):
        """获取单只股票的详细分析"""
        return self.analyze_stock_momentum(code=stock_code, minutes=30)

    def analyze_stock_trend(self, minutes=30):
        """分析每分钟的趋势变化"""
        # 先获取最新时间
        latest_time_query = """
            SELECT MAX(created_at) as latest_time
            FROM stocks
        """
        latest_time = self.conn.execute(latest_time_query).fetchone()[0]

        # 按分钟聚合的查询
        query = """
            WITH minute_data AS (
                SELECT
                    code,
                    name,
                    DATE_TRUNC('minute', created_at) as minute,
                    -- 每分钟的最后一条价格和涨跌幅
                    LAST_VALUE(price) OVER (
                        PARTITION BY code, DATE_TRUNC('minute', created_at)
                        ORDER BY created_at
                        RANGE BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
                    ) as price,
                    LAST_VALUE(change_percentage) OVER (
                        PARTITION BY code, DATE_TRUNC('minute', created_at)
                        ORDER BY created_at
                        RANGE BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
                    ) as change_percentage,
                    -- 计算每分钟的主力净流入
                    SUM(main_inflow) as minute_inflow
                FROM stocks
                WHERE created_at >= (? - INTERVAL '{} minutes')
                GROUP BY code, name, DATE_TRUNC('minute', created_at)
            )
            SELECT
                code,
                name,
                minute,
                price,
                change_percentage,
                minute_inflow,
                -- 计算移动平均
                AVG(minute_inflow) OVER (
                    PARTITION BY code
                    ORDER BY minute
                    ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
                ) as inflow_ma3,
                -- 计算相对强度指标 (RSI)
                100 - (100 / (1 + (
                    SUM(CASE WHEN minute_inflow > 0 THEN minute_inflow ELSE 0 END) OVER (
                        PARTITION BY code
                        ORDER BY minute
                        ROWS BETWEEN 13 PRECEDING AND CURRENT ROW
                    ) /
                    NULLIF(SUM(CASE WHEN minute_inflow < 0 THEN ABS(minute_inflow) ELSE 0 END) OVER (
                        PARTITION BY code
                        ORDER BY minute
                        ROWS BETWEEN 13 PRECEDING AND CURRENT ROW
                    ), 0)
                ))) as inflow_rsi
            FROM minute_data
            ORDER BY code, minute DESC
        """.format(minutes)

        df = self.conn.execute(query, [latest_time]).df()

        # 计算趋势指标
        results = []
        for code, group in df.groupby('code'):
            if len(group) < 5:  # 至少需要5分钟数据
                continue

            # 获取最新数据
            latest = group.iloc[0]

            # 计算主力资金趋势
            inflow_trend = group['minute_inflow'].rolling(window=5).mean()
            inflow_trend_slope = np.polyfit(range(len(inflow_trend.dropna())),
                                          inflow_trend.dropna(), 1)[0]

            # 计算价格趋势
            price_trend = group['change_percentage'].rolling(window=5).mean()
            price_trend_slope = np.polyfit(range(len(price_trend.dropna())),
                                         price_trend.dropna(), 1)[0]

            # 计算综合得分
            trend_score = (
                (inflow_trend_slope > 0) * 0.6 +  # 资金流入趋势向上
                (price_trend_slope > 0) * 0.4 +   # 价格趋势向上
                (latest['inflow_rsi'] > 50) * 0.3 # RSI大于50表示强势
            )

            results.append({
                'code': latest['code'],
                'name': latest['name'],
                'price': latest['price'],
                'change_percentage': latest['change_percentage'],
                'latest_minute_inflow': latest['minute_inflow'],
                'inflow_ma3': latest['inflow_ma3'],
                'inflow_rsi': latest['inflow_rsi'],
                'inflow_trend_slope': inflow_trend_slope,
                'price_trend_slope': price_trend_slope,
                'trend_score': trend_score,
                'continuous_up_minutes': len(group[group['minute_inflow'] > 0])
            })

        return pd.DataFrame(results)

    def get_trending_stocks(self):
        """获取处于上涨趋势的股票"""
        df = self.analyze_stock_trend(minutes=30)

        if df.empty:
            print("没有足够的数据来分析趋势")
            return pd.DataFrame()

        # 筛选强势股
        trending_stocks = df[
            (df['change_percentage'] < 9) &      # 还有上涨空间
            (df['inflow_trend_slope'] > 0) &     # 资金流入趋势向上
            (df['price_trend_slope'] > 0) &      # 价格趋势向上
            (df['inflow_rsi'] > 50) &           # RSI大于50表示强势
            (df['continuous_up_minutes'] >= 3)   # 连续3分钟以上资金流入
        ].copy()

        return trending_stocks.sort_values('trend_score', ascending=False).head(10)

    def analyze_price_inflow_correlation(self, minutes=30):
        """分析主力资金注入与价格变化的相关性"""
        latest_time_query = """
            SELECT MAX(created_at) as latest_time
            FROM stocks
        """
        latest_time = self.conn.execute(latest_time_query).fetchone()[0]

        query = """
            SELECT
                code,
                name,
                price,
                change_percentage,
                main_inflow,
                created_at
            FROM stocks
            WHERE created_at >= (? - INTERVAL '{} minutes')
            ORDER BY code, created_at
        """.format(minutes)

        df = self.conn.execute(query, [latest_time]).df()

        results = []
        for code, group in df.groupby('code'):
            if len(group) < 5:  # 降低最小数据点要求到5个
                continue

            group = group.sort_values('created_at')

            # 计算变化值
            price_changes = group['price'].diff().dropna()
            inflow_changes = group['main_inflow'].diff().dropna()

            if len(price_changes) < 5:
                continue

            try:
                # 使用 numpy 的 corrcoef，处理异常情况
                if price_changes.std() == 0 or inflow_changes.std() == 0:
                    correlation = 0
                else:
                    correlation_matrix = np.corrcoef(price_changes, inflow_changes)
                    correlation = correlation_matrix[0, 1]
                    # 处理 nan 值
                    if np.isnan(correlation):
                        correlation = 0

                # 计算最新的变化趋势（用最后3个点的平均值）
                latest_price_change = price_changes.tail(3).mean()
                latest_inflow_change = inflow_changes.tail(3).mean()

                # 获取最新数据
                latest = group.iloc[-1]

                results.append({
                    'code': latest['code'],
                    'name': latest['name'],
                    'price': latest['price'],
                    'change_percentage': latest['change_percentage'],
                    'correlation': correlation,
                    'r_squared': correlation ** 2 if not np.isnan(correlation) else 0,
                    'latest_price_change': latest_price_change,
                    'latest_inflow_change': latest_inflow_change,
                    'data_points': len(price_changes),
                    'price_volatility': price_changes.std(),
                    'inflow_volatility': inflow_changes.std()
                })

            except Exception as e:
                print(f"处理股票 {code} 时出错: {str(e)}")
                continue

        return pd.DataFrame(results)

    def get_highly_correlated_stocks(self):
        """获取主力资金与价格高度相关的股票"""
        df = self.analyze_price_inflow_correlation(minutes=30)

        if df.empty:
            print("没有足够的数据来分析相关性")
            return pd.DataFrame()

        # 放宽筛选条件
        correlated_stocks = df[
            (df['correlation'] > 0.3) &           # 降低相关性要求
            (df['data_points'] >= 5) &            # 降低数据点要求
            (df['change_percentage'] < 9.8) &     # 稍微放宽涨幅限制
            (df['price_volatility'] > 0) &        # 确保有价格波动
            (df['inflow_volatility'] > 0)         # 确保有资金波动
        ].copy()

        # 计算综合得分
        correlated_stocks['final_score'] = (
            correlated_stocks['correlation'] * 0.5 +          # 相关性权重
            (correlated_stocks['data_points'] / 100 * 0.3) + # 数据点数量权重
            (correlated_stocks['latest_price_change'] > 0) * 0.1 + # 最近价格上涨加分
            (correlated_stocks['latest_inflow_change'] > 0) * 0.1  # 最近资金流入加分
        )

        return correlated_stocks.sort_values('final_score', ascending=False).head(10)

    def analyze_price_momentum(self, start_time='13:00', end_time='13:05'):
        """分析指定时间段内的涨幅变化"""
        query = """
            WITH time_range_data AS (
                SELECT
                    code,
                    name,
                    price,
                    change_percentage,
                    main_inflow,
                    created_at,
                    -- 获取每只股票在时间段内的第一个和最后一个价格
                    FIRST_VALUE(price) OVER (
                        PARTITION BY code
                        ORDER BY created_at
                        RANGE BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
                    ) as start_price,
                    LAST_VALUE(price) OVER (
                        PARTITION BY code
                        ORDER BY created_at
                        RANGE BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
                    ) as end_price,
                    -- 获取时间段内的累计主力净流入
                    SUM(main_inflow) OVER (
                        PARTITION BY code
                    ) as total_inflow
                FROM stocks
                WHERE cast(created_at as time) >= cast(? as time)
                AND cast(created_at as time) <= cast(? as time)
            )
            SELECT
                code,
                name,
                MIN(price) as min_price,
                MAX(price) as max_price,
                MIN(start_price) as start_price,
                MIN(end_price) as end_price,
                MIN(total_inflow) as total_inflow,
                COUNT(*) as data_points
            FROM time_range_data
            GROUP BY code, name
        """

        df = self.conn.execute(query, [start_time, end_time]).df()

        if df.empty:
            print(f"在 {start_time} 到 {end_time} 之间没有找到数据")
            return pd.DataFrame()

        # 计算涨幅和速率
        df['price_change_pct'] = (df['end_price'] - df['start_price']) / df['start_price'] * 100
        df['price_change_speed'] = df['price_change_pct'] / 5  # 每分钟平均涨幅
        df['price_volatility'] = (df['max_price'] - df['min_price']) / df['min_price'] * 100

        # 计算主力资金流入速率（万元/分钟）
        df['inflow_speed'] = df['total_inflow'] / 5 / 10000

        return df.sort_values('price_change_speed', ascending=False)

    def __del__(self):
        if hasattr(self, 'conn'):
            self.conn.close()

def main():
    analyzer = StockAnalyzer()
    momentum_stocks = analyzer.analyze_price_momentum('13:00', '13:05')

    if momentum_stocks.empty:
        return

    print("\n=== 13:00-13:05 涨幅最快的股票 ===")
    print("-" * 100)

    for _, stock in momentum_stocks.head(20).iterrows():
        print(
            f"股票：{stock['name']}({stock['code']}) "
            f"起始价：{stock['start_price']:.2f} "
            f"结束价：{stock['end_price']:.2f} "
            f"5分钟涨幅：{stock['price_change_pct']:.2f}% "
            f"平均每分钟涨幅：{stock['price_change_speed']:.2f}% "
            f"波动幅度：{stock['price_volatility']:.2f}% "
            f"主力净流入：{stock['total_inflow']/10000:.2f}万 "
            f"数据点数：{stock['data_points']}"
        )
        print("-" * 100)

if __name__ == '__main__':
    main()