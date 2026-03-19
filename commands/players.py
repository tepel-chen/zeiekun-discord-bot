import discord
from discord import app_commands

from db import get_participants, is_bot_created_channel


def register_command(ctf_commands: app_commands.Group, context):
    @app_commands.checks.has_role(context.ctf_role_id)
    @ctf_commands.command(name="players", description="CTF参加者の参加種別を確認する")
    async def ctf_players(interaction: discord.Interaction):
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel) or not is_bot_created_channel(channel.id):
            await interaction.response.send_message(
                "❌ このコマンドはbotによって作成されたチャンネルでのみ使用できます。",
                ephemeral=True,
            )
            return

        participants = get_participants(channel.id)
        if not participants:
            await interaction.response.send_message(
                "❌ 参加者情報がありません。",
                ephemeral=True,
            )
            return

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
