import json
import os
import time

import requests
from telegram import ReplyKeyboardMarkup, Update
from telegram.error import TelegramError
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes



def load_token():
    """Токен береться НЕ з коду, а зі змінної BOT_TOKEN або з файлу token.txt."""
    token = os.getenv("BOT_TOKEN")
    if token:
        return token.strip()
    if os.path.exists("token.txt"):
        with open("token.txt", "r", encoding="utf-8") as f:
            return f.read().strip()
    raise SystemExit(
        "Токен не знайдено. Створи файл token.txt поруч із bot.py "
        "і встав у нього токен від @BotFather (тільки токен, без лапок)."
    )


TOKEN = load_token()

# ---------- Налаштування ----------
CG_URL = "https://api.coingecko.com/api/v3"            # ціни криптовалют
FIAT_URL = "https://open.er-api.com/v6/latest/USD"     # курси доларів, євро, гривень...
FNG_URL = "https://api.alternative.me/fng/"            # індекс страху і жадібності

DATA_FILE = "bot_data.json"   # тут зберігаються алерти, портфелі, валюти користувачів
CURRENCIES = ["usd", "eur", "uah"]
SYMBOLS = {"usd": "$", "eur": "€", "uah": "₴"}
DEFAULT_CURRENCY = "eur"
CHECK_EVERY = 60              # як часто перевіряти алерти, секунди
MAX_ALERTS = 5

# Короткі назви монет -> назви для CoinGecko
ALIASES = {
    "btc": "bitcoin",
    "eth": "ethereum",
    "sol": "solana",
    "doge": "dogecoin",
    "xrp": "ripple",
    "ton": "the-open-network",
    "bnb": "binancecoin",
    "ada": "cardano",
    "trx": "tron",
    "ltc": "litecoin",
}


# ---------- Збереження даних у файл ----------
def load_db():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_db():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


db = load_db()


def get_user(chat_id):
    """Повертає дані користувача. Якщо його ще немає, створює."""
    key = str(chat_id)
    if key not in db:
        db[key] = {"currency": DEFAULT_CURRENCY, "alerts": [], "portfolio": {}}
        save_db()
    return db[key]


# ---------- Робота з інтернетом (з кешем, щоб не впиратись у ліміти) ----------
_cache = {}


def cached_get(url, params=None, ttl=30):
    key = url + json.dumps(params or {}, sort_keys=True)
    now = time.time()
    if key in _cache and now - _cache[key][0] < ttl:
        return _cache[key][1]
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    result = response.json()
    _cache[key] = (now, result)
    return result


def resolve(name):
    """btc -> bitcoin. Якщо не знаємо скорочення, лишаємо як є."""
    name = name.lower()
    return ALIASES.get(name, name)


def get_coin_prices(coin_ids, currency):
    params = {
        "ids": ",".join(coin_ids),
        "vs_currencies": currency,
        "include_24hr_change": "true",
    }
    return cached_get(CG_URL + "/simple/price", params)


def get_fiat_rates():
    """Скільки одиниць валюти за 1 долар. Приклад: {'EUR': 0.92, 'UAH': 41.5}"""
    return cached_get(FIAT_URL, ttl=600)["rates"]


def to_usd(amount, code):
    up = code.upper()
    rates = get_fiat_rates()
    if up in rates:
        return amount / rates[up]
    coin = resolve(code)
    prices = cached_get(CG_URL + "/simple/price", {"ids": coin, "vs_currencies": "usd"})
    if coin not in prices:
        raise ValueError(code)
    return amount * prices[coin]["usd"]


def from_usd(amount_usd, code):
    up = code.upper()
    rates = get_fiat_rates()
    if up in rates:
        return amount_usd * rates[up]
    coin = resolve(code)
    prices = cached_get(CG_URL + "/simple/price", {"ids": coin, "vs_currencies": "usd"})
    if coin not in prices:
        raise ValueError(code)
    return amount_usd / prices[coin]["usd"]


# ---------- Допоміжні функції ----------
def fmt_num(x):
    if x >= 1:
        return f"{x:,.2f}"
    return f"{x:.6f}".rstrip("0").rstrip(".")


