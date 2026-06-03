import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { supabase } from '../lib/supabaseClient'
import './Dashboard.css'
import PartidoCard from '../components/PartidoCard'

export default function Dashboard() {
  const [partidos, setPartidos] = useState([])
  const [pronosticos, setPronosticos] = useState([])
  const [username, setUsername] = useState('')
  const [userId, setUserId] = useState('')
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    async function cargarDatosDashboard() {
      try {
        // 1. Obtener el usuario actual autenticado
        const { data: { user } } = await supabase.auth.getUser()
        
        if (!user) {
          navigate('/login')
          return
        }

        // Si hay usuario, guardamos sus datos
        setUserId(user.id)

          // 2. Traer su username desde la tabla profiles
        const { data: profileData } = await supabase
          .from('profiles')
          .select('username')
          .eq('id', user.id)
          .single()
          
        if (profileData) setUsername(profileData.username)
        
        // 3. Traer los partidos ordenados por fecha
        const { data: partidosData, error: partidosError } = await supabase
          .from('partidos')
          .select('*')
          .order('fecha', { ascending: true })

        if (partidosError) throw partidosError
        if (partidosData) setPartidos(partidosData)

        // Traer los pronósticos del usuario actual
        const { data: pronosticosData, error: pronosticosError } = await supabase
          .from('pronosticos')
          .select('*')
          .eq('user_id', user.id)

        if (pronosticosError) throw pronosticosError
        if (pronosticosData) setPronosticos(pronosticosData)

      } catch (error) {
        console.error('Error cargando datos del dashboard:', error)
      } finally {
        setLoading(false)
      }
    }

    cargarDatosDashboard()
  }, [navigate])

  const handleLogout = async () => {
    await supabase.auth.signOut()
    navigate('/login') // Al cerrar sesión, también redirigimos explícitamente
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
    return (
      <div className="dashboard-container">
        <p className="loading-text">Cargando fixture del mundial...</p>
      </div>
    )
  }

  return (
    <div className="dashboard-container">
      {/* Barra superior fija */}
      <header className="dashboard-header">
        <h1 className="welcome-text">
          ⚽ ¡Hola, <span className="username-highlight">{username || 'Jugador'}</span>!
        </h1>
        <div className="header-actions">
          {/* Botón Fixture */}
          <button 
            onClick={() => navigate('/dashboard')} 
            className={`btn-nav ${location.pathname === '/dashboard' ? 'active' : ''}`}
            title="Fixture"
          >
            📅
          </button>

          {/* Botón Tabla */}
          <button 
            onClick={() => navigate('/tabla')} 
            className={`btn-nav ${location.pathname === '/tabla' ? 'active' : ''}`}
            title="Tabla de Posiciones"
          >
            📊
          </button>

          {/* Botón Cerrar Sesión */}
          <button onClick={handleLogout} className="btn-logout">
            Salir
          </button>
        </div>
      </header>

      <main className='dashboard-main-scroll'>
        <h2 className="fixture-title">Fixture Fase de Grupos</h2>
        
        <div className="partidos-list">
          {partidos.map((partido) => {
            // Buscamos si existe un voto guardado para este partido en particular
            const miVoto = pronosticos.find(p => p.partido_id === partido.id_api)

            return (
              <PartidoCard 
                key={partido.id_api} 
                partido={partido} 
                userId={userId} 
                votoInicial={miVoto}
                formatearFecha={formatearFecha} 
              />
            )
          })}
        </div>
      </main>
    </div>
  )
}