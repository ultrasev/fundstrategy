from abc import ABC, abstractmethod
import asyncio
import httpx
import json
from pydantic import BaseModel
from typing import AsyncGenerator


class StockInfo(BaseModel):
    code: str
    name: str
    price: float
    change: float
    percent: float
    main_inflow: float  # 主力流入
    super_inflow_ratio: float  # 超大单占比
    big_inflow_ratio: float  # 大单占比
    middle_inflow_ratio: float  # 中单占比
    small_inflow_ratio: float  # 小单占比

    def __str__(self) -> str:
        return str({
            'code': self.code,
            'name': self.name,
            'price': self.price,
            'change': self.change,
            'percent': self.percent,
            'main_inflow': self.main_inflow,
            'super_inflow_ratio': self.super_inflow_ratio,
            'big_inflow_ratio': self.big_inflow_ratio,
            'middle_inflow_ratio': self.middle_inflow_ratio,
            'small_inflow_ratio': self.small_inflow_ratio,
        })


class AbstractReader(ABC):
    @abstractmethod
    def read(self, data: dict) -> list[StockInfo]:
        pass


class AbstractMonitor(ABC):
    @abstractmethod
    async def monitor(self):
        pass


class Configs:
    class SelfSelect:
        url = "https://55.push2.eastmoney.com/api/qt/ulist/get"
        params = {
            "cb": "jQuery37102835985679119035_1741675059897",
            "secids": "0.002714,0.002271,0.002155,1.603351,1.603678,0.002195,0.002922,1.603081,1.603993,0.002456,0.000921,0.002428,0.002484,1.600602,1.603036,1.603887,0.002261,1.603728,1.603009,0.002843,0.000099,1.688568,1.688522,0.001696,1.603369,0.000063,1.600027,0.002065,0.002036,118.AUTD,0.002031,1.601058,1.601231,1.600131,1.601900,1.603198,1.600916,0.002475,1.600988,0.002253,1.603667,1.603809,0.002896,0.002851,0.002415,1.603596,0.002281,1.601689,1.601138,0.002130,0.002938,0.002384,0.002050,0.002273,0.002463,0.002245,0.000977,0.002837,0.002765,0.000680,1.603179",
            "fields": "f12,f13,f14,f19,f139,f148,f2,f4,f1,f125,f18,f3,f152,f62,f63,f69,f75,f81,f87",
            "invt": "3",
            "fid": "f62",
            "po": "1",
            "pi": "0",
            "pz": "61",
            "dect": "1",
            "_": "1741675059903"
        }
        headers = {
            "sec-ch-ua-platform": "macOS",
            "Referer": "https://quote.eastmoney.com/zixuan/lite.html",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
            "sec-ch-ua": "\"Not(A:Brand\";v=\"99\", \"Google Chrome\";v=\"133\", \"Chromium\";v=\"133\"",
            "DNT": "1",
            "sec-ch-ua-mobile": "?0"
        }


class SelfSelectReader(AbstractReader):
    async def crawl(self) -> dict:
        c = Configs.SelfSelect
        async with httpx.AsyncClient() as client:
            response = await client.get(c.url,
                                        params=c.params,
                                        headers=c.headers)
            text = response.text
            start = text.find('(') + 1
            end = text.rfind(')')
            json_data = text[start:end]
            data = json.loads(json_data)
            return data

    async def read(self) -> AsyncGenerator[StockInfo, None]:
        data = await self.crawl()
        for x in data['data']['diff'].values():
            if x['f12'] == 'AUTD':
                continue
            info = StockInfo(
                code=x['f12'],
                name=x['f14'],
                price=x['f2']/100,
                change=x['f4']/100,
                percent=x['f3']/100,
                main_inflow=x['f62'],
                super_inflow_ratio=x['f69']/100,
                big_inflow_ratio=x['f75']/100,
                middle_inflow_ratio=x['f81']/100,
                small_inflow_ratio=x['f87']/100,
            )
            yield info


class HoldingMonitor(AbstractMonitor):
    def __init__(self, reader: AbstractReader, codes: list[str]):
        self.reader = reader
        self.codes = codes

    async def monitor(self):
        async for info in self.reader.read():
            if info.code in self.codes:
                print(info)


STOCKS = [
    #  {'code': '603993', 'name': '洛阳钼业'},
    {'code': '000680', 'name': '山推股份'},
    {'code': '002384', 'name': '东山精密'},
    {'code': '603887', 'name': '城地香江'}]


async def main():
    reader = SelfSelectReader()
    codes = [x['code'] for x in STOCKS]
    monitor = HoldingMonitor(reader, codes)
    await monitor.monitor()

if __name__ == "__main__":
    asyncio.run(main())
