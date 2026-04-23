import asyncio
import logging
import os
import tempfile

from pyrogram import Client, filters
from pyrogram.types import Message

log = logging.getLogger(__name__)

HELPER_BOT = os.getenv("YOUTUBE_HELPER_BOT", "SaveVideoBot")
_MAX_FILE_MB = 50

_client: Client | None = None
_lock: asyncio.Lock | None = None
_pending: asyncio.Future | None = None


async def start():
    global _client, _lock

    if not all([os.getenv("TG_API_ID"), os.getenv("TG_API_HASH"), os.getenv("TG_SESSION")]):
        log.info("YouTube via bot disabled: TG_API_ID/TG_API_HASH/TG_SESSION not set")
        return

    _lock = asyncio.Lock()

    _client = Client(
        name="savex_user",
        api_id=int(os.getenv("TG_API_ID")),
        api_hash=os.getenv("TG_API_HASH"),
        session_string=os.getenv("TG_SESSION"),
    )

    @_client.on_message(filters.chat(HELPER_BOT))
    async def _on_response(_, message: Message):
        global _pending
        if _pending and not _pending.done():
            has_buttons = bool(
                message.reply_markup
                and getattr(message.reply_markup, "inline_keyboard", None)
            )
            if message.video or message.document or has_buttons:
                _pending.set_result(message)

    await _client.start()
    log.info("YouTube user client started (@%s)", HELPER_BOT)


async def stop():
    if _client:
        try:
            await _client.stop()
        except Exception:
            pass


def is_available() -> bool:
    return _client is not None and _client.is_connected


async def download(url: str) -> tuple[str | None, str, str | None]:
    """Returns (file_path, title, error). error is None on success."""
    if not is_available():
        return None, "", "YouTube не поддерживается (настрой TG_SESSION в .env)."

    global _pending

    async with _lock:
        loop = asyncio.get_running_loop()
        _pending = loop.create_future()

        try:
            await _client.send_message(HELPER_BOT, url)

            msg: Message = await asyncio.wait_for(asyncio.shield(_pending), timeout=30)

            # Bot sent quality selection buttons — click the first one
            if not msg.video and not msg.document:
                keyboard = getattr(msg.reply_markup, "inline_keyboard", None)
                if not keyboard or not keyboard[0]:
                    return None, "", "Бот не вернул видео."
                _pending = loop.create_future()
                await msg.click(0)
                msg = await asyncio.wait_for(asyncio.shield(_pending), timeout=90)

            if not msg.video and not msg.document:
                return None, "", "Бот не вернул видео."

            title = (msg.caption or "").strip()
            if not title and msg.video:
                title = (msg.video.file_name or "").replace(".mp4", "").strip()

            tmp_dir = tempfile.mkdtemp()
            file_path = await _client.download_media(
                msg.video or msg.document,
                file_name=os.path.join(tmp_dir, "video.mp4"),
            )

            size_mb = os.path.getsize(file_path) / (1024 * 1024)
            if size_mb > _MAX_FILE_MB:
                os.remove(file_path)
                os.rmdir(tmp_dir)
                return None, "", f"Видео слишком большое ({size_mb:.0f} МБ)."

            return file_path, title, None

        except asyncio.TimeoutError:
            return None, "", "YouTube: бот-загрузчик не ответил вовремя."
        except Exception as e:
            log.error("YouTube via bot error: %s", e)
            return None, "", f"Ошибка YouTube: {e}"
        finally:
            _pending = None
