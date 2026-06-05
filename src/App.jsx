import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useState, useEffect } from "react";
import { supabase } from "./lib/supabaseClient";

import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import TablaPuntos from "./pages/TablaPuntos";
import PrediccionFinal from "./pages/PrediccionFinal";

export default function App() {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // 1. Revisar si hay una sesión activa al cargar la app
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setLoading(false);
    });

    // 2. Escuchar cambios en el estado de auth (login, logout, etc.)
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
    });

    return () => subscription.unsubscribe();
  }, []);

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center">
        Cargando...
      </div>
    );
  }

  return (
    <BrowserRouter>
      <Routes>
        {/* Rutas públicas */}
        <Route
          path="/login"
          element={!session ? <Login /> : <Navigate to="/dashboard" />}
        />
        <Route
          path="/register"
          element={!session ? <Register /> : <Navigate to="/dashboard" />}
        />

        {/* Rutas protegidas (si no está logueado, rebota al login) */}
        <Route
          path="/dashboard"
          element={session ? <Dashboard /> : <Navigate to="/login" />}
        />
        <Route
          path="/tabla"
          element={session ? <TablaPuntos /> : <Navigate to="/login" />}
        />
        <Route
          path="/campeon"
          element={session ? <PrediccionFinal /> : <Navigate to="/login" />}
        />

        {/* Ruta por defecto */}
        <Route
          path="*"
          element={<Navigate to={session ? "/dashboard" : "/login"} />}
        />
      </Routes>
    </BrowserRouter>
  );
}
