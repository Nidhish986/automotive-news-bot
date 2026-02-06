import feedparser
import os
import time
import asyncio
from telegram import Bot

# ===== CONFIG =====
RSS_URL = "https://www.automotiveworld.com/feed/"
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

# ===== TELEGRAM BOT =====
bot = Bot(token=BOT_TOKEN)

# ===== MEMORY STORAGE (prevents duplicates while running) =====
sent_links = set()

print("Bot started...")

async def check_news():
    global sent_links

    feed = feedparser.parse(RSS_URL)

    for entry in feed.entries:
        if entry.link not in sent_links:
            message = f"📰 {entry.title}\n\n{entry.link}"
            
            await bot.send_message(
                chat_id=CHAT_ID,
                text=message
            )

            sent_links.add(entry.link)

async def main():
    while True:
        try:
            await check_news()
            print("Checked RSS. Sleeping 10 minutes...")
            await asyncio.sleep(600)  # 10 minutes

        except Exception as e:
            print("Error:", e)
            await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
