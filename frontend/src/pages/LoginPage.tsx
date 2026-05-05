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
    <div className="min-h-screen flex items-center justify-center bg-aegis-dark relative overflow-hidden">
      {/* Subtle background gradient */}
      <div className="absolute inset-0 bg-gradient-to-br from-slate-950 via-slate-900 to-slate-800" />
      {/* Glow accents */}
      <div className="absolute top-0 right-0 w-[28rem] h-[28rem] bg-aegis-accent/5 rounded-full -translate-y-1/2 translate-x-1/3 blur-3xl pointer-events-none" />
      <div className="absolute bottom-0 left-0 w-[28rem] h-[28rem] bg-aegis-accent/5 rounded-full translate-y-1/2 -translate-x-1/3 blur-3xl pointer-events-none" />

      <div className="relative w-full max-w-sm mx-4">
        {/* Glass card */}
        <div className="bg-white/5 backdrop-blur-xl rounded-2xl border border-white/10 shadow-2xl p-10">
          {/* Brand */}
          <div className="mb-8">
            <div className="flex items-center gap-3 mb-5">
              <img src="/HPE-Logo.png" alt="HPE" className="h-[19px] w-auto [filter:invert(1)_hue-rotate(180deg)] [mix-blend-mode:screen]" />
              <span className="text-white/20">|</span>
              <span className="text-2xl font-bold text-white tracking-tight">AEGIS</span>
            </div>
            <p className="text-sm text-white/40">AI powered Security Hardening</p>
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div>
              <label className="block text-xs font-medium text-white/50 mb-1.5">Email or Username</label>
              <input
                type="text"
                placeholder="you@example.com"
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
                required
                className="w-full bg-white/10 border border-white/20 rounded-lg px-3.5 py-2.5 text-sm text-white placeholder-white/25 focus:outline-none focus:border-aegis-accent focus:ring-1 focus:ring-aegis-accent transition-colors"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-white/50 mb-1.5">Password</label>
              <input
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full bg-white/10 border border-white/20 rounded-lg px-3.5 py-2.5 text-sm text-white placeholder-white/25 focus:outline-none focus:border-aegis-accent focus:ring-1 focus:ring-aegis-accent transition-colors"
              />
            </div>
            {error && (
              <p className="text-red-400 text-xs bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
                {error}
              </p>
            )}
            <button
              type="submit"
              disabled={loading}
              className="bg-aegis-accent hover:bg-cyan-400 text-white rounded-lg py-2.5 text-sm font-semibold disabled:opacity-50 transition-colors mt-1"
            >
              {loading ? 'Signing in…' : 'Sign In'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
