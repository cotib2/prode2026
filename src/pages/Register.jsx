import { useState } from 'react'
import { supabase } from '../lib/supabaseClient'
import { useNavigate, Link } from 'react-router-dom'
import './Register.css'

export default function Register() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [username, setUsername] = useState('')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleRegister = async(e) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      const { data, error: signUpError } = await supabase.auth.signUp({
        email,
        password,
      })

      if (signUpError) throw signUpError

      if (data?.user) {
        const { error: profileError } = await supabase
          .from('profiles')
          .update({ username: username })
          .eq('id', data.user.id)

        if (profileError) throw profileError
        navigate('/dashboard')
      }
    } catch (err) {
      setError(err.message || 'Ocurrió un error al registrarse')
    } finally {
      setLoading(false)
    }
  }
  return (
    <div className='auth-container'>
      <h2 className='auth-title'>Registrarse en el Prode</h2>

      { error & <p className='auth-error'>{error}</p>}

      <form onSubmit={handleRegister} className='auth-form'>
        <label className='auth-label'>
          Nombre de Usuario (Apodo para la tabla):
          <input type='text' value={username} onChange={(e) => setUsername(e.target.value)} required className='auth-input'/>
        </label>

        <label className="auth-label">
          Email:
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required className="auth-input" />
        </label>

        <label className="auth-label">
          Contraseña:
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required className="auth-input" />
        </label>

        <button type="submit" disabled={loading} className="auth-button-register">
          {loading ? 'Creando cuenta...' : 'Crear Cuenta'}
        </button>

      </form>

      <p className="auth-footer">
        ¿Ya tenés cuenta? <Link to="/login" className="auth-link">Iniciá sesión acá</Link>
      </p>
      
    </div>
  )
}