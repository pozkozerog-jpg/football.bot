import requests
from datetime import datetime, timedelta
import os

API_KEY = os.getenv("FOOTBALL_DATA_KEY")
BASE_URL = "https://api.football-data.org/v4"

headers = {"X-Auth-Token": API_KEY} if API_KEY else {}

def get_leagues():
    """Возвращает список популярных лиг и турниров"""
    return {
        "CL": "Лига чемпионов",
        "PL": "АПЛ (Англия)",
        "PD": "Ла Лига (Испания)",
        "SA": "Серия А (Италия)",
        "BL1": "Бундеслига (Германия)",
        "FL1": "Лига 1 (Франция)",
        "WC": "Чемпионат мира",
        "EC": "Евро",
        "WCQ": "Отбор на ЧМ",
        "ECQ": "Отбор на Евро",
    }

def get_matches(league_code, days_ahead=0):
    """Получает матчи для выбранной лиги"""
    if not API_KEY:
        # Тестовый режим, если нет ключа
        today = datetime.now()
        return [{
            "homeTeam": "Real Madrid",
            "awayTeam": "Barcelona",
            "utcDate": (today + timedelta(days=days_ahead)).strftime("%Y-%m-%dT20:00:00Z")
        }]
    url = f"{BASE_URL}/competitions/{league_code}/matches"
    params = {"dateFrom": datetime.now().strftime("%Y-%m-%d"),
              "dateTo": (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")}
    r = requests.get(url, headers=headers, params=params)
    if r.status_code != 200:
        return []
    data = r.json()
    return data.get("matches", [])

def analyze_match(match):
    """Простая аналитика (заглушка)"""
    home = match["homeTeam"]["name"]
    away = match["awayTeam"]["name"]
    return f"Прогноз: {home} vs {away}\n⚽ Вероятный победитель: {home}\nТотал > 2.5"
