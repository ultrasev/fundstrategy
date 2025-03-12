import asyncio
from app.data.fetch import fetch_fund_data


async def main():
    fund_data = await fetch_fund_data("000522", 100)
    print(fund_data)
    print(len(fund_data))

if __name__ == "__main__":
    asyncio.run(main())
