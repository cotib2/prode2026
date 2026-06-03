import { useState } from 'react'
import { supabase } from '../lib/supabaseClient'
import { useNavigate, Link } from 'react-router-dom'
import './Login.css'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleLogin = async (e) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    const { error: loginError } = await supabase.auth.signInWithPassword({
      email,
      password,
    })

    setLoading(false)

    if (loginError) {
      setError(loginError.message)
    } else {
      navigate('/dashboard')
    }
  }

  return (
    <div className="auth-container">
      <h2 className="auth-title">Iniciar Sesión</h2>
      
      {error && <p className="auth-error">{error}</p>}

      <form onSubmit={handleLogin} className="auth-form">
        <label className="auth-label">
          Email:
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required className="auth-input" />
        </label>

        <label className="auth-label">
          Contraseña:
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required className="auth-input" />
        </label>

        <button type="submit" disabled={loading} className="auth-button-login">
          {loading ? 'Ingresando...' : 'Ingresar'}
        </button>
      </form>

      <p className="auth-footer">
        ¿No tenés cuenta? <Link to="/register" className="auth-link">Registrate acá</Link>
      </p>
    </div>
  )
}