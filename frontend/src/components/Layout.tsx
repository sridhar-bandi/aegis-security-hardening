import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useWorkspace } from '../context/WorkspaceContext'

const navItems = [
  {
    to: '/',
    label: 'Dashboard',
    icon: (
      <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M4 5a1 1 0 011-1h4a1 1 0 011 1v5a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h4a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM14 5a1 1 0 011-1h4a1 1 0 011 1v6a1 1 0 01-1 1h-4a1 1 0 01-1-1V5zM14 17a1 1 0 011-1h4a1 1 0 011 1v2a1 1 0 01-1 1h-4a1 1 0 01-1-1v-2z" />
      </svg>
    ),
  },
  {
    to: '/policies',
    label: 'Policies',
    icon: (
      <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ),
  },
  {
    to: '/solution-types',
    label: 'Solution Types',
    icon: (
      <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
        <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
      </svg>
    ),
  },
  {
    to: '/profiles',
    label: 'Profiles',
    icon: (
      <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
      </svg>
    ),
  },
  {
    to: '/instances',
    label: 'Instances',
    icon: (
      <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
      </svg>
    ),
  },
  {
    to: '/users',
    label: 'Users',
    icon: (
      <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
      </svg>
    ),
  },
]

export default function Layout() {
  const { user, logout } = useAuth()
  const { workspaces, selectedWorkspace, setSelectedWorkspaceId } = useWorkspace()

  return (
    <div className="h-screen flex overflow-hidden bg-slate-50">
      {/* Sidebar */}
      <aside className="w-56 flex-shrink-0 flex flex-col bg-aegis-dark text-white overflow-y-auto">
        {/* Brand */}
        <div className="px-5 py-5 border-b border-white/10">
          <div className="flex items-center gap-3">
            <img src="/HPE-Logo.png" alt="HPE" className="h-[13px] w-auto [filter:invert(1)_hue-rotate(180deg)] [mix-blend-mode:screen]" />
            <span className="text-[10px] font-medium text-white/30">|</span>
            <div className="text-xl font-bold tracking-wide text-white">AEGIS</div>
          </div>
        </div>

        {/* Workspace selector */}
        <div className="px-4 py-3 border-b border-white/10">
          <label className="block text-[10px] font-semibold text-white/40 uppercase tracking-widest mb-1.5">
            Workspace
          </label>
          <select
            value={selectedWorkspace?.id ?? ''}
            onChange={(e) => setSelectedWorkspaceId(e.target.value)}
            className="w-full bg-white/10 text-white text-xs rounded-md px-2.5 py-1.5 border border-white/20 focus:outline-none focus:border-aegis-accent cursor-pointer"
          >
            <option value="" className="bg-slate-900 text-slate-200">— Select —</option>
            {workspaces.map((ws) => (
              <option key={ws.id} value={ws.id} className="bg-slate-900 text-slate-200">
                {ws.name}
              </option>
            ))}
          </select>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-0.5">
          <div className="text-[10px] font-semibold text-white/30 uppercase tracking-widest px-2 mb-2">
            Navigation
          </div>
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all ${
                  isActive
                    ? 'bg-aegis-accent text-white font-medium shadow-sm'
                    : 'text-white/60 hover:text-white hover:bg-white/10'
                }`
              }
            >
              {item.icon}
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        {/* User / sign-out */}
        <div className="px-4 py-4 border-t border-white/10">
          <div className="flex items-center gap-2.5 mb-3">
            <div className="w-7 h-7 rounded-full bg-aegis-accent/20 flex items-center justify-center text-aegis-accent text-xs font-bold uppercase flex-shrink-0">
              {user?.username?.charAt(0) ?? '?'}
            </div>
            <div className="min-w-0">
              <div className="text-xs font-medium text-white truncate">{user?.username}</div>
              <div className="text-[10px] text-white/40 capitalize">{user?.role}</div>
            </div>
          </div>
          <button
            onClick={logout}
            className="flex items-center gap-2 text-xs text-white/50 hover:text-white/90 transition-colors px-1 py-1 rounded w-full"
          >
            <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
            Sign out
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto bg-slate-50 p-8 min-w-0">
        <Outlet />
      </main>
    </div>
  )
}

