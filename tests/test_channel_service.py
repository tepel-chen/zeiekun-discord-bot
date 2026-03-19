import asyncio
import importlib
import sys
import types
from pathlib import Path
from unittest.mock import AsyncMock


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


channel_service = importlib.import_module("services.channel_service")


def test_normalize_category():
    assert channel_service.normalize_category("reversing") == "Rev"
    assert channel_service.normalize_category("miscellaneous") == "Misc"
    assert channel_service.normalize_category("web") == "Web"
    assert channel_service.normalize_category("pwn") == "Pwn"


def test_get_participant_count_excludes_bots():
    members = [
        types.SimpleNamespace(bot=False),
        types.SimpleNamespace(bot=True),
        types.SimpleNamespace(bot=False),
    ]
    channel = types.SimpleNamespace(members=members)

    assert channel_service.get_participant_count(channel) == 2


def test_ensure_category_returns_existing_category():
    existing = types.SimpleNamespace(name="CTF")
    guild = types.SimpleNamespace(
        categories=[existing],
        create_category=AsyncMock(),
    )

    result = asyncio.run(channel_service.ensure_category(guild, "CTF"))

    assert result is existing
    guild.create_category.assert_not_awaited()


def test_ensure_category_creates_category_when_missing():
    created = types.SimpleNamespace(name="ARCHIVE")
    guild = types.SimpleNamespace(
        categories=[],
        create_category=AsyncMock(return_value=created),
    )

    result = asyncio.run(channel_service.ensure_category(guild, "ARCHIVE"))

    assert result is created
    guild.create_category.assert_awaited_once_with("ARCHIVE")


def test_create_private_channel_sets_expected_overwrites():
    me = object()
    created_channel = object()
    guild = types.SimpleNamespace(
        default_role=object(),
        me=me,
        create_text_channel=AsyncMock(return_value=created_channel),
    )
    category = object()

    result = asyncio.run(channel_service.create_private_channel(guild, "ctf-test", category))

    assert result is created_channel
    guild.create_text_channel.assert_awaited_once()
    kwargs = guild.create_text_channel.await_args.kwargs
    overwrites = kwargs["overwrites"]

    assert kwargs["name"] == "ctf-test"
    assert kwargs["category"] is category
    assert guild.default_role in overwrites
    assert overwrites[guild.default_role].view_channel is False
    assert me in overwrites
    assert overwrites[me].view_channel is True
    assert overwrites[me].send_messages is True
    assert overwrites[me].read_message_history is True


def test_allocate_channel_name_appends_suffix_for_conflicts():
    channels = [
        types.SimpleNamespace(name="ctf-test"),
        types.SimpleNamespace(name="ctf-test-2"),
    ]

    assert channel_service.allocate_channel_name(channels, "test") == "ctf-test-3"


def test_filter_threads_applies_category_and_solved_filters():
    threads = [
        types.SimpleNamespace(name="warmup [Web]"),
        types.SimpleNamespace(name="✅ crypto-1 [Crypto]"),
        types.SimpleNamespace(name="✅ web-2 [Web]"),
    ]

    filtered = channel_service.filter_threads(threads, category="Web", solved=True)

    assert [thread.name for thread in filtered] == ["✅ web-2 [Web]"]


def test_build_missing_search_response():
    assert channel_service.build_missing_search_response("Web", True) == "❌ カテゴリ「Web」(解決済み)のスレッドが見つかりません。"
    assert channel_service.build_missing_search_response(None, None) == "❌ スレッドが見つかりません。"
