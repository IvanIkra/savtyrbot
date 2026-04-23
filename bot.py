import asyncio
import json
import logging
import os
import uuid
from dataclasses import asdict

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    FSInputFile,
    InlineQuery,
    InlineQueryResultCachedVideo,
    InlineQueryResultArticle,
    InputTextMessageContent,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from dotenv import load_dotenv

load_dotenv()

from downloader import download_video, is_supported_url, _is_youtube, VideoMeta
from strings import t
import youtube_via_bot

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не задан в .env")

CACHE_CHAT_ID = int(os.getenv("CACHE_CHAT_ID", "0"))
if not CACHE_CHAT_ID:
    raise RuntimeError("CACHE_CHAT_ID не задан в .env")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

BOT_USERNAME = ""

# ── YouTube cache ─────────────────────────────────────────────────────────────

CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "yt_cache.json")

# url → {"file_id": str, "message_id": int, "meta": dict}
_yt_cache: dict[str, dict] = {}
_yt_pending: set[str] = set()
_cleanup_task: asyncio.Task | None = None


def _load_cache():
    global _yt_cache
    try:
        with open(CACHE_FILE) as f:
            _yt_cache = json.load(f)
        log.info("Loaded %d YouTube cache entries", len(_yt_cache))
    except (FileNotFoundError, json.JSONDecodeError):
        _yt_cache = {}


def _save_cache():
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(_yt_cache, f)
    except OSError as e:
        log.error("Failed to save YouTube cache: %s", e)


async def _upload_to_cache(url: str, file_path: str, meta: VideoMeta) -> str:
    """Upload to cache channel, persist entry, return file_id."""
    msg = await bot.send_video(chat_id=CACHE_CHAT_ID, video=FSInputFile(file_path))
    _yt_cache[url] = {
        "file_id": msg.video.file_id,
        "message_id": msg.message_id,
        "meta": asdict(meta),
    }
    _save_cache()
    log.info("YouTube cached: %s", url)
    return msg.video.file_id


async def _finish_and_cache(url: str, task: asyncio.Task):
    """Await an in-flight download task and cache the result."""
    try:
        file_path, result = await task
    except Exception as e:
        log.warning("YouTube bg download failed: %s", e)
        _yt_pending.discard(url)
        return

    if file_path:
        try:
            await _upload_to_cache(url, file_path, result)
        except Exception as e:
            log.error("YouTube bg cache upload failed: %s", e)
        finally:
            _cleanup(file_path)

    _yt_pending.discard(url)


async def _yt_cache_cleanup_loop():
    while True:
        await asyncio.sleep(3600)
        log.info("Clearing YouTube cache (%d entries)", len(_yt_cache))
        for entry in list(_yt_cache.values()):
            try:
                await bot.delete_message(CACHE_CHAT_ID, entry["message_id"])
            except Exception:
                pass
        _yt_cache.clear()
        _save_cache()
        log.info("YouTube cache cleared")


# ── helpers ───────────────────────────────────────────────────────────────────

def _lang(user) -> str | None:
    code = getattr(user, "language_code", None)
    if not code:
        return None
    return code.split("-")[0].split("_")[0]


def _cleanup(file_path: str):
    try:
        os.remove(file_path)
        os.rmdir(os.path.dirname(file_path))
    except OSError:
        pass


def _make_markup(url: str, lang: str | None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t("orig_button", lang), url=url)
    ]])


async def _download(url: str) -> tuple[str, VideoMeta] | tuple[None, str]:
    log.info("Downloading: %s", url)
    file_path, result = await download_video(url)
    if not file_path:
        log.warning("Download failed: %s", result)
    return file_path, result


# ── Commands ──────────────────────────────────────────────────────────────────

@dp.message(CommandStart())
@dp.message(Command("help"))
async def cmd_start(message: Message):
    lang = _lang(message.from_user)
    await message.answer(t("start", lang, username=BOT_USERNAME), parse_mode="HTML")


# ── Inline mode ───────────────────────────────────────────────────────────────

