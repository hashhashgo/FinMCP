from .base import BaseDB
from typing import Dict

DB_CONNECTIONS: Dict[str, BaseDB] = {}

__all__ = ["BaseDB", "DB_CONNECTIONS"]
