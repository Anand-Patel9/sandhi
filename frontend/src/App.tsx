import type { ReactNode } from 'react'
import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router'
import { AppShell } from './components/AppShell'
import { AuthProvider, useAuth } from './lib/auth'
import { Agents } from './pages/Agents'
import { Audit } from './pages/Audit'
import { DataSources } from './pages/DataSources'
import { Deal } from './pages/Deal'
import { Deals } from './pages/Deals'
import { Login } from './pages/Login'
import { NewNegotiation } from './pages/NewNegotiation'

function RequireAuth({ children }: { children: ReactNode }) {
  const { user, loading, signedOutByUser } = useAuth()
  const location = useLocation()
  if (loading) return <div className="main"><div className="skeleton" style={{ height: 60, maxWidth: 400 }} /></div>
  if (!user) return <Navigate to="/login" replace state={signedOutByUser ? undefined : { from: location.pathname }} />
  return <>{children}</>
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route element={<RequireAuth><AppShell /></RequireAuth>}>
            <Route index element={<Deals />} />
            <Route path="new" element={<NewNegotiation />} />
            <Route path="deals/:id" element={<Deal />} />
            <Route path="agents" element={<Agents />} />
            <Route path="data" element={<DataSources />} />
            <Route path="audit" element={<Audit />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}