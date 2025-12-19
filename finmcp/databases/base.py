import json
import pandas as pd
import sqlite3
import tzlocal
from hashlib import sha1
from contextlib import contextmanager
from typing import Dict, Optional, Any
from datetime import datetime, date, timedelta

from contextvars import ContextVar


class BaseDB:

    table_basename: str
    db_path: str
    connection: ContextVar[Optional[sqlite3.Connection]] = ContextVar(
        "connection", default=None
    )

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


Fields = Dict[str, int | str | datetime | float | bool]

__all__ = ["BaseDB", "Fields"]
