import asyncio
import importlib
import types
from datetime import datetime
from unittest.mock import AsyncMock, Mock

import discord
from discord import app_commands

from commands.context import CommandContext
from interaction_errors import UserFacingError


ctfconf_module = importlib.import_module("commands.ctfconf")
create_module = importlib.import_module("commands.create")
archive_module = importlib.import_module("commands.archive")
chal_module = importlib.import_module("commands.chal")
disclose_module = importlib.import_module("commands.disclose")
leave_module = importlib.import_module("commands.leave")
players_module = importlib.import_module("commands.players")
randomname_module = importlib.import_module("commands.randomname")
search_module = importlib.import_module("commands.search")
solve_module = importlib.import_module("commands.solve")
switchteam_module = importlib.import_module("commands.switchteam")
time_module = importlib.import_module("commands.time")


class FakeTextChannel:
    def __init__(self, channel_id=10, name="ctf-test", mention="#ctf-test", members=None):
        self.id = channel_id
        self.name = name
        self.mention = mention
        self.members = members or []
        self.send = AsyncMock()
        self.create_thread = AsyncMock()
        self.edit = AsyncMock()
        self.delete = AsyncMock()
        self.set_permissions = AsyncMock()
        self.threads = []
        self.archived_threads = lambda limit=None: _empty_async_iter()


class FakeThread:
    def __init__(self, name="thread", owner_id=999, mention="#thread"):
        self.name = name
        self.owner_id = owner_id
        self.mention = mention
        self.edit = AsyncMock()


def make_context():
    bot = types.SimpleNamespace(user=types.SimpleNamespace(id=999))
    logger = types.SimpleNamespace(exception=lambda *args, **kwargs: None)
    return CommandContext(
        bot=bot,
        logger=logger,
        category_name="CTF",
        archive_category="ARCHIVE",
        ctf_creator_role_id=1,
        ctf_role_id=2,
    )


def get_command(group, name: str):
    return next(command for command in group.commands if command.name == name)


def make_text_channel(channel_id=10, name="ctf-test", mention="#ctf-test", members=None):
    return FakeTextChannel(channel_id=channel_id, name=name, mention=mention, members=members)


def make_thread(name="thread", owner_id=999):
    return FakeThread(name=name, owner_id=owner_id)


async def _empty_async_iter():
    for item in []:
        yield item


def async_iter(items):
    async def _iterator():
        for item in items:
            yield item

    return _iterator()


def test_create_command_success(monkeypatch):
    monkeypatch.setattr(create_module.discord, "TextChannel", FakeTextChannel)
    monkeypatch.setattr(create_module.discord, "Thread", FakeThread)
    group = app_commands.Group(name="ctf", description="CTF")
    context = make_context()
    create_module.register_command(group, context)
    command = get_command(group, "create")

    created_channel = make_text_channel(
        channel_id=33,
        name="ctf-demo",
        mention="#ctf-demo",
        members=[types.SimpleNamespace(bot=False)],
    )
    interaction_channel = make_text_channel()
    guild = types.SimpleNamespace(id=44, text_channels=[], categories=[])
    interaction = types.SimpleNamespace(
        guild=guild,
        channel=interaction_channel,
        response=types.SimpleNamespace(defer=AsyncMock()),
        followup=types.SimpleNamespace(send=AsyncMock()),
    )

    monkeypatch.setattr(create_module, "ensure_category", AsyncMock(return_value="category"))
    monkeypatch.setattr(create_module, "create_private_channel", AsyncMock(return_value=created_channel))
    monkeypatch.setattr(create_module, "add_channel_record", lambda *args, **kwargs: None)

    asyncio.run(command.callback(interaction, "demo"))

    interaction.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
    interaction.followup.send.assert_awaited_once_with(
        content="#ctf-demo (ctf-demo)が作成されました",
        ephemeral=True,
    )
    interaction_channel.send.assert_awaited_once()
    view = interaction_channel.send.await_args.kwargs["view"]
    custom_ids = [item.custom_id for item in view.children]
    assert custom_ids == ["ctf_join:33:play2win", "ctf_join:33:play4fun"]


def test_create_command_rejects_bot_created_channel(monkeypatch):
    monkeypatch.setattr(create_module.discord, "TextChannel", FakeTextChannel)
    monkeypatch.setattr(create_module.discord, "Thread", FakeThread)
    group = app_commands.Group(name="ctf", description="CTF")
    create_module.register_command(group, make_context())
    command = get_command(group, "create")
    response = types.SimpleNamespace(send_message=AsyncMock(), defer=AsyncMock())
    interaction = types.SimpleNamespace(
        guild=types.SimpleNamespace(id=44, text_channels=[], categories=[]),
        channel=make_text_channel(channel_id=77),
        response=response,
        followup=types.SimpleNamespace(send=AsyncMock()),
    )
    monkeypatch.setattr(create_module, "is_bot_created_channel", lambda channel_id: True)

    try:
        asyncio.run(command.callback(interaction, "demo"))
    except UserFacingError as exc:
        assert str(exc) == "❌ このコマンドはbotによって作成されたチャンネル内では使用できません。"
    else:
        raise AssertionError("UserFacingError was not raised")
    response.defer.assert_not_awaited()


