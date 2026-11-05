# Crypto Price Telegram Bot

A Telegram bot for tracking crypto prices, fiat exchange rates and a personal portfolio, with price alerts.
Built with Python and [python-telegram-bot](https://python-telegram-bot.org/).

> Not financial advice. The bot shows market data and sends notifications; it does not make decisions for you.

## Features

- **Prices** – any coin in USD, EUR and UAH with the 24h change (`/price btc`)
- **Top 10** coins by market cap in your chosen currency (`/top`)
- **Exchange rates** – USD, EUR, UAH, PLN (`/rate`)
- **Converter** – fiat and crypto, e.g. `/convert 100 usd eur` or `/convert 0.5 btc usd`
- **Portfolio** – add coins and see the total value (`/add`, `/remove`, `/portfolio`)
- **Price alerts** – get a message when a coin reaches your target price (`/alert btc 90000`)
- **Fear & Greed index** – current market sentiment (`/fear`)
- **Personal currency** – every user picks USD, EUR or UAH (`/currency`)
- Data (alerts, portfolios, settings) is saved to a local JSON file and survives restarts

## Commands

| Command | Description |
|---|---|
| `/start`, `/help` | Show the menu and all commands |
| `/price <coin>` | Price in $, € and ₴ + 24h change |
| `/top` | Top 10 coins |
| `/rate` | Fiat exchange rates |
| `/convert <amount> <from> <to>` | Convert between currencies and coins |
| `/currency <usd\|eur\|uah>` | Set your default currency |
| `/add <coin> <amount>` | Add a coin to your portfolio |
| `/remove <coin> [amount]` | Remove a coin (or part of it) |
| `/portfolio` | Show portfolio value |
| `/alert <coin> <price>` | Create a price alert |
| `/alerts` | List your alerts |
| `/cancel` | Delete all your alerts |
| `/fear` | Fear & Greed index |

Short names work for popular coins: `btc`, `eth`, `sol`, `doge`, `xrp`, `ton`, `bnb`, `ada`, `trx`, `ltc`.
For other coins use the full CoinGecko id (for example `polkadot`).

## Setup

1. Install Python 3.10 or newer.
2. Create a bot with [@BotFather](https://t.me/BotFather) and copy the token.
3. Install the dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Create a file named `token.txt` next to `bot.py` and paste the token into it (only the token, nothing else).
   Alternatively, set the `BOT_TOKEN` environment variable.
5. Run the bot:
   ```
   python bot.py
   ```

Never commit your token. `token.txt` and `bot_data.json` are listed in `.gitignore`.

## Data sources

- [CoinGecko API](https://www.coingecko.com/en/api) – crypto prices (free tier, rate limited)
- [open.er-api.com](https://www.exchangerate-api.com/docs/free) – fiat exchange rates
- [alternative.me](https://alternative.me/crypto/fear-and-greed-index/) – Fear & Greed index

Prices are cached for a short time to stay within the free API limits.

## Project structure

```
bot.py            # the whole bot
requirements.txt  # dependencies
README.md
.gitignore
```

## Ideas for the future

- Daily portfolio report
- Price charts
- Alerts for sudden price moves
- Hosting 24/7 on a server

## Author

Denys – learning Python and building small automation tools and bots.
Open to small freelance projects: Telegram bots, scripts, automation.
