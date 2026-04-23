STRINGS: dict[str, dict[str, str]] = {
    "ru": {
        "start": (
            "👋 Привет! Я скачиваю видео без рекламы.\n\n"
            "📌 Как использовать:\n"
            "• В <b>личном чате</b> — просто пришли ссылку\n"
            "• В <b>любом чате</b> — напиши <code>@{username} ссылка</code>\n\n"
            "Поддерживаемые платформы:\n"
            "• TikTok\n"
            "• Instagram (Reels, посты)\n"
            "• YouTube / Shorts\n"
        ),
        "send_link": "Пришли ссылку на видео с TikTok, Instagram или YouTube.",
        "downloading": "⏳ Скачиваю...",
        "sending": "📤 Отправляю...",
        "download_error": "❌ Не удалось скачать видео.",
        "send_error": "❌ Не удалось отправить видео.",
        "yt_loading_title": "⏳ Скачиваю YouTube...",
        "yt_loading_desc": "Попробуй снова через ~минуту",
        "yt_loading_text": "⏳ Видео скачивается, попробуй инлайн снова через минуту.",
        "inline_hint_title": "Пришли ссылку на видео",
        "inline_hint_desc": "TikTok, Instagram, YouTube",
        "inline_hint_text": "Используй бота: @{username} <ссылка>",
        "inline_error_title": "Ошибка",
        "orig_button": "🔗 Оригинал",
    },
    "en": {
        "start": (
            "👋 Hi! I download videos without ads.\n\n"
            "📌 How to use:\n"
            "• In a <b>private chat</b> — just send a link\n"
            "• In <b>any chat</b> — type <code>@{username} link</code>\n\n"
            "Supported platforms:\n"
            "• TikTok\n"
            "• Instagram (Reels, posts)\n"
            "• YouTube / Shorts\n"
        ),
        "send_link": "Send a TikTok, Instagram or YouTube video link.",
        "downloading": "⏳ Downloading...",
        "sending": "📤 Sending...",
        "download_error": "❌ Failed to download the video.",
        "send_error": "❌ Failed to send the video.",
        "yt_loading_title": "⏳ Downloading YouTube...",
        "yt_loading_desc": "Try again in ~a minute",
        "yt_loading_text": "⏳ Video is being downloaded, try inline again in a minute.",
        "inline_hint_title": "Send a video link",
        "inline_hint_desc": "TikTok, Instagram, YouTube",
        "inline_hint_text": "Use the bot: @{username} <link>",
        "inline_error_title": "Error",
        "orig_button": "🔗 Original",
    },
}

_FALLBACK = "ru"


def t(key: str, lang: str | None, **kwargs) -> str:
    strings = STRINGS.get(lang or _FALLBACK, STRINGS[_FALLBACK])
    text = strings.get(key, STRINGS[_FALLBACK][key])
    return text.format(**kwargs) if kwargs else text
