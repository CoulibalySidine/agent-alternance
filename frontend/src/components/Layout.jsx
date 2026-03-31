import { NavLink } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { getHealth } from '../api'

const NAV = [
  { to: '/', icon: '👤', label: 'Profil', end: true },
  { to: '/offres', icon: '📋', label: 'Offres', end: false },
  { to: '/suivi', icon: '📊', label: 'Suivi', end: false },
]

export default function Layout({ children }) {
  const [health, setHealth] = useState(null)

  useEffect(() => {
    getHealth().then(setHealth).catch(() => setHealth({ status: 'error' }))
    const id = setInterval(() => {
      getHealth().then(setHealth).catch(() => setHealth({ status: 'error' }))
    }, 30000)
    return () => clearInterval(id)
  }, [])

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <span>⚡</span> Agent Alternance
        </div>
        <nav>
          {NAV.map(n => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.end}
              className={({ isActive }) => isActive ? 'active' : ''}
            >
              <span>{n.icon}</span> {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <span className={`health-dot ${health?.status === 'ok' ? 'health-ok' : 'health-bad'}`} />
          <span className="health-text">
            API {health?.status === 'ok' ? 'connectée' : 'hors ligne'}
          </span>
        </div>
      </aside>
      <main className="main">{children}</main>
    </div>
  )
}
