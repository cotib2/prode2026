import { useEffect, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { supabase } from "../lib/supabaseClient";

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

        if (profileData) setUsername(profileData.username);

        // Pedido a Supabase para traer los puntos
        /* const { data: tablaData, error } = await supabase
        .from('puntajes_usuarios')
        .select('username, puntos')
        .order('puntos', { ascending: false });
        */

        // C. DATOS DE PRUEBA (Para ver cómo va quedando el diseño en el celu antes de armar la tabla real)
        const datosFicticios = [
          { username: "Coti (Vos)", puntos: 12 },
          { username: "Juani99", puntos: 9 },
          { username: "Messi_10", puntos: 6 },
          { username: "Santi_Dev", puntos: 3 },
        ];
        setRanking(datosFicticios);
      } catch (error) {
        console.error("Error cargando datos de la tabla:", error);
      } finally {
        setLoading(false);
      }
    }

    cargarDatosTabla();
  }, [navigate]);

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
          <button onClick={handleLogout} className="btn-logout">
            Salir
          </button>
        </div>
      </header>

      <main className="dashboard-main-scroll">
        <h2 className="fixture-title">Tabla de Posiciones</h2>

        <div
          className="tabla-usuarios"
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "8px",
            marginTop: "16px",
          }}
        >
          {ranking.map((jugador, index) => (
            <div
              key={index}
              style={{
                display: "flex",
                justifyContent: "space-between",
                backgroundColor: "#1e1e1e",
                padding: "12px 16px",
                borderRadius: "8px",
                border: jugador.username.includes("(Vos)")
                  ? "1px solid #4caf50"
                  : "1px solid #2c2c2c",
              }}
            >
              <span>
                {index + 1}° {jugador.username}
              </span>
              <span style={{ fontWeight: "bold", color: "#00d2c4" }}>
                {jugador.puntos} pts
              </span>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
