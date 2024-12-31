from abc import ABC, abstractmethod
from typing import List, TypedDict
import httpx
import pandas as pd
import os

class FundData(TypedDict):
    FSRQ: str  # Date
    DWJZ: str  # Net Value
    JZZZL: str  # Change Rate

class FundDataSource(ABC):
    """Abstract base class for fund data sources"""
    @abstractmethod
    async def get_fund_data(self, identifier: str) -> List[FundData]:
        """Get fund data from source

        Args:
            identifier: Fund code for API, file path for CSV
        Returns:
            List of fund data entries
        """
        pass

class APIDataSource(FundDataSource):
    """Fetch fund data from East Money API"""
    async def get_fund_data(self, fund_code: str, page_size: int = 100) -> List[FundData]:
        url = 'https://api.fund.eastmoney.com/f10/lsjz'
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
            # Return from oldest to newest
            return list(reversed(data['Data']['LSJZList']))

class CSVDataSource(FundDataSource):
    """Load fund data from CSV files"""
    async def get_fund_data(self, file_path: str) -> List[FundData]:
        df = pd.read_csv(file_path)
        fund_data: List[FundData] = []

        for _, row in df.iterrows():
            fund_data.append({
                'FSRQ': row['FSRQ'],
                'DWJZ': str(row['DWJZ']),
                'JZZZL': str(row['JZZZL'])
            })

        return fund_data

class DataSourceFactory:
    """Factory for creating data sources"""
    @staticmethod
    def create_source(source_type: str) -> FundDataSource:
        if source_type == "api":
            return APIDataSource()
        elif source_type == "csv":
            return CSVDataSource()
        else:
            raise ValueError(f"Unknown data source type: {source_type}")