"""ระบบบันทึกขั้นสูงพร้อมระดับการบันทึกและการจัดรูปแบบที่แตกต่างกัน"""
import logging
from datetime import datetime
from typing import Any, Optional


class LogLevel:
    """ระดับการบันทึกแบบกำหนดเอง"""
    VERBOSE: int = 5
    DEBUG: int = 10
    INFO: int = 20
    WARNING: int = 30
    ERROR: int = 40
    CRITICAL: int = 50


logging.addLevelName(LogLevel.VERBOSE, "VERBOSE")


class ContextLogger(logging.Logger):
    """Logger ที่รองรับระดับ VERBOSE"""

    def verbose(self, message: str, *args: Any, **kwargs: Any) -> None:
        """บันทึกข้อความระดับ VERBOSE"""
        if self.isEnabledFor(LogLevel.VERBOSE):
            self._log(LogLevel.VERBOSE, message, args, **kwargs)


logging.setLoggerClass(ContextLogger)


class AdvancedFormatter(logging.Formatter):
    """จัดรูปแบบบันทึกพร้อมสีสันและอิโมจิ"""
    COLORS: dict[int, str] = {
        LogLevel.VERBOSE: "\033[36m",
        LogLevel.DEBUG: "\033[34m",
        LogLevel.INFO: "\033[32m",
        LogLevel.WARNING: "\033[33m",
        LogLevel.ERROR: "\033[31m",
        LogLevel.CRITICAL: "\033[41m",
    }
    RESET: str = "\033[0m"

    EMOJIS: dict[int, str] = {
        LogLevel.VERBOSE: "🔍",
        LogLevel.DEBUG: "🐛",
        LogLevel.INFO: "ℹ️ ",
        LogLevel.WARNING: "⚠️ ",
        LogLevel.ERROR: "❌",
        LogLevel.CRITICAL: "🔴",
    }

    def format(self, record: logging.LogRecord) -> str:
        """จัดรูปแบบบันทึกพร้อมบริบท"""
        emoji = self.EMOJIS.get(record.levelno, "•")
        level = record.levelname
        msg = f"{emoji} [{level}] {record.getMessage()}"
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")

        context_parts: list[str] = []

        user = getattr(record, "user", None)
        if user:
            context_parts.append(f"ผู้ใช้: {user}")

        command = getattr(record, "command", None)
        if command:
            context_parts.append(f"คำสั่ง: {command}")

        channel = getattr(record, "channel", None)
        if channel:
            context_parts.append(f"ช่อง: {channel}")

        guild = getattr(record, "guild", None)
        if guild:
            context_parts.append(f"เซิร์ฟเวอร์: {guild}")

        formatted = f"[{timestamp}] {msg}"
        if context_parts:
            formatted += " | " + " | ".join(context_parts)

        return formatted


def setup_advanced_logger(name: str = "entrophy", level: int = LogLevel.VERBOSE) -> logging.Logger:
    """ตั้งค่าและคืนค่า logger หลักของระบบ"""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.handlers = []

    console_handler = logging.StreamHandler()
    console_handler.setLevel(LogLevel.VERBOSE)
    formatter = AdvancedFormatter()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


def log_command_execution(
    logger: Any,
    interaction_type: str,
    command_name: str,
    user: Any,
    guild: Any,
    channel: Any,
    args: str = "",
    success: bool = True,
) -> None:
    """บันทึกการเรียกใช้คำสั่ง"""
    status = "✅ สำเร็จ" if success else "❌ ล้มเหลว"
    if interaction_type == "slash":
        log_msg = f"คำสั่ง Slash ถูกเรียกใช้: /{command_name}"
    else:
        log_msg = f"คำสั่ง Prefix ถูกเรียกใช้: {command_name}"

    if args:
        log_msg += f" [อาร์กิวเมนต์: {args}]"
    log_msg += f" [{status}]"

    extra = {"user": user, "command": command_name, "channel": channel, "guild": guild}
    logger.info(log_msg, extra=extra)


def log_error(
    logger: Any,
    error_type: str,
    error_msg: str,
    user: Any = None,
    command: Any = None,
    channel: Any = None,
    guild: Any = None,
    exc_info: bool = False,
) -> None:
    """บันทึกข้อผิดพลาด"""
    extra: dict[str, Any] = {"user": user, "command": command, "channel": channel, "guild": guild}

    if exc_info:
        logger.exception(f"ข้อผิดพลาด [{error_type}]: {error_msg}", extra=extra)
    else:
        logger.error(f"ข้อผิดพลาด [{error_type}]: {error_msg}", extra=extra)


def log_user_action(
    logger: Any,
    action: str,
    user: Any,
    guild: Any = None,
    channel: Any = None,
    details: str = "",
) -> None:
    """บันทึกการกระทำของผู้ใช้"""
    msg = f"การกระทำผู้ใช้ [{action}]"
    if details:
        msg += f": {details}"

    extra = {"user": user, "channel": channel, "guild": guild}
    logger.info(msg, extra=extra)


def log_event(
    logger: Any,
    event_name: str,
    details: str = "",
    user: Any = None,
    guild: Any = None,
    channel: Any = None,
) -> None:
    """บันทึกเหตุการณ์"""
    msg = f"เหตุการณ์: {event_name}"
    if details:
        msg += f" - {details}"

    extra = {"user": user, "channel": channel, "guild": guild}
    logger.info(msg, extra=extra)
