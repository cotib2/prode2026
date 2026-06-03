from fastapi import APIRouter, HTTPException # type: ignore
from app.services.football_api import FootballAPIService
from app.database import supabase

# Creamos el router que después se va a acoplar al main.py
router = APIRouter(
    prefix="/api/partidos",
    tags=["Partidos"]
)

# Inicializamos el servicio de la API de fútbol afuera para reutilizarlo
football_service = FootballAPIService()

# @router.post("/sincronizar")
# def sincronizar_fixture():
#     """
#     Endpoint para traer los partidos de la API externa e inyectarlos/actualizarlos en Supabase.
#     """
#     try:
#         # 1. Llamamos al servicio para buscar los partidos actuales de la API
#         partidos_api = football_service.obtener_fixture_mundial()
        
#         if not partidos_api:
#             raise HTTPException(status_code=502, detail="No se pudieron obtener partidos de la API externa.")

#         # 2. Hacemos el upsert masivo en Supabase.
#         # Si el 'id_api' ya existe, actualiza los goles y el estado; si no, lo crea de cero.
#         resultado = supabase.table("partidos").upsert(
#             partidos_api, 
#             on_conflict="id_api"
#         ).execute()

#         return {
#             "status": "success",
#             "message": f"Se sincronizaron {len(partidos_api)} partidos exitosamente en Supabase.",
#             "cantidad": len(partidos_api)
#         }

#     except Exception as e:
#         print(f"❌ Error en sincronizar_fixture: {e}")
#         raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

@router.post("/sincronizar")
def sincronizar_fixture():
    # Le pegamos directo a la API y devolvemos los primeros 2 partidos tal cual vienen
    import requests
    import os
    url = "https://api.football-data.org/v4/competitions/WC/matches"
    headers = { "X-Auth-Token": os.getenv("FOOTBALL_DATA_API_KEY") }
    response = requests.get(url, headers=headers)
    data = response.json()
    
    # Devolvemos solo los 2 primeros partidos para espiar la estructura
    return data.get("matches", [])[:2]