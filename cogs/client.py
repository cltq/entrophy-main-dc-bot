"""
Consolidated cog for all client app commands (commands that work as installed user apps)
These commands can be used in guilds, DMs, and private channels when installed as a user app
"""
import discord
from discord import app_commands
from discord.ext import commands
import datetime
from utils.helpers import get_uptime
import pytz

bangkok_timezone = pytz.timezone('Asia/Bangkok')

def get_current_time():
    """Get current Bangkok time"""
    current_datetime = datetime.datetime.now(bangkok_timezone)
    return current_datetime.strftime("%H:%M:%S")

class ClientAppCommands(commands.Cog):
    """Client app commands - work as installed user apps in guilds, DMs, and private channels"""
    
    def __init__(self, bot):
        self.bot = bot

    # ============ SAY COMMAND ============
    @discord.app_commands.command(name="say", description="Say something anywhere.")
    @app_commands.describe(message="The message the bot will send publicly.", channel_id="Optional channel ID to send the message to")
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def say(self, interaction: discord.Interaction, message: str, channel_id: str = None):
        """Say something anywhere - works as a user app"""
        # If a target channel_id was provided, try to send there (validate first)
        if channel_id:
            try:
                target_id = int(channel_id)
            except Exception:
                await interaction.response.send_message("Invalid channel id provided.", ephemeral=True)
                return

            target = self.bot.get_channel(target_id)
            if target is None:
                try:
                    target = await self.bot.fetch_channel(target_id)
                except Exception:
                    target = None

            if target is None or not hasattr(target, 'send'):
                await interaction.response.send_message("Could not find a sendable channel with that ID.", ephemeral=True)
                return

            # Try to send to the target channel
            await interaction.response.send_message(":white_check_mark: Message queued to target channel.", ephemeral=True)

            try:
                await target.send(message, allowed_mentions=discord.AllowedMentions.none())
            except Exception:
                try:
                    await interaction.followup.send("Failed to send to target channel (missing permissions?).", ephemeral=True)
                except Exception:
                    pass
            return

        # If the command is used in DM
        if isinstance(interaction.channel, discord.DMChannel):
            # Send normal (non-ephemeral) success message
            await interaction.response.send_message(":white_check_mark: Message sent Successfully.", ephemeral=True)
            # Then send the message in the DM as a follow-up (no mentions)
            try:
                await interaction.followup.send(message, allowed_mentions=discord.AllowedMentions.none())
            except Exception:
                # Fallback: try sending directly to the channel
                try:
                    await interaction.channel.send(message, allowed_mentions=discord.AllowedMentions.none())
                except Exception:
                    # If all fails, silently ignore to avoid crashing the cog load
                    pass
            return

        # If the command is in a guild (server)
        # Step 1: ephemeral response to user
        await interaction.response.send_message("Success!", ephemeral=True)

        # Step 2: send public message as a follow-up to the interaction (no mentions)
        try:
            await interaction.followup.send(message, allowed_mentions=discord.AllowedMentions.none())
        except Exception:
            # Fallback to channel send if followup fails
            try:
                await interaction.channel.send(message, allowed_mentions=discord.AllowedMentions.none())
            except Exception:
                # Give the user an ephemeral error message if possible
                try:
                    await interaction.followup.send("Failed to post message (missing permissions?)", ephemeral=True)
                except Exception:
                    pass

    # ============ UPTIME COMMAND ============
    @discord.app_commands.command(name="uptime", description="Show bot uptime")
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def uptime(self, interaction: discord.Interaction):
        """Show bot uptime - works as a user app"""
        await interaction.response.send_message(f"⏱️ Bot uptime: `{get_uptime(self.bot.launch_time)}`")

    # ============ REALTIME CLOCK COMMAND ============
    @discord.app_commands.command(name="rtclock", description="Show bot realtime")
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def rtclock(self, interaction: discord.Interaction):
        """Show bot realtime - works as a user app"""
        await interaction.response.send_message(f"⏱️ Bot Realtime: `{get_current_time()}`")

    # ============ USER INFO COMMAND ============
    @discord.app_commands.command(name="usr", description="Show user information")
    @discord.app_commands.describe(user="The user to get information about (leave empty for yourself)")
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def userinfo(self, interaction: discord.Interaction, user: discord.User = None):
        """Show user information - works as a user app"""
        user = user or interaction.user

        # Try to get member object if in a guild
        member = None
        if interaction.guild and isinstance(user, discord.Member):
            member = user
        elif interaction.guild:
            member = interaction.guild.get_member(user.id)

        embed = await self._create_userinfo_embed(user, member, interaction.user)
        await interaction.response.send_message(embed=embed)

    # ============ HELPER METHODS ============
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

        # Pronouns
        try:
            pronouns = None
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

            # Status
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
            
            # Custom Status
            try:
                custom = None
                for a in member.activities:
                    if getattr(a, 'type', None) == discord.ActivityType.custom or a.__class__.__name__ == 'CustomActivity':
                        custom = getattr(a, 'state', None) or getattr(a, 'name', None)
                        if custom:
                            break
                if custom:
                    embed.add_field(name="💬 Custom Status", value=str(custom), inline=True)
            except Exception:
                pass

            # Top Role
            if member.top_role.name != "@everyone":
                embed.add_field(
                    name="⭐ Top Role",
                    value=member.top_role.mention,
                    inline=True
                )

            # Guild tag
            try:
                display = member.display_name
                guild_tag = f"{display}#{user.discriminator if hasattr(user, 'discriminator') else '----'}"
                embed.add_field(name="🏷️ Guild Tag", value=guild_tag, inline=True)
            except Exception:
                pass

        embed.set_footer(text=f"Requested by {requester}", icon_url=requester.display_avatar.url)

        return embed


async def setup(bot):
    await bot.add_cog(ClientAppCommands(bot))
