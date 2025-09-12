import os
import asyncio
import logging
from typing import Optional
from dotenv import load_dotenv

import discord
from discord import app_commands

load_dotenv(verbose=True)

TOKEN = os.getenv("DISCORD_TOKEN", "YOUR_BOT_TOKEN")
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", "0"))
CTF_CREATOR_ROLE_ID = int(os.getenv("CTF_CREATOR_ROLE_ID", "0"))
CTF_ROLE_ID = int(os.getenv("CTF_ROLE_ID", "0"))
CATEGORY_NAME = os.getenv("CTF_CATEGORY", "CTF")

RULE_TEMPLATE = """
参加してくださりありがとうございます！始めてのご参加のようなので、ルールをご確認ください。
* 問題に取り組むときは、できるだけスレッドを作成してください。スレッド名の例: 「XSS challenge(web)」
* 問題が解けたらスレッドタイトルを編集して✅をつけて下さい。例: 「✅ XSS challenge(web)」
* 特に必要がなければ、CTF開催中はフラグ本体と完全なソルバーをシェアしないでください。(不正防止のため)
* CTF開催中は、そのCTFのルールを遵守してください。特に、フラグやソルバー、その他ヒントになるような情報をチームのメンバー以外に共有しないでください。
* CTF終了後はDiscord内でソルバーを共有するだけでなく、自分のブログなどでwriteupを作成していただいてもかまいません(CTFのルールは遵守してください)。他のメンバーの学習の機会にもなりますので、是非一度書いてみてください！

もしよろしければ下のボタンを押してご参加ください！可能でしたら #ctf-other にて簡単に自己紹介していただけると嬉しいです！
""".strip()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ctfbot")

intents = discord.Intents.default()
intents.guilds = True
intents.members = True

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)


async def ensure_category(guild: discord.Guild, name: str) -> discord.CategoryChannel:
    for c in guild.categories:
        if c.name == name:
            return c
    return await guild.create_category(name)

async def create_private_channel(
    guild: discord.Guild,
    name: str,
    category: Optional[discord.CategoryChannel],
) -> discord.TextChannel:
    overwrites = {guild.default_role: discord.PermissionOverwrite(view_channel=False)}

    me = guild.me
    if me:
        overwrites[me] = discord.PermissionOverwrite(
            view_channel=True, send_messages=True, read_message_history=True
        )
    channel = await guild.create_text_channel(name=name, category=category, overwrites=overwrites)
    return channel


@app_commands.checks.has_role(CTF_CREATOR_ROLE_ID)
@app_commands.command(name="ctfcreate", description="CTFチャンネルを作成する")
@app_commands.describe(name="CTFの名前")
async def ctf_create(interaction: discord.Interaction, name: str):
    guild = interaction.guild
    assert guild is not None, "This command must be used in a guild"

    await interaction.response.defer(ephemeral=True, thinking=True)
    category = await ensure_category(guild, CATEGORY_NAME)

    final_name = f"ctf-{name}"
    i = 1
    while discord.utils.get(guild.text_channels, name=final_name) is not None:
        i += 1
        final_name = f"ctf-{name}-{i}"

    channel = await create_private_channel(guild, final_name, category)

    join_custom_id = f"ctf_join:{channel.id}"
    view = discord.ui.View(timeout=None)
    view.add_item(
        discord.ui.Button(
            label=f"{channel.name} に参加する",
            style=discord.ButtonStyle.primary,
            custom_id=join_custom_id,
        )
    )

    await interaction.followup.send(content=f"{channel.mention} ({channel.name})が作成されました", ephemeral=True)

    try:
        if isinstance(interaction.channel, (discord.TextChannel, discord.Thread)):
            await interaction.channel.send(
                content=(
                    f"CTF用プライベートチャンネル {channel.mention} ({channel.name}) が作成されました\n"
                    f"参加するには以下のボタンをクリックしてください"
                ),
                view=view,
            )
    except Exception:
        logger.exception("Failed to send join button to invoking channel")

async def interaction_join(interaction: discord.Interaction, custom_id: str, skip_check: bool=False):
    _, _, cid = custom_id.partition(":")
    try:
        channel_id = int(cid)
    except ValueError:
        await interaction.response.send_message("Button is misconfigured.", ephemeral=True)
        return

    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message("This only works inside a server.", ephemeral=True)
        return

    channel = guild.get_channel(channel_id) or await guild.fetch_channel(channel_id)
    if not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message("Target channel not found.", ephemeral=True)
        return

    user: discord.Member = interaction.user 

    if not any(role.id == CTF_ROLE_ID for role in user.roles) and not skip_check:
        ctf_role = guild.get_role(CTF_ROLE_ID)
        join_custom_id = f"ctf_join_new:{channel.id}"
        view = discord.ui.View(timeout=None)
        view.add_item(
            discord.ui.Button(
                label=f"ルールを読みました！ {channel.name} に参加する",
                style=discord.ButtonStyle.primary,
                custom_id=join_custom_id,
            )
        )
        await interaction.response.send_message(RULE_TEMPLATE, ephemeral=True, view=view)
        return

    try:
        current = channel.overwrites_for(user)
        if current.view_channel:
            await interaction.response.send_message(f"{channel.mention} に既に参加しています", ephemeral=True)
            return

        await channel.set_permissions(
            user,
            view_channel=True,
            send_messages=True,
            read_message_history=True,
        )
        await interaction.response.send_message(f"{channel.mention}に参加しました", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message(
            "そのチャンネルの権限を編集する権限がありません。", ephemeral=True
        )
    except Exception:
        logger.exception("Failed to grant access")
        await interaction.response.send_message("Something went wrong.", ephemeral=True)

async def interaction_join_new(interaction: discord.Interaction, custom_id: str):
    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message("This only works inside a server.", ephemeral=True)
        return

    user: discord.Member = interaction.user
    ctf_role = guild.get_role(CTF_ROLE_ID)

    try:
        await user.add_roles(ctf_role, reason="CTF join gate passed")
    except discord.Forbidden:
        await interaction.response.send_message(
            "ロールを付与できません（権限またはロール順を確認してください）。", ephemeral=True
        )
        return

    await interaction_join(interaction, custom_id, True)

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type != discord.InteractionType.component:
        return

    data = interaction.data or {}
    custom_id = data.get("custom_id")
    if not isinstance(custom_id, str):
        return

    if custom_id.startswith("ctf_join:"):
        await interaction_join(interaction, custom_id, False)
    elif custom_id.startswith("ctf_join_new:"):
        await interaction_join_new(interaction, custom_id)

@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user} (id={bot.user.id})")
    try:
        if GUILD_ID:
            guild = discord.Object(id=GUILD_ID)
            await tree.sync(guild=guild)
            logger.info("Slash commands synced to the guild.")
        else:
            await tree.sync()
            logger.info("Slash commands globally synced.")
    except Exception:
        logger.exception("Failed to sync commands")

if GUILD_ID:
    guild_obj = discord.Object(id=GUILD_ID)
    tree.add_command(ctf_create, guild=guild_obj)
else:
    tree.add_command(ctf_create)

if __name__ == "__main__":
    if not TOKEN or TOKEN == "YOUR_BOT_TOKEN":
        raise SystemExit("Please set DISCORD_TOKEN env var")
    bot.run(TOKEN)
