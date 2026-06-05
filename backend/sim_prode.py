import os
from datetime import datetime, timezone
import uuid
from app.database import supabase  # Asegurate de que la ruta a tu cliente sea correcta

def simular_datos_prode():
    print("🚀 Iniciando simulación de datos para Prode 2026...")

    # -------------------------------------------------------------------------
    # 👤 1. USAR IDs REALES QUE YA EXISTAN EN TU AUTH DE SUPABASE
    # -------------------------------------------------------------------------
    # ⚠️ REEMPLAZÁ ESTOS STRINGS POR IDs REALES DE TU TABLA PROFILES / AUTH.USERS
    user_coti = "7ea81232-f47f-4ebb-a785-dcc723e4a92d" 
    user_vale = "3edf7bc6-4b33-42eb-b8c9-f29b4a11105f"
    user_guada = "bdf8b156-879e-4549-a231-e7ebb01ab19e"
    
    # Si solo tenés tu usuario creado en Auth por ahora, podemos simular el dataset 
    # compitiendo contra vos misma en diferentes partidos, o registrar dos cuentas rápidas en tu Login.
    
    # Para este ejemplo, asumimos que conseguiste los 3 IDs que ya pasaron por Auth:
    usuarios_prueba = [
        {"id": user_coti, "username": "Coti", "campeon_prediccion": "Argentina", "subcampeon_prediccion": "Alemania"},
        {"id": user_vale, "username": "Vale", "campeon_prediccion": "Brasil", "subcampeon_prediccion": "Francia"},
        {"id": user_guada, "username": "Guada", "campeon_prediccion": "Alemania", "subcampeon_prediccion": "España"}
    ]
    print("Inserting usuarios con predicciones a largo plazo...")
    supabase.table("profiles").upsert(usuarios_prueba, on_conflict="id").execute()
    # -------------------------------------------------------------------------
    # 📅 2. INSERTAR PARTIDOS DE PRUEBA
    # -------------------------------------------------------------------------
    # Ponemos fechas lejanas para que no te rebote el candado de los 5 minutos al votar
    partidos_prueba = [
        {
            "id_api": 1,
            "equipo_1": "Argentina",
            "equipo_2": "Francia",
            "instancia": "GROUP_STAGE",
            "fecha": "2026-06-15T18:00:00Z",
            "estado": "FINISHED",
            "goles_real_1": 2,
            "goles_real_2": 1,
            "ganador_penales_real": None
        },
        {
            "id_api": 2,
            "equipo_1": "Brasil",
            "equipo_2": "Alemania",
            "instancia": "GROUP_STAGE",
            "fecha": "2026-06-16T15:00:00Z",
            "estado": "FINISHED",
            "goles_real_1": 1,
            "goles_real_2": 1,
            "ganador_penales_real": None
        },
        {
            "id_api": 3,
            "equipo_1": "España",
            "equipo_2": "Italia",
            "instancia": "LAST_16", # Eliminación directa (Termina en empate real)
            "fecha": "2026-06-20T21:00:00Z",
            "estado": "FINISHED",
            "goles_real_1": 2,
            "goles_real_2": 2,
            "ganador_penales_real": "España" # España pasó por penales
        },
        {
            "id_api": 4,
            "equipo_1": "Inglaterra",
            "equipo_2": "Japón",
            "instancia": "GROUP_STAGE",
            "fecha": "2026-06-21T12:00:00Z",
            "estado": "FINISHED",
            "goles_real_1": 3,
            "goles_real_2": 0,
            "ganador_penales_real": None
        }
    ]

    print("Inserting partidos...")
    supabase.table("partidos").upsert(partidos_prueba, on_conflict="id_api").execute()

    # -------------------------------------------------------------------------
    # 📊 3. INSERTAR PRONÓSTICOS DE PRUEBA
    # -------------------------------------------------------------------------
    pronosticos_prueba = [
        # --- Tus Pronósticos (Coti) ---
        {
            "user_id": user_coti, "partido_id": 1, 
            "goles_pronostico_1": 2, "goles_pronostico_2": 1, "gana_penales_pronostico": None
        }, # ✅ PLENO EXACTO (6 pts)
        {
            "user_id": user_coti, "partido_id": 2, 
            "goles_pronostico_1": 2, "goles_pronostico_2": 2, "gana_penales_pronostico": None
        }, # 🤝 Empate pero no exacto (3 pts)
        {
            "user_id": user_coti, "partido_id": 3, 
            "goles_pronostico_1": 2, "goles_pronostico_2": 2, "gana_penales_pronostico": "España"
        }, # 🏆 Eliminatoria: Empate exacto + Ganador Penales (9 pts)
        {
            "user_id": user_coti, "partido_id": 4, 
            "goles_pronostico_1": 1, "goles_pronostico_2": 2, "gana_penales_pronostico": None
        }, # ❌ Erró todo (0 pts)
        # TOTAL ESTIMADO COTI: 6 + 3 + 9 + 0 = 18 pts

        # --- Pronósticos de Vale ---
        {
            "user_id": user_vale, "partido_id": 1, 
            "goles_pronostico_1": 1, "goles_pronostico_2": 0, "gana_penales_pronostico": None
        }, # ⚽ Ganador simple (3 pts)
        {
            "user_id": user_vale, "partido_id": 2, 
            "goles_pronostico_1": 1, "goles_pronostico_2": 1, "gana_penales_pronostico": None
        }, # ✅ Empate exacto Grupos (6 pts)
        {
            "user_id": user_vale, "partido_id": 3, 
            "goles_pronostico_1": 1, "goles_pronostico_2": 1, "gana_penales_pronostico": "Italia"
        }, # 🛑 Eliminatoria: Empate no exacto + Erró Penales (3 pts)
        {
            "user_id": user_vale, "partido_id": 4, 
            "goles_pronostico_1": 3, "goles_pronostico_2": 1, "gana_penales_pronostico": None
        }, # 🔥 Parcial: Ganador + goles exactos de Inglaterra (4 pts)
        # TOTAL ESTIMADO VALE: 3 + 6 + 3 + 4 = 16 pts

        # --- Pronósticos de Guada ---
        {
            "user_id": user_guada, "partido_id": 1, 
            "goles_pronostico_1": 0, "goles_pronostico_2": 3, "gana_penales_pronostico": None
        }, # ❌ Erró todo (0 pts)
        {
            "user_id": user_guada, "partido_id": 2, 
            "goles_pronostico_1": 3, "goles_pronostico_2": 0, "gana_penales_pronostico": None
        }, # ❌ Erró todo (0 pts)
        {
            "user_id": user_guada, "partido_id": 3, 
            "goles_pronostico_1": 0, "goles_pronostico_2": 0, "gana_penales_pronostico": "España"
        }, # 🎯 Eliminatoria: Empate no exacto + Acertó Penales (6 pts)
        {
            "user_id": user_guada, "partido_id": 4, 
            "goles_pronostico_1": 3, "goles_pronostico_2": 0, "gana_penales_pronostico": None
        }  # ✅ PLENO EXACTO (6 pts)
        # TOTAL ESTIMADO GUADA: 0 + 0 + 6 + 6 = 12 pts
    ]

    print("Inserting pronósticos...")
    supabase.table("pronosticos").upsert(pronosticos_prueba, on_conflict="user_id,partido_id").execute()

    print("Simulando cierre del torneo...")
    supabase.table("constantes_torneo").upsert({"id": 1, "campeon_real": "Argentina", "subcampeon_real": "Francia"}).execute()
    
    print("✨ ¡Simulación completada con éxito!")

if __name__ == "__main__":
    simular_datos_prode()