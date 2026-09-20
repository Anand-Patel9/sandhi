import { NavLink, Outlet } from 'react-router'
import { useAuth } from '../lib/auth'
import { PARTY_COLOR, initials } from '../lib/format'
import { Icon, type IconName } from './icons'
import { Mark } from './Logo'

const LINKS: { to: string; label: string; icon: IconName; end?: boolean }[] = [
  { to: '/', label: 'Deals', icon: 'deals', end: true },
  { to: '/new', label: 'New negotiation', icon: 'new' },
  { to: '/agents', label: 'Agents', icon: 'agents' },
  { to: '/data', label: 'Data sources', icon: 'data' },
  { to: '/audit', label: 'Audit', icon: 'audit' },
]

export function AppShell() {
  const { user, signOut } = useAuth()
  return (
    <div className="shell">
      <aside className="rail">
        <NavLink to="/" className="rail-brand" aria-label="Sandhi home">
          <Mark size={34} onDark />
          <span>Sandhi</span>
        </NavLink>
        <nav aria-label="Main">
          {LINKS.map((l) => (
            <NavLink key={l.to} to={l.to} end={l.end} className={({ isActive }) => `rail-link${isActive ? ' active' : ''}`}>
              <Icon name={l.icon} />
              <span className="label-text">{l.label}</span>
            </NavLink>
          ))}
        </nav>
        {user && (
          <div className="rail-user">
            <span className="avatar" style={{ background: PARTY_COLOR[user.org.kind] ?? 'var(--buyer)' }}>
              {initials(user.org.name)}
            </span>
            <span className="who">
              <strong>{user.org.name}</strong>
              <span>{user.email}</span>
            </span>
            <button type="button" className="rail-signout" onClick={signOut} aria-label="Sign out" title="Sign out">
              <Icon name="signout" size={18} />
            </button>
          </div>
        )}
      </aside>
      <Outlet />
    </div>
  )
}