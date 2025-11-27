import os, time, platform, sys, pytz, asyncio, datetime
import logging
import discord
from discord.ext import commands
from utils.discord_logger import DiscordHandler
from utils.log_buffer import BufferHandler
from dashboard.server import start_dashboard
from dotenv import load_dotenv
from typing import Literal, Optional
try:
    # keep_alive may not be present in some deployments; import safely
    from keep_alive import keep_alive
except Exception:
    keep_alive = None

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
OWNER_ID = int(os.getenv("BOT_OWNER_ID") or 0)
# Allow setting a bot prefix via env; default to 'q' for backwards compatibility
botprefix = str(os.getenv("BOT_PREFIX") or "q")

intents = discord.Intents.default()
intents.message_content = True  # Required for reading message content (e.g. !commands)
intents.members = True           # Required for accessing member info or DMing them
intents.dm_messages = True       # Needed for handling DMs properly
bot = commands.Bot(command_prefix=botprefix, intents=intents)

# for tracking launch time
bot.launch_time = datetime.datetime.now(datetime.timezone.utc)

# ---------- LOGGING ----------
logger = logging.getLogger("entrophy")
logger.setLevel(logging.INFO)
fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
stream = logging.StreamHandler()
stream.setFormatter(fmt)
logger.addHandler(stream)
# Add in-memory buffer handler for dashboard
try:
    buf = BufferHandler()
    logger.addHandler(buf)
except Exception:
    logger.exception('Failed to attach BufferHandler')

# Add rotating file handler to persist logs for 'all logs' page
try:
    import logging.handlers
    os.makedirs(os.path.join(os.getcwd(), 'logs'), exist_ok=True)
    fileh = logging.handlers.RotatingFileHandler(os.path.join('logs', 'entrophy.log'), maxBytes=2_000_000, backupCount=5, encoding='utf-8')
    fileh.setFormatter(fmt)
    logger.addHandler(fileh)
except Exception:
    logger.exception('Failed to attach file handler')

# Optionally send logs to a Discord channel (set LOG_CHANNEL_ID in .env)
LOG_CHANNEL_ID = os.getenv("LOG_CHANNEL_ID")

# Prepare optional discord handler attach function (runs in setup_hook)
async def _attach_discord_handler_if_configured():
    if not LOG_CHANNEL_ID:
        return
    try:
        discord_handler = DiscordHandler(bot, int(LOG_CHANNEL_ID))
        discord_handler.setFormatter(fmt)
        logger.addHandler(discord_handler)
        try:
            await discord_handler.start()
        except Exception:
            logger.exception("Failed to start DiscordHandler task")
        logger.info("DiscordHandler attached")
    except Exception:
        logger.exception("Failed to attach DiscordHandler")


# Use the bot's async setup hook to attach handlers and start the dashboard
try:
    original_setup = getattr(bot, 'setup_hook', None)

    async def combined_setup():
        if original_setup:
            await original_setup()
        # Attach discord handler if configured
        await _attach_discord_handler_if_configured()

        # Start dashboard server if requested (separate from Discord handler)
        try:
            if os.getenv('DASHBOARD_ENABLED', 'true').lower() in ('1', 'true', 'yes'):
                host = os.getenv('DASHBOARD_HOST', '0.0.0.0')
                # Prefer Render's $PORT if available
                port = int(os.getenv('PORT') or os.getenv('DASHBOARD_PORT', '8080'))
                # start in background; avoid blocking setup
                bot.loop.create_task(start_dashboard(bot, host=host, port=port))
                logger.info(f"Dashboard scheduled on {host}:{port}")
        except Exception:
            logger.exception('Failed to start dashboard')

    bot.setup_hook = combined_setup
except Exception:
    # If we cannot set setup_hook, we'll rely on on_ready or other fallback
    logger.exception('Failed to install setup_hook')

    # ---------- LOG HELPERS ----------
    def format_user(user: discord.abc.User):
        try:
            name = getattr(user, 'display_name', None) or getattr(user, 'name', str(user))
            discr = getattr(user, 'discriminator', None)
            uname = getattr(user, 'name', str(user))
            if discr:
                uname_full = f"{uname}#{discr}"
            else:
                uname_full = uname
            return f"{name} ({uname_full}) [ID:{getattr(user,'id','unknown')}]"
        except Exception:
            return f"{getattr(user,'id','unknown')}"

    def format_channel_and_guild_from_ctx(ctx):
        # Channel info
        try:
            if ctx.guild:
                ch = ctx.channel
                ch_name = getattr(ch, 'name', str(ch))
                ch_id = getattr(ch, 'id', 'unknown')
                channel_str = f"{ch_name} [ID:{ch_id}]"
                guild_str = f"{ctx.guild.name} [ID:{ctx.guild.id}]"
            else:
                user = ctx.author
                channel_str = f"DM with {user.display_name} ({user.name}#{user.discriminator}) [ID:{user.id}]"
                guild_str = "DM"
        except Exception:
            channel_str = str(ctx.channel)
            guild_str = str(getattr(ctx, 'guild', ''))
        return channel_str, guild_str

    def format_channel_and_guild_from_interaction(interaction: discord.Interaction):
        try:
            if interaction.guild:
                ch = interaction.channel
                ch_name = getattr(ch, 'name', str(ch))
                ch_id = getattr(ch, 'id', 'unknown')
                channel_str = f"{ch_name} [ID:{ch_id}]"
                guild_str = f"{interaction.guild.name} [ID:{interaction.guild.id}]"
            else:
                user = interaction.user
                channel_str = f"DM with {user.display_name} ({user.name}#{user.discriminator}) [ID:{user.id}]"
                guild_str = "DM"
        except Exception:
            channel_str = str(interaction.channel)
            guild_str = str(getattr(interaction, 'guild', ''))
        return channel_str, guild_str

