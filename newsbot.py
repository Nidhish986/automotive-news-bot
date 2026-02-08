import os
import sqlite3
import logging
import feedparser
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ================= CONFIG =================

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

# ================= LOGGING =================

logging.basicConfig(level=logging.INFO, format="%(message)s")
logging.getLogger("telegram").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# ================= DATABASE =================

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

# ================= TEMP MEMORY =================

user_selections = {}

# ================= KEYBOARD BUILDER =================

def build_keyboard(chat_id):
    selected = user_selections.get(chat_id, set())
    keyboard = []

    for cat in CATEGORIES:
        prefix = "✅ " if cat in selected else ""
        keyboard.append([
            InlineKeyboardButton(f"{prefix}{cat}", callback_data=f"toggle_{cat}")
        ])

    keyboard.append([
        InlineKeyboardButton("🔘 Select All", callback_data="select_all"),
        InlineKeyboardButton("🗑 Clear All", callback_data="clear_all"),
    ])

    keyboard.append([
        InlineKeyboardButton("💾 Done", callback_data="done")
    ])

    return InlineKeyboardMarkup(keyboard)

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (chat_id) VALUES (?)", (chat_id,))
    conn.commit()
    conn.close()

    user_selections[chat_id] = set()

    await update.message.reply_text(
        "Select your categories:",
        reply_markup=build_keyboard(chat_id)
    )

# ================= SETTINGS =================

async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT category FROM user_categories WHERE chat_id=?",
        (chat_id,)
    )
    categories = [row[0] for row in cursor.fetchall()]
    conn.close()

    user_selections[chat_id] = set(categories)

    await update.message.reply_text(
        "Modify your categories:",
        reply_markup=build_keyboard(chat_id)
    )

# ================= BUTTON HANDLER =================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat.id
    data = query.data

    selected = user_selections.setdefault(chat_id, set())

    if data.startswith("toggle_"):
        category = data.replace("toggle_", "")

        if category in selected:
            selected.remove(category)
        else:
            selected.add(category)

        await query.edit_message_reply_markup(
            reply_markup=build_keyboard(chat_id)
        )

    elif data == "select_all":
        selected.update(CATEGORIES)
        await query.edit_message_reply_markup(
            reply_markup=build_keyboard(chat_id)
        )

    elif data == "clear_all":
        selected.clear()
        await query.edit_message_reply_markup(
            reply_markup=build_keyboard(chat_id)
        )

    elif data == "done":
        conn = sqlite3.connect("bot.db")
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM user_categories WHERE chat_id=?",
            (chat_id,)
        )

        for cat in selected:
            cursor.execute(
                "INSERT INTO user_categories (chat_id, category) VALUES (?, ?)",
                (chat_id, cat)
            )

        conn.commit()
        conn.close()

        await query.edit_message_text(
            "🎉 Categories saved successfully!\n\nUse /settings to modify anytime."
        )

# ================= NEWS CHECKER =================

async def check_news(context: ContextTypes.DEFAULT_TYPE):
    logger.info("Checking news...")

    feed = feedparser.parse(RSS_URL)

    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()

    for entry in feed.entries:
        link = entry.link
        title = entry.title
        summary = entry.summary

        cursor.execute(
            "SELECT link FROM sent_articles WHERE link=?",
            (link,)
        )
        if cursor.fetchone():
            continue

        cursor.execute("SELECT chat_id FROM users")
        users = cursor.fetchall()

        for (chat_id,) in users:
            cursor.execute(
                "SELECT category FROM user_categories WHERE chat_id=?",
                (chat_id,)
            )
            categories = [row[0] for row in cursor.fetchall()]

            if any(cat.lower() in summary.lower() for cat in categories):
                try:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"📰 {title}\n\n{link}"
                    )
                except:
                    logger.warning(f"Failed sending to {chat_id}")

        cursor.execute(
            "INSERT OR IGNORE INTO sent_articles (link) VALUES (?)",
            (link,)
        )
        conn.commit()

    conn.close()

# ================= MAIN =================

def main():
    init_db()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("settings", settings))
    app.add_handler(CallbackQueryHandler(button_handler))

    app.job_queue.run_repeating(
        check_news,
        interval=CHECK_INTERVAL,
        first=10
    )

    logger.info("Bot started.")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
