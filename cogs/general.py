import os
from typing import Any, Optional

import discord
from discord.ext import commands


class HelpView(discord.ui.View):
    def __init__(self, mapping: dict, context: commands.Context, help_command: Any) -> None:
        super().__init__(timeout=60)
        self.mapping = mapping
        self.context = context
        self.help_command = help_command
        self.message: Optional[discord.Message] = None
        self.author_id: int = context.author.id

        options = []
        for cog in mapping.keys():
            if cog and mapping[cog]:
                cog_name = cog.qualified_name if cog else "ไม่มีหมวดหมู่"
                description = cog.description[:50] if cog and cog.description else "ไม่มีคำอธิบาย"
                options.append(
                    discord.SelectOption(
                        label=cog_name,
                        description=description,
                        emoji="📁"
                    )
                )

        if not options:
            options.append(
                discord.SelectOption(
                    label="ไม่มีหมวดหมู่",
                    description="ไม่มีคำสั่งที่ใช้ได้",
                    emoji="❌"
                )
            )

        self.category_select.options = options

    @discord.ui.select(placeholder="เลือกหมวดหมู่...", min_values=1, max_values=1)
    async def category_select(self, interaction: discord.Interaction, select: discord.ui.Select) -> None:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ เมนูนี้ไม่ใช่สำหรับคุณ!", ephemeral=True)
            return

        selected_category = select.values[0]
        selected_cog = None

        for cog in self.mapping.keys():
            if cog and cog.qualified_name == selected_category:
                selected_cog = cog
                break

        if not selected_cog:
            await interaction.response.send_message("❌ ไม่พบหมวดหมู่!", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"📚 {selected_cog.qualified_name}",
            description=selected_cog.description or "ไม่มีคำอธิบาย",
            color=discord.Color.blurple()
        )

        filtered = []
        for cmd in selected_cog.get_commands():
            try:
                can_run = await cmd.can_run(self.context)
                if can_run:
                    filtered.append(cmd)
            except commands.CheckFailure:
                continue
            except Exception:
                filtered.append(cmd)

        if filtered:
            for cmd in sorted(filtered, key=lambda c: c.name):
                embed.add_field(
                    name=f"`{self.context.clean_prefix}{cmd.name} {cmd.signature}`",
                    value=cmd.help or "ไม่มีคำอธิบาย",
                    inline=False
                )
        else:
            embed.add_field(name="คำสั่ง", value="ไม่มีคำสั่งที่ใช้ได้", inline=False)

        embed.set_footer(text="กด ❌ เพื่อปิดเมนู")
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except Exception:
                pass


class CustomHelp(commands.MinimalHelpCommand):
    async def send_bot_help(self, mapping: dict) -> None:
        filtered_mapping: dict = {}
        for cog, cmds in mapping.items():
            filtered = []
            for cmd in cmds:
                try:
                    can_run = await cmd.can_run(self.context)
                    if can_run:
                        filtered.append(cmd)
                except commands.CheckFailure:
                    continue
                except Exception:
                    filtered.append(cmd)

            if filtered:
                filtered_mapping[cog] = filtered

        embed = discord.Embed(
            title="🤖 คำสั่งบอท",
            description="เลือกหมวดหมู่จากเมนูด้านล่างเพื่อดูคำสั่ง\nใช้ `!help <command>` เพื่อดูรายละเอียดคำสั่ง",
            color=discord.Color.blurple()
        )

        if filtered_mapping:
            categories_text = []
            for cog in filtered_mapping.keys():
                cog_name = cog.qualified_name if cog else "ไม่มีหมวดหมู่"
                cmd_count = len(filtered_mapping[cog])
                categories_text.append(f"📁 **{cog_name}** - {cmd_count} คำสั่ง")

            embed.add_field(
                name="หมวดหมู่ที่มี",
                value="\n".join(categories_text),
                inline=False
            )

        embed.set_footer(text="กด ❌ เพื่อปิดเมนู | เมนูหมดอายุใน 60 วินาที")
        view = HelpView(filtered_mapping, self.context, self)
        channel = self.get_destination()
        message = await channel.send(embed=embed, view=view)
        view.message = message
        await message.add_reaction("❌")

        def check(reaction: discord.Reaction, user: discord.User) -> bool:
            return (
                user.id == self.context.author.id
                and str(reaction.emoji) == "❌"
                and reaction.message.id == message.id
            )

        try:
            await self.context.bot.wait_for("reaction_add", timeout=60.0, check=check)
            await message.delete()
        except Exception:
            pass

    async def send_command_help(self, command: commands.Command) -> None:
        embed = discord.Embed(
            title=f"ℹ️ คำสั่ง: {command.name}",
            description=command.help or "ไม่มีคำอธิบาย",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="📝 รูปแบบคำสั่ง",
            value=f"`{self.context.clean_prefix}{command.name} {command.signature}`",
            inline=False
        )

        if command.aliases:
            embed.add_field(
                name="🔄 ชื่ออื่น",
                value=", ".join(f"`{alias}`" for alias in command.aliases),
                inline=False
            )

        await self.get_destination().send(embed=embed)

    async def send_cog_help(self, cog: commands.Cog) -> None:
        embed = discord.Embed(
            title=f"📚 {cog.qualified_name}",
            description=cog.description or "ไม่มีคำอธิบาย",
            color=discord.Color.blurple()
        )

        filtered = []
        for cmd in cog.get_commands():
            try:
                can_run = await cmd.can_run(self.context)
                if can_run:
                    filtered.append(cmd)
            except commands.CheckFailure:
                continue
            except Exception:
                filtered.append(cmd)

        if filtered:
            for cmd in sorted(filtered, key=lambda c: c.name):
                embed.add_field(
                    name=f"`{self.context.clean_prefix}{cmd.name} {cmd.signature}`",
                    value=cmd.help or "ไม่มีคำอธิบาย",
                    inline=False
                )
        else:
            embed.add_field(name="คำสั่ง", value="ไม่มีคำสั่งที่ใช้ได้", inline=False)

        await self.get_destination().send(embed=embed)


