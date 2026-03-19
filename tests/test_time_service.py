from datetime import datetime

from services import time_service


def test_parse_datetime_input():
    assert time_service.parse_datetime_input("2026-03-20 10:00") == datetime(2026, 3, 20, 10, 0)
    assert time_service.parse_datetime_input("2026-03-20 20:00:00") == datetime(2026, 3, 20, 20, 0, 0)
    assert time_service.parse_datetime_input(
        "tomorrow 9pm",
        relative_base=datetime(2026, 3, 19, 10, 0),
    ) == datetime(2026, 3, 20, 21, 0)


def test_build_time_response():
    message = time_service.build_time_response(
        "ctf-demo",
        datetime(2026, 3, 20, 10, 0),
        datetime(2026, 3, 21, 12, 0),
        datetime(2026, 3, 20, 9, 0),
    )

    assert "CTF: ctf-demo" in message
    assert "開始: <t:1773968400:F> (<t:1773968400:R>)" in message
    assert "終了: <t:1774062000:F> (<t:1774062000:R>)" in message
    assert "現在: <t:1773964800:F>" in message
