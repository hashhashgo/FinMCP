if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.append(Path(__file__).parent.parent.as_posix())

import requests

old_init = requests.sessions.Session.__init__

def _new_init(self, *args, **kwargs):
    old_init(self, *args, **kwargs)
    #  不支持 br
    self.headers["Accept-Encoding"] = "gzip,deflate"

requests.sessions.Session.__init__ = _new_init

from finmcp.databases.common_db import common_cache
from finmcp.databases.history_db import history_cache

import os
import dotenv
import pandas as pd
import tushare

dotenv.load_dotenv(dotenv.find_dotenv())
pro = tushare.pro_api(os.getenv("TUSHARE_API_KEY", ""))

@common_cache(
    table_basename = "index_basic",
    db_path = os.getenv("DB_PATH", "")
)
def index_basic() -> pd.DataFrame:
    """
    Get basic information of all indexes.

    Returns:
    A DataFrame containing index basic information.
    """
    df = pro.index_basic()
    return df

def test_common_cache():
    df = index_basic()
    assert not df.empty


if __name__ == "__main__":
    import time, tqdm
    start = time.time()
    for _ in tqdm.trange(200): test_common_cache()
    end = time.time()
    print(f"Elapsed time for 200 runs: {end - start} seconds")

    start = time.time()
    for _ in tqdm.trange(200): pro.index_basic()
    end = time.time()
    print(f"Elapsed time for clearing cache 200 times: {end - start} seconds")