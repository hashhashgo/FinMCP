from pyparsing import ABC, abstractmethod
from datetime import datetime, date, timedelta
import pandas as pd
from typing import Optional, Union, Annotated
from enum import Enum

from .. import DataSource

class SortingMethod(Enum):
    """Enumeration for sorting methods."""
    DEFAULT = "default"
    RELEVANCE = "relevance"
    DATE_ASCENDING = "date_asc"
    DATE_DESCENDING = "date_desc"

class ReportDataSource(DataSource, ABC):
    """Base class for financial news data sources."""

    @abstractmethod
    def list_reports(
        self,
        symbol: str,
        start: Union[str, datetime, date, int] = 0,
        end: Union[str, datetime, date, int] = datetime.now()
    ) -> pd.DataFrame:
        """Fetch a list of reports for a given symbol within a specified date range.
        Args:
            symbol (str): The stock symbol to fetch reports for.
            start (Union[str, datetime, date, int], optional): The start date for fetching reports.
            end (Union[str, datetime, date, int], optional): The end date for fetching reports.
        Returns:
            pd.DataFrame: A DataFrame containing the list of reports.
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    def report_details(
        self,
        code: Annotated[str, "The unique identifier of the report, for example, 202506203436053233."]
    ) -> str:
        """Fetch detailed information about a specific report by its ID.
        Args:
            code (str): The unique identifier of the report.

        Returns:
            str: Detailed information about the report as a string.
        """
        raise NotImplementedError("Subclasses must implement this method")
    
