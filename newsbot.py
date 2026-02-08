import os
import sqlite3
import logging
import feedparser
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# =========================
# CONFIG
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN")
RSS_URL = "https://www.automotiveworld.com/feed/"

CHECK_INTERVAL = 600  # 10 minutes

CATEGORIES = [
    "OEMs",
    "Markets",
    "Commercial Vehicle",
    "Autonomous Driving",
    "E-Mobility",
    "Manufacturing",
    "Software-Defined Vehicle",
]

# =========================
# LOGGING (MINIMAL CLEAN)
# =========================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# =========================
# DATABASE
# =========================

def init_db():
    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_categories (
            chat_id INTEGER,
            category TEXT,
            PRIMARY KEY(chat_id, category)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sent_articles (
            link TEXT PRIMARY KEY
        )
    """)

    conn.commit()
    conn.close()

# =========================
# CATEGORY MENU
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (chat_id) VALUES (?)", (chat_id,))
    conn.commit()
    conn.close()

    await send_category_menu(update)

async def send_category_menu(update: Update):
    keyboard = []

    for cat in CATEGORIES:
        keyboard.append([
            InlineKeyboardButton(cat, callback_data=f"cat_{cat}")
        ])

    keyboard.append([
        InlineKeyboardButton("✅ Done", callback_data="done")
    ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Select categories (you can choose multiple):",
        reply_markup=reply_markup,
    )

# =========================
# CATEGORY HANDLER
# =========================

async def category_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat.id
    data = query.data

    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()

    if data.startswith("cat_"):
        category = data.replace("cat_", "")

        cursor.execute("""
            INSERT OR IGNORE INTO user_categories (chat_id, category)
            VALUES (?, ?)
        """, (chat_id, category))

        conn.commit()
        await query.edit_message_text(f"✅ Added {category}")

    elif data == "done":
        await query.edit_message_text("🎉 Your categories are saved!")

    conn.close()

# =========================
# NEWS CHECKER
# =========================

async def check_news(context: ContextTypes.DEFAULT_TYPE):
    logger.info("Checking for new news...")

    feed = feedparser.parse(RSS_URL)

    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()

    for entry in feed.entries:
        link = entry.link
        title = entry.title
        summary = entry.summary

        cursor.execute("SELECT link FROM sent_articles WHERE link=?", (link,))
        if cursor.fetchone():
            continue

        cursor.execute("SELECT chat_id FROM users")
        users = cursor.fetchall()

        for (chat_id,) in users:
            cursor.execute("""
                SELECT category FROM user_categories
                WHERE chat_id=?
            """, (chat_id,))
            user_categories = [row[0] for row in cursor.fetchall()]

            if any(cat.lower() in summary.lower() for cat in user_categories):
                try:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"📰 {title}\n\n{link}"
                    )
                except Exception:
                    logger.warning(f"Failed sending to {chat_id}")

        cursor.execute("INSERT OR IGNORE INTO sent_articles (link) VALUES (?)", (link,))
        conn.commit()

    conn.close()

# =========================
# MAIN
# =========================

def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN not set")

    init_db()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(category_handler))

    app.job_queue.run_repeating(check_news, interval=CHECK_INTERVAL, first=10)

    logger.info("Bot started successfully!")
    app.run_polling()

if __name__ == "__main__":
    main()
