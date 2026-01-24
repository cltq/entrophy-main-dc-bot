import os
import sys
import datetime
import pytz
from itertools import cycle
from typing import Optional, Literal
import discord
from discord.ext import commands, tasks
from discord import app_commands
from utils.helpers import get_uptime
import aiohttp

bangkok_timezone = pytz.timezone('Asia/Bangkok')

class Owner(commands.Cog):
    """Admin and owner commands"""

    def __init__(self, bot):
        self.bot = bot
        self.cycle_paused = False
        # Status cycler
        self.statuses = cycle([
            lambda: f"Uptime: {get_uptime(getattr(self.bot, 'launch_time', None))}",
            lambda: f"Owner: {self.bot.get_user(int(os.getenv('BOT_OWNER_ID', 0))).name if self.bot.get_user(int(os.getenv('BOT_OWNER_ID', 0))) else 'Unknown'}",
            lambda: f"Serving {len(self.bot.guilds)} servers",
            lambda: f"Time: {datetime.datetime.now(bangkok_timezone).strftime('%H:%M:%S')}",
        ])
        self.status_cycle.start()

    async def _is_owner_interaction(self, interaction: discord.Interaction) -> bool:
        return await interaction.client.is_owner(interaction.user)

    def cog_unload(self):
        """Stop the status cycle task when cog is unloaded"""
        self.status_cycle.cancel()

    # ---------- STATUS CYCLER ----------
    @tasks.loop(seconds=5)
    async def status_cycle(self):
        if self.cycle_paused:
            return
        try:
            next_status = next(self.statuses)()
            await self.bot.change_presence(
                activity=discord.Game(next_status),
                status=discord.Status.online
            )
        except Exception as e:
            print(f"Error in status cycle: {e}")

    @status_cycle.before_loop
    async def before_status_cycle(self):
        await self.bot.wait_until_ready()

    # (slash commands removed; owner-only functionality remains via prefix commands)

    # ---------- SINGLE OWNER COMMAND ----------
    @commands.command(name="bot", help="Owner-only: manage the bot with subcommands.")
    @commands.is_owner()
    async def bot(self, ctx, action: str, *params):
        """Unified owner command. Usage examples:
        - bot status <text>
        - bot setstate <online|idle|dnd|invisible>
        - bot resume|pause
        - bot setname <new name>
        - bot setavatar <url or attach image>
        - bot setbanner <url or attach image>
        - bot removebanner
        - bot profile
        - bot sync [current|global|remove|guild_id ...]
        - bot reload <cog>
        - bot load <cog>
        - bot unload <cog>
        - bot cogs
        - bot shutdown
        - bot restart
        """
        action = action.lower()

        # ----- STATUS ACTIONS (combined) -----
        if action in ("status", "setstatus", "stat", "setstate", "state"):
            states = {
                "online": discord.Status.online,
                "idle": discord.Status.idle,
                "dnd": discord.Status.dnd,
                "invisible": discord.Status.invisible,
            }

            # If a single param equals one of the state keywords, treat as state change
            if len(params) == 1 and params[0].lower() in states:
                state = params[0].lower()
                self.cycle_paused = True
                try:
                    await self.bot.change_presence(status=states[state])
                    await ctx.send(f"✅ Bot online status set to `{state}`\n⏸️ Auto-cycling paused.")
                except Exception as e:
                    await ctx.send(f"❌ Failed to set state: {e}")
                return

            # Otherwise treat params as status text
            text = " ".join(params).strip()
            if not text:
                await ctx.send("❌ Please provide a status text or a state keyword (online, idle, dnd, invisible).")
                return
            self.cycle_paused = True
            try:
                await self.bot.change_presence(activity=discord.Game(text))
                await ctx.send(f"✅ Status changed to: `{text}`\n⏸️ Auto-cycling paused.")
            except Exception as e:
                await ctx.send(f"❌ Failed to change status: {e}")
            return

        if action in ("resume", "resumecycle", "unpause"):
            self.cycle_paused = False
            await ctx.send("▶️ Status auto-cycling resumed!")
            return

        if action in ("pause", "pausecycle"):
            self.cycle_paused = True
            await ctx.send("⏸️ Status auto-cycling paused!")
            return

        # ----- PROFILE MANAGEMENT -----
        if action in ("setname", "name"):
            name = " ".join(params).strip()
            if not name:
                await ctx.send("❌ Please provide a new username.")
                return
            try:
                await self.bot.user.edit(username=name)
                await ctx.send(f"✅ Bot username changed to: `{name}`")
            except discord.HTTPException as e:
                if getattr(e, 'status', None) == 429:
                    await ctx.send("❌ Rate limited! You can only change the bot's username twice per hour.")
                else:
                    await ctx.send(f"❌ Failed to change username: {e}")
            except Exception as e:
                await ctx.send(f"❌ An error occurred: {e}")
            return

        if action in ("setavatar", "avatar"):
            # URL may be provided or attachment
            image_url = None
            if params:
                image_url = params[0]
            if ctx.message.attachments and not image_url:
                image_url = ctx.message.attachments[0].url
            if not image_url:
                await ctx.send("❌ Please provide an image URL or attach an image.")
                return
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(image_url) as resp:
                        if resp.status != 200:
                            await ctx.send("❌ Failed to download the image.")
                            return
                        image_data = await resp.read()
                await self.bot.user.edit(avatar=image_data)
                await ctx.send("✅ Bot avatar updated successfully!")
            except discord.HTTPException as e:
                if getattr(e, 'status', None) == 429:
                    await ctx.send("❌ Rate limited! You can only change the bot's avatar a few times per hour.")
                else:
                    await ctx.send(f"❌ Failed to change avatar: {e}")
            except Exception as e:
                await ctx.send(f"❌ An error occurred: {e}")
            return

        if action in ("setbanner", "banner"):
            image_url = None
            if params:
                image_url = params[0]
            if ctx.message.attachments and not image_url:
                image_url = ctx.message.attachments[0].url
            if not image_url:
                await ctx.send("❌ Please provide an image URL or attach an image.")
                return
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(image_url) as resp:
                        if resp.status != 200:
                            await ctx.send("❌ Failed to download the image.")
                            return
                        image_data = await resp.read()
                await self.bot.user.edit(banner=image_data)
                await ctx.send("✅ Bot banner updated successfully!")
            except discord.HTTPException as e:
                if "premium" in str(e).lower():
                    await ctx.send("❌ Setting a banner requires the bot to have Discord premium (bot subscription).")
                else:
                    await ctx.send(f"❌ Failed to change banner: {e}")
            except Exception as e:
                await ctx.send(f"❌ An error occurred: {e}")
            return

        if action in ("removebanner", "delbanner"):
            try:
                await self.bot.user.edit(banner=None)
                await ctx.send("✅ Bot banner removed successfully!")
            except Exception as e:
                await ctx.send(f"❌ Failed to remove banner: {e}")
            return

        if action in ("profile", "botinfo"):
            user = self.bot.user
            embed = discord.Embed(
                title="🤖 Bot Profile Information",
                color=discord.Color.blue()
            )
            embed.set_thumbnail(url=user.display_avatar.url)
            if user.banner:
                embed.set_image(url=user.banner.url)
            embed.add_field(name="Username", value=user.name, inline=True)
            embed.add_field(name="ID", value=user.id, inline=True)
            embed.add_field(name="Discriminator", value=user.discriminator if user.discriminator != "0" else "None", inline=True)
            embed.add_field(name="Created At", value=user.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=False)
            embed.add_field(name="Servers", value=len(self.bot.guilds), inline=True)
            embed.add_field(name="Users", value=sum(g.member_count for g in self.bot.guilds), inline=True)
            await ctx.send(embed=embed)
            return

        # ----- SYNC -----
        if action == "sync":
            # params may contain keywords or guild ids
            if not params:
                synced = await ctx.bot.tree.sync()
                await ctx.send(f"✅ Synced {len(synced)} commands globally.")
                return

            first = params[0].lower()
            if first == "current":
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
                await ctx.send(f"✅ Synced {len(synced)} commands to current guild.")
                return
            if first == "global":
                ctx.bot.tree.copy_global_to(guild=ctx.guild)
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
                await ctx.send(f"✅ Copied global to current guild ({len(synced)} commands).")
                return
            if first == "remove":
                ctx.bot.tree.clear_commands(guild=ctx.guild)
                await ctx.bot.tree.sync(guild=ctx.guild)
                await ctx.send("✅ Cleared commands for current guild.")
                return

            # Otherwise treat params as guild ids
            ret = 0
            for p in params:
                try:
                    gid = int(p)
                    await ctx.bot.tree.sync(guild=discord.Object(id=gid))
                except Exception:
                    continue
                else:
                    ret += 1
            await ctx.send(f"✅ Synced to {ret}/{len(params)} guild(s).")
            return

        # ----- COG MANAGEMENT -----
        if action in ("reload", "load", "unload"):
            if not params:
                await ctx.send("❌ Please provide a cog name.")
                return
            cog_name = params[0]
            try:
                if action == "reload":
                    # Unload first, then load to ensure a fresh reload
                    await self.bot.unload_extension(f"cogs.{cog_name}")
                    await self.bot.load_extension(f"cogs.{cog_name}")
                    await ctx.send(f"✅ Reloaded cog: `{cog_name}`")
                elif action == "load":
                    await self.bot.load_extension(f"cogs.{cog_name}")
                    await ctx.send(f"✅ Loaded cog: `{cog_name}`")
                else:
                    if cog_name.lower() == "owner":
                        await ctx.send("❌ Cannot unload the Owner cog!")
                        return
                    await self.bot.unload_extension(f"cogs.{cog_name}")
                    await ctx.send(f"✅ Unloaded cog: `{cog_name}`")
            except commands.ExtensionNotFound:
                await ctx.send(f"❌ Cog `{cog_name}` not found.")
            except commands.ExtensionAlreadyLoaded:
                await ctx.send(f"❌ Cog `{cog_name}` is already loaded.")
            except commands.ExtensionNotLoaded:
                await ctx.send(f"❌ Cog `{cog_name}` is not loaded.")
            except Exception as e:
                await ctx.send(f"❌ Failed to {action} `{cog_name}`: {e}")
            return

        if action == "cogs":
            cogs = [cog for cog in self.bot.cogs.keys()]
            if cogs:
                embed = discord.Embed(
                    title="📦 Loaded Cogs",
                    description="\n".join(f"• `{cog}`" for cog in sorted(cogs)),
                    color=discord.Color.blue()
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ No cogs are currently loaded.")
            return

        # ----- SHUTDOWN -----
        if action in ("shutdown", "stop", "restart"):
            await ctx.send("🛑 Shutting down bot...")
            await self.bot.close()
            return
        
        if action in ("restart", "reboot"):
            await ctx.send("🔄 Restarting bot...")
            await self.bot.close()
            # Note: Actual restart logic should be handled by an external process manager
            os.execv(sys.executable, [sys.executable] + sys.argv)

        # ----- UNKNOWN -----
        await ctx.send("❌ Unknown action. Use `!bot help` for usage.")

    @bot.error
    async def bot_error(self, ctx, error):
        if isinstance(error, commands.NotOwner):
            await ctx.send("❌ Only the bot owner can use this command.")
        else:
            await ctx.send(f"❌ An error occurred: {error}")

    # ---------- OWNER-ONLY SLASH COMMANDS ----------
    async def bot_control_check(interaction: discord.Interaction) -> bool:
        """Check if user is the bot owner"""
        owner_id = int(os.getenv("BOT_OWNER_ID", 0))
        return interaction.user.id == owner_id

    botcontrol = app_commands.Group(name="botcontrol", description="🔧 Bot control panel (Owner only)")

    @botcontrol.command(name="restart", description="Restart the bot")
    @app_commands.check(bot_control_check)
    async def botcontrol_restart(self, interaction: discord.Interaction):
        """Restart the bot"""
        await interaction.response.defer(ephemeral=True)
        embed = discord.Embed(
            title="🔄 Bot Restart",
            description="The bot is restarting...",
            color=discord.Color.orange()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        await self.bot.close()

    @botcontrol.command(name="shutdown", description="Shut down the bot")
    @app_commands.check(bot_control_check)
    async def botcontrol_shutdown(self, interaction: discord.Interaction):
        """Shut down the bot"""
        await interaction.response.defer(ephemeral=True)
        embed = discord.Embed(
            title="🛑 Bot Shutdown",
            description="The bot is shutting down...",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        await self.bot.close()

    @botcontrol.command(name="reload", description="Reload a specific cog")
    @app_commands.check(bot_control_check)
    @app_commands.describe(cog="The cog to reload")
    async def botcontrol_reload(self, interaction: discord.Interaction, cog: str):
        """Reload a specific cog"""
        await interaction.response.defer(ephemeral=True)
        try:
            await self.bot.unload_extension(f"cogs.{cog}")
            await self.bot.load_extension(f"cogs.{cog}")
            embed = discord.Embed(
                title="✅ Cog Reloaded",
                description=f"Successfully reloaded cog: `{cog}`",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except commands.ExtensionNotFound:
            embed = discord.Embed(
                title="❌ Not Found",
                description=f"Cog `{cog}` not found.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Failed to Reload",
                description=f"Failed to reload `{cog}`: {e}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @botcontrol.command(name="load", description="Load a specific cog")
    @app_commands.check(bot_control_check)
    @app_commands.describe(cog="The cog to load")
    async def botcontrol_load(self, interaction: discord.Interaction, cog: str):
        """Load a specific cog"""
        await interaction.response.defer(ephemeral=True)
        try:
            await self.bot.load_extension(f"cogs.{cog}")
            embed = discord.Embed(
                title="✅ Cog Loaded",
                description=f"Successfully loaded cog: `{cog}`",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except commands.ExtensionAlreadyLoaded:
            embed = discord.Embed(
                title="⚠️ Already Loaded",
                description=f"Cog `{cog}` is already loaded.",
                color=discord.Color.orange()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except commands.ExtensionNotFound:
            embed = discord.Embed(
                title="❌ Not Found",
                description=f"Cog `{cog}` not found.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Failed to Load",
                description=f"Failed to load `{cog}`: {e}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @botcontrol.command(name="unload", description="Unload a specific cog")
    @app_commands.check(bot_control_check)
    @app_commands.describe(cog="The cog to unload")
    async def botcontrol_unload(self, interaction: discord.Interaction, cog: str):
        """Unload a specific cog"""
        await interaction.response.defer(ephemeral=True)
        if cog.lower() == "owner":
            embed = discord.Embed(
                title="❌ Cannot Unload",
                description="Cannot unload the Owner cog!",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        try:
            await self.bot.unload_extension(f"cogs.{cog}")
            embed = discord.Embed(
                title="✅ Cog Unloaded",
                description=f"Successfully unloaded cog: `{cog}`",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except commands.ExtensionNotLoaded:
            embed = discord.Embed(
                title="⚠️ Not Loaded",
                description=f"Cog `{cog}` is not loaded.",
                color=discord.Color.orange()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except commands.ExtensionNotFound:
            embed = discord.Embed(
                title="❌ Not Found",
                description=f"Cog `{cog}` not found.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Failed to Unload",
                description=f"Failed to unload `{cog}`: {e}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @botcontrol.command(name="sync", description="Sync slash commands globally")
    @app_commands.check(bot_control_check)
    async def botcontrol_sync(self, interaction: discord.Interaction):
        """Sync slash commands globally"""
        await interaction.response.defer(ephemeral=True)
        try:
            synced = await self.bot.tree.sync()
            embed = discord.Embed(
                title="✅ Commands Synced",
                description=f"Successfully synced {len(synced)} commands globally.",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Sync Failed",
                description=f"Failed to sync commands: {e}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @botcontrol.command(name="cogs", description="List all loaded cogs")
    @app_commands.check(bot_control_check)
    async def botcontrol_cogs(self, interaction: discord.Interaction):
        """List all loaded cogs"""
        await interaction.response.defer(ephemeral=True)
        cogs = [cog for cog in self.bot.cogs.keys()]
        if cogs:
            embed = discord.Embed(
                title="📦 Loaded Cogs",
                description="\n".join(f"• `{cog}`" for cog in sorted(cogs)),
                color=discord.Color.blue()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send("❌ No cogs are currently loaded.", ephemeral=True)

    @botcontrol.command(name="profile", description="Show bot profile information")
    @app_commands.check(bot_control_check)
    async def botcontrol_profile(self, interaction: discord.Interaction):
        """Show bot profile information"""
        await interaction.response.defer(ephemeral=True)
        user = self.bot.user
        embed = discord.Embed(
            title="🤖 Bot Profile Information",
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        if user.banner:
            embed.set_image(url=user.banner.url)
        embed.add_field(name="Username", value=user.name, inline=True)
        embed.add_field(name="ID", value=user.id, inline=True)
        embed.add_field(name="Discriminator", value=user.discriminator if user.discriminator != "0" else "None", inline=True)
        embed.add_field(name="Created At", value=user.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=False)
        embed.add_field(name="Servers", value=len(self.bot.guilds), inline=True)
        embed.add_field(name="Users", value=sum(g.member_count for g in self.bot.guilds), inline=True)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @botcontrol.command(name="pause", description="Pause status auto-cycling")
    @app_commands.check(bot_control_check)
    async def botcontrol_pause(self, interaction: discord.Interaction):
        """Pause status auto-cycling"""
        await interaction.response.defer(ephemeral=True)
        self.cycle_paused = True
        embed = discord.Embed(
            title="⏸️ Status Cycling Paused",
            description="Status auto-cycling has been paused.",
            color=discord.Color.orange()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @botcontrol.command(name="resume", description="Resume status auto-cycling")
    @app_commands.check(bot_control_check)
    async def botcontrol_resume(self, interaction: discord.Interaction):
        """Resume status auto-cycling"""
        await interaction.response.defer(ephemeral=True)
        self.cycle_paused = False
        embed = discord.Embed(
            title="▶️ Status Cycling Resumed",
            description="Status auto-cycling has been resumed.",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Owner(bot))
            
