import asyncio
import importlib
import types
from unittest.mock import AsyncMock

import discord
from discord import app_commands

from commands.context import CommandContext


create_module = importlib.import_module("commands.create")
archive_module = importlib.import_module("commands.archive")
chal_module = importlib.import_module("commands.chal")
search_module = importlib.import_module("commands.search")
solve_module = importlib.import_module("commands.solve")


class FakeTextChannel:
    def __init__(self, channel_id=10, name="ctf-test", mention="#ctf-test", members=None):
        self.id = channel_id
        self.name = name
        self.mention = mention
        self.members = members or []
        self.send = AsyncMock()
        self.create_thread = AsyncMock()
        self.edit = AsyncMock()
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
    monkeypatch.setattr(create_module, "add_channel_record", lambda *args: None)

    asyncio.run(command.callback(interaction, "demo"))

    interaction.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
    interaction.followup.send.assert_awaited_once_with(
        content="#ctf-demo (ctf-demo)が作成されました",
        ephemeral=True,
    )
    interaction_channel.send.assert_awaited_once()


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

    asyncio.run(command.callback(interaction))

    interaction.response.send_message.assert_awaited_once_with(
        "❌ このコマンドはbotによって作成されたチャンネルでのみ使用できます。",
        ephemeral=True,
    )


def test_archive_command_success(monkeypatch):
    monkeypatch.setattr(archive_module.discord, "TextChannel", FakeTextChannel)
    group = app_commands.Group(name="ctf", description="CTF")
    archive_module.register_command(group, make_context())
    command = get_command(group, "archive")
    channel = make_text_channel()
    interaction = types.SimpleNamespace(
        guild=types.SimpleNamespace(),
        channel=channel,
        response=types.SimpleNamespace(send_message=AsyncMock()),
    )
    monkeypatch.setattr(archive_module, "is_bot_created_channel", lambda channel_id: True)
    monkeypatch.setattr(archive_module, "ensure_category", AsyncMock(return_value="archive-category"))

    asyncio.run(command.callback(interaction))

    channel.edit.assert_awaited_once_with(category="archive-category")
    interaction.response.send_message.assert_awaited_once_with(
        "✅ チャンネル #ctf-test をカテゴリー「ARCHIVE」へ移動しました。"
    )


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
