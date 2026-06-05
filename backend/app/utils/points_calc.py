def calcular_puntos_prode_complejo(
    prono_1: int, prono_2: int, p_avanza: str,
    real_1: int, real_2: int, r_avanza: str,
    instancia: str
) -> int:
    """
    Motor matemático del Prode 2026 en Python.
    Procesa las reglas de Fase de Grupos y Eliminatorias (con penales).
    """
    if prono_1 is None or prono_2 is None or real_1 is None or real_2 is None:
        return 0

    # Determinar tendencias de los 90 minutos
    # 1 = Gana equipo 1
    # -1 = Gana equipo 2
    # 0 = Empate
    t_real = 1 if real_1 > real_2 else (-1 if real_1 < real_2 else 0)
    t_prono = 1 if prono_1 > prono_2 else (-1 if prono_1 < prono_2 else 0)

    # -------------------------------------------------------------------------
    # ESCENARIO 1: EMPATE EN LOS 90 MINUTOS
    # -------------------------------------------------------------------------
    if t_real == 0:
        if t_prono != 0:
            return 0  # Erró la tendencia principal de empate

        # A. Empate en Fase de Grupos
        if instancia == "GROUP_STAGE":
            if prono_1 == real_1:
                return 6  # Empate exacto
            return 3      # Empate no exacto

        # B. Empate en Eliminación Directa (Entran los penales)
        else:
            es_exacto = (prono_1 == real_1)
            acerto_penales = (p_avanza == r_avanza and r_avanza is not None)

            if es_exacto and acerto_penales:
                return 9  # Empate exacto + ganador penales
            if es_exacto and not acerto_penales:
                return 6  # Empate exacto sin ganador penales
            if not es_exacto and acerto_penales:
                return 6  # Empate no exacto + ganador penales
            if not es_exacto and not acerto_penales:
                return 3  # Empate no exacto y sin ganador penales

    # -------------------------------------------------------------------------
    # ESCENARIO 2: HUBO UN GANADOR EN LOS 90 MINUTOS
    # -------------------------------------------------------------------------
    else:
        if t_real == t_prono:
            if prono_1 == real_1 and prono_2 == real_2:
                return 6  # Marcador exacto
            if prono_1 == real_1 or prono_2 == real_2:
                return 4  # Resultado parcial (Ganador + goles exactos de un equipo)
            return 3      # Ganador correcto simple
        else:
            if prono_1 == real_1 or prono_2 == real_2:
                return 1  # Goles de un equipo correcto (Consuelo)
            return 0