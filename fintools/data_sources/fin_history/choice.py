from contextlib import contextmanager
from .base import OHLCDataSource, UnderlyingType, DataFrequency
from fintools.databases.history_db import history_cache
import pandas as pd
import os
from typing import Optional, Callable, Union, Any
from datetime import datetime, date, timedelta
from threading import Lock, Timer

import importlib

class ChoiceDataSource(OHLCDataSource):

    name = "choice"
    choice: Any  # Placeholder for EmQuantAPI module
    choice_running: bool = False
    lock: Lock
    release_timer: Timer

    freq_map = {
        DataFrequency.DAILY: '1',
        DataFrequency.WEEKLY: '2',
        DataFrequency.MONTHLY: '3',
        DataFrequency.YEARLY: '4',
    }
    column_names = ["DATES", "OPEN", "HIGH", "LOW", "CLOSE", "VOLUME"]

    def __init__(self):
        super().__init__()

    @history_cache(
        table_basename=name,
        db_path=os.getenv("FINTOOLS_DB", ""),
        key_fields=("symbol", "freq"),
        except_fields=("type",)
    )
    def history(self, symbol: str, type: UnderlyingType = UnderlyingType.UNKNOWN, start: Union[str, datetime, date, int] = 0, end: Union[str, datetime, date, int] = datetime.now(), freq: DataFrequency = DataFrequency.DAILY) -> pd.DataFrame:
        yf_freq = self._map_frequency(freq)
        start_date = self._parse_datetime(start)
        end_date = self._parse_datetime(end)
        with self.borrow_choice(timeout=30) as choice:
            data = choice.csd(symbol, "OPEN,CLOSE,HIGH,LOW,VOLUME", start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"), f"period={yf_freq},adjustflag=1,curtype=1,order=1,Ispandas=1")
        if isinstance(data, choice.EmQuantData) and data.ErrorCode != 0:
            raise ValueError(f"Error fetching data from Choice API: {data.ErrorMsg}")
        if not isinstance(data, pd.DataFrame):
            raise ValueError("Unexpected data format received from Choice API")
        df = data.reset_index()
        df['DATES'] = pd.to_datetime(df['DATES']).dt.tz_localize("Asia/Shanghai")
        return self._format_dataframe(df)

    @classmethod
    def _release(cls):
        if hasattr(cls, 'choice'):
            cls.choice.stop()
            cls.choice_running = False
            if cls.lock.locked(): cls.lock.release()
            cls.release_timer.cancel()
        
    @classmethod
    @contextmanager
    def borrow_choice(cls, timeout: float = -1, release_after: float = 5.0):
        try:
            if not hasattr(cls, 'choice'):
                cls.choice = importlib.import_module("EmQuantAPI").c
                cls.lock = Lock()
        except (ModuleNotFoundError, AttributeError) as e:
            raise ImportError("EmQuantAPI module is not installed. Please install it to use ChoiceDataSource.") from e

        if not cls.choice_running:
            cls.choice_running = True
            cls.choice.start(f"ForceLogin=1,UserName={os.getenv('CHOICE_USERNAME','')},Password={os.getenv('CHOICE_PASSWORD','')}")
        if hasattr(cls, 'release_timer'):
            cls.release_timer.cancel()
        
        try:
            if cls.lock.acquire(timeout=timeout):
                yield cls.choice
            else:
                raise TimeoutError("Timeout while waiting to acquire Choice API lock")
        except TimeoutError as e:
            raise e
        finally:
            cls.lock.release()
            cls.release_timer = Timer(release_after, cls._release)
            cls.release_timer.start()

    def subscribe(self, symbol: str, interval: str, callback: Callable) -> None:
        raise NotImplementedError("Yahoo Finance does not support real-time data subscription")

    def unsubscribe(self, symbol: str, interval: str) -> None:
        raise NotImplementedError("Yahoo Finance does not support real-time data unsubscription")