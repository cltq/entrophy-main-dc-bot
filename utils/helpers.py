from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo

# โซนเวลาไทย
BANGKOK_TZ = ZoneInfo("Asia/Bangkok")


def get_uptime(launch_time: Optional[datetime]) -> str:
    """คำนวณระยะเวลาที่บอททำงานตั้งแต่เริ่มต้น"""
    if not launch_time:
        return "ไม่ทราบ"
    delta = datetime.now(timezone.utc) - launch_time
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}h {minutes}m {seconds}s"


def get_bangkok_time() -> datetime:
    """คืนค่าเวลาปัจจุบันในโซนไทย"""
    return datetime.now(BANGKOK_TZ)


def format_bangkok_time(dt: Optional[datetime] = None) -> str:
    """จัดรูปแบบเวลาไทยเป็นข้อความ"""
    if dt is None:
        dt = datetime.now(BANGKOK_TZ)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def format_timestamp(dt: datetime, style: str = "F") -> str:
    """จัดรูปแบบ timestamp แบบ Discord"""
    from discord import utils
    return utils.format_dt(dt, style=style)


def truncate_text(text: str, length: int = 1000) -> str:
    """ตัดข้อความให้สั้นลงถ้าเกินความยาวที่กำหนด"""
    if len(text) <= length:
        return text
    return text[: length - 3] + "..."


def mask_id(id_str: str, visible: int = 4) -> str:
    """ซ่อนรหัสบางส่วนเพื่อความปลอดภัย"""
    if len(id_str) <= visible:
        return "*" * len(id_str)
    return id_str[:visible] + "*" * (len(id_str) - visible)


def format_count(count: int) -> str:
    """จัดรูปแบบตัวเลขขนาดใหญ่ให้อ่านง่าย (K, M)"""
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    if count >= 1_000:
        return f"{count / 1_000:.1f}K"
    return str(count)
