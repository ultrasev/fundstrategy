import httpx
import asyncio
from datetime import datetime
from typing import TypedDict, List, Callable
import json
from abc import ABC, abstractmethod


class FundData(TypedDict):
    FSRQ: str  # Date
    DWJZ: str  # Net Value
    JZZZL: str  # Change Rate


class Investment:
    def __init__(self):
        self.total_units = 0.0  # Total fund units
        self.total_cost = 0.0   # Total investment amount
        self.transactions: List[tuple[str, float, float]] = []


class InvestmentStrategy(ABC):
    @abstractmethod
    def should_invest(self, current_value: float, prev_value: float | None, date_index: int) -> float:
        """Return investment amount if should invest, otherwise 0"""
        pass


async def fetch_fund_data(fund_code: str, page_size: int = 100) -> List[FundData]:
    """Fetch fund historical data using async HTTP request"""
    url = f'https://api.fund.eastmoney.com/f10/lsjz'
    params = {
        'fundCode': fund_code,
        'pageIndex': 1,
        'pageSize': page_size,
    }
    headers = {
        'Referer': 'https://fundf10.eastmoney.com/',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params, headers=headers)
        data = response.json()

        # Add error handling for None data
        if not data or 'Data' not in data or 'LSJZList' not in data['Data']:
            raise ValueError(f"Invalid data format for fund {fund_code}")

        # Convert to list before reversing
        fund_list = list(data['Data']['LSJZList'])
        return list(reversed(fund_list))  # Return from oldest to newest


async def fetch_fund_data_with_retry(fund_code: str, max_retries: int = 3) -> List[FundData]:
    """Fetch fund data with retry mechanism if data seems incomplete"""
    for attempt in range(max_retries):
        try:
            data = await fetch_fund_data(fund_code, page_size=240)
            if not data or len(data) <= 20:  # Check for empty data
                print(
                    f"Attempt {attempt + 1}: Incomplete data for fund {fund_code}, retrying...")
                await asyncio.sleep(2)  # Increased delay between retries
                continue
            return data
        except Exception as e:
            print(f"Error fetching fund {
                  fund_code} (Attempt {attempt + 1}): {str(e)}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2)
            else:
                raise


async def save_fund_data_to_csv(fund_codes: List[str], output_dir: str = "data"):
    """Save historical fund data to CSV files"""
    import os
    import pandas as pd
    from pathlib import Path

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    async def process_fund(fund_code: str):
        try:
            data = await fetch_fund_data_with_retry(fund_code)
            df = pd.DataFrame(data)
            output_path = os.path.join(output_dir, f"{fund_code}.csv")
            df.to_csv(output_path, index=False)
            print(f"Successfully saved data for fund {fund_code}")
        except Exception as e:
            print(f"Failed to process fund {fund_code}: {str(e)}")

    chunk_size = 5
    for i in range(0, len(fund_codes), chunk_size):
        chunk = fund_codes[i:i + chunk_size]
        await asyncio.gather(*(process_fund(code) for code in chunk))
        await asyncio.sleep(1)


if __name__ == "__main__":
    fund_codes = [
        "000411", "000480", "000522", "000534", "000573",
        "000598", "000628", "000746", "001048", "001071",
        "001144", "001167", "001437", "001438", "001513",
        "001564", "001718", "001917", "002152", "002282",
        "002810", "002833", "002849", "002952", "003598",
        "003822", "003823", "004206", "004279", "004280",
        "004496", "004833", "004834", "004845", "005310",
        "005576", "005698", "005970", "005984", "005985",
        "006038", "006160", "006161", "006479", "006675",
        "006676", "006780", "007066", "007509", "007663",
        "007831", "007950", "008269", "008270", "008271",
        "008272", "008298", "008318", "008347", "008348",
        "009069", "009601", "009602", "009707", "009708",
        "010236", "010341", "010342", "011066", "011554",
        "011555", "011570", "011571", "011834", "011835",
        "014002", "017102", "017103", "090007", "090013",
        "090019", "161128", "162102", "163415", "210002",
        "210009", "217021", "257050", "519767"
    ]

    asyncio.run(save_fund_data_to_csv(fund_codes))
