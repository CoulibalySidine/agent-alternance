import { useState, useEffect, useCallback, useRef } from 'react'
import { getSuivi, getSuiviStats, changerEtat, retirerSuivi } from '../api'
import { showToast } from '../components/Toast'
import StatsDetailed from '../components/StatsDetailed'
import { getSuiviStatsDetailed } from '../api'

// ============================================================
// Constantes
// ============================================================

const ETATS = {
  brouillon: '📝', envoyee: '📤', vue: '👁️',
  entretien: '🎤', acceptee: '✅', refusee: '❌', sans_reponse: '⏳',
}
const ETAT_LABELS = {
  brouillon: 'Brouillon', envoyee: 'Envoyée', vue: 'Vue',
  entretien: 'Entretien', acceptee: 'Acceptée', refusee: 'Refusée', sans_reponse: 'Sans réponse',
}
const ETAT_COLORS = {
  brouillon: 'var(--text-muted)',
  envoyee: 'var(--accent)',
  vue: 'var(--purple)',
  entretien: 'var(--yellow)',
  acceptee: 'var(--green)',
  refusee: 'var(--red)',
  sans_reponse: 'var(--text-muted)',
}

// Colonnes du kanban : pipeline principal + résultats
const KANBAN_COLS = [
  { id: 'brouillon', label: 'Brouillon', icon: '📝', color: 'var(--text-muted)' },
  { id: 'envoyee', label: 'Envoyée', icon: '📤', color: 'var(--accent)' },
  { id: 'vue', label: 'Vue', icon: '👁️', color: 'var(--purple)' },
  { id: 'entretien', label: 'Entretien', icon: '🎤', color: 'var(--yellow)' },
  { id: 'acceptee', label: 'Acceptée', icon: '✅', color: 'var(--green)' },
  { id: 'refusee', label: 'Refusée', icon: '❌', color: 'var(--red)' },
  { id: 'sans_reponse', label: 'Sans réponse', icon: '⏳', color: 'var(--text-muted)' },
]

const ETAT_ORDER = KANBAN_COLS.map(c => c.id)
const SCORE_CLS = (s) => s >= 70 ? 'score-high' : s >= 40 ? 'score-mid' : 'score-low'

// ============================================================
// Composant principal
// ============================================================

export default function Dashboard() {
  const [candidatures, setCandidatures] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [viewMode, setViewMode] = useState('kanban') // 'kanban' | 'table'
  const [expanded, setExpanded] = useState(null)
  const [filterEtat, setFilterEtat] = useState('')
  const [detailedStats, setDetailedStats] = useState(null)

  const charger = useCallback(async () => {
    setLoading(true)
    try {
      const params = {}
      if (filterEtat && viewMode === 'table') params.etat = filterEtat
      const [s, st] = await Promise.all([getSuivi(params), getSuiviStats()])
      getSuiviStatsDetailed().then(setDetailedStats).catch(() => {})
      setCandidatures(s)
      setStats(st)
    } catch (e) {
      showToast(e.message, 'error')
    }
    setLoading(false)
  }, [filterEtat, viewMode])

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

  const relances = candidatures.filter(c => c.doit_relancer)
  

  return (
    <div>
      <div className="page-head">
        <h1><span>📊</span> Suivi des candidatures</h1>
        <div className="btn-group">
          <button
          
            className={`btn ${viewMode === 'kanban' ? 'btn-primary' : ''}`}
            onClick={() => setViewMode('kanban')}
          >▦ Kanban</button>
          <button
            className={`btn ${viewMode === 'table' ? 'btn-primary' : ''}`}
            onClick={() => setViewMode('table')}
          >☰ Table</button>
        </div>
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
          borderRadius: 'var(--radius)', padding: '12px 16px', marginBottom: 16,
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
      <StatsDetailed stats={detailedStats} />

      {loading ? (
        <div className="empty">Chargement...</div>
      ) : candidatures.length === 0 ? (
        <div className="empty">
          Aucune candidature dans le suivi. Ajoute des offres depuis la page Offres.
        </div>
      ) : viewMode === 'kanban' ? (
        <KanbanBoard
          candidatures={candidatures}
          onChangerEtat={handleChangerEtat}
          onRetirer={handleRetirer}
        />
      ) : (
        <TableView
          candidatures={candidatures}
          expanded={expanded}
          setExpanded={setExpanded}
          filterEtat={filterEtat}
          setFilterEtat={setFilterEtat}
          onChangerEtat={handleChangerEtat}
          onRetirer={handleRetirer}
        />
      )}
    </div>
  )
}

