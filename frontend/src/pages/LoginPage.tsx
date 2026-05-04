import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { login as apiLogin } from '../api/endpoints'

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const { access_token } = await apiLogin(identifier, password)
      await login(access_token)
      navigate('/')
    } catch {
      setError('Invalid username/email or password')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-aegis-dark">
      <div className="bg-white rounded-xl shadow-xl p-8 w-full max-w-sm">
        <h1 className="text-2xl font-bold text-aegis-dark mb-2">⚔ Project AEGIS</h1>
        <p className="text-gray-500 text-sm mb-6">HPE Private Cloud Security Hardening</p>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <input
            type="text"
            placeholder="Email or Username"
            value={identifier}
            onChange={(e) => setIdentifier(e.target.value)}
            required
            className="border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-aegis-blue"
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            className="border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-aegis-blue"
          />
          {error && <p className="text-aegis-red text-sm">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="bg-aegis-dark text-white rounded py-2 text-sm font-semibold hover:bg-gray-700 disabled:opacity-50 transition-colors"
          >
            {loading ? 'Signing in…' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  )
}
