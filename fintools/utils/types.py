from datetime import datetime, date, timezone
from dateutil import parser

def parse_datetime(datetime_input: str | datetime | date | int) -> datetime:
    datetime_output = None
    if isinstance(datetime_input, datetime):
        datetime_output = datetime_input
    elif isinstance(datetime_input, date):
        datetime_output = datetime(datetime_input.year, datetime_input.month, datetime_input.day)
    elif isinstance(datetime_input, int): # us or s timestamp
        if datetime_input > 9999999999999: datetime_input = datetime_input // 1000000
        datetime_output = datetime.fromtimestamp(datetime_input, tz=timezone.utc)
    elif isinstance(datetime_input, str):
        try:
            datetime_output = parser.isoparse(datetime_input)
        except Exception:
            pass
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y%m%d%H%M%S", "%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
            try:
                datetime_output = datetime.strptime(datetime_input, fmt)
                break
            except ValueError:
                continue
    else:
        raise TypeError(f"Unsupported datetime input type: {type(datetime_input)}")
    if not isinstance(datetime_output, datetime): raise ValueError(f"String datetime format not recognized: {datetime_input}")
    return datetime_output.astimezone()


__all__ = ["parse_datetime"]
