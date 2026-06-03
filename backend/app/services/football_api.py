import os
import requests
from dotenv import load_dotenv # type: ignore

load_dotenv()

TRADUCCIONES_PAISES = {
    "Argentina": "Argentina",
    "Brazil": "Brasil",
    "Germany": "Alemania",
    "France": "Francia",
    "Spain": "España",
    "Italy": "Italia",
    "England": "Inglaterra",
    "Netherlands": "Países Bajos",
    "Saudi Arabia": "Arabia Saudita",
    "United States": "Estados Unidos",
    "Mexico": "México",
    "Japan": "Japón",
    "South Korea": "Corea del Sur",
    "Morocco": "Marruecos",
    "Croatia": "Croacia",
    "Portugal": "Portugal",
    "Uruguay": "Uruguay",
    "Colombia": "Colombia",
    # +
}

class FootballAPIService:
    def __init__(self):
        self.api_key = os.getenv("FOOTBALL_DATA_API_KEY")
        self.base_url = "https://api.football-data.org/v4"
        self.headers = { "X-Auth-Token": self.api_key }

    def obtener_fixture_mundial(self):
        """
        Le pega a la API externa y devuelve los partidos del Mundial moldeados.
        """
        # 'WC' es el código universal para la World Cup en football-data.org
        url = f"{self.base_url}/competitions/WC/matches"
        
        response = requests.get(url, headers=self.headers)
        
        if response.status_code != 200:
            print(f"❌ Error Football API ({response.status_code}): {response.text}")
            return []

        data = response.json()
        matches = data.get("matches", [])
        partidos_limpios = []

        for match in matches:
            home_en = match.get("homeTeam", {}).get("name")
            away_en = match.get("awayTeam", {}).get("name")
            
            # Si todavía no hay equipos definidos (fases avanzadas vacías), los salteamos
            if not home_en or not away_en:
                continue
            
            home_es = TRADUCCIONES_PAISES.get(home_en, home_en)
            away_es = TRADUCCIONES_PAISES.get(away_en, away_en)

            # Estructuramos el diccionario para la tabla 'partidos'
            partido = {
                "id_api": str(match.get("id")),
                "equipo_1": home_es,
                "equipo_2": away_es,
                "fecha": match.get("utcDate"),
                "instancia": match.get("stage"), # Ej: 'GROUP_STAGE'
                "goles_real_1": match.get("score", {}).get("fullTime", {}).get("home"),
                "goles_real_2": match.get("score", {}).get("fullTime", {}).get("away"),
                "estado": match.get("status") # TIMED, IN_PLAY, FINISHED
            }
            partidos_limpios.append(partido)
            
        return partidos_limpios