import os
import datetime
import pytz
from itertools import cycle
from typing import Optional, Literal
import discord
from discord.ext import commands, tasks
from discord import app_commands
from utils.helpers import get_uptime

bangkok_timezone = pytz.timezone('Asia/Bangkok')

class Owner(commands.Cog):
    """Admin and owner commands"""

    def __init__(self, bot):
        self.bot = bot
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
        await self.bot.change_presence(activity=discord.Game(text))
        await ctx.send(f"✅ Status changed to: `{text}`")

    @change_status.error
    async def change_status_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need Administrator permissions to use this command.")
        else:
            await ctx.send(f"❌ An error occurred: {error}")

    @commands.command(name="setstate", help="Change bot status mode (online/idle/dnd/invisible)")
    @commands.is_owner()
    async def set_state(self, ctx, state: str):
        states = {
            "online": discord.Status.online,
            "idle": discord.Status.idle,
            "dnd": discord.Status.dnd,
            "invisible": discord.Status.invisible,
        }
        if state.lower() not in states:
            await ctx.send("⚠️ Invalid state. Use: online, idle, dnd, invisible.")
            return

        await self.bot.change_presence(status=states[state.lower()])
        await ctx.send(f"✅ Bot status set to `{state}`")

    @set_state.error
    async def set_state_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need Administrator permissions to use this command.")
        else:
            await ctx.send(f"❌ An error occurred: {error}")

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
