from fastapi import APIRouter, HTTPException # type: ignore
from app.services.football_api import FootballAPIService
from app.database import supabase
from app.utils.points_calc import calcular_puntos_prode_complejo
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel

# Creamos el router que después se va a acoplar al main.py
router = APIRouter(
    prefix="/api/partidos",
    tags=["Partidos"]
)

# Inicializamos el servicio de la API de fútbol afuera para reutilizarlo
football_service = FootballAPIService()

def fetch_all_rows(table_name: str, select_str: str = "*", filtros: dict = None):
    """
    Supabase/PostgREST devuelve como máximo 1000 filas por consulta por default.
    Esta función pagina con .range() hasta traer la tabla completa.
    """
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

class PronosticoSchema(BaseModel):
    partido_id: str
    user_id: str
    goles_pronostico_1: int
    goles_pronostico_2: int
    gana_penales_pronostico: str = None


# ENDPOINT 1
@router.post("/sincronizar")
def sincronizar_fixture():
    """
    Trae los partidos de la API externa. Si detecta que un partido terminó 
    y localmente no estaba FINISHED, calcula los puntos e incrementa 'puntos_totales'.
    """
    try:
        partidos_api = football_service.obtener_fixture_mundial()
        if not partidos_api:
            raise HTTPException(status_code=502, detail="No se pudieron obtener partidos de la API externa.")

        # 1. Traemos cómo están los partidos guardados localmente para comparar estados
        partidos_locales = fetch_all_rows("partidos", select_str="id_api,estado")
        estados_locales = {str(p["id_api"]): p["estado"] for p in partidos_locales}

        # 2. Buscamos qué usuarios hay en el sistema y sus pronósticos
        usuarios = fetch_all_rows("profiles", select_str="id")
        
        # Procesamos cada partido que viene de la API externa
        for p_api in partidos_api:
            p_id = str(p_api["id_api"])
            estado_nuevo = p_api["estado"]
            estado_viejo = estados_locales.get(p_id)

            if estado_nuevo == "FINISHED" and estado_viejo != "FINISHED":
                print(f"⚽ ¡Partido Finalizado Detectado! Calculando puntos para el partido ID {p_id}...")
                pronos_partido = fetch_all_rows("pronosticos", filtros={"partido_id": p_id})
                pronos_dict = {prono["user_id"]: prono for prono in pronos_partido}

                for u in usuarios:
                    u_id = u["id"]
                    prono = pronos_dict.get(u_id)
                    if not prono:
                        continue

                    puntos_ganados = calcular_puntos_prode_complejo(
                        prono_1=prono.get("goles_pronostico_1"),
                        prono_2=prono.get("goles_pronostico_2"),
                        p_avanza=prono.get("gana_penales_pronostico"),
                        real_1=p_api.get("goles_real_1"),
                        real_2=p_api.get("goles_real_2"),
                        r_avanza=p_api.get("ganador_penales_real"),
                        instancia=p_api.get("instancia")
                    )

                    # SOLUCIÓN CONDICIÓN DE CARRERA: Hacemos un UPDATE idempotente
                    # No importa si 5 hilos corren esto al mismo tiempo, el valor final será el mismo.
                    supabase.table("pronosticos").update({
                        "puntos_ganados": puntos_ganados
                    }).eq("user_id", u_id).eq("partido_id", p_id).execute()
                    
                    if puntos_ganados > 0:
                        print(f"   > {puntos_ganados} pts guardados para {u_id}")

                # 🔒 Lo marcamos como procesado YA, antes de pasar al próximo partido
                supabase.table("partidos").upsert(p_api, on_conflict="id_api").execute()

        # Upsert general solo para partidos no finalizados (los FINISHED ya se procesaron arriba)
        partidos_no_finalizados = [p for p in partidos_api if p["estado"] != "FINISHED"]
        supabase.table("partidos").upsert(partidos_no_finalizados, on_conflict="id_api").execute()
        return {
            "status": "success",
            "message": f"Se sincronizaron {len(partidos_no_finalizados)} partidos activos. Se procesaron los puntos acumulados de los partidos finalizados."
        }
    except Exception as e:
        print(f"❌ Error en sincronizar_fixture: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ENDPOINT 2
@router.post("/votar")
def guardar_o_modificar_pronostico(payload: PronosticoSchema):
    """
    Guarda o actualiza un pronóstico con restricción estricta de tiempo (5 minutos antes).
    """
    try:
        partido_res = supabase.table("partidos").select("fecha").eq("id_api", payload.partido_id).single().execute()
        partido = partido_res.data
        
        if not partido:
            raise HTTPException(status_code=404, detail="El partido especificado no existe.")

        fecha_partido = datetime.fromisoformat(partido["fecha"].replace("Z", "+00:00"))
        limite_voto = fecha_partido - timedelta(minutes=5)
        ahora = datetime.now(timezone.utc)

        if ahora >= limite_voto:
            raise HTTPException(
                status_code=400, 
                detail="🔒 Votación cerrada: Solo podés guardar o modificar hasta 5 minutos antes del inicio oficial del partido."
            )

        voto_dict = {
            "user_id": payload.user_id,
            "partido_id": payload.partido_id,
            "goles_pronostico_1": payload.goles_pronostico_1,
            "goles_pronostico_2": payload.goles_pronostico_2,
            "gana_penales_pronostico": payload.gana_penales_pronostico
        }

        res = supabase.table("pronosticos").upsert(voto_dict, on_conflict="user_id,partido_id").execute()
        return {"status": "success", "message": "Pronóstico guardado correctamente.", "data": res.data}

    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"❌ Error en guardar_o_modificar_pronostico: {e}")
        raise HTTPException(status_code=500, detail=f"Error al procesar el voto: {str(e)}")


