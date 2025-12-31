if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.append(Path(__file__).parent.parent.as_posix())

from fintools.data_sources.fin_news.eastmoney import EastMoneyNewsDataSource
from datetime import datetime, date, timedelta
# import dotenv
# dotenv.load_dotenv()

def test_eastmoney_news_details():
    ds = EastMoneyNewsDataSource()
    content = ds.news_details("202512163593162017")
    assert "统计显示，上证50指数ETF今日合计成交额28.98亿元" in content

def test_eastmoney_news_list():
    ds = EastMoneyNewsDataSource()
    df = ds.list_news("TCL科技", start="2000-01-01", end=datetime.now())
    assert not df.empty

if __name__ == "__main__":
    test_eastmoney_news_list()
    test_eastmoney_news_details()