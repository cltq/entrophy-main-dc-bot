# Entrophy - Discord Bot

A feature-rich Discord bot with AI integration, payment QR generation, game profile lookup, and utility commands.

## Features

- **AI Chat** - Gemini-powered conversational AI with customizable prompts per channel
- **PromptPay QR** - Generate Thai PromptPay QR codes for payments
- **Game Profiles** - Look up Roblox and Minecraft player profiles
- **Utilities** - User info, uptime, reminders, todo lists, notes
- **QWERTY to Thai** - Auto-correct mistyped Thai text
- **Bot Management** - Full owner control panel with slash commands

## Requirements

- Python 3.10+
- Discord Bot Token
- See `requirements.txt` for dependencies

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd Discordbot
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
Create a `.env` file with:
```env
DISCORD_TOKEN=your_bot_token
BOT_OWNER_ID=your_user_id
BOT_PREFIX=q
BOT_GLOBAL_PREFIX=dev!
GEMINI_API_KEY=your_gemini_api_key
LOG_CHANNEL_ID=optional_log_channel_id
KEEP_ALIVE=true  # For web hosting
GUILD_ID=your_server_id

# PromptPay accounts (optional)
PROMPTPAY=1234567890
PROMPTPAY_1=0987654321
```

4. Run the bot:
```bash
python main.py
```

## Commands

### General
- `/ping` - Check bot latency
- `/help` - View all commands

### Utility
- `/uptime` - Show bot uptime
- `/rtclock` - Show current Bangkok time
- `/usr [user]` - Get user information
- `/dashboard` - Get dashboard link

### Owner
- `/botcontrol` - Bot control panel (owner only)
  - `restart`, `shutdown`, `reload`, `load`, `unload`
  - `sync`, `cogs`, `profile`, `pause`, `resume`
- `!bot` - Prefix command version

### AI Chat
- `/setup [language]` - Setup AI chat channel
- `/list_channels` - List configured channels
- `/remove_channel` - Remove channel configuration
- `/ask [question]` - Ask AI directly
- Prefix: `!aisetup`, `!ask`, `!ailistchannels`, `!airemove`

### Payment
- `/pp` - Generate PromptPay QR code
- Prefix: `!pp`

### Productivity
- `/todo [add|view|clear]` - Manage todo list
- `/note` - Manage notes
- `/reminder` - Set reminders
- `/qtt` - Convert QWERTY to Thai text
- `!qwerty_to_thai` - Prefix version

### Game Profiles
- `/gpp roblox <username>` - Get Roblox profile
- `/gpp minecraft <username>` - Get Minecraft profile

### Admin
- `!restart` - Restart the bot (admin/owner only)

## Project Structure

```
Discordbot/
├── main.py              # Bot entry point
├── cogs/                # Command modules
│   ├── admin.py         # Admin commands
│   ├── ai.py            # AI chat functionality
│   ├── general.py       # Basic commands (ping, help)
│   ├── gameprofilepuller.py  # Game profile lookup
│   ├── owner.py         # Owner controls
│   ├── payment.py       # PromptPay QR generation
│   ├── say.py           # Say command
│   ├── utility.py       # Utility commands
│   └── work.py          # Todo, notes, reminders
├── utils/               # Utility modules
│   ├── advanced_logger.py
│   ├── discord_logger.py
│   ├── helpers.py
│   └── log_buffer.py
├── config/              # Configuration files
├── logs/                # Log files
└── data/                # User data storage
```

## Hosting

### Local
```bash
python main.py
```

### Render/Replit
The bot includes `keep_alive.py` for web hosting. Set `KEEP_ALIVE=true` in environment variables.

### Docker
```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "main.py"]
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DISCORD_TOKEN` | Discord bot token | Yes |
| `BOT_OWNER_ID` | Bot owner's Discord ID | Yes |
| `BOT_PREFIX` | Command prefix (default: q) | No |
| `BOT_GLOBAL_PREFIX` | Alternative prefix | No |
| `GEMINI_API_KEY` | Google Gemini API key | For AI features |
| `LOG_CHANNEL_ID` | Discord channel for logs | No |
| `PROMPTPAY` | PromptPay number | For payment features |
| `PROMPTPAY_1` | Additional PromptPay | No |
| `KEEP_ALIVE` | Enable web server | No |

## License

MIT License
