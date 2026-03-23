import asyncio
import importlib
import sys
import types
from pathlib import Path
from unittest.mock import AsyncMock, Mock

from interaction_errors import UserFacingError

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
        data={"custom_id": "ctf_join:123:play2win"},
    )
    asyncio.run(service.route_interaction(interaction))

    service.handle_join.assert_awaited_once_with(interaction, "ctf_join:123:play2win", False)
    service.handle_join_new.assert_not_awaited()

    interaction = types.SimpleNamespace(
        type=join_module.discord.InteractionType.component,
        data={"custom_id": "ctf_join_new:456:play4fun"},
    )
    asyncio.run(service.route_interaction(interaction))

    service.handle_join_new.assert_awaited_once_with(interaction, "ctf_join_new:456:play4fun")


def test_route_interaction_ignores_non_component_interactions():
    service = create_join_service()
    service.handle_join = AsyncMock()

    interaction = types.SimpleNamespace(type=None, data={"custom_id": "ctf_join:123:play2win"})
    asyncio.run(service.route_interaction(interaction))

    service.handle_join.assert_not_awaited()


def test_handle_join_rejects_invalid_channel_id():
    service = create_join_service()
    response = types.SimpleNamespace(send_message=AsyncMock())
    interaction = types.SimpleNamespace(response=response)

    try:
        asyncio.run(service.handle_join(interaction, "ctf_join:abc:play2win"))
    except UserFacingError as exc:
        assert str(exc) == "Button is misconfigured."
    else:
        raise AssertionError("UserFacingError was not raised")


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

    asyncio.run(service.handle_join(interaction, "ctf_join:123:play2win"))

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
    user = types.SimpleNamespace(id=42, roles=[types.SimpleNamespace(id=99)], mention="@user")
    interaction = types.SimpleNamespace(
        guild=guild,
        user=user,
        response=response,
        message=message,
    )

    join_module.upsert_participant_record = Mock()
    asyncio.run(service.handle_join(interaction, "ctf_join:123:play2win"))

    channel.set_permissions.assert_awaited_once_with(
        user,
        view_channel=True,
        send_messages=True,
        read_message_history=True,
    )
    join_module.upsert_participant_record.assert_called_once_with(123, user.id, "play2win")
    channel.send.assert_awaited_once_with("@userが `play2win` として参加しました")
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
        user=types.SimpleNamespace(id=55, roles=[types.SimpleNamespace(id=99)]),
        response=response,
        message=None,
    )

    join_module.get_participant = Mock(return_value=types.SimpleNamespace(participation_type="play4fun"))
    join_module.upsert_participant_record = Mock()
    asyncio.run(service.handle_join(interaction, "ctf_join:123:play4fun"))

    join_module.get_participant.assert_called_once_with(123, 55)
    join_module.upsert_participant_record.assert_called_once_with(123, 55, "play4fun")
    response.send_message.assert_awaited_once_with(
        "#ctf-test に既に参加しています。参加種別を `play4fun` に更新しました",
        ephemeral=True,
    )


def test_handle_join_new_adds_role_and_retries_join():
    service = create_join_service()
    service.handle_join = AsyncMock()
    response = types.SimpleNamespace(send_message=AsyncMock())
    role = types.SimpleNamespace(id=99)
    user = types.SimpleNamespace(add_roles=AsyncMock())
    guild = types.SimpleNamespace(get_role=lambda role_id: role)
    interaction = types.SimpleNamespace(guild=guild, user=user, response=response)

    asyncio.run(service.handle_join_new(interaction, "ctf_join_new:123:play2win"))

    user.add_roles.assert_awaited_once_with(role, reason="CTF join gate passed")
    service.handle_join.assert_awaited_once_with(interaction, "ctf_join_new:123:play2win", True)


def test_handle_join_new_rejects_missing_role():
    service = create_join_service()
    interaction = types.SimpleNamespace(
        guild=types.SimpleNamespace(get_role=lambda role_id: None),
        user=types.SimpleNamespace(add_roles=AsyncMock()),
        response=types.SimpleNamespace(send_message=AsyncMock()),
    )

    try:
        asyncio.run(service.handle_join_new(interaction, "ctf_join_new:123:play2win"))
    except UserFacingError as exc:
        assert str(exc) == "CTF用ロールが見つかりません。"
    else:
        raise AssertionError("UserFacingError was not raised")


def test_handle_join_grants_both_channels_when_disclosed():
    join_module.discord.TextChannel = FakeTextChannel
    split_service = types.SimpleNamespace(
        resolve_target_channel_id=lambda channel_id, participation_type: channel_id,
        sync_participant_channels=AsyncMock(),
    )
    service = join_module.JoinService(logger=types.SimpleNamespace(exception=lambda *args, **kwargs: None), ctf_role_id=99, split_service=split_service)
    response = types.SimpleNamespace(send_message=AsyncMock())
    channel = FakeTextChannel()
    guild = types.SimpleNamespace(get_channel=lambda channel_id: channel, fetch_channel=AsyncMock())
    user = types.SimpleNamespace(id=42, roles=[types.SimpleNamespace(id=99)], mention="@user")
    interaction = types.SimpleNamespace(guild=guild, user=user, response=response, message=None)

    join_module.upsert_participant_record = Mock()
    asyncio.run(service.handle_join(interaction, "ctf_join:123:play2win"))

    split_service.sync_participant_channels.assert_awaited_once_with(guild, 123, user, "play2win")


