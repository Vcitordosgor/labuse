// RETOURS-14 P1-P2 — LA CARTE « ANALYSE LABUSE » extraite de Fiche.tsx (inline auparavant) pour
// être testable en isolation. Le contenu (bande, Signal de mutation, contributions FR, cause
// d'incomplétude) est INCHANGÉ. Deux ajouts vs l'inline :
//   · `version` (le run servi = SOURCE, injecté au build depuis config/served_run.txt) est AFFICHÉ
//     dans l'en-tête de la carte. Ce n'est JAMAIS une version codée en dur : la carte rend ce que
//     l'appelant lui passe, et l'appelant lui passe SOURCE (= la version de la page Données). La
//     bascule q_v11→q_v15 change SOURCE → la carte suit sans toucher au code.
//   · rien d'autre : mêmes styles, mêmes data-attrs (data-analyse-labuse-card, data-fiche-bande…).
import { useState } from 'react'
import { BANDE_META, SIGNAL_META } from '../../lib/status'
import { Chevron } from '../ui/Chevron'

export interface AnalyseLabuse {
  bande: string | null
  signal_niveau: string | null
  contributions: { sens: 'hausse' | 'baisse'; libelle: string }[] | null
  cause: string | null
  non_calculable?: boolean | null
  sdp_residuelle_m2?: number | null
}

export function AnalyseLabuseCard({ analyse, version }: { analyse: AnalyseLabuse; version: string }) {
  const bm = BANDE_META[analyse.bande as keyof typeof BANDE_META]
  const sm = analyse.signal_niveau ? SIGNAL_META[analyse.signal_niveau as keyof typeof SIGNAL_META] : null
  const nc = analyse.bande === 'NC'
  // RECETTE-2 (A12) — l'encart devient un accordéon Chevron qu'on peut replier.
  const [ouvert, setOuvert] = useState(true)
  if (!bm) return null
  return (
    <div data-analyse-labuse-card style={{ marginTop: 8, background: `${bm.color}12`, border: `1px solid ${bm.color}59`, borderRadius: 6, padding: '13px 16px' }}>
      <button type="button" data-analyse-toggle aria-expanded={ouvert} onClick={() => setOuvert((o) => !o)}
        style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, width: '100%', background: 'none', border: 0, padding: 0, cursor: 'pointer', textAlign: 'left' }}>
        <span style={{ display: 'inline-flex', alignItems: 'baseline', gap: 9, minWidth: 0, flexWrap: 'wrap' }}>
          <span style={{ fontSize: 10, letterSpacing: 1.4, color: 'var(--lab)', textTransform: 'uppercase' }}>
            Analyse LABUSE
            {/* RETOURS-14 P1 — la VERSION SERVIE (run) affichée, discrète. Jamais codée en dur : c'est SOURCE. */}
            {version && <span data-analyse-version style={{ marginLeft: 7, color: 'var(--txt-off)', letterSpacing: 0.6 }}>· {version}</span>}
          </span>
          {!ouvert && <span style={{ fontSize: 13, fontWeight: 600, color: bm.color }}>{bm.label}</span>}
        </span>
        <Chevron open={ouvert} />
      </button>
      {ouvert && (<>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, marginTop: 6, flexWrap: 'wrap' }}>
        <span data-fiche-bande={analyse.bande} style={{ fontSize: 22, fontWeight: 600, color: bm.color, lineHeight: 1 }}>{bm.label}</span>
        {sm && !nc && (
          <span data-fiche-signal={analyse.signal_niveau}
            style={{ fontSize: 11, fontWeight: 500, color: sm.color, border: `1px solid ${sm.color}66`, borderRadius: 9999, padding: '2px 8px' }}>{sm.label}</span>
        )}
      </div>
      {nc && analyse.cause && (
        <p data-fiche-cause style={{ margin: '9px 0 0', fontSize: 12, color: BANDE_META.NC.color }}>Analyse incomplète — {analyse.cause}.</p>
      )}
      {!nc && analyse.contributions && analyse.contributions.length > 0 && (
        <div data-fiche-contributions style={{ marginTop: 11, display: 'flex', flexDirection: 'column', gap: 4 }}>
          <p style={{ margin: 0, fontSize: 10, letterSpacing: 1, color: 'var(--txt-off)', textTransform: 'uppercase' }}>Ce qui compte</p>
          {analyse.contributions.map((c, i) => {
            const up = c.sens === 'hausse'
            return (
              <span key={i} style={{ display: 'inline-flex', alignItems: 'flex-start', gap: 6, fontSize: 12, color: up ? '#5CE6A1' : '#C08A6E' }}>
                <span aria-hidden style={{ fontSize: 9, fontWeight: 700, marginTop: 2 }}>{up ? '▲' : '▼'}</span>
                <span style={{ color: 'var(--txt-dim)' }}>{c.libelle}</span>
              </span>
            )
          })}
        </div>
      )}
      </>)}
    </div>
  )
}

export default AnalyseLabuseCard
