import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api, setUnauthorizedHandler, tokenStore, type User } from './api'

interface AuthState {
  user: User | null
  loading: boolean
  signedOutByUser: boolean
  signIn: (email: string, password: string) => Promise<void>
  signOut: () => void
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [signedOutByUser, setSignedOutByUser] = useState(false)

  const expire = useCallback(() => {
    tokenStore.clear()
    setUser(null)
  }, [])

  const signOut = useCallback(() => {
    setSignedOutByUser(true)
    expire()
  }, [expire])

  useEffect(() => {
    setUnauthorizedHandler(expire)
    if (!tokenStore.get()) { setLoading(false); return }
    api.me().then(setUser).catch(() => tokenStore.clear()).finally(() => setLoading(false))
  }, [expire])

  const signIn = useCallback(async (email: string, password: string) => {
    const res = await api.login(email, password)
    tokenStore.set(res.access_token)
    setSignedOutByUser(false)
    setUser(res.user)
  }, [])

  const value = useMemo(() => ({ user, loading, signedOutByUser, signIn, signOut }),
    [user, loading, signedOutByUser, signIn, signOut])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}