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

    @commands.command(name="userinfo")
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

    @discord.app_commands.command(name="userinfo", description="Show user information")
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
    async def context_userinfo(self, interaction: discord.Interaction, user: discord.User):
        """Context menu command for user info"""
        # Try to get member object if in a guild
        member = None
        if interaction.guild and isinstance(user, discord.Member):
            member = user
        elif interaction.guild:
            member = interaction.guild.get_member(user.id)

        embed = await self._create_userinfo_embed(user, member, interaction.user)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def _create_userinfo_embed(self, user: discord.User, member: discord.Member, requester: discord.User):
        """Helper method to create userinfo embed"""
        embed = discord.Embed(
            title=f"User Information - {user}",
            color=member.color if member and member.color != discord.Color.default() else discord.Color.blue(),
            timestamp=datetime.datetime.now(bangkok_timezone)
        )

        embed.set_thumbnail(url=user.display_avatar.url)

        # Basic Info
        embed.add_field(name="👤 Username", value=f"{user.name}", inline=True)
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

        # Only show server-specific info if in a guild and member exists
        if member and member.joined_at:
            joined_at = discord.utils.format_dt(member.joined_at, style='F')
            joined_at_relative = discord.utils.format_dt(member.joined_at, style='R')
            embed.add_field(
                name="📥 Joined Server",
                value=f"{joined_at}\n{joined_at_relative}",
                inline=False
            )

        # Roles (only in guilds)
        if member:
            roles = [role.mention for role in member.roles[1:]]  # Skip @everyone
            if roles:
                embed.add_field(
                    name=f"🎭 Roles ({len(roles)})",
                    value=" ".join(roles) if len(roles) <= 10 else f"{' '.join(roles[:10])} and {len(roles) - 10} more...",
                    inline=False
                )

            # Status and Activity (only in guilds)
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

            # Top Role (only in guilds)
            if member.top_role.name != "@everyone":
                embed.add_field(
                    name="⭐ Top Role",
                    value=member.top_role.mention,
                    inline=True
                )

        embed.set_footer(text=f"Requested by {requester}", icon_url=requester.display_avatar.url)

        return embed

async def setup(bot):
    await bot.add_cog(Utility(bot))
