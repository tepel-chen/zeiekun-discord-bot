from typing import Optional

import discord


def normalize_category(category: str) -> str:
    mappings = {
        "reversing": "Rev",
        "miscellaneous": "Misc",
    }

    lower_category = category.strip().lower()
    if lower_category in mappings:
        return mappings[lower_category]

    return category.title()


async def ensure_category(guild: discord.Guild, name: str) -> discord.CategoryChannel:
    for category in guild.categories:
        if category.name == name:
            return category
    return await guild.create_category(name)


def get_participant_count(channel: discord.TextChannel) -> int:
    return sum(1 for member in channel.members if not member.bot)


async def create_private_channel(
    guild: discord.Guild,
    name: str,
    category: Optional[discord.CategoryChannel],
) -> discord.TextChannel:
    overwrites = {guild.default_role: discord.PermissionOverwrite(view_channel=False)}

    if guild.me:
        overwrites[guild.me] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
        )

    return await guild.create_text_channel(name=name, category=category, overwrites=overwrites)


def allocate_channel_name(existing_channels, requested_name: str) -> str:
    final_name = f"ctf-{requested_name}"
    index = 1
    while discord.utils.get(existing_channels, name=final_name) is not None:
        index += 1
        final_name = f"ctf-{requested_name}-{index}"
    return final_name


def build_join_announcement(channel: discord.TextChannel, participant_count: int) -> str:
    return (
        f"CTF用プライベートチャンネル {channel.mention} ({channel.name}) が作成されました\n"
        f"参加するには以下のボタンをクリックしてください (現在の参加人数: {participant_count}人)"
    )


def filter_threads(threads, category: Optional[str] = None, solved: Optional[bool] = None):
    matching_threads = []
    for thread in threads:
        if category and f"[{category}]" not in thread.name:
            continue

        is_solved = thread.name.startswith("✅")
        if solved is not None and is_solved != solved:
            continue

        matching_threads.append(thread)

    return matching_threads


def build_search_response(matching_threads) -> str:
    response = "✅ 検索結果:\n"
    for thread in matching_threads[:25]:
        response += f"• {thread.mention}\n"

    if len(matching_threads) > 25:
        response += f"\n...他 {len(matching_threads) - 25} 件"

    return response


def build_missing_search_response(category: Optional[str], solved: Optional[bool]) -> str:
    filter_desc = ""
    if category:
        filter_desc += f"カテゴリ「{category}」"
    if solved is not None:
        status = "解決済み" if solved else "未解決"
        if filter_desc:
            filter_desc += f"({status})"
        else:
            filter_desc = status

    if filter_desc:
        return f"❌ {filter_desc}のスレッドが見つかりません。"
    return "❌ スレッドが見つかりません。"
