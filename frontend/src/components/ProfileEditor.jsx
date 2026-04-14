import { useState } from 'react'

// ============================================================
// Section dépliable
// ============================================================
function Section({ title, icon, children, defaultOpen = true, count }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div style={{
      background: 'var(--surface)', border: '1px solid var(--border)',
      borderRadius: 'var(--radius)', marginBottom: 12, overflow: 'hidden',
    }}>
      <div
        onClick={() => setOpen(!open)}
        style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '12px 16px', cursor: 'pointer', userSelect: 'none',
          background: open ? 'var(--surface-2)' : 'transparent',
          transition: 'background 0.15s',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 16 }}>{icon}</span>
          <span style={{ fontWeight: 600, fontSize: 13.5 }}>{title}</span>
          {count !== undefined && (
            <span style={{
              fontSize: 11, fontFamily: 'var(--mono)', color: 'var(--text-muted)',
              background: 'var(--surface-3)', padding: '1px 7px', borderRadius: 4,
            }}>{count}</span>
          )}
        </div>
        <span style={{
          color: 'var(--text-muted)', fontSize: 12, transition: 'transform 0.2s',
          transform: open ? 'rotate(180deg)' : 'rotate(0deg)',
        }}>▼</span>
      </div>
      {open && <div style={{ padding: 16 }}>{children}</div>}
    </div>
  )
}

// ============================================================
// Champ texte simple
// ============================================================
function Field({ label, value, onChange, placeholder, mono, wide }) {
  return (
    <div style={{ marginBottom: 10 }}>
      {label && (
        <label style={{
          display: 'block', fontSize: 11, color: 'var(--text-muted)',
          marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.4px',
        }}>{label}</label>
      )}
      <input
        type="text"
        value={value || ''}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder || ''}
        style={{
          width: wide ? '100%' : '100%',
          background: 'var(--bg)', border: '1px solid var(--border)',
          borderRadius: 6, padding: '8px 12px', color: 'var(--text)',
          fontFamily: mono ? 'var(--mono)' : 'var(--font)', fontSize: 13,
          outline: 'none', transition: 'border-color 0.15s',
        }}
        onFocus={e => e.target.style.borderColor = 'var(--accent)'}
        onBlur={e => e.target.style.borderColor = 'var(--border)'}
      />
    </div>
  )
}

// ============================================================
// Input de tags (compétences, intérêts, etc.)
// ============================================================
function TagInput({ label, tags = [], onChange, placeholder, color = 'var(--accent)' }) {
  const [input, setInput] = useState('')

  const addTag = () => {
    const val = input.trim()
    if (val && !tags.includes(val)) {
      onChange([...tags, val])
      setInput('')
    }
  }

  const removeTag = (index) => {
    onChange(tags.filter((_, i) => i !== index))
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') { e.preventDefault(); addTag() }
    if (e.key === 'Backspace' && !input && tags.length > 0) {
      removeTag(tags.length - 1)
    }
  }

  const dimColor = color.replace(')', ', 0.12)').replace('var(', '').replace('rgb', 'rgba')

  return (
    <div style={{ marginBottom: 12 }}>
      {label && (
        <label style={{
          display: 'block', fontSize: 11, color: 'var(--text-muted)',
          marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.4px',
        }}>{label}</label>
      )}
      <div style={{
        display: 'flex', flexWrap: 'wrap', gap: 6,
        background: 'var(--bg)', border: '1px solid var(--border)',
        borderRadius: 6, padding: '6px 8px', minHeight: 38,
        alignItems: 'center',
      }}>
        {tags.map((tag, i) => (
          <span key={i} style={{
            display: 'inline-flex', alignItems: 'center', gap: 4,
            padding: '3px 10px', borderRadius: 4, fontSize: 12, fontWeight: 500,
            background: `color-mix(in srgb, ${color} 15%, transparent)`,
            color: color, border: `1px solid color-mix(in srgb, ${color} 25%, transparent)`,
          }}>
            {tag}
            <span
              onClick={() => removeTag(i)}
              style={{ cursor: 'pointer', opacity: 0.6, fontSize: 14, marginLeft: 2 }}
              title="Supprimer"
            >×</span>
          </span>
        ))}
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          onBlur={addTag}
          placeholder={tags.length === 0 ? (placeholder || 'Ajouter...') : ''}
          style={{
            flex: 1, minWidth: 100, background: 'transparent', border: 'none',
            color: 'var(--text)', fontSize: 12.5, outline: 'none',
            fontFamily: 'var(--font)', padding: '2px 4px',
          }}
        />
      </div>
    </div>
  )
}

