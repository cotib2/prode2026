import { useEffect, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { supabase } from "../lib/supabaseClient";
import "./TablaPuntos.css";

export default function TablaPuntos() {
  const navigate = useNavigate();
  const location = useLocation();

  const [username, setUsername] = useState("");
  const [ranking, setRanking] = useState([]);
  const [loading, setLoading] = useState(true);

  // 2. Tu useEffect estructurado para luego traer datos
  useEffect(() => {
    async function cargarDatosTabla() {
      try {
        // A. Validamos y traemos al usuario logueado
        const {
          data: { user },
        } = await supabase.auth.getUser();
        if (!user) {
          navigate("/login");
          return;
        }

        const { data: profileData } = await supabase
          .from("profiles")
          .select("username")
          .eq("id", user.id)
          .single();

        let nombreUsuarioActual = "";
        if (profileData) {
          setUsername(profileData.username);
          nombreUsuarioActual = profileData.username;
        }

        // PEDIDO REAL AL BACKEND
        const response = await fetch(
          "https://prode2026-8lxe.onrender.com/api/partidos/tabla-posiciones",
        );
        const result = await response.json();

        if (result.status === "success" && result.data) {
          // Mapeamos los datos para agregar el "(Vos)" al usuario que está mirando la pantalla
          const rankingProcesado = result.data.map((jugador) => {
            if (jugador.username === nombreUsuarioActual) {
              return {
                ...jugador,
                username: `${jugador.username} (Vos)`,
              };
            }
            return jugador;
          });

          setRanking(rankingProcesado);
        }
      } catch (error) {
        console.error("Error cargando datos de la tabla real:", error);
      } finally {
        setLoading(false);
      }
    }

    cargarDatosTabla();
  }, [navigate]);

  const handleLogout = async () => {
    await supabase.auth.signOut();
    localStorage.clear();
    navigate("/login");
  };

  return (
    <div className="dashboard-container">
      {/* 🚀 MENÚ SUPERIOR FIJO E INMUNE AL LOADING */}
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
            title="Votar Campeón"
          >
            🏆
          </button>

          <button onClick={handleLogout} className="btn-logout">
            Salir
          </button>
        </div>
      </header>

      {/* 🚀 LA RUEDITA CONTROLA SOLO EL CUERPO DE LA TABLA */}
      <main className="dashboard-main-scroll">
        <h2 className="fixture-title">Tabla de Posiciones</h2>

        {loading ? (
          <div className="contenedor-spinner-prode">
            <div className="spinner-prode"></div>
            <p className="loading-text-sutil">
              Calculando puntajes en vivo... 📊
            </p>
          </div>
        ) : (
          <div className="tabla-container">
            <table className="prode-tabla">
              <thead>
                <tr>
                  <th>Pos</th>
                  <th>Usuario</th>
                  <th>Puntos</th>
                </tr>
              </thead>
              <tbody>
                {ranking.map((jugador, index) => {
                  const esUsuarioActual = jugador.username.includes("(Vos)");

                  return (
                    <tr
                      key={index}
                      className={esUsuarioActual ? "fila-usuario-actual" : ""}
                    >
                      <td className="posicion-cell">{index + 1}°</td>
                      <td className="username-cell">{jugador.username}</td>
                      <td className="puntos-cell">{jugador.puntos} pts</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  );
}
