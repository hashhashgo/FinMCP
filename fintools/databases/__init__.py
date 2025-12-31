from .base import BaseDB, Fields
from typing import Dict

DB_CONNECTIONS: Dict[str, BaseDB] = {} 

__all__ = ["BaseDB", "Fields", "DB_CONNECTIONS"]
