from .base import DataSource, DataType, DataFrequency
import pandas as pd
import sqlite3
from typing import Optional, Callable, Union
from datetime import datetime, date, timedelta

import requests

class NanHuaDataSource(DataSource):

    name = "nanhua"

    freq_map = {
        DataFrequency.MINUTE1: 'MIN1',
        DataFrequency.MINUTE5: 'MIN5',
        DataFrequency.MINUTE15: 'MIN15',
        DataFrequency.MINUTE30: 'MIN30',
        DataFrequency.MINUTE60: 'MIN60',
        DataFrequency.MINUTE120: 'MIN120',
        DataFrequency.MINUTE240: 'MIN240',
        DataFrequency.DAILY: 'DAY1',
        DataFrequency.WEEKLY: 'WEEK1',
        DataFrequency.MONTHLY: 'MONTH1'
    }
    column_names = ["date", "open", "high", "low", "close", "volume"]


    def __init__(self, token: Optional[str] = None, cache_file: Optional[str] = None):
        if cache_file is not None: self.__class__.cache_conn = sqlite3.connect(cache_file)


    def history(self, symbol: str, type: DataType, start: Union[str, datetime, date, int] = 0, end: Union[str, datetime, date, int] = datetime.now(), freq: DataFrequency = DataFrequency.DAILY) -> pd.DataFrame:
        assert type == DataType.COMMODITY, "NanHuaDataSource only supports commodity data"
        nh_freq = self._map_frequency(freq)
        data_raw = requests.get(f'http://localhost:13200/?ticker={symbol}&freq={nh_freq}').json()
        df = pd.DataFrame(data_raw)
        df["date"] = pd.to_datetime(df['quoteTime'], unit='ms')
        start_date = self._parse_datetime(start)
        end_date = self._parse_datetime(end)
        if start_date.time() == datetime.min.time() and end_date.time() == datetime.min.time():
            end_date = end_date + self._datetime_shift_base(freq)
        df = pd.DataFrame(df[(df["date"] >= start_date) & (df["date"] <= end_date)])
        return self._format_dataframe(df)


    def subscribe(self, symbol: str, interval: str, callback: Callable) -> None:
        raise NotImplementedError("Yahoo Finance does not support real-time data subscription")

    def unsubscribe(self, symbol: str, interval: str) -> None:
        raise NotImplementedError("Yahoo Finance does not support real-time data unsubscription")
