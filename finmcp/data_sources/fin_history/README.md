Languages: English | [中文](README.zh_CN.md)

# Introduction

A unified Python interface for multiple market data providers. This library standardizes financial data across different sources and returns consistent Pandas `DataFrame` formats.

## Standard Output Format

Every data source must return a `pd.DataFrame` including the following columns:

```python
["date", "open", "high", "low", "close", "volume"]
```

If the underlying provider does not offer certain fields, they are automatically filled with `NaN`.

Other fields provided are kept unchanged in the `DataFrame`.

## Supported Asset Types

`DataType` enum:

```json
STOCK, INDEX, FUTURES, FOREX, CRYPTO
```

------

## Supported Frequencies

`DataFrequency` enum includes:

```
MINUTE1, MINUTE5, MINUTE15, MINUTE30, MINUTE60, DAILY, WEEKLY, MONTHLY, ...
```

Frequency values are mapped by each provider through `freq`.

------

## Basic Usage Example

```

from your_package import YourDataSource, DataType, DataFrequency

source = YourDataSource(token="your-token")

df = source.history(
    symbol="AAPL",
    type=DataType.STOCK,
    start="2023-01-01",
    end="2023-12-31",
    freq=DataFrequency.DAILY
)

print(df.head())
```

------

## Implementing a Custom Data Source

To add a new provider, subclass `OHLCDataSource` and implement three abstract methods:

```

from your_package import OHLCDataSource, DataType, DataFrequency
import pandas as pd

class ExampleSource(OHLCDataSource):

    freq_map = {
        DataFrequency.MINUTE1: "1m",
        DataFrequency.DAILY: "1d",
    }
    column_names = ["Date", "Open", "High", "Low", "Close", "Volume"]

    def history(self, symbol, type, start, end, freq) -> pd.DataFrame:
        raw = ...  # API request or local loading
        df = pd.DataFrame(raw)
        return self._format_dataframe(df)

    def subscribe(self, symbol: str, interval: str, callback) -> None:
        # Optional WebSocket implementation
        pass

    def unsubscribe(self, symbol: str, interval: str) -> None:
        pass
```

You can rely on:

- `_parse_datetime()` for automatic date conversion
- `_format_dataframe()` for standardizing column names
- `_map_frequency()` to validate frequency support