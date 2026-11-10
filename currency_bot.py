import os

import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.environ["BOT_TOKEN"]
API_URL = "https://www.cbr-xml-daily.ru/daily_json.js"  # курсы ЦБ РФ, без ключа
MAIN = ["USD", "EUR", "CNY", "GBP", "TRY", "KZT"]


async def fetch_rates() -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(API_URL)
        r.raise_for_status()
        return r.json()


def per_unit(cur: dict) -> float:
    return cur["Value"] / cur["Nominal"]


def arrow(cur: dict) -> str:
    diff = cur["Value"] - cur["Previous"]
    if diff > 0:
        return "📈"
    if diff < 0:
        return "📉"
    return "➖"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я показываю курсы валют ЦБ РФ 💱\n\n"
        "/rates — основные курсы\n"
        "/rate USD — курс одной валюты\n"
        "/convert 100 USD — перевести в рубли\n"
        "/convert 5000 RUB EUR — из рублей в валюту"
    )


async def rates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        data = await fetch_rates()
    except Exception:
        await update.message.reply_text("Не удалось получить курсы. Попробуйте позже.")
        return

    date = data["Date"][:10]
    lines = [f"Курсы ЦБ РФ на {date}:\n"]
    for code in MAIN:
        cur = data["Valute"].get(code)
        if cur:
            lines.append(f"{arrow(cur)} {code}: {per_unit(cur):.2f} ₽")
    await update.message.reply_text("\n".join(lines))


async def rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Пример: /rate USD")
        return
    code = context.args[0].upper()
    try:
        data = await fetch_rates()
    except Exception:
        await update.message.reply_text("Не удалось получить курсы. Попробуйте позже.")
        return

    cur = data["Valute"].get(code)
    if not cur:
        await update.message.reply_text(f"Валюта {code} не найдена.")
        return
    await update.message.reply_text(
        f"{arrow(cur)} {cur['Name']} ({code})\n"
        f"Курс: {per_unit(cur):.4f} ₽\n"
        f"Вчера: {cur['Previous'] / cur['Nominal']:.4f} ₽"
    )


async def convert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # /convert 100 USD       -> USD в рубли
    # /convert 5000 RUB EUR  -> рубли в EUR
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Пример: /convert 100 USD")
        return
    try:
        amount = float(args[0].replace(",", "."))
    except ValueError:
        await update.message.reply_text("Сумма должна быть числом.")
        return

    try:
        data = await fetch_rates()
    except Exception:
        await update.message.reply_text("Не удалось получить курсы. Попробуйте позже.")
        return

    first = args[1].upper()
    if first == "RUB":
        if len(args) < 3:
            await update.message.reply_text("Пример: /convert 5000 RUB EUR")
            return
        code = args[2].upper()
        cur = data["Valute"].get(code)
        if not cur:
            await update.message.reply_text(f"Валюта {code} не найдена.")
            return
        result = amount / per_unit(cur)
        await update.message.reply_text(f"{amount:,.2f} ₽ = {result:,.2f} {code}")
    else:
        cur = data["Valute"].get(first)
        if not cur:
            await update.message.reply_text(f"Валюта {first} не найдена.")
            return
        result = amount * per_unit(cur)
        await update.message.reply_text(f"{amount:,.2f} {first} = {result:,.2f} ₽")


def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("rates", rates))
    app.add_handler(CommandHandler("rate", rate))
    app.add_handler(CommandHandler("convert", convert))
    print("Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()
