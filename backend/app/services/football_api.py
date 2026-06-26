import os
import requests
from dotenv import load_dotenv # type: ignore

load_dotenv()

# (TLA -> Español)
TRADUCCIONES_PAISES = {
    "ALG": "Argelia",
    "ARG": "Argentina",
    "AUS": "Australia",
    "AUT": "Austria",
    "BEL": "Bélgica",
    "BIH": "Bosnia y Herzegovina",
    "BRA": "Brasil",
    "CAN": "Canadá",
    "CIV": "Costa de Marfil",
    "COD": "República Democrática del Congo",
    "COL": "Colombia",
    "CPV": "Cabo Verde",
    "CRO": "Croacia",
    "CUW": "Curazao",
    "CZE": "República Checa",
    "DEN": "Dinamarca",
    "ECU": "Ecuador",
    "EGY": "Egipto",
    "ENG": "Inglaterra",
    "ESP": "España",
    "FRA": "Francia",
    "GER": "Alemania",
    "GHA": "Ghana",
    "HAI": "Haití",
    "IRN": "Irán",
    "IRQ": "Irak",
    "ITA": "Italia",
    "JOR": "Jordania",
    "JPN": "Japón",
    "KSA": "Arabia Saudita",
    "KOR": "Corea del Sur",
    "MAR": "Marruecos",
    "MEX": "México",
    "NED": "Países Bajos",
    "NOR": "Noruega",
    "NZL": "Nueva Zelanda",
    "PAN": "Panamá",
    "PAR": "Paraguay",
    "POR": "Portugal",
    "QAT": "Catar",
    "RSA": "Sudáfrica",
    "SCO": "Escocia",
    "SEN": "Senegal",
    "SUI": "Suiza",
    "SWE": "Suecia",
    "TUN": "Túnez",
    "TUR": "Turquía",
    "URU": "Uruguay",
    "URY": "Uruguay",
    "USA": "Estados Unidos",
    "UZB": "Uzbekistán"
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
            home_tla = match.get("homeTeam", {}).get("tla")
            away_tla = match.get("awayTeam", {}).get("tla")
            
            # Si todavía no hay equipos definidos (fases avanzadas vacías), los salteamos
            if not home_tla or not away_tla:
                continue
            
            home_es = TRADUCCIONES_PAISES.get(home_tla, home_tla)
            away_es = TRADUCCIONES_PAISES.get(away_tla, away_tla)

            # Extraemos el bloque score para analizar la definición
            score_data = match.get("score", {})
            
            # 🚀 Lógica de penales: detectamos si hubo definición por penales
            ganador_penales = None
            if score_data.get("duration") == "PENALTY_SHOOTOUT":
                winner = score_data.get("winner")
                # Mapeamos "HOME_TEAM" a "1" (equipo_1) y "AWAY_TEAM" a "2" (equipo_2)
                ganador_penales = "1" if winner == "HOME_TEAM" else "2"

            # Estructuramos el diccionario para la tabla 'partidos'
            partido = {
                "id_api": str(match.get("id")),
                "equipo_1": home_es,
                "equipo_2": away_es,
                "fecha": match.get("utcDate"),
                "instancia": match.get("stage"), # Ej: 'GROUP_STAGE'
                "goles_real_1": score_data.get("fullTime", {}).get("home"),
                "goles_real_2": score_data.get("fullTime", {}).get("away"),
                "estado": match.get("status"), # TIMED, IN_PLAY, FINISHED
                "ganador_penales_real": ganador_penales # 💥 Guardamos el ganador de los penales
            }
            partidos_limpios.append(partido)
            
        return partidos_limpios