import discord
from discord import app_commands

from commands.permissions import command_metadata, require_registered_context, require_registered_role
from db import add_channel_record
from interaction_errors import UserFacingError, send_interaction_error
from services.join_service import build_join_view
from services.channel_service import (
    allocate_channel_name,
    build_join_announcement,
    create_private_channel,
    ensure_category,
    get_participant_count,
)
from services.time_service import TimeParseError, parse_datetime_input, validate_time_range


@command_metadata(required_role="creator", channel_scope="outside_ctf_channel")
def register_command(ctf_commands: app_commands.Group, context):
    """新しいCTFチャンネルを作成し、参加ボタンを案内する。"""

    @require_registered_role(register_command, context)
    @require_registered_context(register_command, context)
    @ctf_commands.command(name="create", description="CTFチャンネルを作成する")
    @app_commands.describe(
        name="CTFの名前",
        start_time="開始時刻 (`tomorrow 21:00`, `3/20 18:00` など)",
        end_time="終了時刻 (`tomorrow 21:00`, `3/20 18:00` など)",
    )
    async def ctf_create(
        interaction: discord.Interaction,
        name: str,
        start_time: str | None = None,
        end_time: str | None = None,
    ):
        guild = interaction.guild
        assert guild is not None, "This command must be used in a guild"

        await interaction.response.defer(ephemeral=True, thinking=True)
        category = await ensure_category(guild, context.category_name)
        final_name = allocate_channel_name(guild.text_channels, name)
        try:
            parsed_start_time = parse_datetime_input(start_time) if start_time else None
            parsed_end_time = parse_datetime_input(end_time) if end_time else None
            validate_time_range(parsed_start_time, parsed_end_time)
        except TimeParseError as exc:
            await send_interaction_error(interaction, UserFacingError(str(exc)))
            return

        channel = await create_private_channel(guild, final_name, category)
        try:
            add_channel_record(
                channel.id,
                guild.id,
                final_name,
                start_time=parsed_start_time,
                end_time=parsed_end_time,
            )
        except Exception:
            context.logger.exception("Failed to persist created channel. Rolling back Discord channel")
            try:
                await channel.delete(reason="Rollback failed channel creation")
            except Exception:
                context.logger.exception("Failed to rollback created Discord channel")
            raise

        view = build_join_view(channel.id, channel.name)

        await interaction.followup.send(
            content=f"{channel.mention} ({channel.name})が作成されました",
            ephemeral=True,
        )

        try:
            if isinstance(interaction.channel, (discord.TextChannel, discord.Thread)):
                await interaction.channel.send(
                    content=build_join_announcement(channel, get_participant_count(channel)),
                    view=view,
                )
        except Exception:
            context.logger.exception("Failed to send join button to invoking channel")
