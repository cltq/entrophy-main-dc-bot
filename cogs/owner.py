import os
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

    # ---------- MANUAL STATUS ----------
    @commands.command(name="status", help="Change bot presence manually (Admin only)")
    @commands.is_owner()
    async def change_status(self, ctx, *, text: str):
        self.cycle_paused = True
        await self.bot.change_presence(activity=discord.Game(text))
        await ctx.send(f"✅ Status changed to: `{text}`\n⏸️ Auto-cycling paused. Use `!resumecycle` to resume.")

    @change_status.error
    async def change_status_error(self, ctx, error):
        if isinstance(error, commands.NotOwner):
            await ctx.send("❌ Only the bot owner can use this command.")
        else:
            await ctx.send(f"❌ An error occurred: {error}")

    @commands.command(name="setstate", help="Change bot status mode (online/idle/dnd/invisible)")
    @commands.is_owner()
    async def set_bot_state(self, ctx, state: str):
        states = {
            "online": discord.Status.online,
            "idle": discord.Status.idle,
            "dnd": discord.Status.dnd,
            "invisible": discord.Status.invisible,
        }
        if state.lower() not in states:
            await ctx.send("⚠️ Invalid state. Use: online, idle, dnd, invisible.")
            return

        self.cycle_paused = false
        await self.bot.change_presence(status=states[state.lower()])
        await ctx.send(f"✅ Bot online status set to `{state}`\n⏸️ Auto-cycling paused. Use `!resumecycle` to resume.")

    @set_bot_state.error
    async def set_bot_state_error(self, ctx, error):
        if isinstance(error, commands.NotOwner):
            await ctx.send("❌ Only the bot owner can use this command.")
        else:
            await ctx.send(f"❌ An error occurred: {error}")

    @commands.command(name="resumecycle", help="Resume automatic status cycling")
    @commands.is_owner()
    async def resume_cycle(self, ctx):
        self.cycle_paused = False
        await ctx.send("▶️ Status auto-cycling resumed!")

    @resume_cycle.error
    async def resume_cycle_error(self, ctx, error):
        if isinstance(error, commands.NotOwner):
            await ctx.send("❌ Only the bot owner can use this command.")

    @commands.command(name="pausecycle", help="Pause automatic status cycling")
    @commands.is_owner()
    async def pause_cycle(self, ctx):
        self.cycle_paused = True
        await ctx.send("⏸️ Status auto-cycling paused!")

    @pause_cycle.error
    async def pause_cycle_error(self, ctx, error):
        if isinstance(error, commands.NotOwner):
            await ctx.send("❌ Only the bot owner can use this command.")

    # ---------- BOT PROFILE MANAGEMENT ----------
    @commands.command(name="setname", help="Change the bot's username")
    @commands.is_owner()
    async def set_name(self, ctx, *, name: str):
        """Change the bot's username"""
        try:
            await self.bot.user.edit(username=name)
            await ctx.send(f"✅ Bot username changed to: `{name}`")
        except discord.HTTPException as e:
            if e.status == 429:
                await ctx.send("❌ Rate limited! You can only change the bot's username twice per hour.")
            else:
                await ctx.send(f"❌ Failed to change username: {e}")
        except Exception as e:
            await ctx.send(f"❌ An error occurred: {e}")

    @set_name.error
    async def set_name_error(self, ctx, error):
        if isinstance(error, commands.NotOwner):
            await ctx.send("❌ Only the bot owner can use this command.")

    @commands.command(name="setavatar", help="Change the bot's profile picture")
    @commands.is_owner()
    async def set_avatar(self, ctx, url: str = None):
        """
        Change the bot's profile picture
        Usage: !setavatar <image_url> or attach an image
        """
        try:
            # Check if image is attached
            if ctx.message.attachments:
                image_url = ctx.message.attachments[0].url
            elif url:
                image_url = url
            else:
                await ctx.send("❌ Please provide an image URL or attach an image.")
                return

            # Download the image
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as resp:
                    if resp.status != 200:
                        await ctx.send("❌ Failed to download the image.")
                        return
                    image_data = await resp.read()

            # Set the avatar
            await self.bot.user.edit(avatar=image_data)
            await ctx.send("✅ Bot avatar updated successfully!")

        except discord.HTTPException as e:
            if e.status == 429:
                await ctx.send("❌ Rate limited! You can only change the bot's avatar a few times per hour.")
            else:
                await ctx.send(f"❌ Failed to change avatar: {e}")
        except Exception as e:
            await ctx.send(f"❌ An error occurred: {e}")

    @set_avatar.error
    async def set_avatar_error(self, ctx, error):
        if isinstance(error, commands.NotOwner):
            await ctx.send("❌ Only the bot owner can use this command.")

    @commands.command(name="setbio", help="Change the bot's profile description")
    @commands.is_owner()
    async def set_bio(self, ctx, *, bio: str):
        """
        Change the bot's profile description (About Me)
        Note: This requires the bot to have a premium subscription
        """
        try:
            await self.bot.user.edit(bio=bio)
            await ctx.send(f"✅ Bot bio updated to:\n```{bio}```")
        except discord.HTTPException as e:
            if "premium" in str(e).lower():
                await ctx.send("❌ Setting a bio requires the bot to have Discord premium (bot subscription).")
            else:
                await ctx.send(f"❌ Failed to change bio: {e}")
        except Exception as e:
            await ctx.send(f"❌ An error occurred: {e}")

    @set_bio.error
    async def set_bio_error(self, ctx, error):
        if isinstance(error, commands.NotOwner):
            await ctx.send("❌ Only the bot owner can use this command.")

    @commands.command(name="setbanner", help="Change the bot's profile banner")
    @commands.is_owner()
    async def set_banner(self, ctx, url: str = None):
        """
        Change the bot's profile banner
        Usage: !setbanner <image_url> or attach an image
        Note: This requires the bot to have a premium subscription
        """
        try:
            # Check if image is attached
            if ctx.message.attachments:
                image_url = ctx.message.attachments[0].url
            elif url:
                image_url = url
            else:
                await ctx.send("❌ Please provide an image URL or attach an image.")
                return

            # Download the image
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as resp:
                    if resp.status != 200:
                        await ctx.send("❌ Failed to download the image.")
                        return
                    image_data = await resp.read()

            # Set the banner
            await self.bot.user.edit(banner=image_data)
            await ctx.send("✅ Bot banner updated successfully!")

        except discord.HTTPException as e:
            if "premium" in str(e).lower():
                await ctx.send("❌ Setting a banner requires the bot to have Discord premium (bot subscription).")
            else:
                await ctx.send(f"❌ Failed to change banner: {e}")
        except Exception as e:
            await ctx.send(f"❌ An error occurred: {e}")

    @set_banner.error
    async def set_banner_error(self, ctx, error):
        if isinstance(error, commands.NotOwner):
            await ctx.send("❌ Only the bot owner can use this command.")

    @commands.command(name="removebanner", help="Remove the bot's profile banner")
    @commands.is_owner()
    async def remove_banner(self, ctx):
        """Remove the bot's profile banner"""
        try:
            await self.bot.user.edit(banner=None)
            await ctx.send("✅ Bot banner removed successfully!")
        except discord.HTTPException as e:
            await ctx.send(f"❌ Failed to remove banner: {e}")
        except Exception as e:
            await ctx.send(f"❌ An error occurred: {e}")

    @remove_banner.error
    async def remove_banner_error(self, ctx, error):
        if isinstance(error, commands.NotOwner):
            await ctx.send("❌ Only the bot owner can use this command.")

    @commands.command(name="botinfo", help="Display current bot profile information")
    @commands.is_owner()
    async def profile_info(self, ctx):
        """Display current bot profile information"""
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

        # Note: Bio might not be accessible via self.bot.user
        embed.add_field(name="Created At", value=user.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=False)
        embed.add_field(name="Servers", value=len(self.bot.guilds), inline=True)
        embed.add_field(name="Users", value=sum(g.member_count for g in self.bot.guilds), inline=True)

        await ctx.send(embed=embed)

    @profile_info.error
    async def profile_info_error(self, ctx, error):
        if isinstance(error, commands.NotOwner):
            await ctx.send("❌ Only the bot owner can use this command.")

    # ---------- SYNC COMMAND ----------
    @commands.command(name="sync", help="Sync slash commands")
    @commands.guild_only()
    @commands.is_owner()
    async def sync(
        self,
        ctx: commands.Context,
        guilds: commands.Greedy[discord.Object],
        spec: Optional[Literal["current", "global", "remove"]] = None
    ) -> None:
        """
        Sync slash commands to Discord.

        Usage:
        - !sync -> Sync globally
        - !sync current -> Sync to current guild
        - !sync global -> Copy global commands to current guild
        - !sync remove -> Remove all commands from current guild
        - !sync [guild_id] -> Sync to specific guild(s)
        """
        if not guilds:
            if spec == "current":
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "global":
                ctx.bot.tree.copy_global_to(guild=ctx.guild)
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "remove":
                ctx.bot.tree.clear_commands(guild=ctx.guild)
                await ctx.bot.tree.sync(guild=ctx.guild)
                synced = []
            else:
                synced = await ctx.bot.tree.sync()

            await ctx.send(
                f"✅ Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}"
            )
            return

        ret = 0
        for guild in guilds:
            try:
                await ctx.bot.tree.sync(guild=guild)
            except discord.HTTPException:
                pass
            else:
                ret += 1

        await ctx.send(f"✅ Synced the tree to {ret}/{len(guilds)} guild(s).")

    @sync.error
    async def sync_error(self, ctx, error):
        if isinstance(error, commands.NotOwner):
            await ctx.send("❌ Only the bot owner can use this command.")
        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.send("❌ This command can only be used in a server.")
        else:
            await ctx.send(f"❌ An error occurred: {error}")

    # ---------- RELOAD COMMAND ----------
    @commands.command(name="reload", help="Reload a specific cog")
    @commands.is_owner()
    async def reload_cog(self, ctx, cog_name: str):
        """Reload a cog without restarting the bot"""
        try:
            await self.bot.reload_extension(f"cogs.{cog_name}")
            await ctx.send(f"✅ Reloaded cog: `{cog_name}`")
        except commands.ExtensionNotFound:
            await ctx.send(f"❌ Cog `{cog_name}` not found.")
        except commands.ExtensionNotLoaded:
            await ctx.send(f"❌ Cog `{cog_name}` is not loaded.")
        except Exception as e:
            await ctx.send(f"❌ Failed to reload `{cog_name}`: {e}")

    @reload_cog.error
    async def reload_cog_error(self, ctx, error):
        if isinstance(error, commands.NotOwner):
            await ctx.send("❌ Only the bot owner can use this command.")

    # ---------- LOAD COMMAND ----------
    @commands.command(name="load", help="Load a cog")
    @commands.is_owner()
    async def load_cog(self, ctx, cog_name: str):
        """Load a cog"""
        try:
            await self.bot.load_extension(f"cogs.{cog_name}")
            await ctx.send(f"✅ Loaded cog: `{cog_name}`")
        except commands.ExtensionNotFound:
            await ctx.send(f"❌ Cog `{cog_name}` not found.")
        except commands.ExtensionAlreadyLoaded:
            await ctx.send(f"❌ Cog `{cog_name}` is already loaded.")
        except Exception as e:
            await ctx.send(f"❌ Failed to load `{cog_name}`: {e}")

    @load_cog.error
    async def load_cog_error(self, ctx, error):
        if isinstance(error, commands.NotOwner):
            await ctx.send("❌ Only the bot owner can use this command.")

    # ---------- UNLOAD COMMAND ----------
    @commands.command(name="unload", help="Unload a cog")
    @commands.is_owner()
    async def unload_cog(self, ctx, cog_name: str):
        """Unload a cog"""
        if cog_name.lower() == "owner":
            await ctx.send("❌ Cannot unload the Owner cog!")
            return

        try:
            await self.bot.unload_extension(f"cogs.{cog_name}")
            await ctx.send(f"✅ Unloaded cog: `{cog_name}`")
        except commands.ExtensionNotLoaded:
            await ctx.send(f"❌ Cog `{cog_name}` is not loaded.")
        except Exception as e:
            await ctx.send(f"❌ Failed to unload `{cog_name}`: {e}")

    @unload_cog.error
    async def unload_cog_error(self, ctx, error):
        if isinstance(error, commands.NotOwner):
            await ctx.send("❌ Only the bot owner can use this command.")

    # ---------- LIST COGS ----------
    @commands.command(name="cogs", help="List all loaded cogs")
    @commands.is_owner()
    async def list_cogs(self, ctx):
        """List all currently loaded cogs"""
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

    @list_cogs.error
    async def list_cogs_error(self, ctx, error):
        if isinstance(error, commands.NotOwner):
            await ctx.send("❌ Only the bot owner can use this command.")

    # ---------- SHUTDOWN ----------
    @commands.command(name="shutdown")
    @commands.is_owner()
    async def shutdown(self, ctx):
        """Shutdown the bot"""
        await ctx.send("🛑 Shutting down bot...")
        await self.bot.close()

    @shutdown.error
    async def shutdown_error(self, ctx, error):
        if isinstance(error, commands.NotOwner):
            await ctx.send("❌ Only the bot owner can use this command.")


async def setup(bot):
    await bot.add_cog(Owner(bot))
