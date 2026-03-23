import discord
from discord import app_commands

from db import (
    get_participant,
    get_root_channel_record,
    get_team_channel_record,
    is_bot_created_channel,
    upsert_participant_record,
)
from interaction_errors import UserFacingError
from services.split_service import SplitService


def register_command(ctf_commands: app_commands.Group, context):
    @app_commands.checks.has_role(context.ctf_role_id)
    @ctf_commands.command(name="switchteam", description="参加種別を切り替える")
    @app_commands.describe(team="切り替え先の参加種別")
    @app_commands.choices(
        team=[
            app_commands.Choice(name="play2win", value="play2win"),
            app_commands.Choice(name="play4fun", value="play4fun"),
        ]
    )
    async def ctf_switchteam(interaction: discord.Interaction, team: app_commands.Choice[str]):
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel) or not is_bot_created_channel(channel.id):
            raise UserFacingError("❌ このコマンドはbotによって作成されたチャンネルでのみ使用できます。")

        participant = get_participant(channel.id, interaction.user.id)
        if participant is None:
            raise UserFacingError("❌ まだこのCTFに参加していません。参加ボタンから参加してください。")
        previous_team = participant.participation_type
        if previous_team == team.value:
            raise UserFacingError(f"⚠️ 既に `{team.value}` に参加しています。")
        root_record = get_root_channel_record(channel.id)
        if root_record is not None and getattr(root_record, "disclosed", 0):
            raise UserFacingError("❌ disclose 後は switchteam できません。")

        upsert_participant_record(channel.id, interaction.user.id, team.value)
        split_service = SplitService(context.bot, context.logger)
        if isinstance(interaction.user, discord.Member):
            await split_service.sync_participant_channels(interaction.guild, channel.id, interaction.user, team.value)
        await interaction.response.send_message(
            f"✅ 参加種別を `{team.value}` に切り替えました。",
            ephemeral=True,
        )
        notice = f"{interaction.user.mention}が `{team.value}` にチーム変更しました。"
        if root_record is not None and root_record.split_completed:
            root_channel = None
            play2win_channel = None
            root_channel = interaction.guild.get_channel(root_record.channel_id)
            if not isinstance(root_channel, discord.TextChannel):
                root_channel = None
            play2win_record = get_team_channel_record(root_record.channel_id, "play2win")
            if play2win_record is not None:
                fetched_channel = interaction.guild.get_channel(play2win_record.channel_id)
                if isinstance(fetched_channel, discord.TextChannel):
                    play2win_channel = fetched_channel

            previous_channel = play2win_channel if previous_team == "play2win" else root_channel
            current_channel = play2win_channel if team.value == "play2win" else root_channel

            if isinstance(previous_channel, discord.TextChannel):
                await previous_channel.send(notice)
            if (
                isinstance(current_channel, discord.TextChannel)
                and current_channel.id != getattr(previous_channel, "id", None)
            ):
                await current_channel.send(f"{interaction.user.mention}が `{team.value}` として参加しました")
        else:
            await channel.send(notice)
