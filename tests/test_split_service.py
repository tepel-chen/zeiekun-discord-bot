import asyncio
import importlib
import types
from datetime import datetime
from unittest.mock import AsyncMock, Mock


split_module = importlib.import_module("services.split_service")


class FakeTextChannel:
    def __init__(self, channel_id, name, category="cat"):
        self.id = channel_id
        self.name = name
        self.category = category
        self.edit = AsyncMock()
        self.send = AsyncMock()
        self.set_permissions = AsyncMock()
        self.delete = AsyncMock()


def test_should_split_channel():
    start = datetime(2026, 3, 20, 18, 0)
    assert split_module.should_split_channel(start, datetime(2026, 3, 20, 15, 0)) is True
    assert split_module.should_split_channel(start, datetime(2026, 3, 20, 14, 59)) is False


def test_resolve_target_channel_id(monkeypatch):
    service = split_module.SplitService(bot=Mock(), logger=Mock())
    monkeypatch.setattr(
        split_module,
        "get_root_channel_record",
        lambda channel_id: types.SimpleNamespace(channel_id=10, split_completed=1),
    )
    monkeypatch.setattr(
        split_module,
        "get_team_channel_record",
        lambda root_channel_id, team_type: types.SimpleNamespace(channel_id=20),
    )

    assert service.resolve_target_channel_id(10, "play2win") == 20
    assert service.resolve_target_channel_id(10, "play4fun") == 10


def test_split_channel_success(monkeypatch):
    root_record = types.SimpleNamespace(
        channel_id=10,
        channel_name="ctf-demo",
        split_completed=0,
        team_mode="split",
        start_time=datetime(2026, 3, 20, 18, 0),
        end_time=datetime(2026, 3, 21, 18, 0),
    )
    play4fun_channel = FakeTextChannel(10, "ctf-demo")
    play2win_channel = FakeTextChannel(20, "ctf-demo-p2w")
    member1 = types.SimpleNamespace(id=1)
    member2 = types.SimpleNamespace(id=2)
    member3 = types.SimpleNamespace(id=3)
    member4 = types.SimpleNamespace(id=4)
    member5 = types.SimpleNamespace(id=5)
    member6 = types.SimpleNamespace(id=6)
    guild = types.SimpleNamespace(
        get_channel=lambda channel_id: {10: play4fun_channel, 20: play2win_channel}.get(channel_id),
        fetch_channel=AsyncMock(),
        get_member=lambda user_id: {
            1: member1,
            2: member2,
            3: member3,
            4: member4,
            5: member5,
            6: member6,
        }.get(user_id),
        id=123,
    )
    service = split_module.SplitService(bot=Mock(), logger=Mock())
    monkeypatch.setattr(split_module.discord, "TextChannel", FakeTextChannel)
    monkeypatch.setattr(split_module, "get_root_channel_record", lambda channel_id: root_record)
    monkeypatch.setattr(split_module, "get_team_channel_record", lambda root_channel_id, team_type: None)
    monkeypatch.setattr(
        split_module,
        "get_participants",
        lambda channel_id: [
            types.SimpleNamespace(user_id=1, participation_type="play2win"),
            types.SimpleNamespace(user_id=2, participation_type="play2win"),
            types.SimpleNamespace(user_id=3, participation_type="play2win"),
            types.SimpleNamespace(user_id=4, participation_type="play4fun"),
            types.SimpleNamespace(user_id=5, participation_type="play4fun"),
            types.SimpleNamespace(user_id=6, participation_type="play4fun"),
        ],
    )
    monkeypatch.setattr(split_module, "update_channel_record", Mock())
    monkeypatch.setattr(split_module, "add_channel_record", Mock())
    monkeypatch.setattr(split_module, "create_private_channel", AsyncMock(return_value=play2win_channel))

    asyncio.run(service.split_channel(guild, 10))

    play4fun_channel.edit.assert_awaited_once_with(name="ctf-demo-p4f")
    split_module.create_private_channel.assert_awaited_once()
    split_module.update_channel_record.assert_called_once()
    split_module.add_channel_record.assert_called_once()
    play4fun_channel.send.assert_awaited_once()
    play2win_channel.send.assert_awaited_once()


def test_reconcile_channel_state_merges_on_join_mode(monkeypatch):
    service = split_module.SplitService(bot=Mock(), logger=Mock())
    guild = types.SimpleNamespace()
    merge_channel = AsyncMock()
    service.merge_channel = merge_channel
    monkeypatch.setattr(
        split_module,
        "get_root_channel_record",
        lambda channel_id: types.SimpleNamespace(channel_id=10, team_mode="join", split_completed=1, start_time=None),
    )

    asyncio.run(service.reconcile_channel_state(guild, 10, datetime(2026, 3, 20, 10, 0)))

    merge_channel.assert_awaited_once_with(guild, 10)


