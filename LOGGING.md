# 📊 Advanced Logging System Documentation

## Overview
The bot now has a comprehensive logging system with multiple log levels, rich formatting, and context-aware logging.

## Log Levels
- **VERBOSE (5)**: Most detailed information - includes debug details about commands, state changes
- **DEBUG (10)**: Debugging information
- **INFO (20)**: General information - command executions, events, normal operations
- **WARNING (30)**: Warning messages - permission errors, deprecated features
- **ERROR (40)**: Error conditions
- **CRITICAL (50)**: Critical failures

## Log Formatting
Each log entry includes:
- **Emoji**: Visual indicator of the log type
- **Level**: Log severity (VERBOSE, INFO, WARNING, ERROR, etc.)
- **Timestamp**: When the event occurred
- **Message**: Main log message
- **Context**: Additional information when available:
  - User info (name, discriminator, ID)
  - Command being executed
  - Channel name and ID
  - Guild/Server name and ID

Example log output:
```
[2026-01-23 14:35:42] ⚡ [INFO] Slash command executed: /notecreate [Args: ] [✅ SUCCESS] | User: John#1234 (123456789) | Command: notecreate | Channel: #general (987654321) | Guild: My Server (123456789)
```

## Logging Components

### 1. Console Output
- Streams to terminal with ANSI color codes
- Shows all log levels from VERBOSE and above
- Real-time visibility of bot operations

### 2. File Handler
- Rotates logs when they exceed 2MB
- Keeps up to 5 backup files
- Located in `logs/entrophy.log`
- Preserves full formatting with color codes

### 3. Discord Handler
- Sends logs to a specified Discord channel
- Configured via `LOG_CHANNEL_ID` environment variable
- Updates messages to keep them concise
- Buffer management to stay within Discord message limits

### 4. Dashboard Buffer
- In-memory log buffer for the web dashboard
- Fast access to recent logs
- No disk I/O overhead

## Usage Examples

### Logging Command Execution
```python
from utils.advanced_logger import log_command_execution

log_command_execution(
    logger, 
    "slash",  # or "prefix"
    "notecreate",  # command name
    interaction.user,  # user
    interaction.guild,  # guild
    interaction.channel,  # channel
    "args here",  # optional arguments
    success=True  # whether command succeeded
)
```

### Logging Errors
```python
from utils.advanced_logger import log_error

log_error(
    logger,
    "PermissionError",  # error type
    "User tried to execute without permissions",  # message
    user=ctx.author,
    command=ctx.command.name,
    channel=ctx.channel,
    guild=ctx.guild,
    exc_info=True  # includes exception traceback
)
```

### Logging User Actions
```python
from utils.advanced_logger import log_user_action

log_user_action(
    logger,
    "note_created",  # action type
    user=interaction.user,
    guild=interaction.guild,
    channel=interaction.channel,
    details="Note with 3 attachments"  # optional details
)
```

### Logging Events
```python
from utils.advanced_logger import log_event

log_event(
    logger,
    "SlashCommandsSync",  # event name
    details="Synced 45 commands",
    user=None,  # optional
    guild=None,
    channel=None
)
```

### Verbose Logging
```python
logger.verbose("Detailed information about operation")  # Custom VERBOSE level
logger.debug("Debug information")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error message")
logger.critical("Critical error")
```

## Configuration

### Environment Variables
- `LOG_CHANNEL_ID`: Discord channel ID to send logs to (optional)
- `BOT_PREFIX`: Bot prefix for prefix commands (default: "q")

### Log Level
The default log level is `VERBOSE`, which captures all events. To change it:
```python
logger.setLevel(LogLevel.INFO)  # Only show INFO and above
```

## Current Logging Points

### Commands
- ✅ Prefix command execution (with args)
- ✅ Slash command execution
- ✅ Command completion tracking

### Events
- ✅ Bot ready/login
- ✅ Slash commands sync
- ✅ Cog loading

### Errors
- ✅ Command errors with context
- ✅ Permission errors
- ✅ Owner-only command violations
- ✅ Exception tracebacks

### Work Cog (Potential Additions)
- Todo list operations (add, complete, delete)
- Note creation with attachments
- Code validation success/failure
- Reminder creation

## Tips for Better Logging

1. **Always include context**: User, guild, channel when available
2. **Use appropriate log levels**: Don't log everything as INFO
3. **Include actionable information**: What action, by whom, where, when
4. **Use the helper functions**: They ensure consistent formatting
5. **For errors**: Always include exception traceback for debugging

## Future Improvements
- Database logging support
- Log filtering/search in dashboard
- Webhook notifications for critical errors
- Per-user/guild log filtering