def test_create_command_stores_times(monkeypatch):
    monkeypatch.setattr(create_module.discord, "TextChannel", FakeTextChannel)
    monkeypatch.setattr(create_module.discord, "Thread", FakeThread)
    group = app_commands.Group(name="ctf", description="CTF")
    create_module.register_command(group, make_context())
    command = get_command(group, "create")

    created_channel = make_text_channel(channel_id=33, name="ctf-demo", mention="#ctf-demo")
    interaction = types.SimpleNamespace(
        guild=types.SimpleNamespace(id=44, text_channels=[], categories=[]),
        channel=make_text_channel(),
        response=types.SimpleNamespace(defer=AsyncMock()),
        followup=types.SimpleNamespace(send=AsyncMock()),
    )
    calls = []

    monkeypatch.setattr(create_module, "ensure_category", AsyncMock(return_value="category"))
    monkeypatch.setattr(create_module, "create_private_channel", AsyncMock(return_value=created_channel))
    monkeypatch.setattr(create_module, "add_channel_record", lambda *args, **kwargs: calls.append((args, kwargs)))

    asyncio.run(command.callback(interaction, "demo", "2026-03-20 10:00", "2026-03-21 12:00"))

    kwargs = calls[0][1]
    assert kwargs["start_time"] == datetime(2026, 3, 20, 10, 0)
    assert kwargs["end_time"] == datetime(2026, 3, 21, 12, 0)


def test_create_command_rejects_end_before_start(monkeypatch):
    monkeypatch.setattr(create_module.discord, "TextChannel", FakeTextChannel)
    monkeypatch.setattr(create_module.discord, "Thread", FakeThread)
    group = app_commands.Group(name="ctf", description="CTF")
    create_module.register_command(group, make_context())
    command = get_command(group, "create")

    interaction = types.SimpleNamespace(
        guild=types.SimpleNamespace(id=44, text_channels=[], categories=[]),
        channel=make_text_channel(),
        response=types.SimpleNamespace(defer=AsyncMock()),
        followup=types.SimpleNamespace(send=AsyncMock()),
    )

    monkeypatch.setattr(create_module, "ensure_category", AsyncMock(return_value="category"))
    monkeypatch.setattr(create_module, "create_private_channel", AsyncMock())
    monkeypatch.setattr(create_module, "add_channel_record", lambda *args, **kwargs: None)

    asyncio.run(command.callback(interaction, "demo", "2026-03-21 12:00", "2026-03-20 10:00"))

    interaction.followup.send.assert_awaited_once_with(
        "終了時刻は開始時刻以降にしてください。",
        ephemeral=True,
    )
    create_module.create_private_channel.assert_not_awaited()


def test_create_command_rolls_back_discord_channel_when_db_write_fails(monkeypatch):
    monkeypatch.setattr(create_module.discord, "TextChannel", FakeTextChannel)
    monkeypatch.setattr(create_module.discord, "Thread", FakeThread)
    group = app_commands.Group(name="ctf", description="CTF")
    context = make_context()
    create_module.register_command(group, context)
    command = get_command(group, "create")

    created_channel = make_text_channel(channel_id=33, name="ctf-demo", mention="#ctf-demo")
    interaction = types.SimpleNamespace(
        guild=types.SimpleNamespace(id=44, text_channels=[], categories=[]),
        channel=make_text_channel(),
        response=types.SimpleNamespace(defer=AsyncMock()),
        followup=types.SimpleNamespace(send=AsyncMock()),
    )

    monkeypatch.setattr(create_module, "ensure_category", AsyncMock(return_value="category"))
    monkeypatch.setattr(create_module, "create_private_channel", AsyncMock(return_value=created_channel))
    monkeypatch.setattr(create_module, "add_channel_record", Mock(side_effect=RuntimeError("db boom")))

    try:
        asyncio.run(command.callback(interaction, "demo"))
    except RuntimeError as exc:
        assert str(exc) == "db boom"
    else:
        raise AssertionError("RuntimeError was not raised")

    created_channel.delete.assert_awaited_once_with(reason="Rollback failed channel creation")


def test_archive_command_rejects_non_bot_channel(monkeypatch):
    monkeypatch.setattr(archive_module.discord, "TextChannel", FakeTextChannel)
    group = app_commands.Group(name="ctf", description="CTF")
    archive_module.register_command(group, make_context())
    command = get_command(group, "archive")
    interaction = types.SimpleNamespace(
        guild=types.SimpleNamespace(),
        channel=types.SimpleNamespace(id=1),
        response=types.SimpleNamespace(send_message=AsyncMock()),
    )
    monkeypatch.setattr(archive_module, "is_bot_created_channel", lambda channel_id: False)

    try:
        asyncio.run(command.callback(interaction))
    except UserFacingError as exc:
        assert str(exc) == "❌ このコマンドはbotによって作成されたチャンネルでのみ使用できます。"
    else:
        raise AssertionError("UserFacingError was not raised")


