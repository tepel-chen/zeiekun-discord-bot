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


def test_tokyo_now_returns_naive_datetime_in_tokyo_timezone(monkeypatch):
    class FakeDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            assert tz == time_service.TOKYO
            return cls(2026, 3, 20, 9, 0, tzinfo=tz)

    monkeypatch.setattr(time_service, "datetime", FakeDateTime)

    assert time_service.tokyo_now() == datetime(2026, 3, 20, 9, 0)


def test_validate_time_range_rejects_end_before_start():
    try:
        time_service.validate_time_range(
            datetime(2026, 3, 21, 12, 0),
            datetime(2026, 3, 20, 10, 0),
        )
    except time_service.TimeParseError as exc:
        assert str(exc) == "終了時刻は開始時刻以降にしてください。"
    else:
        raise AssertionError("TimeParseError was not raised")
