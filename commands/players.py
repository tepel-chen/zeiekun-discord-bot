import discord
from discord import app_commands

from commands.permissions import command_metadata, require_registered_context, require_registered_role
from db import get_participants
from interaction_errors import UserFacingError


@command_metadata(required_role="ctf", channel_scope="bot_ctf_channel_or_thread")
def register_command(ctf_commands: app_commands.Group, context):
    """CTF参加者を参加種別ごとに一覧表示する。"""

    @require_registered_role(register_command, context)
    @require_registered_context(register_command, context)
    @ctf_commands.command(name="players", description="CTF参加者の参加種別を確認する")
    async def ctf_players(interaction: discord.Interaction):
        channel = interaction.channel
        target_channel_id = channel.parent_id if isinstance(channel, discord.Thread) else channel.id

        participants = get_participants(target_channel_id)
        if not participants:
            raise UserFacingError("❌ 参加者情報がありません。")

        grouped = {"play2win": [], "play4fun": []}
        for participant in participants:
            grouped.setdefault(participant.participation_type, []).append(f"<@{participant.user_id}>")

        total_count = len(participants)
        lines = [f"✅ 参加者一覧 (合計: {total_count}人)"]
        for participation_type in ("play2win", "play4fun"):
            players = grouped.get(participation_type, [])
            lines.append(f"{participation_type}: {len(players)}人")
            if players:
                lines.append(", ".join(players))

        await interaction.response.send_message("\n".join(lines), ephemeral=True)
