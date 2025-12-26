import sqlite3
import os
import pandas as pd
from datetime import date, datetime, timedelta
from typing import Optional, Tuple, List, Callable, Dict, Any, Union
from dataclasses import dataclass
import inspect

from pyparsing import wraps

from . import BaseDB, Fields, DB_CONNECTIONS
from .utils import *

import logging


class CommonDB(BaseDB):
    def __init__(self, table_basename: str, db_path: str = os.getenv("DB_PATH", "history.db")):
        assert os.path.exists(db_path), f"数据库文件不存在：{db_path}"
        self.db_path = db_path
        self.table_basename = table_basename
        self.tables = {}
    
    def fetch(self, key_fields: Fields = {}, common_fields: Fields = {}, except_fields: Fields = {},
              callback: Optional[Callable[..., Any]] = None) -> Any:
        """
        获取一条数据。

        参数：
            key_fields: 关键字段，如 symbol 等，key_fields 作为主键的一部分
            common_fields: 公共字段，如 freq 等，common_fields 作为表名的一部分
            except_fields: 排除字段，如 type 等, 忽略这些字段
            callback: 当发现缺失数据时，用于下载数据的回调函数，函数签名类似：
                callback(key1, key2, common1, common2, ...) -> Any
        返回值：
            符合条件的数据，类型为Any。
        """
        table_name = self._get_table_name(common_fields=common_fields)

        # 最后，返回完整数据
        cur = self._get_cursor()
        if not self.tables.get(table_name): self.tables[table_name] = self._get_table_info(common_fields=common_fields)

        rows = []
        if self.tables.get(table_name):
            cond = f"WHERE {' AND '.join([f'{k} = ?' for k in key_fields.keys()])}" if key_fields else ""
            cur.execute(f"""
                SELECT * FROM {table_name}
                {cond}
            """, (*[_python_value_to_sqlite_value(v) for v in key_fields.values()], ))
            rows = cur.fetchall()
        
        if len(rows) == 0:
            assert callback is not None, f"数据库表 {table_name} 不存在，且未提供回调函数以获取数据。"
            # 调用回调函数获取数据
            data = callback(**key_fields, **common_fields, **except_fields)
            if isinstance(data, pd.DataFrame):
                assert "data" not in data.columns, "DataFrame 不应包含名为 'data' 的列"
            self._insert_data(data, key_fields=key_fields, common_fields=common_fields)
        
        cur = self._get_cursor()
        if not self.tables.get(table_name): self.tables[table_name] = self._get_table_info(common_fields=common_fields)
        assert self.tables.get(table_name), f"数据库表 {table_name} 不存在，插入数据失败。"

        cond = f"WHERE {' AND '.join([f'{k} = ?' for k in key_fields.keys()])}" if key_fields else ""

        cur.execute(f"""
            SELECT * FROM {table_name}
            {cond}
        """, (*[_python_value_to_sqlite_value(v) for v in key_fields.values()], ))
        rows = cur.fetchall()

        if isinstance(self.tables[table_name], dict):
            df = pd.DataFrame(rows, columns=rows[0].keys() if rows else [])
            if not df.empty:
                return _sqlite_value_to_pandas_value(df, type_dict=self.tables[table_name])
            else:
                return df
        else:
            data = rows[0]['data']
            return _sqlite_value_to_python_value(data, type_s=self.tables[table_name])
    

    def _insert_data(self, data: Any, key_fields: Fields, common_fields: Fields):
        """
        将数据插入到数据库表中。
        """
        table_name = self._get_table_name(common_fields=common_fields)
        if table_name not in self.tables or self.tables.get(table_name) == "":
            self._create_table_from_data(data, key_fields=key_fields, common_fields=common_fields)

        if not isinstance(data, pd.DataFrame):
            self._check_data(data, key_fields=key_fields, common_fields=common_fields)
            placeholders = ",".join("?" * (len(key_fields) + 1))
            columns = ",".join([f'"{col}"' for col in list(key_fields.keys()) + ['data']])

            sql = f'INSERT OR REPLACE INTO "{table_name}" ({columns}) VALUES ({placeholders});'

            cur = self._get_cursor()
            with self._tx():
                cur.execute(sql, (*[_python_value_to_sqlite_value(v) for v in key_fields.values()],
                                _python_value_to_sqlite_value(data)))
        else:
            for i, k in enumerate(key_fields.keys()):
                data.insert(i, k, _python_value_to_sqlite_value(key_fields[k]))
                if isinstance(key_fields[k], str):
                    data[k] = data[k].astype("string")
            self._check_data(data, key_fields=key_fields, common_fields=common_fields)
            placeholders = ",".join("?" * len(data.columns))
            columns = ",".join([f'"{col}"' for col in data.columns])

            sql = f'INSERT OR REPLACE INTO "{table_name}" ({columns}) VALUES ({placeholders});'

            data = data.where(data.notna(), None)
            data = _pandas_value_to_sqlite_value(data)
            data_tuples = [tuple(row) for row in data.itertuples(index=False)]

            cur = self._get_cursor()
            with self._tx():
                cur.executemany(sql, data_tuples)
    
    def _check_data(self, data: Any, key_fields: Fields, common_fields: Fields) -> None:
        """
        检查 data 和 dtype 是否和数据库表匹配。
        """
        # 检查列名和数量
        table_name = self._get_table_name(common_fields=common_fields)
        if table_name not in self.tables:
            self.tables[table_name] = self._get_table_info(common_fields=common_fields)
        
        if not self.tables.get(table_name):
            print(self.tables[table_name], f"数据库表 {table_name} 不存在，跳过。")
            return

        # 检查数据类型
        if isinstance(data, pd.DataFrame):
            for col, dtype in data.dtypes.items():
                if col in key_fields:
                    continue  # 跳过 key_fields 的类型检查
                sql_type = str(dtype)
                db_type = self.tables[table_name].get(col, None)

                if db_type is None:
                    raise ValueError(f"数据库表中缺少列：{col}")

                if sql_type != db_type and not (pd.api.types.is_datetime64_any_dtype(sql_type) and pd.api.types.is_datetime64_any_dtype(db_type)):
                    raise ValueError(f"列 '{col}' 的数据类型不匹配。数据库类型：{db_type}，DataFrame 类型：{sql_type}")
        else:
            if type(data).__name__ != self.tables[table_name]:
                raise TypeError(f"数据类型不匹配，记录的 'data' 列的类型为 {self.tables[table_name]}，"
                                f"但插入的数据类型为 {type(data).__name__}。")

    def _create_table_from_data(self, data: Any, key_fields: Fields, common_fields: Fields) -> None:
        """
        根据 data 自动创建 SQLite 表。
        """
        table_name = self._get_table_name(common_fields=common_fields)

        cols = set([f'"{k}" {_python_type_to_sqlite_type(type(v).__name__)}' for k, v in key_fields.items()])
        if not isinstance(data, pd.DataFrame):
            cols.add(f'"data" {_python_type_to_sqlite_type(type(data).__name__)}')
        else:
            for col_name, dtype in data.dtypes.items():
                cols.add(f'"{col_name}" {_pandas_dtype_to_sqlite_type(dtype)}')
        primary_keys = ", ".join([f'"{k}"' for k in key_fields.keys()])
        if not primary_keys.strip() == "": primary_keys = f"PRIMARY KEY ({primary_keys})"

        col_definitions = ",\n".join(cols)
        if not col_definitions.strip() == "" and not primary_keys.strip() == "": col_definitions += ","

        sql = f'CREATE TABLE IF NOT EXISTS "{table_name}" (\n{col_definitions}\n {primary_keys});'

        logging.info("Generated SQL:")
        logging.info(sql)

        curr = self._get_cursor()
        with self._tx():
            curr.execute(sql)
            self.tables[table_name] = self._set_table_info(data, common_fields=common_fields)

    def _set_table_info(self, data: Any, common_fields: Fields) -> str | Dict[str, str]:
        """
        把 data 的类型存储起来。
        """
        table_name = self._get_table_name(common_fields=common_fields)
        cur = self._get_cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS DataFrame_infos (
            table_name TEXT,
            column_name TEXT,
            data_type TEXT,
            PRIMARY KEY (table_name, column_name)
        );
        """)
        cur.fetchall()
        cur.execute(f"""
        INSERT OR REPLACE INTO DataFrame_infos (table_name, column_name, data_type)
        VALUES (?, ?, ?);            
        """, (table_name, "data", type(data).__name__))
        
        if isinstance(data, pd.DataFrame):
            cur.execute(f"PRAGMA table_info({table_name});")
            cols = cur.fetchall()
            for col, dtype in data.dtypes.items():
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

    def _get_table_info(self, common_fields: Fields) -> str | Dict[str, str]:
        table_name = self._get_table_name(common_fields=common_fields)
        cur = self._get_cursor()
        try:
            cur.execute(f"""
            SELECT * FROM DataFrame_infos
            WHERE table_name = ? AND column_name = 'data';
            """, (table_name,))
        except sqlite3.OperationalError:
            return ""
        rows = cur.fetchall()
        if len(rows) == 0: return ""
        elif len(rows) == 1:
            data_type = rows[0]['data_type']
            if data_type == "DataFrame":
                cur.execute(f"""
                SELECT column_name, data_type FROM DataFrame_infos
                WHERE table_name = ? AND column_name != 'data';
                """, (table_name,))
                rows = cur.fetchall()
                dtype_map = {row['column_name']: row['data_type'] for row in rows}
                return dtype_map
            else:
                return data_type
        else:
            raise ValueError(f"查询到多条数据，无法唯一确定表信息：{rows}")

@dataclass(frozen=True)
class CacheConfig:
    table_basename: str
    db_path: str
    key_fields: Tuple[str, ...]
    common_fields: Tuple[str, ...]
    except_fields: Tuple[str, ...]

def common_cache(
    table_basename: str = "",
    db_path: str = "history.db",
    key_fields: Tuple[str, ...] = (),
    common_fields: Tuple[str, ...] = (),
    except_fields: Tuple[str, ...] = (),
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
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
        except_fields=except_fields
    )

    if not cfg.db_path:
        return lambda func: func  # 不启用缓存，直接返回原函数

    def deco(func: Callable[..., pd.DataFrame]) -> Callable[..., pd.DataFrame]:
        # 注册 DB（按 模块名:BaseDB）
        reg_key = f"{func.__module__}:{func.__qualname__}"
        sig = inspect.signature(func)

        table_basename = cfg.table_basename if cfg.table_basename else func.__name__
        if reg_key not in DB_CONNECTIONS:
            DB_CONNECTIONS[reg_key] = CommonDB(
                table_basename=table_basename,
                db_path=cfg.db_path
            )


        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            argmap: Dict[str, Any] = dict(bound.arguments)

            if not cfg.common_fields:
                common_fields = {}
                for each in argmap.keys():
                    if each not in cfg.key_fields and each not in cfg.except_fields and each != "self":
                        common_fields[each] = argmap[each]
            else:
                common_fields = {k: argmap[k] for k in cfg.common_fields if k not in cfg.except_fields}

            if not cfg.except_fields:
                except_fields = {}
                for each in argmap.keys():
                    if each not in cfg.key_fields and each not in common_fields and each != "self":
                        except_fields[each] = argmap[each]
            else:
                except_fields = {k: argmap[k] for k in cfg.except_fields}

            if "self" in argmap:
                func_dec = lambda *args, **fkwargs: func(argmap["self"], *args, **fkwargs)
            else:
                func_dec = func

            db = DB_CONNECTIONS[reg_key]
            if not isinstance(db, CommonDB):
                raise TypeError(f"DB_CONNECTIONS[{reg_key}] 必须是 CommonDB 类型")
            return db.fetch(
                key_fields={k: argmap[k] for k in cfg.key_fields},
                common_fields=common_fields,
                except_fields=except_fields,
                callback=func_dec
            )

        return wrapper

    return deco




__all__ = ["CommonDB", "DB_CONNECTIONS", "common_cache"]
