# Cairo Book Fair Bot 📚

A Telegram bot for the Cairo International Book Fair, helping visitors navigate publishers, halls, and events.

## Features 🌟

- 🔍 Search publishers by name or booth code
- 🗺 Interactive hall maps with section navigation
- ⭐️ Bookmark favorite publishers
- 📅 View events and special offers
- 📍 Find adjacent publishers
- 📊 Analytics tracking with GA4

## Project Structure 📁

```
bookfairbot/
├── bot.py              # Main bot logic
├── analytics.py        # GA4 tracking
├── halls/             # Hall data
│   ├── hall_manager.py
│   └── hall*.json     # Hall data files
├── assets/            # Media assets
│   └── image.png      # Bot logo
├── requirements.txt   # Dependencies
└── README.md         # Documentation
```

## Setup 🛠

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure environment variables in `.env`:
   ```
   BOT_TOKEN=your_telegram_bot_token
   GA4_MEASUREMENT_ID=your_ga4_measurement_id
   GA4_API_SECRET=your_ga4_api_secret
   RAILWAY_ENVIRONMENT=production
   ```

3. Run the bot:
   ```bash
   python bot.py
   ```

## Deployment on Railway 🚂

1. Connect your GitHub repository to Railway
2. Add the environment variables in Railway's dashboard
3. Deploy using the Railway CLI:
   ```bash
   railway up
   ```

## Analytics 📊

The bot uses Google Analytics 4 for tracking:
- User searches and results
- Navigation patterns
- Feature usage
- Performance metrics
- Error tracking

View analytics in the GA4 dashboard under property: Cairo Book Fair Bot

## Maintenance 🔧

- Update hall data in `halls/hall*.json`
- Monitor GA4 dashboard for usage patterns
- Check error logs in Railway dashboard
- Update event information as needed

## Support 💬

For issues or questions:
- Open an issue on GitHub
- Contact: support@asfar.io
- Visit: https://asfar.io/

## License 📄

Copyright (c) 2024 Asfar.io. All rights reserved. 