from app.services.comparison.profit import profits
from app.services.comparison.frequency import analyze_frequencies

import asyncio

if __name__ == "__main__":
    asyncio.run(analyze_frequencies())