def test_archive_command_success(monkeypatch):
    monkeypatch.setattr(archive_module.discord, "TextChannel", FakeTextChannel)
    group = app_commands.Group(name="ctf", description="CTF")
    archive_module.register_command(group, make_context())
    command = get_command(group, "archive")
    channel = make_text_channel(channel_id=10, name="ctf-root")
    team_channel = make_text_channel(channel_id=20, name="ctf-team")
    interaction = types.SimpleNamespace(
        guild=types.SimpleNamespace(get_channel=lambda channel_id: {10: channel, 20: team_channel}.get(channel_id)),
        channel=channel,
        user=types.SimpleNamespace(mention="@user"),
        response=types.SimpleNamespace(send_message=AsyncMock()),
    )
    updates = []
    monkeypatch.setattr(archive_module, "is_bot_created_channel", lambda channel_id: True)
    monkeypatch.setattr(archive_module, "ensure_category", AsyncMock(return_value="archive-category"))
    monkeypatch.setattr(
        archive_module,
        "get_root_channel_record",
        lambda channel_id: types.SimpleNamespace(channel_id=10),
    )
    monkeypatch.setattr(
        archive_module,
        "get_team_channels",
        lambda root_channel_id: [types.SimpleNamespace(channel_id=20)],
    )
    monkeypatch.setattr(
        archive_module,
        "update_channel_record",
        lambda channel_id, **kwargs: updates.append((channel_id, kwargs)) or True,
    )

    asyncio.run(command.callback(interaction))

    channel.edit.assert_awaited_once_with(category="archive-category")
    team_channel.edit.assert_awaited_once_with(category="archive-category")
    assert updates == [(10, {"archived": 1}), (20, {"archived": 1})]
    interaction.response.send_message.assert_awaited_once_with(
        "✅ チャンネル #ctf-test をカテゴリー「ARCHIVE」へ移動しました。"
    )
    channel.send.assert_awaited_once_with("@user がこの CTF をアーカイブしました。")


def test_chal_command_success(monkeypatch):
    monkeypatch.setattr(chal_module.discord, "TextChannel", FakeTextChannel)
    group = app_commands.Group(name="ctf", description="CTF")
    chal_module.register_command(group, make_context())
    command = get_command(group, "chal")
    channel = make_text_channel()
    interaction = types.SimpleNamespace(
        channel=channel,
        user=types.SimpleNamespace(mention="@user"),
        response=types.SimpleNamespace(send_message=AsyncMock()),
    )
    monkeypatch.setattr(chal_module, "is_bot_created_channel", lambda channel_id: True)

    asyncio.run(command.callback(interaction, "web", "warmup"))

    channel.create_thread.assert_awaited_once_with(
        name="warmup [Web]",
        type=discord.ChannelType.public_thread,
        auto_archive_duration=60,
    )
    interaction.response.send_message.assert_awaited_once_with(
        "✅ @user さんがスレッドを作成しました",
        ephemeral=False,
    )


def test_leave_command_removes_participant_and_logs(monkeypatch):
    monkeypatch.setattr(leave_module.discord, "TextChannel", FakeTextChannel)
    group = app_commands.Group(name="ctf", description="CTF")
    leave_module.register_command(group, make_context())
    command = get_command(group, "leave")
    channel = make_text_channel(channel_id=10, name="ctf-root")
    interaction = types.SimpleNamespace(
        guild=types.SimpleNamespace(get_channel=lambda channel_id: {10: channel}.get(channel_id)),
        channel=channel,
        user=types.SimpleNamespace(id=42, mention="@user"),
        response=types.SimpleNamespace(send_message=AsyncMock()),
    )
    deleted = []
    monkeypatch.setattr(leave_module, "is_bot_created_channel", lambda channel_id: True)
    monkeypatch.setattr(
        leave_module,
        "get_participant",
        lambda channel_id, user_id: types.SimpleNamespace(user_id=user_id, participation_type="play4fun"),
    )
    monkeypatch.setattr(
        leave_module,
        "get_root_channel_record",
        lambda channel_id: types.SimpleNamespace(channel_id=10, split_completed=0),
    )
    monkeypatch.setattr(leave_module, "get_team_channel_record", lambda root_channel_id, team_type: None)
    monkeypatch.setattr(
        leave_module,
        "delete_participant_record",
        lambda channel_id, user_id: deleted.append((channel_id, user_id)) or True,
    )

    asyncio.run(command.callback(interaction))

    assert deleted == [(10, 42)]
    channel.set_permissions.assert_awaited_once_with(interaction.user, overwrite=None)
    interaction.response.send_message.assert_awaited_once_with("✅ CTFから退出しました。", ephemeral=True)
    channel.send.assert_awaited_once_with("@user がこの CTF から退出しました。")