# ENDPOINT 3 (EL QUE QUERÍAS REFORZAR)
@router.get("/tabla-posiciones")
def obtener_tabla_posiciones():
    try:
        # 1. Traer valores reales
        constantes_res = supabase.table("constantes_torneo")\
            .select("campeon_real,subcampeon_real")\
            .eq("id", 1)\
            .single()\
            .execute()
        
        campeon_real = constantes_res.data.get("campeon_real") if constantes_res.data else None
        subcampeon_real = constantes_res.data.get("subcampeon_real") if constantes_res.data else None

        # 🚨 DEBUG: Imprimimos qué trajo de la tabla constantes_torneo
        print(f"🏆 REALES -> Campeón: '{campeon_real}' | Subcampeón: '{subcampeon_real}'")

        # 2. Traer ranking base
        usuarios_res = supabase.table("ranking_posiciones")\
            .select("username,puntos_totales")\
            .execute()

        # 3. Traer predicciones
        perfiles_res = supabase.table("profiles")\
            .select("username,campeon_prediccion,subcampeon_prediccion")\
            .execute()

        predicciones_dict = {
            p["username"]: p 
            for p in perfiles_res.data if p.get("username")
        }

        # 4. Procesar y sumar
        ranking_final = []
        for u in usuarios_res.data:
            username = u["username"]
            pts = u.get("puntos_totales", 0)
            if pts is None: # Por si viene un nulo
                pts = 0
                
            pred = predicciones_dict.get(username, {})
            pred_camp = pred.get("campeon_prediccion")
            pred_sub = pred.get("subcampeon_prediccion")

            # 🚨 DEBUG: Imprimimos qué votó cada usuario
            print(f"👤 {username} -> Votó Campeón: '{pred_camp}' | Votó Subcampeón: '{pred_sub}' | Puntos Base: {pts}")

            bonus = 0
            # Usamos .strip().lower() para evitar problemas de mayúsculas o espacios extra
            if campeon_real and pred_camp and campeon_real.strip().lower() == pred_camp.strip().lower():
                bonus += 10
                print(f"   ✅ ¡Acertó campeón! +10 puntos")
                
            if subcampeon_real and pred_sub and subcampeon_real.strip().lower() == pred_sub.strip().lower():
                bonus += 5
                print(f"   ✅ ¡Acertó subcampeón! +5 puntos")
            
            ranking_final.append({"username": username, "puntos": pts + bonus})

        ranking_ordenado = sorted(ranking_final, key=lambda x: x["puntos"], reverse=True)
        return {"status": "success", "data": ranking_ordenado}

    except Exception as e:
        print(f"❌ Error en tabla-posiciones: {e}")
        raise HTTPException(status_code=500, detail=f"Error al traer posiciones: {str(e)}")

