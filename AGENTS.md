# Agent Guidelines for Entrophy Discord Bot

> **Note:** Every time in a different project, if the following AGENTS.md doesn't match the current project structure, update it automatically.

---

## General
- Use **Asia/Bangkok** or **GMT+7** timezone as the main timezone for every session
- Always run `git status` to check the current state before summarizing
- When task is done, summarize: 1) Changes made 2) How many commits 3) How many ongoing local commits not pushed (from git status)
- Create necessary tracking files if they don't exist: `GIT_HISTORY.md` for git commits, `AGENTS_HISTORY.md` for agent actions

---

## Project Overview
Entrophy is a Discord bot built with Python 3.10+, discord.py 2.0+, and various APIs (Gemini AI, Mojang, Roblox).

### Tech Stack
- Python 3.10+
- discord.py 2.0+ (slash commands, context menus)
- aiohttp for async HTTP requests
- PIL/Pillow for image processing

---

## Build & Development Commands

```bash
# Run the bot
python main.py

# Or with keep_alive (for web hosting)
python main.py
# (KEEP_ALIVE env var must be set to true)
```

---

## Code Style Guidelines

### Python
- Use **type hints** where applicable
- Use `async`/`await` for all Discord operations
- Follow PEP 8 with 100 char line limit
- Use f-strings for string formatting

### Naming Conventions
- **Modules/Files**: snake_case (e.g., `advanced_logger.py`, `game_profile_puller.py`)
- **Classes**: PascalCase (e.g., `General`, `OwnerCog`)
- **Functions**: snake_case (e.g., `get_uptime`, `fetch_roblox_user`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `LOG_BUFFER_MAX`, `BANGKOK_TZ`)

### Imports
Group in order:
1. Standard library
2. Third-party (discord, aiohttp, etc.)
3. Local utilities

Example:
```python
import os
import asyncio
from datetime import datetime

import discord
from discord.ext import commands

from utils.helpers import get_uptime
from utils.advanced_logger import logger
```

### Cogs
- Use `commands.Cog` base class
- Include both prefix commands and app commands (slash)
- Always include `setup(bot)` function at bottom
- Add proper docstrings

Example:
```python
import discord
from discord.ext import commands

class ExampleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="example")
    async def example_cmd(self, ctx):
        await ctx.send("Hello!")

    @discord.app_commands.command(name="example", description="Example command")
    async def example_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message("Hello!")

async def setup(bot):
    await bot.add_cog(ExampleCog(bot))
```

### Error Handling
- Use try/except for API calls
- Send user-friendly error messages
- Log errors with context for debugging

---

## Project Structure

```
Discordbot/
├── main.py              # Bot entry point
├── cogs/                # Command modules
│   ├── admin.py         # Admin commands
│   ├── ai.py            # AI chat (Gemini)
│   ├── general.py       # Basic commands
│   ├── gameprofilepuller.py  # Roblox/Minecraft lookup
│   ├── owner.py         # Owner controls
│   ├── payment.py       # PromptPay QR
│   ├── say.py           # Say command
│   ├── utility.py       # User info, uptime
│   └── work.py          # Todo, notes, reminders
├── utils/               # Utility modules
│   ├── advanced_logger.py
│   ├── discord_logger.py
│   ├── helpers.py
│   └── log_buffer.py
├── config/              # Config files
├── logs/                # Log files
├── data/                # User data
└── .env                 # Environment variables
```

---

## Logging
- Use the custom logger from `utils/advanced_logger.py`
- Log levels: VERBOSE, DEBUG, INFO, WARNING, ERROR, CRITICAL
- Include context (user, channel, guild) in logs

---

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DISCORD_TOKEN` | Discord bot token | Yes |
| `BOT_OWNER_ID` | Bot owner's Discord ID | Yes |
| `BOT_PREFIX` | Command prefix (default: q) | No |
| `BOT_GLOBAL_PREFIX` | Alternative prefix | No |
| `GEMINI_API_KEY` | Google Gemini API key | For AI |
| `LOG_CHANNEL_ID` | Discord log channel | No |
| `PROMPTPAY` | PromptPay number | For payment |
| `KEEP_ALIVE` | Enable web server | No |

---

## Git
- Commit with message every time code or files change
- Commit message format: "type: description - Files: list"
- Example: "refactor: clean up codebase - Files: main.py, cogs/"
- Log every commit in `GIT_HISTORY.md` with timestamp, description, and files changed
- Exception: AGENTS.md, .agents/CLAUDE.md, .agents/GEMINI.md should commit with message and push automatically if changed
- If "git status" shows local commits NOT present with remote, push GIT_HISTORY.md and AGENTS_HISTORY.md

---

## Agent History
- Log every agent action in `AGENTS_HISTORY.md` with:
  1. Agent used
  2. User requested message
  3. Agent response
  4. Everything the agent does
- Log every git commit in `GIT_HISTORY.md` with timestamp, description, and files changed
