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
  if (partido.estado !== "FINISHED") return null; // No hay puntos si no terminó

  const gReal1 = partido.goles_real_1;
  const gReal2 = partido.goles_real_2;
  const rAvanza = partido.equipo_avanza_real;

  const pG1 = prono.g1;
  const pG2 = prono.g2;
  const pAvanza = prono.avanza;

  const aciertoGoles1 = gReal1 === pG1;
  const aciertoGoles2 = gReal2 === pG2;
  const aciertoGanador = Math.sign(gReal1 - gReal2) === Math.sign(pG1 - pG2);

  const esEliminatoria = partido.instancia !== "GROUP_STAGE";

  if (esEliminatoria) {
    const aciertoAvanza = rAvanza === pAvanza;
    // Pleno absoluto en playoffs
    if (aciertoGoles1 && aciertoGoles2 && aciertoAvanza) return 9;
    // Acertó goles pero le erró al penal (solo pasa en empates)
    if (aciertoGoles1 && aciertoGoles2 && !aciertoAvanza) return 3;
    // Acertó tendencia + penal
    if (aciertoGanador && aciertoAvanza) return 6;
    // Acertó solo el que avanza por penales sin pegar la tendencia
    if (!aciertoGanador && aciertoAvanza) return 3;
    return 0;
  } else {
    // Fase de grupos tradicional
    if (aciertoGoles1 && aciertoGoles2) return 5;
    if (aciertoGanador) return 2;
    return 0;
  }
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
      setGoles1(votoInicial.goles_pronostico_1.toString());
      setGoles2(votoInicial.goles_pronostico_2.toString());
      setVotoGuardado({
        g1: votoInicial.goles_pronostico_1.toString(),
        g2: votoInicial.goles_pronostico_2.toString(),
        avanza: votoInicial.equipo_avanza_pronostico,
      });
    }
  }, [votoInicial]);

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

    setGuardando(true);
    try {
      const { error } = await supabase.from("pronosticos").upsert(
        {
          user_id: userId,
          partido_id: partido.id_api,
          goles_pronostico_1: parseInt(goles1),
          goles_pronostico_2: parseInt(goles2),
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
        setVotosGrupo(json.data);
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
