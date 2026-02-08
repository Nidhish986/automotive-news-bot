import os
import sqlite3
import logging
import feedparser
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ================= CONFIG =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHECK_INTERVAL = 600

RSS_SOURCES = {
    "Automotive World": {
        "url": "https://www.automotiveworld.com/feed/",
        "categories": [
            "OEMs",
            "Markets",
            "Commercial Vehicle",
            "Autonomous",
            "E-Mobility",
            "Manufacturing",
            "Software"
        ]
    },
    "Car and Driver": {
        "url": "https://www.caranddriver.com/rss/news.xml",
        "categories": [
            "News",
            "Reviews",
            "EV",
            "SUV",
            "Performance",
            "Industry"
        ]
    },
    "MotorTrend": {
        "url": "https://www.motortrend.com/feeds/rss/",
        "categories": [
            "Reviews",
            "Electric",
            "Trucks",
            "Performance",
            "Concept",
            "Motorsports"
        ]
    },
    "Autocar": {
        "url": "https://www.autocar.co.uk/rss",
        "categories": [
            "Reviews",
            "EV",
            "Business",
            "Launch",
            "Technology",
            "Future"
        ]
    }
}

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
        CREATE TABLE IF NOT EXISTS user_sources (
            chat_id INTEGER,
            source TEXT,
            PRIMARY KEY(chat_id, source)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_categories (
            chat_id INTEGER,
            source TEXT,
            category TEXT,
            PRIMARY KEY(chat_id, source, category)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sent_articles (
            link TEXT PRIMARY KEY
        )
    """)

    conn.commit()
    conn.close()

# ================= TEMP STATE =================

temp_sources = {}
temp_categories = {}
current_config_source = {}

# ================= KEYBOARDS =================

def source_keyboard(chat_id):
    selected = temp_sources.get(chat_id, set())
    keyboard = []

    for source in RSS_SOURCES:
        prefix = "✅ " if source in selected else ""
        keyboard.append([
            InlineKeyboardButton(
                f"{prefix}{source}",
                callback_data=f"toggle_source|{source}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton("⚙ Configure Categories",
                             callback_data="configure_categories")
    ])

    keyboard.append([
        InlineKeyboardButton("💾 Save Preferences",
                             callback_data="save_all")
    ])

    return InlineKeyboardMarkup(keyboard)

def category_keyboard(chat_id, source):
    selected = temp_categories.setdefault(chat_id, {}).setdefault(source, set())
    keyboard = []

    for cat in RSS_SOURCES[source]["categories"]:
        prefix = "✅ " if cat in selected else ""
        keyboard.append([
            InlineKeyboardButton(
                f"{prefix}{cat}",
                callback_data=f"toggle_cat|{source}|{cat}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton("🔘 Select All",
                             callback_data=f"select_all|{source}"),
        InlineKeyboardButton("🗑 Clear All",
                             callback_data=f"clear_all|{source}")
    ])

    keyboard.append([
        InlineKeyboardButton("⬅ Back",
                             callback_data="back_to_sources")
    ])

    return InlineKeyboardMarkup(keyboard)

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users VALUES (?)", (chat_id,))
    conn.commit()
    conn.close()

    temp_sources[chat_id] = set()
    temp_categories[chat_id] = {}
    current_config_source[chat_id] = None

    await update.message.reply_text(
        "Step 1️⃣ Select News Sources:",
        reply_markup=source_keyboard(chat_id)
    )

# ================= SETTINGS =================

async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()

    cursor.execute("SELECT source FROM user_sources WHERE chat_id=?", (chat_id,))
    sources = {row[0] for row in cursor.fetchall()}

    cursor.execute("""
        SELECT source, category FROM user_categories
        WHERE chat_id=?
    """, (chat_id,))
    rows = cursor.fetchall()

    categories = {}
    for source, cat in rows:
        categories.setdefault(source, set()).add(cat)

    conn.close()

    temp_sources[chat_id] = sources
    temp_categories[chat_id] = categories

    await update.message.reply_text(
        "Modify your preferences:",
        reply_markup=source_keyboard(chat_id)
    )

# ================= HANDLER =================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    data = query.data

    if data.startswith("toggle_source"):
        _, source = data.split("|")
        selected = temp_sources.setdefault(chat_id, set())

        if source in selected:
            selected.remove(source)
        else:
            selected.add(source)

        await query.edit_message_reply_markup(
            reply_markup=source_keyboard(chat_id)
        )

    elif data == "configure_categories":
        if not temp_sources.get(chat_id):
            await query.answer("Select at least one source.", show_alert=True)
            return

        # Open first source for configuration
        source = list(temp_sources[chat_id])[0]
        current_config_source[chat_id] = source

        selected = temp_categories.setdefault(chat_id, {}).get(source, set())
        selected_display = ", ".join(selected) if selected else "None"

        await query.edit_message_text(
            f"Configuring: {source}\n\n"
            f"Currently Selected: {selected_display}",
            reply_markup=category_keyboard(chat_id, source)
        )

    elif data.startswith("toggle_cat"):
        _, source, cat = data.split("|")
        selected = temp_categories.setdefault(chat_id, {}).setdefault(source, set())

        if cat in selected:
            selected.remove(cat)
        else:
            selected.add(cat)

        selected_display = ", ".join(selected) if selected else "None"

        await query.edit_message_text(
            f"Configuring: {source}\n\n"
            f"Currently Selected: {selected_display}",
            reply_markup=category_keyboard(chat_id, source)
        )

    elif data.startswith("select_all"):
        _, source = data.split("|")
        temp_categories.setdefault(chat_id, {})[source] = \
            set(RSS_SOURCES[source]["categories"])

        selected_display = ", ".join(temp_categories[chat_id][source])

        await query.edit_message_text(
            f"Configuring: {source}\n\n"
            f"Currently Selected: {selected_display}",
            reply_markup=category_keyboard(chat_id, source)
        )

    elif data.startswith("clear_all"):
        _, source = data.split("|")
        temp_categories.setdefault(chat_id, {})[source] = set()

        await query.edit_message_text(
            f"Configuring: {source}\n\nCurrently Selected: None",
            reply_markup=category_keyboard(chat_id, source)
        )

    elif data == "back_to_sources":
        await query.edit_message_text(
            "Step 1️⃣ Select News Sources:",
            reply_markup=source_keyboard(chat_id)
        )

    elif data == "save_all":
        conn = sqlite3.connect("bot.db")
        cursor = conn.cursor()

        cursor.execute("DELETE FROM user_sources WHERE chat_id=?", (chat_id,))
        cursor.execute("DELETE FROM user_categories WHERE chat_id=?", (chat_id,))

        for source in temp_sources.get(chat_id, []):
            cursor.execute("INSERT INTO user_sources VALUES (?, ?)",
                           (chat_id, source))

            for cat in temp_categories.get(chat_id, {}).get(source, []):
                cursor.execute(
                    "INSERT INTO user_categories VALUES (?, ?, ?)",
                    (chat_id, source, cat)
                )

        conn.commit()
        conn.close()

        await query.edit_message_text("🎉 Preferences saved successfully!")

# ================= NEWS CHECKER =================

async def check_news(context: ContextTypes.DEFAULT_TYPE):
    logger.info("Checking news...")

    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()

    cursor.execute("SELECT chat_id FROM users")
    users = cursor.fetchall()

    for (chat_id,) in users:
        cursor.execute("SELECT source FROM user_sources WHERE chat_id=?",
                       (chat_id,))
        sources = [row[0] for row in cursor.fetchall()]

        for source in sources:
            feed = feedparser.parse(RSS_SOURCES[source]["url"])

            cursor.execute("""
                SELECT category FROM user_categories
                WHERE chat_id=? AND source=?
            """, (chat_id, source))
            categories = [row[0] for row in cursor.fetchall()]

            for entry in feed.entries:
                link = entry.link
                title = entry.title
                summary = entry.get("summary", "")

                cursor.execute("SELECT link FROM sent_articles WHERE link=?",
                               (link,))
                if cursor.fetchone():
                    continue

                if any(cat.lower() in title.lower() or
                       cat.lower() in summary.lower()
                       for cat in categories):

                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"📰 {title}\nSource: {source}\n\n{link}"
                    )

                    cursor.execute("INSERT OR IGNORE INTO sent_articles VALUES (?)",
                                   (link,))
                    conn.commit()

    conn.close()

# ================= MAIN =================

def main():
    init_db()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("settings", settings))
    app.add_handler(CallbackQueryHandler(button_handler))

    app.job_queue.run_repeating(check_news,
                                interval=CHECK_INTERVAL,
                                first=10)

    logger.info("Bot started.")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
