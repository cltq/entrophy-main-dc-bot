"""Advanced logging system with different log levels and formatting"""
import logging
import discord
from datetime import datetime


class LogLevel:
    """Custom log levels"""
    VERBOSE = 5
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


# Add VERBOSE level to logging module
logging.addLevelName(LogLevel.VERBOSE, "VERBOSE")


def log_verbose(logger, message, *args, **kwargs):
    """Log at VERBOSE level"""
    if logger.isEnabledFor(LogLevel.VERBOSE):
        logger._log(LogLevel.VERBOSE, message, args, **kwargs)


logging.Logger.verbose = log_verbose


class AdvancedFormatter(logging.Formatter):
    """Custom formatter with colors and better formatting"""
    
    # ANSI color codes
    COLORS = {
        LogLevel.VERBOSE: '\033[36m',      # Cyan
        LogLevel.DEBUG: '\033[34m',        # Blue
        LogLevel.INFO: '\033[32m',         # Green
        LogLevel.WARNING: '\033[33m',      # Yellow
        LogLevel.ERROR: '\033[31m',        # Red
        LogLevel.CRITICAL: '\033[41m',     # Red background
    }
    RESET = '\033[0m'
    
    EMOJIS = {
        LogLevel.VERBOSE: '🔍',
        LogLevel.DEBUG: '🐛',
        LogLevel.INFO: 'ℹ️ ',
        LogLevel.WARNING: '⚠️ ',
        LogLevel.ERROR: '❌',
        LogLevel.CRITICAL: '🔴',
    }
    
    def format(self, record):
        # Add emoji and level name
        emoji = self.EMOJIS.get(record.levelno, '•')
        level = record.levelname
        
        # Format message
        if record.exc_info:
            # For exceptions, include traceback
            msg = f"{emoji} [{level}] {record.getMessage()}"
        else:
            msg = f"{emoji} [{level}] {record.getMessage()}"
        
        # Add timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
        
        # Add context if available
        context_parts = []
        
        if hasattr(record, 'user') and record.user:
            try:
                if isinstance(record.user, discord.User):
                    context_parts.append(f"User: {record.user.name}#{record.user.discriminator} ({record.user.id})")
                else:
                    context_parts.append(f"User: {record.user}")
            except:
                context_parts.append(f"User: {record.user}")
        
        if hasattr(record, 'command') and record.command:
            context_parts.append(f"Command: {record.command}")
        
        if hasattr(record, 'channel') and record.channel:
            try:
                if isinstance(record.channel, discord.TextChannel):
                    context_parts.append(f"Channel: #{record.channel.name} ({record.channel.id})")
                else:
                    context_parts.append(f"Channel: {record.channel}")
            except:
                context_parts.append(f"Channel: {record.channel}")
        
        if hasattr(record, 'guild') and record.guild:
            try:
                if isinstance(record.guild, discord.Guild):
                    context_parts.append(f"Guild: {record.guild.name} ({record.guild.id})")
                else:
                    context_parts.append(f"Guild: {record.guild}")
            except:
                context_parts.append(f"Guild: {record.guild}")
        
        # Build final message
        formatted = f"[{timestamp}] {msg}"
        if context_parts:
            formatted += " | " + " | ".join(context_parts)
        
        return formatted


def setup_advanced_logger(name="entrophy", level=LogLevel.VERBOSE):
    """Set up and return an advanced logger"""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Clear existing handlers
    logger.handlers = []
    
    # Console handler with advanced formatter
    console_handler = logging.StreamHandler()
    console_handler.setLevel(LogLevel.VERBOSE)
    formatter = AdvancedFormatter()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger


# Log event types
def log_command_execution(logger, interaction_type, command_name, user, guild, channel, args="", success=True):
    """Log command execution"""
    status = "✅ SUCCESS" if success else "❌ FAILED"
    emoji = "⚡" if interaction_type == "slash" else "📝"
    
    if interaction_type == "slash":
        log_msg = f"Slash command executed: /{command_name}"
    else:
        log_msg = f"Prefix command executed: {command_name}"
    
    if args:
        log_msg += f" [Args: {args}]"
    
    log_msg += f" [{status}]"
    
    extra = {
        'user': user,
        'command': command_name,
        'channel': channel,
        'guild': guild,
    }
    
    logger.info(log_msg, extra=extra)


def log_error(logger, error_type, error_msg, user=None, command=None, channel=None, guild=None, exc_info=None):
    """Log errors with context"""
    extra = {
        'user': user,
        'command': command,
        'channel': channel,
        'guild': guild,
    }
    
    if exc_info:
        logger.exception(f"Error [{error_type}]: {error_msg}", extra=extra)
    else:
        logger.error(f"Error [{error_type}]: {error_msg}", extra=extra)


def log_user_action(logger, action, user, guild=None, channel=None, details=""):
    """Log user actions"""
    msg = f"User action [{action}]"
    if details:
        msg += f": {details}"
    
    extra = {
        'user': user,
        'channel': channel,
        'guild': guild,
    }
    
    logger.info(msg, extra=extra)


def log_event(logger, event_name, details="", user=None, guild=None, channel=None):
    """Log bot events"""
    msg = f"Event: {event_name}"
    if details:
        msg += f" - {details}"
    
    extra = {
        'user': user,
        'channel': channel,
        'guild': guild,
    }
    
    logger.info(msg, extra=extra)
