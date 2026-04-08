import { Routes, Route, NavLink } from 'react-router-dom'
import GlobalFilterBar from './components/GlobalFilterBar'
import ToastContainer from './components/ToastContainer'
import { useAlerts } from './hooks/useAlerts'
import Dashboard from './pages/Dashboard'
import WorldMap from './pages/WorldMap'
import Findings from './pages/Findings'
import Contacts from './pages/Contacts'
import Sources from './pages/Sources'
import Reports from './pages/Reports'

const TABS = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/map', label: 'World Map' },
  { to: '/findings', label: 'Findings' },
  { to: '/contacts', label: 'Contacts' },
  { to: '/sources', label: 'Sources' },
  { to: '/reports', label: 'Reports' },
]

function AlertsConnector() {
  useAlerts()
  return null
}

export default function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <AlertsConnector />
      <ToastContainer />

      <nav className="bg-white border-b border-gray-200 px-6 flex items-center gap-1 h-14 shrink-0">
        <span className="text-green-700 font-bold text-lg mr-6">🌿 Climate Intel</span>
        {TABS.map(({ to, label, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-green-50 text-green-700'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
              }`
            }
          >
            {label}
          </NavLink>
        ))}
      </nav>

      <GlobalFilterBar />

      <main className="flex-1 overflow-auto">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/map" element={<WorldMap />} />
          <Route path="/findings" element={<Findings />} />
          <Route path="/contacts" element={<Contacts />} />
          <Route path="/sources" element={<Sources />} />
          <Route path="/reports" element={<Reports />} />
        </Routes>
      </main>
    </div>
  )
}
