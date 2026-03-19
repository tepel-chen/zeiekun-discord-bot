from datetime import datetime, timedelta

import discord

from db import (
    add_channel_record,
    delete_channel_record,
    get_channels_pending_split,
    get_participants,
    get_root_channel_record,
    get_team_channels,
    get_team_channel_record,
    update_channel_record,
)
from services.channel_service import create_private_channel
from services.time_service import tokyo_now


TEAM_TYPES = ("play2win", "play4fun")


def should_split_channel(start_time: datetime | None, now: datetime) -> bool:
    if start_time is None:
        return False
    return now >= start_time - timedelta(hours=3)


def build_split_channel_name(base_name: str, team_type: str) -> str:
    suffix = "p2w" if team_type == "play2win" else "p4f"
    if base_name.endswith("-p2w") or base_name.endswith("-p4f"):
        base_name = base_name.rsplit("-", 1)[0]
    return f"{base_name}-{suffix}"


class SplitService:
    def __init__(self, bot: discord.Client, logger):
        self.bot = bot
        self.logger = logger

    async def run_pending_splits(self, guild_id: int):
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            return

        now = tokyo_now()
        for record in get_channels_pending_split(now):
            await self.reconcile_channel_state(guild, record.channel_id, now)

    async def reconcile_channel_state(self, guild: discord.Guild, root_channel_id: int, now: datetime | None = None):
        root_record = get_root_channel_record(root_channel_id)
        if root_record is None:
            return

        current_time = now or tokyo_now()
        if root_record.team_mode == "split":
            await self.split_channel(guild, root_record.channel_id, force=True)
            return
        if root_record.team_mode == "join":
            await self.merge_channel(guild, root_record.channel_id)
            return
        if should_split_channel(root_record.start_time, current_time):
            await self.split_channel(guild, root_record.channel_id, force=False)

    async def split_channel(self, guild: discord.Guild, root_channel_id: int, force: bool = False):
        root_record = get_root_channel_record(root_channel_id)
        if root_record is None or root_record.split_completed:
            return

        participants = get_participants(root_channel_id)
        team_counts = {
            team_type: sum(1 for participant in participants if participant.participation_type == team_type)
            for team_type in TEAM_TYPES
        }
        if not force and (team_counts["play2win"] < 3 or team_counts["play4fun"] < 3):
            return

        play4fun_channel = guild.get_channel(root_record.channel_id) or await guild.fetch_channel(root_record.channel_id)
        if not isinstance(play4fun_channel, discord.TextChannel):
            return

        base_name = root_record.channel_name
        play4fun_name = build_split_channel_name(base_name, "play4fun")
        play2win_name = build_split_channel_name(base_name, "play2win")
        original_play4fun_name = play4fun_channel.name
        play2win_record = get_team_channel_record(root_record.channel_id, "play2win")
        created_play2win_channel = False
        if play2win_record is None:
            play2win_channel = await create_private_channel(guild, play2win_name, play4fun_channel.category)
            created_play2win_channel = True
            try:
                add_channel_record(
                    play2win_channel.id,
                    guild.id,
                    play2win_name,
                    root_channel_id=root_record.channel_id,
                    team_type="play2win",
                    team_mode=root_record.team_mode,
                    split_completed=1,
                    start_time=root_record.start_time,
                    end_time=root_record.end_time,
                )
            except Exception:
                await play2win_channel.delete(reason="Rollback failed split setup")
                raise
            original_play2win_name = play2win_channel.name
            original_play2win_category = play2win_channel.category
        else:
            play2win_channel = guild.get_channel(play2win_record.channel_id) or await guild.fetch_channel(play2win_record.channel_id)
            if not isinstance(play2win_channel, discord.TextChannel):
                return
            original_play2win_name = play2win_channel.name
            original_play2win_category = play2win_channel.category
            await play2win_channel.edit(name=play2win_name, category=play4fun_channel.category)

        await play4fun_channel.edit(name=play4fun_name)
        try:
            updated = update_channel_record(
                root_record.channel_id,
                channel_name=play4fun_name,
                team_type="play4fun",
                team_mode=root_record.team_mode,
                split_completed=1,
            )
            if not updated:
                raise RuntimeError("Failed to update root split record")
            if play2win_record is not None:
                updated = update_channel_record(
                    play2win_channel.id,
                    channel_name=play2win_name,
                    team_type="play2win",
                    team_mode=root_record.team_mode,
                    split_completed=1,
                    start_time=root_record.start_time,
                    end_time=root_record.end_time,
                )
                if not updated:
                    raise RuntimeError("Failed to update team split record")
        except Exception:
            await play4fun_channel.edit(name=original_play4fun_name)
            if created_play2win_channel:
                try:
                    await play2win_channel.delete(reason="Rollback failed split setup")
                finally:
                    delete_channel_record(play2win_channel.id)
            else:
                await play2win_channel.edit(name=original_play2win_name, category=original_play2win_category)
            raise

        for participant in participants:
            member = guild.get_member(participant.user_id)
            if member is None:
                continue
            await self.sync_member_channels(
                play4fun_channel,
                play2win_channel,
                member,
                participant.participation_type,
            )

        await play4fun_channel.send("チームを分割しました。こちらは `play4fun` 用チャンネルです。")
        await play2win_channel.send("チームを分割しました。こちらは `play2win` 用チャンネルです。")

    async def merge_channel(self, guild: discord.Guild, root_channel_id: int):
        root_record = get_root_channel_record(root_channel_id)
        if root_record is None or not root_record.split_completed:
            return

        root_channel = guild.get_channel(root_record.channel_id) or await guild.fetch_channel(root_record.channel_id)
        if not isinstance(root_channel, discord.TextChannel):
            return

        merged_name = build_base_channel_name(root_record.channel_name)
        original_root_name = root_channel.name
        await root_channel.edit(name=merged_name)
        team_channels = get_team_channels(root_record.channel_id)
        try:
            updated = update_channel_record(
                root_record.channel_id,
                channel_name=merged_name,
                team_type="all",
                split_completed=0,
            )
            if not updated:
                raise RuntimeError("Failed to update merged root record")
            for team_record in team_channels:
                updated = update_channel_record(team_record.channel_id, split_completed=0)
                if not updated:
                    raise RuntimeError("Failed to update merged team record")
        except Exception:
            await root_channel.edit(name=original_root_name)
            raise

        participants = get_participants(root_record.channel_id)
        for participant in participants:
            member = guild.get_member(participant.user_id)
            if member is None:
                continue
            await root_channel.set_permissions(
                member,
                view_channel=True,
                send_messages=True,
                read_message_history=True,
            )

        for team_record in team_channels:
            team_channel = guild.get_channel(team_record.channel_id) or await guild.fetch_channel(team_record.channel_id)
            if not isinstance(team_channel, discord.TextChannel):
                continue
            for participant in participants:
                member = guild.get_member(participant.user_id)
                if member is None:
                    continue
                await team_channel.set_permissions(member, overwrite=discord.PermissionOverwrite(view_channel=False))
        await root_channel.send("チームを合同に戻しました。全員このチャンネルを利用してください。")

    async def sync_participant_channels(self, guild: discord.Guild, channel_id: int, member: discord.Member, participation_type: str):
        root_record = get_root_channel_record(channel_id)
        if root_record is None or not root_record.split_completed:
            return

        play4fun_channel = guild.get_channel(root_record.channel_id) or await guild.fetch_channel(root_record.channel_id)
        play2win_record = get_team_channel_record(root_record.channel_id, "play2win")
        if play2win_record is None:
            return
        play2win_channel = guild.get_channel(play2win_record.channel_id) or await guild.fetch_channel(play2win_record.channel_id)
        if not isinstance(play4fun_channel, discord.TextChannel) or not isinstance(play2win_channel, discord.TextChannel):
            return

        if getattr(root_record, "disclosed", 0):
            await self.grant_both_team_channels(play4fun_channel, play2win_channel, member)
            return

        await self.sync_member_channels(play4fun_channel, play2win_channel, member, participation_type)

    async def disclose_channel(self, guild: discord.Guild, root_channel_id: int):
        root_record = get_root_channel_record(root_channel_id)
        if root_record is None:
            return False
        if not root_record.split_completed:
            update_channel_record(root_record.channel_id, disclosed=1)
            return True

        play4fun_channel = guild.get_channel(root_record.channel_id) or await guild.fetch_channel(root_record.channel_id)
        play2win_record = get_team_channel_record(root_record.channel_id, "play2win")
        if play2win_record is None:
            return False
        play2win_channel = guild.get_channel(play2win_record.channel_id) or await guild.fetch_channel(play2win_record.channel_id)
        if not isinstance(play4fun_channel, discord.TextChannel) or not isinstance(play2win_channel, discord.TextChannel):
            return False

        participants = get_participants(root_record.channel_id)
        for participant in participants:
            member = guild.get_member(participant.user_id)
            if member is None:
                continue
            await self.grant_both_team_channels(play4fun_channel, play2win_channel, member)

        update_channel_record(root_record.channel_id, disclosed=1)
        update_channel_record(play2win_channel.id, disclosed=1)
        return True

    async def grant_both_team_channels(
        self,
        play4fun_channel: discord.TextChannel,
        play2win_channel: discord.TextChannel,
        member: discord.Member,
    ):
        await play4fun_channel.set_permissions(
            member,
            view_channel=True,
            send_messages=True,
            read_message_history=True,
        )
        await play2win_channel.set_permissions(
            member,
            view_channel=True,
            send_messages=True,
            read_message_history=True,
        )

    async def sync_member_channels(
        self,
        play4fun_channel: discord.TextChannel,
        play2win_channel: discord.TextChannel,
        member: discord.Member,
        participation_type: str,
    ):
        if participation_type == "play2win":
            await play4fun_channel.set_permissions(member, overwrite=discord.PermissionOverwrite(view_channel=False))
            await play2win_channel.set_permissions(
                member,
                view_channel=True,
                send_messages=True,
                read_message_history=True,
            )
        else:
            await play4fun_channel.set_permissions(
                member,
                view_channel=True,
                send_messages=True,
                read_message_history=True,
            )
            await play2win_channel.set_permissions(member, overwrite=discord.PermissionOverwrite(view_channel=False))

    def resolve_target_channel_id(self, source_channel_id: int, participation_type: str) -> int:
        root_record = get_root_channel_record(source_channel_id)
        if root_record is None:
            return source_channel_id
        if not root_record.split_completed or participation_type == "play4fun":
            return root_record.channel_id
        team_record = get_team_channel_record(root_record.channel_id, "play2win")
        return team_record.channel_id if team_record is not None else root_record.channel_id


def build_base_channel_name(channel_name: str) -> str:
    if channel_name.endswith("-p2w") or channel_name.endswith("-p4f"):
        return channel_name.rsplit("-", 1)[0]
    return channel_name
