import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { uploadCV, getProfil, getProfilParsed, updateProfilStructured, deleteProfil } from '../api'
import { showToast } from '../components/Toast'
import ProfileEditor from '../components/ProfileEditor'

export default function Onboarding() {
  const [file, setFile] = useState(null)
  const [metier, setMetier] = useState('')
  const [ville, setVille] = useState('')
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)

  // Profil : null = pas de profil, objet = profil chargé
  const [profil, setProfil] = useState(null)
  const [profilExiste, setProfilExiste] = useState(false)

  // Mode : 'onboarding' | 'editor' | 'yaml' (fallback si parsing échoue)
  const [mode, setMode] = useState('onboarding')
  const [yamlBrut, setYamlBrut] = useState('')

  const [dragOver, setDragOver] = useState(false)
  const fileRef = useRef()
  const navigate = useNavigate()

  // Charger le profil existant au montage
  useEffect(() => {
    chargerProfil()
  }, [])

  const chargerProfil = async () => {
    try {
      const res = await getProfilParsed()
      if (res.existe && res.profil) {
        setProfil(res.profil)
        setProfilExiste(true)
        setMode('editor')
      } else if (res.existe && res.brut) {
        // YAML invalide → fallback texte
        setYamlBrut(res.brut)
        setProfilExiste(true)
        setMode('yaml')
      } else {
        setProfilExiste(false)
        setMode('onboarding')
      }
    } catch {
      // Fallback : essayer l'ancien endpoint
      try {
        const p = await getProfil()
        if (p.existe) {
          setYamlBrut(p.contenu)
          setProfilExiste(true)
          setMode('yaml')
        }
      } catch {
        setProfilExiste(false)
        setMode('onboarding')
      }
    }
  }

  // Upload du CV
  const handleUpload = async () => {
    if (!file) { showToast('Sélectionne un CV', 'error'); return }
    setLoading(true)
    try {
      await uploadCV(file, metier, ville)
      showToast('Profil généré avec succès !')
      await chargerProfil()
    } catch (e) {
      showToast(e.message, 'error')
    }
    setLoading(false)
  }

  // Sauvegarder le profil via l'éditeur visuel
  const handleSave = async () => {
    setSaving(true)
    try {
      await updateProfilStructured(profil)
      showToast('Profil sauvegardé')
    } catch (e) {
      showToast(e.message, 'error')
    }
    setSaving(false)
  }

  // Reset
  const handleReset = async () => {
    if (!confirm('Supprimer le profil actuel ? Tu pourras en générer un nouveau.')) return
    try {
      await deleteProfil()
      setProfil(null)
      setProfilExiste(false)
      setFile(null)
      setMode('onboarding')
      showToast('Profil supprimé')
    } catch (e) {
      showToast(e.message, 'error')
    }
  }

  // Drop handler
  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    const f = e.dataTransfer.files[0]
    if (f) setFile(f)
  }

  // ============================================================
  // MODE ÉDITEUR VISUEL
  // ============================================================
  if (mode === 'editor' && profil) {
    return (
      <div>
        <div className="page-head">
          <h1><span>👤</span> Mon profil</h1>
          <div className="btn-group">
            <button className="btn" onClick={() => navigate('/offres')}>
              📋 Voir les offres →
            </button>
            <button
              className="btn"
              onClick={() => {
                // Re-upload : basculer en mode onboarding
                setMode('onboarding')
              }}
            >
              📄 Nouveau CV
            </button>
            <button className="btn btn-danger" onClick={handleReset}>
              🗑️ Réinitialiser
            </button>
          </div>
        </div>

        <div style={{
          background: 'var(--green-dim)', border: '1px solid rgba(63,185,80,0.3)',
          borderRadius: 'var(--radius)', padding: '10px 16px', marginBottom: 16,
          fontSize: 13, color: 'var(--green)', display: 'flex', alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          <span>✅ Profil actif — modifie les champs ci-dessous si besoin</span>
        </div>

        <ProfileEditor
          profil={profil}
          onChange={setProfil}
          onSave={handleSave}
          saving={saving}
        />
      </div>
    )
  }

  // ============================================================
  // MODE YAML FALLBACK (si le parsing a échoué)
  // ============================================================
  if (mode === 'yaml') {
    return (
      <div>
        <div className="page-head">
          <h1><span>✏️</span> Profil (YAML)</h1>
          <div className="btn-group">
            <button className="btn" onClick={() => chargerProfil()}>
              🔄 Recharger en visuel
            </button>
            <button className="btn btn-danger" onClick={handleReset}>
              🗑️ Réinitialiser
            </button>
          </div>
        </div>

        <div style={{
          background: 'var(--yellow-dim)', border: '1px solid rgba(210,153,34,0.3)',
          borderRadius: 'var(--radius)', padding: '10px 16px', marginBottom: 16,
          fontSize: 13, color: 'var(--yellow)',
        }}>
          ⚠️ Le profil YAML n'a pas pu être parsé — édition en mode texte.
          Corrige la syntaxe puis clique "Recharger en visuel".
        </div>

        <textarea
          value={yamlBrut}
          onChange={e => setYamlBrut(e.target.value)}
          style={{
            width: '100%', minHeight: 500, background: 'var(--surface)',
            border: '1px solid var(--border)', borderRadius: 'var(--radius)',
            padding: 16, fontFamily: 'var(--mono)', fontSize: 12,
            color: 'var(--text)', resize: 'vertical', outline: 'none',
            lineHeight: 1.6,
          }}
        />
        <button
          className="btn btn-primary"
          style={{ marginTop: 12, width: '100%', padding: '12px', fontSize: 14 }}
          onClick={async () => {
            try {
              const { updateProfil } = await import('../api')
              await updateProfil(yamlBrut)
              showToast('Profil sauvegardé')
              await chargerProfil()
            } catch (e) {
              showToast(e.message, 'error')
            }
          }}
        >
          💾 Sauvegarder
        </button>
      </div>
    )
  }

  // ============================================================
  // MODE ONBOARDING (pas de profil)
  // ============================================================
  return (
    <div>
      <div className="page-head">
        <h1><span>🚀</span> Bienvenue</h1>
        {profilExiste && (
          <button className="btn" onClick={() => setMode('editor')}>
            ← Retour au profil
          </button>
        )}
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