@router.get("/{partido_id}/pronosticos-grupo")
def obtener_pronosticos_grupo(partido_id: int):
    """
    Devuelve los pronósticos de todos los usuarios para un partido específico.
    """
    try:
        res = supabase.table("pronosticos") \
            .select("goles_pronostico_1,goles_pronostico_2,gana_penales_pronostico,user_id,profiles(username)") \
            .eq("partido_id", partido_id) \
            .execute()
            
        votos = []
        for item in res.data:
            profile = item.get("profiles", {})
            votos.append({
                "user_id": item.get("user_id"),
                "username": profile.get("username", "Anon"),
                "g1": item.get("goles_pronostico_1"),
                "g2": item.get("goles_pronostico_2"),
                "avanza": item.get("gana_penales_pronostico")
            })
            
        return {"status": "success", "data": votos}
    except Exception as e:
        print(f"❌ Error al traer pronósticos del grupo: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    

    # ENDPOINT 4: Recálculo manual
@router.post("/recalcular-puntos")
def recalcular_puntos_historicos():
    """
    Recalcula los puntos de todos los pronósticos para los partidos que ya están finalizados (FINISHED).
    Ideal para correr manualmente desde Swagger si hubo algún cambio en la lógica de puntajes.
    """
    try:
        print("🚀 Iniciando el recálculo de puntos históricos desde el endpoint...")
        
        # 1. Traemos solo los partidos que ya terminaron (estado FINISHED)
        partidos_finalizados = fetch_all_rows("partidos", filtros={"estado": "FINISHED"})
        print(f"Se encontraron {len(partidos_finalizados)} partidos finalizados.")
        
        # Contador para tener un resumen al final
        total_pronosticos_actualizados = 0

        for partido in partidos_finalizados:
            p_id = str(partido["id_api"])
            print(f"\nProcesando partido {p_id} ({partido.get('equipo_1', 'Local')} vs {partido.get('equipo_2', 'Visitante')})...")
            
            # 2. Traemos todos los pronósticos para este partido específico
            pronosticos = fetch_all_rows("pronosticos", filtros={"partido_id": p_id})
            
            for prono in pronosticos:
                # 3. Calculamos los puntos con tu lógica exacta
                puntos_reales = calcular_puntos_prode_complejo(
                    prono_1=prono.get("goles_pronostico_1"),
                    prono_2=prono.get("goles_pronostico_2"),
                    p_avanza=prono.get("gana_penales_pronostico"),
                    real_1=partido.get("goles_real_1"),
                    real_2=partido.get("goles_real_2"),
                    r_avanza=partido.get("ganador_penales_real"),
                    instancia=partido.get("instancia")
                )
                
                # 4. Actualizamos la fila específica de ese pronóstico con el puntaje corregido
                supabase.table("pronosticos") \
                    .update({"puntos_ganados": puntos_reales}) \
                    .eq("user_id", prono["user_id"]) \
                    .eq("partido_id", p_id) \
                    .execute()
                    
                total_pronosticos_actualizados += 1
                
        print("\n✅ ¡Recálculo completado con éxito! La columna 'puntos_ganados' ahora es 100% confiable.")
        
        return {
            "status": "success",
            "message": "¡Recálculo completado con éxito!",
            "data": {
                "partidos_procesados": len(partidos_finalizados),
                "pronosticos_actualizados": total_pronosticos_actualizados
            }
        }

    except Exception as e:
        print(f"❌ Error al recalcular puntos: {e}")
        raise HTTPException(status_code=500, detail=f"Error en el recálculo: {str(e)}")