if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.append(Path(__file__).parent.parent.as_posix())

from finmcp.data_sources.fin_news.eastmoney import EastMoneyNewsDataSource
from finmcp.data_sources import DataType
from datetime import datetime, date, timedelta

def test_eastmoney_news_details():
    ds = EastMoneyNewsDataSource()
    content = ds.news_details("202512163593162017")
    assert "统计显示，上证50指数ETF今日合计成交额28.98亿元" in content

def test_eastmoney_news_list():
    ds = EastMoneyNewsDataSource()
    df = ds.list_news("上证50", type=DataType.INDEX, start=datetime.now() - timedelta(days=30), end=datetime.now())
    assert not df.empty
    assert df['date'].max() < datetime.now().astimezone()
    assert df['date'].min() >= (datetime.now() - timedelta(days=30)).astimezone()

if __name__ == "__main__":
    test_eastmoney_news_details()
    test_eastmoney_news_list()