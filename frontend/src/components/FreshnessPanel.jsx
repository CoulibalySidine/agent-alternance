import { useState } from 'react'
import { showToast } from './Toast'

/**
 * FreshnessPanel — Panneau de fraîcheur des offres
 * 
 * Affiche :
 * - Répartition par âge (< 7j, 7-14j, 14-30j, > 30j)
 * - Répartition par source
 * - Bouton "Nettoyer les anciennes" avec confirmation
 * - Bouton "Vérifier les URLs" avec résultats
 * 
 * Usage dans Offres.jsx :
 *   import FreshnessPanel from '../components/FreshnessPanel'
 *   <FreshnessPanel fraicheur={fraicheurData} onCleanup={handleCleanup} onVerify={handleVerify} />
 */

export default function FreshnessPanel({ fraicheur, onCleanup, onVerify, onRefresh }) {
  const [cleaning, setCleaning] = useState(false)
  const [verifying, setVerifying] = useState(false)
  const [verifyResults, setVerifyResults] = useState(null)
  const [cleanupJours, setCleanupJours] = useState(30)

  if (!fraicheur || fraicheur.total === 0) return null

  const handleCleanup = async () => {
    const count = cleanupJours <= 7 ? fraicheur.moins_de_7j
      : cleanupJours <= 14 ? fraicheur.total - fraicheur.moins_de_7j - fraicheur['7_a_14j']
      : fraicheur.plus_de_30j

    if (!confirm(`Supprimer les offres de plus de ${cleanupJours} jours ?`)) return

    setCleaning(true)
    try {
      const result = await onCleanup(cleanupJours)
      showToast(`${result.supprimees} offre${result.supprimees > 1 ? 's' : ''} supprimée${result.supprimees > 1 ? 's' : ''}`)
      if (onRefresh) onRefresh()
    } catch (e) {
      showToast(e.message, 'error')
    }
    setCleaning(false)
  }

  const handleVerify = async () => {
    setVerifying(true)
    setVerifyResults(null)
    try {
      const result = await onVerify(20)
      setVerifyResults(result)
      showToast(`${result.actives} actives, ${result.inactives} inactives sur ${result.verifiees} vérifiées`)
    } catch (e) {
      showToast(e.message, 'error')
    }
    setVerifying(false)
  }

  const ageTotal = fraicheur.total
  const segments = [
    { label: '< 7j', count: fraicheur.moins_de_7j || 0, color: 'var(--green)' },
    { label: '7-14j', count: fraicheur['7_a_14j'] || 0, color: 'var(--accent)' },
    { label: '14-30j', count: fraicheur['14_a_30j'] || 0, color: 'var(--yellow)' },
    { label: '> 30j', count: fraicheur.plus_de_30j || 0, color: 'var(--red)' },
  ]

  return (
    <div style={{
      background: 'var(--surface)', border: '1px solid var(--border)',
      borderRadius: 'var(--radius)', padding: 14, marginBottom: 16,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
        <h3 style={{ fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.4px', color: 'var(--text-muted)' }}>
          Fraîcheur des offres — âge moyen : {fraicheur.age_moyen}j
        </h3>
        <div className="btn-group">
          <button
            className="btn btn-sm"
            onClick={handleVerify}
            disabled={verifying}
            title="Vérifier si les URLs sont encore actives"
          >
            {verifying ? '⏳ Vérification...' : '🔗 Vérifier URLs'}
          </button>
        </div>
      </div>

      {/* Barre segmentée */}
      <div style={{
        display: 'flex', height: 20, borderRadius: 4, overflow: 'hidden',
        marginBottom: 8, background: 'var(--surface-3)',
      }}>
        {segments.map((seg, i) => {
          const pct = ageTotal > 0 ? (seg.count / ageTotal) * 100 : 0
          if (pct === 0) return null
          return (
            <div
              key={i}
              title={`${seg.label} : ${seg.count} offres`}
              style={{
                width: `${pct}%`,
                background: `color-mix(in srgb, ${seg.color} 40%, transparent)`,
                borderRight: i < segments.length - 1 ? '1px solid var(--bg)' : 'none',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                transition: 'width 0.3s',
              }}
            >
              {pct > 15 && (
                <span style={{ fontSize: 10, fontFamily: 'var(--mono)', color: seg.color, fontWeight: 600 }}>
                  {seg.count}
                </span>
              )}
            </div>
          )
        })}
      </div>

      {/* Légende + actions */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
        <div style={{ display: 'flex', gap: 12 }}>
          {segments.map((seg, i) => (
            <span key={i} style={{ fontSize: 11, color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{
                width: 8, height: 8, borderRadius: 2,
                background: `color-mix(in srgb, ${seg.color} 60%, transparent)`,
                border: `1px solid ${seg.color}`,
                display: 'inline-block',
              }} />
              {seg.label}: {seg.count}
            </span>
          ))}
        </div>

        {/* Nettoyage */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <select
            value={cleanupJours}
            onChange={e => setCleanupJours(Number(e.target.value))}
            style={{
              background: 'var(--bg)', border: '1px solid var(--border)',
              borderRadius: 4, padding: '3px 6px', fontSize: 11,
              color: 'var(--text)', fontFamily: 'var(--font)',
            }}
          >
            <option value={7}>+ de 7 jours</option>
            <option value={14}>+ de 14 jours</option>
            <option value={30}>+ de 30 jours</option>
            <option value={60}>+ de 60 jours</option>
          </select>
          <button
            className="btn btn-sm btn-danger"
            onClick={handleCleanup}
            disabled={cleaning}
          >
            {cleaning ? '⏳...' : '🗑️ Nettoyer'}
          </button>
        </div>
      </div>

      {/* Sources */}
      {fraicheur.par_source && Object.keys(fraicheur.par_source).length > 1 && (
        <div style={{ display: 'flex', gap: 12, marginTop: 8, paddingTop: 8, borderTop: '1px solid var(--border)' }}>
          {Object.entries(fraicheur.par_source).map(([source, count]) => {
            const labels = { wttj: '🌴 WTTJ', lba: '🏛️ LBA', demo: '🎭 Demo' }
            return (
              <span key={source} style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                {labels[source] || source}: <strong style={{ color: 'var(--text)' }}>{count}</strong>
              </span>
            )
          })}
        </div>
      )}

      {/* Résultats vérification URLs */}
      {verifyResults && (
        <div style={{ marginTop: 10, paddingTop: 10, borderTop: '1px solid var(--border)' }}>
          <div style={{ fontSize: 12, marginBottom: 6, color: 'var(--text-muted)' }}>
            Vérification : <strong style={{ color: 'var(--green)' }}>{verifyResults.actives} actives</strong>
            {' '}/{' '}
            <strong style={{ color: 'var(--red)' }}>{verifyResults.inactives} inactives</strong>
            {' '}sur {verifyResults.verifiees}
          </div>
          {verifyResults.details?.filter(d => !d.url_active).length > 0 && (
            <div style={{ maxHeight: 100, overflow: 'auto' }}>
              {verifyResults.details.filter(d => !d.url_active).map((d, i) => (
                <div key={i} style={{ fontSize: 11, color: 'var(--red)', padding: '2px 0' }}>
                  ✕ {d.titre} @ {d.entreprise} — {d.erreur || `HTTP ${d.status}`}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
