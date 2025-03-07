from pydantic import BaseModel, Field
import httpx
import asyncio
import json


class StockData(BaseModel):
    data_type: int          # 数据类型标识符
    price: float            # 当前价格
    change_percentage: float  # 涨跌幅
    code: str               # 股票代码
    status: int             # 股票状态（0表示正常，1表示停牌等）
    name: str               # 股票名称
    volume: float = Field(default=0.0)           # 成交量
    turnover: float = Field(default=0.0)         # 成交额
    pe_ratio: float = Field(default=0.0)         # 市盈率（PE Ratio）
    main_inflow: float = Field(default=0.0)      # 主力净注入
    main_inflow_ratio: float = Field(default=0.0)  # 主力净注入占比
    large_inflow: float = Field(default=0.0)      # 超大单净注入
    large_inflow_ratio: float = Field(default=0.0)  # 超大单净注入占比
    big_inflow: float = Field(default=0.0)        # 大单净注入
    big_inflow_ratio: float = Field(default=0.0)   # 大单净注入占比
    medium_inflow: float = Field(default=0.0)      # 中单净注入
    medium_inflow_ratio: float = Field(default=0.0)  # 中单净注入占比
    small_inflow: float = Field(default=0.0)        # 小单净注入
    small_inflow_ratio: float = Field(default=0.0)  # 小单净注入占比
    daily_change: float = Field(default=0.0)      # 近一日涨跌幅
    daily_volume: float = Field(default=0.0)      # 近一日成交量
    daily_turnover: float = Field(default=0.0)    # 近一日成交额
    update_timestamp: int = Field(default=0)      # 更新时间戳
    status_info_1: str = Field(default='')         # 其他状态或信息
    status_info_2: str = Field(default='')         # 其他状态或信息
    status_info_3: str = Field(default='')         # 其他状态或信息

    def __str__(self):
        return f"股票代码: {self.code}, 股票名称: {self.name}, 最新价: {self.price}, 涨跌幅: {self.change_percentage}, 主力净注入: {self.main_inflow}, 超大单净注入: {self.large_inflow}, 大单净注入: {self.big_inflow}, 中单净注入: {self.medium_inflow}, 小单净注入: {self.small_inflow}"


class PriceReader:
    def __init__(self):
        self.url = 'https://push2.eastmoney.com/api/qt/clist/get'
        self.params = {
            'cb': 'jQuery112308868174707193375_1741226624773',
            'fid': 'f62',
            'po': 1,
            'pz': 50,
            'pn': 1,
            'np': 1,
            'fltt': 2,
            'invt': 2,
            'ut': '8dec03ba335b81bf4ebdf7b29ec27d15',
            'fs': 'm:0+t:6+f:1,m:0+t:13+f:1,m:0+t:80+f:1,m:1+t:2+f:1,m:1+t:23+f:1',
            'fields': 'f12,f14,f2,f3,f62,f184,f66,f69,f72,f75,f78,f81,f84,f87,f204,f205,f124,f1,f13'
        }
        self.headers = {
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
            'dnt': '1',
            'referer': 'https://data.eastmoney.com/zjlx/detail.html',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36'
        }

    async def read(self):
        async with httpx.AsyncClient() as client:
            response = await client.get(self.url, params=self.params, headers=self.headers)
            return response.text

    def parse(self, text):
        json_data = text[text.index('(') + 1:text.rindex(')')]
        parsed = json.loads(json_data)

        stock_list = []
        for item in parsed['data']['diff']:
            stock = StockData(
                data_type=item['f1'],  # 数据类型标识符
                price=item['f2'],  # 最新价
                change_percentage=item['f3'],  # 涨跌幅
                code=item['f12'],  # 股票代码
                status=item['f13'],  # 股票状态
                name=item['f14'],  # 股票名称
                main_inflow=self.parse_float(item['f62']),  # 主力注入净额
                large_inflow=self.parse_float(item['f66']),  # 超大单注入净额
                large_inflow_ratio=self.parse_float(item['f69']),  # 超大单注入净占比
                big_inflow=self.parse_float(item['f72']),  # 大单注入净额
                big_inflow_ratio=self.parse_float(item['f75']),  # 大单注入净占比
                medium_inflow=self.parse_float(item['f78']),  # 中单注入净额
                medium_inflow_ratio=self.parse_float(item['f81']),  # 中单注入净占比
                small_inflow=self.parse_float(item['f84']),  # 小单注入净额
                small_inflow_ratio=self.parse_float(item['f87']),  # 小单注入净占比
                update_timestamp=self.parse_int(item['f124']),  # 时间戳
                main_inflow_ratio=self.parse_float(item['f184']),  # 其他指标
                status_info_1=item.get('f204', ''),  # 其他状态或信息
                status_info_2=item.get('f205', ''),  # 其他状态或信息
                status_info_3=item.get('f206', '')   # 其他状态或信息
            )
            stock_list.append(stock)
        return stock_list

    def parse_float(self, value):
        return float(value) if value != '-' else 0.0

    def parse_int(self, value):
        return int(value) if value != '-' else 0


async def main():
    price_reader = PriceReader()
    data = await price_reader.read()
    stock_data_list = price_reader.parse(data)
    for stock in stock_data_list:
        print(stock)

if __name__ == '__main__':
    asyncio.run(main())
