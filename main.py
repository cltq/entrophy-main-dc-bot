import os, time, platform, sys, pytz, asyncio, datetime
import discord
from discord.ext import commands
from dotenv import load_dotenv
from typing import Literal, Optional
from keep_alive import keep_alive

systemPlatform = platform.system()

def systemPlatform_clear_delay():
    time.sleep(1)
    if systemPlatform == ('Windows'):
     os.system('cls')
     print(f'Your system is identified as {systemPlatform}, Cleared the Prompt')
    elif platform.system == ('Darwin'):
     os.system('clear')
     print(f'Your system is identified as {systemPlatform}, Cleared the Terminal')
    else:
     os.system('clear')
     print(f"Your system is identified as {systemPlatform}, Cleared the Terminal")


# systemPlatform_clear_delay()

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_ID = int(os.getenv("BOT_OWNER_ID"))

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=".", intents=intents)

# for tracking launch time
bot.launch_time = datetime.datetime.now(datetime.timezone.utc)

# ---------- EVENTS ----------
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    await sync_slash()
    print("🔁 Slash commands synced.")

# ---------- COMMAND LOGGING ----------
@bot.event
async def on_command(ctx):
    """Log whenever a prefix command is used"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user = f"{ctx.author} (ID: {ctx.author.id})"
    guild = f"{ctx.guild.name} (ID: {ctx.guild.id})" if ctx.guild else "DM"
    command = ctx.command.name
    args = ' '.join(ctx.args[2:]) if len(ctx.args) > 2 else "No args"

    print(f"[{timestamp}] 📝 Command: !{command}")
    print(f"  └─ User: {user}")
    print(f"  └─ Guild: {guild}")
    print(f"  └─ Channel: #{ctx.channel}")
    if args != "No args":
        print(f"  └─ Args: {args}")

@bot.event
async def on_app_command_completion(interaction: discord.Interaction, command):
    """Log whenever a slash command is used"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user = f"{interaction.user} (ID: {interaction.user.id})"
    guild = f"{interaction.guild.name} (ID: {interaction.guild.id})" if interaction.guild else "DM"
    cmd_name = command.name

    print(f"[{timestamp}] ⚡ Slash Command: /{cmd_name}")
    print(f"  └─ User: {user}")
    print(f"  └─ Guild: {guild}")
    print(f"  └─ Channel: #{interaction.channel}")

# ---------- ERROR HANDLER ----------
@bot.event
async def on_command_error(ctx, error):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingPermissions):
        print(f"[{timestamp}] ⚠️ {ctx.author} tried to use {ctx.command.name} without permissions")
        await ctx.send("⚠️ You lack permissions to use this command.")
    elif isinstance(error, commands.NotOwner):
        print(f"[{timestamp}] ❌ {ctx.author} tried to use owner-only command: {ctx.command.name}")
        await ctx.send("❌ This command is restricted to the bot owner.")
    else:
        print(f"[{timestamp}] ❌ Error in {ctx.command.name}: {error}")
        await ctx.send(f"❌ Error: `{error}`")
        raise error

# ---------- UTIL FUNCTIONS ----------
async def sync_slash():
    synced = await bot.tree.sync()
    print(f"🔁 Synced {len(synced)} slash commands")

# ---------- LOAD ALL COGS ----------
async def load_cogs():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            await bot.load_extension(f"cogs.{filename[:-3]}")
            print(f"📦 Loaded cog: {filename[:-3]}")

async def main():
    async with bot:
        await load_cogs()
        await bot.start(TOKEN)

if __name__ == "__main__":
    keep_alive()  # Start the web server
    asyncio.run(main())
