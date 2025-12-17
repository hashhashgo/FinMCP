from .base import BaseDB
from typing import Dict
from contextvars import ContextVar

_db_connections: ContextVar[Dict[str, BaseDB]] = ContextVar(
    "db_connections", default={}
)

class ContextDBConnections:
    def _get(self):
        conns = _db_connections.get()
        if conns is None:
            conns = {}
            _db_connections.set(conns)
        return conns

    def __getitem__(self, key):
        return self._get()[key]

    def __setitem__(self, key, value):
        self._get()[key] = value

    def __contains__(self, key):
        return key in self._get()


DB_CONNECTIONS = ContextDBConnections()

__all__ = ["BaseDB", "DB_CONNECTIONS"]
