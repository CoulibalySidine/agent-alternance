import { useState, useEffect, useCallback } from 'react'
import { getSuivi, getSuiviStats, changerEtat, retirerSuivi } from '../api'
import { showToast } from '../components/Toast'

const ETATS = {
  brouillon: '📝', envoyee: '📤', vue: '👁️',
  entretien: '🎤', acceptee: '✅', refusee: '❌', sans_reponse: '⏳',
}
const ETAT_LABELS = {
  brouillon: 'Brouillon', envoyee: 'Envoyée', vue: 'Vue',
  entretien: 'Entretien', acceptee: 'Acceptée', refusee: 'Refusée', sans_reponse: 'Sans réponse',
}
const ETAT_ORDER = ['brouillon','envoyee','vue','entretien','acceptee','refusee','sans_reponse']

const SCORE_CLS = (s) => s >= 70 ? 'score-high' : s >= 40 ? 'score-mid' : 'score-low'

export default function Dashboard() {
  const [candidatures, setCandidatures] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState(null)
  const [filterEtat, setFilterEtat] = useState('')

  const charger = useCallback(async () => {
    setLoading(true)
    try {
      const params = {}
      if (filterEtat) params.etat = filterEtat
      const [s, st] = await Promise.all([getSuivi(params), getSuiviStats()])
      setCandidatures(s)
      setStats(st)
    } catch (e) {
      showToast(e.message, 'error')
    }
    setLoading(false)
  }, [filterEtat])

  useEffect(() => { charger() }, [charger])

  const handleChangerEtat = async (offreId, nouvelEtat) => {
    try {
      await changerEtat(offreId, nouvelEtat)
      showToast(`État changé → ${ETAT_LABELS[nouvelEtat]}`)
      charger()
    } catch (e) {
      showToast(e.message, 'error')
    }
  }

  const handleRetirer = async (offreId) => {
    if (!confirm('Retirer cette candidature du suivi ?')) return
    try {
      await retirerSuivi(offreId)
      showToast('Candidature retirée')
      charger()
    } catch (e) {
      showToast(e.message, 'error')
    }
  }

  // Relances
  const relances = candidatures.filter(c => c.doit_relancer)

  return (
    <div>
      <div className="page-head">
        <h1><span>📊</span> Suivi des candidatures</h1>
      </div>

      {/* Stats */}
      {stats && (
        <div className="stats-row">
          <div className="stat-card highlight">
            <div className="num">{stats.total}</div>
            <div className="label">Total</div>
          </div>
          {stats.score_moyen != null && (
            <div className="stat-card">
              <div className="num">{Math.round(stats.score_moyen)}</div>
              <div className="label">Score moyen</div>
            </div>
          )}
          {ETAT_ORDER.map(e => {
            const count = stats.par_etat?.[e] || 0
            if (count === 0) return null
            return (
              <div className="stat-card" key={e}>
                <div className="num">{ETATS[e]} {count}</div>
                <div className="label">{ETAT_LABELS[e]}</div>
              </div>
            )
          })}
        </div>
      )}

      {/* Alertes relance */}
      {relances.length > 0 && (
        <div style={{
          background: 'var(--red-dim)', border: '1px solid rgba(248,81,73,0.3)',
          borderRadius: 'var(--radius)', padding: '12px 16px', marginBottom: 16
        }}>
          <strong style={{ fontSize: 13, color: 'var(--red)' }}>
            🔔 {relances.length} candidature{relances.length > 1 ? 's' : ''} à relancer
          </strong>
          <div style={{ marginTop: 6, fontSize: 12.5, color: 'var(--text-muted)' }}>
            {relances.map(c => (
              <div key={c.offre_id}>{ETATS[c.etat]} <strong>{c.entreprise}</strong> — {c.titre}</div>
            ))}
          </div>
        </div>
      )}

      {/* Filtre */}
      <div className="toolbar">
        <select className="filter" value={filterEtat} onChange={e => setFilterEtat(e.target.value)}>
          <option value="">Tous les statuts</option>
          {ETAT_ORDER.map(e => (
            <option key={e} value={e}>{ETATS[e]} {ETAT_LABELS[e]}</option>
          ))}
        </select>
      </div>

      <div className="count-bar">
        {candidatures.length} candidature{candidatures.length > 1 ? 's' : ''}
      </div>

      {/* Table */}
      {loading ? (
        <div className="empty">Chargement...</div>
      ) : candidatures.length === 0 ? (
        <div className="empty">
          Aucune candidature dans le suivi. Ajoute des offres depuis la page Offres.
        </div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th style={{ width: 60 }}>Score</th>
                <th>Poste</th>
                <th>Lieu</th>
                <th>État</th>
                <th style={{ width: 55 }}>Jours</th>
                <th style={{ width: 200 }}>Changer l'état</th>
              </tr>
            </thead>
            <tbody>
              {candidatures.map(c => (
                <CandidatureRow
                  key={c.offre_id}
                  c={c}
                  isOpen={expanded === c.offre_id}
                  onToggle={() => setExpanded(expanded === c.offre_id ? null : c.offre_id)}
                  onChangerEtat={handleChangerEtat}
                  onRetirer={handleRetirer}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function CandidatureRow({ c, isOpen, onToggle, onChangerEtat, onRetirer }) {
  const jours = c.jours_depuis_envoi
  return (
    <>
      <tr onClick={onToggle} style={{ cursor: 'pointer' }}>
        <td>
          {c.score != null
            ? <span className={`score ${SCORE_CLS(c.score)}`}>{Math.round(c.score)}</span>
            : <span className="score-none">—</span>}
        </td>
        <td>
          <strong>{c.titre}</strong><br />
          <span className="sub">{c.entreprise}</span>
        </td>
        <td><span className="sub">{c.lieu}</span></td>
        <td>
          <span className={`etat etat-${c.etat}`}>
            {ETATS[c.etat]} {ETAT_LABELS[c.etat]}
          </span>
          {c.doit_relancer && <span className="badge-relance">RELANCER</span>}
        </td>
        <td>
          <span className="mono">{jours != null ? `J+${jours}` : '—'}</span>
        </td>
        <td onClick={e => e.stopPropagation()}>
          <div className="btn-group">
            <select
              className="filter"
              value=""
              onChange={e => { if (e.target.value) onChangerEtat(c.offre_id, e.target.value) }}
              style={{ fontSize: 11, padding: '4px 6px' }}
            >
              <option value="">→ Changer...</option>
              {ETAT_ORDER.filter(e => e !== c.etat).map(e => (
                <option key={e} value={e}>{ETATS[e]} {ETAT_LABELS[e]}</option>
              ))}
            </select>
            <button className="btn btn-sm btn-danger" onClick={() => onRetirer(c.offre_id)} title="Retirer du suivi">✕</button>
          </div>
        </td>
      </tr>
      {isOpen && (
        <tr>
          <td colSpan={6} style={{ padding: 0 }}>
            <div className="expand-content">
              <div className="expand-grid">
                <div>
                  <h4>Historique</h4>
                  <ul>
                    {c.historique.map((h, i) => (
                      <li key={i}>
                        {h.date?.slice(0, 10)} — {ETATS[h.etat] || '❓'} {h.etat}
                        {h.commentaire ? ` : ${h.commentaire}` : ''}
                      </li>
                    ))}
                  </ul>
                </div>
                <div>
                  <h4>Notes</h4>
                  {c.notes.length > 0 ? (
                    <ul>
                      {c.notes.map((n, i) => (
                        <li key={i}>{n.date?.slice(0, 10)} — {n.texte}</li>
                      ))}
                    </ul>
                  ) : (
                    <p style={{ color: 'var(--text-muted)', fontSize: 12 }}>Aucune note</p>
                  )}
                  {c.url && (
                    <div style={{ marginTop: 12 }}>
                      <a href={c.url} target="_blank" rel="noopener noreferrer" style={{ fontSize: 13 }}>
                        Voir l'offre ↗
                      </a>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  )
}
