import discord
import datetime
from discord.ext import commands
from utils.helpers import get_uptime
import pytz

bangkok_timezone = pytz.timezone('Asia/Bangkok')

def get_current_time():
    """Get current Bangkok time"""
    current_datetime = datetime.datetime.now(bangkok_timezone)
    return current_datetime.strftime("%H:%M:%S")

class Utility(commands.Cog):
    """Utility commands"""
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="uptime")
    async def uptime(self, ctx):
        """Show bot uptime (prefix)"""
        await ctx.send(f"⏱️ Bot uptime: `{get_uptime(self.bot.launch_time)}`")

    @discord.app_commands.command(name="uptime", description="Show bot uptime")
    async def slash_uptime(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"⏱️ Bot uptime: `{get_uptime(self.bot.launch_time)}`")

    @commands.command(name="rtclock")
    async def rtclock(self, ctx):
        """Show bot realtime (prefix)"""
        await ctx.send(f"⏱️ Bot Realtime: `{get_current_time()}`")

    @discord.app_commands.command(name="rtclock", description="Show bot realtime")
    async def slash_rtclock(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"⏱️ Bot Realtime: `{get_current_time()}`")

    @commands.command(name="userinfo")
    async def userinfo(self, ctx, member: discord.Member = None):
        """Show user information (prefix)"""
        member = member or ctx.author

        embed = discord.Embed(
            title=f"User Information - {member}",
            color=member.color if member.color != discord.Color.default() else discord.Color.blue(),
            timestamp=datetime.datetime.now(bangkok_timezone)
        )

        embed.set_thumbnail(url=member.display_avatar.url)

        # Basic Info
        embed.add_field(name="👤 Username", value=f"{member.name}", inline=True)
        embed.add_field(name="🆔 User ID", value=f"`{member.id}`", inline=True)
        embed.add_field(name="🤖 Bot", value="Yes" if member.bot else "No", inline=True)

        # Dates
        created_at = discord.utils.format_dt(member.created_at, style='F')
        created_at_relative = discord.utils.format_dt(member.created_at, style='R')
        embed.add_field(
            name="📅 Account Created",
            value=f"{created_at}\n{created_at_relative}",
            inline=False
        )

        if member.joined_at:
            joined_at = discord.utils.format_dt(member.joined_at, style='F')
            joined_at_relative = discord.utils.format_dt(member.joined_at, style='R')
            embed.add_field(
                name="📥 Joined Server",
                value=f"{joined_at}\n{joined_at_relative}",
                inline=False
            )

        # Roles
        roles = [role.mention for role in member.roles[1:]]  # Skip @everyone
        if roles:
            embed.add_field(
                name=f"🎭 Roles ({len(roles)})",
                value=" ".join(roles) if len(roles) <= 10 else f"{' '.join(roles[:10])} and {len(roles) - 10} more...",
                inline=False
            )

        # Status and Activity
        status_emoji = {
            discord.Status.online: "🟢 Online",
            discord.Status.idle: "🟡 Idle",
            discord.Status.dnd: "🔴 Do Not Disturb",
            discord.Status.offline: "⚫ Offline"
        }
        embed.add_field(
            name="📡 Status",
            value=status_emoji.get(member.status, "❓ Unknown"),
            inline=True
        )

        # Top Role
        if member.top_role.name != "@everyone":
            embed.add_field(
                name="⭐ Top Role",
                value=member.top_role.mention,
                inline=True
            )

        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)

        await ctx.send(embed=embed)

    @discord.app_commands.command(name="userinfo", description="Show user information")
    @discord.app_commands.describe(member="The user to get information about (leave empty for yourself)")
    async def slash_userinfo(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user

        embed = discord.Embed(
            title=f"User Information - {member}",
            color=member.color if member.color != discord.Color.default() else discord.Color.blue(),
            timestamp=datetime.datetime.now(bangkok_timezone)
        )

        embed.set_thumbnail(url=member.display_avatar.url)

        # Basic Info
        embed.add_field(name="👤 Username", value=f"{member.name}", inline=True)
        embed.add_field(name="🆔 User ID", value=f"`{member.id}`", inline=True)
        embed.add_field(name="🤖 Bot", value="Yes" if member.bot else "No", inline=True)

        # Dates
        created_at = discord.utils.format_dt(member.created_at, style='F')
        created_at_relative = discord.utils.format_dt(member.created_at, style='R')
        embed.add_field(
            name="📅 Account Created",
            value=f"{created_at}\n{created_at_relative}",
            inline=False
        )

        if member.joined_at:
            joined_at = discord.utils.format_dt(member.joined_at, style='F')
            joined_at_relative = discord.utils.format_dt(member.joined_at, style='R')
            embed.add_field(
                name="📥 Joined Server",
                value=f"{joined_at}\n{joined_at_relative}",
                inline=False
            )

        # Roles
        roles = [role.mention for role in member.roles[1:]]  # Skip @everyone
        if roles:
            embed.add_field(
                name=f"🎭 Roles ({len(roles)})",
                value=" ".join(roles) if len(roles) <= 10 else f"{' '.join(roles[:10])} and {len(roles) - 10} more...",
                inline=False
            )

        # Status and Activity
        status_emoji = {
            discord.Status.online: "🟢 Online",
            discord.Status.idle: "🟡 Idle",
            discord.Status.dnd: "🔴 Do Not Disturb",
            discord.Status.offline: "⚫ Offline"
        }
        embed.add_field(
            name="📡 Status",
            value=status_emoji.get(member.status, "❓ Unknown"),
            inline=True
        )

        # Top Role
        if member.top_role.name != "@everyone":
            embed.add_field(
                name="⭐ Top Role",
                value=member.top_role.mention,
                inline=True
            )

        embed.set_footer(text=f"Requested by {interaction.user}", icon_url=interaction.user.display_avatar.url)

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Utility(bot))
