import json
import pandas as pd
import tzlocal
from hashlib import sha1
from typing import Dict, Optional, Any
from datetime import datetime, date, timedelta
from . import Fields


def _python_type_to_sqlite_type(py_type: str) -> str:
    if py_type in ["int", "bool"]:
        return "INTEGER"
    elif py_type == "float":
        return "REAL"
    elif py_type == "str":
        return "TEXT"
    elif py_type == "datetime":
        return "INTEGER"
    else:
        return "TEXT"

def _python_value_to_sqlite_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return _datetime_to_timestamp(value)
    elif isinstance(value, bool):
        return int(value)
    elif isinstance(value, (int, float, str)):
        return value
    elif isinstance(value, (list, dict)):
        return json.dumps(value)
    else:
        return str(value)

def _sqlite_value_to_python_value(value: Any, type_s: str) -> Any:
    if type_s == "datetime":
        return _timestamp_to_datetime(value)
    elif type_s == "bool":
        return bool(value)
    elif type_s == "int":
        return int(value)
    elif type_s == "float":
        return float(value)
    elif type_s == "str":
        return str(value)
    elif type_s in ["list", "dict"]:
        return json.loads(value)
    else:
        return value

def _pandas_dtype_to_sqlite_type(dtype: pd.api.extensions.ExtensionDtype) -> str:
    if pd.api.types.is_integer_dtype(dtype):
        return "INTEGER"
    elif pd.api.types.is_float_dtype(dtype):
        return "REAL"
    elif pd.api.types.is_bool_dtype(dtype):
        return "INTEGER"   # 0/1
    elif pd.api.types.is_datetime64_any_dtype(dtype):
        return "INTEGER"    # 存 timestamp us
    else:
        return "TEXT"       # 默认当作 TEXT
    
def _timestamp_to_datetime(ts: int) -> datetime:
    return datetime.fromtimestamp(ts / 1000000).astimezone()

def _datetime_to_timestamp(dt: datetime) -> int:
    return int(dt.timestamp() * 1000000)

def _get_table_name(base: str, common_fields: Fields) -> str:
    hashed_name = sha1(("-".join([str(v) for v in common_fields.values()])).encode()).hexdigest()
    return f"{base}_{hashed_name}"

def _json_serialize(obj: Any) -> str:
    if isinstance(obj, str):
        return obj
    try:
        return json.dumps(obj)
    except TypeError:
        return str(obj)

def _pandas_value_to_sqlite_value(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].astype('int64') // 1000
        elif pd.api.types.is_bool_dtype(df[col]):
            df[col] = df[col].astype(int)
        elif df[col].dtype == 'object':
            df[col] = df[col].map(_json_serialize).astype("string")
    return df

def _sqlite_value_to_pandas_value(df: pd.DataFrame, type_dict: Dict[str, str]) -> pd.DataFrame:
    cols = []
    for col, dtype in type_dict.items():
        if pd.api.types.is_datetime64_any_dtype(dtype):
            df[col] = pd.to_datetime(df[col], unit='us', utc=True).dt.tz_convert(tzlocal.get_localzone_name())
        elif pd.api.types.is_bool_dtype(dtype):
            df[col] = df[col].astype(bool)
        cols.append(col)
    return df[cols]

def _parse_datetime(datetime_input: str | datetime | date | int) -> datetime:
    if isinstance(datetime_input, datetime):
        return datetime_input
    elif isinstance(datetime_input, date):
        return datetime(datetime_input.year, datetime_input.month, datetime_input.day)
    elif isinstance(datetime_input, int):
        if datetime_input > 9999999999: datetime_input = datetime_input // 1000
        return datetime.fromtimestamp(datetime_input).astimezone()
    elif isinstance(datetime_input, str):
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y%m%d%H%M%S", "%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
            try:
                return datetime.strptime(datetime_input, fmt).astimezone()
            except ValueError:
                continue
        raise ValueError(f"String datetime format not recognized: {datetime_input}")
    else:
        raise TypeError(f"Unsupported datetime input type: {type(datetime_input)}")


__all__ = [
    "_python_type_to_sqlite_type",
    "_python_value_to_sqlite_value",
    "_sqlite_value_to_python_value",
    "_pandas_dtype_to_sqlite_type",
    "_timestamp_to_datetime",
    "_datetime_to_timestamp",
    "_get_table_name",
    "_json_serialize",
    "_pandas_value_to_sqlite_value",
    "_sqlite_value_to_pandas_value",
    "_parse_datetime",
]