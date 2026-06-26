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
    Endpoint manual para traer todo el fixture inicial o forzar recarga.
    """
    try:
        partidos_api = football_service.obtener_fixture_mundial()
        if not partidos_api:
            raise HTTPException(status_code=502, detail="No se pudieron obtener partidos de la API externa.")

        supabase.table("partidos").upsert(partidos_api, on_conflict="id_api").execute()

        return {
            "status": "success",
            "message": f"Se sincronizaron {len(partidos_api)} partidos exitosamente en Supabase.",
            "cantidad": len(partidos_api)
        }
    except Exception as e:
        print(f"❌ Error en sincronizar_fixture: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


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
    """
    Sincronización reactiva 'On-Demand' con candado de 2 minutos.
    Filtra los partidos para actualizar ÚNICAMENTE los que no están finalizados localmente.
    """
    try:
        constantes_res = supabase.table("constantes_torneo").select("*").eq("id", 1).execute()
        ahora = datetime.now(timezone.utc)
        necesita_sincronizar = False

        if constantes_res.data and len(constantes_res.data) > 0:
            constantes = constantes_res.data[0]
            ultima_sincro_str = constantes.get("ultima_sincronizacion")
            
            if ultima_sincro_str:
                ultima_sincro = datetime.fromisoformat(ultima_sincro_str.replace("Z", "+00:00"))
                print(f"⏰ HORA ACTUAL (UTC): {ahora}")
                print(f"📅 ÚLTIMA SINCRO EN BDD: {ultima_sincro}")
                print(f"⏱️ TIEMPO TRANSCURRIDO: {ahora - ultima_sincro}")                
                # 🚀 Candado corto de 2 minutos para evitar saturación por ráfagas
                if ahora - ultima_sincro > timedelta(minutes=2):
                    necesita_sincronizar = True
            else:
                necesita_sincronizar = True
        else:
            necesita_sincronizar = True

        # 🔄 Sincronización inteligente bajo demanda
        if necesita_sincronizar:
            print("⏳ Candado vencido. Sincronizando partidos activos con la API externa...")
            try:
                # 1. Buscamos qué IDs ya tenemos cerrados/finalizados en Supabase
                partidos_finalizados = supabase.table("partidos").select("id_api").eq("estado", "FINISHED").execute()
                ids_finalizados = {int(p["id_api"]) for p in partidos_finalizados.data}

                # 2. Traemos el fixture fresco completo de la API de fútbol
                partidos_api = football_service.obtener_fixture_mundial()
                
                if partidos_api:
                    # 🚀 FILTRO ESTRATÉGICO: Mandamos al upsert únicamente los activos
                    partidos_activos_a_actualizar = [
                        p for p in partidos_api 
                        if int(p["id_api"]) not in ids_finalizados
                    ]

                    if partidos_activos_a_actualizar:
                        supabase.table("partidos").upsert(partidos_activos_a_actualizar, on_conflict="id_api").execute()
                        print(f"✅ Se actualizaron {len(partidos_activos_a_actualizar)} partidos activos.")
                    else:
                        print("🤷‍♂️ No hay partidos activos nuevos por impactar.")
                    
                    # Guardamos el registro del candado temporal global
                    supabase.table("constantes_torneo").update({"ultima_sincronizacion": ahora.isoformat()}).eq("id", 1).execute()
            
            except Exception as api_err:
                print(f"⚠️ No se pudo auto-sincronizar (API externa caída o sin saldo): {api_err}")

        # -------------------------------------------------------------------------
        # PROCESAMIENTO GENERAL DEL RANKING
        # -------------------------------------------------------------------------
        partidos = fetch_all_rows("partidos", filtros={"estado": "FINISHED"})
        partidos_dict = {int(p["id_api"]): p for p in partidos}

        pronosticos = fetch_all_rows("pronosticos")
        usuarios = fetch_all_rows("profiles", select_str="id, username, campeon_prediccion, subcampeon_prediccion")
        
        constantes_res = supabase.table("constantes_torneo").select("campeon_real, subcampeon_real").eq("id", 1).execute()
        campeon_real = None
        subcampeon_real = None

        if constantes_res.data and len(constantes_res.data) > 0:
            campeon_real = constantes_res.data[0].get("campeon_real")
            subcampeon_real = constantes_res.data[0].get("subcampeon_real")

        ranking = {u["id"]: {"username": u["username"], "puntos": 0} for u in usuarios}

        for prono in pronosticos:
            p_id = int(prono["partido_id"])
            u_id = prono["user_id"]

            if p_id not in partidos_dict or u_id not in ranking:
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
            ranking[u_id]["puntos"] += puntos

        for u in usuarios:
            u_id = u["id"]
            if u_id not in ranking:
                continue
            
            if campeon_real and u.get("campeon_prediccion") == campeon_real:
                ranking[u_id]["puntos"] += 10
                
            if subcampeon_real and u.get("subcampeon_prediccion") == subcampeon_real:
                ranking[u_id]["puntos"] += 5

        ranking_ordenado = sorted(ranking.values(), key=lambda x: x["puntos"], reverse=True)
        return {"status": "success", "data": ranking_ordenado}

    except Exception as e:
        print(f"❌ Error en obtener_tabla_posiciones: {e}")
        raise HTTPException(status_code=500, detail=f"Error al procesar el ranking de posiciones: {str(e)}")


@router.get("/{partido_id}/pronosticos-grupo")
def obtener_pronosticos_grupo(partido_id: int):
    """
    Devuelve los pronósticos de todos los usuarios para un partido específico.
    """
    try:
        res = supabase.table("pronosticos") \
            .select("goles_pronostico_1, goles_pronostico_2, gana_penales_pronostico, user_id, profiles(username)") \
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