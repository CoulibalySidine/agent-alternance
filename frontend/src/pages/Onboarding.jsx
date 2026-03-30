import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { uploadCV, getProfil, updateProfil, deleteProfil } from '../api'
import { showToast } from '../components/Toast'

export default function Onboarding() {
  const [file, setFile] = useState(null)
  const [metier, setMetier] = useState('')
  const [ville, setVille] = useState('')
  const [loading, setLoading] = useState(false)
  const [profil, setProfil] = useState(null)
  const [editMode, setEditMode] = useState(false)
  const [editContent, setEditContent] = useState('')
  const [dragOver, setDragOver] = useState(false)
  const fileRef = useRef()
  const navigate = useNavigate()

  // Charger le profil existant
  useEffect(() => {
    getProfil().then(p => {
      if (p.existe) setProfil(p.contenu)
    }).catch(() => {})
  }, [])

  const handleUpload = async () => {
    if (!file) { showToast('Sélectionne un CV', 'error'); return }
    setLoading(true)
    try {
      const res = await uploadCV(file, metier, ville)
      showToast('Profil généré avec succès !')
      // Recharger le profil
      const p = await getProfil()
      setProfil(p.contenu)
    } catch (e) {
      showToast(e.message, 'error')
    }
    setLoading(false)
  }

  const handleSaveEdit = async () => {
    try {
      await updateProfil(editContent)
      setProfil(editContent)
      setEditMode(false)
      showToast('Profil mis à jour')
    } catch (e) {
      showToast(e.message, 'error')
    }
  }

  const handleReset = async () => {
    if (!confirm('Supprimer le profil actuel ?')) return
    try {
      await deleteProfil()
      setProfil(null)
      setFile(null)
      showToast('Profil supprimé')
    } catch (e) {
      showToast(e.message, 'error')
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    const f = e.dataTransfer.files[0]
    if (f) setFile(f)
  }

  // Si un profil existe → mode "profil actif"
  if (profil && !editMode) {
    return (
      <div>
        <div className="page-head">
          <h1><span>👤</span> Profil actif</h1>
          <div className="btn-group">
            <button className="btn" onClick={() => { setEditContent(profil); setEditMode(true) }}>
              ✏️ Modifier
            </button>
            <button className="btn btn-danger" onClick={handleReset}>
              🗑️ Réinitialiser
            </button>
            <button className="btn btn-primary" onClick={() => navigate('/offres')}>
              📋 Voir les offres →
            </button>
          </div>
        </div>

        <div style={{
          background: 'var(--green-dim)', border: '1px solid rgba(63,185,80,0.3)',
          borderRadius: 'var(--radius)', padding: '12px 16px', marginBottom: 20,
          fontSize: 13, color: 'var(--green)',
        }}>
          ✅ Profil chargé — tu peux scraper des offres et lancer le scoring.
        </div>

        <div style={{
          background: 'var(--surface)', border: '1px solid var(--border)',
          borderRadius: 'var(--radius)', padding: '20px',
        }}>
          <pre style={{
            fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--text-muted)',
            whiteSpace: 'pre-wrap', lineHeight: 1.6, maxHeight: 500, overflow: 'auto',
          }}>
            {profil}
          </pre>
        </div>
      </div>
    )
  }

  // Mode édition
  if (editMode) {
    return (
      <div>
        <div className="page-head">
          <h1><span>✏️</span> Modifier le profil</h1>
          <div className="btn-group">
            <button className="btn" onClick={() => setEditMode(false)}>Annuler</button>
            <button className="btn btn-primary" onClick={handleSaveEdit}>💾 Sauvegarder</button>
          </div>
        </div>

        <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 12 }}>
          Corrige les informations si Claude a mal extrait quelque chose. Le format est YAML.
        </p>

        <textarea
          value={editContent}
          onChange={e => setEditContent(e.target.value)}
          style={{
            width: '100%', minHeight: 500, background: 'var(--surface)',
            border: '1px solid var(--border)', borderRadius: 'var(--radius)',
            padding: 16, fontFamily: 'var(--mono)', fontSize: 12,
            color: 'var(--text)', resize: 'vertical', outline: 'none',
            lineHeight: 1.6,
          }}
        />
      </div>
    )
  }

  // Mode onboarding (pas de profil)
  return (
    <div>
      <div className="page-head">
        <h1><span>🚀</span> Bienvenue</h1>
      </div>

      <p style={{ fontSize: 14, color: 'var(--text-muted)', marginBottom: 28, maxWidth: 600, lineHeight: 1.6 }}>
        Upload ton CV, indique le poste et la ville que tu cherches.
        L'agent IA analyse ton profil, collecte des offres, les score, et génère tes candidatures.
      </p>

      {/* Drop zone */}
      <div
        onDragOver={e => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => fileRef.current?.click()}
        style={{
          background: dragOver ? 'var(--accent-dim)' : 'var(--surface)',
          border: `2px dashed ${dragOver ? 'var(--accent)' : 'var(--border)'}`,
          borderRadius: 'var(--radius)',
          padding: '40px 20px',
          textAlign: 'center',
          cursor: 'pointer',
          transition: 'all 0.2s',
          marginBottom: 20,
        }}
      >
        <input
          ref={fileRef}
          type="file"
          accept=".pdf,.docx,.txt"
          style={{ display: 'none' }}
          onChange={e => setFile(e.target.files[0])}
        />
        <div style={{ fontSize: 32, marginBottom: 8 }}>
          {file ? '📄' : '📎'}
        </div>
        {file ? (
          <div>
            <strong style={{ fontSize: 14 }}>{file.name}</strong>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
              {(file.size / 1024).toFixed(0)} Ko — Clic pour changer
            </div>
          </div>
        ) : (
          <div>
            <strong style={{ fontSize: 14 }}>Glisse ton CV ici</strong>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
              PDF, Word ou texte — ou clic pour sélectionner
            </div>
          </div>
        )}
      </div>

      {/* Champs métier et ville */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 24 }}>
        <div>
          <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
            Quel poste recherches-tu ?
          </label>
          <input
            className="search-input"
            style={{ width: '100%' }}
            placeholder="Ex : développeur Python, data analyst, DevOps…"
            value={metier}
            onChange={e => setMetier(e.target.value)}
          />
        </div>
        <div>
          <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
            Où ?
          </label>
          <input
            className="search-input"
            style={{ width: '100%' }}
            placeholder="Ex : Paris, Lyon, Île-de-France…"
            value={ville}
            onChange={e => setVille(e.target.value)}
          />
        </div>
      </div>

      {/* Bouton */}
      <button
        className="btn btn-primary"
        onClick={handleUpload}
        disabled={loading || !file}
        style={{ fontSize: 14, padding: '12px 28px' }}
      >
        {loading ? (
          <>
            <span className="spinner" style={{ width: 14, height: 14, display: 'inline-block', verticalAlign: 'middle', marginRight: 8 }} />
            Analyse du CV en cours...
          </>
        ) : (
          "🚀 Analyser mon CV"
        )}
      </button>

      {loading && (
        <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 12 }}>
          Claude lit ton CV et génère ton profil... (~10 secondes)
        </p>
      )}
    </div>
  )
}
