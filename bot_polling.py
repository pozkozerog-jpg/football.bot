import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from utils import get_leagues, get_matches, analyze_match
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    leagues = get_leagues()
    buttons = [
        [InlineKeyboardButton(name, callback_data=code)] for code, name in leagues.items()
    ]
    await update.message.reply_text("Выбери лигу или турнир:", reply_markup=InlineKeyboardMarkup(buttons))

async def league_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    league_code = query.data
    matches = get_matches(league_code, days_ahead=7)
    if not matches:
        await query.edit_message_text("Матчей не найдено 😢")
        return
    buttons = []
    for m in matches[:10]:
        home = m["homeTeam"]["name"]
        away = m["awayTeam"]["name"]
        match_id = f"{home} vs {away}"
        buttons.append([InlineKeyboardButton(match_id, callback_data=f"MATCH|{match_id}")])
    await query.edit_message_text("Выбери матч:", reply_markup=InlineKeyboardMarkup(buttons))

async def match_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    match_name = query.data.split("|")[1]
    fake_match = {"homeTeam": {"name": match_name.split(" vs ")[0]},
                  "awayTeam": {"name": match_name.split(" vs ")[1]}}
    result = analyze_match(fake_match)
    now = datetime.now().strftime("%d.%m %H:%M (МСК)")
    await query.edit_message_text(f"{result}\n\n🕒 Данные на {now}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(league_selected, pattern="^[A-Z]+$"))
    app.add_handler(CallbackQueryHandler(match_selected, pattern="^MATCH"))
    print("Бот запущен ✅")
    app.run_polling()

if __name__ == "__main__":
    main()
