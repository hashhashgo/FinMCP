from datetime import datetime, date, timezone
import os
from dateutil import parser
from typing import Annotated, Dict, Literal, TypedDict
from openai import api_key
import requests
import pandas as pd
import json
import tushare
from tushare.pro.client import DataApi

def _parse_datetime(datetime_input: str | datetime | date | int) -> datetime:
    datetime_output = None
    if isinstance(datetime_input, datetime):
        datetime_output = datetime_input
    elif isinstance(datetime_input, date):
        datetime_output = datetime(datetime_input.year, datetime_input.month, datetime_input.day)
    elif isinstance(datetime_input, int): # us or s timestamp
        if datetime_input > 9999999999999: datetime_input = datetime_input // 1000000
        datetime_output = datetime.fromtimestamp(datetime_input, tz=timezone.utc)
    elif isinstance(datetime_input, str):
        try:
            datetime_output = parser.isoparse(datetime_input)
        except Exception:
            pass
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y%m%d%H%M%S", "%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
            try:
                datetime_output = datetime.strptime(datetime_input, fmt)
                break
            except ValueError:
                continue
    else:
        raise TypeError(f"Unsupported datetime input type: {type(datetime_input)}")
    if not isinstance(datetime_output, datetime): raise ValueError(f"String datetime format not recognized: {datetime_input}")
    return datetime_output.astimezone()

_pro: DataApi | None = None
def pro(api_key: str = os.getenv("TUSHARE_API_KEY", "")) -> DataApi:
    global _pro
    if not _pro:
        _pro = tushare.pro_api(api_key)
    return _pro

_index_basic = None
def index_basic() -> pd.DataFrame:
    """
    Get basic information of all indexes.

    Returns:
    A DataFrame containing index basic information.
    """
    global _index_basic
    if _index_basic is not None:
        return _index_basic
    df = pro().index_basic()
    _index_basic = df
    return df

_stock_basic = None
def stock_basic() -> pd.DataFrame:
    """
    Get basic information of all stocks.

    Returns:
    A DataFrame containing stock basic information.
    """
    global _stock_basic
    if _stock_basic is not None:
        return _stock_basic
    df = pro().stock_basic(list_status='L')
    _stock_basic = df
    return df

class SYMBOL_SEARCH_RESULT(TypedDict):
    type: Literal['stock', 'index', 'etf']
    symbol: str
    name: str

_symbol_search_cache: Dict[str, SYMBOL_SEARCH_RESULT | None] = {}
def symbol_search(
    keyword: Annotated[str, "The symbol code or name to search for."] = ""
) -> SYMBOL_SEARCH_RESULT | None:
    raise NotImplementedError
    assert keyword, "Either symbol or name must be provided."
    global _symbol_search_cache
    if keyword in _symbol_search_cache:
        return _symbol_search_cache[keyword]
    
    ret = None
    # Try to search in stocks
    if keyword and keyword in stock_basic()['symbol'].values:
        res = stock_basic()[stock_basic()['symbol'] == keyword].iloc[0]
        ret = {'type': 'stock', 'symbol': res['ts_code'], 'name': res['name']}
    elif keyword and keyword in stock_basic()['ts_code'].values:
        res = stock_basic()[stock_basic()['ts_code'] == keyword].iloc[0]
        ret = {'type': 'stock', 'symbol': res['ts_code'], 'name': res['name']}
    elif keyword and keyword in stock_basic()['name'].values:
        res = stock_basic()[stock_basic()['name'] == keyword].iloc[0]
        ret = {'type': 'stock', 'symbol': res['ts_code'], 'name': keyword}
    
    # Try to search in indexes
    if keyword and keyword in index_basic()['ts_code'].values:
        res = index_basic()[index_basic()['ts_code'] == keyword].iloc[0]
        ret = {'type': 'index', 'symbol': keyword, 'name': res['name']}
    elif keyword and keyword in index_basic()['name'].values:
        res = index_basic()[index_basic()['name'] == keyword].iloc[0]
        ret = {'type': 'index', 'symbol': res['ts_code'], 'name': keyword}
    
    # Try to fetch eastmoney
    if not ret:
        try:
            req = requests.get(f"https://search-codetable.eastmoney.com/codetable/search/web?client=web&clientType=webSuggest&clientVersion=lastest&cb=jQuery35102584463847576248_1767928521853&keyword={keyword}&pageIndex=1&pageSize=10&securityFilter=&_=1767928521870")
            s = req.text
            s = s[s.index('(')+1: s.rindex(')')]
            data = json.loads(s)
            for info in data['result']:
                type_name = info['securityTypeName']
                if type_name == "基金":
                    name = info['shortName']
                    code = info['code']
                    if len(get_data("tushare", f"{code}.SH", UnderlyingType.ETF)):
                        ret = {'type': 'etf', 'symbol': f"{code}.SH", 'name': name}
                    elif len(get_data("tushare", f"{code}.SZ", UnderlyingType.ETF)):
                        ret = {'type': 'etf', 'symbol': f"{code}.SZ", 'name': name}
        except Exception as e:
            logger.debug(f"Failed to fetch symbol info from eastmoney for keyword {keyword}: {e}")

    if ret:
        _symbol_search_cache[keyword] = {
            'type': ret['type'],
            'symbol': ret['symbol'],
            'name': ret['name']
        }
    else:
        _symbol_search_cache[keyword] = None
    return _symbol_search_cache[keyword]

__all__ = ["_parse_datetime"]
