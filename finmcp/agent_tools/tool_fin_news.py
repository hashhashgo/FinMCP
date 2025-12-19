from fastmcp import FastMCP
import pandas as pd
from datetime import datetime, date
from typing import Literal, List, Dict, Any

import os
import sys
from pathlib import Path

from importlib.resources import files

if not __package__:
    sys.path.append(str(Path(__file__).parent.parent.parent))
from finmcp.data_sources.fin_news import NewsDataSource
from finmcp.data_sources.fin_news import DATASOURCES

mcp = FastMCP(
    name = "Financial News MCP Service",
    instructions = """
    This service provides news retrieval.
    """,
)

datasources: Dict[str, NewsDataSource] = {}

@mcp.tool(
    description = 
f"""
List news for a given symbol from specified data source.

Returns: DataFrame
- Columns (at least):
    - date: str, Date and time of the news in "YYYY-MM-DD HH:MM:SS" format
    - title: str, Title of the news article
    - content: str, some content of the news article
    - code: str, Unique code identifier for the news article

If an error occurs, returns a list with a single dictionary containing:
- request: dict, The original request parameters
- error: str, Error message

Be careful with the symbol parameter, for chinese news, it may requiere a chinese keyword.
For example, to search for news related to "CSI500", you may use the chinese name "中证500".
This function only returns news articles that exactly match the given symbol keyword in their title or content.

Parameters:
- datasource: str, Data source, currently supports: "{'" / "'.join(DATASOURCES.keys())}"
- symbol: str, any keywords to search for in the news articles
- start: str, start time, supports: "YYYY-MM-DD" / "YYYY-MM-DD HH:MM:SS"
- end: str, end time, supports: "YYYY-MM-DD" / "YYYY-MM-DD HH:MM:SS", default is current time
"""
)
def list_news(
    datasource: str,
    symbol: str,
    start: str = "2000-01-01 00:00:00",
    end: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
) -> List[Dict[str, Any]]:
    try:
        if datasource not in DATASOURCES:
            raise ValueError(f"Unknown datasource: {datasource}\n\nSupported datasources: {' / '.join(DATASOURCES.keys())}")

        if datasource not in datasources:
            datasources[datasource] = DATASOURCES[datasource]()
        ds = datasources[datasource]

        print(f"Fetching news: datasource={datasource}, symbol={symbol}, start={start}, end={end}")

        df: pd.DataFrame = ds.list_news(
            symbol=symbol,
            start=start,
            end=end,
        )

        df['date'] = df['date'].dt.strftime("%Y-%m-%d %H:%M:%S")

        return df.to_dict(orient="records")
    except Exception as e:
        return [
            {
                "request": {
                    "datasource": datasource,
                    "symbol": symbol,
                    "start": start,
                    "end": end,
                },
                "error": str(e)
            }
        ]


@mcp.tool(
    description =
f"""
Get news article details by its unique code.

Parameters:
- datasource: str, Data source, currently supports: "{'" / "'.join(DATASOURCES.keys())}"
- code: str, The unique identifier of the news article, get from list_news function.

Returns: str, Detailed information about the news article as a string.
"""
)
def news_details(
    datasource: str,
    code: str
) -> str:
    if datasource not in DATASOURCES:
        raise ValueError(f"Unknown datasource: {datasource}\n\nSupported datasources: {' / '.join(DATASOURCES.keys())}")
    
    if datasource not in datasources:
        datasources[datasource] = DATASOURCES[datasource]()
    
    ds = datasources[datasource]

    print(f"Fetching news details for code: {code}")

    return ds.news_details(code=code)


__all__ = ["mcp", "news_details", "list_news"]


if __name__ == "__main__":
    mcp.run()