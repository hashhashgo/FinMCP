from fastmcp import FastMCP
import pandas as pd
from datetime import datetime, date
from typing import Literal, List, Dict, Any

import os
import sys
from pathlib import Path
import logging
logger = logging.getLogger(__name__)

from importlib.resources import files

if not __package__:
    sys.path.append(str(Path(__file__).parent.parent.parent))
from fintools.data_sources.fin_history import OHLCDataSource
from fintools.data_sources.fin_history import UnderlyingType, DataFrequency, STANDARD_COLUMN_NAMES, DATASOURCES

mcp = FastMCP(
    name = "Financial Data History MCP Service",
    instructions = """
    This service provides historical financial data retrieval.
    """,
)

datasources: Dict[str, OHLCDataSource] = {}

@mcp.tool(
    description = 
f"""
Get historical financial data for a given symbol from specified data source.

Returns: DataFrame, with standard columns: {', '.join(STANDARD_COLUMN_NAMES)} and specific columns
- date: str (formatted as "YYYY-MM-DD HH:MM:SS")
- other standard columns: float
- specific columns: refer to data source documnentation.

If an error occurs, returns a list with a single dictionary containing:
- request: dict, The original request parameters
- error: str, Error message

Parameters:
- datasource: str, Data source, currently supports: "{'" / "'.join(DATASOURCES.keys())}"
- symbol: str, The symbol code, e.g., "AAPL", "000001.SZ", "AUDCAD.FXCM". It's recommended to use list_indices tool to find valid symbols, or refer to the data source documentation.
- type: str, The type of the symbol, supports: "{'" / "'.join([t.value for t in UnderlyingType])}"
- start: str, start time, supports: "YYYY-MM-DD" / "YYYY-MM-DD HH:MM:SS"
- end: str, end time, supports: "YYYY-MM-DD" / "YYYY-MM-DD HH:MM:SS", default is current time
- freq: str, data frequency, supports: "{'" / "'.join([f.value for f in DataFrequency])}", default is "daily"
- only_standard_columns: bool, if True, only return standard columns
"""
)
def history(
    datasource: str,
    symbol: str,
    type: str,
    start: str = "2000-01-01 00:00:00",
    end: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    freq: str = "daily",
    only_standard_columns: bool = True
) -> List[Dict[str, Any]]:
    try:
        if datasource not in DATASOURCES:
            raise ValueError(f"Unknown datasource: {datasource}\n\nSupported datasources: {' / '.join(DATASOURCES.keys())}")

        if datasource not in datasources:
            datasources[datasource] = DATASOURCES[datasource]()
        ds = datasources[datasource]

        try:
            data_type = UnderlyingType(type)
        except ValueError:
            raise ValueError(f"Unknown data type: {type}\n\nSupported types: {' / '.join([t.value for t in UnderlyingType])}")

        try:
            freq_enum = DataFrequency(freq)
        except ValueError:
            raise ValueError(f"Unknown frequency: {freq}\n\nSupported frequencies: {' / '.join([f.value for f in DataFrequency])}")

        logger.info(f"Fetching history: datasource={datasource}, symbol={symbol}, type={type}, start={start}, end={end}, freq={freq}, only_standard_columns={only_standard_columns}")

        df: pd.DataFrame = ds.history(
            symbol=symbol,
            type=data_type,
            start=start,
            end=end,
            freq=freq_enum,
        )

        df['date'] = df['date'].dt.strftime("%Y-%m-%d %H:%M:%S")
        if only_standard_columns:
            df = pd.DataFrame(df[STANDARD_COLUMN_NAMES])

        return df.to_dict(orient="records")
    except Exception as e:
        return [
            {
                "request": {
                    "datasource": datasource,
                    "symbol": symbol,
                    "type": type,
                    "start": start,
                    "end": end,
                    "freq": freq,
                    "only_standard_columns": only_standard_columns
                },
                "error": str(e)
            }
        ]


@mcp.tool(
    description =
"""
List known financial indices with their types and available data sources.
Returns: List of dictionaries, each containing:
- name: str, Name of the index
- type: str, Type of the index
- datasource1: str, Symbol code in datasource1
- datasource2: str, Symbol code in datasource2 (if available)
- ... (other data sources)
"""
)
def list_indices() -> List[Dict[str, str]]:
    logger.info("Listing known financial indices")
    df = pd.read_csv(files("fintools").joinpath("data/known_indices.csv").open(encoding="utf-8"))
    df = df[['name', 'type'] + list(DATASOURCES.keys())]
    ret = []
    for _, row in df.iterrows():
        entry = {col: row[col] for col in df.columns if pd.notna(row[col])}
        ret.append(entry)
    return ret


__all__ = ["mcp", "history", "list_indices"]


if __name__ == "__main__":
    mcp.run()