// ============================================================
// Carte d'item de liste (formation, expérience, projet, langue)
// ============================================================
function ListItemCard({ children, onRemove, index }) {
  return (
    <div style={{
      background: 'var(--bg)', border: '1px solid var(--border)',
      borderRadius: 8, padding: 14, marginBottom: 8, position: 'relative',
    }}>
      <button
        onClick={onRemove}
        title="Supprimer"
        style={{
          position: 'absolute', top: 8, right: 8,
          background: 'none', border: 'none', color: 'var(--text-muted)',
          cursor: 'pointer', fontSize: 16, padding: '2px 6px',
          borderRadius: 4, transition: 'all 0.15s',
        }}
        onMouseOver={e => { e.target.style.color = 'var(--red)'; e.target.style.background = 'var(--red-dim)' }}
        onMouseOut={e => { e.target.style.color = 'var(--text-muted)'; e.target.style.background = 'none' }}
      >×</button>
      {children}
    </div>
  )
}

// ============================================================
// Bouton "Ajouter"
// ============================================================
function AddButton({ onClick, label }) {
  return (
    <button
      onClick={onClick}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 6,
        padding: '7px 14px', borderRadius: 6, fontSize: 12, fontWeight: 500,
        background: 'transparent', border: '1px dashed var(--border)',
        color: 'var(--text-muted)', cursor: 'pointer', transition: 'all 0.15s',
      }}
      onMouseOver={e => { e.target.style.borderColor = 'var(--accent)'; e.target.style.color = 'var(--accent)' }}
      onMouseOut={e => { e.target.style.borderColor = 'var(--border)'; e.target.style.color = 'var(--text-muted)' }}
    >
      + {label}
    </button>
  )
}


// ============================================================
// COMPOSANT PRINCIPAL : ProfileEditor
// ============================================================

