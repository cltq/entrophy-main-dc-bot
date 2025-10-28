import discord
import datetime
from discord.ext import commands
from utils.helpers import get_uptime
import pytz

bangkok_timezone = pytz.timezone('Asia/Bangkok')
current_datetime = datetime.datetime.now(bangkok_timezone)
hour = current_datetime.hour
minute = current_datetime.minute
second = current_datetime.second
formatted_time = current_datetime.strftime("%H:%M:%S")

class Utility(commands.Cog):
    """Utility commands"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="uptime")
    async def uptime(self, ctx):
        """Show bot uptime (prefix)"""
        await ctx.send(f"⏱️ Bot uptime: `{get_uptime(self.bot.launch_time)}`")

    @discord.app_commands.command(name="uptime", description="Show bot uptime")
    async def slash_uptime(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"⏱️ Bot uptime: `{get_uptime(self.bot.launch_time)}`")

    @commands.command(name="rtclock")
    async def rtclock(self, ctx):
        """Show bot uptime (prefix)"""
        await ctx.send(f"⏱️ Bot Realtime: `{formatted_time}`")

    @discord.app_commands.command(name="rtclock", description="Show bot realtime")
    async def slash_rtclock(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"⏱️ Bot Realtime: `{formatted_time}`")

async def setup(bot):
    await bot.add_cog(Utility(bot))
