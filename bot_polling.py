# bot_polling.py
import os
import json
import logging
from datetime import datetime, timedelta
import pytz
import requests
from dotenv import load_dotenv
from telegram import Bot, Update
from telegram.ext import Updater, CommandHandler, CallbackContext

# Load .env (локально) — добавляй .env в .gitignore
load_dotenv()

# ============ Настройки (не хардкодь реальные токены здесь) ============
BOT_TOKEN = os.getenv("8545943161:AAG6O1eCfHhQY8xtpqLplPhyVgbUR6RhGRE")
FOOTBALL_DATA_KEY = os.getenv("FOOTBALL_DATA_KEY", "")  # optional, football-data.org
USERS_FILE = "subscribed_users.json"
MOSCOW_TZ = "Europe/Moscow"
BASE_URL = "https://api.football-data.org/v4"

# ============ Логирование ============
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("football_bot")

# ============ Работа с подписчиками ============
def load_users():
    if not os.path.exists(USERS_FILE):
        return []
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def add_user(chat_id):
    users = load_users()
    if chat_id not in users:
        users.append(chat_id)
        save_users(users)
        logger.info(f"Added user {chat_id}")

def remove_user(chat_id):
    users = load_users()
    if chat_id in users:
        users.remove(chat_id)
        save_users(users)
        logger.info(f"Removed user {chat_id}")

# ============ Вспомогательные функции ============
def fd_headers():
    headers = {}
    if FOOTBALL_DATA_KEY:
        headers["X-Auth-Token"] = FOOTBALL_DATA_KEY
    return headers

def now_msk():
    return datetime.now(pytz.timezone(MOSCOW_TZ))

def fetch_matches_by_date(date_str):
    """date_str like 'YYYY-MM-DD'"""
    url = f"{BASE_URL}/matches?dateFrom={date_str}&dateTo={date_str}"
    try:
        r = requests.get(url, headers=fd_headers(), timeout=10)
        if r.status_code == 200:
            return r.json().get("matches", [])
        else:
            logger.warning(f"FD API returned {r.status_code}: {r.text[:200]}")
            return []
    except Exception as e:
        logger.exception("Error fetching matches: %s", e)
        return []

def fetch_match_details(match_id):
    url = f"{BASE_URL}/matches/{match_id}"
    try:
        r = requests.get(url, headers=fd_headers(), timeout=10)
        if r.status_code == 200:
            return r.json()
        else:
            logger.warning(f"FD details returned {r.status_code}")
            return {}
    except Exception as e:
        logger.exception("Error fetching match details: %s", e)
        return {}

