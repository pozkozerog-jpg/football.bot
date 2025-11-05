import os
import requests
from utils import get_matches, analyze_match
from datetime import datetime, timedelta

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID", None)  # можно позже добавить в secrets

def send_message(text):
    if not CHAT_ID:
        print("❌ CHAT_ID не указан, пропуск отправки.")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text})

def main():
    matches = get_matches("PL", days_ahead=1)
    if not matches:
        send_message("Сегодня нет матчей ⚽")
        return
    message = "📅 Прогнозы на завтра:\n\n"
    for m in matches[:5]:
        message += analyze_match(m) + "\n\n"
    send_message(message)

if __name__ == "__main__":
    main()
