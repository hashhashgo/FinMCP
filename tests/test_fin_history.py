if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.append(Path(__file__).parent.parent.as_posix())

from finmcp.data_sources.fin_history import DATASOURCES, DataType, DataFrequency
from datetime import datetime, date, timedelta
import dotenv
dotenv.load_dotenv()

def test_tushare_history():
    tu = DATASOURCES['tushare']()
    df_tu = tu.history("600519.SH", type=DataType.STOCK, start=datetime.now() - timedelta(days=365*10), end=datetime.now(), freq=DataFrequency.DAILY)
    assert len(df_tu)

def test_yahoo_finance_history():
    yf = DATASOURCES['yahoo_finance']()
    df_yf = yf.history("AAAA", type=DataType.STOCK, start=datetime.now() - timedelta(days=365*10), end=datetime.now(), freq=DataFrequency.DAILY)
    assert len(df_yf)
    df_yf = yf.history("AAAA", type=DataType.STOCK, start=datetime.now() - timedelta(days=5), end=datetime.now(), freq=DataFrequency.MINUTE60)
    assert len(df_yf)

def test_investing_history():
    ic = DATASOURCES['investing.com']()
    df_ic = ic.history("usd-cny", type=DataType.FOREX, start=datetime.now() - timedelta(days=365*10), end=datetime.now(), freq=DataFrequency.DAILY)
    assert len(df_ic)
    df_ic = ic.history("usd-cny", type=DataType.FOREX, start=datetime.now() - timedelta(days=5), end=datetime.now(), freq=DataFrequency.MINUTE60)
    assert len(df_ic)

def test_nanhua_history():
    nh = DATASOURCES['nanhua']()
    df_nh = nh.history("PP_NH", type=DataType.COMMODITY, start=datetime.now() - timedelta(days=365*10), end=datetime.now(), freq=DataFrequency.DAILY)
    assert len(df_nh)
    df_nh = nh.history("PP_NH", type=DataType.COMMODITY, start=datetime.now() - timedelta(days=5), end=datetime.now(), freq=DataFrequency.MINUTE60)
    assert len(df_nh)

if __name__ == "__main__":
    test_tushare_history()
    test_yahoo_finance_history()
    test_investing_history()
    test_nanhua_history()