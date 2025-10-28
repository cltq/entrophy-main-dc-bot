import os, time, platform, sys, pytz, asyncio, datetime
import discord
from discord.ext import commands
from dotenv import load_dotenv
from typing import Literal, Optional
from keep_alive import keep_alive

systemPlatform = platform.system()

def systemPlatform_clear_delay():
    time.sleep(1)

def infoClearer():
    if systemPlatform == ('Windows'):
     print(f'Your system is identified as {systemPlatform}, Clearing the Prompt')
     systemPlatform_clear_delay()
     os.system('cls')
     print(f'Your system is identified as {systemPlatform}, Cleared the Prompt')
    elif platform.system == ('Darwin'):
     print(f'Your system is identified as {systemPlatform}, Clearing the Terminal')
     systemPlatform_clear_delay()
     os.system('clear')
     print(f'Your system is identified as {systemPlatform}, Cleared the Terminal')
    else:
     print(f"Your system is identified as {systemPlatform}, Clearing the Terminal")
     systemPlatform_clear_delay()
     os.system('clear')
     print(f"Your system is identified as {systemPlatform}, Cleared the Terminal")

# infoClearer()
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_ID = int(os.getenv("BOT_OWNER_ID"))

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# for tracking launch time
bot.launch_time = datetime.datetime.now(datetime.timezone.utc)

# ---------- EVENTS ----------
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    await sync_slash()
    print("🔁 Slash commands synced.")

# ---------- ERROR HANDLER ----------
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("⚠️ You lack permissions to use this command.")
    elif isinstance(error, commands.NotOwner):
        await ctx.send("❌ This command is restricted to the bot owner.")
    else:
        await ctx.send(f"❌ Error: `{error}`")
        raise error

# Set the custom help command
# bot.help_command = CustomHelp()

# ---------- UTIL FUNCTIONS ----------
async def sync_slash():
    synced = await bot.tree.sync()
    print(f"🔁 Synced {len(synced)} slash commands")

# ---------- LOAD ALL COGS ----------
async def load_cogs():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            await bot.load_extension(f"cogs.{filename[:-3]}")

async def main():
    async with bot:
        await load_cogs()
        await bot.start(TOKEN)

if __name__ == "__main__":
    keep_alive()  # Start the web server
    asyncio.run(main())
