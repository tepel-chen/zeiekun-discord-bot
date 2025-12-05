import os
import logging
import sqlite3
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
ARCHIVE_CATEGORY = os.getenv("ARCHIVE_CATEGORY", "ARCHIVE")

RULE_TEMPLATE = """
参加してくださりありがとうございます！始めてのご参加のようなので、ルールをご確認ください。
* 問題に取り組むときは、できるだけ`/ctf chal`コマンドを利用してスレッドを作成してください。
* 問題が解けたら`/ctf solve`コマンドでスレッドタイトルを完了済みにしてください。
* 特に必要がなければ、CTF開催中はフラグ本体と完全なソルバーをシェアしないでください。(不正防止のため)
* CTF開催中は、そのCTFのルールを遵守してください。特に、フラグやソルバー、その他ヒントになるような情報をチームのメンバー以外に共有しないでください。
* CTF終了後はDiscord内でソルバーを共有するだけでなく、自分のブログなどでwriteupを作成していただいてもかまいません(CTFのルールは遵守してください)。他のメンバーの学習の機会にもなりますので、是非一度書いてみてください！

もしよろしければ下のボタンを押してご参加ください！可能でしたら #ctf-other にて簡単に自己紹介していただけると嬉しいです！
""".strip()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ctfbot")

DB_PATH = "ctf_channels.db"

def init_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ctf_channels (
            channel_id INTEGER PRIMARY KEY,
            guild_id INTEGER NOT NULL,
            channel_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def add_channel_record(channel_id: int, guild_id: int, channel_name: str):
    """Add a new channel to the database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO ctf_channels (channel_id, guild_id, channel_name)
        VALUES (?, ?, ?)
    """, (channel_id, guild_id, channel_name))
    conn.commit()
    conn.close()

def is_bot_created_channel(channel_id: int) -> bool:
    """Check if channel was created by the bot"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT channel_id FROM ctf_channels WHERE channel_id = ?
    """, (channel_id,))
    result = cursor.fetchone()
    conn.close()
    
    return result is not None

intents = discord.Intents.default()
intents.guilds = True
intents.members = True

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)
ctf_commands = app_commands.Group(name="ctf", description="CTF関連")


async def ensure_category(guild: discord.Guild, name: str) -> discord.CategoryChannel:
    for c in guild.categories:
        if c.name == name:
            return c
    return await guild.create_category(name)

def get_participant_count(ch: discord.TextChannel) -> int:
    return sum(1 for m in ch.members if not m.bot)

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
@ctf_commands.command(name="create", description="CTFチャンネルを作成する")
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
    
    add_channel_record(channel.id, guild.id, final_name)

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
            count = get_participant_count(channel)
            await interaction.channel.send(
                content=(
                    f"CTF用プライベートチャンネル {channel.mention} ({channel.name}) が作成されました\n"
                    f"参加するには以下のボタンをクリックしてください (現在の参加人数: {count}人)"
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
        await channel.send(f"{user.mention}が参加しました")
        try:
            if interaction.message is not None:
                view = interaction.message.components and discord.ui.View.from_message(interaction.message) or None
                count = get_participant_count(channel)
                new_content = (
                    f"CTF用プライベートチャンネル {channel.mention} ({channel.name}) が作成されました\n"
                    f"参加するには以下のボタンをクリックしてください (現在の参加人数: {count}人)"
                )
                await interaction.message.edit(content=new_content, view=view)
        except Exception:
            logger.exception("Failed to update join message with participant count")
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

@app_commands.checks.has_role(CTF_CREATOR_ROLE_ID)
@ctf_commands.command(name="archive", description="CTFチャンネルをアーカイブする")
async def move_category(interaction: discord.Interaction):
    guild = interaction.guild
    assert guild is not None, "This command must be used in a guild"
    channel = interaction.channel
    if not isinstance(channel, discord.TextChannel) or not is_bot_created_channel(channel.id):
        await interaction.response.send_message(
            "❌ このコマンドはbotによって作成されたチャンネルでのみ使用できます。",
            ephemeral=True
        )
        return
    
    try:
        category = await ensure_category(guild, ARCHIVE_CATEGORY)

        await channel.edit(category=category)
        await interaction.response.send_message(
            f"✅ チャンネル {channel.mention} をカテゴリー「{ARCHIVE_CATEGORY}」へ移動しました。"
        )
    except Exception as e:
        await interaction.response.send_message(
            f"❌ スレッド作成に失敗しました: {e}", ephemeral=True
        )


@app_commands.checks.has_role(CTF_ROLE_ID)
@ctf_commands.command(name="chal", description="CTFチャンネルでチャレンジスレッドを作製する")
@app_commands.describe(category="チャレンジのカテゴリ", name="チャレンジ名")
async def ctf_chal(interaction: discord.Interaction, category: str, name: str):
    channel = interaction.channel
    if not isinstance(channel, discord.TextChannel) or not is_bot_created_channel(channel.id):
        await interaction.response.send_message(
            "❌ このコマンドはbotによって作成されたチャンネルでのみ使用できます。",
            ephemeral=True
        )
        return
    
    try:
        await interaction.channel.create_thread(
            name=f"{name} [{category}]",
            type=discord.ChannelType.public_thread,
            auto_archive_duration=60
        )
        await interaction.response.send_message(
            f"✅ {interaction.user.mention} さんがスレッドを作成しました", ephemeral=False
        )
    except Exception as e:
        await interaction.response.send_message(
            f"❌ スレッド作成に失敗しました: {e}", ephemeral=True
        )
        
@app_commands.checks.has_role(CTF_ROLE_ID)
@ctf_commands.command(name="solve", description="CTFチャンネルのチャレンジスレッドを完了状態にする")
async def ctf_solve(interaction: discord.Interaction):
    channel = interaction.channel
    if not isinstance(channel, discord.Thread):
        await interaction.response.send_message("❌ このコマンドはスレッド内でのみ使用できます。", ephemeral=True)
        return

    if channel.owner_id != bot.user.id:
        await interaction.response.send_message("❌ このスレッドは bot が作成したものではありません。", ephemeral=True)
        return

    if not channel.name.startswith("✅"):
        await channel.edit(name=f"✅ {channel.name}")
        await interaction.response.send_message(f"✅ {interaction.user.mention} さんがスレッドを解決済みにしました！", ephemeral=False)
    else:
        await interaction.response.send_message("⚠️ すでに解決済みです。", ephemeral=True)


@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user} (id={bot.user.id})")
    init_database()
    logger.info("Database initialized")
    try:
        guild = discord.Object(id=GUILD_ID)
        await tree.sync(guild=guild)
        logger.info("Slash commands synced to the guild.")
    except Exception:
        logger.exception("Failed to sync commands")

guild_obj = discord.Object(id=GUILD_ID)
tree.add_command(ctf_commands, guild=guild_obj)

if __name__ == "__main__":
    if not TOKEN or TOKEN == "YOUR_BOT_TOKEN":
        raise SystemExit("Please set DISCORD_TOKEN env var")
    bot.run(TOKEN)
