import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabaseClient'
import './Dashboard.css'

export default function Dashboard() {
  const [partidos, setPartidos] = useState([])
  const [username, setUsername] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function cargarDatosDashboard() {
      try {
        // 1. Obtener el usuario actual autenticado
        const { data: { user } } = await supabase.auth.getUser()

        if (user) {
          // 2. Traer su username desde la tabla profiles
          const { data: profileData } = await supabase
            .from('profiles')
            .select('username')
            .eq('id', user.id)
            .single()
          
          if (profileData) setUsername(profileData.username)
        }

        // 3. Traer los partidos ordenados por fecha
        const { data: partidosData, error: partidosError } = await supabase
          .from('partidos')
          .select('*')
          .order('fecha', { ascending: true })

        if (partidosError) throw partidosError
        if (partidosData) setPartidos(partidosData)

      } catch (error) {
        console.error('Error cargando datos del dashboard:', error)
      } finally {
        setLoading(false)
      }
    }

    cargarDatosDashboard()
  }, [])

  const handleLogout = () => {
    supabase.auth.signOut()
  }

  // Función formateadora de fecha para que quede linda (ej: "jue 11 jun, 16:00")
  const formatearFecha = (fechaString) => {
    const fecha = new Date(fechaString)
    return fecha.toLocaleDateString('es-AR', {
      weekday: 'short',
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  if (loading) {
    return <div className="dashboard-container"><p className="loading-text">Cargando fixture del mundial...</p></div>
  }

  return (
    <div className="dashboard-container">
      {/* Barra superior */}
      <header className="dashboard-header">
        <h1 className="welcome-text">
          ⚽ ¡Hola, <span className="username-highlight">{username || 'Jugador'}</span>!
        </h1>
        <button onClick={handleLogout} className="btn-logout">
          Cerrar Sesión
        </button>
      </header>

      <main>
        <h2 className="fixture-title">Fixture Fase de Grupos</h2>
        
        <div className="partidos-list">
          {partidos.map((partido) => (
            <div key={partido.id_api} className="partido-card">
              
              {/* Información del Partido */}
              <div className="partido-info">
                <div className="partido-fecha">{formatearFecha(partido.fecha)}</div>
                <div className="partido-equipos">
                  <span>{partido.equipo_1}</span>
                  <span className="vs-text">vs</span>
                  <span>{partido.equipo_2}</span>
                </div>
              </div>

              {/* Casilleros para arriesgar el Prode (inputs mockeados por ahora) */}
              <div className="partido-voto">
                <div className="voto-inputs">
                  <input type="number" min="0" placeholder="0" className="input-goles" />
                  <span className="vs-text">-</span>
                  <input type="number" min="0" placeholder="0" className="input-goles" />
                </div>
                <button className="btn-guardar">Votar</button>
              </div>

            </div>
          ))}
        </div>
      </main>
    </div>
  )
}