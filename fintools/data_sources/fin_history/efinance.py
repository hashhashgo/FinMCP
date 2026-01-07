from .base import OHLCDataSource, UnderlyingType, DataFrequency
from fintools.databases.history_db import history_cache
import pandas as pd
import os
from typing import Optional, Callable, Union
from datetime import datetime, date, timedelta

import efinance as ef


class EFinanceDataSource(OHLCDataSource):

    name = "efinance"

    freq_map = {
        DataFrequency.MINUTE1: '1',
        DataFrequency.MINUTE5: '5',
        DataFrequency.MINUTE15: '15',
        DataFrequency.MINUTE30: '30',
        DataFrequency.MINUTE60: '60',
        DataFrequency.DAILY: '101',
        DataFrequency.WEEKLY: '102',
        DataFrequency.MONTHLY: '103',
    }
    column_names = ["date", "开盘", "最高", "最低", "收盘", "成交量"]

    @history_cache(
        table_basename=name,
        db_path=os.getenv("FINTOOLS_DB", ""),
        key_fields=("symbol", "freq"),
        except_fields=("type",)
    )
    def history(self, symbol: str, type: UnderlyingType = UnderlyingType.INDEX, start: Union[str, datetime, date, int] = 0, end: Union[str, datetime, date, int] = datetime.now(), freq: DataFrequency = DataFrequency.DAILY) -> pd.DataFrame:
        ef_freq = int(self._map_frequency(freq))
        start_date = self._parse_datetime(start)
        end_date = self._parse_datetime(end)
        if type in [UnderlyingType.STOCK, UnderlyingType.ETF, UnderlyingType.INDEX]:
            # if start_date.time() == datetime.min.time() and end_date.time() == datetime.min.time():
            #     end_date = end_date + self._datetime_shift_base(freq)
            df = ef.stock.get_quote_history(symbol, klt=ef_freq)
        elif type == UnderlyingType.COMMODITY:
            df = ef.futures.get_quote_history(symbol, klt=ef_freq)
        elif type == UnderlyingType.BOND:
            df = ef.bond.get_quote_history(symbol, klt=ef_freq)
        else:
            raise ValueError(f"Unsupported UnderlyingType: {type}")
        assert isinstance(df, pd.DataFrame)
        df['date'] = pd.to_datetime(df['日期']).dt.tz_localize('Asia/Shanghai')
        df.drop(columns=['日期'], inplace=True)
        df = df[(df['date'] >= start_date) & (df['date'] < end_date)]
        return self._format_dataframe(df)


    def subscribe(self, symbol: str, interval: str, callback: Callable) -> None:
        raise NotImplementedError("Yahoo Finance does not support real-time data subscription")

    def unsubscribe(self, symbol: str, interval: str) -> None:
        raise NotImplementedError("Yahoo Finance does not support real-time data unsubscription")