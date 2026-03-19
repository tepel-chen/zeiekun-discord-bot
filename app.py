import logging
import asyncio

import discord
from discord import app_commands

from commands.context import CommandContext
from commands.registry import register_commands
from db import init_database
from services.join_service import JoinService
from services.split_service import SplitService


def create_intents():
    intents = discord.Intents.default()
    intents.guilds = True
    intents.members = True
    return intents


def create_application(settings):
    logger = logging.getLogger("ctfbot")
    bot = discord.Client(intents=create_intents())
    tree = app_commands.CommandTree(bot)
    ctf_commands = app_commands.Group(name="ctf", description="CTF関連")

    context = CommandContext(
        bot=bot,
        logger=logger,
        category_name=settings.category_name,
        archive_category=settings.archive_category,
        ctf_creator_role_id=settings.ctf_creator_role_id,
        ctf_role_id=settings.ctf_role_id,
    )
    register_commands(ctf_commands, context)

    split_service = SplitService(bot=bot, logger=logger)
    join_service = JoinService(logger=logger, ctf_role_id=settings.ctf_role_id, split_service=split_service)
    split_task = None

    @bot.event
    async def on_interaction(interaction: discord.Interaction):
        await join_service.route_interaction(interaction)

    @bot.event
    async def on_ready():
        nonlocal split_task
        logger.info(f"Logged in as {bot.user} (id={bot.user.id})")
        init_database()
        logger.info("Database initialized")
        try:
            guild = discord.Object(id=settings.guild_id)
            await tree.sync(guild=guild)
            logger.info("Slash commands synced to the guild.")
        except Exception:
            logger.exception("Failed to sync commands")
        if split_task is None or split_task.done():
            split_task = asyncio.create_task(split_loop())

    async def split_loop():
        while not bot.is_closed():
            try:
                await split_service.run_pending_splits(settings.guild_id)
            except Exception:
                logger.exception("Failed to process pending channel splits")
            await asyncio.sleep(60)

    guild_obj = discord.Object(id=settings.guild_id)
    tree.add_command(ctf_commands, guild=guild_obj)

    return bot, tree, ctf_commands, join_service