@dp.inline_query()
async def inline_handler(query: InlineQuery):
    url = query.query.strip()
    lang = _lang(query.from_user)

    if not url:
        await query.answer(
            results=[InlineQueryResultArticle(
                id="help",
                title=t("inline_hint_title", lang),
                description=t("inline_hint_desc", lang),
                input_message_content=InputTextMessageContent(
                    message_text=t("inline_hint_text", lang, username=BOT_USERNAME)
                ),
            )],
            cache_time=5,
        )
        return

    if not is_supported_url(url):
        await query.answer(results=[], cache_time=10)
        return

    if _is_youtube(url):
        # Cached → instant response
        cached = _yt_cache.get(url)
        if cached:
            meta = VideoMeta(**cached["meta"])
            await query.answer(
                results=[InlineQueryResultCachedVideo(
                    id=uuid.uuid4().hex,
                    video_file_id=cached["file_id"],
                    title=meta.title[:100],
                    description=meta.inline_description(),
                    caption=meta.caption(),
                    parse_mode="HTML",
                    reply_markup=_make_markup(url, lang),
                )],
                cache_time=3600,
            )
            return

        # Already downloading in background → ask to retry
        if url in _yt_pending:
            await query.answer(
                results=[InlineQueryResultArticle(
                    id="yt_loading",
                    title=t("yt_loading_title", lang),
                    description=t("yt_loading_desc", lang),
                    input_message_content=InputTextMessageContent(
                        message_text=t("yt_loading_text", lang)
                    ),
                )],
                cache_time=5,
            )
            return

        # Try to finish within 8s before Telegram's 10s inline timeout
        task = asyncio.create_task(_download(url))
        _yt_pending.add(url)

        try:
            file_path, result = await asyncio.wait_for(asyncio.shield(task), timeout=8)
        except asyncio.TimeoutError:
            # Hand off the running task to background; don't start a new download
            asyncio.create_task(_finish_and_cache(url, task))
            await query.answer(
                results=[InlineQueryResultArticle(
                    id="yt_loading",
                    title=t("yt_loading_title", lang),
                    description=t("yt_loading_desc", lang),
                    input_message_content=InputTextMessageContent(
                        message_text=t("yt_loading_text", lang)
                    ),
                )],
                cache_time=5,
            )
            return

        _yt_pending.discard(url)

        if not file_path:
            log.warning("YouTube inline download error: %s", result)
            await query.answer(results=[], cache_time=5)
            return

        meta: VideoMeta = result
        try:
            file_id = await _upload_to_cache(url, file_path, meta)
            await query.answer(
                results=[InlineQueryResultCachedVideo(
                    id=uuid.uuid4().hex,
                    video_file_id=file_id,
                    title=meta.title[:100],
                    description=meta.inline_description(),
                    caption=meta.caption(),
                    parse_mode="HTML",
                    reply_markup=_make_markup(url, lang),
                )],
                cache_time=3600,
            )
        except Exception as e:
            log.error("YouTube inline upload failed: %s", e)
            await query.answer(results=[], cache_time=5)
        finally:
            _cleanup(file_path)
        return

    file_path, result = await _download(url)
    if not file_path:
        log.warning("Inline download error (hidden): %s", result)
        error_text = t("download_error", lang)
        await query.answer(
            results=[InlineQueryResultArticle(
                id="error",
                title=t("inline_error_title", lang),
                description=error_text,
                input_message_content=InputTextMessageContent(message_text=error_text),
            )],
            cache_time=5,
        )
        return

    meta: VideoMeta = result
    try:
        msg = await bot.send_video(chat_id=CACHE_CHAT_ID, video=FSInputFile(file_path))
        file_id = msg.video.file_id
        await bot.delete_message(chat_id=CACHE_CHAT_ID, message_id=msg.message_id)
        await query.answer(
            results=[InlineQueryResultCachedVideo(
                id=uuid.uuid4().hex,
                video_file_id=file_id,
                title=meta.title[:100],
                description=meta.inline_description(),
                caption=meta.caption(),
                parse_mode="HTML",
                reply_markup=_make_markup(url, lang),
            )],
            cache_time=300,
        )
    except Exception as e:
        log.error("Inline upload failed: %s", e)
        await query.answer(results=[], cache_time=5)
    finally:
        _cleanup(file_path)


# ── Direct message mode ───────────────────────────────────────────────────────

@dp.message(F.text)
async def handle_link(message: Message):
    url = message.text.strip()
    lang = _lang(message.from_user)

    if not is_supported_url(url):
        await message.answer(t("send_link", lang))
        return

    status = await message.answer(t("downloading", lang))
    file_path, result = await _download(url)

    if not file_path:
        log.warning("Download error (hidden): %s", result)
        await status.edit_text(t("download_error", lang))
        return

    meta: VideoMeta = result
    try:
        await status.edit_text(t("sending", lang))
        await message.answer_video(
            video=FSInputFile(file_path),
            caption=meta.caption(),
            parse_mode="HTML",
            reply_markup=_make_markup(url, lang),
        )
    except Exception as e:
        log.error("Send error: %s", e)
        await status.edit_text(t("send_error", lang))
    else:
        await status.delete()
    finally:
        _cleanup(file_path)


async def main():
    global BOT_USERNAME, _cleanup_task
    _load_cache()
    me = await bot.get_me()
    BOT_USERNAME = me.username
    log.info("Bot started: @%s", BOT_USERNAME)
    await youtube_via_bot.start()
    _cleanup_task = asyncio.create_task(_yt_cache_cleanup_loop())
    try:
        await dp.start_polling(bot)
    finally:
        await youtube_via_bot.stop()


if __name__ == "__main__":
    asyncio.run(main())