# ---------- EVENTS ----------
@bot.event
async def on_ready():
    logger.info(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    await sync_slash()
    logger.info("🔁 Slash commands synced.")

# ---------- COMMAND LOGGING ----------
@bot.event
async def on_command(ctx):
    """Log whenever a prefix command is used"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user = f"{ctx.author} (ID: {ctx.author.id})"
    guild = f"{ctx.guild.name} (ID: {ctx.guild.id})" if ctx.guild else "DM"
    command = ctx.command.name
    args = ' '.join(ctx.args[2:]) if len(ctx.args) > 2 else "No args"

    user_str = format_user(ctx.author)
    channel_str, guild_str = format_channel_and_guild_from_ctx(ctx)
    logger.info(f"[{timestamp}] 📝 Command: {botprefix}{command} — User: {user_str} — Guild: {guild_str} — Channel: {channel_str} — Args: {args}")

@bot.event
async def on_app_command_completion(interaction: discord.Interaction, command):
    """Log whenever a slash command is used"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user = f"{interaction.user} (ID: {interaction.user.id})"
    guild = f"{interaction.guild.name} (ID: {interaction.guild.id})" if interaction.guild else "DM"
    cmd_name = command.name

    user_str = format_user(interaction.user)
    channel_str, guild_str = format_channel_and_guild_from_interaction(interaction)
    logger.info(f"[{timestamp}] ⚡ Slash Command: /{cmd_name} — User: {user_str} — Guild: {guild_str} — Channel: {channel_str}")

# ---------- ERROR HANDLER ----------
@bot.event
async def on_command_error(ctx, error):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingPermissions):
        logger.warning(f"[{timestamp}] ⚠️ {ctx.author} tried to use {ctx.command.name} without permissions")
        await ctx.send("⚠️ You lack permissions to use this command.")
    elif isinstance(error, commands.NotOwner):
        logger.warning(f"[{timestamp}] ❌ {ctx.author} tried to use owner-only command: {ctx.command.name}")
        await ctx.send("❌ This command is restricted to the bot owner.")
    else:
        logger.exception(f"[{timestamp}] ❌ Error in {ctx.command.name}: {error}")
        await ctx.send(f"❌ Error: `{error}`")
        raise error

# ---------- UTIL FUNCTIONS ----------
async def sync_slash():
    synced = await bot.tree.sync()
    logger.info(f"🔁 Synced {len(synced)} slash commands")

    # Debug: list registered app commands and where they're registered
    try:
        for cmd in bot.tree.get_commands():
            guilds = getattr(cmd, 'guilds', None)
            if guilds:
                # guilds may be a sequence of Guild or Object; print ids
                ids = []
                for g in guilds:
                    try:
                        ids.append(getattr(g, 'id', g))
                    except Exception:
                        ids.append(str(g))
                logger.info(f"  - {cmd.name}: guild-only -> {ids}")
            else:
                logger.info(f"  - {cmd.name}: global")
    except Exception:
        pass

# ---------- LOAD ALL COGS ----------
async def load_cogs():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            await bot.load_extension(f"cogs.{filename[:-3]}")
            logger.info(f"📦 Loaded cog: {filename[:-3]}")

async def main():
    async with bot:
        await load_cogs()
        await bot.start(TOKEN)

if __name__ == "__main__":
    # Start the optional keep-alive webserver if available and enabled via env
    # Only start the Flask keep_alive if the aiohttp dashboard is NOT enabled.
    dashboard_enabled = os.getenv('DASHBOARD_ENABLED', 'true').lower() in ('1', 'true', 'yes')
    if keep_alive and os.getenv("KEEP_ALIVE", "false").lower() in ("1", "true", "yes") and not dashboard_enabled:
        try:
            keep_alive()
            logger.info("keep_alive enabled")
        except Exception:
            logger.exception("Failed to start keep_alive server")

    asyncio.run(main())
