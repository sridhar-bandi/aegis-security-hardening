import { Link, NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const navItems = [
  { to: '/', label: 'Dashboard' },
  { to: '/policies', label: 'Policies' },
  { to: '/solution-types', label: 'Solution Types' },
  { to: '/instances', label: 'Instances' },
  { to: '/users', label: 'Users' },
]

export default function Layout() {
  const { user, logout } = useAuth()
  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-aegis-dark text-white px-6 py-4 flex items-center gap-6">
        <img src="/HPE-Logo.png" alt="HPE Logo" className="h-10 w-auto" />
        <span className="font-bold text-2xl tracking-wide">⚔ AEGIS</span>
        <nav className="flex gap-4 flex-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `text-base px-2 py-1 rounded transition-colors ${isActive ? 'bg-white/20 font-semibold' : 'hover:bg-white/10'}`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="flex items-center gap-3 text-base">
          <span className="opacity-70">{user?.username} ({user?.role})</span>
          <button
            onClick={logout}
            className="bg-white/10 hover:bg-white/20 px-3 py-1 rounded transition-colors"
          >
            Logout
          </button>
        </div>
      </header>
      <main className="flex-1 p-6">
        <Outlet />
      </main>
    </div>
  )
}
