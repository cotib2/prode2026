import { useState, useEffect } from "react";
import { supabase } from "../lib/supabaseClient";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const TRADUCCIONES_INSTANCIAS = {
  GROUP_STAGE: "Fase de Grupos",
  LAST_16: "Octavos de Final",
  QUARTER_FINALS: "Cuartos de Final",
  SEMI_FINALS: "Semifinal",
  THIRD_PLACE: "Tercer Puesto",
  FINAL: "Gran Final",
};

function calcularPuntosEspejo(prono, partido) {
  if (partido.estado !== "FINISHED") return null;

  const real1 = partido.goles_real_1;
  const real2 = partido.goles_real_2;
  const rAvanza = partido.ganador_penales_real;
  const instancia = partido.instancia;

  const prono1 =
    prono.g1 !== null && prono.g1 !== undefined ? parseInt(prono.g1) : null;
  const prono2 =
    prono.g2 !== null && prono.g2 !== undefined ? parseInt(prono.g2) : null;
  const pAvanza = prono.avanza;

  if (prono1 === null || prono2 === null || real1 === null || real2 === null) {
    return 0;
  }

  const tReal = real1 > real2 ? 1 : real1 < real2 ? -1 : 0;
  const tProno = prono1 > prono2 ? 1 : prono1 < prono2 ? -1 : 0;

  // -------------------------------------------------------------------------
  // ESCENARIO 1: EMPATE EN LOS 90 MINUTOS REALES
  // -------------------------------------------------------------------------
  if (tReal === 0) {
    // Si también pronosticó empate
    if (tProno === 0) {
      if (instancia === "GROUP_STAGE") {
        if (prono1 === real1) return 6; // Empate exacto (ej: 1-1 y puso 1-1)
        return 3; // Empate no exacto (ej: 1-1 y puso 2-2)
      } else {
        const esExacto = prono1 === real1;
        const acertoPenales =
          pAvanza === rAvanza && rAvanza !== null && rAvanza !== undefined;

        if (esExacto && acertoPenales) return 9;
        if (esExacto && !acertoPenales) return 6;
        if (!esExacto && acertoPenales) return 6;
        if (!esExacto && !acertoPenales) return 3;
      }
    }
    // Si NO pronosticó empate (ej: 1-1 real y puso 1-3), salta al chequeo de consuelo al final
  }
  // -------------------------------------------------------------------------
  // ESCENARIO 2: HUBO UN GANADOR EN LOS 90 MINUTOS REALES
  // -------------------------------------------------------------------------
  else {
    if (tReal === tProno) {
      if (prono1 === real1 && prono2 === real2) return 6; // Marcador exacto
      if (prono1 === real1 || prono2 === real2) return 4; // Resultado parcial
      return 3; // Ganador correcto simple
    }
  }

  // -------------------------------------------------------------------------
  // FILTRO DE CONSUELO: Para cualquiera que haya errado la tendencia (incluye empates)
  // -------------------------------------------------------------------------
  if (prono1 === real1 || prono2 === real2) {
    return 1; // Rescata 1 punto por pegarle a los goles de un equipo
  }

  return 0;
}

