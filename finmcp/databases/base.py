import sqlite3
from contextlib import contextmanager
from typing import Dict

class BaseDB:

    table_basename: str
    connection: sqlite3.Connection

    @contextmanager
    def _tx(self):
        """简单事务封装，保证一组操作要么全成功，要么全失败。"""
        try:
            self.connection.execute("BEGIN IMMEDIATE")
            yield
            self.connection.commit()
        except Exception as e:
            self.connection.rollback()
            raise e

    def __del__(self):
        self.close()
    
    def close(self):
        if self.connection:
            self.connection.commit()
            self.connection.close()

__all__ = ["BaseDB"]