def test_leave_command_removes_permissions_from_split_channels(monkeypatch):
    monkeypatch.setattr(leave_module.discord, "TextChannel", FakeTextChannel)
    group = app_commands.Group(name="ctf", description="CTF")
    leave_module.register_command(group, make_context())
    command = get_command(group, "leave")
    root_channel = make_text_channel(channel_id=45, name="ctf-demo-p4f")
    p2w_channel = make_text_channel(channel_id=46, name="ctf-demo-p2w")
    interaction = types.SimpleNamespace(
        guild=types.SimpleNamespace(get_channel=lambda channel_id: {45: root_channel, 46: p2w_channel}.get(channel_id)),
        channel=root_channel,
        user=types.SimpleNamespace(id=42, mention="@user"),
        response=types.SimpleNamespace(send_message=AsyncMock()),
    )
    monkeypatch.setattr(leave_module, "is_bot_created_channel", lambda channel_id: True)
    monkeypatch.setattr(
        leave_module,
        "get_participant",
        lambda channel_id, user_id: types.SimpleNamespace(user_id=user_id, participation_type="play2win"),
    )
    monkeypatch.setattr(
        leave_module,
        "get_root_channel_record",
        lambda channel_id: types.SimpleNamespace(channel_id=45, split_completed=1),
    )
    monkeypatch.setattr(
        leave_module,
        "get_team_channel_record",
        lambda root_channel_id, team_type: types.SimpleNamespace(channel_id=46),
    )
    monkeypatch.setattr(leave_module, "delete_participant_record", lambda channel_id, user_id: True)

    asyncio.run(command.callback(interaction))

    root_channel.set_permissions.assert_awaited_once_with(interaction.user, overwrite=None)
    p2w_channel.set_permissions.assert_awaited_once_with(interaction.user, overwrite=None)
    root_channel.send.assert_awaited_once_with("@user がこの CTF から退出しました。")
    p2w_channel.send.assert_awaited_once_with("@user がこの CTF から退出しました。")


def test_leave_command_rejects_non_participants(monkeypatch):
    monkeypatch.setattr(leave_module.discord, "TextChannel", FakeTextChannel)
    group = app_commands.Group(name="ctf", description="CTF")
    leave_module.register_command(group, make_context())
    command = get_command(group, "leave")
    interaction = types.SimpleNamespace(
        guild=types.SimpleNamespace(),
        channel=make_text_channel(channel_id=45),
        user=types.SimpleNamespace(id=42, mention="@user"),
        response=types.SimpleNamespace(send_message=AsyncMock()),
    )
    monkeypatch.setattr(leave_module, "is_bot_created_channel", lambda channel_id: True)
    monkeypatch.setattr(leave_module, "get_participant", lambda channel_id, user_id: None)

    try:
        asyncio.run(command.callback(interaction))
    except UserFacingError as exc:
        assert str(exc) == "❌ まだこのCTFに参加していません。"
    else:
        raise AssertionError("UserFacingError was not raised")


def test_leave_command_rejects_after_disclose(monkeypatch):
    monkeypatch.setattr(leave_module.discord, "TextChannel", FakeTextChannel)
    group = app_commands.Group(name="ctf", description="CTF")
    leave_module.register_command(group, make_context())
    command = get_command(group, "leave")
    interaction = types.SimpleNamespace(
        guild=types.SimpleNamespace(),
        channel=make_text_channel(channel_id=45),
        user=types.SimpleNamespace(id=42, mention="@user"),
        response=types.SimpleNamespace(send_message=AsyncMock()),
    )
    monkeypatch.setattr(leave_module, "is_bot_created_channel", lambda channel_id: True)
    monkeypatch.setattr(
        leave_module,
        "get_participant",
        lambda channel_id, user_id: types.SimpleNamespace(user_id=user_id, participation_type="play4fun"),
    )
    monkeypatch.setattr(
        leave_module,
        "get_root_channel_record",
        lambda channel_id: types.SimpleNamespace(channel_id=45, disclosed=1),
    )

    try:
        asyncio.run(command.callback(interaction))
    except UserFacingError as exc:
        assert str(exc) == "❌ disclose 後は leave できません。"
    else:
        raise AssertionError("UserFacingError was not raised")


def test_search_command_returns_matches(monkeypatch):
    monkeypatch.setattr(search_module.discord, "TextChannel", FakeTextChannel)
    group = app_commands.Group(name="ctf", description="CTF")
    search_module.register_command(group, make_context())
    command = get_command(group, "search")
    channel = make_text_channel()
    channel.threads = [types.SimpleNamespace(name="✅ web-1 [Web]", mention="#solved-web")]
    channel.archived_threads = lambda limit=None: async_iter(
        [types.SimpleNamespace(name="warmup [Web]", mention="#warmup")]
    )
    interaction = types.SimpleNamespace(
        channel=channel,
        response=types.SimpleNamespace(send_message=AsyncMock()),
    )
    monkeypatch.setattr(search_module, "is_bot_created_channel", lambda channel_id: True)

    asyncio.run(command.callback(interaction, "web", None))

    interaction.response.send_message.assert_awaited_once()
    message = interaction.response.send_message.await_args.args[0]
    assert "#warmup" in message
    assert "#solved-web" in message