def test_handle_join_logs_previous_team_when_switching_via_button():
    join_module.discord.TextChannel = FakeTextChannel
    old_channel = FakeTextChannel(channel_id=123, name="ctf-p4f", mention="#ctf-p4f")
    new_channel = FakeTextChannel(channel_id=456, name="ctf-p2w", mention="#ctf-p2w")
    split_service = types.SimpleNamespace(
        resolve_target_channel_id=lambda channel_id, participation_type: 123 if participation_type == "play4fun" else 456,
        sync_participant_channels=AsyncMock(),
    )
    service = join_module.JoinService(
        logger=types.SimpleNamespace(exception=lambda *args, **kwargs: None),
        ctf_role_id=99,
        split_service=split_service,
    )
    response = types.SimpleNamespace(send_message=AsyncMock())
    guild = types.SimpleNamespace(
        get_channel=lambda channel_id: {123: old_channel, 456: new_channel}.get(channel_id),
        fetch_channel=AsyncMock(),
    )
    interaction = types.SimpleNamespace(
        guild=guild,
        user=types.SimpleNamespace(id=55, roles=[types.SimpleNamespace(id=99)], mention="@user"),
        response=response,
        message=None,
    )
    new_channel.overwrites_for = lambda user: types.SimpleNamespace(view_channel=False)

    join_module.get_participant = Mock(return_value=types.SimpleNamespace(participation_type="play4fun"))
    join_module.upsert_participant_record = Mock()

    asyncio.run(service.handle_join(interaction, "ctf_join:123:play2win"))

    new_channel.set_permissions.assert_awaited_once_with(
        interaction.user,
        view_channel=True,
        send_messages=True,
        read_message_history=True,
    )
    split_service.sync_participant_channels.assert_awaited_once_with(guild, 123, interaction.user, "play2win")
    old_channel.send.assert_awaited_once_with("@userが `play2win` にチーム変更しました。")
    response.send_message.assert_awaited_once_with(
        "#ctf-p2wに `play2win` として参加しました",
        ephemeral=True,
    )


def test_handle_join_logs_previous_team_when_already_in_target_channel():
    join_module.discord.TextChannel = FakeTextChannel
    old_channel = FakeTextChannel(channel_id=123, name="ctf-p4f", mention="#ctf-p4f")
    new_channel = FakeTextChannel(channel_id=456, name="ctf-p2w", mention="#ctf-p2w")
    new_channel.overwrites_for = lambda user: types.SimpleNamespace(view_channel=True)
    split_service = types.SimpleNamespace(
        resolve_target_channel_id=lambda channel_id, participation_type: 123 if participation_type == "play4fun" else 456,
        sync_participant_channels=AsyncMock(),
    )
    service = join_module.JoinService(
        logger=types.SimpleNamespace(exception=lambda *args, **kwargs: None),
        ctf_role_id=99,
        split_service=split_service,
    )
    response = types.SimpleNamespace(send_message=AsyncMock())
    guild = types.SimpleNamespace(
        get_channel=lambda channel_id: {123: old_channel, 456: new_channel}.get(channel_id),
        fetch_channel=AsyncMock(),
    )
    user = types.SimpleNamespace(id=55, roles=[types.SimpleNamespace(id=99)], mention="@user")
    interaction = types.SimpleNamespace(
        guild=guild,
        user=user,
        response=response,
        message=None,
    )

    join_module.get_participant = Mock(return_value=types.SimpleNamespace(participation_type="play4fun"))
    join_module.upsert_participant_record = Mock()

    asyncio.run(service.handle_join(interaction, "ctf_join:123:play2win"))

    join_module.upsert_participant_record.assert_called_once_with(456, 55, "play2win")
    split_service.sync_participant_channels.assert_awaited_once_with(guild, 123, user, "play2win")
    old_channel.send.assert_awaited_once_with("@userが `play2win` にチーム変更しました。")
    response.send_message.assert_awaited_once_with(
        "#ctf-p2w に既に参加しています。参加種別を `play2win` に更新しました",
        ephemeral=True,
    )


def test_update_join_message_returns_without_message():
    join_module.discord.TextChannel = FakeTextChannel
    service = create_join_service()
    interaction = types.SimpleNamespace(message=None)
    channel = FakeTextChannel(channel_id=1, name="ctf", mention="#ctf")

    asyncio.run(service.update_join_message(interaction, channel))
