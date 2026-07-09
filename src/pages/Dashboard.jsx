import { useEffect, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { supabase } from "../lib/supabaseClient";
import "./Dashboard.css";
import PartidoCard from "../components/PartidoCard";

// 🚀 CONSTANTES DE INSTANCIAS (Fuera del componente para no re-crearlas)
const ORDEN_INSTANCIAS = [
  "GROUP_STAGE",
  "LAST_32", // 16avos de final
  "LAST_16", // Octavos de final
  "QUARTER_FINALS", // Cuartos de final
  "SEMI_FINALS", // Semifinales
  "THIRD_PLACE", // Tercer Puesto
  "FINAL", // Final
];

const TRADUCCIONES = {
  GROUP_STAGE: "Grupos",
  LAST_32: "16avos",
  LAST_16: "Octavos",
  QUARTER_FINALS: "Cuartos",
  SEMI_FINALS: "Semis",
  THIRD_PLACE: "3er Puesto",
  FINAL: "Final",
};

export default function Dashboard() {
  const [partidos, setPartidos] = useState([]);
  const [pronosticos, setPronosticos] = useState([]);
  const [username, setUsername] = useState("");
  const [userId, setUserId] = useState("");
  const [loading, setLoading] = useState(true);

  // 🚀 ESTADO PARA LAS PESTAÑAS
  const [pestañaActiva, setPestañaActiva] = useState("");

  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    async function cargarDatosDashboard() {
      try {
        const {
          data: { user },
        } = await supabase.auth.getUser();

        if (!user) {
          navigate("/login");
          return;
        }

        setUserId(user.id);

        const { data: profileData } = await supabase
          .from("profiles")
          .select("username")
          .eq("id", user.id)
          .single();

        if (profileData) setUsername(profileData.username);

        const { data: partidosData, error: partidosError } = await supabase
          .from("partidos")
          .select("*")
          .order("fecha", { ascending: true });

        if (partidosError) throw partidosError;
        if (partidosData) setPartidos(partidosData);

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

  // 🚀 LÓGICA DE PESTAÑAS
  const instanciasDisponibles = ORDEN_INSTANCIAS.filter((instancia) =>
    partidos.some((p) => p.instancia === instancia),
  );

  useEffect(() => {
    // Si hay instancias disponibles y todavía no hay pestaña activa, seleccionamos la primera
    if (instanciasDisponibles.length > 0 && !pestañaActiva) {
      setPestañaActiva(instanciasDisponibles[0]);
    }
  }, [partidos, instanciasDisponibles, pestañaActiva]);

  // Filtramos los partidos para mostrar solo los de la pestaña activa
  const partidosFiltrados = partidos.filter(
    (p) => p.instancia === pestañaActiva,
  );

  const handleLogout = async () => {
    await supabase.auth.signOut();
    navigate("/login");
  };

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

      <main className="dashboard-main-scroll">
        {loading ? (
          <div className="contenedor-spinner-prode">
            <div className="spinner-prode"></div>
            <p className="loading-text-sutil">Cargando partidos...</p>
          </div>
        ) : (
          <>
            {/* 🚀 MENÚ DE PESTAÑAS DINÁMICAS */}
            <div className="tabs-container">
              {instanciasDisponibles.map((instancia) => (
                <button
                  key={instancia}
                  className={`tab-btn ${pestañaActiva === instancia ? "active" : ""}`}
                  onClick={() => setPestañaActiva(instancia)}
                >
                  {TRADUCCIONES[instancia] || instancia}
                </button>
              ))}
            </div>

            {/* 🚀 LISTA FILTRADA DE PARTIDOS */}
            <div className="partidos-list">
              {partidosFiltrados.length > 0 ? (
                partidosFiltrados.map((partido) => {
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
                })
              ) : (
                <p
                  style={{
                    textAlign: "center",
                    color: "#6b7280",
                    marginTop: "20px",
                  }}
                >
                  Aún no hay partidos programados para esta instancia.
                </p>
              )}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
