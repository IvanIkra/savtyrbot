# SavXBot

Telegram-бот для скачивания видео без рекламы с TikTok, Instagram и YouTube.

## Возможности

- **Личный чат** — отправь ссылку, получи видео
- **Инлайн-режим** — `@bot ссылка` в любом чате, видео отправляется с подписью `via @bot`
- Метаданные: автор, лайки, просмотры
- Кнопка «🔗 Оригинал» под каждым видео
- Локализация: 🇷🇺 русский, 🇬🇧 английский (автоматически по языку Telegram)
- YouTube кешируется и отдаётся мгновенно при повторных запросах

## Поддерживаемые платформы

| Платформа | Личный чат | Инлайн |
|-----------|-----------|--------|
| TikTok | ✅ | ✅ |
| Instagram Reels / посты | ✅ | ✅ |
| YouTube / Shorts | ✅ | ✅ (кеш) |

## Деплой на Railway

1. Форкни репозиторий
2. Создай проект на [Railway](https://railway.app) → **Deploy from GitHub**
3. Добавь переменные окружения:

| Переменная | Описание |
|------------|----------|
| `BOT_TOKEN` | Токен бота от [@BotFather](https://t.me/BotFather) |
| `CACHE_CHAT_ID` | ID канала/группы для кеширования видео (бот должен быть админом) |
| `TG_API_ID` | API ID с [my.telegram.org](https://my.telegram.org) (для YouTube) |
| `TG_API_HASH` | API Hash с [my.telegram.org](https://my.telegram.org) (для YouTube) |
| `TG_SESSION` | Session string (генерируется через `setup_tg_session.py`) |
| `YOUTUBE_HELPER_BOT` | Username бота-загрузчика YouTube (без @) |

## Локальный запуск

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # заполни переменные
python bot.py
```

### Настройка YouTube (опционально)

```bash
python setup_tg_session.py
```

Введи `TG_API_ID` и `TG_API_HASH`, пройди авторизацию — получишь `TG_SESSION` для `.env`.

## Лицензия

[PolyForm Strict 1.0.0](LICENSE) — только личное использование.