export default function PartidoCard({
  partido,
  userId,
  votoInicial,
  formatearFecha,
}) {
  const [goles1, setGoles1] = useState("");
  const [goles2, setGoles2] = useState("");
  const [equipoAvanza, setEquipoAvanza] = useState(null);
  const [guardando, setGuardando] = useState(false);
  const [votoCerrado, setVotoCerrado] = useState(false);

  const [verDetalleGrupo, setVerDetalleGrupo] = useState(false);
  const [votosGrupo, setVotosGrupo] = useState([]);
  const [cargandoGrupo, setCargandoGrupo] = useState(false);

  const [votoGuardado, setVotoGuardado] = useState(
    votoInicial
      ? {
          g1: votoInicial.goles_pronostico_1.toString(),
          g2: votoInicial.goles_pronostico_2.toString(),
        }
      : null,
  );

  const partidoTerminado = partido.estado === "FINISHED";

  useEffect(() => {
    function chequearTiempoLimite() {
      const ahora = new Date();
      const fechaPartido = new Date(partido.fecha);

      // Límite: Hora del partido MENOS 5 minutos (en milisegundos)
      const limiteTiempo = fechaPartido.getTime() - 5 * 60 * 1000;

      // Si la hora actual superó el límite, congelamos la tarjeta
      if (ahora.getTime() >= limiteTiempo) {
        setVotoCerrado(true);
      } else {
        setVotoCerrado(false);
      }
    }

    // Ejecutamos al montar el componente
    chequearTiempoLimite();

    // Re-chequeamos cada 30 segundos por si la usuaria se queda estática en la pantalla
    const interval = setInterval(chequearTiempoLimite, 30000);
    return () => clearInterval(interval);
  }, [partido.fecha]);

  useEffect(() => {
    if (votoInicial) {
      const g1Str = votoInicial.goles_pronostico_1.toString();
      const g2Str = votoInicial.goles_pronostico_2.toString();

      // 🚀 CONVERSIÓN INVERSA: Pasamos el "1" o "2" de la BDD al nombre del país
      let paisAvanza = null;
      if (votoInicial.gana_penales_pronostico === "1")
        paisAvanza = partido.equipo_1;
      if (votoInicial.gana_penales_pronostico === "2")
        paisAvanza = partido.equipo_2;

      setGoles1(g1Str);
      setGoles2(g2Str);
      setEquipoAvanza(paisAvanza); // Selecciona el botón correcto en la UI

      setVotoGuardado({
        g1: g1Str,
        g2: g2Str,
        avanza: paisAvanza,
      });
    }
  }, [votoInicial, partido.equipo_1, partido.equipo_2]);

  const esEliminatoria = partido.instancia !== "GROUP_STAGE";
  const esEmpateEnInputs = goles1 !== "" && goles2 !== "" && goles1 === goles2;
  const requierePenales = esEliminatoria && esEmpateEnInputs;

  // Si cambia el marcador y deja de ser empate, reseteamos el clasificado
  useEffect(() => {
    if (!esEmpateEnInputs) {
      setEquipoAvanza(null);
    }
  }, [goles1, goles2, esEmpateEnInputs]);

  // El botón se muestra verde SÓLO si hay un voto guardado Y coincide exactamente con los inputs actuales
  const esVotoIdenticoAGuardado =
    votoGuardado !== null &&
    goles1 === votoGuardado.g1 &&
    goles2 === votoGuardado.g2 &&
    equipoAvanza === votoGuardado.avanza;

  const handleVotar = async () => {
    if (votoCerrado || partidoTerminado) return;
    if (!userId) {
      alert("Tu sesión no se cargó correctamente. Recargá la página.");
      return;
    }

    if (goles1 === "" || goles2 === "") {
      alert("Por favor, ingresá los goles de ambos equipos para votar.");
      return;
    }

    // Validar que si hay penales, hayan elegido un ganador
    if (requierePenales && !equipoAvanza) {
      alert(
        "El partido es de eliminación directa. Elegí quién avanza por penales.",
      );
      return;
    }

    let penalesVoto = null;
    if (equipoAvanza === partido.equipo_1) penalesVoto = "1";
    if (equipoAvanza === partido.equipo_2) penalesVoto = "2";

    setGuardando(true);
    try {
      const { error } = await supabase.from("pronosticos").upsert(
        {
          user_id: userId,
          partido_id: partido.id_api,
          goles_pronostico_1: parseInt(goles1),
          goles_pronostico_2: parseInt(goles2),
          gana_penales_pronostico: penalesVoto,
        },
        {
          onConflict: "user_id,partido_id",
        },
      );

      if (error) throw error;

      // Actualizamos nuestro estado de "guardados" para que el botón pase a verde
      setVotoGuardado({ g1: goles1, g2: goles2, avanza: equipoAvanza });
    } catch (error) {
      console.error("Error al guardar el pronóstico:", error);
      alert("No se pudo guardar tu voto. Revisá la consola.");
    } finally {
      setGuardando(false);
    }
  };

  // 🚀 Función para alternar el ojito y cargar los datos
  const handleToggleOjito = async () => {
    if (verDetalleGrupo) {
      setVerDetalleGrupo(false);
      return;
    }

    setVerDetalleGrupo(true);
    setCargandoGrupo(true);
    try {
      // Reemplazar URL por tu dominio real en producción, ej: `https://tuprode.render.com/api/partidos/...`
      const res = await fetch(
        `${API_BASE_URL}/api/partidos/${partido.id_api}/pronosticos-grupo`,
      );
      const json = await res.json();
      if (json.status === "success") {
        const votosOrdenados = json.data.sort((a, b) => {
          const puntosA = calcularPuntosEspejo(a, partido) || 0;
          const puntosB = calcularPuntosEspejo(b, partido) || 0;

          return puntosB - puntosA; // Mayor a menor
        });

        setVotosGrupo(votosOrdenados);
      }
    } catch (error) {
      console.error("Error trayendo votos del grupo:", error);
    } finally {
      setCargandoGrupo(false);
    }
  };

  return (
    <div className="partido-card-container">
      <div
        className={`partido-card ${votoCerrado ? "card-deshabilitada" : ""}`}
      >
        <div className="partido-info">
          <div className="partido-fecha">
            <span className="instancia-tag">
              {TRADUCCIONES_INSTANCIAS[partido.instancia] ||
                partido.instancia ||
                "MUNDIAL"}
            </span>
            • {formatearFecha(partido.fecha)}
          </div>

          {/* 2. Nombre de los equipos e indicador vs */}
          <div className="partido-equipos">
            <span
              className={
                equipoAvanza === partido.equipo_1 ? "ganador-resaltado" : ""
              }
            >
              {partido.equipo_1}
            </span>
            <span className="vs-text">vs</span>
            <span
              className={
                equipoAvanza === partido.equipo_2 ? "ganador-resaltado" : ""
              }
            >
              {partido.equipo_2}
            </span>
          </div>
          {partidoTerminado && (
            <div className="resultado-real-badge">
              Final:{" "}
              <b>
                {partido.goles_real_1} - {partido.goles_real_2}
              </b>
              {partido.equipo_avanza_real &&
                ` (Avanzó: ${partido.equipo_avanza_real})`}
            </div>
          )}
        </div>

        {requierePenales && (
          <div className="seccion-penales">
            <p className="penales-titulo">¿Quién pasa por penales?</p>
            <div className="penales-botones">
              <button
                type="button"
                className={`btn-penal ${equipoAvanza === partido.equipo_1 ? "selected" : ""}`}
                onClick={() => setEquipoAvanza(partido.equipo_1)}
                disabled={guardando || votoCerrado}
              >
                {partido.equipo_1}
              </button>
              <button
                type="button"
                className={`btn-penal ${equipoAvanza === partido.equipo_2 ? "selected" : ""}`}
                onClick={() => setEquipoAvanza(partido.equipo_2)}
                disabled={guardando || votoCerrado}
              >
                {partido.equipo_2}
              </button>
            </div>
          </div>
        )}

        <div className="partido-voto">
          <div className="voto-inputs">
            <input
              type="number"
              min="0"
              placeholder="0"
              className="input-goles"
              value={goles1}
              onChange={(e) => setGoles1(e.target.value)}
              disabled={guardando || votoCerrado}
            />
            <span className="vs-text">-</span>
            <input
              type="number"
              min="0"
              placeholder="0"
              className="input-goles"
              value={goles2}
              onChange={(e) => setGoles2(e.target.value)}
              disabled={guardando || votoCerrado}
            />
          </div>
          {!votoCerrado ? (
            <button
              onClick={handleVotar}
              className="btn-guardar"
              disabled={guardando || esVotoIdenticoAGuardado}
              style={{
                backgroundColor: esVotoIdenticoAGuardado
                  ? "#4caf50"
                  : "#2196f3",
              }}
            >
              {guardando
                ? "..."
                : esVotoIdenticoAGuardado
                  ? "Guardado ✓"
                  : "Votar"}
            </button>
          ) : (
            <button
              onClick={handleToggleOjito}
              className={`btn-ojito ${verDetalleGrupo ? "ojito-abierto" : ""}`}
              title="Ver pronósticos del grupo"
            >
              {verDetalleGrupo ? "cerrar" : "ver votos"}
            </button>
          )}
        </div>
      </div>

      {votoCerrado && verDetalleGrupo && (
        <div className="desgloses-grupo-box">
          {cargandoGrupo ? (
            <p className="loading-grupo">Cargando apuestas...</p>
          ) : votosGrupo.length > 0 ? (
            <div className="tabla-mini-grupo">
              {votosGrupo.map((v) => {
                const ptsSumados = calcularPuntosEspejo(v, partido);
                return (
                  <div key={v.user_id} className="fila-voto-grupo">
                    <span className="grupo-username">👤 {v.username}</span>
                    <div className="grupo-valores-derecha">
                      <span className="grupo-prediccion">
                        {v.g1} - {v.g2}
                        {v.avanza && <small> ({v.avanza})</small>}
                      </span>
                      {partidoTerminado && ptsSumados !== null && (
                        <span
                          className={`grupo-puntos-badge ${ptsSumados > 0 ? "sumo-puntos" : "cero-puntos"}`}
                        >
                          +{ptsSumados} pts
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="no-votos-grupo">
              Nadie cargó pronósticos para este partido.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
