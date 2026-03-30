import os
import sys
import datetime
from itertools import cycle
from typing import Any, Optional

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks
from utils.helpers import get_uptime, get_bangkok_time


class Owner(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot
        self.cycle_paused: bool = False
        self.statuses = cycle([
            lambda: f"Uptime: {get_uptime(getattr(self.bot, 'launch_time', None))}",
            lambda: f"Owner: {self.bot.get_user(int(os.getenv('BOT_OWNER_ID', 0))).name if self.bot.get_user(int(os.getenv('BOT_OWNER_ID', 0))) else 'Unknown'}",
            lambda: f"Serving {len(self.bot.guilds)} servers",
            lambda: f"Time: {get_bangkok_time().strftime('%H:%M:%S')}",
        ])
        self.status_cycle.start()

    def cog_unload(self) -> None:
        self.status_cycle.cancel()

    @tasks.loop(seconds=5)
    async def status_cycle(self) -> None:
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
    async def before_status_cycle(self) -> None:
        await self.bot.wait_until_ready()

    @commands.command(name="bot", help="Owner-only: manage the bot with subcommands.")
    @commands.is_owner()
    async def bot(self, ctx: commands.Context, action: str, *params: str) -> None:
        action = action.lower()

        if action in ("status", "setstatus", "stat", "setstate", "state"):
            states = {
                "online": discord.Status.online,
                "idle": discord.Status.idle,
                "dnd": discord.Status.dnd,
                "invisible": discord.Status.invisible,
            }
            if len(params) == 1 and params[0].lower() in states:
                state = params[0].lower()
                self.cycle_paused = True
                try:
                    await self.bot.change_presence(status=states[state])
                    await ctx.send(f"✅ Bot online status set to `{state}`\n⏸️ Auto-cycling paused.")
                except Exception as e:
                    await ctx.send(f"❌ Failed to set state: {e}")
                return

            text = " ".join(params).strip()
            if not text:
                await ctx.send("❌ Please provide a status text or a state keyword.")
                return
            self.cycle_paused = True
            await self.bot.change_presence(activity=discord.Game(text))
            await ctx.send(f"✅ Status changed to: `{text}`\n⏸️ Auto-cycling paused.")
            return

        if action in ("resume", "resumecycle", "unpause"):
            self.cycle_paused = False
            await ctx.send("▶️ Status auto-cycling resumed!")
            return

        if action in ("pause", "pausecycle"):
            self.cycle_paused = True
            await ctx.send("⏸️ Status auto-cycling paused!")
            return

        if action in ("setname", "name"):
            name = " ".join(params).strip()
            if not name:
                await ctx.send("❌ Please provide a new username.")
                return
            try:
                await self.bot.user.edit(username=name)
                await ctx.send(f"✅ Bot username changed to: `{name}`")
            except discord.HTTPException as e:
                if getattr(e, "status", None) == 429:
                    await ctx.send("❌ Rate limited!")
                else:
                    await ctx.send(f"❌ Failed: {e}")
            return

        if action in ("setavatar", "avatar"):
            image_url = params[0] if params else None
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
            except Exception as e:
                await ctx.send(f"❌ Failed: {e}")
            return

        if action in ("setbanner", "banner"):
            image_url = params[0] if params else None
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
            except Exception as e:
                await ctx.send(f"❌ Failed: {e}")
            return

        if action in ("removebanner", "delbanner"):
            try:
                await self.bot.user.edit(banner=None)
                await ctx.send("✅ Bot banner removed successfully!")
            except Exception as e:
                await ctx.send(f"❌ Failed: {e}")
            return

        if action in ("profile", "botinfo"):
            user = self.bot.user
            embed = discord.Embed(title="🤖 Bot Profile", color=discord.Color.blue())
            if user:
                embed.set_thumbnail(url=user.display_avatar.url)
                if user.banner:
                    embed.set_image(url=user.banner.url)
                embed.add_field(name="Username", value=user.name, inline=True)
                embed.add_field(name="ID", value=user.id, inline=True)
                embed.add_field(name="Created At", value=user.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=False)
            embed.add_field(name="Servers", value=len(self.bot.guilds), inline=True)
            total_members = sum(g.member_count or 0 for g in self.bot.guilds)
            embed.add_field(name="Users", value=str(total_members), inline=True)
            await ctx.send(embed=embed)
            return

        if action == "sync":
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

        if action in ("reload", "load", "unload"):
            if not params:
                await ctx.send("❌ Please provide a cog name.")
                return
            cog_name = params[0]
            try:
                if action == "reload":
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
            except Exception as e:
                await ctx.send(f"❌ Failed to {action} `{cog_name}`: {e}")
            return

        if action == "cogs":
            cogs = list(self.bot.cogs.keys())
            if cogs:
                embed = discord.Embed(title="📦 Loaded Cogs", description="\n".join(f"• `{cog}`" for cog in sorted(cogs)), color=discord.Color.blue())
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ No cogs are currently loaded.")
            return

        if action in ("shutdown", "stop"):
            await ctx.send("🛑 Shutting down bot...")
            await self.bot.close()
            return

        if action == "restart":
            await ctx.send("🔄 Restarting bot...")
            await self.bot.close()
            os.execv(sys.executable, [sys.executable] + sys.argv)

        await ctx.send("❌ Unknown action. Use `!bot help` for usage.")

    @bot.error
    async def bot_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        if isinstance(error, commands.NotOwner):
            await ctx.send("❌ Only the bot owner can use this command.")
        else:
            await ctx.send(f"❌ An error occurred: {error}")

    async def bot_control_check(self, interaction: discord.Interaction) -> bool:
        owner_id = int(os.getenv("BOT_OWNER_ID", 0))
        return interaction.user.id == owner_id

    async def action_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        actions = ["restart", "shutdown", "reload", "load", "unload", "sync", "cogs", "profile", "pause", "resume"]
        return [app_commands.Choice(name=action, value=action) for action in actions if action.startswith(current.lower())]

    @app_commands.command(name="botcontrol", description="Bot control panel (Owner only)")
    @app_commands.check(bot_control_check)
    @app_commands.describe(action="The action to perform", args="Arguments for the action")
    @app_commands.autocomplete(action=action_autocomplete)
    async def botcontrol(self, interaction: discord.Interaction, action: str, args: Optional[str] = None) -> None:
        await interaction.response.defer(ephemeral=True)
        action = action.lower()

        if action == "restart":
            await interaction.followup.send(embed=discord.Embed(title="🔄 Bot Restart", description="Restarting...", color=discord.Color.orange()), ephemeral=True)
            await self.bot.close()
            return

        if action == "shutdown":
            await interaction.followup.send(embed=discord.Embed(title="🛑 Bot Shutdown", description="Shutting down...", color=discord.Color.red()), ephemeral=True)
            await self.bot.close()
            return

        if action == "reload":
            if not args:
                await interaction.followup.send("❌ Please provide a cog name.", ephemeral=True)
                return
            try:
                await self.bot.unload_extension(f"cogs.{args}")
                await self.bot.load_extension(f"cogs.{args}")
                await interaction.followup.send(embed=discord.Embed(title="✅ Cog Reloaded", description=f"`{args}`", color=discord.Color.green()), ephemeral=True)
            except Exception as e:
                await interaction.followup.send(embed=discord.Embed(title="❌ Failed", description=str(e), color=discord.Color.red()), ephemeral=True)
            return

        if action == "load":
            if not args:
                await interaction.followup.send("❌ Please provide a cog name.", ephemeral=True)
                return
            try:
                await self.bot.load_extension(f"cogs.{args}")
                await interaction.followup.send(embed=discord.Embed(title="✅ Cog Loaded", description=f"`{args}`", color=discord.Color.green()), ephemeral=True)
            except Exception as e:
                await interaction.followup.send(embed=discord.Embed(title="❌ Failed", description=str(e), color=discord.Color.red()), ephemeral=True)
            return

        if action == "unload":
            if not args:
                await interaction.followup.send("❌ Please provide a cog name.", ephemeral=True)
                return
            if args.lower() == "owner":
                await interaction.followup.send("❌ Cannot unload the Owner cog!", ephemeral=True)
                return
            try:
                await self.bot.unload_extension(f"cogs.{args}")
                await interaction.followup.send(embed=discord.Embed(title="✅ Cog Unloaded", description=f"`{args}`", color=discord.Color.green()), ephemeral=True)
            except Exception as e:
                await interaction.followup.send(embed=discord.Embed(title="❌ Failed", description=str(e), color=discord.Color.red()), ephemeral=True)
            return

        if action == "sync":
            try:
                synced = await self.bot.tree.sync()
                await interaction.followup.send(embed=discord.Embed(title="✅ Synced", description=f"{len(synced)} commands", color=discord.Color.green()), ephemeral=True)
            except Exception as e:
                await interaction.followup.send(embed=discord.Embed(title="❌ Failed", description=str(e), color=discord.Color.red()), ephemeral=True)
            return

        if action == "cogs":
            cogs = list(self.bot.cogs.keys())
            embed = discord.Embed(title="📦 Loaded Cogs", description="\n".join(f"• `{cog}`" for cog in sorted(cogs)), color=discord.Color.blue())
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        if action == "profile":
            user = self.bot.user
            embed = discord.Embed(title="🤖 Bot Profile", color=discord.Color.blue())
            embed.set_thumbnail(url=user.display_avatar.url)
            if user.banner:
                embed.set_image(url=user.banner.url)
            embed.add_field(name="Username", value=user.name, inline=True)
            embed.add_field(name="ID", value=user.id, inline=True)
            embed.add_field(name="Servers", value=len(self.bot.guilds), inline=True)
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        if action == "pause":
            self.cycle_paused = True
            await interaction.followup.send(embed=discord.Embed(title="⏸️ Paused", description="Status cycling paused", color=discord.Color.orange()), ephemeral=True)
            return

        if action == "resume":
            self.cycle_paused = False
            await interaction.followup.send(embed=discord.Embed(title="▶️ Resumed", description="Status cycling resumed", color=discord.Color.green()), ephemeral=True)
            return

        await interaction.followup.send(f"❌ Unknown action: `{action}`", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Owner(bot))
