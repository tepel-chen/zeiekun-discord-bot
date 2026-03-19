import discord
from discord import app_commands

from db import UPDATE_UNSET, get_root_channel_record, is_bot_created_channel, update_channel_record
from interaction_errors import UserFacingError
from services.split_service import SplitService
from services.time_service import (
    TimeParseError,
    format_datetime,
    format_hour_delta,
    parse_datetime_input,
    validate_time_range,
)


def register_command(ctf_commands: app_commands.Group, context):
    @app_commands.checks.has_role(context.ctf_creator_role_id)
    @ctf_commands.command(name="ctfconf", description="CTF設定を更新する")
    @app_commands.describe(
        start_time="開始時刻 (`tomorrow 21:00`, `3/20 18:00` など)",
        end_time="終了時刻 (`tomorrow 21:00`, `3/20 18:00` など)",
        teammode="チームの扱い (`auto`, `split`, `join`)",
    )
    @app_commands.choices(
        teammode=[
            app_commands.Choice(name="auto", value="auto"),
            app_commands.Choice(name="split", value="split"),
            app_commands.Choice(name="join", value="join"),
        ]
    )
    async def ctfconf(
        interaction: discord.Interaction,
        start_time: str | None = None,
        end_time: str | None = None,
        teammode: app_commands.Choice[str] | None = None,
    ):
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel) or not is_bot_created_channel(channel.id):
            raise UserFacingError("❌ このコマンドはbotによって作成されたチャンネルでのみ使用できます。")

        if start_time is None and end_time is None and teammode is None:
            raise UserFacingError("❌ 更新する値を1つ以上指定してください。")

        try:
            parsed_start_time = parse_datetime_input(start_time) if start_time is not None else None
            parsed_end_time = parse_datetime_input(end_time) if end_time is not None else None
        except TimeParseError as exc:
            raise UserFacingError(str(exc)) from exc

        root_record = get_root_channel_record(channel.id)
        target_channel_id = root_record.channel_id if root_record is not None else channel.id
        if teammode is not None and root_record is not None and getattr(root_record, "disclosed", 0):
            raise UserFacingError("❌ disclose 後は teammode を変更できません。")
        effective_start_time = parsed_start_time if start_time is not None else (root_record.start_time if root_record is not None else None)
        effective_end_time = parsed_end_time if end_time is not None else (root_record.end_time if root_record is not None else None)
        try:
            validate_time_range(effective_start_time, effective_end_time)
        except TimeParseError as exc:
            raise UserFacingError(str(exc)) from exc
        updated = update_channel_record(
            target_channel_id,
            team_mode=teammode.value if teammode is not None else UPDATE_UNSET,
            start_time=parsed_start_time if start_time is not None else UPDATE_UNSET,
            end_time=parsed_end_time if end_time is not None else UPDATE_UNSET,
        )
        if not updated:
            raise UserFacingError("❌ CTF設定の更新に失敗しました。")

        messages = []
        if start_time is not None:
            messages.append(f"開始: {format_datetime(parsed_start_time)} ({format_hour_delta(parsed_start_time, parsed_start_time)})")
        if end_time is not None:
            messages.append(f"終了: {format_datetime(parsed_end_time)} ({format_hour_delta(parsed_end_time, parsed_end_time)})")
        if teammode is not None:
            messages.append(f"teammode: `{teammode.value}`")

        if interaction.guild is not None:
            split_service = SplitService(context.bot, context.logger)
            await split_service.reconcile_channel_state(interaction.guild, target_channel_id)

        result_message = "✅ CTF設定を更新しました\n" + "\n".join(messages)
        await interaction.response.send_message(result_message, ephemeral=True)
        if isinstance(channel, discord.TextChannel):
            await channel.send(
                f"{interaction.user.mention} が CTF 設定を更新しました。\n" + "\n".join(messages)
            )
