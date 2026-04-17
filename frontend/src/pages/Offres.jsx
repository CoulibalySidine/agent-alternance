import { useState, useEffect, useCallback, useMemo } from 'react'
import {
  getOffres, deleteOffre, lancerScrape, scorerOffre, scorerBatch,
  genererDossier, ajouterSuivi, pollTask,
} from '../api'
import TaskBar from '../components/TaskBar'
import { showToast } from '../components/Toast'
import FreshnessPanel from '../components/FreshnessPanel'
import { getFraicheur, verifierOffres, supprimerAnciennes } from '../api'

const SCORE_CLS = (s) => s >= 70 ? 'score-high' : s >= 40 ? 'score-mid' : 'score-low'
const SCORE_COLOR = (s) => s >= 70 ? 'var(--green)' : s >= 40 ? 'var(--yellow)' : 'var(--red)'

export default function Offres() {
  const [offres, setOffres] = useState([])
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState(null)
  const [task, setTask] = useState(null)


  // Scrape modal
  const [showScrape, setShowScrape] = useState(false)
  const [scrapeMotCle, setScrapeMotCle] = useState('alternance développeur')
  const [scrapeVille, setScrapeVille] = useState('Paris')
  const [scraping, setScraping] = useState(false)
  const [fraicheur, setFraicheur] = useState(null)

  // Filters
  const [search, setSearch] = useState('')
  const [source, setSource] = useState('')
  const [scoreFilter, setScoreFilter] = useState('')
  const [scoreMin, setScoreMin] = useState(0)
  const [lieuFilter, setLieuFilter] = useState('')
  const [tri, setTri] = useState('score')
  const [ordre, setOrdre] = useState('desc')

  // Sélection batch
  const [selected, setSelected] = useState(new Set())

  const charger = useCallback(async () => {
    setLoading(true)
    try {
      const params = { tri, ordre, limit: 200 }
      if (search) params.recherche = search
      if (source) params.source = source
      if (scoreFilter === 'scored') params.scorees_only = true
      if (scoreFilter === 'unscored') params.non_scorees_only = true
      if (scoreFilter === '70+') { params.score_min = 70; params.scorees_only = true }
      if (scoreFilter === '40-69') { params.score_min = 40; params.score_max = 69; params.scorees_only = true }
      if (scoreFilter === '<40') { params.score_max = 39; params.scorees_only = true }
      if (scoreMin > 0) params.score_min = scoreMin
      if (lieuFilter) params.lieu = lieuFilter
      const data = await getOffres(params)
      setOffres(data)
    } catch (e) {
      showToast(e.message, 'error')
    }
    setLoading(false)
  }, [search, source, scoreFilter, scoreMin, lieuFilter, tri, ordre])

  useEffect(() => { charger() }, [charger])

  useEffect(() => { getFraicheur().then(setFraicheur).catch(() => {})}, [offres])

  // Lieux uniques pour le filtre
  const lieuxUniques = useMemo(() => {
    const lieux = new Set(offres.map(o => o.lieu).filter(Boolean))
    return [...lieux].sort()
  }, [offres])

  // --- Sélection ---
  const toggleSelect = (id) => {
    setSelected(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }
  const selectAll = () => {
    if (selected.size === offres.length) {
      setSelected(new Set())
    } else {
      setSelected(new Set(offres.map(o => o.id)))
    }
  }
  const clearSelection = () => setSelected(new Set())

  // --- Actions ---
  const handleScrape = async () => {
    setScraping(true)
    try {
      const res = await lancerScrape({ mot_cle: scrapeMotCle, ville: scrapeVille, sources: ['wttj', 'lba'] })
      showToast(`${res.nouvelles_offres} nouvelles offres collectées`)
      setShowScrape(false)
      charger()
    } catch (e) {
      showToast(e.message, 'error')
    }
    setScraping(false)
  }

  const handleScoreBatch = async (ids = null) => {
    try {
      const params = ids ? { offre_ids: ids } : { max_offres: 5 }
      const res = await scorerBatch(params)
      if (res.task_id === 'already_scored') {
        showToast('Toutes les offres sont déjà scorées')
        return
      }
      setTask(res)
      pollTask(res.task_id, (t) => {
        setTask(t)
        if (t.status === 'done') {
          showToast(`${t.result?.offres_scorees ?? 0} offres scorées`)
          charger()
          clearSelection()
        }
        if (t.status === 'error') showToast(t.error, 'error')
      })
    } catch (e) {
      showToast(e.message, 'error')
    }
  }

  const handleScoreOne = async (id) => {
    try {
      const res = await scorerOffre(id, true)
      if (res.status === 'done') { showToast('Offre scorée'); charger(); return }
      setTask(res)
      pollTask(res.task_id, (t) => {
        setTask(t)
        if (t.status === 'done') { showToast('Offre scorée'); charger() }
        if (t.status === 'error') showToast(t.error, 'error')
      })
    } catch (e) {
      showToast(e.message, 'error')
    }
  }

  const handleGenerer = async (id) => {
    try {
      const res = await genererDossier(id)
      setTask(res)
      pollTask(res.task_id, (t) => {
        setTask(t)
        if (t.status === 'done') showToast(`Dossier généré — ${t.result?.nombre_fichiers ?? 0} fichiers`)
        if (t.status === 'error') showToast(t.error, 'error')
      })
    } catch (e) {
      showToast(e.message, 'error')
    }
  }

  const handleAjouterSuivi = async (id) => {
    try {
      await ajouterSuivi(id)
      showToast('Ajouté au suivi')
    } catch (e) {
      showToast(e.message, 'error')
    }
  }

  const handleBatchSuivi = async () => {
    let ok = 0
    for (const id of selected) {
      try { await ajouterSuivi(id); ok++ } catch {}
    }
    showToast(`${ok} offre${ok > 1 ? 's' : ''} ajoutée${ok > 1 ? 's' : ''} au suivi`)
    clearSelection()
  }

  const handleBatchDelete = async () => {
    if (!confirm(`Supprimer ${selected.size} offre${selected.size > 1 ? 's' : ''} ?`)) return
    let ok = 0
    for (const id of selected) {
      try { await deleteOffre(id); ok++ } catch {}
    }
    showToast(`${ok} offre${ok > 1 ? 's' : ''} supprimée${ok > 1 ? 's' : ''}`)
    clearSelection()
    charger()
  }

  const resetFilters = () => {
    setSearch(''); setSource(''); setScoreFilter(''); setScoreMin(0); setLieuFilter('')
    setTri('score'); setOrdre('desc')
  }

  // --- Stats ---
  const total = offres.length
  const scored = offres.filter(o => o.score != null).length
  const avgScore = scored > 0
    ? Math.round(offres.filter(o => o.score != null).reduce((a, o) => a + o.score, 0) / scored)
    : null

  const hasActiveFilters = search || source || scoreFilter || scoreMin > 0 || lieuFilter

  return (
    <div>
      <div className="page-head">
        <h1><span>📋</span> Offres</h1>
        <div className="btn-group">
          <button className="btn" onClick={() => setShowScrape(true)}>
            🔍 Scraper des offres
          </button>
          <button className="btn btn-primary" onClick={() => handleScoreBatch()} disabled={task?.status === 'running'}>
            🎯 Scorer (5 offres)
          </button>
        </div>
      </div>

      {/* Scrape modal */}
      {showScrape && (
        <div className="modal-backdrop" onClick={() => !scraping && setShowScrape(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>🔍 Scraper des offres</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div>
                <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>
                  Mots-clés
                </label>
                <input
                  className="search-input" style={{ width: '100%' }}
                  value={scrapeMotCle} onChange={e => setScrapeMotCle(e.target.value)}
                  placeholder="alternance développeur Python"
                />
              </div>
              <div>
                <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>
                  Ville
                </label>
                <input
                  className="search-input" style={{ width: '100%' }}
                  value={scrapeVille} onChange={e => setScrapeVille(e.target.value)}
                  placeholder="Paris"
                />
              </div>
              <div>
  <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>
    Sources
  </label>
  <div style={{ display: 'flex', gap: 8 }}>
    {[
      { id: 'lba', label: '🏛️ La bonne alternance' },
      { id: 'wttj', label: '🌴 WTTJ' },
    ].map(s => (
      <label key={s.id} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 12.5, cursor: 'pointer' }}>
        <input type="checkbox" defaultChecked style={{ accentColor: 'var(--accent)' }}
          onChange={e => {/* gérer la sélection */}} />
        {s.label}
      </label>
    ))}
  </div>
</div>
            </div>
            <div className="modal-actions">
              <button className="btn" onClick={() => setShowScrape(false)} disabled={scraping}>Annuler</button>
              <button className="btn btn-primary" onClick={handleScrape} disabled={scraping}>
                {scraping ? '⏳ Scraping...' : '🔍 Lancer'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Stats */}
      <div className="stats-row">
        <div className="stat-card highlight"><div className="num">{total}</div><div className="label">Total</div></div>
        <div className="stat-card"><div className="num">{scored}</div><div className="label">Scorées</div></div>
        <div className="stat-card"><div className="num">{total - scored}</div><div className="label">À scorer</div></div>
        {avgScore != null && <div className="stat-card"><div className="num">{avgScore}</div><div className="label">Score moyen</div></div>}
      </div>

      <TaskBar task={task} />
      <FreshnessPanel
        fraicheur={fraicheur}
        onCleanup={supprimerAnciennes}
        onVerify={verifierOffres}
        onRefresh={() => { charger(); getFraicheur().then(setFraicheur) }}
      />

      {/* Toolbar améliorée */}
      <div className="toolbar" style={{ flexWrap: 'wrap' }}>
        <input
          className="search-input"
          placeholder="Rechercher titre, entreprise, description..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{ minWidth: 260 }}
        />
        <select className="filter" value={source} onChange={e => setSource(e.target.value)}>
          <option value="">Toutes sources</option>
          <option value="wttj">WTTJ</option>
          <option value="indeed">Indeed</option>
          <option value="demo">Demo</option>
        </select>
        <select className="filter" value={lieuFilter} onChange={e => setLieuFilter(e.target.value)}>
          <option value="">Tous lieux</option>
          {lieuxUniques.map(l => <option key={l} value={l}>{l}</option>)}
        </select>
        <select className="filter" value={scoreFilter} onChange={e => setScoreFilter(e.target.value)}>
          <option value="">Tous scores</option>
          <option value="scored">Scorées</option>
          <option value="unscored">Non scorées</option>
          <option value="70+">≥ 70</option>
          <option value="40-69">40–69</option>
          <option value="<40">{'< 40'}</option>
        </select>
        <select className="filter" value={`${tri}-${ordre}`} onChange={e => { const [t, o] = e.target.value.split('-'); setTri(t); setOrdre(o) }}>
          <option value="score-desc">Score ↓</option>
          <option value="score-asc">Score ↑</option>
          <option value="entreprise-asc">Entreprise A-Z</option>
          <option value="date-desc">Plus récent</option>
        </select>
        {hasActiveFilters && (
          <button
            className="btn btn-sm"
            onClick={resetFilters}
            style={{ color: 'var(--red)', borderColor: 'var(--red)' }}
          >✕ Réinitialiser</button>
        )}
      </div>

      {/* Slider score minimum */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 10,
        marginBottom: 12, padding: '0 2px',
      }}>
        <span style={{ fontSize: 11, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
          Score min :
        </span>
        <input
          type="range" min={0} max={100} step={5}
          value={scoreMin}
          onChange={e => setScoreMin(Number(e.target.value))}
          style={{
            flex: 1, maxWidth: 200, accentColor: SCORE_COLOR(scoreMin),
            cursor: 'pointer',
          }}
        />
        <span style={{
          fontFamily: 'var(--mono)', fontSize: 12, fontWeight: 600,
          color: scoreMin > 0 ? SCORE_COLOR(scoreMin) : 'var(--text-muted)',
          minWidth: 28, textAlign: 'right',
        }}>
          {scoreMin > 0 ? scoreMin : '—'}
        </span>
      </div>

      <div className="count-bar" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span>{total} offre{total > 1 ? 's' : ''}</span>
        <button
          className="btn btn-sm"
          onClick={selectAll}
          style={{ fontSize: 10, padding: '3px 8px' }}
        >
          {selected.size === offres.length && offres.length > 0 ? 'Tout désélectionner' : 'Tout sélectionner'}
        </button>
      </div>

      {/* Table */}
      {loading ? (
        <div className="empty">Chargement...</div>
      ) : offres.length === 0 ? (
        <div className="empty">
          {hasActiveFilters
            ? 'Aucune offre ne correspond aux filtres. Essaie de réinitialiser.'
            : 'Aucune offre. Clique sur "Scraper des offres" pour commencer.'}
        </div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th style={{ width: 32 }}>
                  <input
                    type="checkbox"
                    checked={selected.size === offres.length && offres.length > 0}
                    onChange={selectAll}
                    style={{ cursor: 'pointer', accentColor: 'var(--accent)' }}
                  />
                </th>
                <th style={{ width: 80 }}>Score</th>
                <th>Poste</th>
                <th>Lieu</th>
                <th>Source</th>
                <th style={{ width: 150 }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {offres.map(o => (
                <OffreRow
                  key={o.id}
                  offre={o}
                  isOpen={expanded === o.id}
                  isSelected={selected.has(o.id)}
                  onToggle={() => setExpanded(expanded === o.id ? null : o.id)}
                  onSelect={() => toggleSelect(o.id)}
                  onScore={() => handleScoreOne(o.id)}
                  onGenerer={() => handleGenerer(o.id)}
                  onAjouterSuivi={() => handleAjouterSuivi(o.id)}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Barre d'actions flottante (sélection) */}
      {selected.size > 0 && (
        <div style={{
          position: 'fixed', bottom: 20, left: '50%', transform: 'translateX(-50%)',
          background: 'var(--surface-3)', border: '1px solid var(--border)',
          borderRadius: 'var(--radius)', padding: '10px 20px',
          display: 'flex', alignItems: 'center', gap: 12,
          boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
          zIndex: 100, animation: 'slideIn 0.2s ease-out',
        }}>
          <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--accent)' }}>
            {selected.size} sélectionnée{selected.size > 1 ? 's' : ''}
          </span>
          <div style={{ width: 1, height: 20, background: 'var(--border)' }} />
          <button className="btn btn-sm btn-primary" onClick={() => handleScoreBatch()}>
            🎯 Scorer
          </button>
          <button className="btn btn-sm" onClick={handleBatchSuivi}>
            📌 Ajouter au suivi
          </button>
          <button className="btn btn-sm btn-danger" onClick={handleBatchDelete}>
            🗑️ Supprimer
          </button>
          <div style={{ width: 1, height: 20, background: 'var(--border)' }} />
          <button
            className="btn btn-sm"
            onClick={clearSelection}
            style={{ color: 'var(--text-muted)', fontSize: 11 }}
          >✕</button>
        </div>
      )}
    </div>
  )
}

// ============================================================
// Ligne d'offre avec checkbox et barre de score visuelle
// ============================================================

function OffreRow({ offre: o, isOpen, isSelected, onToggle, onSelect, onScore, onGenerer, onAjouterSuivi }) {
  return (
    <>
      <tr
        onClick={onToggle}
        style={{
          cursor: 'pointer',
          background: isSelected ? 'var(--accent-dim)' : undefined,
        }}
      >
        <td onClick={e => e.stopPropagation()}>
          <input
            type="checkbox"
            checked={isSelected}
            onChange={onSelect}
            style={{ cursor: 'pointer', accentColor: 'var(--accent)' }}
          />
        </td>
        <td>
          {o.score != null ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span className={`score ${SCORE_CLS(o.score)}`}>{Math.round(o.score)}</span>
              <div style={{
                flex: 1, height: 4, background: 'var(--surface-3)',
                borderRadius: 2, overflow: 'hidden', minWidth: 30,
              }}>
                <div style={{
                  width: `${o.score}%`, height: '100%',
                  background: SCORE_COLOR(o.score),
                  borderRadius: 2, transition: 'width 0.3s',
                }} />
              </div>
            </div>
          ) : (
            <span className="score-none">—</span>
          )}
        </td>
        <td>
          <strong>{o.titre}</strong><br />
          <span className="sub">{o.entreprise}</span>
        </td>
        <td><span className="sub">{o.lieu}</span></td>
        <td><span className="mono">{o.source}</span></td>
        <td onClick={e => e.stopPropagation()}>
          <div className="btn-group">
            <button className="btn btn-sm" onClick={onScore} title="Scorer cette offre">🎯</button>
            <button className="btn btn-sm" onClick={onGenerer} title="Générer le dossier" disabled={o.score == null}>📁</button>
            <button className="btn btn-sm" onClick={onAjouterSuivi} title="Ajouter au suivi">📌</button>
          </div>
        </td>
      </tr>
      {isOpen && (
        <tr>
          <td colSpan={6} style={{ padding: 0 }}>
            <div className="expand-content">
              <div className="expand-grid">
                <div>
                  <h4>Description</h4>
                  <p style={{ fontSize: 12.5, color: 'var(--text-muted)', lineHeight: 1.5, maxHeight: 120, overflow: 'auto' }}>
                    {o.description || 'Pas de description'}
                  </p>
                </div>
                <div>
                  {o.score != null && (
                    <>
                      <h4>Analyse IA</h4>
                      {o.raison_score && <p style={{ fontSize: 12.5, marginBottom: 8 }}>{o.raison_score}</p>}
                      {o.points_forts?.length > 0 && (
                        <>
                          <h4 style={{ marginTop: 8 }}>Points forts</h4>
                          <ul>{o.points_forts.map((p, i) => <li key={i}>{p}</li>)}</ul>
                        </>
                      )}
                      {o.points_faibles?.length > 0 && (
                        <>
                          <h4 style={{ marginTop: 8 }}>Points faibles</h4>
                          <ul>{o.points_faibles.map((p, i) => <li key={i}>{p}</li>)}</ul>
                        </>
                      )}
                      {o.conseil && (
                        <>
                          <h4 style={{ marginTop: 8 }}>Conseil</h4>
                          <p style={{ fontSize: 12.5, color: 'var(--accent)' }}>{o.conseil}</p>
                        </>
                      )}
                    </>
                  )}
                  {o.url && (
                    <div style={{ marginTop: 12 }}>
                      <a href={o.url} target="_blank" rel="noopener noreferrer" style={{ fontSize: 13 }}>
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
