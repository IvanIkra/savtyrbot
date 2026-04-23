"""
Run once to get a TG_SESSION string for YouTube downloads.
You'll need api_id and api_hash from https://my.telegram.org
"""
import asyncio
from pyrogram import Client


async def main():
    print("Получаем session string для YouTube через Telegram-бота\n")
    api_id = int(input("api_id (с my.telegram.org): "))
    api_hash = input("api_hash: ").strip()

    async with Client("setup_temp", api_id=api_id, api_hash=api_hash) as app:
        session = await app.export_session_string()

    print("\n✅ Скопируй это в .env:")
    print(f"TG_API_ID={api_id}")
    print(f"TG_API_HASH={api_hash}")
    print(f"TG_SESSION={session}")


asyncio.run(main())
