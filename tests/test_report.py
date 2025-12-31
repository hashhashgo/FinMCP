if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.append(Path(__file__).parent.parent.as_posix())

from finmcp.data_sources.fin_report import DATASOURCES
from datetime import datetime, date, timedelta
# import dotenv
# dotenv.load_dotenv()

def test_eastmoney_report_details():
    ds = DATASOURCES["eastmoney"]()
    content = ds.report_details("AP202508261734580053")
    assert "2025第二季度公司销售肉猪2425.2万头" in content

def test_eastmoney_report_list():
    ds = DATASOURCES["eastmoney"]()
    df = ds.list_reports("TCL科技")
    assert not df.empty

if __name__ == "__main__":
    test_eastmoney_report_list()
    test_eastmoney_report_details()