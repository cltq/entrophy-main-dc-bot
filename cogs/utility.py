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
        # Add context menu command
        self.ctx_menu = discord.app_commands.ContextMenu(
            name='User Info',
            callback=self.context_userinfo,
        )
        self.bot.tree.add_command(self.ctx_menu)

    async def cog_unload(self):
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

    @commands.command(name="uptime")
    async def uptime(self, ctx):
        """Show bot uptime (prefix)"""
        await ctx.send(f"⏱️ Bot uptime: `{get_uptime(self.bot.launch_time)}`")

    @discord.app_commands.command(name="uptime", description="Show bot uptime")
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def slash_uptime(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"⏱️ Bot uptime: `{get_uptime(self.bot.launch_time)}`")

    @commands.command(name="rtclock")
    async def rtclock(self, ctx):
        """Show bot realtime (prefix)"""
        await ctx.send(f"⏱️ Bot Realtime: `{get_current_time()}`")

    @discord.app_commands.command(name="rtclock", description="Show bot realtime")
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def slash_rtclock(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"⏱️ Bot Realtime: `{get_current_time()}`")

    @commands.command(name="usr")
    async def userinfo(self, ctx, user: discord.User = None):
        """Show user information (prefix)"""
        user = user or ctx.author

        # Try to get member object if in a guild, otherwise use user object
        member = None
        if ctx.guild and isinstance(user, discord.Member):
            member = user
        elif ctx.guild:
            member = ctx.guild.get_member(user.id)

        embed = await self._create_userinfo_embed(user, member, ctx.author)
        await ctx.send(embed=embed)

    @discord.app_commands.command(name="usr", description="Show user information")
    @discord.app_commands.describe(user="The user to get information about (leave empty for yourself)")
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def slash_userinfo(self, interaction: discord.Interaction, user: discord.User = None):
        user = user or interaction.user

        # Try to get member object if in a guild
        member = None
        if interaction.guild and isinstance(user, discord.Member):
            member = user
        elif interaction.guild:
            member = interaction.guild.get_member(user.id)

        embed = await self._create_userinfo_embed(user, member, interaction.user)
        await interaction.response.send_message(embed=embed)

    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def _create_userinfo_embed(self, user: discord.User, member: discord.Member, requester: discord.User):
    embed = discord.Embed(
        title=f"User Information - {user}",
        color=member.color if member and member.color != discord.Color.default() else discord.Color.blue(),
        timestamp=datetime.datetime.now(bangkok_timezone)
    )

    embed.set_thumbnail(url=user.display_avatar.url)

    # Basic Info
    embed.add_field(name="👤 Username", value=user.name, inline=True)
    embed.add_field(name="🆔 User ID", value=f"||`{user.id}`||", inline=True)
    embed.add_field(name="🤖 Bot", value="Yes" if user.bot else "No", inline=True)

    # Dates
    created_at = discord.utils.format_dt(user.created_at, style='F')
    created_at_relative = discord.utils.format_dt(user.created_at, style='R')
    embed.add_field(
        name="📅 Account Created",
        value=f"{created_at}\n{created_at_relative}",
        inline=False
    )

    # User Badges
    if hasattr(user, "public_flags"):
        flags = user.public_flags
        badge_map = {
            "staff": "👑 Discord Staff",
            "partner": "💎 Partnered Server Owner",
            "hypesquad": "🎉 HypeSquad",
            "hypesquad_bravery": "🦁 HypeSquad Bravery",
            "hypesquad_brilliance": "🧠 HypeSquad Brilliance",
            "hypesquad_balance": "⚖️ HypeSquad Balance",
            "bug_hunter": "🐛 Bug Hunter",
            "bug_hunter_level_2": "🔧 Bug Hunter Level 2",
            "early_supporter": "🌟 Early Supporter",
            "verified_bot": "🤖 Verified Bot",
            "verified_bot_developer": "🏅 Early Verified Developer",
            "active_developer": "🛠 Active Developer",
            "discord_certified_moderator": "🛡 Certified Moderator"
        }

        active_badges = [
            badge for flag, badge in badge_map.items()
            if getattr(flags, flag, False)
        ]

        embed.add_field(
            name="🏅 Badges",
            value="\n".join(active_badges) if active_badges else "None",
            inline=False
        )

    # Guild Info
    if member:
        # Join Date
        if member.joined_at:
            joined_at = discord.utils.format_dt(member.joined_at, style='F')
            joined_at_relative = discord.utils.format_dt(member.joined_at, style='R')
            embed.add_field(
                name="📥 Joined Server",
                value=f"{joined_at}\n{joined_at_relative}",
                inline=False
            )

        # Roles
        roles = [r.mention for r in member.roles[1:]]
        if roles:
            if len(roles) <= 10:
                role_list = " ".join(roles)
            else:
                role_list = f"{' '.join(roles[:10])} and {len(roles)-10} more..."
            embed.add_field(
                name=f"🎭 Roles ({len(roles)})",
                value=role_list,
                inline=False
            )

        # Status
        status_map = {
            discord.Status.online: "🟢 Online",
            discord.Status.idle: "🟡 Idle",
            discord.Status.dnd: "🔴 Do Not Disturb",
            discord.Status.offline: "⚫ Offline"
        }
        embed.add_field(
            name="📡 Status",
            value=status_map.get(member.status, "Unknown"),
            inline=True
        )

        # Top role
        if member.top_role.name != "@everyone":
            embed.add_field(
                name="⭐ Top Role",
                value=member.top_role.mention,
                inline=True
            )

        # Guild Tag
        guild_tag = None
        if member.guild.owner_id == user.id:
            guild_tag = "👑 Server Owner"
        elif member.premium_since:
            guild_tag = "💗 Server Booster"
        elif member.nick:
            guild_tag = f"🏷 Nickname: `{member.nick}`"

        embed.add_field(
            name="🔖 Guild Tag",
            value=guild_tag if guild_tag else "None",
            inline=False
        )

    # Footer
    embed.set_footer(text=f"Requested by {requester}", icon_url=requester.display_avatar.url)

    return embed


async def setup(bot):
    await bot.add_cog(Utility(bot))