def test_ctfconf_command_updates_times(monkeypatch):
    monkeypatch.setattr(ctfconf_module.discord, "TextChannel", FakeTextChannel)
    group = app_commands.Group(name="ctf", description="CTF")
    ctfconf_module.register_command(group, make_context())
    command = get_command(group, "ctfconf")
    channel = make_text_channel()
    interaction = types.SimpleNamespace(
        channel=channel,
        user=types.SimpleNamespace(mention="@user"),
        response=types.SimpleNamespace(send_message=AsyncMock()),
    )
    updates = []
    monkeypatch.setattr(ctfconf_module, "is_bot_created_channel", lambda channel_id: True)
    monkeypatch.setattr(
        ctfconf_module,
        "get_root_channel_record",
        lambda channel_id: types.SimpleNamespace(channel_id=channel_id),
    )
    monkeypatch.setattr(
        ctfconf_module,
        "update_channel_record",
        lambda channel_id, **kwargs: updates.append((channel_id, kwargs)) or True,
    )
    reconcile = AsyncMock()
    split_service = types.SimpleNamespace(reconcile_channel_state=reconcile)
    monkeypatch.setattr(ctfconf_module, "SplitService", lambda bot, logger: split_service)

    teammode = app_commands.Choice(name="split", value="split")
    interaction.guild = types.SimpleNamespace()
    asyncio.run(command.callback(interaction, "2026-03-20 10:00", "2026-03-21 12:00", teammode))

    assert updates[0][0] == channel.id
    assert updates[0][1]["start_time"] == datetime(2026, 3, 20, 10, 0)
    assert updates[0][1]["end_time"] == datetime(2026, 3, 21, 12, 0)
    assert updates[0][1]["team_mode"] == "split"
    reconcile.assert_awaited_once_with(interaction.guild, channel.id)
    interaction.response.send_message.assert_awaited_once()
    channel.send.assert_awaited_once()
    assert "@user が CTF 設定を更新しました。" in channel.send.await_args.args[0]


def test_ctfconf_command_rejects_end_before_existing_start(monkeypatch):
    monkeypatch.setattr(ctfconf_module.discord, "TextChannel", FakeTextChannel)
    group = app_commands.Group(name="ctf", description="CTF")
    ctfconf_module.register_command(group, make_context())
    command = get_command(group, "ctfconf")
    channel = make_text_channel()
    interaction = types.SimpleNamespace(
        channel=channel,
        response=types.SimpleNamespace(send_message=AsyncMock()),
    )
    monkeypatch.setattr(ctfconf_module, "is_bot_created_channel", lambda channel_id: True)
    monkeypatch.setattr(
        ctfconf_module,
        "get_root_channel_record",
        lambda channel_id: types.SimpleNamespace(
            channel_id=channel_id,
            start_time=datetime(2026, 3, 21, 12, 0),
            end_time=None,
        ),
    )
    monkeypatch.setattr(ctfconf_module, "update_channel_record", lambda *args, **kwargs: True)

    try:
        asyncio.run(command.callback(interaction, None, "2026-03-20 10:00", None))
    except UserFacingError as exc:
        assert str(exc) == "終了時刻は開始時刻以降にしてください。"
    else:
        raise AssertionError("UserFacingError was not raised")


def test_ctfconf_command_rejects_teammode_change_after_disclose(monkeypatch):
    monkeypatch.setattr(ctfconf_module.discord, "TextChannel", FakeTextChannel)
    group = app_commands.Group(name="ctf", description="CTF")
    ctfconf_module.register_command(group, make_context())
    command = get_command(group, "ctfconf")
    channel = make_text_channel()
    interaction = types.SimpleNamespace(channel=channel, response=types.SimpleNamespace(send_message=AsyncMock()))
    monkeypatch.setattr(ctfconf_module, "is_bot_created_channel", lambda channel_id: True)
    monkeypatch.setattr(
        ctfconf_module,
        "get_root_channel_record",
        lambda channel_id: types.SimpleNamespace(channel_id=channel_id, disclosed=1, start_time=None, end_time=None),
    )

    try:
        asyncio.run(command.callback(interaction, None, None, app_commands.Choice(name="join", value="join")))
    except UserFacingError as exc:
        assert str(exc) == "❌ disclose 後は teammode を変更できません。"
    else:
        raise AssertionError("UserFacingError was not raised")


def test_disclose_command_success(monkeypatch):
    monkeypatch.setattr(disclose_module.discord, "TextChannel", FakeTextChannel)
    group = app_commands.Group(name="ctf", description="CTF")
    disclose_module.register_command(group, make_context())
    command = get_command(group, "disclose")
    channel = make_text_channel(channel_id=45)
    interaction = types.SimpleNamespace(
        channel=channel,
        guild=types.SimpleNamespace(),
        user=types.SimpleNamespace(mention="@user"),
        response=types.SimpleNamespace(send_message=AsyncMock()),
    )
    disclose = AsyncMock(return_value=True)
    monkeypatch.setattr(disclose_module, "is_bot_created_channel", lambda channel_id: True)
    monkeypatch.setattr(
        disclose_module,
        "get_root_channel_record",
        lambda channel_id: types.SimpleNamespace(channel_id=45, split_completed=1, end_time=datetime(2026, 3, 21, 12, 0), disclosed=0),
    )
    monkeypatch.setattr(disclose_module, "tokyo_now", lambda: datetime(2026, 3, 21, 12, 0))
    monkeypatch.setattr(disclose_module, "SplitService", lambda bot, logger: types.SimpleNamespace(disclose_channel=disclose))

    asyncio.run(command.callback(interaction))

    disclose.assert_awaited_once_with(interaction.guild, 45)
    interaction.response.send_message.assert_awaited_once_with("✅ disclose しました。", ephemeral=True)
    channel.send.assert_awaited_once_with("@user が disclose しました。")


