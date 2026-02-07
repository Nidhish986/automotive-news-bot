import feedparser
import os
import asyncio
import sqlite3
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

RSS_URL = "https://www.automotiveworld.com/feed/"
BOT_TOKEN = os.getenv("BOT_TOKEN")

# ---------------- DATABASE ----------------
conn = sqlite3.connect("bot_data.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    chat_id INTEGER PRIMARY KEY
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS sent_links (
    link TEXT PRIMARY KEY
)
""")

conn.commit()

# ---------------- START COMMAND ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    cursor.execute("INSERT OR IGNORE INTO users (chat_id) VALUES (?)", (chat_id,))
    conn.commit()
    await update.message.reply_text("✅ You are subscribed to Automotive News!")

# ---------------- NEWS CHECK ----------------
async def check_news(context: ContextTypes.DEFAULT_TYPE):
    feed = feedparser.parse(RSS_URL)

    for entry in feed.entries:
        link = entry.link

        cursor.execute("SELECT 1 FROM sent_links WHERE link = ?", (link,))
        if cursor.fetchone():
            continue

        message = f"📰 {entry.title}\n\n{link}"

        cursor.execute("SELECT chat_id FROM users")
        users = cursor.fetchall()

        for (chat_id,) in users:
            await context.bot.send_message(chat_id=chat_id, text=message)

        cursor.execute("INSERT INTO sent_links (link) VALUES (?)", (link,))
        conn.commit()

# ---------------- MAIN ----------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    # Run news check every 10 minutes using job queue
    app.job_queue.run_repeating(check_news, interval=600, first=10)

    app.run_polling()

if __name__ == "__main__":
    main()
