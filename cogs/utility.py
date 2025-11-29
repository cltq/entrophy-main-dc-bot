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

        # Badges (public flags)
        try:
            flags = getattr(user, 'public_flags', None)
            badges = []
            if flags is not None:
                # Known mapping of PublicUserFlags attributes to friendly names
                flag_map = [
                    ('staff', 'Discord Staff'),
                    ('partner', 'Partner'),
                    ('hypesquad', 'HypeSquad'),
                    ('bug_hunter', 'Bug Hunter'),
                    ('early_supporter', 'Early Supporter'),
                    ('verified_bot_developer', 'Verified Bot Dev'),
                    ('certified_moderator', 'Certified Moderator'),
                    ('active_developer', 'Active Developer'),
                ]
                for attr, label in flag_map:
                    if getattr(flags, attr, False):
                        badges.append(label)
            if badges:
                embed.add_field(name="🎖️ Badges", value=", ".join(badges), inline=False)
        except Exception:
            pass

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

        # Pronouns (best-effort: Discord may expose via profile/pronouns depending on API)
        try:
            pronouns = None
            # try common attribute locations
            pronouns = getattr(user, 'pronouns', None)
            if pronouns is None and hasattr(user, 'profile'):
                try:
                    prof = getattr(user, 'profile')
                    pronouns = getattr(prof, 'pronouns', None)
                except Exception:
                    pronouns = None
            if pronouns:
                embed.add_field(name="🏷️ Pronouns", value=str(pronouns), inline=True)
        except Exception:
            pass

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
            # Custom Status (if set)
            try:
                custom = None
                for a in member.activities:
                    # discord.CustomActivity may be present or ActivityType.custom
                    if getattr(a, 'type', None) == discord.ActivityType.custom or a.__class__.__name__ == 'CustomActivity':
                        # a.state holds the custom status text
                        custom = getattr(a, 'state', None) or getattr(a, 'name', None)
                        if custom:
                            break
                if custom:
                    embed.add_field(name="💬 Custom Status", value=str(custom), inline=True)
            except Exception:
                pass

            # Top Role (only in guilds)
            if member.top_role.name != "@everyone":
                embed.add_field(
                    name="⭐ Top Role",
                    value=member.top_role.mention,
                    inline=True
                )

            # Guild tag / server display name
            try:
                display = member.display_name
                guild_tag = f"{display}#{user.discriminator if hasattr(user, 'discriminator') else '----'}"
                embed.add_field(name="🏷️ Guild Tag", value=guild_tag, inline=True)
            except Exception:
                pass

        embed.set_footer(text=f"Requested by {requester}", icon_url=requester.display_avatar.url)

        return embed
    
    @discord.app_commands.command(name="dashboard", description="Send the Bot's Dashboard link.")
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def uptime(self, ctx):
        await ctx.send(f"⏱️ Bot Dashboard: https://entrophy-main-dc-bot.onrender.com")

async def setup(bot):
    await bot.add_cog(Utility(bot))
