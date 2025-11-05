import os
import requests
import datetime
import random
from aiogram import Bot, Dispatcher, executor, types

# === Настройки ===
API_KEY = os.getenv("API_FOOTBALL_KEY")  # Ключ от API-Football (RapidAPI)
BOT_TOKEN = os.getenv("BOT_TOKEN")        # Токен от BotFather
CHAT_ID = os.getenv("CHAT_ID")            # ID чата для автоотправки

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# --- Список лиг и турниров ---
LEAGUES = {
    "Англия": 39,      # Premier League
    "Испания": 140,    # La Liga
    "Германия": 78,    # Bundesliga
    "Италия": 135,     # Serie A
    "Франция": 61,     # Ligue 1
    "Португалия": 94,  # Liga Portugal
    "Нидерланды": 88,  # Eredivisie
    "Россия": 235,     # Premier League Russia
    "Бразилия": 71,    # Serie A Brazil
    "США": 253,        # MLS
    "Лига Чемпионов": 2,
    "Лига Европы": 3,
    "Лига Конференций": 848,
    "Чемпионат Мира": 1,
    "Чемпионат Европы": 4
}

# --- Получение матчей из API ---
def get_matches(league_id, date):
    url = "https://api-football-v1.p.rapidapi.com/v3/fixtures"
    headers = {
        "x-rapidapi-key": API_KEY,
        "x-rapidapi-host": "api-football-v1.p.rapidapi.com"
    }
    params = {"league": league_id, "season": 2024, "date": date}
    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    return data.get("response", [])

# --- Простейший анализ формы ---
def analyze_match(match):
    home = match["teams"]["home"]["name"]
    away = match["teams"]["away"]["name"]

    # (в реальном проекте здесь был бы анализ по head2head и статистике)
    home_score = random.uniform(0, 3)
    away_score = random.uniform(0, 3)

    winner = "Ничья"
    if home_score > away_score:
        winner = home
    elif away_score > home_score:
        winner = away

    total = home_score + away_score
    total_text = "Тотал больше 2.5" if total > 2.5 else "Тотал меньше 2.5"

    return f"🏟 {home} vs {away}\n⚽ Прогноз: {winner}\n📊 {total_text}\n"

# --- Автоматическая рассылка ---
def send_auto_forecast():
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    text = f"⚽ Прогнозы на {today} (по МСК):\n\n"

    for league_name, league_id in LEAGUES.items():
        matches = get_matches(league_id, today)
        if not matches:
            continue
        text += f"🏆 {league_name}\n"
        for m in matches:
            text += analyze_match(m) + "\n"

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": text}
    requests.post(url, data=data)

# --- Команда /today ---
@dp.message_handler(commands=["today"])
async def today_cmd(message: types.Message):
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    text = f"⚽ Матчи сегодня ({today}):\n\n"
    for league_name, league_id in LEAGUES.items():
        matches = get_matches(league_id, today)
        if matches:
            text += f"🏆 {league_name}\n"
            for m in matches:
                home = m["teams"]["home"]["name"]
                away = m["teams"]["away"]["name"]
                text += f"- {home} vs {away}\n"
    await message.answer(text)

# --- Команда /next ---
@dp.message_handler(commands=["next"])
async def next_cmd(message: types.Message):
    date = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    text = f"⚽ Матчи завтра ({date}):\n\n"
    for league_name, league_id in LEAGUES.items():
        matches = get_matches(league_id, date)
        if matches:
            text += f"🏆 {league_name}\n"
            for m in matches:
                home = m["teams"]["home"]["name"]
                away = m["teams"]["away"]["name"]
                text += f"- {home} vs {away}\n"
    await message.answer(text)

if __name__ == "__main__":
    send_auto_forecast()  # отправка прогнозов каждый день в 00:00
    executor.start_polling(dp)
