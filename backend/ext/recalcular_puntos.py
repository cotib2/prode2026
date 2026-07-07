import os
from dotenv import load_dotenv
from app.database import supabase
from app.utils.points_calc import calcular_puntos_prode_complejo

load_dotenv()

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

def correr_recalculo():
    print("🚀 Iniciando el recálculo de puntos históricos...")
    
    # 1. Traemos solo los partidos que ya terminaron (estado FINISHED)
    partidos_finalizados = fetch_all_rows("partidos", filtros={"estado": "FINISHED"})
    print(f"Se encontraron {len(partidos_finalizados)} partidos finalizados.")

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
                
            print(f"  -> {puntos_reales} pts re-calculados para el usuario {prono['user_id']}")
            
    print("\n✅ ¡Recálculo completado con éxito! La columna 'puntos_ganados' ahora es 100% confiable.")

if __name__ == "__main__":
    correr_recalculo()