def fmt_money(x, currency):
    return f"{SYMBOLS.get(currency, '')}{fmt_num(x)}"


def fmt_change(pct):
    if pct is None:
        return ""
    icon = "🟢" if pct >= 0 else "🔴"
    return f"{icon} {pct:+.2f}%"


def parse_number(text):
    return float(text.replace(",", "."))


NET_ERROR = "Не вийшло зв'язатися із сервісом, спробуй за хвилину."
UNKNOWN_COIN = "Не знайшов таку монету. Приклад: btc, eth, sol, doge, або повна назва англійською."


# ---------- Команди ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    get_user(update.effective_chat.id)
    keyboard = ReplyKeyboardMarkup(
        [["/top", "/rate"], ["/portfolio", "/alerts"], ["/fear", "/help"]],
        resize_keyboard=True,
    )
    await update.message.reply_text(
        "Привіт! Я крипто-бот 🚀\nНатискай кнопки внизу або напиши /help.",
        reply_markup=keyboard,
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📊 Ціни\n"
        "/price btc - ціна монети в $, € і ₴\n"
        "/top - топ-10 монет за капіталізацією\n"
        "/fear - індекс страху і жадібності\n\n"
        "💱 Валюти\n"
        "/rate - курси долара, євро, гривні\n"
        "/convert 100 usd eur - конвертер (можна і крипту: /convert 0.5 btc usd)\n"
        "/currency eur - моя валюта (usd, eur, uah)\n\n"
        "💼 Портфель\n"
        "/add btc 0.5 - додати монету\n"
        "/remove btc - прибрати монету (або /remove btc 0.2)\n"
        "/portfolio - скільки коштує мій портфель\n\n"
        "🔔 Алерти\n"
        "/alert btc 90000 - сповістити, коли ціна дійде до рівня\n"
        "/alerts - мої алерти\n"
        "/cancel - видалити всі алерти"
    )


async def currency_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_chat.id)
    if not context.args:
        await update.message.reply_text(
            f"Зараз твоя валюта: {user['currency'].upper()}.\nЗмінити: /currency usd, /currency eur або /currency uah"
        )
        return

    choice = context.args[0].lower()
    if choice not in CURRENCIES:
        await update.message.reply_text("Доступні валюти: usd, eur, uah")
        return

    user["currency"] = choice
    save_db()
    await update.message.reply_text(f"Готово! Тепер усе рахую в {choice.upper()}.")


async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Напиши монету, наприклад: /price btc")
        return

    coin = resolve(context.args[0])
    try:
        prices = cached_get(
            CG_URL + "/simple/price",
            {"ids": coin, "vs_currencies": "usd,eur,uah", "include_24hr_change": "true"},
        )
    except requests.RequestException:
        await update.message.reply_text(NET_ERROR)
        return

    if coin not in prices:
        await update.message.reply_text(UNKNOWN_COIN)
        return

    p = prices[coin]
    text = (
        f"💰 {coin.capitalize()}\n"
        f"{fmt_money(p['usd'], 'usd')}\n"
        f"{fmt_money(p['eur'], 'eur')}\n"
        f"{fmt_money(p['uah'], 'uah')}\n"
        f"За 24 години: {fmt_change(p.get('usd_24h_change'))}"
    )
    await update.message.reply_text(text)


async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    currency = get_user(update.effective_chat.id)["currency"]
    try:
        coins = cached_get(
            CG_URL + "/coins/markets",
            {
                "vs_currency": currency,
                "order": "market_cap_desc",
                "per_page": 10,
                "page": 1,
            },
        )
    except requests.RequestException:
        await update.message.reply_text(NET_ERROR)
        return

    lines = [f"🏆 Топ-10 монет ({currency.upper()})"]
    for i, c in enumerate(coins, start=1):
        lines.append(
            f"{i}. {c['symbol'].upper()}: {fmt_money(c['current_price'], currency)} "
            f"{fmt_change(c.get('price_change_percentage_24h'))}"
        )
    await update.message.reply_text("\n".join(lines))


