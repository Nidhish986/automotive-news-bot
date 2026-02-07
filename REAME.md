# Automotive News Telegram Bot

A 24/7 cloud-hosted Telegram bot that fetches the latest news from Automotive World RSS feed and automatically sends updates to subscribed users.

---

## Features

-  Multi-user support (anyone can subscribe using /start)
-  Restart-proof (uses SQLite for persistence)
-  No duplicate news (even after redeploy)
-  Fully async (no coroutine warnings)
-  Secure environment variables
-  Deployed on Railway (cloud hosted)

---

## Tech Stack

- Python 3
- python-telegram-bot v20.7
- feedparser
- SQLite (persistent storage)
- Railway (deployment)
- GitHub (version control)

---

## How It Works

1. Users press `/start` to subscribe.
2. Bot stores their `chat_id` in SQLite database.
3. Every 10 minutes:
   - RSS feed is checked
   - New articles are identified
   - Only unseen articles are sent
4. Sent article links are stored in database to prevent duplicates.

---

## Database

The bot uses a local SQLite database:

- `users` table → stores subscribed chat IDs
- `sent_links` table → stores previously sent article links

This makes the bot restart-proof and prevents duplicate messages.

---

## Environment Variables

Set these in Railway:

## Deployment

- Hosted on Railway
- Auto-deploys on every `git push`
- Runs independently of local machine

---

## Future Improvements

- AI-generated article summaries
- Category filtering (EV, Market, OEM)
- External cloud database (PostgreSQL)
- Admin controls
- Daily digest mode

---

## Learning Goals

This project demonstrates:

- Cloud deployment
- Async programming
- Multi-user bot design
- Persistent storage with SQLite
- CI/CD workflow using GitHub
