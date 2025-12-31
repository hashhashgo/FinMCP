Languages: [English](README.md) | 中文

# 介绍

这是一个面向多种行情数据源的统一 Python 接口库。本库可将不同来源的金融数据进行标准化处理，并输出一致格式的 Pandas `DataFrame`。

## 标准输出格式

所有数据源必须返回包含以下列的 `pd.DataFrame`：

```python
["date", "open", "high", "low", "close", "volume"]
```

如果底层数据源缺少某些字段，会自动填充为 `NaN`。

除标准字段以外的其他数据会被原样保留在 `DataFrame` 中。

## 支持的资产类型

`DataType` 枚举：

```json
STOCK, INDEX, FUTURES, FOREX, CRYPTO
```

------

## 支持的时间周期

`DataFrequency` 枚举包括：

```
MINUTE1, MINUTE5, MINUTE15, MINUTE30, MINUTE60, DAILY, WEEKLY, MONTHLY, ...
```

具体周期值通过各数据源的 `freq` 映射实现。

------

## 基本使用示例

```python
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

## 如何实现自定义数据源

只需继承 `OHLCDataSource` 并实现三个抽象方法：

```python
from your_package import OHLCDataSource, DataType, DataFrequency
import pandas as pd

class ExampleSource(OHLCDataSource):

    freq_map = {
        DataFrequency.MINUTE1: "1m",
        DataFrequency.DAILY: "1d",
    }
    column_names = ["Date", "Open", "High", "Low", "Close", "Volume"]

    def history(self, symbol, type, start, end, freq) -> pd.DataFrame:
        raw = ...  # 请求 API 或读取本地数据
        df = pd.DataFrame(raw)
        return self._format_dataframe(df)

    def subscribe(self, symbol: str, interval: str, callback) -> None:
        # 可选的 WebSocket 订阅实现
        pass

    def unsubscribe(self, symbol: str, interval: str) -> None:
        pass
```

你可以使用以下辅助方法：

- `_parse_datetime()`：自动解析多种日期格式
- `_format_dataframe()`：统一列名并补充缺失字段
- `_map_frequency()`：验证并转换时间周期映射
