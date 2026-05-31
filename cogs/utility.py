import datetime
from typing import Any, Optional

import discord
from discord.ext import commands
from utils.helpers import get_uptime, get_bangkok_time, BANGKOK_TZ


class Utility(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot
        self.ctx_menu = discord.app_commands.ContextMenu(
            name="ข้อมูลผู้ใช้",
            callback=self.context_userinfo,
        )
        self.bot.tree.add_command(self.ctx_menu)

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

    @commands.command(name="uptime")
    async def uptime(self, ctx: commands.Context) -> None:
        await ctx.send(f"⏱️ เวลาทำงานของบอท: `{get_uptime(self.bot.launch_time)}`")

    @discord.app_commands.command(name="uptime", description="แสดงเวลาทำงานของบอท")
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def slash_uptime(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(f"⏱️ เวลาทำงานของบอท: `{get_uptime(self.bot.launch_time)}`")

    @commands.command(name="rtclock")
    async def rtclock(self, ctx: commands.Context) -> None:
        now = get_bangkok_time()
        await ctx.send(f"⏱️ เวลาจริงของบอท: `{now.strftime('%H:%M:%S')}`")

    @discord.app_commands.command(name="rtclock", description="แสดงเวลาจริงของบอท")
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def slash_rtclock(self, interaction: discord.Interaction) -> None:
        now = get_bangkok_time()
        await interaction.response.send_message(f"⏱️ เวลาจริงของบอท: `{now.strftime('%H:%M:%S')}`")

    @commands.command(name="usr")
    async def userinfo(self, ctx: commands.Context, user: Optional[discord.User] = None) -> None:
        user = user or ctx.author
        member: Optional[discord.Member] = None
        if ctx.guild and isinstance(user, discord.Member):
            member = user
        elif ctx.guild:
            member = ctx.guild.get_member(user.id)

        embed = await self._create_userinfo_embed(user, member, ctx.author)
        await ctx.send(embed=embed)

    @discord.app_commands.command(name="usr", description="แสดงข้อมูลผู้ใช้")
    @discord.app_commands.describe(user="ผู้ใช้ที่ต้องการดูข้อมูล")
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def slash_userinfo(self, interaction: discord.Interaction, user: Optional[discord.User] = None) -> None:
        user = user or interaction.user
        member: Optional[discord.Member] = None
        if interaction.guild and isinstance(user, discord.Member):
            member = user
        elif interaction.guild:
            member = interaction.guild.get_member(user.id)

        embed = await self._create_userinfo_embed(user, member, interaction.user)
        await interaction.response.send_message(embed=embed)

    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def context_userinfo(self, interaction: discord.Interaction, user: discord.User) -> None:
        member: Optional[discord.Member] = None
        if interaction.guild and isinstance(user, discord.Member):
            member = user
        elif interaction.guild:
            member = interaction.guild.get_member(user.id)

        embed = await self._create_userinfo_embed(user, member, interaction.user)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def _create_userinfo_embed(self, user: discord.User, member: Optional[discord.Member], requester: discord.User) -> discord.Embed:
        embed = discord.Embed(
            title=f"ข้อมูลผู้ใช้ - {user}",
            color=member.color if member and member.color != discord.Color.default() else discord.Color.blue(),
            timestamp=datetime.datetime.now(BANGKOK_TZ)
        )

        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="👤 ชื่อผู้ใช้", value=str(user.name), inline=True)
        embed.add_field(name="🆔 User ID", value=f"||{user.id}||", inline=True)
        embed.add_field(name="🤖 บอท", value="ใช่" if user.bot else "ไม่ใช่", inline=True)

        try:
            flags = getattr(user, "public_flags", None)
            badges = []
            if flags:
                flag_map = [
                    ("staff", "Discord Staff"),
                    ("partner", "Partner"),
                    ("hypesquad", "HypeSquad"),
                    ("bug_hunter", "Bug Hunter"),
                    ("early_supporter", "Early Supporter"),
                    ("verified_bot_developer", "Verified Bot Dev"),
                    ("certified_moderator", "Certified Moderator"),
                    ("active_developer", "Active Developer"),
                ]
                for attr, label in flag_map:
                    if getattr(flags, attr, False):
                        badges.append(label)
            if badges:
                embed.add_field(name="🎖️ ตรา", value=", ".join(badges), inline=False)
        except Exception:
            pass

        created_at = discord.utils.format_dt(user.created_at, style="F")
        embed.add_field(name="📅 สร้างบัญชีเมื่อ", value=created_at, inline=False)

        if member and member.joined_at:
            joined_at = discord.utils.format_dt(member.joined_at, style="F")
            embed.add_field(name="📥 เข้าร่วมเซิร์ฟเวอร์เมื่อ", value=joined_at, inline=False)

        if member:
            roles = [role.mention for role in member.roles[1:]]
            if roles:
                embed.add_field(
                    name=f"🎭 บทบาท ({len(roles)})",
                    value=" ".join(roles) if len(roles) <= 10 else f"{' '.join(roles[:10])} และอีก {len(roles) - 10}...",
                    inline=False
                )

            status_emoji = {
                discord.Status.online: "🟢 ออนไลน์",
                discord.Status.idle: "🟡 ไม่ว่าง",
                discord.Status.dnd: "🔴 ห้ามรบกวน",
                discord.Status.offline: "⚫ ออฟไลน์"
            }
            embed.add_field(name="📡 สถานะ", value=status_emoji.get(member.status, "❓ ไม่ทราบ"), inline=True)

            if member.top_role.name != "@everyone":
                embed.add_field(name="⭐ บทบาทสูงสุด", value=member.top_role.mention, inline=True)

        embed.set_footer(text=f"ร้องขอโดย {requester}", icon_url=requester.display_avatar.url)
        return embed



async def setup(bot):
    await bot.add_cog(Utility(bot))
