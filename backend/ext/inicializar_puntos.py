import os
import sys

# 🚀 TRUCO DE PATHS: Encontramos la raíz del backend e inyectamos en sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Ahora que Python ya sabe dónde mirar, los imports van a andar sin chistar
from dotenv import load_dotenv
from supabase import create_client, Client
from app.utils.points_calc import calcular_puntos_prode_complejo

PATH_ENV = os.path.join(BASE_DIR, ".env")
print(f"🔍 Buscando archivo de configuración en: {PATH_ENV}")
load_dotenv(PATH_ENV)

# Leemos las variables nativas del backend
SUPABASE_URL = os.getenv("SUPABASE_URL") or os.getenv("VITE_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print(f"❌ Error: No se encontraron las credenciales en {PATH_ENV}")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_all_rows(table_name: str, select_str: str = "*", filtros: dict = None):
    all_rows = []
    page_size = 1000
    start = 0
    while True:
        query = supabase.table(table_name).select(select_str)
        if filtros:
            for col, val in filtros.items():
                query = query.eq(col, val)
        res = query.range(start, start + page_size - 1).execute()
        chunk = res.data
        if not chunk:
            break
        all_rows.extend(chunk)
        if len(chunk) < page_size:
            break
        start += page_size
    return all_rows

def inicializar_puntos_totales():
    print("⏳ Iniciando recalculación histórica de puntos...")
    try:
        # A. Traer partidos que ya terminaron (FINISHED)
        partidos = fetch_all_rows("partidos", filtros={"estado": "FINISHED"})
        partidos_dict = {int(p["id_api"]): p for p in partidos}
        print(f"🏟️  Se encontraron {len(partidos)} partidos finalizados.")

        # B. Traer TODOS los pronósticos y perfiles
        pronosticos = fetch_all_rows("pronosticos")
        usuarios = fetch_all_rows("profiles", select_str="id, username, campeon_prediccion, subcampeon_prediccion")
        print(f"👥 Se procesarán {len(usuarios)} usuarios y {len(pronosticos)} pronósticos.")

        # C. Traer los resultados reales de campeon/subcampeon de las constantes
        constantes_res = supabase.table("constantes_torneo").select("campeon_real, subcampeon_real").eq("id", 1).execute()
        campeon_real = constantes_res.data[0].get("campeon_real") if constantes_res.data else None
        subcampeon_real = constantes_res.data[0].get("subcampeon_real") if constantes_res.data else None

        # D. Estructura temporal para acumular los puntos en memoria
        ranking_local = {u["id"]: {"username": u["username"], "puntos": 0} for u in usuarios}

        # E. Sumar puntos por partidos jugados
        for prono in pronosticos:
            p_id = int(prono["partido_id"])
            u_id = prono["user_id"]

            if p_id not in partidos_dict or u_id not in ranking_local:
                continue

            partido = partidos_dict[p_id]

            puntos = calcular_puntos_prode_complejo(
                prono_1=prono.get("goles_pronostico_1"),
                prono_2=prono.get("goles_pronostico_2"),
                p_avanza=prono.get("gana_penales_pronostico"),
                real_1=partido.get("goles_real_1"),
                real_2=partido.get("goles_real_2"),
                r_avanza=partido.get("ganador_penales_real"),
                instancia=partido.get("instancia")
            )
            ranking_local[u_id]["puntos"] += puntos

        # F. Sumar puntos extras finales (Campeón / Subcampeón)
        for u in usuarios:
            u_id = u["id"]
            if u_id not in ranking_local:
                continue
            
            if campeon_real and u.get("campeon_prediccion") == campeon_real:
                ranking_local[u_id]["puntos"] += 10
                
            if subcampeon_real and u.get("subcampeon_prediccion") == subcampeon_real:
                ranking_local[u_id]["puntos"] += 5

        # G. IMPACTAR EN LA BASE DE DATOS USER POR USER
        print("\n🚀 Actualizando columna 'puntos_totales' en Supabase...")
        print("-" * 50)
        
        for u_id, datos in ranking_local.items():
            pts_finales = datos["puntos"]
            username = datos["username"]
            
            # Hacemos el update directo sobre la fila del perfil
            supabase.table("profiles").update({"puntos_totales": pts_finales}).eq("id", u_id).execute()
            print(f"✅ {username:<15} -> {pts_finales} pts guardados en base de datos.")

        print("-" * 50)
        print("🎉 ¡Sincronización histórica completada con éxito! Todos los perfiles quedaron al día.")

    except Exception as e:
        print(f"❌ Error durante la inicialización: {e}")

if __name__ == "__main__":
    inicializar_puntos_totales()