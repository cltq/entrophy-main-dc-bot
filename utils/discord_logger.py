import logging
import asyncio

class DiscordHandler(logging.Handler):
    """แฮนเดิลบันทึกแบบอะซิงก์ที่ส่งข้อความบันทึกไปยังช่อง Discord

    วิธีใช้: แนบไปกับ logger หลังจากสร้างบอท:
        handler = DiscordHandler(bot, channel_id)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    แฮนเดิลนี้จะเก็บข้อความใน asyncio.Queue และงานพื้นหลังจะส่งเมื่อบอทพร้อม
    ข้อความถูกส่งเป็นบล็อกรหัสเพื่อรักษารูปแบบ ข้อผิดพลาดจะถูกข้ามเพื่อไม่ให้บอทล่ม
    """

    def __init__(self, bot, channel_id, level=logging.NOTSET):
        super().__init__(level)
        self.bot = bot
        self.channel_id = int(channel_id)
        self.queue = asyncio.Queue()
        self._task = None
        self._lock = asyncio.Lock()
        self._last_message = None
        self._buffer = ""
        # กำหนดฟอร์แมตเตอร์เริ่มต้นถ้ายังไม่มี
        if not self.formatter:
            fmt = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')
            self.setFormatter(fmt)

    async def start(self):
        """เริ่มงานส่งข้อความพื้นหลังจากบริบทอะซิงก์"""
        if self._task is None:
            self._task = asyncio.create_task(self._sender())

    async def _ensure_channel(self):
        """ตรวจสอบและคืนค่าช่อง Discord ให้พร้อมใช้งาน"""
        ch = self.bot.get_channel(self.channel_id)
        if ch is None:
            try:
                ch = await self.bot.fetch_channel(self.channel_id)
            except Exception:
                ch = None
        return ch

    async def _sender(self):
        """รอให้บอทพร้อมแล้วส่งข้อความที่ค้างอยู่"""
        try:
            await self.bot.wait_until_ready()
        except Exception:
            pass

        channel = await self._ensure_channel()
        while True:
            try:
                msg = await self.queue.get()
            except asyncio.CancelledError:
                break

            try:
                if channel is None:
                    channel = await self._ensure_channel()

                # ต่อข้อความใหม่เข้ากับบัฟเฟอร์และจำกัดขนาด
                async with self._lock:
                    if self._buffer:
                        self._buffer += "\n"
                    self._buffer += msg

                    # เก็บประมาณ 1800 ตัวอักษรสุดท้ายให้พอดีกับบล็อกรหัสและขีดจำกัด Discord
                    if len(self._buffer) > 1800:
                        self._buffer = self._buffer[-1800:]

                    body = f"```\n{self._buffer}\n```"

                if channel is not None:
                    try:
                        if self._last_message is None:
                            self._last_message = await channel.send(body)
                        else:
                            try:
                                await self._last_message.edit(content=body)
                            except Exception:
                                # ข้อความอาจถูกลบหรือแก้ไขโดยผู้อื่น ส่งใหม่
                                self._last_message = await channel.send(body)
                    except Exception:
                        # ข้ามข้อผิดพลาดเพื่อให้ logger ทำงานต่อได้
                        pass
                    finally:
                        try:
                            self.queue.task_done()
                        except Exception:
                            pass
            except Exception:
                # ข้ามข้อผิดพลาดที่ไม่คาดคิดในลูปส่งข้อความ
                pass

    def emit(self, record: logging.LogRecord) -> None:
        """ส่งข้อความบันทึกเข้าคิว"""
        try:
            base = self.format(record)
            extra = self._format_record_extra(record)
            if extra:
                msg = f"{base}\n{extra}"
            else:
                msg = base
            # ใส่ข้อความเข้าคิวอย่างปลอดภัยในเธรด
            loop = None
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # ไม่มีลูปวิ่งในเธรดนี้ ลองใช้ bot.loop
                loop = getattr(self.bot, 'loop', None)

            if loop is None or (hasattr(loop, 'is_closed') and loop.is_closed()):
                # ไม่สามารถเข้าคิวได้ ปล่อยอย่างเงียบ ๆ
                return

            try:
                if getattr(loop, 'is_running', lambda: False)():
                    loop.call_soon_threadsafe(self.queue.put_nowait, msg)
                else:
                    asyncio.run_coroutine_threadsafe(self.queue.put(msg), loop)
            except Exception:
                pass
        except Exception:
            pass

    def _format_record_extra(self, record: logging.LogRecord) -> str:
        """จัดรูปแบบข้อมูลบริบทเพิ่มเติมจาก record"""
        parts = []
        user = getattr(record, 'user', None) or getattr(record, 'author', None)
        if user is not None:
            try:
                if hasattr(user, 'name') and hasattr(user, 'discriminator'):
                    parts.append(f"ผู้ใช้: {getattr(user, 'name')}#{getattr(user, 'discriminator')} ({getattr(user, 'id', '?')})")
                elif hasattr(user, 'display_name'):
                    parts.append(f"ผู้ใช้: {getattr(user, 'display_name')} ({getattr(user, 'id', '?')})")
                else:
                    parts.append(f"ผู้ใช้: {str(user)}")
            except Exception:
                parts.append(f"ผู้ใช้: {str(user)}")

        cmd = getattr(record, 'command', None) or getattr(record, 'cmd', None)
        if cmd is not None:
            try:
                parts.append(f"คำสั่ง: {str(cmd)}")
            except Exception:
                parts.append(f"คำสั่ง: {repr(cmd)}")

        interaction = getattr(record, 'interaction', None)
        if interaction is not None:
            try:
                parts.append(f"โต้ตอบ: {getattr(interaction, 'type', repr(interaction))} โดย {getattr(interaction, 'user', getattr(interaction, 'author', 'ไม่ทราบ'))}")
            except Exception:
                parts.append(f"โต้ตอบ: {repr(interaction)}")

        channel = getattr(record, 'channel', None)
        if channel is not None:
            try:
                parts.append(f"ช่อง: {getattr(channel, 'name', str(channel))} ({getattr(channel, 'id', '?')})")
            except Exception:
                parts.append(f"ช่อง: {str(channel)}")

        guild = getattr(record, 'guild', None)
        if guild is not None:
            try:
                parts.append(f"เซิร์ฟเวอร์: {getattr(guild, 'name', str(guild))} ({getattr(guild, 'id', '?')})")
            except Exception:
                parts.append(f"เซิร์ฟเวอร์: {str(guild)}")

        try:
            import datetime
            parts.append(f"เวลา: {datetime.datetime.utcnow().isoformat()}Z")
        except Exception:
            pass

        return "\n".join(parts)

    def close(self) -> None:
        """ปิดแฮนเดิลและยกเลิกงานพื้นหลัง"""
        try:
            if self._task and not self._task.cancelled():
                self._task.cancel()
        except Exception:
            pass
        super().close()
