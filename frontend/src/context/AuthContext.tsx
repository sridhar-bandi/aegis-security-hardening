import React, { createContext, useContext, useEffect, useState } from 'react'
import type { User } from '../types'
import { getMe } from '../api/endpoints'

interface AuthContextValue {
  user: User | null
  token: string | null
  login: (token: string) => Promise<void>
  logout: () => void
  loading: boolean
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(localStorage.getItem('aegis_token'))
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (token) {
      getMe()
        .then(setUser)
        .catch(() => {
          setToken(null)
          localStorage.removeItem('aegis_token')
        })
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [token])

  const login = async (newToken: string) => {
    localStorage.setItem('aegis_token', newToken)
    setToken(newToken)
    const me = await getMe()
    setUser(me)
  }

  const logout = () => {
    localStorage.removeItem('aegis_token')
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, token, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
