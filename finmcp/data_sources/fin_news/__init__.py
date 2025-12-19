from .base import NewsDataSource
import pkgutil
import importlib
import inspect
from pathlib import Path
from typing import Type, Dict

DATASOURCES: Dict[str, Type[NewsDataSource]] = {}

import dotenv
dotenv.load_dotenv()

def _discover_datasource_classes():
    """
    扫描当前包下所有 .py 模块，找到所有继承 NewsDataSource 的子类，
    填充到 DATASOURCES 里。
    """
    package_name = __name__
    package_path = Path(__file__).parent

    for module_info in pkgutil.iter_modules([str(package_path)]):
        mod_name = module_info.name

        if mod_name in ("base", "__init__") or mod_name.startswith("_"):
            continue

        full_name = f"{package_name}.{mod_name}"
        module = importlib.import_module(full_name)

        for attr_name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, NewsDataSource) and obj is not NewsDataSource:
                key = getattr(obj, "name", obj.__name__)
                if key == "base":
                    print(f"Warning: NewsDataSource subclass in {full_name} has reserved name 'base'.")
                    print("Please rename it to avoid conflicts.")
                    print("Skipping registration of this class.")
                    continue
                if key in DATASOURCES:
                    raise ValueError(f"Duplicate NewsDataSource name detected: {key} in {obj.__name__} and {DATASOURCES[key].__name__}")
                DATASOURCES[key] = obj

_discover_datasource_classes()

__all__ = [
    "NewsDataSource",
    "DATASOURCES",
]