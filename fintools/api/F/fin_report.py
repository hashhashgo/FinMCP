from typing import Dict, Annotated

from datetime import datetime, date
import pandas as pd
import tzlocal

import logging

logger = logging.getLogger(__name__)

from fintools.data_sources.fin_report import DATASOURCES, ReportDataSource

datasources: Dict[str, ReportDataSource] = {}

def list_reports(
    datasource: Annotated[str, "data source, selected from: " + ", ".join(DATASOURCES.keys())],
    symbol: Annotated[str, "any keywords to search for reports articles"],
    start: Annotated[str | datetime | date | int, "start time, supports str: YYYY-MM-DD / YYYY-MM-DD HH:MM:SS | datetime | date | int (timestamp)"] = 0,
    end: Annotated[str | datetime | date | int, "end time, supports str: YYYY-MM-DD / YYYY-MM-DD HH:MM:SS | datetime | date | int (timestamp)"] = datetime.now(),
) -> pd.DataFrame:
    """
    Search for reports articles related to a given symbol from specified data source.

    Parameters:
    - datasource: str, Data source
    - symbol: str, Keywords to search for reports articles.
    - start: str | datetime | date | int, start time
    - end: str | datetime | date | int, end time

    Time range is [start, end), i.e., start is inclusive, end is exclusive.
    So if you want reports up to and including 2025-01-01, please set end to 2025-01-02.

    Returns: reports DataFrame, containing reports articles with at least the following fields:
    - date: str, Publication date of the reports article
    - code: str, Unique identifier of the reports article
    - title: str, Title of the reports article
    - content: str, Content of the reports article
    """
    if datasource not in DATASOURCES:
        raise ValueError(f"Unknown datasource: {datasource}\n\nSupported datasources: {' / '.join(DATASOURCES.keys())}")

    if datasource not in datasources:
        datasources[datasource] = DATASOURCES[datasource]()
    ds = datasources[datasource]

    logger.info(f"Fetching reports: datasource={datasource}, symbol={symbol}, start={start}, end={end}")

    df: pd.DataFrame = ds.list_reports(
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

def reports_details(
    datasource: Annotated[str, "data source, selected from: " + ", ".join(DATASOURCES.keys())],
    code: Annotated[str, "unique identifier of the reports article"]
) -> str:
    """
    Get detailed information about a reports article given its unique code.
    Parameters:
    - datasource: str, Data source
    - code: str, Unique identifier of the reports article.

    Returns: str, detailed content of the reports article.
    """
    logger.info(f"Fetching reports details for code: {code}")
    if datasource not in DATASOURCES:
        raise ValueError(f"Unknown datasource: {datasource}\n\nSupported datasources: {' / '.join(DATASOURCES.keys())}")
    if datasource not in datasources:
        datasources[datasource] = DATASOURCES[datasource]()
    ds = datasources[datasource]
    
    reports = ds.report_details(code=code)

    return reports