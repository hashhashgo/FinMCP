from pyparsing import ABC
from typing import Optional, Union
from enum import Enum
from datetime import datetime, date, timedelta, timezone

from fintools.utils.types import parse_datetime

class UnderlyingType(Enum):
    STOCK = 'stock'
    INDEX = 'index'
    BOND = 'bond'
    FUND = 'fund'
    FOREX = 'forex'
    COMMODITY = 'commodity'
    CRYPTO = 'crypto'
    UNKNOWN = 'unknown'

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
    YEARLY = 'yearly'


class DataSource(ABC):

    name: str = "base"
    token: Optional[Union[str, dict]] = None


    def _parse_datetime(self, datetime_input: Union[str, datetime, date, int]) -> datetime:
        return parse_datetime(datetime_input)
    
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