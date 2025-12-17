from abc import ABC, abstractmethod
import sqlite3
import numpy as np
import pandas as pd
from typing import Literal, Callable, Optional, Union
from enum import Enum
from datetime import datetime, date, timedelta

STANDARD_COLUMN_NAMES = ["date", "open", "high", "low", "close", "volume"]

class DataType(Enum):
    STOCK = 'stock'
    INDEX = 'index'
    COMMODITY = 'commodity'
    BOND = 'bond'
    FOREX = 'forex'
    CRYPTO = 'crypto'

class DataFrequency(Enum):
    MINUTE1 = 'minute1'
    MINUTE2 = 'minute2'
    MINUTE5 = 'minute5'
    MINUTE15 = 'minute15'
    MINUTE30 = 'minute30'
    MINUTE60 = 'minute60'
    MINUTE90 = 'minute90'
    MINUTE120 = 'minute120'
    MINUTE240 = 'minute240'
    MINUTE300 = 'minute300'
    DAILY = 'daily'
    DAY5 = 'day5'
    WEEKLY = 'weekly'
    MONTHLY = 'monthly'
    MONTH3 = 'month3'


class DataSource(ABC):

    name: str = "base"
    subscribed_symbols: dict = {}
    cache_conn: Optional[sqlite3.Connection] = None
    token: Optional[Union[str, dict]] = None
    column_names: list = STANDARD_COLUMN_NAMES
    freq_map: dict

    @abstractmethod
    def history(
        self,
        symbol: str,
        type: DataType,
        start: Union[str, datetime, date, int] = 0,
        end: Union[str, datetime, date, int] = datetime.now(),
        freq: DataFrequency = DataFrequency.DAILY
    ) -> pd.DataFrame:
        raise NotImplementedError("Subclasses must implement this method")
    
    @abstractmethod
    def subscribe(self, symbol: str, interval: str, callback: Callable) -> None:
        raise NotImplementedError("Subclasses must implement this method")
    
    @abstractmethod
    def unsubscribe(self, symbol: str, interval: str) -> None:
        raise NotImplementedError("Subclasses must implement this method")
    
    
    def _parse_datetime(self, datetime_input: Union[str, datetime, date, int]) -> datetime:
        if isinstance(datetime_input, date):
            return datetime(datetime_input.year, datetime_input.month, datetime_input.day)
        elif isinstance(datetime_input, datetime):
            return datetime_input
        elif isinstance(datetime_input, int):
            if datetime_input > 9999999999: datetime_input = datetime_input // 1000
            return datetime.fromtimestamp(datetime_input).astimezone()
        elif isinstance(datetime_input, str):
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y%m%d%H%M%S", "%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
                try:
                    return datetime.strptime(datetime_input, fmt).astimezone()
                except ValueError:
                    continue
            raise ValueError(f"String datetime format not recognized: {datetime_input}")
        else:
            raise TypeError(f"Unsupported datetime input type: {type(datetime_input)}")
    
    def _parse_date(self, date_input: Union[str, datetime, date, int]) -> date:
        dt = self._parse_datetime(date_input)
        return dt.date()

    def _datetime_shift_base(self, freq: DataFrequency) -> timedelta:
        if freq == DataFrequency.MINUTE1:
            return timedelta(minutes=1)
        elif freq == DataFrequency.MINUTE2:
            return timedelta(minutes=2)
        elif freq == DataFrequency.MINUTE5:
            return timedelta(minutes=5)
        elif freq == DataFrequency.MINUTE15:
            return timedelta(minutes=15)
        elif freq == DataFrequency.MINUTE30:
            return timedelta(minutes=30)
        elif freq == DataFrequency.MINUTE60:
            return timedelta(minutes=60)
        elif freq == DataFrequency.MINUTE90:
            return timedelta(minutes=90)
        elif freq == DataFrequency.MINUTE120:
            return timedelta(minutes=120)
        elif freq == DataFrequency.MINUTE240:
            return timedelta(minutes=240)
        elif freq == DataFrequency.MINUTE300:
            return timedelta(minutes=300)
        elif freq == DataFrequency.DAILY:
            return timedelta(days=1)
        elif freq == DataFrequency.DAY5:
            return timedelta(days=5)
        elif freq == DataFrequency.WEEKLY:
            return timedelta(weeks=1)
        elif freq == DataFrequency.MONTHLY:
            return timedelta(days=30)
        elif freq == DataFrequency.MONTH3:
            return timedelta(days=90)
        else:
            raise NotImplementedError(f"Frequency {freq} not supported for datetime shift")
    
    def _format_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        for custom, standard in zip(self.__class__.column_names, STANDARD_COLUMN_NAMES):
            if custom is None:
                df[standard] = np.nan
            df = df.rename(columns={custom: standard})
        df['date'] = pd.to_datetime(df['date'])
        return df
    
    def _map_frequency(self, freq: DataFrequency) -> str:
        if freq in self.__class__.freq_map:
            return self.__class__.freq_map[freq]
        else:
            raise NotImplementedError(f"Frequency {freq} not supported in {self.__class__.__name__}")