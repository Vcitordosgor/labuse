// CIRCUIT-1 lot 7.2 — LE MODE TRAÇAGE : chaque nombre étiqueté porte son chiffre_id.
//
// `<Trace id="prix_ancien_median_eur_m2">{fmtEur(x)}</Trace>` :
//   · traçage ÉTEINT (défaut, clients) → rend STRICTEMENT les enfants, rien d'autre — le
//     rendu est identique par construction (testé par snapshot) ;
//   · traçage ALLUMÉ (interrupteur admin, bandeau Circuit) → le nombre porte une étiquette
//     (id, couleur d'état) ; le clic ouvre le TIROIR : définition, moteur, portée, unité —
//     lus du registre servi (GET /admin/circuit → chiffres).
// Le mauve reste réservé aux agents (DA) : l'étiquette est jaune (« Fiche → » jaune).
import { useQuery } from '@tanstack/react-query'

import { getAdminCircuit } from './api'
import { useApp } from '../store/useApp'

export function Trace({ id, children }: { id: string; children: React.ReactNode }) {
  const tracage = useApp((s) => s.tracage)
  const setTraceOuvert = useApp((s) => s.setTraceOuvert)
  if (!tracage) return <>{children}</>
  return (
    <span
      data-chiffre={id}
      onClick={(e) => { e.preventDefault(); e.stopPropagation(); setTraceOuvert(id) }}
      style={{ outline: '1px dashed #facc15', outlineOffset: 1, cursor: 'help', borderRadius: 3 }}
      title={`chiffre : ${id} — cliquer pour la trace`}
    >
      {children}
    </span>
  )
}

/** Le TIROIR de trace (un seul, monté au niveau app) : définition/moteur/portée du chiffre,
 *  lus du registre servi. « La même valeur sur chaque surface » viendra de la sonde (lot 4)
 *  quand ses passages porteront les valeurs par robinet. */
export function TraceTiroir() {
  const id = useApp((s) => s.traceOuvert)
  const setTraceOuvert = useApp((s) => s.setTraceOuvert)
  const tracage = useApp((s) => s.tracage)
  const q = useQuery({ queryKey: ['admin-circuit'], queryFn: getAdminCircuit, enabled: tracage && !!id })
  if (!tracage || !id) return null
  const c = q.data?.chiffres?.[id]
  return (
    <div style={{
      position: 'fixed', right: 16, bottom: 16, zIndex: 60, maxWidth: 420,
      background: '#141b17', border: '1px solid #facc15', borderRadius: 8, padding: '12px 14px',
      color: '#e7ece8', fontSize: 12.5,
    }}>
      <button onClick={() => setTraceOuvert(null)}
        style={{ float: 'right', color: '#94a099', background: 'none', border: 0, cursor: 'pointer' }}>✕</button>
      <div style={{ fontFamily: 'ui-monospace,Menlo,monospace', fontSize: 11, color: '#facc15' }}>{id}</div>
      {c ? (
        <>
          <div style={{ fontWeight: 650, marginTop: 2 }}>{c.libelle} <span style={{ color: '#94a099' }}>({c.unite} · {c.niveau})</span></div>
          <div style={{ color: '#94a099', marginTop: 6 }}>{c.definition}</div>
          <div style={{ marginTop: 8, display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '2px 10px' }}>
            <span style={{ color: '#94a099' }}>moteur</span><span>{c.moteur || `(${c.calcul})`}</span>
            <span style={{ color: '#94a099' }}>portée</span>
            <span>{c.portee === 'run' ? `run — ne change qu'à la bascule (servi : ${q.data?.run_servi})` : "live — change à l'injection"}</span>
          </div>
        </>
      ) : (
        <div style={{ color: '#94a099', marginTop: 4 }}>
          {q.isLoading ? 'trace en chargement…' : 'chiffre absent du registre servi (labuse registre sync ?)'}
        </div>
      )}
    </div>
  )
}
