import feedparser
import os
import time
from telegram import Bot

RSS_URL = "https://www.automotiveworld.com/feed/"
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

bot = Bot(token=BOT_TOKEN)

SENT_FILE = "sent_articles.txt"

if not os.path.exists(SENT_FILE):
    open(SENT_FILE, "w").close()

print("Bot started...")

while True:
    try:
        with open(SENT_FILE, "r") as f:
            sent_links = f.read().splitlines()

        feed = feedparser.parse(RSS_URL)

        for entry in feed.entries:
            if entry.link not in sent_links:
                message = f"📰 {entry.title}\n\n{entry.summary}\n\nRead more: {entry.link}"
                bot.send_message(chat_id=CHAT_ID, text=message)

                with open(SENT_FILE, "a") as f:
                    f.write(entry.link + "\n")

        print("Checked RSS. Sleeping 10 minutes...")
        time.sleep(600)

    except Exception as e:
        print("Error:", e)
        time.sleep(60)