def test_disclose_command_allows_non_split_ctf(monkeypatch):
    monkeypatch.setattr(disclose_module.discord, "TextChannel", FakeTextChannel)
    group = app_commands.Group(name="ctf", description="CTF")
    disclose_module.register_command(group, make_context())
    command = get_command(group, "disclose")
    channel = make_text_channel(channel_id=45)
    interaction = types.SimpleNamespace(
        channel=channel,
        guild=types.SimpleNamespace(),
        user=types.SimpleNamespace(mention="@user"),
        response=types.SimpleNamespace(send_message=AsyncMock()),
    )
    disclose = AsyncMock(return_value=True)
    monkeypatch.setattr(disclose_module, "is_bot_created_channel", lambda channel_id: True)
    monkeypatch.setattr(
        disclose_module,
        "get_root_channel_record",
        lambda channel_id: types.SimpleNamespace(channel_id=45, split_completed=0, end_time=datetime(2026, 3, 21, 12, 0), disclosed=0),
    )
    monkeypatch.setattr(disclose_module, "tokyo_now", lambda: datetime(2026, 3, 21, 12, 0))
    monkeypatch.setattr(disclose_module, "SplitService", lambda bot, logger: types.SimpleNamespace(disclose_channel=disclose))

    asyncio.run(command.callback(interaction))

    disclose.assert_awaited_once_with(interaction.guild, 45)
    interaction.response.send_message.assert_awaited_once_with("✅ disclose しました。", ephemeral=True)


def test_disclose_command_rejects_before_end(monkeypatch):
    monkeypatch.setattr(disclose_module.discord, "TextChannel", FakeTextChannel)
    group = app_commands.Group(name="ctf", description="CTF")
    disclose_module.register_command(group, make_context())
    command = get_command(group, "disclose")
    interaction = types.SimpleNamespace(channel=make_text_channel(channel_id=45), response=types.SimpleNamespace(send_message=AsyncMock()))
    monkeypatch.setattr(disclose_module, "is_bot_created_channel", lambda channel_id: True)
    monkeypatch.setattr(
        disclose_module,
        "get_root_channel_record",
        lambda channel_id: types.SimpleNamespace(channel_id=45, split_completed=1, end_time=datetime(2026, 3, 21, 12, 0), disclosed=0),
    )
    monkeypatch.setattr(disclose_module, "tokyo_now", lambda: datetime(2026, 3, 21, 11, 59))

    try:
        asyncio.run(command.callback(interaction))
    except UserFacingError as exc:
        assert str(exc) == "❌ このコマンドは終了時刻以降にのみ実行できます。"
    else:
        raise AssertionError("UserFacingError was not raised")


def test_time_command_displays_schedule(monkeypatch):
    monkeypatch.setattr(time_module.discord, "TextChannel", FakeTextChannel)
    group = app_commands.Group(name="ctf", description="CTF")
    time_module.register_command(group, make_context())
    command = get_command(group, "time")
    channel = make_text_channel(name="ctf-demo")
    interaction = types.SimpleNamespace(
        channel=channel,
        response=types.SimpleNamespace(send_message=AsyncMock()),
    )
    monkeypatch.setattr(time_module, "is_bot_created_channel", lambda channel_id: True)
    monkeypatch.setattr(
        time_module,
        "get_root_channel_record",
        lambda channel_id: types.SimpleNamespace(
            channel_name="ctf-demo",
            start_time=datetime(2026, 3, 20, 10, 0),
            end_time=datetime(2026, 3, 21, 12, 0),
        ),
    )
    monkeypatch.setattr(time_module, "tokyo_now", lambda: datetime(2026, 3, 20, 9, 0))

    asyncio.run(command.callback(interaction))

    interaction.response.send_message.assert_awaited_once()
    message = interaction.response.send_message.await_args.args[0]
    assert "開始: <t:1773968400:F> (<t:1773968400:R>)" in message
    assert "終了: <t:1774062000:F> (<t:1774062000:R>)" in message


