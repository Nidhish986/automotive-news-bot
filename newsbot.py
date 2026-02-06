import feedparser
from telegram import Bot
import os

RSS_URL = "https://www.automotiveworld.com/feed/"
BOT_TOKEN = os.environ.get("8226886589:AAExiXPah_A6jRWBluSjB-KhIT6ZEbrBUhM")
CHAT_ID = os.environ.get("6465154955")

bot = Bot(token=BOT_TOKEN)

SENT_FILE = "sent_articles.txt"

if not os.path.exists(SENT_FILE):
    open(SENT_FILE, "w").close()

with open(SENT_FILE, "r") as f:
    sent_links = f.read().splitlines()

feed = feedparser.parse(RSS_URL)

for entry in feed.entries:
    if entry.link not in sent_links:
        message = f"📰 {entry.title}\n\n{entry.summary}\n\nRead more: {entry.link}"
        bot.send_message(chat_id=CHAT_ID, text=message)

        with open(SENT_FILE, "a") as f:
            f.write(entry.link + "\n")
