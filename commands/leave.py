import discord
from discord import app_commands

from commands.permissions import command_metadata, require_registered_context, require_registered_role
from db import (
    delete_participant_record,
    get_participant,
    get_root_channel_record,
    get_team_channel_record,
)
from interaction_errors import UserFacingError


@command_metadata(required_role="ctf", channel_scope="bot_ctf_channel")
def register_command(ctf_commands: app_commands.Group, context):
    """参加中のCTFチャンネルから退出し、権限を外す。"""

    @require_registered_role(register_command, context)
    @require_registered_context(register_command, context)
    @ctf_commands.command(name="leave", description="CTFチャンネルから退出する")
    async def ctf_leave(interaction: discord.Interaction):
        guild = interaction.guild
        channel = interaction.channel
        if guild is None:
            raise UserFacingError("This command must be used in a guild.")

        participant = get_participant(channel.id, interaction.user.id)
        if participant is None:
            raise UserFacingError("❌ まだこのCTFに参加していません。")

        root_record = get_root_channel_record(channel.id)
        if root_record is not None and getattr(root_record, "disclosed", 0):
            raise UserFacingError("❌ disclose 後は leave できません。")
        target_channels = []
        if root_record is not None:
            root_channel = guild.get_channel(root_record.channel_id)
            if isinstance(root_channel, discord.TextChannel):
                target_channels.append(root_channel)
            play2win_record = get_team_channel_record(root_record.channel_id, "play2win")
            if play2win_record is not None:
                play2win_channel = guild.get_channel(play2win_record.channel_id)
                if isinstance(play2win_channel, discord.TextChannel):
                    target_channels.append(play2win_channel)
        if not target_channels:
            target_channels = [channel]

        seen_ids = set()
        deduped_channels = []
        for target_channel in target_channels:
            if target_channel.id in seen_ids:
                continue
            seen_ids.add(target_channel.id)
            deduped_channels.append(target_channel)

        for target_channel in deduped_channels:
            await target_channel.set_permissions(interaction.user, overwrite=None)

        delete_participant_record(channel.id, interaction.user.id)

        await interaction.response.send_message(
            "✅ CTFから退出しました。",
            ephemeral=True,
        )

        notice = f"{interaction.user.mention} がこの CTF から退出しました。"
        for target_channel in deduped_channels:
            await target_channel.send(notice)
