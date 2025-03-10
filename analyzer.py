import duckdb
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

class StockAnalyzer:
    def __init__(self):
        self.conn = duckdb.connect('stocks.duckdb')