def test_players_command_displays_grouped_participants(monkeypatch):
    monkeypatch.setattr(players_module.discord, "TextChannel", FakeTextChannel)
    group = app_commands.Group(name="ctf", description="CTF")
    players_module.register_command(group, make_context())
    command = get_command(group, "players")
    channel = make_text_channel(channel_id=45)
    interaction = types.SimpleNamespace(
        channel=channel,
        response=types.SimpleNamespace(send_message=AsyncMock()),
    )
    monkeypatch.setattr(players_module, "is_bot_created_channel", lambda channel_id: True)
    monkeypatch.setattr(
        players_module,
        "get_participants",
        lambda channel_id: [
            types.SimpleNamespace(user_id=10, participation_type="play2win"),
            types.SimpleNamespace(user_id=20, participation_type="play4fun"),
        ],
    )

    asyncio.run(command.callback(interaction))

    interaction.response.send_message.assert_awaited_once_with(
        "✅ 参加者一覧 (合計: 2人)\nplay2win: 1人\n<@10>\nplay4fun: 1人\n<@20>",
        ephemeral=True,
    )


def test_randomname_command_returns_formatted_candidates(monkeypatch):
    group = app_commands.Group(name="ctf", description="CTF")
    randomname_module.register_command(group, make_context())
    command = get_command(group, "randomname")
    interaction = types.SimpleNamespace(
        response=types.SimpleNamespace(send_message=AsyncMock()),
    )
    random_word = Mock()
    random_word.random_words.return_value = ["falcon", "otter"]
    monkeypatch.setattr(randomname_module, "RandomWord", lambda: random_word)

    asyncio.run(command.callback(interaction, "2"))

    random_word.random_words.assert_called_once_with(2, include_parts_of_speech=["nouns"])
    interaction.response.send_message.assert_awaited_once_with(
        "チーム名候補: \n`full_weak_falcon`\n`full_weak_otter`",
        ephemeral=False,
    )


def test_randomname_command_rejects_non_numeric_count():
    group = app_commands.Group(name="ctf", description="CTF")
    randomname_module.register_command(group, make_context())
    command = get_command(group, "randomname")
    interaction = types.SimpleNamespace(
        response=types.SimpleNamespace(send_message=AsyncMock()),
    )

    try:
        asyncio.run(command.callback(interaction, "abc"))
    except UserFacingError as exc:
        assert str(exc) == "countは数値を入力してください。"
    else:
        raise AssertionError("UserFacingError was not raised")


def test_randomname_command_rejects_out_of_range_count():
    group = app_commands.Group(name="ctf", description="CTF")
    randomname_module.register_command(group, make_context())
    command = get_command(group, "randomname")
    interaction = types.SimpleNamespace(
        response=types.SimpleNamespace(send_message=AsyncMock()),
    )

    try:
        asyncio.run(command.callback(interaction, "11"))
    except UserFacingError as exc:
        assert str(exc) == "countの値が不正です。"
    else:
        raise AssertionError("UserFacingError was not raised")


def test_switchteam_command_updates_participation_type(monkeypatch):
    monkeypatch.setattr(switchteam_module.discord, "TextChannel", FakeTextChannel)
    group = app_commands.Group(name="ctf", description="CTF")
    switchteam_module.register_command(group, make_context())
    command = get_command(group, "switchteam")
    channel = make_text_channel(channel_id=45)
    interaction = types.SimpleNamespace(
        channel=channel,
        user=types.SimpleNamespace(id=10, mention="@user"),
        response=types.SimpleNamespace(send_message=AsyncMock()),
    )
    calls = []
    monkeypatch.setattr(switchteam_module, "is_bot_created_channel", lambda channel_id: True)
    monkeypatch.setattr(
        switchteam_module,
        "get_participant",
        lambda channel_id, user_id: types.SimpleNamespace(user_id=user_id, participation_type="play4fun"),
    )
    monkeypatch.setattr(
        switchteam_module,
        "upsert_participant_record",
        lambda channel_id, user_id, participation_type: calls.append((channel_id, user_id, participation_type)),
    )
    monkeypatch.setattr(switchteam_module, "get_root_channel_record", lambda channel_id: None)
    choice = app_commands.Choice(name="play2win", value="play2win")

    asyncio.run(command.callback(interaction, choice))

    assert calls == [(45, 10, "play2win")]
    interaction.response.send_message.assert_awaited_once_with(
        "✅ 参加種別を `play2win` に切り替えました。",
        ephemeral=True,
    )
    channel.send.assert_awaited_once_with("@user が参加種別を `play2win` に切り替えました。")