# Простая детерминированная модель-прогноз (можно заменить позже)
def compute_simple_prediction(match):
    home = match.get("homeTeam", {}).get("name", "Home")
    away = match.get("awayTeam", {}).get("name", "Away")
    seed = sum(ord(c) for c in (home + away + str(match.get("utcDate", ""))))
    eh = (sum(ord(c) for c in home) % 40) / 30.0 + 0.6
    ea = (sum(ord(c) for c in away) % 40) / 30.0 + 0.6
    gh = int(eh * ((seed % 7)/10.0 + 1)) % 5
    ga = int(ea * (((seed//7) % 5)/10.0 + 1)) % 5
    outcome = "Draw" if gh == ga else (home if gh > ga else away)
    p_over = min(0.98, (eh+ea)/3.0)
    return {
        "home": home, "away": away,
        "exp_home": round(eh,2), "exp_away": round(ea,2),
        "sim_score": f"{gh}:{ga}", "outcome": outcome, "p_over_2_5": round(p_over,3)
    }

def format_prediction(pred, match):
    utc = match.get("utcDate", "")
    try:
        dt = datetime.fromisoformat(utc.replace("Z", "+00:00"))
        dt_msk = dt.astimezone(pytz.timezone(MOSCOW_TZ))
        timestr = dt_msk.strftime("%Y-%m-%d %H:%M MSK")
    except Exception:
        timestr = utc
    return (f"⚽ {pred['home']} — {pred['away']}\n"
            f"🏟 {match.get('competition',{}).get('name','')}\n"
            f"🕒 {timestr}\n"
            f"🔮 Прогноз: {pred['outcome']}  |  Счёт: {pred['sim_score']}\n"
            f"📈 Exp goals: {pred['exp_home']} — {pred['exp_away']}  |  P(over2.5): {int(pred['p_over_2_5']*100)}%\n")

# ============ Телеграм команды ============
def start(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    add_user(chat_id)
    txt = ("Привет! Я футбольный бот.\n\n"
           "Команды:\n"
           "/today — прогнозы на сегодня\n"
           "/next <days> — прогнозы через N дней (например /next 3)\n"
           "/matches [YYYY-MM-DD] — список матчей на дату\n"
           "/detail <match_id> — подробный разбор матча\n"
           "/unsubscribe — отписаться от рассылки\n")
    update.message.reply_text(txt)

def unsubscribe(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    remove_user(chat_id)
    update.message.reply_text("Отписал тебя от рассылки.")

def cmd_today(update: Update, context: CallbackContext):
    date = now_msk().strftime("%Y-%m-%d")
    matches = fetch_matches_by_date(date)
    if not matches:
        update.message.reply_text("Матчей сегодня не найдено.")
        return
    texts = []
    for m in matches[:20]:
        pred = compute_simple_prediction(m)
        texts.append(format_prediction(pred, m))
    chunk = ""
    for t in texts:
        if len(chunk) + len(t) > 3000:
            update.message.reply_text(chunk)
            chunk = t
        else:
            chunk += t + "\n"
    if chunk:
        update.message.reply_text(chunk)

def cmd_next(update: Update, context: CallbackContext):
    days = 1
    try:
        if context.args:
            days = int(context.args[0])
    except:
        days = 1
    target = (now_msk().date() + timedelta(days=days)).isoformat()
    matches = fetch_matches_by_date(target)
    if not matches:
        update.message.reply_text("Матчей не найдено.")
        return
    texts=[]
    for m in matches[:20]:
        pred = compute_simple_prediction(m)
        texts.append(format_prediction(pred, m))
    chunk=""; 
    for t in texts:
        if len(chunk)+len(t)>3000:
            update.message.reply_text(chunk); chunk=t
        else:
            chunk+=t+"\n"
    if chunk: update.message.reply_text(chunk)

def cmd_matches(update: Update, context: CallbackContext):
    date = context.args[0] if context.args else now_msk().strftime("%Y-%m-%d")
    matches = fetch_matches_by_date(date)
    if not matches:
        update.message.reply_text("Матчей не найдено.")
        return
    text = f"Матчи на {date}:\n"
    for m in matches:
        mid = m.get("id") or m.get("utcDate")
        home = m.get("homeTeam",{}).get("name")
        away = m.get("awayTeam",{}).get("name")
        text += f"{mid} | {home} — {away}\n"
    update.message.reply_text(text)

def cmd_detail(update: Update, context: CallbackContext):
    if not context.args:
        update.message.reply_text("Использование: /detail <match_id>")
        return
    fid = context.args[0]
    details = fetch_match_details(fid)
    if not details:
        update.message.reply_text("Деталей не найдено.")
        return
    match = details.get("match") or {}
    home = match.get("homeTeam",{}).get("name","")
    away = match.get("awayTeam",{}).get("name","")
    score = match.get("score", {})
    venue = match.get("venue", "—")
    txt = f"Подробности: {home} — {away}\nСтадион: {venue}\nСчёт: {score}\n"
    update.message.reply_text(txt)

# ============ Main ============
def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("unsubscribe", unsubscribe))
    dp.add_handler(CommandHandler("today", cmd_today))
    dp.add_handler(CommandHandler("next", cmd_next))
    dp.add_handler(CommandHandler("matches", cmd_matches))
    dp.add_handler(CommandHandler("detail", cmd_detail))

    logger.info("Polling bot started")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()

