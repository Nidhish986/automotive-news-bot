# Automotive News Telegram Bot

A production-ready cloud Telegram bot that delivers filtered Automotive World RSS news to users based on their selected categories.

---

## Features

- Multi-user support  
- Multiple category selection  
- Inline button UI  
- SQLite database (restart-safe)  
- No duplicate news  
- Railway deployment ready  
- CI/CD via GitHub  
- Secure environment variables  
- Async architecture (python-telegram-bot v20)

---

## Architecture

User → Telegram → Bot (Railway)  
Bot → Fetch RSS Feed → Filter by user categories  
Bot → Store sent links in SQLite  
Bot → Send relevant news  

---

## Project Structure

.
├── newsbot.py
├── requirements.txt
├── README.md
└── .gitignore
