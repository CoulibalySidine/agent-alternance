/**
 * api.js — Client API centralisé
 * Toutes les requêtes passent par /api pour éviter
 * les conflits avec les routes React Router.
 */

async function request(path, options = {}) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `Erreur ${res.status}`)
  }
  return res.json()
}

// --- Profil ---
export const getProfil = () => request('/api/profil')
export const updateProfil = (contenu) =>
  request('/api/profil', { method: 'PUT', body: JSON.stringify({ contenu }) })
export const deleteProfil = () => request('/api/profil', { method: 'DELETE' })

export async function uploadCV(file, metier = '', ville = '') {
  const form = new FormData()
  form.append('cv', file)
  if (metier) form.append('metier', metier)
  if (ville) form.append('ville', ville)
  const res = await fetch('/api/profil/upload', { method: 'POST', body: form })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `Erreur ${res.status}`)
  }
  return res.json()
}

// --- Sourcing ---
export const getOffres = (params = {}) => {
  const qs = new URLSearchParams(
    Object.fromEntries(Object.entries(params).filter(([, v]) => v !== '' && v != null))
  ).toString()
  return request(`/api/offres${qs ? '?' + qs : ''}`)
}
export const deleteOffre = (id) => request(`/api/offres/${id}`, { method: 'DELETE' })
export const lancerScrape = (p = {}) =>
  request('/api/offres/scrape', { method: 'POST', body: JSON.stringify(p) })

// --- Qualification ---
export const scorerOffre = (id, forcer = false) =>
  request(`/api/score/${id}`, { method: 'POST', body: JSON.stringify({ forcer_rescore: forcer }) })
export const scorerBatch = (p = {}) =>
  request('/api/score/batch', { method: 'POST', body: JSON.stringify({ max_offres: 5, ...p }) })
export const getTask = (id) => request(`/api/tasks/${id}`)

// --- Candidature ---
export const genererDossier = (id, p = {}) =>
  request(`/api/candidatures/${id}/generer`, { method: 'POST', body: JSON.stringify(p) })
export const getFichiers = (id) => request(`/api/candidatures/${id}/fichiers`)

// --- Suivi ---
export const getSuivi = (params = {}) => {
  const qs = new URLSearchParams(
    Object.fromEntries(Object.entries(params).filter(([, v]) => v))
  ).toString()
  return request(`/api/suivi${qs ? '?' + qs : ''}`)
}
export const getSuiviStats = () => request('/api/suivi/stats')
export const ajouterSuivi = (offreId, notes = '') =>
  request('/api/suivi', { method: 'POST', body: JSON.stringify({ offre_id: offreId, notes }) })
export const changerEtat = (offreId, nouvelEtat, commentaire = '') =>
  request(`/api/suivi/${offreId}/etat`, { method: 'PATCH', body: JSON.stringify({ nouvel_etat: nouvelEtat, commentaire }) })
export const retirerSuivi = (id) => request(`/api/suivi/${id}`, { method: 'DELETE' })

// --- Système ---
export const getHealth = () => request('/api/health')

// --- Polling ---
export function pollTask(taskId, onUpdate, interval = 2000) {
  let stopped = false
  const poll = async () => {
    if (stopped) return
    try {
      const t = await getTask(taskId)
      onUpdate(t)
      if (t.status === 'done' || t.status === 'error') return
      setTimeout(poll, interval)
    } catch (e) {
      onUpdate({ status: 'error', error: e.message })
    }
  }
  poll()
  return () => { stopped = true }
}
