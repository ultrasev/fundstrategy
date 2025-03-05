from pydantic import BaseModel
import httpx
import json
import os


class BaseReader:
    def __init__(self, code):
        self.code = code
        self._path = f'data/stocks/{code}.json'

    def read(self):
        pass


class KlimeItem(BaseModel):
    date: str
    open: float
    close: float
    high: float
    low: float
    volume: int          # Trading volume
    amount: float        # Trading amount
    amplitude: float     # Price amplitude percentage
    change_percent: float  # Price change percentage
    change_amount: float   # Price change amount
    turnover_rate: float   # Turnover rate percentage


class Kline(BaseModel):
    code: str
    market: int
    name: str
    decimal: int
    dktotal: int
    preKPrice: float
    klines: list[KlimeItem]

    @classmethod
    def process_klines(cls, data):
        """Process klines data by splitting strings into lists"""
        x = data.copy()
        if isinstance(data['klines'], list):
            x['klines'] = [
                KlimeItem(
                    date=parts[0],
                    open=float(parts[1]),
                    close=float(parts[2]),
                    high=float(parts[3]),
                    low=float(parts[4]),
                    volume=int(parts[5]),
                    amount=float(parts[6]),
                    amplitude=float(parts[7]),
                    change_percent=float(parts[8]),
                    change_amount=float(parts[9]),
                    turnover_rate=float(parts[10])
                ) if isinstance(kline, str) and (parts := kline.split(',')) else kline
                for kline in data['klines']
            ]
        return x

    def __init__(self, **data):
        x = self.process_klines(data)
        super().__init__(**x)


class KlineReader(BaseReader):
    def read(self):
        """
            Load stock data from EastMoney API using httpx

        Args:
            code: stock code, e.g. '000001' for Ping An Bank

        Returns:
            dict: JSON response containing stock data
        """
        # Check if file exists - if yes, read from file
        if os.path.exists(self._path):
            with open(self._path, 'r') as f:
                data = json.load(f)
                return Kline(**data['data'])

        # If file doesn't exist, fetch from API
        url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
        params = {
            # 0 for SZ, 1 for SH
            "secid": "0.{}".format(self.code) if self.code.startswith("00") else "1.{}".format(self.code),
            "ut": "fa5fd1943c7b386f172d6893dbfba10b",
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
            "klt": "101",  # Daily K-line
            "fqt": "1",    # Forward adjustment
            "end": "20250305",
            "lmt": "210",  # Limit to 210 records
            "cb": "quote_jp5"  # Callback parameter required by API
        }

        with httpx.Client(timeout=10.0) as client:
            response = client.get(url, params=params)
            jsonp = response.text
            json_str = jsonp[jsonp.index("(")+1:jsonp.rindex(")")]
            data = json.loads(json_str)
            with open(self._path, 'w') as f:
                json.dump(data, f)
            return Kline(**data['data'])


if __name__ == "__main__":
    reader = KlineReader("002154")
    data = reader.read()
    print(data)
