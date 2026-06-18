def calcular_puntos_prode_complejo(
    prono_1: int, prono_2: int, p_avanza: str,
    real_1: int, real_2: int, r_avanza: str,
    instancia: str
) -> int:
    """
    Motor matemático del Prode 2026 en Python.
    Permite rescatar el punto de consuelo incluso si el partido real fue un empate.
    """
    if prono_1 is None or prono_2 is None or real_1 is None or real_2 is None:
        return 0

    # Determinar tendencias de los 90 minutos
    t_real = 1 if real_1 > real_2 else (-1 if real_1 < real_2 else 0)
    t_prono = 1 if prono_1 > prono_2 else (-1 if prono_1 < prono_2 else 0)

    # -------------------------------------------------------------------------
    # ESCENARIO 1: EMPATE EN LOS 90 MINUTOS REALES
    # -------------------------------------------------------------------------
    if t_real == 0:
        if t_prono == 0:
            # A. Empate en Fase de Grupos
            if instancia == "GROUP_STAGE":
                if prono_1 == real_1:
                    return 6  # Empate exacto
                return 3      # Empate no exacto

            # B. Empate en Eliminación Directa
            else:
                es_exacto = (prono_1 == real_1)
                acerto_penales = (p_avanza == r_avanza and r_avanza is not None)

                if es_exacto and acerto_penales:
                    return 9
                if es_exacto and not acerto_penales:
                    return 6
                if not es_exacto and acerto_penales:
                    return 6
                if not es_exacto and not acerto_penales:
                    return 3

    # -------------------------------------------------------------------------
    # ESCENARIO 2: HUBO UN GANADOR EN LOS 90 MINUTOS REALES
    # -------------------------------------------------------------------------
    else:
        if t_real == t_prono:
            if prono_1 == real_1 and prono_2 == real_2:
                return 6  # Marcador exacto
            if prono_1 == real_1 or prono_2 == real_2:
                return 4  # Resultado parcial
            return 3      # Ganador correcto simple

    # -------------------------------------------------------------------------
    # FILTRO DE CONSUELO: Si llegó acá es porque erró la tendencia principal
    # -------------------------------------------------------------------------
    if prono_1 == real_1 or prono_2 == real_2:
        return 1  # Goles de un equipo correcto (Consuelo)

    return 0