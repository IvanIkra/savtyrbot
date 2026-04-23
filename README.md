# SavXBot

Telegram bot for downloading videos without ads from TikTok, Instagram, and YouTube.

## Features

- **Direct chat** — send a link, get the video
- **Inline mode** — `@bot link` in any chat, video is sent with `via @bot` attribution
- Metadata: author, likes, views
- "🔗 Original" button under every video
- Localization: 🇷🇺 Russian, 🇬🇧 English (auto-detected from Telegram language)
- YouTube videos are cached and served instantly on repeated requests

## Supported Platforms

| Platform | Direct chat | Inline |
|----------|-------------|--------|
| TikTok | ✅ | ✅ |
| Instagram Reels / posts | ✅ | ✅ |
| YouTube / Shorts | ✅ | ✅ (cached) |

## Deploy to Railway

1. Fork this repository
2. Create a project on [Railway](https://railway.app) → **Deploy from GitHub**
3. Add environment variables:

| Variable | Description |
|----------|-------------|
| `BOT_TOKEN` | Bot token from [@BotFather](https://t.me/BotFather) |
| `CACHE_CHAT_ID` | ID of a channel/group for video caching (bot must be admin) |
| `TG_API_ID` | API ID from [my.telegram.org](https://my.telegram.org) (for YouTube) |
| `TG_API_HASH` | API Hash from [my.telegram.org](https://my.telegram.org) (for YouTube) |
| `TG_SESSION` | Session string (generated via `setup_tg_session.py`) |
| `YOUTUBE_HELPER_BOT` | Username of a YouTube downloader bot (without @) |

## Local Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in the variables
python bot.py
```

### YouTube Setup (optional)

```bash
python setup_tg_session.py
```

Enter your `TG_API_ID` and `TG_API_HASH`, complete authorization — you'll get a `TG_SESSION` string for `.env`.

## License

[PolyForm Strict 1.0.0](LICENSE) — personal use only.
