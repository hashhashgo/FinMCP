import json
import sqlite3
from contextlib import contextmanager
import os
import pandas as pd
from datetime import date, datetime
from typing import Optional, Tuple, List, Callable, Dict, Any, Union
from hashlib import sha1
from dataclasses import dataclass
import inspect

from pyparsing import wraps

from . import BaseDB, DB_CONNECTIONS

import logging


Fields = Dict[str, Union[int, str, datetime, float, bool]]

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
        return "TEXT"     # 默认当作 BLOB

def _python_value_to_sqlite_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return _datetime_to_timestamp(value)
    elif isinstance(value, bool):
        return int(value)
    elif isinstance(value, (int, float, str)):
        return value
    else:
        return str(value)

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
    return datetime.fromtimestamp(ts / 1000000)

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
            df[col] = pd.to_datetime(df[col], unit='us')
        elif pd.api.types.is_bool_dtype(dtype):
            df[col] = df[col].astype(bool)
        cols.append(col)
    return df[cols]

class IntervalDB(BaseDB):
    def __init__(self, table_basename: str, db_path: str = os.getenv("HISTORY_DB_PATH", "history.db")):
        assert os.path.exists(db_path), f"数据库文件不存在：{db_path}"
        self.connection = sqlite3.connect(db_path)
        self.connection.execute("PRAGMA journal_mode=WAL;")
        self.connection.row_factory = sqlite3.Row
        self.table_basename = table_basename + "_intervals"
        self.tables = set()


    def _init_schema(self, key_fields: Fields, common_fields: Fields) -> None:
        cur = self.connection.cursor()

        table_name = _get_table_name(base=self.table_basename, common_fields=common_fields)

        table_fields = []
        for field, value in key_fields.items():
            sql_type = _python_type_to_sqlite_type(type(value).__name__)
            table_fields.append(f"{field} {sql_type} NOT NULL")

        # 1. 区间缓存表
        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name}(
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            {', '.join(table_fields)},
            start_ts  INTEGER NOT NULL,  -- [start_ts, end_ts)
            end_ts    INTEGER NOT NULL
        );
        """)

        # 2. 复合索引：按 (symbol, freq, start_ts) 查区间
        cur.execute(f"""
        CREATE INDEX IF NOT EXISTS idx_cache_sym_tf_start
        ON {table_name}({", ".join(key_fields.keys())}, start_ts);
        """)

        # 可选：按 end_ts 再建一个索引，会让查询略微快一点
        cur.execute(f"""
        CREATE INDEX IF NOT EXISTS idx_cache_sym_tf_end
        ON {table_name}({", ".join(key_fields.keys())}, end_ts);
        """)

        self.connection.commit()
        self.tables.add(table_name)

    # ------------------- 写缓存：插入并合并区间 -------------------

    def add_interval(self, key_fields: Fields, common_fields: Fields, 
                     start: datetime, end: datetime) -> None:
        """
        插入一个已经下载好的区间 [start_ts, end_ts)，
        自动和已有区间合并，保证表里同一 (symbol, type, freq) 下
        只有若干个不重叠的已缓存区间。
        """
        if end <= start:
            return  # 空区间，直接忽略

        start_ts = _datetime_to_timestamp(start)
        end_ts = _datetime_to_timestamp(end)

        table_name = _get_table_name(base=self.table_basename, common_fields=common_fields)
        if table_name not in self.tables:
            self._init_schema(key_fields=key_fields, common_fields=common_fields)

        with self._tx():
            cur = self.connection.cursor()

            # 1. 查出所有与新区间 [start_ts, end_ts) 有交集的旧区间
            cur.execute(f"""
                SELECT id, start_ts, end_ts
                FROM {table_name}
                WHERE 
                    {" AND ".join([f"{k} = ?" for k in key_fields.keys()])}
                    AND end_ts   >= ?
                    AND start_ts <= ?
                ORDER BY start_ts
            """, (*[_python_value_to_sqlite_value(v) for v in key_fields.values()], start_ts, end_ts))
            rows = cur.fetchall()

            # 2. 和这些区间做并集，合并成一个大区间 [S, E)
            S, E = start_ts, end_ts
            ids_to_delete = []

            for r in rows:
                ids_to_delete.append(r["id"])
                S = min(S, r["start_ts"])
                E = max(E, r["end_ts"])

            # 3. 删除旧的重叠区间
            if ids_to_delete:
                placeholders = ",".join("?" * len(ids_to_delete))
                cur.execute(f"""
                    DELETE FROM {table_name}
                    WHERE id IN ({placeholders})
                """, ids_to_delete)

            # 4. 插入合并后的新区间
            cur.execute(f"""
                INSERT INTO {table_name}({", ".join(key_fields.keys())}, start_ts, end_ts)
                VALUES ({", ".join(["?"] * (len(key_fields) + 2))})
            """, (*[_python_value_to_sqlite_value(v) for v in key_fields.values()], S, E))

    # ------------------- 读缓存：查缺失区间 -------------------

    def get_missing(self, key_fields: Fields, common_fields: Fields,
                    start: datetime, end: datetime) -> List[Tuple[datetime, datetime]]:
        """
        在整体查询区间 [qs, qe) 内，返回所有“尚未缓存”的子区间列表。

        返回值形如：
            [(missing_start_1, missing_end_1),
             (missing_start_2, missing_end_2), ...]
        """
        if end <= start:
            return []
        
        start_ts = _datetime_to_timestamp(start)
        end_ts = _datetime_to_timestamp(end)

        table_name = _get_table_name(base=self.table_basename, common_fields=common_fields)
        if table_name not in self.tables:
            self._init_schema(key_fields=key_fields, common_fields=common_fields)

        cur = self.connection.cursor()

        # 1. 查出所有和 [qs, qe) 有交集的已缓存区间
        cur.execute(f"""
            SELECT start_ts, end_ts
            FROM {table_name}
            WHERE 
                {" AND ".join([f"{k} = ?" for k in key_fields.keys()])}
                AND end_ts   > ?
                AND start_ts < ?
            ORDER BY start_ts
        """, (*[_python_value_to_sqlite_value(v) for v in key_fields.values()], start_ts, end_ts))
        intervals = cur.fetchall()

        res: List[Tuple[datetime, datetime]] = []

        # 2. 扣掉已缓存区间，找中间的“空洞”
        cur_pos = start_ts  # 当前已覆盖到的最右端
        for row in intervals:
            s, e = row["start_ts"], row["end_ts"]

            assert e > cur_pos, "数据库中存在非法区间"

            if s > cur_pos:
                # [cur_pos, s) 是一段没缓存的区间
                res.append((_timestamp_to_datetime(cur_pos), _timestamp_to_datetime(s)))

            # 更新游标：当前已覆盖到的最右端
            cur_pos = e

            if cur_pos >= end_ts:
                break

        # 3. 尾巴上还有一段没覆盖
        if cur_pos < end_ts:
            res.append((_timestamp_to_datetime(cur_pos), _timestamp_to_datetime(end_ts)))

        return res

    def get_all(self, key_fields: Fields, common_fields: Fields) -> List[Tuple[datetime, datetime]]:
        """
        获取某个 (symbol, freq) 下的所有已缓存区间。
        返回值形如：
            [(cached_start_1, cached_end_1),
             (cached_start_2, cached_end_2), ...]
        """
        table_name = _get_table_name(base=self.table_basename, common_fields=common_fields)
        if table_name not in self.tables:
            self._init_schema(key_fields=key_fields, common_fields=common_fields)

        cur = self.connection.cursor()

        cur.execute(f"""
            SELECT start_ts, end_ts
            FROM {table_name}
            WHERE
                {" AND ".join([f"{k} = ?" for k in key_fields.keys()])}
            ORDER BY start_ts
        """, (*[_python_value_to_sqlite_value(v) for v in key_fields.values()],))

        intervals = cur.fetchall()

        res: List[Tuple[datetime, datetime]] = []
        for row in intervals:
            res.append((_timestamp_to_datetime(row["start_ts"]), _timestamp_to_datetime(row["end_ts"])))

        return res


class HistoryDB(BaseDB):
    def __init__(self, table_basename: str, db_path: str = os.getenv("HISTORY_DB_PATH", "history.db"), missing_threshold: int = 1):
        assert os.path.exists(db_path), f"数据库文件不存在：{db_path}"
        self.connection = sqlite3.connect(db_path)
        self.connection.execute("PRAGMA journal_mode=WAL;")
        self.connection.row_factory = sqlite3.Row
        self.table_basename = table_basename
        self.missing_threshold = missing_threshold
        self._interval_db = IntervalDB(table_basename, db_path)
        self.tables = {}
    
    def history(self, key_fields: Fields = {}, common_fields: Fields = {}, except_fields: Fields = {},
                start: datetime = datetime.fromtimestamp(0),
                end: datetime = datetime.now(),
                callback: Optional[Callable[..., pd.DataFrame]] = None,
                field_map: Optional[Dict[str, str]] = None) -> pd.DataFrame:
        """
        获取历史数据。

        参数：
            key_fields: 关键字段，如 symbol 等
            common_fields: 公共字段，如 type、 freq 等
            start: 起始时间（包含）, datetime 类型
            end: 结束时间（不包含）, datetime 类型
            callback: 当发现缺失区间时，用于下载数据的回调函数，函数签名类似：
                callback(symbol: str, type: str, freq: str, start: datetime, end: datetime) -> pd.DataFrame
            field_map: 函数调用时用于字段映射的字典，键为回调函数返回的字段名，值为数据库中的字段名。
        返回值：
            符合条件的历史数据表，类型为pd.DataFrame。
        """
        table_name = _get_table_name(base=self.table_basename, common_fields=common_fields)

        missing = self._interval_db.get_missing(key_fields=key_fields, common_fields=common_fields, start=start, end=end)
        if len(missing) > self.missing_threshold:
            logging.debug(f"[HistoryDB]: 发现表 {table_name} 中有 {len(missing)} 个缺失区间，超过阈值 {self.missing_threshold}，采用整块下载。")
            assert callback is not None, "需要提供 callback 函数以下载缺失数据"
            arguments: Dict[str, Any] = {}
            arguments.update(key_fields)
            arguments.update(common_fields)
            arguments.update(except_fields)
            arguments.update({"start": missing[0][0], "end": missing[-1][1]})
            if field_map is not None:
                call_args = {}
                for k, v in field_map.items():
                    call_args[k] = arguments.get(v)
            else: call_args = arguments
            data = callback(**call_args)
            if not data.empty:
                self._insert_data(data, key_fields=key_fields, common_fields=common_fields)
                self._interval_db.add_interval(key_fields=key_fields, common_fields=common_fields,
                                               start=missing[0][0], end=(data["date"].dt.tz_localize(None).max() + pd.Timedelta(microseconds=1)).to_pydatetime())
        elif len(missing) > 0:
            for (ms, me) in missing:
                logging.debug(f"[HistoryDB]: 发现表 {table_name} 中缺失区间 [{ms} - {me})，采用分块下载。")
                assert callback is not None, "需要提供 callback 函数以下载缺失数据"
                arguments: Dict[str, Any] = {}
                arguments.update(key_fields)
                arguments.update(common_fields)
                arguments.update(except_fields)
                arguments.update({"start": ms, "end": me})
                if field_map is not None:
                    call_args = {}
                    for k, v in field_map.items():
                        call_args[k] = arguments.get(v)
                else:
                    call_args = arguments
                data = callback(**call_args)
                if not data.empty:
                    self._insert_data(data, key_fields=key_fields, common_fields=common_fields)
                    self._interval_db.add_interval(key_fields=key_fields, common_fields=common_fields, 
                                                   start=ms, end=(data["date"].dt.tz_localize(None).max() + pd.Timedelta(microseconds=1)).to_pydatetime())

        # 最后，返回完整数据
        cur = self.connection.cursor()
        if not self.tables.get(table_name): self.tables[table_name] = self._get_table_info(common_fields=common_fields)
        if not self.tables.get(table_name): return pd.DataFrame([])  # 表不存在，且本次也没数据，直接返回空表
        cur.execute(f"""
            SELECT * FROM {table_name}
            WHERE date >= ? AND date < ?
                AND {" AND ".join([f"{k} = ?" for k in key_fields.keys()])}
            ORDER BY date ASC
        """, (_datetime_to_timestamp(start), _datetime_to_timestamp(end), *[_python_value_to_sqlite_value(v) for v in key_fields.values()]))
        rows = cur.fetchall()
        df = pd.DataFrame(rows, columns=rows[0].keys() if rows else [])
        if not df.empty:
            return _sqlite_value_to_pandas_value(df, type_dict=self._get_table_info(common_fields=common_fields))
        else:
            return df


    def _insert_data(self, df: pd.DataFrame, key_fields: Fields, common_fields: Fields):
        """
        将 DataFrame 中的数据插入到数据库表中。
        """
        table_name = _get_table_name(base=self.table_basename, common_fields=common_fields)
        if table_name not in self.tables:
            self._create_table_from_df(df, key_fields=key_fields, common_fields=common_fields)
        for i, k in enumerate(key_fields.keys()):
            df.insert(i, k, _python_value_to_sqlite_value(key_fields[k]))
            if isinstance(key_fields[k], str):
                df[k] = df[k].astype("string")
        self._check_df(df, key_fields=key_fields, common_fields=common_fields)

        placeholders = ",".join("?" * len(df.columns))
        columns = ",".join([f'"{col}"' for col in df.columns])

        sql = f'INSERT OR REPLACE INTO "{table_name}" ({columns}) VALUES ({placeholders});'

        df = df.where(df.notna(), None)
        df = _pandas_value_to_sqlite_value(df)
        data_tuples = [tuple(row) for row in df.itertuples(index=False)]

        cur = self.connection.cursor()
        with self._tx():
            cur.executemany(sql, data_tuples)
    
    def _check_df(self, df: pd.DataFrame, key_fields: Fields, common_fields: Fields) -> None:
        """
        检查 DataFrame 的列名和 dtype 是否和数据库表结构匹配。
        """
        # 检查列名和数量
        table_name = _get_table_name(base=self.table_basename, common_fields=common_fields)
        if table_name not in self.tables:
            self.tables[table_name] = self._get_table_info(common_fields=common_fields)
        
        if not self.tables.get(table_name):
            print(self.tables[table_name], f"数据库表 {table_name} 不存在，跳过。")
            return

        # 检查数据类型
        for col, dtype in df.dtypes.items():
            if col in key_fields:
                continue  # 跳过 key_fields 的类型检查
            sql_type = str(dtype)
            db_type = self.tables[table_name].get(col, None)

            if db_type is None:
                raise ValueError(f"数据库表中缺少列：{col}")

            if sql_type != db_type and not (pd.api.types.is_datetime64_any_dtype(sql_type) and pd.api.types.is_datetime64_any_dtype(db_type)):
                raise ValueError(f"列 '{col}' 的数据类型不匹配。数据库类型：{db_type}，DataFrame 类型：{sql_type}")

    def _create_table_from_df(self, df: pd.DataFrame, key_fields: Fields, common_fields: Fields) -> None:
        """
        根据 DataFrame 的列名和 dtype 自动创建 SQLite 表。
        """
        table_name = _get_table_name(base=self.table_basename, common_fields=common_fields)

        assert "date" in df.columns, "DataFrame 必须包含 'date' 列作为主键"
        cols = [f'"{k}" {_python_type_to_sqlite_type(type(v).__name__)}' for k, v in key_fields.items()]
        for col, dtype in df.dtypes.items():
            sql_type = _pandas_dtype_to_sqlite_type(dtype)
            cols.append(f'"{col}" {sql_type}')
        primary_keys = ", ".join([f'"{k}"' for k in key_fields.keys()] + ['"date"'])

        col_definitions = ",\n".join(cols)

        sql = f'CREATE TABLE IF NOT EXISTS "{table_name}" (\n{col_definitions},\n PRIMARY KEY ({primary_keys}));'

        logging.info("Generated SQL:")
        logging.info(sql)

        curr = self.connection.cursor()
        with self._tx():
            curr.execute(sql)
            self.tables[table_name] = self._set_table_info(df, common_fields=common_fields)

    def _set_table_info(self, df: pd.DataFrame, common_fields: Fields) -> Dict[str, str]:
        """
        把 DataFrame 的表结构信息存储起来。
        """
        table_name = _get_table_name(base=self.table_basename, common_fields=common_fields)
        cur = self.connection.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS DataFrame_infos (
            table_name TEXT,
            column_name TEXT,
            data_type TEXT,
            PRIMARY KEY (table_name, column_name)
        );
        """)
        cur.fetchall()
        cur.execute(f"PRAGMA table_info({table_name});")
        cols = cur.fetchall()
        for col, dtype in df.dtypes.items():
            cur.execute("""
            INSERT OR REPLACE INTO DataFrame_infos (table_name, column_name, data_type)
            VALUES (?, ?, ?);
            """, (table_name, col, str(dtype)))
            if col not in [c["name"] for c in cols]:
                logging.warning(f"Column '{col}' not found in table '{table_name}' during _set_table_info.")
                cur.execute(f"""
                ALTER TABLE {table_name}
                ADD COLUMN "{col}" {_pandas_dtype_to_sqlite_type(dtype)};
                """)

        return self._get_table_info(common_fields=common_fields)

    def _get_table_info(self, common_fields: Fields) -> Dict[str, str]:
        table_name = _get_table_name(base=self.table_basename, common_fields=common_fields)
        cur = self.connection.cursor()
        try:
            cur.execute(f"""
            SELECT * FROM DataFrame_infos
            WHERE table_name = ?;
            """, (table_name,))
        except sqlite3.OperationalError:
            return {}
        info = {}
        for col in cur.fetchall():
            info[col["column_name"]] = col["data_type"]
        return info