async def rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        r = get_fiat_rates()
    except requests.RequestException:
        await update.message.reply_text(NET_ERROR)
        return

    text = (
        "💱 Курси валют\n"
        f"1 USD = {r['EUR']:.4f} EUR\n"
        f"1 USD = {r['UAH']:.2f} UAH\n"
        f"1 EUR = {r['UAH'] / r['EUR']:.2f} UAH\n"
        f"1 USD = {r['PLN']:.2f} PLN\n"
        f"1 EUR = {1 / r['EUR']:.4f} USD"
    )
    await update.message.reply_text(text)


async def convert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 3:
        await update.message.reply_text("Формат: /convert 100 usd eur\nАбо з криптою: /convert 0.5 btc usd")
        return

    try:
        amount = parse_number(context.args[0])
    except ValueError:
        await update.message.reply_text("Перше має бути число, наприклад: /convert 100 usd eur")
        return

    code_from, code_to = context.args[1], context.args[2]

    try:
        result = from_usd(to_usd(amount, code_from), code_to)
    except ValueError as e:
        await update.message.reply_text(f"Не знаю таку валюту чи монету: {e}")
        return
    except requests.RequestException:
        await update.message.reply_text(NET_ERROR)
        return

    await update.message.reply_text(
        f"{fmt_num(amount)} {code_from.upper()} = {fmt_num(result)} {code_to.upper()}"
    )


async def fear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        info = cached_get(FNG_URL, ttl=600)["data"][0]
    except (requests.RequestException, KeyError, IndexError):
        await update.message.reply_text(NET_ERROR)
        return

    await update.message.reply_text(
        f"😱 Індекс страху і жадібності: {info['value']}/100\n"
        f"Настрій ринку: {info['value_classification']}\n\n"
        "0 - екстремальний страх, 100 - екстремальна жадібність. "
        "Це лише індикатор настрою, а не порада купувати чи продавати."
    )


# ---------- Портфель ----------
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text("Формат: /add btc 0.5")
        return

    coin = resolve(context.args[0])
    try:
        amount = parse_number(context.args[1])
    except ValueError:
        await update.message.reply_text("Кількість має бути числом, наприклад: /add btc 0.5")
        return

    if amount <= 0:
        await update.message.reply_text("Кількість має бути більше нуля.")
        return

    try:
        prices = get_coin_prices([coin], "usd")
    except requests.RequestException:
        await update.message.reply_text(NET_ERROR)
        return

    if coin not in prices:
        await update.message.reply_text(UNKNOWN_COIN)
        return

    user = get_user(update.effective_chat.id)
    user["portfolio"][coin] = user["portfolio"].get(coin, 0) + amount
    save_db()
    await update.message.reply_text(
        f"Додано. Тепер у портфелі: {fmt_num(user['portfolio'][coin])} {coin.capitalize()}"
    )


async def remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Формат: /remove btc (прибрати все) або /remove btc 0.2")
        return

    coin = resolve(context.args[0])
    user = get_user(update.effective_chat.id)

    if coin not in user["portfolio"]:
        await update.message.reply_text("Такої монети немає в твоєму портфелі.")
        return

    if len(context.args) >= 2:
        try:
            amount = parse_number(context.args[1])
        except ValueError:
            await update.message.reply_text("Кількість має бути числом.")
            return
        user["portfolio"][coin] -= amount
        if user["portfolio"][coin] <= 0:
            del user["portfolio"][coin]
    else:
        del user["portfolio"][coin]

    save_db()
    await update.message.reply_text("Готово. Дивись: /portfolio")


async def portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_chat.id)
    currency = user["currency"]

    if not user["portfolio"]:
        await update.message.reply_text("Портфель порожній. Додай монету: /add btc 0.5")
        return

    try:
        prices = get_coin_prices(list(user["portfolio"].keys()), currency)
    except requests.RequestException:
        await update.message.reply_text(NET_ERROR)
        return

    lines = [f"💼 Мій портфель ({currency.upper()})"]
    total = 0
    for coin, amount in user["portfolio"].items():
        if coin not in prices:
            continue
        value = amount * prices[coin][currency]
        total += value
        lines.append(f"{coin.capitalize()}: {fmt_num(amount)} = {fmt_money(value, currency)}")

    lines.append(f"\nРазом: {fmt_money(total, currency)}")
    await update.message.reply_text("\n".join(lines))


