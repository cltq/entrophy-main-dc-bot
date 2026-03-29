from datetime import datetime, timezone
import pytz

BANGKOK_TZ = pytz.timezone("Asia/Bangkok")


def get_uptime(launch_time):
    if not launch_time:
        return "Unknown"
    delta = datetime.now(timezone.utc) - launch_time
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}h {minutes}m {seconds}s"


def get_bangkok_time():
    return datetime.now(BANGKOK_TZ)


def format_bangkok_time(dt=None):
    if dt is None:
        dt = datetime.now(BANGKOK_TZ)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def format_timestamp(dt, style="F"):
    from discord import utils
    return utils.format_dt(dt, style=style)


def truncate_text(text: str, length: int = 1000) -> str:
    if len(text) <= length:
        return text
    return text[: length - 3] + "..."


def mask_id(id_str: str, visible: int = 4) -> str:
    if len(id_str) <= visible:
        return "*" * len(id_str)
    return id_str[:visible] + "*" * (len(id_str) - visible)


def format_count(count: int) -> str:
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    if count >= 1_000:
        return f"{count / 1_000:.1f}K"
    return str(count)
