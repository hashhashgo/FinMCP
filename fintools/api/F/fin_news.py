from typing import Dict, Annotated

from datetime import datetime, date
import pandas as pd
import tzlocal
import os

import logging

logger = logging.getLogger(__name__)

from fintools.data_sources.fin_news import DATASOURCES, NewsDataSource
from fintools.databases.common_db import DB_CONNECTIONS

datasources: Dict[str, NewsDataSource] = {}

def list_news(
    datasource: Annotated[str, "data source, selected from: " + ", ".join(DATASOURCES.keys())],
    symbol: Annotated[str, "any keywords to search for news articles"],
    start: Annotated[str | datetime | date | int, "start time, supports str: YYYY-MM-DD / YYYY-MM-DD HH:MM:SS | datetime | date | int (timestamp)"] = 0,
    end: Annotated[str | datetime | date | int, "end time, supports str: YYYY-MM-DD / YYYY-MM-DD HH:MM:SS | datetime | date | int (timestamp)"] = datetime.now(),
) -> pd.DataFrame:
    """
    Search for news articles related to a given symbol from specified data source.

    Parameters:
    - datasource: str, Data source
    - symbol: str, Keywords to search for news articles.
    - start: str | datetime | date | int, start time
    - end: str | datetime | date | int, end time

    Time range is [start, end), i.e., start is inclusive, end is exclusive.
    So if you want news up to and including 2025-01-01, please set end to 2025-01-02.

    Returns: news DataFrame, containing news articles with at least the following fields:
    - date: str, Publication date of the news article
    - code: str, Unique identifier of the news article
    - title: str, Title of the news article
    - content: str, Content of the news article
    """
    if datasource not in DATASOURCES:
        raise ValueError(f"Unknown datasource: {datasource}\n\nSupported datasources: {' / '.join(DATASOURCES.keys())}")

    if datasource not in datasources:
        datasources[datasource] = DATASOURCES[datasource]()
    ds = datasources[datasource]

    logger.info(f"Fetching news: datasource={datasource}, symbol={symbol}, start={start}, end={end}")

    df: pd.DataFrame = ds.list_news(
        symbol=symbol,
        start=start,
        end=end
    )

    logger.debug("News data fetched:")
    logger.debug(df)

    if df.empty:
        return pd.DataFrame(columns=['date', 'code', 'title', 'content'])

    df['date'] = pd.to_datetime(df['date']).dt.tz_convert(tzlocal.get_localzone()).dt.strftime("%Y-%m-%d %H:%M:%S")

    return df

def news_details(
    datasource: Annotated[str, "data source, selected from: " + ", ".join(DATASOURCES.keys())],
    code: Annotated[str, "unique identifier of the news article"]
) -> str:
    """
    Get detailed information about a news article given its unique code.
    Parameters:
    - datasource: str, Data source
    - code: str, Unique identifier of the news article.

    Returns: str, detailed content of the news article.
    """
    logger.info(f"Fetching news details for code: {code}")
    if datasource not in DATASOURCES:
        raise ValueError(f"Unknown datasource: {datasource}\n\nSupported datasources: {' / '.join(DATASOURCES.keys())}")
    if datasource not in datasources:
        datasources[datasource] = DATASOURCES[datasource]()
    ds = datasources[datasource]
    
    news = ds.news_details(code=code)

    return news

def db_cached_news_details(codes: list[str]) -> pd.DataFrame:
    ret = pd.DataFrame(columns=['code', 'content'])
    if not os.getenv("FINTOOLS_DB"): return ret
    if len(DATASOURCES) == 0: return ret
    rows = []
    for key, db in DB_CONNECTIONS.items():
        module, function = key.split(":")
        if not module.startswith("fintools.data_sources.fin_news"): continue
        if not function.endswith("news_details"): continue
        rows.extend(db.select_by_primary_keys([{'code': code} for code in codes]))
    return pd.DataFrame([{ 'code': str(row['code']), 'content': str(row['data']) } for row in rows])