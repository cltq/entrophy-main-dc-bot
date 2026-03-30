import asyncio
import datetime
import json
import os
import sys
from typing import Any

import discord
from discord.ext import commands

from utils.helpers import BANGKOK_TZ

RESTART_INFO_FILE: str = "restart_info.json"


class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot

    def is_admin_or_owner() -> Any:
        async def predicate(ctx: commands.Context) -> bool:
            if await ctx.bot.is_owner(ctx.author):
                return True
            if ctx.guild:
                admin_role = discord.utils.get(ctx.guild.roles, name="Admin")
                if admin_role and admin_role in ctx.author.roles:
                    return True
            raise commands.MissingPermissions(["Admin role or Bot Owner"])
        return commands.check(predicate)

    @commands.command()
    @is_admin_or_owner()
    async def restart(self, ctx: commands.Context) -> None:
        restart_meta = {
            "requested_by_id": ctx.author.id,
            "requested_by_name": str(ctx.author),
            "guild_id": ctx.guild.id if ctx.guild else None,
            "channel_id": ctx.channel.id if ctx.channel else None,
            "timestamp": datetime.datetime.now(BANGKOK_TZ).isoformat()
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
            timestamp=datetime.datetime.now(BANGKOK_TZ)
        )
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)
        await asyncio.sleep(2)
        os.execv(sys.executable, ["python"] + sys.argv)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Admin(bot))