# ---------- Алерти ----------
async def alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text("Формат: /alert btc 90000")
        return

    coin = resolve(context.args[0])
    try:
        target = parse_number(context.args[1])
    except ValueError:
        await update.message.reply_text("Ціна має бути числом, наприклад: /alert btc 90000")
        return

    user = get_user(update.effective_chat.id)
    currency = user["currency"]

    if len(user["alerts"]) >= MAX_ALERTS:
        await update.message.reply_text(f"Максимум {MAX_ALERTS} алертів. Видали старі: /cancel")
        return

    try:
        prices = get_coin_prices([coin], currency)
    except requests.RequestException:
        await update.message.reply_text(NET_ERROR)
        return

    if coin not in prices:
        await update.message.reply_text(UNKNOWN_COIN)
        return

    current = prices[coin][currency]
    direction = "up" if target > current else "down"
    word = "виросте до" if direction == "up" else "впаде до"

    user["alerts"].append(
        {"coin": coin, "target": target, "direction": direction, "currency": currency}
    )
    save_db()

    await update.message.reply_text(
        f"🔔 Готово! Сповіщу, коли {coin.capitalize()} {word} {fmt_money(target, currency)}.\n"
        f"Зараз: {fmt_money(current, currency)}"
    )


async def my_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_chat.id)
    if not user["alerts"]:
        await update.message.reply_text("Алертів немає. Створи: /alert btc 90000")
        return

    lines = ["🔔 Мої алерти"]
    for a in user["alerts"]:
        arrow = "вище" if a["direction"] == "up" else "нижче"
        lines.append(f"{a['coin'].capitalize()}: коли {arrow} {fmt_money(a['target'], a['currency'])}")
    await update.message.reply_text("\n".join(lines))


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_chat.id)
    count = len(user["alerts"])
    user["alerts"] = []
    save_db()
    await update.message.reply_text(f"Видалено алертів: {count}")


async def check_alerts(context: ContextTypes.DEFAULT_TYPE):
    """Запускається автоматично кожні CHECK_EVERY секунд."""
    # Збираємо, які монети треба перевірити, згруповані за валютою
    needed = {}
    for user in db.values():
        for a in user["alerts"]:
            needed.setdefault(a["currency"], set()).add(a["coin"])

    if not needed:
        return

    prices = {}
    for currency, coins in needed.items():
        try:
            prices[currency] = get_coin_prices(list(coins), currency)
        except requests.RequestException:
            continue  # не вийшло цього разу, спробуємо наступного

    changed = False
    for chat_id, user in db.items():
        for a in user["alerts"][:]:
            p = prices.get(a["currency"], {}).get(a["coin"])
            if not p:
                continue

            current = p[a["currency"]]
            if a["direction"] == "up":
                hit = current >= a["target"]
            else:
                hit = current <= a["target"]

            if hit:
                try:
                    await context.bot.send_message(
                        chat_id=int(chat_id),
                        text=(
                            f"🔔 {a['coin'].capitalize()} досяг {fmt_money(current, a['currency'])} "
                            f"(твоя ціль: {fmt_money(a['target'], a['currency'])})"
                        ),
                    )
                except TelegramError:
                    pass  # наприклад, людина заблокувала бота
                user["alerts"].remove(a)
                changed = True

    if changed:
        save_db()


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("currency", currency_cmd))
    app.add_handler(CommandHandler("price", price))
    app.add_handler(CommandHandler("top", top))
    app.add_handler(CommandHandler("rate", rate))
    app.add_handler(CommandHandler("convert", convert))
    app.add_handler(CommandHandler("fear", fear))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("remove", remove))
    app.add_handler(CommandHandler("portfolio", portfolio))
    app.add_handler(CommandHandler("alert", alert))
    app.add_handler(CommandHandler("alerts", my_alerts))
    app.add_handler(CommandHandler("cancel", cancel))

    app.job_queue.run_repeating(check_alerts, interval=CHECK_EVERY, first=15)

    print("Бот запущено. Зупинити: Ctrl+C")
    app.run_polling()


if __name__ == "__main__":
    main()
