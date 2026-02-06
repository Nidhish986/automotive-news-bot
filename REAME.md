# Automotive News Telegram Bot

A cloud-hosted Telegram bot that automatically fetches the latest news from Automotive World RSS feed and sends updates to Telegram every 10 minutes.

## Features

- Fetches latest automotive news
- Sends updates directly to Telegram
- Prevents duplicate messages (while running)
- Deployed on Railway (24/7 cloud hosting)
- Uses environment variables for secure configuration

## Tech Stack

- Python 3
- python-telegram-bot (v20.7)
- feedparser
- Railway (deployment)
- GitHub (version control)

## How It Works

1. Reads RSS feed from:
   https://www.automotiveworld.com/feed/
2. Checks for new articles
3. Sends only new articles to Telegram
4. Sleeps for 10 minutes
5. Repeats continuously

## Environment Variables

The following must be configured in Railway:

BOT_TOKEN = your_telegram_bot_token  
CHAT_ID = your_chat_id  

⚠ Do not hardcode secrets in the source code.

## Deployment

- Hosted using Railway
- Auto-deploys on every Git push
- Runs independently of local machine

## Future Improvements

- AI-based article summarization
- Category filtering (EV, Market, OEM)
- Database storage for permanent duplicate tracking
- Multi-source aggregation
