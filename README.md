# Cairo Book Fair Bot 📚

A Telegram bot for the Cairo International Book Fair 2025, designed to help visitors navigate the fair, find publishers, and track their favorite exhibitors.

## Features 🌟

- **Publisher Search** 🔍
  - Search by name (Arabic/English)
  - Search by booth code
  - Search by hall number

- **Interactive Maps** 🗺
  - View hall layouts
  - Locate publishers
  - Navigate between sections

- **Favorites System** ⭐️
  - Save favorite publishers
  - Quick access to saved exhibitors
  - Personalized experience

- **Analytics & Monitoring** 📊
  - User interaction tracking
  - Performance metrics
  - Usage statistics

## Technical Stack 🛠

- Python 3.11
- python-telegram-bot
- Analytics system
- Deployment on Railway

## Setup & Installation 🚀

1. Clone the repository:
```bash
git clone https://github.com/Othmancee/BookFairBot.git
cd BookFairBot
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file with:
```
BOT_TOKEN=your_telegram_bot_token
TZ=Africa/Cairo
```

5. Run the bot:
```bash
python deploy.py
```

## Project Structure 📁

```
BookFairBot/
├── bot.py              # Main bot logic
├── deploy.py           # Deployment script
├── halls/              # Publishers data
│   ├── __init__.py
│   ├── hall_manager.py
│   └── hall*.json      # Hall data files
├── analytics.py        # Analytics system
├── favorites.py        # Favorites management
├── maps.py            # Map generation
└── requirements.txt    # Dependencies
```

## Deployment 🌐

The bot is configured for deployment on Railway:

1. Connect your GitHub repository to Railway
2. Set the required environment variables
3. Railway will automatically deploy using the Procfile

## Contributing 🤝

Contributions are welcome! Please feel free to submit a Pull Request.

## License 📄

This project is licensed under the MIT License - see the LICENSE file for details.

## Contact 📧

For any queries or support, please contact [Your Contact Information] 