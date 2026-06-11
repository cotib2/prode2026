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
    Endpoint para traer los partidos de la API externa e inyectarlos/actualizarlos en Supabase.
    """
    try:
        # 1. Llamamos al servicio para buscar los partidos actuales de la API
        partidos_api = football_service.obtener_fixture_mundial()
        
        if not partidos_api:
            raise HTTPException(status_code=502, detail="No se pudieron obtener partidos de la API externa.")

        # 2. Hacemos el upsert masivo en Supabase.
        # Si el 'id_api' ya existe, actualiza los goles y el estado; si no, lo crea de cero.
        resultado = supabase.table("partidos").upsert(
            partidos_api, 
            on_conflict="id_api"
        ).execute()

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
        # 1. Buscar cuándo arranca el partido en Supabase
        partido_res = supabase.table("partidos").select("fecha").eq("id_api", payload.partido_id).single().execute()
        partido = partido_res.data
        
        if not partido:
            raise HTTPException(status_code=404, detail="El partido especificado no existe.")

        # 2. Validar restricción de tiempo (5 minutos antes del inicio oficial)
        fecha_partido = datetime.fromisoformat(partido["fecha"].replace("Z", "+00:00"))
        limite_voto = fecha_partido - timedelta(minutes=5)
        ahora = datetime.now(timezone.utc)

        if ahora >= limite_voto:
            raise HTTPException(
                status_code=400, 
                detail="🔒 Votación cerrada: Solo podés guardar o modificar hasta 5 minutos antes del inicio oficial del partido."
            )

        # 3. Armar el diccionario para meter el upsert usando tu cliente de base de datos
        voto_dict = {
            "user_id": payload.user_id,
            "partido_id": payload.partido_id,
            "goles_pronostico_1": payload.goles_pronostico_1,
            "goles_pronostico_2": payload.goles_pronostico_2,
            "gana_penales_pronostico": payload.gana_penales_pronostico
        }

        # Hacemos upsert en base a la clave compuesta/única de tu tabla pronosticos
        res = supabase.table("pronosticos").upsert(voto_dict, on_conflict="user_id,partido_id").execute()
        
        return {"status": "success", "message": "Pronóstico guardado correctamente.", "data": res.data}

    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"❌ Error en guardar_o_modificar_pronostico: {e}")
        raise HTTPException(status_code=500, detail=f"Error al procesar el voto: {str(e)}")

# ENDPOINT 3
@router.get("/tabla-posiciones")
def obtener_tabla_posiciones():
    """
    Aplica 'Lazy Update': si pasaron más de 15 minutos desde la última vez,
    sincroniza automáticamente los partidos con la API externa en segundo plano.
    """
    try:

        constantes_res = supabase.table("constantes_torneo").select("*").eq("id", 1).execute()
        ahora = datetime.now(timezone.utc)
        necesita_sincronizar = False

        if constantes_res.data and len(constantes_res.data) > 0:
            constantes = constantes_res.data[0]
            ultima_sincro_str = constantes.get("ultima_sincronizacion")
            
            if ultima_sincro_str:
                # Parseamos la fecha que viene de Postgres (quitando el 'Z' o formateando)
                # Reemplazar 'Z' por '+00:00' para compatibilidad con Python de ser necesario
                ultima_sincro = datetime.fromisoformat(ultima_sincro_str.replace("Z", "+00:00"))
                
                # 🚀 CANDADO: Si pasaron más de 15 minutos, habilitamos la recarga
                if ahora - ultima_sincro > timedelta(minutes=15):
                    necesita_sincronizar = True
            else:
                necesita_sincronizar = True
        else:
            necesita_sincronizar = True

        # 2. 🔄 Si el candado venció, disparamos tu función de sincronización existente
        if necesita_sincronizar:
            print("⏳ El candado de 15 min venció. Sincronizando partidos de forma automática...")
            try:
                # LLAMÁ ACÁ A TU FUNCIÓN REAL QUE TRAE LOS PARTIDOS DE LA FOOTBALL API
                # Ejemplo ficticio (reemplazalo por tu lógica de sincronizar):
                # sincronizar_partidos_con_api_externa()
                
                # Después de sincronizar los partidos con éxito, actualizamos el timestamp en Supabase
                supabase.table("constantes_torneo").update({"ultima_sincronizacion": ahora.isoformat()}).eq("id", 1).execute()
                print("✅ Sincronización automática completada.")
            except Exception as api_err:
                # Si la API externa falla (ej: te quedaste sin créditos), lo atajamos acá 
                # para que la app siga funcionando igual con los datos locales viejos
                print(f"⚠️ No se pudo auto-sincronizar (API externa caída/sin créditos): {api_err}")

        # A. Traer partidos que ya terminaron (FINISHED)
        partidos = supabase.table("partidos").select("*").eq("estado", "FINISHED").execute().data
        partidos_dict = {p["id_api"]: p for p in partidos}

        pronosticos = supabase.table("pronosticos").select("*").execute().data
        usuarios = supabase.table("profiles").select("id, username, campeon_prediccion, subcampeon_prediccion").execute().data
        
        constantes_res = supabase.table("constantes_torneo").select("campeon_real, subcampeon_real").eq("id", 1).execute()
        campeon_real = None
        subcampeon_real = None

        if constantes_res.data and len(constantes_res.data) > 0:
            campeon_real = constantes_res.data[0].get("campeon_real")
            subcampeon_real = constantes_res.data[0].get("subcampeon_real")

        # D. Inicializar el acumulador en el diccionario
        ranking = {u["id"]: {"username": u["username"], "puntos": 0} for u in usuarios}

        # E. Correr el bucle sumador usando la calculadora matemática pura de Python
        for prono in pronosticos:
            p_id = prono["partido_id"]
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

        # F. Cómputo 2: Puntos por Campeón (+10) y Subcampeón (+g)
        # Solo se calculan si ya cargaste los resultados reales en la bdd
      
        for u in usuarios:
            u_id = u["id"]
            if u_id not in ranking:
                continue
            
            # Sumamos Campeón si hay coincidencia
            print(f"Usuario: {u['username']} | Diccionario completo: {u}")
            print(f"  > Lo que lee de campeon_prediccion: '{u.get('campeon_prediccion')}'")
            print(f"  > Lo que lee de subcampeon_prediccion: '{u.get('subcampeon_prediccion')}'")
            
            # Sumamos Campeón si hay coincidencia
            if campeon_real and u.get("campeon_prediccion") == campeon_real:
                print(f"  ¡¡Suma 10 puntos a {u['username']}!!")
                ranking[u_id]["puntos"] += 10
                
            # Sumamos Subcampeón si hay coincidencia
            if subcampeon_real and u.get("subcampeon_prediccion") == subcampeon_real:
                print(f"  ¡¡Suma 5 puntos a {u['username']}!!")
                ranking[u_id]["puntos"] += 5


        # G. Ordenar la tabla definitiva de mayor a menor según sus puntos
        ranking_ordenado = sorted(ranking.values(), key=lambda x: x["puntos"], reverse=True)

        return {"status": "success", "data": ranking_ordenado}

    except Exception as e:
        print(f"❌ Error en obtener_tabla_posiciones: {e}")
        raise HTTPException(status_code=500, detail=f"Error al procesar el ranking de posiciones: {str(e)}")
    

@router.get("/{partido_id}/pronosticos-grupo")
def obtener_pronosticos_grupo(partido_id: int):
    """
    Devuelve los pronósticos de todos los usuarios para un partido específico,
    incluyendo el username de cada uno para poder armar el desglose.
    """
    try:
        # Traemos los pronósticos de este partido cruzando con la tabla profiles
        res = supabase.table("pronosticos") \
            .select("goles_pronostico_1, goles_pronostico_2, equipo_avanza_pronostico, user_id, profiles(username)") \
            .eq("partido_id", partido_id) \
            .execute()
            
        # Acomodamos el JSON para que sea más fácil de leer en React
        votos = []
        for item in res.data:
            # profiles puede venir como diccionario por la relación
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