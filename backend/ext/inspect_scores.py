import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("FOOTBALL_DATA_API_KEY")
url = "https://api.football-data.org/v4/competitions/WC/matches"
headers = {"X-Auth-Token": api_key}

response = requests.get(url, headers=headers)
matches = response.json().get("matches", [])

for match in matches:
    score = match.get("score", {})
    if score.get("duration") == "PENALTY_SHOOTOUT":
        home = match["homeTeam"]["tla"]
        away = match["awayTeam"]["tla"]
        print(f"\n{home} vs {away}")
        print(f"  fullTime:  {score.get('fullTime')}")
        print(f"  extraTime: {score.get('extraTime')}")
        print(f"  penalties: {score.get('penalties')}")
        print(f"  winner:    {score.get('winner')}")
        print(f"  status:    {match.get('status')}")