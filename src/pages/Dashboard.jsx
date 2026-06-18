import { useEffect, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { supabase } from "../lib/supabaseClient";
import "./Dashboard.css";
import PartidoCard from "../components/PartidoCard";

export default function Dashboard() {
  const [partidos, setPartidos] = useState([]);
  const [pronosticos, setPronosticos] = useState([]);
  const [username, setUsername] = useState("");
  const [userId, setUserId] = useState("");
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    async function cargarDatosDashboard() {
      try {
        // 1. Obtener el usuario actual autenticado
        const {
          data: { user },
        } = await supabase.auth.getUser();

        if (!user) {
          navigate("/login");
          return;
        }

        // Si hay usuario, guardamos sus datos
        setUserId(user.id);

        // 2. Traer su username desde la tabla profiles
        const { data: profileData } = await supabase
          .from("profiles")
          .select("username")
          .eq("id", user.id)
          .single();

        if (profileData) setUsername(profileData.username);

        // 3. Traer los partidos ordenados por fecha
        const { data: partidosData, error: partidosError } = await supabase
          .from("partidos")
          .select("*")
          .order("fecha", { ascending: true });

        if (partidosError) throw partidosError;
        if (partidosData) setPartidos(partidosData);

        // Traer los pronósticos del usuario actual
        const { data: pronosticosData, error: pronosticosError } =
          await supabase.from("pronosticos").select("*").eq("user_id", user.id);

        if (pronosticosError) throw pronosticosError;
        if (pronosticosData) setPronosticos(pronosticosData);
      } catch (error) {
        console.error("Error cargando datos del dashboard:", error);
      } finally {
        setLoading(false);
      }
    }

    cargarDatosDashboard();
  }, [navigate]);

  const handleLogout = async () => {
    await supabase.auth.signOut();
    navigate("/login"); // Al cerrar sesión, también redirigimos explícitamente
  };

  // Función formateadora de fecha para que quede linda (ej: "jue 11 jun, 16:00")
  const formatearFecha = (fechaString) => {
    const fecha = new Date(fechaString);
    return fecha.toLocaleDateString("es-AR", {
      weekday: "short",
      day: "numeric",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className="dashboard-container">
      {/* 🚀 EL HEADER SE RENDERIZA SIEMPRE DESDE EL MINUTO CERO */}
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

      {/* 🚀 EL LOADING AHORA CONTROLAR SOLO EL CONTENIDO INTERNO */}
      <main className="dashboard-main-scroll">
        <h2 className="fixture-title">Fixture Fase de Grupos</h2>

        {loading ? (
          <div className="contenedor-spinner-prode">
            <div className="spinner-prode"></div>
            <p className="loading-text-sutil">Cargando partidos...</p>
          </div>
        ) : (
          <div className="partidos-list">
            {partidos.map((partido) => {
              const miVoto = pronosticos.find(
                (p) => p.partido_id === partido.id_api,
              );

              return (
                <PartidoCard
                  key={partido.id_api}
                  partido={partido}
                  userId={userId}
                  votoInicial={miVoto}
                  formatearFecha={formatearFecha}
                />
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}