def test_switchteam_command_notifies_both_channels_when_split(monkeypatch):
    monkeypatch.setattr(switchteam_module.discord, "TextChannel", FakeTextChannel)
    group = app_commands.Group(name="ctf", description="CTF")
    switchteam_module.register_command(group, make_context())
    command = get_command(group, "switchteam")
    root_channel = make_text_channel(channel_id=45, name="ctf-demo-p4f")
    p2w_channel = make_text_channel(channel_id=46, name="ctf-demo-p2w")
    guild = types.SimpleNamespace(get_channel=lambda channel_id: {45: root_channel, 46: p2w_channel}.get(channel_id))
    interaction = types.SimpleNamespace(
        channel=root_channel,
        guild=guild,
        user=types.SimpleNamespace(id=10, mention="@user"),
        response=types.SimpleNamespace(send_message=AsyncMock()),
    )
    monkeypatch.setattr(switchteam_module, "is_bot_created_channel", lambda channel_id: True)
    monkeypatch.setattr(
        switchteam_module,
        "get_participant",
        lambda channel_id, user_id: types.SimpleNamespace(user_id=user_id, participation_type="play4fun"),
    )
    monkeypatch.setattr(switchteam_module, "upsert_participant_record", lambda *args: None)
    monkeypatch.setattr(
        switchteam_module,
        "get_root_channel_record",
        lambda channel_id: types.SimpleNamespace(channel_id=45, split_completed=1),
    )
    monkeypatch.setattr(
        switchteam_module,
        "get_team_channel_record",
        lambda root_channel_id, team_type: types.SimpleNamespace(channel_id=46),
    )
    choice = app_commands.Choice(name="play2win", value="play2win")

    asyncio.run(command.callback(interaction, choice))

    root_channel.send.assert_awaited_once_with("@user が参加種別を `play2win` に切り替えました。")
    p2w_channel.send.assert_awaited_once_with("@user が参加種別を `play2win` に切り替えました。")


def test_switchteam_command_rejects_non_participants(monkeypatch):
    monkeypatch.setattr(switchteam_module.discord, "TextChannel", FakeTextChannel)
    group = app_commands.Group(name="ctf", description="CTF")
    switchteam_module.register_command(group, make_context())
    command = get_command(group, "switchteam")
    interaction = types.SimpleNamespace(
        channel=make_text_channel(channel_id=45),
        user=types.SimpleNamespace(id=10),
        response=types.SimpleNamespace(send_message=AsyncMock()),
    )
    monkeypatch.setattr(switchteam_module, "is_bot_created_channel", lambda channel_id: True)
    monkeypatch.setattr(switchteam_module, "get_participant", lambda channel_id, user_id: None)
    choice = app_commands.Choice(name="play2win", value="play2win")

    try:
        asyncio.run(command.callback(interaction, choice))
    except UserFacingError as exc:
        assert str(exc) == "❌ まだこのCTFに参加していません。参加ボタンから参加してください。"
    else:
        raise AssertionError("UserFacingError was not raised")


def test_switchteam_command_rejects_after_disclose(monkeypatch):
    monkeypatch.setattr(switchteam_module.discord, "TextChannel", FakeTextChannel)
    group = app_commands.Group(name="ctf", description="CTF")
    switchteam_module.register_command(group, make_context())
    command = get_command(group, "switchteam")
    interaction = types.SimpleNamespace(
        channel=make_text_channel(channel_id=45),
        user=types.SimpleNamespace(id=10),
        response=types.SimpleNamespace(send_message=AsyncMock()),
    )
    monkeypatch.setattr(switchteam_module, "is_bot_created_channel", lambda channel_id: True)
    monkeypatch.setattr(
        switchteam_module,
        "get_participant",
        lambda channel_id, user_id: types.SimpleNamespace(user_id=user_id, participation_type="play4fun"),
    )
    monkeypatch.setattr(
        switchteam_module,
        "get_root_channel_record",
        lambda channel_id: types.SimpleNamespace(channel_id=45, disclosed=1),
    )

    try:
        asyncio.run(command.callback(interaction, app_commands.Choice(name="play2win", value="play2win")))
    except UserFacingError as exc:
        assert str(exc) == "❌ disclose 後は switchteam できません。"
    else:
        raise AssertionError("UserFacingError was not raised")


def test_solve_command_handles_unsolved_thread(monkeypatch):
    monkeypatch.setattr(solve_module.discord, "Thread", FakeThread)
    group = app_commands.Group(name="ctf", description="CTF")
    solve_module.register_command(group, make_context())
    command = get_command(group, "solve")
    thread = make_thread(name="crypto [Crypto]", owner_id=999)
    interaction = types.SimpleNamespace(
        channel=thread,
        user=types.SimpleNamespace(mention="@user"),
        response=types.SimpleNamespace(send_message=AsyncMock()),
    )

    asyncio.run(command.callback(interaction))

    thread.edit.assert_awaited_once_with(name="✅ crypto [Crypto]")
    interaction.response.send_message.assert_awaited_once_with(
        "✅ @user さんがスレッドを解決済みにしました！",
        ephemeral=False,
    )


def test_solve_command_handles_already_solved_thread(monkeypatch):
    monkeypatch.setattr(solve_module.discord, "Thread", FakeThread)
    group = app_commands.Group(name="ctf", description="CTF")
    solve_module.register_command(group, make_context())
    command = get_command(group, "solve")
    thread = make_thread(name="✅ crypto [Crypto]", owner_id=999)
    interaction = types.SimpleNamespace(
        channel=thread,
        user=types.SimpleNamespace(mention="@user"),
        response=types.SimpleNamespace(send_message=AsyncMock()),
    )

    asyncio.run(command.callback(interaction))

    thread.edit.assert_not_awaited()
    interaction.response.send_message.assert_awaited_once_with(
        "⚠️ すでに解決済みです。",
        ephemeral=True,
    )
