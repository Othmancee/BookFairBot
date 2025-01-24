# Bookfair Bot

A Telegram bot for managing and navigating book fairs. This bot helps users find publishers, halls, and books at book fairs.

## Features

- Search for publishers and halls
- View hall maps and locations
- Save favorite publishers
- Get analytics on searches and interactions

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables in `.env`:
```
BOT_TOKEN=your_telegram_bot_token
```

3. Run the bot:
```bash
python lambda_function.py
```

## Commands

- `/start` - Start the bot and get welcome message
- `/help` - Show available commands
- `/search` - Search for publishers or halls

## Development

The bot is built using:
- python-telegram-bot
- fuzzywuzzy for search
- JSON for data storage

## Deployment

The bot can be deployed to:
- Railway.app (recommended)
- Heroku
- AWS Lambda
- DigitalOcean App Platform 