import httpx
import json
import os


class BaseReader:
    def __init__(self, code):
        self.code = code
        self._path = f'data/stocks/{code}.json'

    def read(self):
        pass


class KlineReader(BaseReader):
    def __init__(self, code):
        super().__init__(code)

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
                return json.load(f)

        # If file doesn't exist, fetch from API
        url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
        params = {
            "secid": "0.{}".format(self.code),  # 0 for SZ, 1 for SH
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
            return data


if __name__ == "__main__":
    reader = KlineReader("000001")
    data = reader.read()
    print(data)
