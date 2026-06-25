import os
from dotenv import load_dotenv
from supabase import create_client, Client

# 1. Cargar variables de entorno locales
load_dotenv(".env.local")

SUPABASE_URL = os.getenv("VITE_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Error: No se encontraron SUPABASE_URL o SUPABASE_KEY")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# =========================================================================
# ⚙️ CONFIGURACIÓN: Pegá acá el UUID del usuario que querés auditar
# =========================================================================
USER_ID_A_AUDITAR = "41add92c-6c78-4651-9312-902cdac68e6b" 
# =========================================================================

def calcular_puntos_prode_motor(prono_1, prono_2, p_avanza, real_1, real_2, r_avanza, instancia):
    """ El mismo motor matemático exacto con el fix de consuelo """
    if prono_1 is None or prono_2 is None or real_1 is None or real_2 is None:
        return 0
    t_real = 1 if real_1 > real_2 else (-1 if real_1 < real_2 else 0)
    t_prono = 1 if prono_1 > prono_2 else (-1 if prono_1 < prono_2 else 0)

    if t_real == 0:
        if t_prono == 0:
            if instancia == "GROUP_STAGE":
                return 6 if prono_1 == real_1 else 3
            else:
                es_exacto = (prono_1 == real_1)
                acerto_penales = (p_avanza == r_avanza and r_avanza is not None)
                if es_exacto and acerto_penales: return 9
                if es_exacto and not acerto_penales: return 6
                if not es_exacto and acerto_penales: return 6
                if not es_exacto and not acerto_penales: return 3
    else:
        if t_real == t_prono:
            if prono_1 == real_1 and prono_2 == real_2: return 6
            if prono_1 == real_1 or prono_2 == real_2: return 4
            return 3

    if prono_1 == real_1 or prono_2 == real_2:
        return 1
    return 0

def auditar_usuario(user_id):
    print(f"⏳ Buscando historial del usuario en Supabase...")
    try:
        # A. Traer el perfil del usuario para saber el nombre
        user_res = supabase.table("profiles").select("*").eq("id", user_id).single().execute()
        if not user_res.data:
            print(f"❌ Error: No se encontró ningún usuario con el ID: {user_id}")
            return
        username = user_res.data.get("username", "Sin nombre")

        # B. Traer TODOS los partidos terminados (Quitamos el .order conflictivo)
        partidos_res = supabase.table("partidos").select("*").eq("estado", "FINISHED").execute()
        if not partidos_res.data:
            print("📅 No hay partidos terminados (FINISHED) en la base de datos todavía.")
            return

        # 🚀 SOLUCIÓN DEFINITIVA: Ordenamos en memoria nativamente usando Python
        partidos_ordenados = sorted(partidos_res.data, key=lambda x: x.get("fecha", ""))

        # C. Traer los pronósticos de este usuario específico
        print(f"🔍 Ejecutando consulta de pronósticos para el UUID: {user_id}...")
        pronos_res = supabase.table("pronosticos").select("*").eq("user_id", user_id).execute()
        
        print(f"📊 Cantidad de pronósticos devueltos por Supabase: {len(pronos_res.data)}")

        # 🚀 NORMALIZACIÓN TOTAL: Forzamos a que la clave del diccionario sea un entero puro (int)
        pronos_dict = {int(prono["partido_id"]): prono for prono in pronos_res.data}

        # D. Traer constantes del torneo para el bónus de campeón
        constantes_res = supabase.table("constantes_torneo").select("*").eq("id", 1).single().execute()
        campeon_real = constantes_res.data.get("campeon_real") if constantes_res.data else None
        subcampeon_real = constantes_res.data.get("subcampeon_real") if constantes_res.data else None

        # -------------------------------------------------------------------------
        # IMPRESIÓN DEL REPORTE EN TERMINAL
        # -------------------------------------------------------------------------
        print("\n" + "="*85)
        print(f"🕵️‍♂️  AUDITORÍA DE VOTOS: {username.upper()} ")
        print("="*85)
        print(f"{'Partido':<30} | {'Tu Voto':<10} | {'Real':<10} | {'Puntos Ganados':<15}")
        print("-"*85)

        acumulado_partidos = 0

        for partido in partidos_ordenados:
            # 🚀 NORMALIZACIÓN DEL BUSCADOR: Forzamos también a entero el id del partido real
            p_id_int = int(partido["id_api"])
            enfrentamiento = f"{partido['equipo_1']} vs {partido['equipo_2']}"
            
            res_real_str = f"{partido['goles_real_1']}-{partido['goles_real_2']}"
            if partido.get("ganador_penales_real"):
                res_real_str += f" ({partido['ganador_penales_real'][:3]}. 🏆)"

            # Buscamos usando el entero forzado
            prono = pronos_dict.get(p_id_int)

            if prono:
                res_voto_str = f"{prono['goles_pronostico_1']}-{prono['goles_pronostico_2']}"
                if prono.get("gana_penales_pronostico"):
                    res_voto_str += f" ({prono['gana_penales_pronostico'][:3]}. 🏆)"

                # Calculamos el puntaje de este partido
                pts = calcular_puntos_prode_motor(
                    prono_1=prono.get("goles_pronostico_1"),
                    prono_2=prono.get("goles_pronostico_2"),
                    p_avanza=prono.get("gana_penales_pronostico"),
                    real_1=partido.get("goles_real_1"),
                    real_2=partido.get("goles_real_2"),
                    r_avanza=partido.get("ganador_penales_real"),
                    instancia=partido.get("instancia")
                )
            else:
                res_voto_str = "No votó ❌"
                pts = 0

            acumulado_partidos += pts
            print(f"{enfrentamiento:<30} | {res_voto_str:<10} | {res_real_str:<10} | +{pts} pts")

        # E. Cómputo de puntos extra finales
        print("-"*85)
        pts_extras = 0
        voto_camp = user_res.data.get("campeon_prediccion")
        voto_sub = user_res.data.get("subcampeon_prediccion")

        print(f"🥇 Predicción Campeón:    {str(voto_camp):<15} | Real: {str(campeon_real):<12}")
        if campeon_real and voto_camp == campeon_real:
            print(f"{'':<61} | +10 pts 🔥")
            pts_extras += 10

        print(f"🥈 Predicción Subcampeón: {str(voto_sub):<15} | Real: {str(subcampeon_real):<12}")
        if subcampeon_real and voto_sub == subcampeon_real:
            print(f"{'':<61} | +5 pts  🔥")
            pts_extras += 5

        # F. Cierre Total
        total_final = acumulado_partidos + pts_extras
        print("="*85)
        print(f"📊 RESUMEN FINAL DE {username.upper()}:")
        print(f"   • Puntos en partidos: {acumulado_partidos} pts")
        print(f"   • Puntos por extras:   {pts_extras} pts")
        print(f"   🚀 PUNTAJE NETO TOTAL: {total_final} pts")
        print("="*85 + "\n")

    except Exception as e:
        print(f"❌ Error durante la auditoría: {e}")

if __name__ == "__main__":
    if USER_ID_A_AUDITAR == "TU-UUID-DE-SUPERBASE-AQUÍ":
        print("💡 Por favor, reemplazá 'USER_ID_A_AUDITAR' con un UUID válido de tu tabla profiles.")
    else:
        auditar_usuario(USER_ID_A_AUDITAR)