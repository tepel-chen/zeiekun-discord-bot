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
        notice = f"{interaction.user.mention} が参加種別を `{team.value}` に切り替えました。"
        if root_record is not None and root_record.split_completed:
            target_channels = []
            root_channel = interaction.guild.get_channel(root_record.channel_id)
            if isinstance(root_channel, discord.TextChannel):
                target_channels.append(root_channel)
            play2win_record = get_team_channel_record(root_record.channel_id, "play2win")
            if play2win_record is not None:
                play2win_channel = interaction.guild.get_channel(play2win_record.channel_id)
                if isinstance(play2win_channel, discord.TextChannel):
                    target_channels.append(play2win_channel)
            sent_ids = set()
            for target_channel in target_channels:
                if target_channel.id in sent_ids:
                    continue
                sent_ids.add(target_channel.id)
                await target_channel.send(notice)
        else:
            await channel.send(notice)
