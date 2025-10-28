import discord
from discord.ext import commands
import json
import datetime
import pytz
import asyncio
import os
import sys

RESTART_INFO_FILE = "restart_info.json"
bangkok_timezone = pytz.timezone('Asia/Bangkok')

class Admin(commands.Cog):
    """Admin commands for bot management."""

    def __init__(self, bot):
        self.bot = bot

    def is_admin_or_owner():
        """Check if user is admin or bot owner."""
        async def predicate(ctx):
            # Check if user is bot owner
            if await ctx.bot.is_owner(ctx.author):
                return True

            # Check if user has admin role
            if ctx.guild:
                admin_role = discord.utils.get(ctx.guild.roles, name="Admin")
                if admin_role and admin_role in ctx.author.roles:
                    return True

            # If neither, deny access
            raise commands.MissingPermissions(["Admin role or Bot Owner"])

        return commands.check(predicate)

    @commands.command()
    @is_admin_or_owner()
    async def restart(self, ctx):
        """Restart the bot process (loads new saved code)."""
        # Save restart meta so the new process can report who requested and where
        restart_meta = {
            "requested_by_id": ctx.author.id,
            "requested_by_name": str(ctx.author),
            "guild_id": ctx.guild.id if ctx.guild else None,
            "channel_id": ctx.channel.id if ctx.channel else None,
            "timestamp": datetime.datetime.now(bangkok_timezone).isoformat()
        }
        try:
            with open(RESTART_INFO_FILE, "w") as f:
                json.dump(restart_meta, f)
        except Exception:
            pass

        embed = discord.Embed(
            title="🔁 Restarting Bot",
            description="Please wait... restarting now.",
            color=discord.Color.orange(),
            timestamp=datetime.datetime.now(bangkok_timezone)
        )
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)
        await asyncio.sleep(2)

        try:
            # Assuming send_log is a function you have defined elsewhere
            # You may need to import it or adjust this based on your setup
            await self.send_log(ctx, "Bot Restart Initiated", ctx.author, "Manual restart requested")
        except Exception:
            pass

        # Exec to restart process
        os.execv(sys.executable, ['python'] + sys.argv)
        print(sys.argv)

    async def send_log(self, ctx, title, user, description):
        """Helper function for logging - adjust based on your implementation."""
        # Implement your logging logic here
        pass

async def setup(bot):
    await bot.add_cog(Admin(bot))