def _parse_datetime(datetime_input: Union[str, datetime, date, int]) -> datetime:
    if isinstance(datetime_input, date):
        return datetime(datetime_input.year, datetime_input.month, datetime_input.day)
    elif isinstance(datetime_input, datetime):
        return datetime_input
    elif isinstance(datetime_input, int):
        if datetime_input > 9999999999: datetime_input = datetime_input // 1000
        return datetime.fromtimestamp(datetime_input)
    elif isinstance(datetime_input, str):
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y%m%d%H%M%S", "%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
            try:
                return datetime.strptime(datetime_input, fmt)
            except ValueError:
                continue
        raise ValueError(f"String datetime format not recognized: {datetime_input}")
    else:
        raise TypeError(f"Unsupported datetime input type: {type(datetime_input)}")

@dataclass(frozen=True)
class CacheConfig:
    table_basename: str
    db_path: str
    key_fields: Tuple[str, ...]
    common_fields: Tuple[str, ...]
    except_fields: Tuple[str, ...]
    date_col: str
    start_col: str
    end_col: str
    missing_threshold: int

def history_cache(
    table_basename: str = "",
    db_path: str = "history.db",
    key_fields: Tuple[str, ...] = (),
    common_fields: Tuple[str, ...] = (),
    except_fields: Tuple[str, ...] = (),
    date_col: str = "date",
    start_col: str = "start",
    end_col: str = "end",
    missing_threshold: int = 1
) -> Callable[[Callable[..., pd.DataFrame]], Callable[..., pd.DataFrame]]:
    """
    - 自动识别参数：bind(*args, **kwargs)
    - 默认所有参数都是 common_fields
    - except_fields 从 common_fields 里剔除（同时也不参与 hash）
    - 表名：{table_basename}_{sha1(common_fields + func_id)}_{data/ranges}
    - 注册：DB_CONNECTIONS["模块名:BaseDB"] = BaseDB(db_path)
    """
    cfg = CacheConfig(
        table_basename=table_basename,
        db_path=db_path,
        key_fields=key_fields,
        common_fields=common_fields,
        except_fields=except_fields,
        date_col=date_col,
        start_col=start_col,
        end_col=end_col,
        missing_threshold=missing_threshold
    )

    assert date_col == "date", NotImplementedError("暂不支持自定义 date_col")

    def deco(func: Callable[..., pd.DataFrame]) -> Callable[..., pd.DataFrame]:
        # 注册 DB（按 模块名:BaseDB）
        reg_key = f"{func.__module__}:{func.__qualname__}"
        sig = inspect.signature(func)

        table_basename = cfg.table_basename if cfg.table_basename else func.__name__
        if reg_key not in DB_CONNECTIONS:
            DB_CONNECTIONS[reg_key] = HistoryDB(
                table_basename=table_basename,
                db_path=cfg.db_path,
                missing_threshold=cfg.missing_threshold
            )


        @wraps(func)
        def wrapper(*args, **kwargs) -> pd.DataFrame:
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            argmap: Dict[str, Any] = dict(bound.arguments)

            # start/end 必须存在（你也可以改成自动找 datetime 参数）
            if cfg.start_col not in argmap or cfg.end_col not in argmap:
                raise TypeError(f"Decorated function must accept parameters named '{cfg.start_col}' and '{cfg.end_col}'.")

            start_dt = _parse_datetime(argmap[cfg.start_col])
            end_dt = _parse_datetime(argmap[cfg.end_col])
            
            if not cfg.common_fields:
                common_fields = {}
                for each in argmap.keys():
                    if each not in cfg.key_fields and each not in cfg.except_fields and each != cfg.start_col and each != cfg.end_col and each != "self":
                        common_fields[each] = argmap[each]
            else:
                common_fields = {k: argmap[k] for k in cfg.common_fields if k not in cfg.except_fields}

            if not cfg.except_fields:
                except_fields = {}
                for each in argmap.keys():
                    if each not in cfg.key_fields and each not in common_fields and each != cfg.start_col and each != cfg.end_col and each != "self":
                        except_fields[each] = argmap[each]
            else:
                except_fields = {k: argmap[k] for k in cfg.except_fields}

            if "self" in argmap:
                func_dec = lambda *args, **fkwargs: func(argmap["self"], *args, **fkwargs)
            else:
                func_dec = func

            db = DB_CONNECTIONS[reg_key]
            if not isinstance(db, HistoryDB):
                raise TypeError(f"DB_CONNECTIONS[{reg_key}] 必须是 HistoryDB 类型")
            return db.history(
                key_fields={k: argmap[k] for k in cfg.key_fields},
                common_fields=common_fields,
                except_fields=except_fields,
                start=start_dt,
                end=end_dt,
                callback=func_dec
            )

        return wrapper

    return deco




__all__ = ["IntervalDB", "HistoryDB", "DB_CONNECTIONS", "history_cache"]
