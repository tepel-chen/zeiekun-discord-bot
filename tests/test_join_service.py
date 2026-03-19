import asyncio
import importlib
import sys
import types
from pathlib import Path
from unittest.mock import AsyncMock


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


join_module = importlib.import_module("services.join_service")


class FakeTextChannel:
    def __init__(self, channel_id=123, name="ctf-test", mention="#ctf-test"):
        self.id = channel_id
        self.name = name
        self.mention = mention
        self.members = []
        self.set_permissions = AsyncMock()
        self.send = AsyncMock()
        self.overwrites_for = lambda user: types.SimpleNamespace(view_channel=False)


def create_join_service():
    logger = types.SimpleNamespace(exception=lambda *args, **kwargs: None)
    return join_module.JoinService(logger=logger, ctf_role_id=99)


def test_route_interaction_dispatches_join_handlers():
    service = create_join_service()
    service.handle_join = AsyncMock()
    service.handle_join_new = AsyncMock()

    interaction = types.SimpleNamespace(
        type=join_module.discord.InteractionType.component,
        data={"custom_id": "ctf_join:123"},
    )
    asyncio.run(service.route_interaction(interaction))

    service.handle_join.assert_awaited_once_with(interaction, "ctf_join:123", False)
    service.handle_join_new.assert_not_awaited()

    interaction = types.SimpleNamespace(
        type=join_module.discord.InteractionType.component,
        data={"custom_id": "ctf_join_new:456"},
    )
    asyncio.run(service.route_interaction(interaction))

    service.handle_join_new.assert_awaited_once_with(interaction, "ctf_join_new:456")


def test_route_interaction_ignores_non_component_interactions():
    service = create_join_service()
    service.handle_join = AsyncMock()

    interaction = types.SimpleNamespace(type=None, data={"custom_id": "ctf_join:123"})
    asyncio.run(service.route_interaction(interaction))

    service.handle_join.assert_not_awaited()


def test_handle_join_rejects_invalid_channel_id():
    service = create_join_service()
    response = types.SimpleNamespace(send_message=AsyncMock())
    interaction = types.SimpleNamespace(response=response)

    asyncio.run(service.handle_join(interaction, "ctf_join:abc"))

    response.send_message.assert_awaited_once_with("Button is misconfigured.", ephemeral=True)


def test_handle_join_shows_rule_gate_when_role_missing():
    join_module.discord.TextChannel = FakeTextChannel
    service = create_join_service()
    response = types.SimpleNamespace(send_message=AsyncMock())
    channel = FakeTextChannel()
    guild = types.SimpleNamespace(
        get_channel=lambda channel_id: channel,
        fetch_channel=AsyncMock(),
    )
    user = types.SimpleNamespace(roles=[])
    interaction = types.SimpleNamespace(
        guild=guild,
        user=user,
        response=response,
    )

    asyncio.run(service.handle_join(interaction, "ctf_join:123"))

    response.send_message.assert_awaited_once()
    args = response.send_message.await_args
    assert args.args[0] == join_module.RULE_TEMPLATE
    assert args.kwargs["ephemeral"] is True
    assert args.kwargs["view"] is not None


def test_handle_join_succeeds_and_updates_message():
    join_module.discord.TextChannel = FakeTextChannel
    service = create_join_service()
    response = types.SimpleNamespace(send_message=AsyncMock())
    current = types.SimpleNamespace(view_channel=False)
    channel = FakeTextChannel()
    channel.members = [types.SimpleNamespace(bot=False)]
    channel.overwrites_for = lambda user: current
    message = types.SimpleNamespace(components=[], edit=AsyncMock())
    guild = types.SimpleNamespace(
        get_channel=lambda channel_id: channel,
        fetch_channel=AsyncMock(),
    )
    user = types.SimpleNamespace(roles=[types.SimpleNamespace(id=99)], mention="@user")
    interaction = types.SimpleNamespace(
        guild=guild,
        user=user,
        response=response,
        message=message,
    )

    asyncio.run(service.handle_join(interaction, "ctf_join:123"))

    channel.set_permissions.assert_awaited_once_with(
        user,
        view_channel=True,
        send_messages=True,
        read_message_history=True,
    )
    channel.send.assert_awaited_once_with("@userが参加しました")
    message.edit.assert_awaited_once()


def test_handle_join_reports_already_joined():
    join_module.discord.TextChannel = FakeTextChannel
    service = create_join_service()
    response = types.SimpleNamespace(send_message=AsyncMock())
    channel = FakeTextChannel()
    channel.overwrites_for = lambda user: types.SimpleNamespace(view_channel=True)
    guild = types.SimpleNamespace(get_channel=lambda channel_id: channel, fetch_channel=AsyncMock())
    interaction = types.SimpleNamespace(
        guild=guild,
        user=types.SimpleNamespace(roles=[types.SimpleNamespace(id=99)]),
        response=response,
        message=None,
    )

    asyncio.run(service.handle_join(interaction, "ctf_join:123"))

    response.send_message.assert_awaited_once_with("#ctf-test に既に参加しています", ephemeral=True)


def test_handle_join_new_adds_role_and_retries_join():
    service = create_join_service()
    service.handle_join = AsyncMock()
    response = types.SimpleNamespace(send_message=AsyncMock())
    role = types.SimpleNamespace(id=99)
    user = types.SimpleNamespace(add_roles=AsyncMock())
    guild = types.SimpleNamespace(get_role=lambda role_id: role)
    interaction = types.SimpleNamespace(guild=guild, user=user, response=response)

    asyncio.run(service.handle_join_new(interaction, "ctf_join_new:123"))

    user.add_roles.assert_awaited_once_with(role, reason="CTF join gate passed")
    service.handle_join.assert_awaited_once_with(interaction, "ctf_join_new:123", True)


def test_update_join_message_returns_without_message():
    join_module.discord.TextChannel = FakeTextChannel
    service = create_join_service()
    interaction = types.SimpleNamespace(message=None)
    channel = FakeTextChannel(channel_id=1, name="ctf", mention="#ctf")

    asyncio.run(service.update_join_message(interaction, channel))
