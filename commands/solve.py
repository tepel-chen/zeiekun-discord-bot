import discord
from discord import app_commands

from interaction_errors import UserFacingError


def register_command(ctf_commands: app_commands.Group, context):
    @app_commands.checks.has_role(context.ctf_role_id)
    @ctf_commands.command(name="solve", description="CTFチャンネルのチャレンジスレッドを完了状態にする")
    async def ctf_solve(interaction: discord.Interaction):
        channel = interaction.channel
        if not isinstance(channel, discord.Thread):
            raise UserFacingError("❌ このコマンドはスレッド内でのみ使用できます。")

        if channel.owner_id != context.bot.user.id:
            raise UserFacingError("❌ このスレッドは bot が作成したものではありません。")

        if not channel.name.startswith("✅"):
            await channel.edit(name=f"✅ {channel.name}")
            await interaction.response.send_message(
                f"✅ {interaction.user.mention} さんがスレッドを解決済みにしました！",
                ephemeral=False,
            )
        else:
            await interaction.response.send_message("⚠️ すでに解決済みです。", ephemeral=True)