export default function ProfileEditor({ profil, onChange, onSave, saving }) {
  if (!profil) return null

  // Helper pour mettre à jour un champ du profil
  const set = (key, value) => {
    onChange({ ...profil, [key]: value })
  }

  // Helper pour mettre à jour un item dans une liste
  const setListItem = (listKey, index, field, value) => {
    const list = [...(profil[listKey] || [])]
    list[index] = { ...list[index], [field]: value }
    set(listKey, list)
  }

  // Helper pour supprimer un item d'une liste
  const removeListItem = (listKey, index) => {
    const list = [...(profil[listKey] || [])]
    list.splice(index, 1)
    set(listKey, list)
  }

  // Helper pour ajouter un item à une liste
  const addListItem = (listKey, template) => {
    const list = [...(profil[listKey] || []), template]
    set(listKey, list)
  }

  // Compétences helpers
  const setComp = (category, value) => {
    set('competences', { ...(profil.competences || {}), [category]: value })
  }

  // Recherche helpers
  const setRecherche = (key, value) => {
    set('recherche', { ...(profil.recherche || {}), [key]: value })
  }

  return (
    <div>
      {/* ---- IDENTITÉ ---- */}
      <Section title="Identité" icon="👤" defaultOpen={true}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 16px' }}>
          <Field label="Nom complet" value={profil.nom} onChange={v => set('nom', v)} placeholder="Jean Dupont" />
          <Field label="Email" value={profil.email} onChange={v => set('email', v)} placeholder="jean@email.com" mono />
          <Field label="Téléphone" value={profil.telephone} onChange={v => set('telephone', v)} placeholder="+33 6 12 34 56 78" mono />
          <Field label="Localisation" value={profil.localisation} onChange={v => set('localisation', v)} placeholder="Paris, Île-de-France" />
          <Field label="LinkedIn" value={profil.linkedin} onChange={v => set('linkedin', v)} placeholder="linkedin.com/in/..." mono />
          <Field label="GitHub" value={profil.github} onChange={v => set('github', v)} placeholder="github.com/..." mono />
        </div>
        <Field label="Titre professionnel" value={profil.titre} onChange={v => set('titre', v)} placeholder="Développeur Full-Stack Python / React" wide />
      </Section>

      {/* ---- FORMATION ---- */}
      <Section title="Formation" icon="🎓" count={profil.formation?.length || 0}>
        {(profil.formation || []).map((f, i) => (
          <ListItemCard key={i} index={i} onRemove={() => removeListItem('formation', i)}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 16px' }}>
              <Field label="Diplôme" value={f.diplome} onChange={v => setListItem('formation', i, 'diplome', v)} />
              <Field label="Établissement" value={f.etablissement} onChange={v => setListItem('formation', i, 'etablissement', v)} />
              <Field label="Période" value={f.periode} onChange={v => setListItem('formation', i, 'periode', v)} placeholder="2020 — 2024" />
              <Field label="Détails" value={f.details} onChange={v => setListItem('formation', i, 'details', v)} placeholder="Spécialité, mentions..." />
            </div>
          </ListItemCard>
        ))}
        <AddButton label="Ajouter une formation" onClick={() => addListItem('formation', { diplome: '', etablissement: '', periode: '', details: '' })} />
      </Section>

      {/* ---- EXPÉRIENCE ---- */}
      <Section title="Expérience" icon="💼" count={profil.experience?.length || 0}>
        {(profil.experience || []).map((e, i) => (
          <ListItemCard key={i} index={i} onRemove={() => removeListItem('experience', i)}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 16px' }}>
              <Field label="Poste" value={e.poste} onChange={v => setListItem('experience', i, 'poste', v)} />
              <Field label="Entreprise" value={e.entreprise} onChange={v => setListItem('experience', i, 'entreprise', v)} />
              <Field label="Période" value={e.periode} onChange={v => setListItem('experience', i, 'periode', v)} placeholder="Jan 2023 — Juin 2023" />
            </div>
            <div style={{ marginTop: 4 }}>
              <TagInput
                label="Missions"
                tags={e.missions || []}
                onChange={v => setListItem('experience', i, 'missions', v)}
                placeholder="Décrire une mission puis Entrée..."
                color="var(--purple)"
              />
            </div>
          </ListItemCard>
        ))}
        <AddButton label="Ajouter une expérience" onClick={() => addListItem('experience', { poste: '', entreprise: '', periode: '', missions: [] })} />
      </Section>

      {/* ---- COMPÉTENCES ---- */}
      <Section title="Compétences" icon="⚡" defaultOpen={true}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 16px' }}>
          <TagInput
            label="Langages"
            tags={profil.competences?.langages || []}
            onChange={v => setComp('langages', v)}
            placeholder="Python, JavaScript..."
            color="var(--accent)"
          />
          <TagInput
            label="Frameworks"
            tags={profil.competences?.frameworks || []}
            onChange={v => setComp('frameworks', v)}
            placeholder="React, FastAPI..."
            color="var(--green)"
          />
          <TagInput
            label="Bases de données"
            tags={profil.competences?.bases_de_donnees || []}
            onChange={v => setComp('bases_de_donnees', v)}
            placeholder="PostgreSQL, MongoDB..."
            color="var(--yellow)"
          />
          <TagInput
            label="Outils"
            tags={profil.competences?.outils || []}
            onChange={v => setComp('outils', v)}
            placeholder="Git, Docker, VS Code..."
            color="var(--purple)"
          />
        </div>
        <TagInput
          label="Méthodes"
          tags={profil.competences?.methodes || []}
          onChange={v => setComp('methodes', v)}
          placeholder="Agile, Scrum, CI/CD..."
          color="var(--text-muted)"
        />
      </Section>

      {/* ---- PROJETS ---- */}
      <Section title="Projets" icon="🚀" count={profil.projets?.length || 0} defaultOpen={false}>
        {(profil.projets || []).map((p, i) => (
          <ListItemCard key={i} index={i} onRemove={() => removeListItem('projets', i)}>
            <Field label="Titre" value={p.titre} onChange={v => setListItem('projets', i, 'titre', v)} />
            <Field label="Technologies" value={p.technologies} onChange={v => setListItem('projets', i, 'technologies', v)} placeholder="Python, React, API REST..." />
            <Field label="Description" value={p.description} onChange={v => setListItem('projets', i, 'description', v)} placeholder="Ce que fait le projet..." />
          </ListItemCard>
        ))}
        <AddButton label="Ajouter un projet" onClick={() => addListItem('projets', { titre: '', technologies: '', description: '' })} />
      </Section>

      {/* ---- LANGUES ---- */}
      <Section title="Langues" icon="🌍" count={profil.langues?.length || 0} defaultOpen={false}>
        {(profil.langues || []).map((l, i) => (
          <ListItemCard key={i} index={i} onRemove={() => removeListItem('langues', i)}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 16px' }}>
              <Field label="Langue" value={l.langue} onChange={v => setListItem('langues', i, 'langue', v)} />
              <Field label="Niveau" value={l.niveau} onChange={v => setListItem('langues', i, 'niveau', v)} placeholder="natif, courant, intermédiaire..." />
            </div>
          </ListItemCard>
        ))}
        <AddButton label="Ajouter une langue" onClick={() => addListItem('langues', { langue: '', niveau: '' })} />
      </Section>

      {/* ---- CENTRES D'INTÉRÊT ---- */}
      <Section title="Centres d'intérêt" icon="🎯" defaultOpen={false}>
        <TagInput
          tags={profil.interets || []}
          onChange={v => set('interets', v)}
          placeholder="Sport, musique, voyages..."
          color="var(--accent)"
        />
      </Section>

      {/* ---- RECHERCHE ---- */}
      <Section title="Recherche" icon="🔎" defaultOpen={false}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 16px' }}>
          <Field label="Type de contrat" value={profil.recherche?.type} onChange={v => setRecherche('type', v)} placeholder="Alternance, stage..." />
          <Field label="Rythme" value={profil.recherche?.rythme} onChange={v => setRecherche('rythme', v)} placeholder="1 sem. école / 3 sem. entreprise" />
          <Field label="Durée" value={profil.recherche?.duree} onChange={v => setRecherche('duree', v)} placeholder="2 ans" />
          <Field label="Localisation" value={profil.recherche?.localisation} onChange={v => setRecherche('localisation', v)} placeholder="Île-de-France" />
        </div>
        <TagInput
          label="Domaines visés"
          tags={profil.recherche?.domaines || []}
          onChange={v => setRecherche('domaines', v)}
          placeholder="Développement, Data, Cybersécurité..."
          color="var(--green)"
        />
      </Section>

      {/* ---- POINTS FORTS ---- */}
      <Section title="Points forts" icon="💪" defaultOpen={false}>
        <TagInput
          tags={profil.points_forts || []}
          onChange={v => set('points_forts', v)}
          placeholder="Ajouter un point fort..."
          color="var(--green)"
        />
      </Section>

      {/* ---- BOUTON SAUVEGARDER (sticky) ---- */}
      <div style={{
        position: 'sticky', bottom: 0, padding: '12px 0',
        background: 'linear-gradient(transparent, var(--bg) 30%)',
      }}>
        <button
          className="btn btn-primary"
          onClick={onSave}
          disabled={saving}
          style={{ fontSize: 14, padding: '12px 32px', width: '100%' }}
        >
          {saving ? '⏳ Sauvegarde...' : '💾 Sauvegarder le profil'}
        </button>
      </div>
    </div>
  )
}
