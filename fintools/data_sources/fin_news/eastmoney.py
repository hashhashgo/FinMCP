from datetime import date, datetime, timedelta
from lxml import etree
import pandas as pd
import requests
import random
import json
import os

from .base import NewsDataSource, SortingMethod

from fintools.databases.history_db import history_cache
from fintools.databases.common_db import common_cache

class EastMoneyNewsDataSource(NewsDataSource):
    """
    Data source for East Money financial news.
    """

    name = "eastmoney"
    BASE_URL = "https://search-api-web.eastmoney.com/search/jsonp"
    PAGE_SIZE = 100
    COMMON_PARAMS = {
        "cb": f"jQuery35100489329{random.randint(0,int(1e10-1))}_{int(datetime.now().timestamp() * 1000)}",
        "param": {
            "uid": "",
            "keyword": "????",
            "type":["cmsArticleWebOld"], 
            "client": "web", 
            "clientType": "web",
            "clientVersion": "curr",
            "param": {
                "cmsArticleWebOld": {
                    "searchScope": "default",
                    "sort": "default", 
                    "pageIndex": 1,
                    "pageSize": 100,
                    "preTag": "<em>",
                    "postTag": "</em>"
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

    SUPPORTED_SORTING_METHODS = [SortingMethod.DEFAULT, SortingMethod.RELEVANCE, SortingMethod.DATE_ASCENDING, SortingMethod.DATE_DESCENDING]

    @history_cache(
        table_basename="eastmoney_news",
        db_path=os.getenv("FINTOOLS_DB", ""),
        key_fields=("symbol", ),
        common_fields=(),
        except_fields=()
    )
    def list_news(
        self,
        symbol: str,
        start: str | datetime | date | int = 0,
        end: str | datetime | date | int = datetime.now()
    ) -> pd.DataFrame:
        params = self.COMMON_PARAMS.copy()
        params["param"]["keyword"] = symbol
        params["param"]["param"]["cmsArticleWebOld"]["pageSize"] = self.PAGE_SIZE
        start_dt = self._parse_datetime(start)
        end_dt = self._parse_datetime(end)
        total = 1000
        index = 1
        everything = []
        while index * self.PAGE_SIZE <= total:
            params["param"]["param"]["cmsArticleWebOld"]["pageIndex"] = index
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
            data = content.get("result", {}).get("cmsArticleWebOld", [])
            index += 1
            if len(data) == 0: break
            everything.extend(data)
            if datetime.strptime(data[-1]['date'], "%Y-%m-%d %H:%M:%S").astimezone() < start_dt:
                break
        df = pd.DataFrame(everything)
        if not df.empty:
            df['title'] = df['title'].apply(self._remove_html_tags)
            df['content'] = df['content'].apply(self._remove_html_tags)
            df['date'] = pd.to_datetime(df['date']).dt.tz_localize('Asia/Shanghai')
            df = df[(df['date'] >= start_dt) & (df['date'] < end_dt)]
            df = df[(df['content'].str.contains(symbol)) | (df['title'].str.contains(symbol))]
        return df

    @common_cache(
        table_basename="eastmoney_news_details",
        db_path=os.getenv("FINTOOLS_DB", ""),
        key_fields=("code", ),
        common_fields=(),
        except_fields=()
    )
    def news_details(self, code: str) -> str:
        res = requests.get(
            url=f"https://finance.eastmoney.com/a/{code}.html",
            headers=self.COMMON_HEADERS
        )
        res.raise_for_status()
        tree = etree.HTML(res.text)
        main_block = tree.xpath(r'body/div[@class="main"]//div[@class="mainleft"]//div[@id="ContentBody"]/comment()[contains(., "文章主体")]/following-sibling::p')
        sl = []
        for block in main_block:
            sl.append(etree.tostring(block, encoding='utf-8', method='text').decode('utf-8').strip())
        return "\n".join(sl)
    
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
