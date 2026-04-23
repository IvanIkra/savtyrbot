import asyncio
import os
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import yt_dlp

MAX_FILE_MB = 50

SUPPORTED_DOMAINS = (
    "tiktok.com",
    "instagram.com",
    "youtube.com",
    "youtu.be",
)

_VIDEO_EXTS = {".mp4", ".mkv", ".webm", ".mov", ".avi", ".m4v"}
_dl_sem = asyncio.Semaphore(3)


@dataclass
class VideoMeta:
    title: str
    author: str = ""
    likes: int | None = None
    views: int | None = None

    def caption(self) -> str:
        parts = []
        if self.author:
            parts.append(f"👤 @{self.author}")
        if self.likes is not None:
            parts.append(f"❤️ {_fmt_num(self.likes)}")
        if self.views is not None:
            parts.append(f"👁 {_fmt_num(self.views)}")
        return "  ·  ".join(parts)

    def inline_description(self) -> str:
        parts = []
        if self.author:
            parts.append(f"@{self.author}")
        if self.likes is not None:
            parts.append(f"❤️ {_fmt_num(self.likes)}")
        if self.views is not None:
            parts.append(f"👁 {_fmt_num(self.views)}")
        return "  ·  ".join(parts) if parts else self.title


def _fmt_num(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}K"
    return str(n)


def is_supported_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        return parsed.scheme in ("http", "https") and any(
            host == d or host.endswith("." + d) for d in SUPPORTED_DOMAINS
        )
    except Exception:
        return False


def _is_youtube(url: str) -> bool:
    try:
        host = urlparse(url).hostname or ""
        return host in ("youtube.com", "youtu.be") or host.endswith(".youtube.com")
    except Exception:
        return False


# ── TikTok / Instagram via yt-dlp ────────────────────────────────────────────

def _ydl_opts(output_template: str) -> dict:
    return {
        "outtmpl": output_template,
        "format": "best[ext=mp4]/best",
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        },
    }


def _download_ytdlp(url: str, out_dir: str) -> tuple[str | None, VideoMeta | str]:
    uid = uuid.uuid4().hex
    output_template = os.path.join(out_dir, f"{uid}.%(ext)s")
    try:
        with yt_dlp.YoutubeDL(_ydl_opts(output_template)) as ydl:
            info = ydl.extract_info(url, download=True)
            author = (
                info.get("uploader") or info.get("creator") or info.get("channel") or ""
            ).lstrip("@")
            meta = VideoMeta(
                title=info.get("title") or info.get("description", "")[:80] or "Видео",
                author=author,
                likes=info.get("like_count"),
                views=info.get("view_count"),
            )

            all_files = list(Path(out_dir).glob(f"{uid}.*"))
            if not all_files:
                return None, "Файл не найден после скачивания."
            video_files = [f for f in all_files if f.suffix.lower() in _VIDEO_EXTS]
            file_path = str((video_files or all_files)[0])

            size_mb = os.path.getsize(file_path) / (1024 * 1024)
            if size_mb > MAX_FILE_MB:
                os.remove(file_path)
                return None, f"Видео слишком большое ({size_mb:.0f} МБ)."
            return file_path, meta
    except yt_dlp.utils.DownloadError as e:
        msg = str(e)
        if "Private" in msg or "login" in msg.lower():
            return None, "Это приватное видео — скачать нельзя."
        return None, "Не удалось скачать видео. Проверьте ссылку."
    except Exception as e:
        return None, f"Ошибка: {e}"


# ── YouTube via Telegram bot ──────────────────────────────────────────────────

async def _download_youtube(url: str) -> tuple[str | None, VideoMeta | str]:
    import youtube_via_bot
    file_path, title, error = await youtube_via_bot.download(url)
    if error:
        return None, error
    return file_path, VideoMeta(title=title or "YouTube")


# ── Public API ────────────────────────────────────────────────────────────────

async def download_video(url: str) -> tuple[str | None, VideoMeta | str]:
    if _is_youtube(url):
        return await _download_youtube(url)

    tmp_dir = tempfile.mkdtemp()

    try:
        async with _dl_sem:
            file_path, result = await asyncio.wait_for(
                asyncio.get_running_loop().run_in_executor(
                    None, lambda: _download_ytdlp(url, tmp_dir)
                ),
                timeout=90,
            )
    except asyncio.TimeoutError:
        file_path, result = None, "Слишком долго скачивается, попробуй позже."

    if file_path is None:
        try:
            os.rmdir(tmp_dir)
        except OSError:
            pass

    return file_path, result
