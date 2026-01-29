if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.append(Path(__file__).parent.parent.as_posix())

def test_datasource_parse_datetime():
    from fintools.data_sources import DataSource
    from datetime import datetime, date, timedelta
    import time

    ds = DataSource()

    # Test datetime input
    dt_input = datetime(2023, 1, 1, 12, 0, 0)
    assert ds._parse_datetime(dt_input) == dt_input.astimezone()

    # Test date input
    date_input = date(2023, 1, 1)
    expected_dt = datetime(2023, 1, 1, 0, 0, 0).astimezone()
    assert ds._parse_datetime(date_input) == expected_dt

    # Test integer timestamp input (seconds)
    ts_input = int(time.mktime(dt_input.timetuple()))
    assert ds._parse_datetime(ts_input) == dt_input.astimezone()

    # Test integer timestamp input (microseconds)
    ts_input_us = ts_input * 1000000
    assert ds._parse_datetime(ts_input_us) == dt_input.astimezone()

    # Test string input in various formats
    str_inputs = [
        "2023-01-01 12:00:00",
        "2023/01/01 12:00:00",
        "20230101120000",
    ]
    for str_input in str_inputs:
        assert ds._parse_datetime(str_input) == dt_input.astimezone()

    str_inputs_date = [
        "2023-01-01",
        "2023/01/01",
        "20230101"
    ]
    for str_input in str_inputs_date:
        assert ds._parse_datetime(str_input) == expected_dt.astimezone()

    # Test invalid string format
    try:
        ds._parse_datetime("01-01-2023")
    except ValueError as e:
        assert str(e) == "String datetime format not recognized: 01-01-2023"

    # Test unsupported type
    try:
        ds._parse_datetime(12.34)
    except TypeError as e:
        assert str(e) == "Unsupported datetime input type: <class 'float'>"

def test_utils_parse_datetime():
    from fintools.databases.utils import parse_datetime
    from datetime import datetime, date, timedelta
    import time

    # Test datetime input
    dt_input = datetime(2023, 1, 1, 12, 0, 0)
    assert parse_datetime(dt_input) == dt_input.astimezone()

    # Test date input
    date_input = date(2023, 1, 1)
    expected_dt = datetime(2023, 1, 1, 0, 0, 0).astimezone()
    assert parse_datetime(date_input) == expected_dt

    # Test integer timestamp input (seconds)
    ts_input = int(time.mktime(dt_input.timetuple()))
    assert parse_datetime(ts_input) == dt_input.astimezone()

    # Test integer timestamp input (microseconds)
    ts_input_us = ts_input * 1000000
    assert parse_datetime(ts_input_us) == dt_input.astimezone()

    # Test string input in various formats
    str_inputs = [
        "2023-01-01 12:00:00",
        "2023/01/01 12:00:00",
        "20230101120000",
    ]
    for str_input in str_inputs:
        assert parse_datetime(str_input) == dt_input.astimezone()
    
    str_inputs_date = [
        "2023-01-01",
        "2023/01/01",
        "20230101"
    ]
    for str_input in str_inputs_date:
        assert parse_datetime(str_input) == expected_dt.astimezone()

    # Test invalid string format
    try:
        parse_datetime("01-01-2023")
    except ValueError as e:
        assert str(e) == "String datetime format not recognized: 01-01-2023"

    # Test unsupported type
    try:
        parse_datetime(12.34)
    except TypeError as e:
        assert str(e) == "Unsupported datetime input type: <class 'float'>"

if __name__ == "__main__":
    test_datasource_parse_datetime()
    test_utils_parse_datetime()
    print("All tests passed.")