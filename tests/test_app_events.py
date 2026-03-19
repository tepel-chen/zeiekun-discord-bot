import asyncio
import importlib
import types
from unittest.mock import AsyncMock, Mock


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


def test_on_ready_initializes_database_and_syncs(monkeypatch):
    bot, tree, _, _ = app_module.create_application(make_settings())
    bot._connection.user = types.SimpleNamespace(id=5)
    init_database = Mock()
    sync = AsyncMock()
    monkeypatch.setattr(app_module, "init_database", init_database)
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
    tree.sync = AsyncMock(side_effect=RuntimeError("boom"))

    asyncio.run(bot.on_ready())

    logger.exception.assert_called_once_with("Failed to sync commands")
