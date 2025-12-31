from .base import OHLCDataSource, DataType, DataFrequency
from fintools.databases.history_db import history_cache
import pandas as pd
import sqlite3
import os
from typing import Optional, Callable, Union
from datetime import datetime, date, timedelta

import yfinance as yf


class YahooFinanceDataSource(OHLCDataSource):

    name = "yahoo_finance"

    freq_map = {
        DataFrequency.MINUTE1: '1min',
        DataFrequency.MINUTE2: '2min',
        DataFrequency.MINUTE5: '5min',
        DataFrequency.MINUTE15: '15min',
        DataFrequency.MINUTE30: '30min',
        DataFrequency.MINUTE60: '1h',
        DataFrequency.MINUTE90: '90min',
        DataFrequency.DAILY: '1d',
        DataFrequency.DAY5: '5d',
        DataFrequency.WEEKLY: '1wk',
        DataFrequency.MONTHLY: '1mo',
        DataFrequency.MONTH3: '3mo'
    }
    column_names = ["Date", "Open", "High", "Low", "Close", "Volume"]

    @history_cache(
        table_basename=name,
        db_path=os.getenv("DB_PATH", ""),
        key_fields=("symbol", "freq"),
        except_fields=("type",)
    )
    def history(self, symbol: str, type: DataType = DataType.INDEX, start: Union[str, datetime, date, int] = 0, end: Union[str, datetime, date, int] = datetime.now(), freq: DataFrequency = DataFrequency.DAILY) -> pd.DataFrame:
        yf_freq = self._map_frequency(freq)
        start_date = self._parse_datetime(start)
        end_date = self._parse_datetime(end)
        # if start_date.time() == datetime.min.time() and end_date.time() == datetime.min.time():
        #     end_date = end_date + self._datetime_shift_base(freq)
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start_date, end=end_date, interval=yf_freq)
        df.index.name = "date"
        df = df.reset_index()
        return self._format_dataframe(df)


    def subscribe(self, symbol: str, interval: str, callback: Callable) -> None:
        raise NotImplementedError("Yahoo Finance does not support real-time data subscription")

    def unsubscribe(self, symbol: str, interval: str) -> None:
        raise NotImplementedError("Yahoo Finance does not support real-time data unsubscription")