// M54-EXPO-3 A8 — comparateur : 2 à 3 parcelles côte à côte (GET /compare). Réutilise les
// idiomes de la fiche (verdictMeta pour le verdict client, formats €/m²) — pas de nouveau DS.
import { useQuery } from '@tanstack/react-query'
import { getCompare, type CompareRow } from '../../lib/api'
import { fmtEurCompact, fmtInt } from '../../lib/format'
import { verdictMeta, type TierV2 } from '../../lib/status'
import { useApp } from '../../store/useApp'

function verdict(r: CompareRow) {
  return verdictMeta((r.status ?? null) as never, (r.tier_v2 ?? null) as TierV2 | null, !!r.etage0)
}
const ca = (r: CompareRow) => (r.ca_bas != null || r.ca_haut != null)
  ? `${fmtEurCompact(r.ca_bas)}–${fmtEurCompact(r.ca_haut)}` : '—'

// lignes du tableau comparatif : (libellé, valeur par parcelle)
const ROWS: { label: string; val: (r: CompareRow) => string }[] = [
  { label: 'Surface', val: (r) => r.surface_m2 != null ? `${fmtInt(r.surface_m2)} m²` : '—' },
  { label: 'Zone PLU', val: (r) => r.zone || '—' },
  { label: 'Constructible', val: (r) => r.constructible == null ? '—' : r.constructible ? 'oui' : 'non' },
  { label: 'Capacité', val: (r) => r.capacite || '—' },
  { label: 'SDP max', val: (r) => r.sdp_max_m2 != null ? `${fmtInt(r.sdp_max_m2)} m²` : '—' },
  { label: 'SDP résiduelle', val: (r) => r.sdp_residuelle_m2 != null ? `${fmtInt(r.sdp_residuelle_m2)} m²` : '—' },
  { label: 'Charge foncière /m²', val: (r) => r.charge_fonciere_m2 != null ? `${fmtEurCompact(r.charge_fonciere_m2)}/m²` : '—' },
  { label: 'Marché (CA estimé)', val: ca },
  { label: 'Contraintes', val: (r) => String(r.n_contraintes ?? 0) },
]

export function ComparePanel() {
  const { compareIdus, clearCompare, removeFromCompare, select, setCompareOpen } = useApp()
  const q = useQuery({ queryKey: ['compare', compareIdus.join(',')], queryFn: () => getCompare(compareIdus), enabled: compareIdus.length > 0 })
  const parcels = q.data?.parcels ?? []
  return (
    <div data-compare-panel className="absolute inset-0 z-40 flex items-center justify-center bg-black/50 p-6">
      <div className="floating flex max-h-full w-full max-w-[880px] flex-col overflow-hidden">
        <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
          <p className="label-caps">Comparer les parcelles ({compareIdus.length}/3)</p>
          <div className="flex items-center gap-3 text-[11px]">
            <button onClick={clearCompare} className="text-txt-mut hover:text-txt">Tout vider</button>
            <button onClick={() => setCompareOpen(false)} className="text-txt-mut hover:text-txt" aria-label="Fermer">✕</button>
          </div>
        </div>
        <div className="min-h-0 flex-1 overflow-auto p-3">
          {q.isPending && <p className="p-4 text-xs text-txt-dim">Chargement…</p>}
          {parcels.length > 0 && (
            <table className="w-full border-collapse text-[12px]">
              <thead>
                <tr>
                  <th className="w-[150px] p-2" />
                  {parcels.map((r) => {
                    const v = verdict(r)
                    return (
                      <th key={r.idu} data-compare-col className="border-l border-line p-2 align-top">
                        <div className="flex items-center justify-between gap-2">
                          <button onClick={() => select(r.idu)} className="font-mono text-[11px] tracking-tight text-txt-hi hover:underline">{r.idu}</button>
                          <button onClick={() => removeFromCompare(r.idu)} title="Retirer" className="text-[11px] text-txt-dim hover:text-st-ecartee">✕</button>
                        </div>
                        <span className="mt-1 inline-block rounded-full px-2 py-0.5 text-[10px]" style={{ color: v.color, border: `1px solid ${v.color}55` }}>{v.label}</span>
                        <p className="mt-0.5 text-[10px] font-normal text-txt-dim">{r.commune}{r.rang_v2 != null ? ` · rang ${fmtInt(r.rang_v2)}` : ''}</p>
                      </th>
                    )
                  })}
                </tr>
              </thead>
              <tbody>
                {ROWS.map((row) => (
                  <tr key={row.label} className="border-t border-line">
                    <td className="p-2 text-[10.5px] uppercase tracking-wide text-txt-dim">{row.label}</td>
                    {parcels.map((r) => <td key={r.idu} className="border-l border-line p-2 text-txt">{row.val(r)}</td>)}
                  </tr>
                ))}
                <tr className="border-t border-line">
                  <td className="p-2 text-[10.5px] uppercase tracking-wide text-txt-dim align-top">Détail contraintes</td>
                  {parcels.map((r) => (
                    <td key={r.idu} className="border-l border-line p-2 align-top text-[10.5px] text-txt-mut">
                      {(r.contraintes ?? []).length ? <ul className="list-disc pl-4">{(r.contraintes ?? []).map((c, i) => <li key={i}>{c}</li>)}</ul> : '—'}
                    </td>
                  ))}
                </tr>
              </tbody>
            </table>
          )}
          <p className="mt-3 text-[10.5px] text-txt-dim">Ajoutez des parcelles depuis une fiche (« Comparer ») ou la Shortlist — jusqu’à 3.</p>
        </div>
      </div>
    </div>
  )
}
