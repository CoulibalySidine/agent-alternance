import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Onboarding from './pages/Onboarding'
import Offres from './pages/Offres'
import Dashboard from './pages/Dashboard'
import { Toast, useToast } from './components/Toast'

export default function App() {
  const toast = useToast()
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Onboarding />} />
        <Route path="/offres" element={<Offres />} />
        <Route path="/suivi" element={<Dashboard />} />
      </Routes>
      <Toast toast={toast} />
    </Layout>
  )
}
