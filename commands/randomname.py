import discord
from discord import app_commands
from wonderwords import RandomWord

from commands.permissions import command_metadata, require_registered_role
from interaction_errors import UserFacingError


@command_metadata(required_role=None, channel_scope="any")
def register_command(ctf_commands: app_commands.Group, context):
    """ランダムなチーム名候補を生成する。"""

    @require_registered_role(register_command, context)
    @ctf_commands.command(name="randomname", description="ランダムなチーム名を提案する")
    @app_commands.describe(count="個数")
    async def ctf_randomname(interaction: discord.Interaction, count: str):
        try:
            n = int(count)
        except:
            raise UserFacingError("countは数値を入力してください。")
        if n > 10 or n <= 0:
            raise UserFacingError("countの値が不正です。")
        r = RandomWord()
        cands = r.random_words(n, include_parts_of_speech=["nouns"])
        cands = [f'`full_weak_{cand}`' for cand in cands]
        await interaction.response.send_message(
            (
                "チーム名候補: \n" +
                "\n".join(cands)
            ),
            ephemeral=False,
        )
