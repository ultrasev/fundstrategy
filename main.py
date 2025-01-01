from app.services.comparison.profit import profits
from app.services.comparison.frequency import analyze_frequencies
from app.services.comparison.rsi_analysis import analyze_rsi_thresholds

import asyncio

if __name__ == "__main__":
    asyncio.run(analyze_rsi_thresholds())
