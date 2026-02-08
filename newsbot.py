import os
import sqlite3
import feedparser
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ------------------ CONFIG ------------------

BOT_TOKEN = os.environ.get("BOT_TOKEN")
RSS_URL = "https://www.automotiveworld.com/feed/"

CHECK_INTERVAL = 600  # 10 minutes

CATEGORIES = [
    "News",
    "Articles",
    "Magazine",
    "Data",
    "Newsletters",
    "Events",
    "OEMs",
    "Markets",
    "Commercial Vehicle",
    "Autonomous Driving",
    "E-Mobility",
    "Manufacturing",
    "Software-Defined Vehicle",
]

# ------------------ LOGGING ------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------ DATABASE ------------------

def init_db():
    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER,
            category TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sent_news (
            link TEXT PRIMARY KEY
        )
    """)

    conn.commit()
    conn.close()


# ------------------ START COMMAND ------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []

    for category in CATEGORIES:
        keyboard.append([
            InlineKeyboardButton(category, callback_data=f"toggle_{category}")
        ])

    keyboard.append([InlineKeyboardButton("✅ Done", callback_data="done")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Select categories you want to receive:",
        reply_markup=reply_markup
    )


# ------------------ BUTTON HANDLER ------------------

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id
    data = query.data

    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()

    if data.startswith("toggle_"):
        category = data.replace("toggle_", "")

        cursor.execute(
            "SELECT * FROM users WHERE chat_id=? AND category=?",
            (chat_id, category)
        )
        exists = cursor.fetchone()

        if exists:
            cursor.execute(
                "DELETE FROM users WHERE chat_id=? AND category=?",
                (chat_id, category)
            )
            await query.edit_message_text(f"❌ Removed {category}")
        else:
            cursor.execute(
                "INSERT INTO users (chat_id, category) VALUES (?, ?)",
                (chat_id, category)
            )
            await query.edit_message_text(f"✅ Added {category}")

    elif data == "done":
        await query.edit_message_text("🎉 Your categories are saved!")

    conn.commit()
    conn.close()


# ------------------ NEWS CHECKER ------------------

async def check_news(context: ContextTypes.DEFAULT_TYPE):
    logger.info("Checking for new news...")

    feed = feedparser.parse(RSS_URL)

    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()

    for entry in feed.entries:
        link = entry.link

        # Skip if already sent globally
        cursor.execute("SELECT * FROM sent_news WHERE link=?", (link,))
        if cursor.fetchone():
            continue

        title = entry.title
        summary = entry.summary

        # Get all unique users
        cursor.execute("SELECT DISTINCT chat_id FROM users")
        users = cursor.fetchall()

        for user in users:
            chat_id = user[0]

            cursor.execute(
                "SELECT category FROM users WHERE chat_id=?",
                (chat_id,)
            )
            categories = [row[0] for row in cursor.fetchall()]

            if any(cat.lower() in title.lower() or cat.lower() in summary.lower()
                   for cat in categories):

                message = f"📰 {title}\n\n{summary}\n\nRead more: {link}"

                try:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=message,
                        disable_web_page_preview=False
                    )
                except Exception as e:
                    logger.error(f"Error sending to {chat_id}: {e}")

        # Mark as sent
        cursor.execute("INSERT OR IGNORE INTO sent_news (link) VALUES (?)", (link,))
        conn.commit()

    conn.close()


# ------------------ MAIN ------------------

def main():
    init_db()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    # Schedule job
    app.job_queue.run_repeating(check_news, interval=CHECK_INTERVAL, first=10)

    logger.info("Bot started successfully!")
    app.run_polling()


if __name__ == "__main__":
    main()
