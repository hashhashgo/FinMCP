import sqlite3
from hashlib import sha1
from contextlib import contextmanager
from typing import Dict, Optional, Any, List
from datetime import datetime, date, timedelta
from pyparsing import ABC, abstractmethod

from contextvars import ContextVar


Fields = Dict[str, int | str | datetime | float | bool]

class BaseDB(ABC):

    table_basename: str
    db_path: str
    connection: ContextVar[Optional[sqlite3.Connection]] = ContextVar(
        "connection", default=None
    )
    tables: Dict[str, Any] = {}

    def list_all_cached(self, common_fields: Fields = {}) -> List[Any]:
        """
        列出所有缓存的数据条目。

        参数：
            common_fields: 公共字段，如 freq 等，common_fields 作为表名的一部分
        返回值：
            符合条件的数据列表，类型为 pd.DataFrame。
        """
        table_name = self._get_table_name(common_fields=common_fields)

        if not self.tables.get(table_name): self.tables[table_name] = self._get_table_info(common_fields=common_fields)
        if not self.tables.get(table_name):
            return []

        cur = self._get_cursor()

        cur.execute(f"PRAGMA table_info({table_name});")
        primary_keys = [row['name'] for row in cur.fetchall() if row['pk'] == 1]

        cur.execute(f"""
            SELECT {", ".join(primary_keys)} FROM {table_name};
        """)
        return cur.fetchall()

    def _connect(self) -> sqlite3.Connection:
        conn = self.connection.get()
        if not isinstance(conn, sqlite3.Connection):
            self.connection.set(
                sqlite3.connect(
                    self.db_path,
                    check_same_thread=False,
                )
            )
            conn = self.connection.get()
            assert isinstance(conn, sqlite3.Connection), "数据库连接未正确建立。"
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def _tx(self):
        """简单事务封装，保证一组操作要么全成功，要么全失败。"""
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            yield
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e

    def _get_cursor(self):
        conn = self._connect()
        return conn.cursor()

    def __del__(self):
        self.close()
    
    def close(self):
        conn = self.connection.get()
        if conn:
            conn.commit()
            conn.close()
            self.connection.set(None)
    
    def _get_table_name(self, common_fields: Fields) -> str:
        hashed_name = sha1(("-".join([str(v) for v in common_fields.values()])).encode()).hexdigest()
        return f"{self.table_basename}_{hashed_name}"

    @abstractmethod
    def _set_table_info(self, data: Any, common_fields: Fields) -> str | Dict[str, str] | bool:
        raise NotImplementedError

    @abstractmethod
    def _get_table_info(self, common_fields: Fields) -> str | Dict[str, str] | bool:
        raise NotImplementedError


__all__ = ["BaseDB", "Fields"]
