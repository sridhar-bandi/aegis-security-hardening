import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import PolicyManagerPage from './pages/PolicyManagerPage'
import SolutionTypeBuilderPage from './pages/SolutionTypeBuilderPage'
import HardeningProfileEditorPage from './pages/HardeningProfileEditorPage'
import InstanceManagerPage from './pages/InstanceManagerPage'
import EnforcementConsolePage from './pages/EnforcementConsolePage'
import UserManagementPage from './pages/UserManagementPage'
import Layout from './components/Layout'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="flex items-center justify-center h-screen">Loading…</div>
  if (!user) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route index element={<DashboardPage />} />
            <Route path="policies" element={<PolicyManagerPage />} />
            <Route path="solution-types" element={<SolutionTypeBuilderPage />} />
            <Route path="profiles/:profileId" element={<HardeningProfileEditorPage />} />
            <Route path="instances" element={<InstanceManagerPage />} />
            <Route path="instances/:instanceId/enforcement" element={<EnforcementConsolePage />} />
            <Route path="users" element={<UserManagementPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
