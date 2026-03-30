import { useState, useEffect, useCallback } from 'react'
import {
  getOffres, lancerScrape, scorerOffre, scorerBatch,
  genererDossier, ajouterSuivi, pollTask,
} from '../api'
import TaskBar from '../components/TaskBar'
import { showToast } from '../components/Toast'

const SCORE_CLS = (s) => s >= 70 ? 'score-high' : s >= 40 ? 'score-mid' : 'score-low'

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

  // Filters
  const [search, setSearch] = useState('')
  const [source, setSource] = useState('')
  const [scoreFilter, setScoreFilter] = useState('')
  const [tri, setTri] = useState('score')
  const [ordre, setOrdre] = useState('desc')

  const charger = useCallback(async () => {
    setLoading(true)
    try {
      const params = { tri, ordre, limit: 100 }
      if (search) params.recherche = search
      if (source) params.source = source
      if (scoreFilter === 'scored') params.scorees_only = true
      if (scoreFilter === 'unscored') params.non_scorees_only = true
      if (scoreFilter === '70+') { params.score_min = 70; params.scorees_only = true }
      if (scoreFilter === '40-69') { params.score_min = 40; params.score_max = 69; params.scorees_only = true }
      if (scoreFilter === '<40') { params.score_max = 39; params.scorees_only = true }
      const data = await getOffres(params)
      setOffres(data)
    } catch (e) {
      showToast(e.message, 'error')
    }
    setLoading(false)
  }, [search, source, scoreFilter, tri, ordre])

  useEffect(() => { charger() }, [charger])

  // --- Actions ---
  const handleScrape = async () => {
    setScraping(true)
    try {
      const res = await lancerScrape({ mot_cle: scrapeMotCle, ville: scrapeVille })
      showToast(`${res.nouvelles_offres} nouvelles offres collectées`)
      setShowScrape(false)
      charger()
    } catch (e) {
      showToast(e.message, 'error')
    }
    setScraping(false)
  }

  const handleScoreBatch = async () => {
    try {
      const res = await scorerBatch({ max_offres: 5 })
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

  // --- Stats ---
  const total = offres.length
  const scored = offres.filter(o => o.score != null).length
  const avgScore = scored > 0
    ? Math.round(offres.filter(o => o.score != null).reduce((a, o) => a + o.score, 0) / scored)
    : null

  return (
    <div>
      <div className="page-head">
        <h1><span>📋</span> Offres</h1>
        <div className="btn-group">
          <button className="btn" onClick={() => setShowScrape(true)}>
            🔍 Scraper des offres
          </button>
          <button className="btn btn-primary" onClick={handleScoreBatch} disabled={task?.status === 'running'}>
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
                  className="search-input"
                  style={{ width: '100%' }}
                  value={scrapeMotCle}
                  onChange={e => setScrapeMotCle(e.target.value)}
                  placeholder="alternance développeur Python"
                />
              </div>
              <div>
                <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>
                  Ville
                </label>
                <input
                  className="search-input"
                  style={{ width: '100%' }}
                  value={scrapeVille}
                  onChange={e => setScrapeVille(e.target.value)}
                  placeholder="Paris"
                />
              </div>
            </div>
            <div className="modal-actions">
              <button className="btn" onClick={() => setShowScrape(false)} disabled={scraping}>
                Annuler
              </button>
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

      {/* Toolbar */}
      <div className="toolbar">
        <input
          className="search-input"
          placeholder="Rechercher (titre, entreprise…)"
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        <select className="filter" value={source} onChange={e => setSource(e.target.value)}>
          <option value="">Toutes les sources</option>
          <option value="wttj">WTTJ</option>
          <option value="indeed">Indeed</option>
          <option value="demo">Demo</option>
        </select>
        <select className="filter" value={scoreFilter} onChange={e => setScoreFilter(e.target.value)}>
          <option value="">Tous les scores</option>
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
      </div>

      <div className="count-bar">{total} offre{total > 1 ? 's' : ''}</div>

      {/* Table */}
      {loading ? (
        <div className="empty">Chargement...</div>
      ) : offres.length === 0 ? (
        <div className="empty">Aucune offre. Clique sur "Scraper des offres" pour commencer.</div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th style={{ width: 65 }}>Score</th>
                <th>Poste</th>
                <th>Lieu</th>
                <th>Source</th>
                <th style={{ width: 180 }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {offres.map(o => (
                <OffreRow
                  key={o.id}
                  offre={o}
                  isOpen={expanded === o.id}
                  onToggle={() => setExpanded(expanded === o.id ? null : o.id)}
                  onScore={() => handleScoreOne(o.id)}
                  onGenerer={() => handleGenerer(o.id)}
                  onAjouterSuivi={() => handleAjouterSuivi(o.id)}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function OffreRow({ offre: o, isOpen, onToggle, onScore, onGenerer, onAjouterSuivi }) {
  return (
    <>
      <tr onClick={onToggle} style={{ cursor: 'pointer' }}>
        <td>
          {o.score != null
            ? <span className={`score ${SCORE_CLS(o.score)}`}>{Math.round(o.score)}</span>
            : <span className="score-none">—</span>}
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
          <td colSpan={5} style={{ padding: 0 }}>
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
