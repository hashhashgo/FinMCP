from .base import OHLCDataSource, UnderlyingType, DataFrequency
from fintools.databases.history_db import history_cache
import pandas as pd
import sqlite3
from typing import Optional, Callable, Union
from threading import Lock
from datetime import datetime, date

from lxml import etree
import requests
import json
from playwright.sync_api import sync_playwright, Response
import pandas as pd
import os
import logging
logger = logging.getLogger(__name__)

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
        self._playwright = sync_playwright().start()
        self.browser = self._playwright.firefox.launch(headless=True)
        self.lock = Lock()
    
    def __del__(self) -> None:
        self.browser.close()
        self._playwright.stop()
    
    @history_cache(
        table_basename="investing_com",
        db_path=os.getenv("FINTOOLS_DB", ""),
        key_fields=("symbol", "freq"),
        common_fields= ("type",),
        except_fields=(),
    )
    def history(self, symbol: str, type: UnderlyingType, start: Union[str, datetime, date, int] = 0, end: Union[str, datetime, date, int] = datetime.now(), freq: DataFrequency = DataFrequency.DAILY) -> pd.DataFrame:
        ic_freq = self._map_frequency(freq)
        if type == UnderlyingType.INDEX:
            data = self.load_data(name=symbol, type="indices", freq=ic_freq)
        elif type == UnderlyingType.STOCK:
            data = self.load_data(name=symbol, type="equities", freq=ic_freq)
        elif type == UnderlyingType.COMMODITY:
            data = self.load_data(name=symbol, type="commodities", freq=ic_freq)
        elif type == UnderlyingType.BOND:
            data = self.load_data(name=symbol, type="rates-bonds", freq=ic_freq)
        elif type == UnderlyingType.FOREX:
            data = self.load_data(name=symbol, type="currencies", freq=ic_freq)
        elif type == UnderlyingType.CRYPTO:
            data = self.load_data(name=symbol, type="currencies", freq=ic_freq)
        else:
            raise NotImplementedError(f"UnderlyingType {type} not supported in Investing.com data source")
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

    def _route_handler(self, route):
        req = route.request

        # 只允许主文档（index.html）
        if req.resource_type == "document":
            route.continue_()
        else:
            route.abort()

    def driver_get(self, url: str) -> bytes:
        with self.lock:
            page = self.browser.new_page()
            page.route("**/*", self._route_handler)
            res = page.goto(url, wait_until="networkidle")
            if res is None:
                raise ValueError(f"Failed to load URL: {url}")
            body = res.body()
            page.close()
            return body

    def grab_investing_com_html(self, name: str, type: str) -> str:
        url = f"https://www.investing.com/{type}/{name}"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 403:
            logger.warning("Access forbidden. You may need to implement human verification to obtain cookies.")
            res = self.driver_get(url)
            return res.decode('utf-8')
        else:
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
        data = json.loads(res.decode('utf-8'))
        data = data['data']
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'null'])
        df['date'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
        return pd.DataFrame(df[['date', 'open', 'high', 'low', 'close', 'volume']])
