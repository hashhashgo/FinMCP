if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.append(Path(__file__).parent.parent.as_posix())

from fintools.api.F.fin_history import get_data, list_indices, UnderlyingType, DataFrequency
from datetime import datetime, date, timedelta
import dotenv
dotenv.load_dotenv()

def test_get_data_tushare():
    df_tu = get_data("tushare", "510300.SH", UnderlyingType.ETF, DataFrequency.DAILY, indicators=['macd', 'rsi', 'boll'])
    assert not df_tu.empty


if __name__ == "__main__":
    test_get_data_tushare()