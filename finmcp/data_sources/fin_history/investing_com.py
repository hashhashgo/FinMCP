from .base import OHLCDataSource, DataType, DataFrequency
from finmcp.databases.history_db import history_cache
import pandas as pd
import sqlite3
from typing import Optional, Callable, Union
from threading import Lock
from datetime import datetime, date

from lxml import etree
import requests
import json
import brotli
from seleniumwire import webdriver
from seleniumwire.request import Request, Response
import pandas as pd
import os

from typing import Optional, Union

class InvestingComDataSource(OHLCDataSource):

    name = "investing.com"

    freq_map = {
        DataFrequency.MINUTE1: 'PT1M',
        DataFrequency.MINUTE5: 'PT5M',
        DataFrequency.MINUTE15: 'PT15M',
        DataFrequency.MINUTE30: 'PT30M',
        DataFrequency.MINUTE60: 'PT1H',
        DataFrequency.MINUTE300: 'PT5H',
        DataFrequency.DAILY: 'P1D',
        DataFrequency.WEEKLY: 'P1W',
        DataFrequency.MONTHLY: 'P1M'
    }
    column_names = ["date", "open", "high", "low", "close", "volume"]


    def __init__(self) -> None:
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:145.0) Gecko/20100101 Firefox/145.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Priority': 'u=0, i',
            'Te': 'trailers'
        }
        self.driver = webdriver.Firefox()
        self.driver.minimize_window()
        self.lock = Lock()
    
    def __del__(self) -> None:
        self.driver.quit()
    

    @history_cache(
        table_basename="investing_com",
        db_path=os.getenv("DB_PATH", ""),
        key_fields=("symbol", "freq"),
        common_fields= ("type",),
        except_fields=(),
    )
    def history(self, symbol: str, type: DataType, start: Union[str, datetime, date, int] = 0, end: Union[str, datetime, date, int] = datetime.now(), freq: DataFrequency = DataFrequency.DAILY) -> pd.DataFrame:
        ic_freq = self._map_frequency(freq)
        if type == DataType.INDEX:
            data = self.load_data(name=symbol, type="indices", freq=ic_freq)
        elif type == DataType.STOCK:
            data = self.load_data(name=symbol, type="equities", freq=ic_freq)
        elif type == DataType.COMMODITY:
            data = self.load_data(name=symbol, type="commodities", freq=ic_freq)
        elif type == DataType.BOND:
            data = self.load_data(name=symbol, type="rates-bonds", freq=ic_freq)
        elif type == DataType.FOREX:
            data = self.load_data(name=symbol, type="currencies", freq=ic_freq)
        elif type == DataType.CRYPTO:
            data = self.load_data(name=symbol, type="currencies", freq=ic_freq)
        else:
            raise NotImplementedError(f"DataType {type} not supported in Investing.com data source")
        start_date = self._parse_datetime(start)
        end_date = self._parse_datetime(end)
        if start_date.time() == datetime.min.time() and end_date.time() == datetime.min.time():
            end_date = end_date + self._datetime_shift_base(freq)
        data = pd.DataFrame(data[(data["date"] >= start_date) & (data["date"] <= end_date)])
        return self._format_dataframe(data)

    def subscribe(self, symbol: str, interval: str, callback: Callable) -> None:
        raise NotImplementedError("Investing.com does not support real-time data subscription")
    
    def unsubscribe(self, symbol: str, interval: str) -> None:
        raise NotImplementedError("Investing.com does not support real-time data unsubscription")


    def driver_get(self, url: str, use_cache: bool = True) -> Response:
        res = None
        if use_cache:
            for request in reversed(self.driver.requests):
                if request.url == url:
                    res = request.response
                    break
        if res is None:
            with self.lock:
                self.driver.get(url)
        for request in reversed(self.driver.requests):
            if request.url == url:
                res = request.response
                break
        if res is None:
            raise ValueError("Could not find the request for the specified URL.")
        if res.headers.get('Content-Encoding') == 'br':
            res.body = brotli.decompress(res.body)
        return res

    def grab_investing_com_html(self, name: str, type: str) -> str:
        url = f"https://www.investing.com/{type}/{name}"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 403:
            print("Access forbidden. You may need to implement human verification to obtain cookies.")
            self.driver.maximize_window()
            res = self.driver_get(url)
            self.driver.minimize_window()
            assert res.status_code == 200, "Failed to retrieve page after human verification."
            return res.body.decode('utf-8')
        response.raise_for_status()
        return response.text

    def get_investing_com_metadata(self, html: str) -> dict:
        tree = etree.HTML(html)
        l_next_data = tree.xpath("//body/script[@id='__NEXT_DATA__']")
        if len(l_next_data) == 0:
            raise ValueError("Could not find __NEXT_DATA__ script tag in the HTML.")
        next_data_json = l_next_data[0].text
        return json.loads(next_data_json)

    def get_investing_com_instrument_id(self, metadata: dict) -> str:
        try:
            instrument_id = metadata['props']['pageProps']['state']['pageInfoStore']['identifiers']['instrument_id']
            return instrument_id
        except KeyError:
            raise ValueError("Instrument ID not found in metadata.")
    
    def load_data(self, name: Optional[str] = None, type: str = "indices", freq: str = "P1D", instrument_id: Optional[Union[str, int]] = None) -> pd.DataFrame:
        if instrument_id is None:
            if name is None:
                raise ValueError("Either 'name' or 'instrument_id' must be provided.")
            try:
                html = self.grab_investing_com_html(name, type)
                metadata = self.get_investing_com_metadata(html)
                instrument_id = self.get_investing_com_instrument_id(metadata)
            except Exception as e:
                raise ValueError(f"Error retrieving instrument ID for index '{name}': {e}")
        else: instrument_id = str(instrument_id)
        url = f"https://api.investing.com/api/financialdata/{instrument_id}/historical/chart/?interval={freq}&pointscount=160"
        res = self.driver_get(url)
        data = json.loads(res.body.decode('utf-8'))
        data = data['data']
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'null'])
        df['date'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
        return pd.DataFrame(df[['date', 'open', 'high', 'low', 'close', 'volume']])
