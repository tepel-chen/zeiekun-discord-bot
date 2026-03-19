import discord

from services.channel_service import build_join_announcement, get_participant_count


RULE_TEMPLATE = """
参加してくださりありがとうございます！始めてのご参加のようなので、ルールをご確認ください。
* 問題に取り組むときは、できるだけ`/ctf chal`コマンドを利用してスレッドを作成してください。
* 問題が解けたら`/ctf solve`コマンドでスレッドタイトルを完了済みにしてください。
* 特に必要がなければ、CTF開催中はフラグ本体と完全なソルバーをシェアしないでください。(不正防止のため)
* CTF開催中は、そのCTFのルールを遵守してください。特に、フラグやソルバー、その他ヒントになるような情報をチームのメンバー以外に共有しないでください。
* CTF終了後はDiscord内でソルバーを共有するだけでなく、自分のブログなどでwriteupを作成していただいてもかまいません(CTFのルールは遵守してください)。他のメンバーの学習の機会にもなりますので、是非一度書いてみてください！

もしよろしければ下のボタンを押してご参加ください！可能でしたら #ctf-other にて簡単に自己紹介していただけると嬉しいです！
""".strip()


class JoinService:
    def __init__(self, logger, ctf_role_id: int):
        self.logger = logger
        self.ctf_role_id = ctf_role_id

    async def route_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return

        data = interaction.data or {}
        custom_id = data.get("custom_id")
        if not isinstance(custom_id, str):
            return

        if custom_id.startswith("ctf_join:"):
            await self.handle_join(interaction, custom_id, False)
        elif custom_id.startswith("ctf_join_new:"):
            await self.handle_join_new(interaction, custom_id)

    async def handle_join(self, interaction: discord.Interaction, custom_id: str, skip_check: bool = False):
        _, _, channel_id_text = custom_id.partition(":")
        try:
            channel_id = int(channel_id_text)
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
        if not any(role.id == self.ctf_role_id for role in user.roles) and not skip_check:
            await interaction.response.send_message(
                RULE_TEMPLATE,
                ephemeral=True,
                view=self.build_join_gate_view(channel.id, channel.name),
            )
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
            await self.update_join_message(interaction, channel)
        except discord.Forbidden:
            await interaction.response.send_message(
                "そのチャンネルの権限を編集する権限がありません。", ephemeral=True
            )
        except Exception:
            self.logger.exception("Failed to grant access")
            await interaction.response.send_message("Something went wrong.", ephemeral=True)

    async def handle_join_new(self, interaction: discord.Interaction, custom_id: str):
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("This only works inside a server.", ephemeral=True)
            return

        user: discord.Member = interaction.user
        ctf_role = guild.get_role(self.ctf_role_id)

        try:
            await user.add_roles(ctf_role, reason="CTF join gate passed")
        except discord.Forbidden:
            await interaction.response.send_message(
                "ロールを付与できません（権限またはロール順を確認してください）。", ephemeral=True
            )
            return

        await self.handle_join(interaction, custom_id, True)

    def build_join_gate_view(self, channel_id: int, channel_name: str) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        view.add_item(
            discord.ui.Button(
                label=f"ルールを読みました！ {channel_name} に参加する",
                style=discord.ButtonStyle.primary,
                custom_id=f"ctf_join_new:{channel_id}",
            )
        )
        return view

    async def update_join_message(self, interaction: discord.Interaction, channel: discord.TextChannel):
        try:
            if interaction.message is None:
                return

            view = interaction.message.components and discord.ui.View.from_message(interaction.message) or None
            content = build_join_announcement(channel, get_participant_count(channel))
            await interaction.message.edit(content=content, view=view)
        except Exception:
            self.logger.exception("Failed to update join message with participant count")
