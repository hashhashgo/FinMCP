from pyparsing import ABC, abstractmethod
from datetime import datetime, date, timedelta
import pandas as pd
from typing import Optional, Union, Annotated
from enum import Enum

from .. import DataSource, DataType

class SortingMethod(Enum):
    """Enumeration for sorting methods."""
    DEFAULT = "default"
    RELEVANCE = "relevance"
    DATE_ASCENDING = "date_asc"
    DATE_DESCENDING = "date_desc"

class NewsDataSource(DataSource, ABC):
    """Base class for financial news data sources."""

    @abstractmethod
    def list_news(
        self,
        symbol: str,
        type: DataType,
        start: Union[str, datetime, date, int] = 0,
        end: Union[str, datetime, date, int] = datetime.now()
    ) -> pd.DataFrame:
        """Fetch a list of news articles for a given symbol within a specified date range.
        Args:
            symbol (str): The stock symbol to fetch news for.
            type (DataType): The type of data to fetch.
            start (Union[str, datetime, date, int], optional): The start date for fetching news.
            end (Union[str, datetime, date, int], optional): The end date for fetching news.
        Returns:
            pd.DataFrame: A DataFrame containing the list of news articles.
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    def news_details(
        self,
        code: Annotated[str, "The unique identifier of the news article, for example, 202506203436053233."]
    ) -> str:
        """Fetch detailed information about a specific news article by its ID.

        Args:
            code (str): The unique identifier of the news article.

        Returns:
            str: Detailed information about the news article as a string.
        """
        raise NotImplementedError("Subclasses must implement this method")
    
