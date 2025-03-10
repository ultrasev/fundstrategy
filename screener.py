import duckdb
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import warnings

# 忽略除零警告和其他警告
warnings.filterwarnings('ignore', category=RuntimeWarning)
warnings.filterwarnings('ignore', category=FutureWarning)

logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s')

class StockScreener:
    def __init__(self, db_path='stocks.duckdb'):
        """初始化筛选器"""
        self.conn = duckdb.connect(db_path)
        self.params = {
            'min_inflow': 5e4,  # 主力净流入最小值（5万，更关注趋势）
            'min_price_slope': 0.0001,  # 最小价格斜率（0.01%/分钟）
            'max_price_slope': 0.01,  # 最大价格斜率（1%/分钟）
            'min_vol_growth': 0.01,  # 最小成交量增长（1%）
            'max_vol_growth': 0.5,  # 最大成交量增长（50%）
            'window_size': 10,  # 观察窗口（10个数据点）
            'resample_minutes': 1  # 重采样间隔（分钟）
        }

    def check_data_availability(self, start_time: str, end_time: str) -> None:
        """检查指定时间段的数据情况"""
        query = """
        WITH stats AS (
            SELECT
                code,
                COUNT(*) as data_points,
                MIN(created_at) as first_time,
                MAX(created_at) as last_time,
                SUM(main_inflow) as total_inflow,
                AVG(main_inflow) as avg_inflow,
                AVG(main_inflow_ratio) as avg_inflow_ratio
            FROM stocks
            WHERE created_at >= CAST(? AS TIMESTAMP)
              AND created_at <= CAST(? AS TIMESTAMP)
            GROUP BY code
        )
        SELECT
            COUNT(DISTINCT code) as stock_count,
            AVG(data_points) as avg_points_per_stock,
            MIN(first_time) as period_start,
            MAX(last_time) as period_end,
            COUNT(CASE WHEN total_inflow > 0 THEN 1 END) as positive_inflow_stocks,
            AVG(CASE WHEN total_inflow > 0 THEN avg_inflow END) as avg_positive_inflow,
            AVG(CASE WHEN total_inflow > 0 THEN avg_inflow_ratio END) as avg_positive_ratio
        FROM stats
        """
        result = self.conn.execute(query, [start_time, end_time]).fetchone()
        logging.info(f"数据统计:")
        logging.info(f"股票数量: {result[0]}")
        logging.info(f"每只股票平均数据点数: {result[1]:.1f}")
        logging.info(f"数据时间范围: {result[2]} 到 {result[3]}")
        logging.info(f"主力净流入为正的股票数: {result[4]}")
        logging.info(f"主力净流入为正的股票平均流入: {result[5]/10000:.2f}万")
        logging.info(f"主力净流入为正的股票平均净流入比例: {result[6]:.2%}")

    def get_stock_data(self, start_time: str, end_time: str) -> pd.DataFrame:
        """获取指定时间段的股票数据"""
        query = """
        SELECT code, price, volume, main_inflow, created_at,
               main_inflow_ratio, turnover, name,
               LEAD(price) OVER (PARTITION BY code ORDER BY created_at) as next_price,
               LEAD(volume) OVER (PARTITION BY code ORDER BY created_at) as next_volume
        FROM stocks
        WHERE created_at >= CAST(? AS TIMESTAMP)
          AND created_at <= CAST(? AS TIMESTAMP)
        ORDER BY created_at
        """
        return self.conn.execute(query, [start_time, end_time]).df()

    def resample_data(self, group: pd.DataFrame) -> pd.DataFrame:
        """对数据进行重采样，减少噪音"""
        group = group.copy()
        group['created_at'] = pd.to_datetime(group['created_at'])
        group.set_index('created_at', inplace=True)

        # 按分钟重采样，使用'min'而不是'T'
        resampled = group.resample(f'{self.params["resample_minutes"]}min').agg({
            'price': 'last',
            'volume': 'sum',
            'main_inflow': 'sum',
            'main_inflow_ratio': 'mean',
            'turnover': 'sum',
            'name': 'last',
            'code': 'last'
        }).dropna()

        return resampled.reset_index()

    def calculate_slopes(self, group: pd.DataFrame) -> dict:
        """计算价格和成交量的斜率"""
        if len(group) < self.params['window_size']:
            return None

        # 重采样数据
        group = self.resample_data(group)
        if len(group) < self.params['window_size']:
            return None

        recent_data = group.tail(self.params['window_size'])
        x = np.arange(len(recent_data))

        # 计算价格斜率
        price_slope = np.polyfit(x, recent_data['price'].values, 1)[0]
        price_slope_pct = price_slope / recent_data['price'].iloc[0]

        # 计算成交量增长（处理零值情况）
        recent_vol = recent_data['volume'].tail(3).mean()
        prev_vol = recent_data['volume'].head(3).mean()

        if prev_vol > 0:
            vol_growth = (recent_vol / prev_vol) - 1
        else:
            vol_growth = 1.0 if recent_vol > 0 else 0.0

        # 计算主力资金流入
        inflows = recent_data['main_inflow'].values
        avg_inflow = np.mean(inflows)
        inflow_trend = np.diff(inflows).mean()

        # 计算波动率
        price_volatility = recent_data['price'].std() / recent_data['price'].mean()

        # 计算价格趋势的稳定性（R方值）
        try:
            _, residuals, _, _, _ = np.polyfit(x, recent_data['price'].values, 1, full=True)
            r_squared = 1 - residuals[0] / (len(x) * recent_data['price'].var()) if len(residuals) > 0 else 0
        except:
            r_squared = 0

        return {
            'price_slope': price_slope_pct,
            'vol_growth': vol_growth,
            'avg_inflow': avg_inflow,
            'inflow_trend': inflow_trend,
            'volatility': price_volatility,
            'r_squared': r_squared
        }

    def screen_stocks(self, start_time: str, end_time: str) -> list:
        """筛选符合条件的股票"""
        df = self.get_stock_data(start_time, end_time)
        if df.empty:
            logging.warning("没有找到符合时间条件的数据")
            return []

        results = []
        for code, group in df.groupby('code'):
            metrics = self.calculate_slopes(group)
            if not metrics:
                continue

            # 筛选条件
            conditions = [
                metrics['avg_inflow'] > self.params['min_inflow'],  # 主力资金流入
                metrics['inflow_trend'] > 0,  # 主力资金加速流入
                metrics['price_slope'] > self.params['min_price_slope'],  # 价格上涨
                metrics['price_slope'] < self.params['max_price_slope'],  # 但不能涨太快
                metrics['r_squared'] > 0.6,  # 价格走势较为稳定
                metrics['volatility'] < 0.02  # 波动率小于2%
            ]

            if all(conditions):
                latest = group.iloc[-1]
                results.append({
                    'code': code,
                    'name': latest['name'],
                    'price': latest['price'],
                    'main_inflow': latest['main_inflow'],
                    'main_inflow_ratio': latest['main_inflow_ratio'],
                    'metrics': metrics
                })

        return sorted(results, key=lambda x: x['metrics']['avg_inflow'], reverse=True)

def main():
    screener = StockScreener()

    # 使用2025年3月10日9:30到10:30的数据
    start_time = '2025-03-10 09:30:00'
    end_time = '2025-03-10 10:30:00'
    logging.info(f"分析时间范围: {start_time} 到 {end_time}")

    # 先检查数据情况
    screener.check_data_availability(start_time, end_time)

    # 扫描符合条件的股票
    results = screener.screen_stocks(start_time, end_time)

    if not results:
        logging.info("没找到符合条件的股票")
        return

    logging.info(f"找到 {len(results)} 只符合条件的股票:")
    for stock in results:
        logging.info(
            f"股票代码: {stock['code']}, "
            f"股票名称: {stock['name']}, "
            f"当前价: {stock['price']:.2f}, "
            f"主力净流入: {stock['main_inflow']/10000:.2f}万, "
            f"主力净流入占比: {stock['main_inflow_ratio']:.2%}, "
            f"价格斜率: {stock['metrics']['price_slope']:.2%}/分钟, "
            f"价格稳定性: {stock['metrics']['r_squared']:.2%}, "
            f"波动率: {stock['metrics']['volatility']:.2%}"
        )

if __name__ == "__main__":
    main()