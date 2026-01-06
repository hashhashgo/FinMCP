from abc import ABC, abstractmethod
import sqlite3
import numpy as np
import pandas as pd
from typing import Literal, Callable, Optional, Union
from enum import Enum
from datetime import datetime, date, timedelta

from .. import DataSource, DataFrequency, UnderlyingType

STANDARD_COLUMN_NAMES = ["date", "open", "high", "low", "close", "volume"]


class OHLCDataSource(DataSource, ABC):

    subscribed_symbols: dict = {}
    column_names: list = STANDARD_COLUMN_NAMES
    freq_map: dict

    @abstractmethod
    def history(
        self,
        symbol: str,
        type: UnderlyingType,
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