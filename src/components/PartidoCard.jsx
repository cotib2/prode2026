import { useState, useEffect } from "react";
import { supabase } from "../lib/supabaseClient";

const TRADUCCIONES_INSTANCIAS = {
  GROUP_STAGE: "Fase de Grupos",
  LAST_16: "Octavos de Final",
  QUARTER_FINALS: "Cuartos de Final",
  SEMI_FINALS: "Semifinal",
  THIRD_PLACE: "Tercer Puesto",
  FINAL: "Gran Final",
};

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

  const [votoGuardado, setVotoGuardado] = useState(
    votoInicial
      ? {
          g1: votoInicial.goles_pronostico_1.toString(),
          g2: votoInicial.goles_pronostico_2.toString(),
        }
      : null,
  );

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

  return (
    <div className="partido-card">
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
      </div>

      {requierePenales && (
        <div className="seccion-penales">
          <p className="penales-titulo">¿Quién pasa por penales?</p>
          <div className="penales-botones">
            <button
              type="button"
              className={`btn-penal ${equipoAvanza === partido.equipo_1 ? "selected" : ""}`}
              onClick={() => setEquipoAvanza(partido.equipo_1)}
              disabled={guardando}
            >
              {partido.equipo_1}
            </button>
            <button
              type="button"
              className={`btn-penal ${equipoAvanza === partido.equipo_2 ? "selected" : ""}`}
              onClick={() => setEquipoAvanza(partido.equipo_2)}
              disabled={guardando}
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
            disabled={guardando}
          />
          <span className="vs-text">-</span>
          <input
            type="number"
            min="0"
            placeholder="0"
            className="input-goles"
            value={goles2}
            onChange={(e) => setGoles2(e.target.value)}
            disabled={guardando}
          />
        </div>
        <button
          onClick={handleVotar}
          className="btn-guardar"
          disabled={guardando || esVotoIdenticoAGuardado} // Se deshabilita si es idéntico (para no votar al vicio)
          style={{
            backgroundColor: esVotoIdenticoAGuardado ? "#4caf50" : "#2196f3",
            cursor: esVotoIdenticoAGuardado ? "default" : "pointer",
          }}
        >
          {guardando ? "..." : esVotoIdenticoAGuardado ? "Guardado ✓" : "Votar"}
        </button>
      </div>
    </div>
  );
}
