import { useState, useEffect } from 'react'

/**
 * StatsDetailed — Composant de stats enrichies
 * 
 * Affiche :
 * - Funnel de conversion (brouillon → envoyée → vue → entretien → acceptée)
 * - Taux de conversion entre étapes
 * - Activité par semaine (mini bar chart)
 * - Répartition par source et par lieu
 * - Top entreprises
 * 
 * Usage dans Dashboard.jsx :
 *   import StatsDetailed from '../components/StatsDetailed'
 *   <StatsDetailed stats={detailedStats} />
 */

const FUNNEL_STEPS = [
  { key: 'brouillon', label: 'Brouillon', icon: '📝', color: 'var(--text-muted)' },
  { key: 'envoyee', label: 'Envoyée', icon: '📤', color: 'var(--accent)' },
  { key: 'vue', label: 'Vue', icon: '👁️', color: 'var(--purple)' },
  { key: 'entretien', label: 'Entretien', icon: '🎤', color: 'var(--yellow)' },
  { key: 'acceptee', label: 'Acceptée', icon: '✅', color: 'var(--green)' },
]

export default function StatsDetailed({ stats }) {
  if (!stats || stats.total === 0) return null

  const maxFunnel = Math.max(...Object.values(stats.funnel || {}), 1)

  return (
    <div style={{ marginBottom: 24 }}>
      {/* Funnel de conversion */}
      <div style={{
        background: 'var(--surface)', border: '1px solid var(--border)',
        borderRadius: 'var(--radius)', padding: 16, marginBottom: 12,
      }}>
        <h3 style={{
          fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.4px',
          color: 'var(--text-muted)', marginBottom: 14,
        }}>Pipeline de conversion</h3>

        <div style={{ display: 'flex', alignItems: 'flex-end', gap: 4, height: 100 }}>
          {FUNNEL_STEPS.map((step, i) => {
            const count = stats.funnel?.[step.key] || 0
            const pct = maxFunnel > 0 ? (count / maxFunnel) * 100 : 0
            const nextStep = FUNNEL_STEPS[i + 1]
            const taux = nextStep
              ? stats.taux_conversion?.[`${step.key}_vers_${nextStep.key}`]
              : null

            return (
              <div key={step.key} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                {/* Barre */}
                <div style={{
                  width: '100%', maxWidth: 60,
                  height: `${Math.max(pct, 8)}%`,
                  background: `color-mix(in srgb, ${step.color} 25%, transparent)`,
                  border: `1px solid color-mix(in srgb, ${step.color} 40%, transparent)`,
                  borderRadius: '4px 4px 0 0',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  minHeight: 24, transition: 'height 0.3s',
                }}>
                  <span style={{ fontFamily: 'var(--mono)', fontSize: 13, fontWeight: 700, color: step.color }}>
                    {count}
                  </span>
                </div>
                {/* Label */}
                <span style={{ fontSize: 10, color: step.color, textAlign: 'center', lineHeight: 1.2 }}>
                  {step.icon}<br />{step.label}
                </span>
                {/* Taux vers l'étape suivante */}
                {taux != null && (
                  <span style={{
                    fontSize: 9, fontFamily: 'var(--mono)',
                    color: taux >= 50 ? 'var(--green)' : taux >= 20 ? 'var(--yellow)' : 'var(--red)',
                    position: 'absolute', marginTop: -14,
                  }}>
                  </span>
                )}
              </div>
            )
          })}
        </div>

        {/* Taux de conversion en ligne */}
        <div style={{ display: 'flex', justifyContent: 'space-around', marginTop: 10, flexWrap: 'wrap', gap: 8 }}>
          {stats.taux_conversion?.global_entretien != null && (
            <MiniStat label="→ Entretien" value={`${stats.taux_conversion.global_entretien}%`}
              color={stats.taux_conversion.global_entretien >= 20 ? 'var(--yellow)' : 'var(--text-muted)'} />
          )}
          {stats.taux_conversion?.global_acceptee != null && (
            <MiniStat label="→ Acceptée" value={`${stats.taux_conversion.global_acceptee}%`}
              color={stats.taux_conversion.global_acceptee > 0 ? 'var(--green)' : 'var(--text-muted)'} />
          )}
          {stats.duree_moyenne_jours != null && (
            <MiniStat label="Durée moy." value={`${stats.duree_moyenne_jours}j`} color="var(--accent)" />
          )}
          {stats.relances > 0 && (
            <MiniStat label="À relancer" value={stats.relances} color="var(--red)" />
          )}
        </div>
      </div>

      {/* Ligne 2 : Activité + Sources + Top entreprises */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>

        {/* Activité par semaine */}
        <div style={{
          background: 'var(--surface)', border: '1px solid var(--border)',
          borderRadius: 'var(--radius)', padding: 14,
        }}>
          <h3 style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.4px', color: 'var(--text-muted)', marginBottom: 10 }}>
            Activité récente
          </h3>
          {(stats.activite_semaine || []).map((s, i) => {
            const max = Math.max(...(stats.activite_semaine || []).map(x => x.candidatures), 1)
            const pct = (s.candidatures / max) * 100
            return (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                <span style={{ fontSize: 10, color: 'var(--text-muted)', width: 70, textAlign: 'right', fontFamily: 'var(--mono)' }}>
                  {s.semaine}
                </span>
                <div style={{ flex: 1, height: 14, background: 'var(--surface-3)', borderRadius: 3, overflow: 'hidden' }}>
                  <div style={{
                    width: `${Math.max(pct, 3)}%`, height: '100%',
                    background: 'var(--accent)', borderRadius: 3, transition: 'width 0.3s',
                  }} />
                </div>
                <span style={{ fontSize: 11, fontFamily: 'var(--mono)', color: 'var(--text-muted)', width: 20, textAlign: 'right' }}>
                  {s.candidatures}
                </span>
              </div>
            )
          })}
        </div>

        {/* Par source */}
        <div style={{
          background: 'var(--surface)', border: '1px solid var(--border)',
          borderRadius: 'var(--radius)', padding: 14,
        }}>
          <h3 style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.4px', color: 'var(--text-muted)', marginBottom: 10 }}>
            Par source
          </h3>
          {Object.entries(stats.par_source || {}).map(([source, count]) => {
            const pct = stats.total > 0 ? (count / stats.total * 100).toFixed(0) : 0
            const sourceLabels = { wttj: '🌴 WTTJ', lba: '🏛️ LBA', demo: '🎭 Demo' }
            return (
              <div key={source} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '3px 0' }}>
                <span style={{ fontSize: 12 }}>{sourceLabels[source] || source}</span>
                <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--text-muted)' }}>
                  {count} ({pct}%)
                </span>
              </div>
            )
          })}
          {Object.keys(stats.par_source || {}).length === 0 && (
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Aucune donnée</span>
          )}
        </div>

        {/* Top entreprises */}
        <div style={{
          background: 'var(--surface)', border: '1px solid var(--border)',
          borderRadius: 'var(--radius)', padding: 14,
        }}>
          <h3 style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.4px', color: 'var(--text-muted)', marginBottom: 10 }}>
            Top entreprises
          </h3>
          {(stats.top_entreprises || []).slice(0, 5).map((e, i) => (
            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '3px 0' }}>
              <span style={{ fontSize: 12, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 130 }}>
                {e.entreprise}
              </span>
              <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--accent)' }}>
                {e.count}
              </span>
            </div>
          ))}
          {(stats.top_entreprises || []).length === 0 && (
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Aucune donnée</span>
          )}
        </div>
      </div>
    </div>
  )
}

function MiniStat({ label, value, color }) {
  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{ fontFamily: 'var(--mono)', fontSize: 15, fontWeight: 700, color }}>{value}</div>
      <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.3px' }}>{label}</div>
    </div>
  )
}
