import asyncio
import importlib
import types
from unittest.mock import AsyncMock, Mock

from interaction_errors import UserFacingCheckFailure


app_module = importlib.import_module("app")
config_module = importlib.import_module("config")


def make_settings():
    return config_module.Settings(
        token="token",
        guild_id=123,
        ctf_creator_role_id=1,
        ctf_role_id=2,
        category_name="CTF",
        archive_category="ARCHIVE",
    )


def test_on_interaction_routes_to_join_service(monkeypatch):
    bot, _, _, join_service = app_module.create_application(make_settings())
    join_service.route_interaction = AsyncMock()
    interaction = types.SimpleNamespace()

    asyncio.run(bot.on_interaction(interaction))

    join_service.route_interaction.assert_awaited_once_with(interaction)


def test_on_interaction_reports_errors_ephemerally(monkeypatch):
    bot, _, _, join_service = app_module.create_application(make_settings())
    join_service.route_interaction = AsyncMock(side_effect=RuntimeError("boom"))
    interaction = types.SimpleNamespace(
        response=types.SimpleNamespace(send_message=AsyncMock(), is_done=lambda: False),
        followup=types.SimpleNamespace(send=AsyncMock()),
    )

    asyncio.run(bot.on_interaction(interaction))

    interaction.response.send_message.assert_awaited_once_with("エラー: boom", ephemeral=True)
    interaction.followup.send.assert_not_awaited()


def test_on_ready_initializes_database_and_syncs(monkeypatch):
    bot, tree, _, _ = app_module.create_application(make_settings())
    bot._connection.user = types.SimpleNamespace(id=5)
    init_database = Mock()
    sync = AsyncMock()
    def create_task(coro):
        coro.close()
        return Mock()
    monkeypatch.setattr(app_module, "init_database", init_database)
    monkeypatch.setattr(app_module.asyncio, "create_task", create_task)
    tree.sync = sync

    asyncio.run(bot.on_ready())

    init_database.assert_called_once()
    sync.assert_awaited_once()


def test_on_ready_logs_sync_failures(monkeypatch):
    logger = types.SimpleNamespace(info=lambda *args, **kwargs: None, exception=Mock())
    original_get_logger = app_module.logging.getLogger
    monkeypatch.setattr(
        app_module.logging,
        "getLogger",
        lambda name=None: logger if name == "ctfbot" else original_get_logger(name),
    )

    bot, tree, _, _ = app_module.create_application(make_settings())
    bot._connection.user = types.SimpleNamespace(id=5)
    monkeypatch.setattr(app_module, "init_database", Mock())
    monkeypatch.setattr(app_module.asyncio, "create_task", lambda coro: coro.close() or Mock())
    tree.sync = AsyncMock(side_effect=RuntimeError("boom"))

    asyncio.run(bot.on_ready())

    logger.exception.assert_called_once_with("Failed to sync commands")


def test_on_ready_reuses_running_split_task(monkeypatch):
    bot, tree, _, _ = app_module.create_application(make_settings())
    bot._connection.user = types.SimpleNamespace(id=5)
    monkeypatch.setattr(app_module, "init_database", Mock())
    task = types.SimpleNamespace(done=lambda: False)
    monkeypatch.setattr(app_module.asyncio, "create_task", lambda coro: coro.close() or task)
    tree.sync = AsyncMock()

    asyncio.run(bot.on_ready())
    asyncio.run(bot.on_ready())

    tree.sync.assert_awaited()


def test_create_intents_enables_required_flags():
    intents = app_module.create_intents()

    assert intents.guilds is True
    assert intents.members is True


def test_app_command_error_uses_followup_after_response_started(monkeypatch):
    bot, tree, _, _ = app_module.create_application(make_settings())
    interaction = types.SimpleNamespace(
        response=types.SimpleNamespace(send_message=AsyncMock(), is_done=lambda: True),
        followup=types.SimpleNamespace(send=AsyncMock()),
    )

    asyncio.run(tree.on_error(interaction, app_module.app_commands.AppCommandError("boom")))

    interaction.followup.send.assert_awaited_once_with("エラー: boom", ephemeral=True)
    interaction.response.send_message.assert_not_awaited()


def test_app_command_error_formats_forbidden(monkeypatch):
    bot, tree, _, _ = app_module.create_application(make_settings())
    interaction = types.SimpleNamespace(
        response=types.SimpleNamespace(send_message=AsyncMock(), is_done=lambda: False),
        followup=types.SimpleNamespace(send=AsyncMock()),
    )
    error = app_module.app_commands.CommandInvokeError(
        Mock(),
        app_module.discord.Forbidden(
            response=types.SimpleNamespace(status=403, reason="Forbidden"),
            message="Missing Access",
        ),
    )

    asyncio.run(tree.on_error(interaction, error))

    interaction.response.send_message.assert_awaited_once_with(
        "その操作をする権限がありません",
        ephemeral=True,
    )


def test_app_command_error_formats_user_facing_check_failure():
    bot, tree, _, _ = app_module.create_application(make_settings())
    interaction = types.SimpleNamespace(
        response=types.SimpleNamespace(send_message=AsyncMock(), is_done=lambda: False),
        followup=types.SimpleNamespace(send=AsyncMock()),
    )
    error = UserFacingCheckFailure("❌ このコマンドを実行する権限がありません。")

    asyncio.run(tree.on_error(interaction, error))

    interaction.response.send_message.assert_awaited_once_with(
        "❌ このコマンドを実行する権限がありません。",
        ephemeral=True,
    )
