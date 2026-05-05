import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import { WorkspaceProvider } from './context/WorkspaceContext'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import PolicyManagerPage from './pages/PolicyManagerPage'
import SolutionTypeBuilderPage from './pages/SolutionTypeBuilderPage'
import HardeningProfileManagerPage from './pages/HardeningProfileManagerPage'
import HardeningProfileEditorPage from './pages/HardeningProfileEditorPage'
import InstanceManagerPage from './pages/InstanceManagerPage'
import EnforcementConsolePage from './pages/EnforcementConsolePage'
import UserManagementPage from './pages/UserManagementPage'
import Layout from './components/Layout'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="flex items-center justify-center h-screen bg-aegis-dark text-slate-400 text-sm">Loading…</div>
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
                <WorkspaceProvider>
                  <Layout />
                </WorkspaceProvider>
              </ProtectedRoute>
            }
          >
            <Route index element={<DashboardPage />} />
            <Route path="policies" element={<PolicyManagerPage />} />
            <Route path="solution-types" element={<SolutionTypeBuilderPage />} />
            <Route path="profiles" element={<HardeningProfileManagerPage />} />
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
