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

  const [prediccionesUsuarios, setPrediccionesUsuarios] = useState([]);

  // Lista de países ordenada alfabéticamente
  const paises = [
    "Argelia", "Argentina", "Australia", "Austria", "Bélgica",
    "Bosnia y Herzegovina", "Brasil", "Canadá", "Costa de Marfil",
    "República Democrática del Congo", "Colombia", "Cabo Verde",
    "Croacia", "Curazao", "República Checa", "Dinamarca", "Ecuador",
    "Egipto", "Inglaterra", "España", "Francia", "Alemania", "Ghana",
    "Haití", "Irán", "Irak", "Italia", "Jordania", "Japón",
    "Arabia Saudita", "Corea del Sur", "Marruecos", "México",
    "Países Bajos", "Noruega", "Nueva Zelanda", "Panamá", "Paraguay",
    "Portugal", "Catar", "Sudáfrica", "Escocia", "Senegal", "Suiza",
    "Suecia", "Túnez", "Turquía", "Uruguay", "Estados Unidos", "Uzbekistán",
  ].sort();

  useEffect(() => {
    async function inicializarPrediccion() {
      try {
        const { data: { user } } = await supabase.auth.getUser();
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

        const { data: primerPartido } = await supabase
          .from("partidos")
          .select("fecha")
          .order("fecha", { ascending: true })
          .limit(1)
          .single();

        if (primerPartido) {
          const fechaInicio = new Date(primerPartido.fecha).getTime();
          const limiteVoto = fechaInicio - 5 * 60 * 1000;
          const ahora = new Date().getTime();

          if (ahora >= limiteVoto) {
            setEstaBloqueado(true);
          }
        }

        const { data: votoExistente } = await supabase
          .from("profiles")
          .select("campeon_prediccion, subcampeon_prediccion")
          .eq("id", user.id)
          .single();

        if (votoExistente) {
          setCampeon(votoExistente.campeon_prediccion || "");
          setSubcampeon(votoExistente.subcampeon_prediccion || "");
        }

        const { data: prediccionesData } = await supabase
          .from("profiles")
          .select("username, campeon_prediccion, subcampeon_prediccion")
          .not("campeon_prediccion", "is", null)
          .order("username", { ascending: true });

        if (prediccionesData) {
          setPrediccionesUsuarios(prediccionesData);
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
      const { data: { user } } = await supabase.auth.getUser();

      const { error } = await supabase
        .from("profiles")
        .update({
          campeon_prediccion: campeon,
          subcampeon_prediccion: subcampeon,
        })
        .eq("id", user?.id);

      if (error) throw error;
      alert("¡Predicción guardada con éxito! 🏆");
      
      setPrediccionesUsuarios((prev) => {
        const index = prev.findIndex(p => p.username === username);
        const nuevaPrediccion = { username, campeon_prediccion: campeon, subcampeon_prediccion: subcampeon };
        if (index >= 0) {
          const nuevaLista = [...prev];
          nuevaLista[index] = nuevaPrediccion;
          return nuevaLista;
        }
        return [...prev, nuevaPrediccion].sort((a, b) => a.username.localeCompare(b.username));
      });

    } catch (error) {
      console.error("Error al guardar:", error);
      alert("Hubo un error al guardar tu predicción.");
    }
  };

  const handleLogout = async () => {
    await supabase.auth.signOut();
    navigate("/login");
  };

  // 🚀 ELIMINAMOS el `if (loading) return ...` de acá para que el header renderice siempre

  return (
    <div className="dashboard-container">
      {/* HEADER FIJO */}
      <header className="dashboard-header">
        <h1 className="welcome-text">
          ⚽ ¡Hola,{" "}
          <span className="username-highlight">{username || "Jugador"}</span>!
        </h1>

        <div className="header-actions">
          <button
            onClick={() => navigate("/dashboard")}
            className={`btn-nav ${location.pathname === "/dashboard" ? "active" : ""}`}
            title="Fixture"
          >
            📅
          </button>
          <button
            onClick={() => navigate("/tabla")}
            className={`btn-nav ${location.pathname === "/tabla" ? "active" : ""}`}
            title="Tabla de Posiciones"
          >
            📊
          </button>
          <button
            onClick={() => navigate("/campeon")}
            className={`btn-nav ${location.pathname === "/campeon" ? "active" : ""}`}
            title="Votar Campeón"
          >
            🏆
          </button>
          <button onClick={handleLogout} className="btn-logout">
            Salir
          </button>
        </div>
      </header>

      {/* CONTENIDO PRINCIPAL */}
      <main className="dashboard-main-scroll">
        <h2 className="fixture-title">Predicción del Torneo</h2>

        {/* 🚀 CONDICIONAL DE CARGA */}
        {loading ? (
          <div className="contenedor-spinner-prode">
            <div className="spinner-prode"></div>
            <p className="loading-text-sutil">Cargando predicciones...</p>
          </div>
        ) : (
          <>
            {estaBloqueado ? (
              <div className="tiempo-alerta bloqueado">🔒 Votación cerrada.</div>
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

            {/* TABLA DE LA COMUNIDAD */}
            <div className="comunidad-predicciones-container">
              <h2 className="fixture-title" style={{ marginTop: "32px" }}>Predicciones del Grupo</h2>
              
              {prediccionesUsuarios.length > 0 ? (
                <div className="tabla-comunidad-wrapper">
                  <table className="tabla-comunidad">
                    <thead>
                      <tr>
                        <th>Usuario</th>
                        <th>🥇 Campeón</th>
                        <th>🥈 Subcampeón</th>
                      </tr>
                    </thead>
                    <tbody>
                      {prediccionesUsuarios.map((user, idx) => (
                        <tr key={idx} className={user.username === username ? "fila-mi-voto" : ""}>
                          <td className="col-user">
                            👤 {user.username} {user.username === username && "(Vos)"}
                          </td>
                          <td className="col-campeon">{user.campeon_prediccion}</td>
                          <td className="col-subcampeon">{user.subcampeon_prediccion}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="no-votos-msg">Nadie eligió a sus candidatos todavía.</p>
              )}
            </div>
          </>
        )}
      </main>
    </div>
  );
}