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
        partidos_locales = fetch_all_rows("partidos", select_str="id_api, estado")
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

                    if puntos_ganados > 0:
                        supabase.rpc("incrementar_puntos_usuario", {"user_id_param": u_id, "puntos_incremento": puntos_ganados}).execute()
                        print(f"   > +{puntos_ganados} pts aplicados a {u_id}")

                # 🔒 Lo marcamos como procesado YA, antes de pasar al próximo partido
                supabase.table("partidos").upsert(p_api, on_conflict="id_api").execute()

        # Upsert general para mantener actualizados estados en vivo, fechas, etc.
        supabase.table("partidos").upsert(partidos_api, on_conflict="id_api").execute()
        return {
            "status": "success",
            "message": f"Se sincronizaron {len(partidos_api)} partidos. Se procesaron los puntos acumulados de los partidos finalizados."
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
    """
    Retorna el ranking leyendo directamente de 'puntos_totales' en la tabla profiles.
    Mantiene la auto-sincronización On-Demand por si hay partidos en juego.
    """
    try:
        # 1. Mantenemos tu sincronización On-Demand (Llama al endpoint de arriba internamente)
        constantes_res = supabase.table("constantes_torneo").select("*").eq("id", 1).execute()
        ahora = datetime.now(timezone.utc)
        necesita_sincronizar = False

        if constantes_res.data and len(constantes_res.data) > 0:
            constantes = constantes_res.data[0]
            ultima_sincro_str = constantes.get("ultima_sincronizacion")
            if ultima_sincro_str:
                ultima_sincro = datetime.fromisoformat(ultima_sincro_str.replace("Z", "+00:00"))
                if ahora - ultima_sincro > timedelta(minutes=2):
                    necesita_sincronizar = True
            else:
                necesita_sincronizar = True
        else:
            necesita_sincronizar = True

        # Si el candado venció, cerramos el candado INMEDIATAMENTE en la BDD y sincronizamos
        if necesita_sincronizar:
            supabase.table("constantes_torneo").update({"ultima_sincronizacion": ahora.isoformat()}).eq("id", 1).execute()
            sincronizar_fixture()

        # 2. 🚀 LA MAGIA: Traemos los usuarios ordenados directamente por su puntaje acumulado
        # Modificá 'puntos_totales' por el nombre exacto de tu columna si cambia en Postgres
        usuarios_res = supabase.table("profiles")\
            .select("username, puntos_totales")\
            .order("puntos_totales", desc=True)\
            .execute()

        # Moldeamos la respuesta para que tu Frontend (TablaPuntos.jsx) la lea sin enterarse del cambio
        ranking_ordenado = [
            {"username": u["username"], "puntos": u.get("puntos_totales", 0)}
            for u in usuarios_res.data
        ]

        return {"status": "success", "data": ranking_ordenado}

    except Exception as e:
        print(f"❌ Error en obtener_tabla_posiciones simplificado: {e}")
        raise HTTPException(status_code=500, detail=f"Error al traer posiciones: {str(e)}")

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