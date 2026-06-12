import { useEffect, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { supabase } from "../lib/supabaseClient";
import "./PrediccionFinal.css";

export default function PrediccionFinal() {
  const navigate = useNavigate();
  const location = useLocation();

  const [username, setUsername] = useState("");
  const [campeon, setCampeon] = useState("");
  const [subcampeon, setSubcampeon] = useState("");
  const [estaBloqueado, setEstaBloqueado] = useState(false);
  const [loading, setLoading] = useState(true);

  // Lista de países ordenada alfabéticamente
  const paises = [
    "Argelia",
    "Argentina",
    "Australia",
    "Austria",
    "Bélgica",
    "Bosnia y Herzegovina",
    "Brasil",
    "Canadá",
    "Costa de Marfil",
    "República Democrática del Congo",
    "Colombia",
    "Cabo Verde",
    "Croacia",
    "Curazao",
    "República Checa",
    "Dinamarca",
    "Ecuador",
    "Egipto",
    "Inglaterra",
    "España",
    "Francia",
    "Alemania",
    "Ghana",
    "Haití",
    "Irán",
    "Irak",
    "Italia",
    "Jordania",
    "Japón",
    "Arabia Saudita",
    "Corea del Sur",
    "Marruecos",
    "México",
    "Países Bajos",
    "Noruega",
    "Nueva Zelanda",
    "Panamá",
    "Paraguay",
    "Portugal",
    "Catar",
    "Sudáfrica",
    "Escocia",
    "Senegal",
    "Suiza",
    "Suecia",
    "Túnez",
    "Turquía",
    "Uruguay",
    "Estados Unidos",
    "Uzbekistán",
  ].sort();

  useEffect(() => {
    async function inicializarPrediccion() {
      try {
        // 1. Validar Usuario logueado
        const {
          data: { user },
        } = await supabase.auth.getUser();
        if (!user) {
          navigate("/login");
          return;
        }

        const { data: profile } = await supabase
          .from("profiles")
          .select("username")
          .eq("id", user.id)
          .single();
        if (profile) setUsername(profile.username);

        // 2. Control del tiempo (5 minutos antes del primer partido)
        const { data: primerPartido } = await supabase
          .from("partidos")
          .select("fecha")
          .order("fecha", { ascending: true })
          .limit(1)
          .single();

        if (primerPartido) {
          const fechaInicio = new Date(primerPartido.fecha).getTime();
          const limiteVoto = fechaInicio - 5 * 60 * 1000; // Restamos 5 minutos en milisegundos
          const ahora = new Date().getTime();

          if (ahora >= limiteVoto) {
            setEstaBloqueado(true);
          }
        }

        // 3. Traer predicciones previas si el usuario ya votó antes
        const { data: votoExistente } = await supabase
          .from("profiles")
          .select("campeon_prediccion, subcampeon_prediccion")
          .eq("id", user.id)
          .single();

        if (votoExistente) {
          setCampeon(votoExistente.campeon_prediccion || "");
          setSubcampeon(votoExistente.subcampeon_prediccion || "");
        }
      } catch (error) {
        console.error("Error en predicciones:", error);
      } finally {
        setLoading(false);
      }
    }

    inicializarPrediccion();
  }, [navigate]);

  const guardarPrediccionFinal = async () => {
    if (!campeon || !subcampeon) {
      alert("Por favor seleccioná ambos equipos.");
      return;
    }
    if (campeon === subcampeon) {
      alert("El campeón y el subcampeón no pueden ser el mismo país.");
      return;
    }

    try {
      const {
        data: { user },
      } = await supabase.auth.getUser();

      const { error } = await supabase
        .from("profiles")
        .update({
          campeon_prediccion: campeon,
          subcampeon_prediccion: subcampeon,
        })
        .eq("id", user?.id);

      if (error) throw error;
      alert("¡Predicción guardada con éxito! 🏆");
    } catch (error) {
      console.error("Error al guardar:", error);
      alert("Hubo un error al guardar tu predicción.");
    }
  };

  const handleLogout = () => {
    localStorage.clear();
    navigate("/login");
  };

  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
        <h1 className="welcome-text">
          ⚽ ¡Hola,{" "}
          <span className="username-highlight">{username || "Jugador"}</span>!
        </h1>

        <div className="header-actions">
          <button
            onClick={() => navigate("/dashboard")}
            className={`btn-nav ${location.pathname === "/dashboard" ? "active" : ""}`}
          >
            📅
          </button>
          <button
            onClick={() => navigate("/tabla")}
            className={`btn-nav ${location.pathname === "/tabla" ? "active" : ""}`}
          >
            📊
          </button>
          <button
            onClick={() => navigate("/campeon")}
            className={`btn-nav ${location.pathname === "/campeon" ? "active" : ""}`}
          >
            🏆
          </button>
          <button onClick={handleLogout} className="btn-logout">
            Salir
          </button>
        </div>
      </header>

      <main className="dashboard-main-scroll">
        <h2 className="fixture-title">Predicción del Torneo</h2>

        {loading ? (
          <div className="contenedor-spinner-prode">
            <div className="spinner-prode"></div>
            <p className="loading-text-sutil">
              Cargando tus predicciones finales... 🏆
            </p>
          </div>
        ) : (
          <>
            {estaBloqueado ? (
              <div className="tiempo-alerta bloqueado">
                🔒 Votación cerrada.
              </div>
            ) : (
              <div className="tiempo-alerta disponible">
                ⏰ Disponible hasta 5 minutos antes del primer partido.
              </div>
            )}

            <div className="campeon-container">
              <div className="seleccion-bloque">
                <h3>🥇 Elegí tu Campeón</h3>
                <select
                  value={campeon}
                  onChange={(e) => setCampeon(e.target.value)}
                  disabled={estaBloqueado}
                  className="select-pais"
                >
                  <option value="">-- Seleccionar País --</option>
                  {paises.map((p) => (
                    <option key={p} value={p}>
                      {p}
                    </option>
                  ))}
                </select>
              </div>

              <div className="seleccion-bloque">
                <h3>🥈 Elegí tu Subcampeón</h3>
                <select
                  value={subcampeon}
                  onChange={(e) => setSubcampeon(e.target.value)}
                  disabled={estaBloqueado}
                  className="select-pais"
                >
                  <option value="">-- Seleccionar País --</option>
                  {paises.map((p) => (
                    <option key={p} value={p}>
                      {p}
                    </option>
                  ))}
                </select>
              </div>

              <button
                onClick={guardarPrediccionFinal}
                disabled={estaBloqueado}
                className="btn-guardar-final"
              >
                Guardar Elección
              </button>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
