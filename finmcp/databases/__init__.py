from .base import BaseDB
from typing import Dict
import threading

_tls = threading.local()
if not hasattr(_tls, "db_connections"):
    _tls.db_connections = {}

DB_CONNECTIONS: Dict[str, BaseDB] = _tls.db_connections

__all__ = ["BaseDB", "DB_CONNECTIONS"]
