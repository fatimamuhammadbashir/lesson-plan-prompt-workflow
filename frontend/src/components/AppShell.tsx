import { useEffect, useState, type ReactNode } from 'react'
import { Link, NavLink, useLocation } from 'react-router-dom'
import {
  BookOpen,
  ChevronRight,
  Inbox,
  LayoutDashboard,
  LibraryBig,
  ListChecks,
  Menu,
  Plus,
  X,
} from 'lucide-react'
import { api } from '../api'

const navItems = [
  { to: '/', label: 'Overview', icon: LayoutDashboard, end: true },
  { to: '/plans', label: 'Lesson plans', icon: ListChecks, end: false },
  { to: '/reviews', label: 'Review queue', icon: Inbox, end: false },
  { to: '/curriculum', label: 'Curriculum', icon: LibraryBig, end: false },
]

export function AppShell({ children }: { children: ReactNode }) {
  const location = useLocation()
  const [menuOpen, setMenuOpen] = useState(false)
  const [online, setOnline] = useState<boolean | null>(null)

  useEffect(() => {
    setMenuOpen(false)
  }, [location.pathname])

  useEffect(() => {
    let active = true
    api
      .health()
      .then(() => active && setOnline(true))
      .catch(() => active && setOnline(false))
    return () => {
      active = false
    }
  }, [location.pathname])

  const pageLabel = location.pathname.startsWith('/plans/new')
    ? 'New lesson plan'
    : location.pathname.match(/^\/plans\/[^/]+\/decide/)
      ? 'Record decision'
      : location.pathname.match(/^\/plans\/[^/]+\/edit/)
        ? 'Edit lesson plan'
        : location.pathname.match(/^\/plans\/[^/]+/)
          ? 'Lesson plan'
          : location.pathname.startsWith('/plans')
            ? 'Lesson plans'
            : location.pathname.startsWith('/reviews')
              ? 'Review queue'
              : location.pathname.startsWith('/curriculum')
                ? 'Curriculum'
                : 'Overview'

  return (
    <div className="shell">
      <aside className={`sidebar ${menuOpen ? 'sidebar-open' : ''}`}>
        <div className="sidebar-head">
          <Link to="/" className="brand">
            <span className="brand-mark">LS</span>
            <span className="brand-copy">
              <strong>Lesson Studio</strong>
              <em>Planning workspace</em>
            </span>
          </Link>
          <button
            type="button"
            className="icon-button sidebar-close"
            aria-label="Close menu"
            onClick={() => setMenuOpen(false)}
          >
            <X size={18} />
          </button>
        </div>

        <nav className="side-nav" aria-label="Workspace">
          <span className="nav-label">Workspace</span>
          {navItems.map((item) => {
            const Icon = item.icon
            const plansActive =
              item.to === '/plans' &&
              location.pathname.startsWith('/plans') &&
              !location.pathname.startsWith('/plans/new')
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `nav-link ${(item.to === '/plans' ? plansActive : isActive) ? 'active' : ''}`
                }
              >
                <Icon size={17} />
                {item.label}
              </NavLink>
            )
          })}
        </nav>

        <div className="side-create">
          <NavLink
            to="/plans/new"
            className={({ isActive }) =>
              `nav-link nav-link-create ${isActive ? 'active' : ''}`
            }
          >
            <Plus size={17} />
            New lesson plan
          </NavLink>
        </div>

        <div className="side-footer">
          <div className="engine-row">
            <BookOpen size={15} />
            <div>
              <strong>Rule-based engine</strong>
              <span>Approved curriculum only</span>
            </div>
          </div>
          <span className={`api-status ${online === false ? 'offline' : ''}`}>
            <span />
            {online === false ? 'API offline' : online ? 'Local API connected' : 'Checking API'}
          </span>
        </div>
      </aside>

      {menuOpen ? (
        <button
          type="button"
          className="scrim"
          aria-label="Close menu"
          onClick={() => setMenuOpen(false)}
        />
      ) : null}

      <div className="main">
        <header className="topbar">
          <div className="topbar-left">
            <button
              type="button"
              className="icon-button mobile-menu"
              aria-label="Open menu"
              onClick={() => setMenuOpen(true)}
            >
              <Menu size={20} />
            </button>
            <div className="breadcrumb">
              <span>Lesson Studio</span>
              <ChevronRight size={14} />
              <strong>{pageLabel}</strong>
            </div>
          </div>
          <Link to="/plans/new" className="button button-primary button-small">
            <Plus size={16} />
            New lesson plan
          </Link>
        </header>

        <main className="page">{children}</main>
      </div>
    </div>
  )
}