class General(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot

    @commands.command(name="ping")
    async def ping(self, ctx: commands.Context) -> None:
        """ตรวจสอบความหน่วงของบอท"""
        await ctx.send(f"Pong! 🏓 `{round(self.bot.latency*1000)}ms`")

    @discord.app_commands.command(name="ping", description="ตรวจสอบความหน่วงของบอท")
    async def slash_ping(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(f"Pong! 🏓 `{round(self.bot.latency*1000)}ms`")

    @discord.app_commands.command(name="bot-control", description="แผงควบคุมบอท")
    async def control_panel(self, interaction: discord.Interaction) -> None:
        owner_id = int(os.getenv("BOT_OWNER_ID", 0))
        is_owner = interaction.user.id == owner_id

        embed = discord.Embed(title="🤖 แผงควบคุมบอท", color=discord.Color.blurple())
        embed.add_field(name="เซิร์ฟเวอร์", value=str(len(self.bot.guilds)), inline=True)
        embed.add_field(name="ความหน่วง", value=f"{round(self.bot.latency*1000)}ms", inline=True)

        class BotControlView(discord.ui.View):
            def __init__(self, bot: commands.Bot, owner_id: int) -> None:
                super().__init__(timeout=60)
                self.bot = bot
                self.owner_id = owner_id
                self.author_id = interaction.user.id

            async def interaction_check(self, interaction: discord.Interaction) -> bool:
                if interaction.user.id != self.owner_id:
                    await interaction.response.send_message("❌ สำหรับเจ้าของเท่านั้น!", ephemeral=True)
                    return False
                return True

            @discord.ui.button(label="รีสตาร์ท", style=discord.ButtonStyle.secondary, emoji="🔄")
            async def restart_btn(self, i: discord.Interaction, b: discord.ui.Button) -> None:
                await i.response.send_message("🔄 กำลังรีสตาร์ท...", ephemeral=True)
                await self.bot.close()

            @discord.ui.button(label="ปิดเครื่อง", style=discord.ButtonStyle.danger, emoji="🛑")
            async def shutdown_btn(self, i: discord.Interaction, b: discord.ui.Button) -> None:
                await i.response.send_message("🛑 กำลังปิดเครื่อง...", ephemeral=True)
                await self.bot.close()

            @discord.ui.button(label="ซิงค์คำสั่ง", style=discord.ButtonStyle.primary, emoji="⚡")
            async def sync_btn(self, i: discord.Interaction, b: discord.ui.Button) -> None:
                try:
                    synced = await self.bot.tree.sync()
                    await i.response.send_message(f"✅ ซิงค์แล้ว {len(synced)} คำสั่ง", ephemeral=True)
                except Exception as e:
                    await i.response.send_message(f"❌ Error: {e}", ephemeral=True)

            @discord.ui.button(label="โมดูล", style=discord.ButtonStyle.secondary, emoji="📦")
            async def cogs_btn(self, i: discord.Interaction, b: discord.ui.Button) -> None:
                cogs = list(self.bot.cogs.keys())
                embed = discord.Embed(title="📦 โมดูลที่โหลดแล้ว", description="\n".join(f"• `{cog}`" for cog in sorted(cogs)), color=discord.Color.blue())
                await i.response.send_message(embed=embed, ephemeral=True)

        await interaction.response.send_message(embed=embed, view=BotControlView(self.bot, owner_id))


async def setup(bot: commands.Bot) -> None:
    bot.help_command = CustomHelp()
    await bot.add_cog(General(bot))
