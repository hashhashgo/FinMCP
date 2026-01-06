from datetime import date, datetime, timedelta
from lxml import etree
import pandas as pd
import requests
import random
import json
import os

from .base import ReportDataSource, SortingMethod

from fintools.databases.history_db import history_cache
from fintools.databases.common_db import common_cache

class EastMoneyReportDataSource(ReportDataSource):
    """
    Data source for East Money financial reports.
    """

    name = "eastmoney"
    BASE_URL = "https://search-api-web.eastmoney.com/search/jsonp"
    PAGE_SIZE = 100
    COMMON_PARAMS = {
        "cb": f"jQuery35100489329{random.randint(0,int(1e10-1))}_{int(datetime.now().timestamp() * 1000)}",
        "param": {
            "uid": "",
            "keyword": "????",
            "type":["researchReport"], 
            "client": "web", 
            "clientType": "web",
            "clientVersion": "curr",
            "param": {
                "researchReport": {
                    "client":"web",
                    "pageSize":100,
                    "pageIndex":1
                }
            }
        },
        "_": int(datetime.now().timestamp() * 1000 + random.randint(0,50))
    }
    COMMON_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:146.0) Gecko/20100101 Firefox/146.0",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.5",
    }

    @history_cache(
        table_basename="eastmoney_report",
        db_path=os.getenv("FINTOOLS_DB", ""),
        key_fields=("symbol", ),
        common_fields=(),
        except_fields=()
    )
    def list_reports(
        self,
        symbol: str,
        start: str | datetime | date | int = 0,
        end: str | datetime | date | int = datetime.now()
    ) -> pd.DataFrame:
        params = self.COMMON_PARAMS.copy()
        params["param"]["keyword"] = symbol
        params["param"]["param"]["researchReport"]["pageSize"] = self.PAGE_SIZE
        start_dt = self._parse_datetime(start)
        end_dt = self._parse_datetime(end)
        total = 1000
        index = 1
        everything = []
        while index * self.PAGE_SIZE <= total:
            params["param"]["param"]["researchReport"]["pageIndex"] = index
            get_params = {
                "cb": params["cb"],
                "param": json.dumps(params["param"], separators=(',', ':')),
                "_": params["_"]
            }
            res = requests.get(
                url = self.BASE_URL,
                params = get_params,
                headers = self.COMMON_HEADERS
            )
            res.raise_for_status()
            l = res.text.find("(")
            r = res.text.rfind(")")
            content = json.loads(res.text[l+1:r])
            total = content.get("hitsTotal", 0)
            data = content.get("result", {}).get("researchReport", [])
            index += 1
            if len(data) == 0: break
            everything.extend(data)
            if datetime.strptime(data[-1]['date'], "%Y-%m-%d %H:%M:%S").astimezone() < start_dt:
                break
        df = pd.DataFrame(everything)
        if not df.empty:
            df['title'] = df['title'].apply(self._remove_html_tags)
            df['date'] = pd.to_datetime(df['date']).dt.tz_localize('Asia/Shanghai')
            df = df[(df['date'] >= start_dt) & (df['date'] < end_dt)]
            df = df[(df['title'].str.contains(symbol))]
        return df

    @common_cache(
        table_basename="eastmoney_report_details",
        db_path=os.getenv("FINTOOLS_DB", ""),
        key_fields=("code", ),
        common_fields=(),
        except_fields=()
    )
    def report_details(self, code: str) -> str:
        res = requests.get(
            url=f"https://data.eastmoney.com/report/zw_stock.jshtml?infocode={code}",
            headers=self.COMMON_HEADERS
        )
        res.raise_for_status()
        tree = etree.HTML(res.text)
        main_block = tree.xpath(r'//div[@id="ctx-content"][@class="ctx-content"]')[0]
        return etree.tostring(main_block, encoding='utf-8', method='text').decode('utf-8').strip()
    
    def _remove_html_tags(self, text: str) -> str:
        parser = etree.HTMLParser()
        tree = etree.fromstring(f"<div>{text}</div>", parser)
        return etree.tostring(tree, encoding='utf-8', method='text').decode('utf-8').strip()

    def _map_sorting_method(self, sorting: SortingMethod) -> str:
        if sorting == SortingMethod.DEFAULT:
            return "default"
        elif sorting == SortingMethod.RELEVANCE:
            return "score"
        elif sorting == SortingMethod.DATE_ASCENDING or sorting == SortingMethod.DATE_DESCENDING:
            return "time"
        else:
            raise ValueError(f"Unsupported sorting method: {sorting}")
