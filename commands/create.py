import discord
from discord import app_commands

from db import add_channel_record, is_bot_created_channel
from services.join_service import build_join_view
from services.channel_service import (
    allocate_channel_name,
    build_join_announcement,
    create_private_channel,
    ensure_category,
    get_participant_count,
)
from services.time_service import TimeParseError, parse_datetime_input


def register_command(ctf_commands: app_commands.Group, context):
    @app_commands.checks.has_role(context.ctf_creator_role_id)
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
        current_channel = interaction.channel
        if isinstance(current_channel, discord.TextChannel) and is_bot_created_channel(current_channel.id):
            await interaction.response.send_message(
                "❌ このコマンドはbotによって作成されたチャンネル内では使用できません。",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        category = await ensure_category(guild, context.category_name)
        final_name = allocate_channel_name(guild.text_channels, name)
        try:
            parsed_start_time = parse_datetime_input(start_time) if start_time else None
            parsed_end_time = parse_datetime_input(end_time) if end_time else None
        except TimeParseError as exc:
            await interaction.followup.send(content=str(exc), ephemeral=True)
            return

        channel = await create_private_channel(guild, final_name, category)

        add_channel_record(
            channel.id,
            guild.id,
            final_name,
            start_time=parsed_start_time,
            end_time=parsed_end_time,
        )

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
