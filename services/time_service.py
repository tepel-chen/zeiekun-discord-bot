from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

import dateparser


TOKYO = ZoneInfo("Asia/Tokyo")


class TimeParseError(ValueError):
    pass


def parse_datetime_input(value: str, relative_base: datetime | None = None) -> datetime:
    base = relative_base or datetime.now(TOKYO)
    settings = {
        "TIMEZONE": "Asia/Tokyo",
        "TO_TIMEZONE": "Asia/Tokyo",
        "RETURN_AS_TIMEZONE_AWARE": True,
        "PREFER_DATES_FROM": "future",
        "RELATIVE_BASE": base,
    }
    parsed = dateparser.parse(value.strip(), settings=settings)
    if parsed is None:
        raise TimeParseError(
            "時刻を解釈できませんでした。`2026-03-20 10:00`, `2026-03-20 20:00:00`, `tomorrow 9pm` のように指定してください。"
        )

    return parsed.astimezone(TOKYO).replace(tzinfo=None)


def to_discord_timestamp(value: datetime, style: str = "F") -> str:
    return f"<t:{int(value.replace(tzinfo=TOKYO).timestamp())}:{style}>"


def format_datetime(value: Optional[datetime]) -> str:
    if value is None:
        return "未設定"
    return to_discord_timestamp(value, "F")


def format_hour_delta(target: Optional[datetime], now: datetime) -> str:
    if target is None:
        return "未設定"
    return to_discord_timestamp(target, "R")


def build_time_response(name: str, start_time: Optional[datetime], end_time: Optional[datetime], now: datetime) -> str:
    return (
        f"CTF: {name}\n"
        f"開始: {format_datetime(start_time)} ({format_hour_delta(start_time, now)})\n"
        f"終了: {format_datetime(end_time)} ({format_hour_delta(end_time, now)})\n"
        f"現在: {to_discord_timestamp(now, 'F')}"
    )
