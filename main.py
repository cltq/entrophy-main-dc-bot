import os
import asyncio
import logging
import logging.handlers
from datetime import datetime, timezone
from typing import Any, Optional

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

from utils.advanced_logger import setup_advanced_logger, LogLevel, log_command_execution, log_error, log_event
from utils.discord_logger import DiscordHandler
from utils.log_buffer import BufferHandler

load_dotenv()

TOKEN: str = os.getenv("DISCORD_TOKEN", "")
OWNER_ID: int = int(os.getenv("BOT_OWNER_ID") or 0)
BOT_PREFIX: str = os.getenv("BOT_PREFIX", "q")
GLOBAL_PREFIX: str = os.getenv("BOT_GLOBAL_PREFIX", "dev!")
LOG_CHANNEL_ID: Optional[str] = os.getenv("LOG_CHANNEL_ID")

intents: discord.Intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.dm_messages = True

bot: commands.Bot = commands.Bot(
    command_prefix=[BOT_PREFIX, GLOBAL_PREFIX],
    intents=intents,
    help_command=None
)

bot.launch_time: datetime = datetime.now(timezone.utc)

logger: Any = setup_advanced_logger("entrophy", level=LogLevel.VERBOSE)

try:
    buf = BufferHandler()
    logger.addHandler(buf)
except Exception:
    logger.exception("Failed to attach BufferHandler")

try:
    os.makedirs(os.path.join(os.getcwd(), "logs"), exist_ok=True)
    file_handler = logging.handlers.RotatingFileHandler(
        os.path.join("logs", "entrophy.log"),
        maxBytes=2_000_000,
        backupCount=5,
        encoding="utf-8"
    )
    from utils.advanced_logger import AdvancedFormatter
    file_handler.setFormatter(AdvancedFormatter())
    logger.addHandler(file_handler)
except Exception:
    logger.exception("Failed to attach file handler")


async def attach_discord_logger() -> None:
    if not LOG_CHANNEL_ID:
        return
    try:
        discord_handler = DiscordHandler(bot, int(LOG_CHANNEL_ID))
        from utils.advanced_logger import AdvancedFormatter
        discord_handler.setFormatter(AdvancedFormatter())
        logger.addHandler(discord_handler)
        try:
            await discord_handler.start()
        except Exception:
            logger.exception("Failed to start DiscordHandler task")
        logger.info("DiscordHandler attached")
    except Exception:
        logger.exception("Failed to attach DiscordHandler")


original_setup: Optional[Any] = getattr(bot, "setup_hook", None)

async def combined_setup() -> None:
    if original_setup:
        await original_setup()
    await attach_discord_logger()

bot.setup_hook = combined_setup


@bot.event
async def on_ready() -> None:
    log_event(logger, "Bot Ready", f"Logged in as {bot.user} (ID: {bot.user.id})")
    await sync_slash_commands()


@bot.event
async def on_command(ctx: commands.Context) -> None:
    args: str = " ".join(ctx.args[2:]) if len(ctx.args) > 2 else ""
    log_command_execution(
        logger, "prefix", ctx.command.name,
        ctx.author, ctx.guild, ctx.channel, args
    )


@bot.event
async def on_app_command_completion(interaction: discord.Interaction, command: app_commands.Command) -> None:
    log_command_execution(
        logger, "slash", command.name,
        interaction.user, interaction.guild, interaction.channel
    )


@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError) -> None:
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingPermissions):
        log_error(
            logger, "PermissionError",
            f"{ctx.author} tried to use {ctx.command.name} without permissions",
            user=ctx.author, command=ctx.command.name,
            channel=ctx.channel, guild=ctx.guild
        )
        await ctx.send("⚠️ You lack permissions to use this command.")
    elif isinstance(error, commands.NotOwner):
        log_error(
            logger, "OwnerOnly",
            f"{ctx.author} tried to use owner-only command: {ctx.command.name}",
            user=ctx.author, command=ctx.command.name,
            channel=ctx.channel, guild=ctx.guild
        )
        await ctx.send("❌ This command is restricted to the bot owner.")
    else:
        log_error(
            logger, "CommandError",
            f"Error in {ctx.command.name}: {error}",
            user=ctx.author, command=ctx.command.name,
            channel=ctx.channel, guild=ctx.guild, exc_info=True
        )
        await ctx.send(f"❌ Error: `{error}`")
        raise error


async def sync_slash_commands() -> None:
    synced: list[app_commands.Command] = await bot.tree.sync()
    log_event(logger, "SlashCommandsSync", f"Synced {len(synced)} slash commands")

    try:
        for cmd in bot.tree.get_commands():
            guilds = getattr(cmd, "guilds", None)
            if guilds:
                ids: list[Any] = [getattr(g, "id", g) for g in guilds]
                logger.verbose(f"Slash command {cmd.name}: guild-only -> {ids}")
            else:
                logger.verbose(f"Slash command {cmd.name}: global")
    except Exception:
        pass


async def load_cogs() -> None:
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py") and not filename.startswith("_"):
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                logger.info(f"📦 Loaded cog: {filename[:-3]}")
            except Exception:
                logger.exception(f"Failed to load cog: {filename[:-3]}")


async def main() -> None:
    async with bot:
        await load_cogs()
        await bot.start(TOKEN)


if __name__ == "__main__":
    try:
        from keep_alive import keep_alive
        if os.getenv("KEEP_ALIVE", "false").lower() in ("1", "true", "yes"):
            keep_alive()
            logger.info("keep_alive enabled")
    except ImportError:
        pass

    asyncio.run(main())