// ============================================================
// VUE KANBAN
// ============================================================

function KanbanBoard({ candidatures, onChangerEtat, onRetirer }) {
  const [draggedId, setDraggedId] = useState(null)
  const [dragOverCol, setDragOverCol] = useState(null)

  const handleDragStart = (e, offreId) => {
    setDraggedId(offreId)
    e.dataTransfer.effectAllowed = 'move'
    // Pour Firefox
    e.dataTransfer.setData('text/plain', offreId)
  }

  const handleDragOver = (e, colId) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
    setDragOverCol(colId)
  }

  const handleDragLeave = () => {
    setDragOverCol(null)
  }

  const handleDrop = (e, colId) => {
    e.preventDefault()
    setDragOverCol(null)
    if (draggedId) {
      const card = candidatures.find(c => c.offre_id === draggedId)
      if (card && card.etat !== colId) {
        onChangerEtat(draggedId, colId)
      }
    }
    setDraggedId(null)
  }

  const handleDragEnd = () => {
    setDraggedId(null)
    setDragOverCol(null)
  }

  return (
    <div style={{
      display: 'flex', gap: 10, overflowX: 'auto',
      paddingBottom: 16, minHeight: 400,
    }}>
      {KANBAN_COLS.map(col => {
        const cards = candidatures.filter(c => c.etat === col.id)
        const isOver = dragOverCol === col.id
        const hasDragged = draggedId && candidatures.find(c => c.offre_id === draggedId)?.etat !== col.id

        return (
          <div
            key={col.id}
            onDragOver={e => handleDragOver(e, col.id)}
            onDragLeave={handleDragLeave}
            onDrop={e => handleDrop(e, col.id)}
            style={{
              flex: '1 0 170px',
              maxWidth: 260,
              minWidth: 170,
              display: 'flex',
              flexDirection: 'column',
            }}
          >
            {/* Header colonne */}
            <div style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '8px 10px', marginBottom: 8,
              borderBottom: `2px solid ${col.color}`,
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ fontSize: 14 }}>{col.icon}</span>
                <span style={{
                  fontSize: 12, fontWeight: 600, color: col.color,
                  textTransform: 'uppercase', letterSpacing: '0.3px',
                }}>{col.label}</span>
              </div>
              <span style={{
                fontSize: 11, fontFamily: 'var(--mono)', color: 'var(--text-muted)',
                background: 'var(--surface)', padding: '1px 6px', borderRadius: 4,
              }}>{cards.length}</span>
            </div>

            {/* Zone de drop */}
            <div style={{
              flex: 1,
              background: isOver && hasDragged ? 'var(--surface-2)' : 'transparent',
              border: isOver && hasDragged
                ? `2px dashed ${col.color}`
                : '2px dashed transparent',
              borderRadius: 'var(--radius)',
              padding: 4,
              transition: 'all 0.15s',
              minHeight: 80,
            }}>
              {cards.length === 0 && !isOver && (
                <div style={{
                  textAlign: 'center', padding: '20px 8px',
                  fontSize: 11, color: 'var(--text-muted)', opacity: 0.5,
                }}>
                  Glisse une carte ici
                </div>
              )}

              {cards.map(c => (
                <KanbanCard
                  key={c.offre_id}
                  c={c}
                  isDragged={draggedId === c.offre_id}
                  onDragStart={e => handleDragStart(e, c.offre_id)}
                  onDragEnd={handleDragEnd}
                  onRetirer={() => onRetirer(c.offre_id)}
                />
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ============================================================
// Carte Kanban
// ============================================================

function KanbanCard({ c, isDragged, onDragStart, onDragEnd, onRetirer }) {
  const [showDetail, setShowDetail] = useState(false)

  return (
    <div
      draggable
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
      onClick={() => setShowDetail(!showDetail)}
      style={{
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: 8,
        padding: '10px 12px',
        marginBottom: 6,
        cursor: 'grab',
        opacity: isDragged ? 0.4 : 1,
        transition: 'all 0.15s',
        position: 'relative',
      }}
      onMouseOver={e => {
        if (!isDragged) e.currentTarget.style.borderColor = ETAT_COLORS[c.etat]
      }}
      onMouseOut={e => {
        e.currentTarget.style.borderColor = 'var(--border)'
      }}
    >
      {/* Score badge */}
      {c.score != null && (
        <span style={{
          position: 'absolute', top: 8, right: 8,
          fontSize: 11, fontFamily: 'var(--mono)', fontWeight: 600,
          padding: '1px 6px', borderRadius: 4,
          background: c.score >= 70
            ? 'var(--green-dim)' : c.score >= 40
            ? 'var(--yellow-dim)' : 'var(--red-dim)',
          color: c.score >= 70
            ? 'var(--green)' : c.score >= 40
            ? 'var(--yellow)' : 'var(--red)',
        }}>{Math.round(c.score)}</span>
      )}

      {/* Titre */}
      <div style={{
        fontSize: 12.5, fontWeight: 600, color: 'var(--text)',
        marginBottom: 4, paddingRight: c.score != null ? 36 : 0,
        lineHeight: 1.3,
      }}>
        {c.titre}
      </div>

      {/* Entreprise */}
      <div style={{ fontSize: 11.5, color: 'var(--text-muted)', marginBottom: 2 }}>
        {c.entreprise}
      </div>

      {/* Lieu */}
      {c.lieu && (
        <div style={{ fontSize: 11, color: 'var(--text-muted)', opacity: 0.7 }}>
          📍 {c.lieu}
        </div>
      )}

      {/* Badge relance */}
      {c.doit_relancer && (
        <div style={{
          marginTop: 6, fontSize: 10, padding: '2px 6px', borderRadius: 4,
          background: 'var(--red-dim)', color: 'var(--red)',
          fontWeight: 600, display: 'inline-block',
        }}>
          🔔 RELANCER
        </div>
      )}

      {/* Jours depuis envoi */}
      {c.jours_depuis_envoi != null && c.etat !== 'brouillon' && (
        <div style={{
          marginTop: 4, fontSize: 10, color: 'var(--text-muted)',
          fontFamily: 'var(--mono)',
        }}>
          J+{c.jours_depuis_envoi}
        </div>
      )}

      {/* Détail dépliable */}
      {showDetail && (
        <div
          onClick={e => e.stopPropagation()}
          style={{
            marginTop: 8, paddingTop: 8,
            borderTop: '1px solid var(--border)', fontSize: 11,
          }}
        >
          {/* Historique */}
          <div style={{ color: 'var(--text-muted)', marginBottom: 6 }}>
            <strong style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.3px' }}>
              Historique
            </strong>
            {c.historique?.map((h, i) => (
              <div key={i} style={{ padding: '2px 0' }}>
                <span style={{ fontFamily: 'var(--mono)', fontSize: 10 }}>{h.date?.slice(0, 10)}</span>
                {' '}{ETATS[h.etat] || '❓'} {h.etat}
                {h.commentaire ? ` — ${h.commentaire}` : ''}
              </div>
            ))}
          </div>

          {/* Lien + supprimer */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 6 }}>
            {c.url && (
              <a href={c.url} target="_blank" rel="noopener noreferrer"
                style={{ fontSize: 11, color: 'var(--accent)' }}
              >Voir l'offre ↗</a>
            )}
            <button
              onClick={() => onRetirer()}
              style={{
                background: 'none', border: 'none', fontSize: 11,
                color: 'var(--red)', cursor: 'pointer', padding: '2px 6px',
              }}
            >🗑️ Retirer</button>
          </div>
        </div>
      )}
    </div>
  )
}

// ============================================================
// VUE TABLE (existante, conservée)
// ============================================================

function TableView({ candidatures, expanded, setExpanded, filterEtat, setFilterEtat, onChangerEtat, onRetirer }) {
  return (
    <>
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
                onChangerEtat={onChangerEtat}
                onRetirer={onRetirer}
              />
            ))}
          </tbody>
        </table>
      </div>
    </>
  )
}

// ============================================================
// Ligne de table (conservée de l'original)
// ============================================================

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
                    {c.historique?.map((h, i) => (
                      <li key={i}>
                        {h.date?.slice(0, 10)} — {ETATS[h.etat] || '❓'} {h.etat}
                        {h.commentaire ? ` : ${h.commentaire}` : ''}
                      </li>
                    ))}
                  </ul>
                </div>
                <div>
                  <h4>Notes</h4>
                  {c.notes?.length > 0
                    ? <ul>{c.notes.map((n, i) => <li key={i}>{n.texte || n}</li>)}</ul>
                    : <span className="sub">Aucune note</span>
                  }
                </div>
                <div>
                  <h4>Offre</h4>
                  {c.url
                    ? <a href={c.url} target="_blank" rel="noopener noreferrer">Voir l'offre ↗</a>
                    : <span className="sub">Pas de lien</span>
                  }
                </div>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  )
}