def test_merge_channel_success(monkeypatch):
    root_record = types.SimpleNamespace(
        channel_id=10,
        channel_name="ctf-demo-p4f",
        split_completed=1,
        root_channel_id=10,
    )
    root_channel = FakeTextChannel(10, "ctf-demo-p4f")
    team_channel = FakeTextChannel(20, "ctf-demo-p2w")
    member1 = types.SimpleNamespace(id=1)
    member2 = types.SimpleNamespace(id=2)
    guild = types.SimpleNamespace(
        get_channel=lambda channel_id: {10: root_channel, 20: team_channel}.get(channel_id),
        fetch_channel=AsyncMock(),
        get_member=lambda user_id: {1: member1, 2: member2}.get(user_id),
    )
    service = split_module.SplitService(bot=Mock(), logger=Mock())
    monkeypatch.setattr(split_module.discord, "TextChannel", FakeTextChannel)
    monkeypatch.setattr(split_module, "get_root_channel_record", lambda channel_id: root_record)
    monkeypatch.setattr(split_module, "get_team_channels", lambda root_channel_id: [types.SimpleNamespace(channel_id=20)])
    monkeypatch.setattr(
        split_module,
        "get_participants",
        lambda channel_id: [
            types.SimpleNamespace(user_id=1, participation_type="play2win"),
            types.SimpleNamespace(user_id=2, participation_type="play4fun"),
        ],
    )
    monkeypatch.setattr(split_module, "update_channel_record", Mock())

    asyncio.run(service.merge_channel(guild, 10))

    root_channel.edit.assert_awaited_once_with(name="ctf-demo")
    assert root_channel.set_permissions.await_count == 2
    assert team_channel.set_permissions.await_count == 2
    root_channel.send.assert_awaited_once()


def test_split_channel_rolls_back_when_root_record_update_fails(monkeypatch):
    root_record = types.SimpleNamespace(
        channel_id=10,
        channel_name="ctf-demo",
        split_completed=0,
        team_mode="split",
        start_time=datetime(2026, 3, 20, 18, 0),
        end_time=datetime(2026, 3, 21, 18, 0),
    )
    play4fun_channel = FakeTextChannel(10, "ctf-demo")
    play2win_channel = FakeTextChannel(20, "ctf-demo-p2w")
    guild = types.SimpleNamespace(
        get_channel=lambda channel_id: {10: play4fun_channel, 20: play2win_channel}.get(channel_id),
        fetch_channel=AsyncMock(),
        get_member=lambda user_id: None,
        id=123,
    )
    service = split_module.SplitService(bot=Mock(), logger=Mock())
    monkeypatch.setattr(split_module.discord, "TextChannel", FakeTextChannel)
    monkeypatch.setattr(split_module, "get_root_channel_record", lambda channel_id: root_record)
    monkeypatch.setattr(split_module, "get_team_channel_record", lambda root_channel_id, team_type: None)
    monkeypatch.setattr(
        split_module,
        "get_participants",
        lambda channel_id: [
            types.SimpleNamespace(user_id=1, participation_type="play2win"),
            types.SimpleNamespace(user_id=2, participation_type="play2win"),
            types.SimpleNamespace(user_id=3, participation_type="play2win"),
            types.SimpleNamespace(user_id=4, participation_type="play4fun"),
            types.SimpleNamespace(user_id=5, participation_type="play4fun"),
            types.SimpleNamespace(user_id=6, participation_type="play4fun"),
        ],
    )
    monkeypatch.setattr(split_module, "add_channel_record", Mock())
    monkeypatch.setattr(split_module, "delete_channel_record", Mock())
    monkeypatch.setattr(split_module, "create_private_channel", AsyncMock(return_value=play2win_channel))
    monkeypatch.setattr(split_module, "update_channel_record", Mock(return_value=False))

    try:
        asyncio.run(service.split_channel(guild, 10))
    except RuntimeError as exc:
        assert str(exc) == "Failed to update root split record"
    else:
        raise AssertionError("RuntimeError was not raised")

    play4fun_channel.edit.assert_any_await(name="ctf-demo-p4f")
    play4fun_channel.edit.assert_any_await(name="ctf-demo")
    play2win_channel.delete.assert_awaited_once_with(reason="Rollback failed split setup")
    split_module.delete_channel_record.assert_called_once_with(20)
