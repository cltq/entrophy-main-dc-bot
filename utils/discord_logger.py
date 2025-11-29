import logging
import asyncio

class DiscordHandler(logging.Handler):
    """Async logging handler that forwards log records to a Discord channel.

    Usage: attach to a logger after the bot is created:
        handler = DiscordHandler(bot, channel_id)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    The handler buffers messages in an asyncio.Queue and a background task
    sends them once the bot is ready. Messages are sent as codeblocks to
    preserve formatting. Failures are silently ignored to avoid crashing.
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
        # Ensure a reasonable default formatter if not provided later
        if not self.formatter:
            fmt = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')
            self.setFormatter(fmt)

    async def start(self):
        """Start the background sender task from an async context."""
        if self._task is None:
            self._task = asyncio.create_task(self._sender())

    async def _ensure_channel(self):
        ch = self.bot.get_channel(self.channel_id)
        if ch is None:
            try:
                ch = await self.bot.fetch_channel(self.channel_id)
            except Exception:
                ch = None
        return ch

    async def _sender(self):
        # wait for bot ready then send queued messages
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

                # Append the new message to the buffer and keep buffer within limits
                async with self._lock:
                    if self._buffer:
                        self._buffer += "\n"
                    self._buffer += msg

                    # Keep last ~1800 characters to fit inside a codeblock and Discord limits
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
                                # Message may have been deleted or edited by others; send a new one
                                self._last_message = await channel.send(body)
                    except Exception:
                        # ignore exceptions to keep logger robust
                        pass
                    finally:
                        try:
                            self.queue.task_done()
                        except Exception:
                            pass
            except Exception:
                # ignore unexpected errors in the sender loop to keep it running
                pass

    def emit(self, record: logging.LogRecord) -> None:
        try:
            # format the record (includes exc_info if present)
            base = self.format(record)
            # append contextual info when available on the record
            extra = self._format_record_extra(record)
            if extra:
                msg = f"{base}\n{extra}"
            else:
                msg = base
            # Put message into the queue in a thread-safe way
            loop = None
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # No running loop in this thread; try to get the bot.loop
                loop = getattr(self.bot, 'loop', None)

            if loop is None or (hasattr(loop, 'is_closed') and loop.is_closed()):
                # Can't enqueue safely; drop silently to avoid blocking
                return

            try:
                if getattr(loop, 'is_running', lambda: False)():
                    loop.call_soon_threadsafe(self.queue.put_nowait, msg)
                else:
                    asyncio.run_coroutine_threadsafe(self.queue.put(msg), loop)
            except Exception:
                # If we cannot enqueue, avoid raising from logging
                pass
        except Exception:
            # don't propagate logging errors
            pass

    def _format_record_extra(self, record: logging.LogRecord) -> str:
        parts = []
        # Common possible attributes
        user = getattr(record, 'user', None) or getattr(record, 'author', None)
        if user is not None:
            try:
                # discord objects have 'name' and 'discriminator' or 'display_name'
                if hasattr(user, 'name') and hasattr(user, 'discriminator'):
                    parts.append(f"User: {getattr(user, 'name')}#{getattr(user, 'discriminator')} ({getattr(user, 'id', '?')})")
                elif hasattr(user, 'display_name'):
                    parts.append(f"User: {getattr(user, 'display_name')} ({getattr(user, 'id', '?')})")
                else:
                    parts.append(f"User: {str(user)}")
            except Exception:
                parts.append(f"User: {str(user)}")

        # Command / interaction
        cmd = getattr(record, 'command', None) or getattr(record, 'cmd', None)
        if cmd is not None:
            try:
                parts.append(f"Command: {str(cmd)}")
            except Exception:
                parts.append(f"Command: {repr(cmd)}")

        interaction = getattr(record, 'interaction', None)
        if interaction is not None:
            try:
                parts.append(f"Interaction: {getattr(interaction, 'type', repr(interaction))} by {getattr(interaction, 'user', getattr(interaction, 'author', 'unknown'))}")
            except Exception:
                parts.append(f"Interaction: {repr(interaction)}")

        channel = getattr(record, 'channel', None)
        if channel is not None:
            try:
                parts.append(f"Channel: {getattr(channel, 'name', str(channel))} ({getattr(channel, 'id', '?')})")
            except Exception:
                parts.append(f"Channel: {str(channel)}")

        guild = getattr(record, 'guild', None)
        if guild is not None:
            try:
                parts.append(f"Guild: {getattr(guild, 'name', str(guild))} ({getattr(guild, 'id', '?')})")
            except Exception:
                parts.append(f"Guild: {str(guild)}")

        # ensure a timestamp is present (format uses asctime but include ISO for clarity)
        try:
            import datetime
            parts.append(f"Time: {datetime.datetime.utcnow().isoformat()}Z")
        except Exception:
            pass

        return "\n".join(parts)

    def close(self) -> None:
        try:
            if self._task and not self._task.cancelled():
                self._task.cancel()
        except Exception:
            pass
        super().close()
