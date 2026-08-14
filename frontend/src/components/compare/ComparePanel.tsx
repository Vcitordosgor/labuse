// M54-EXPO-3 A8 / M82 (refonte) — comparateur : 2 à 3 parcelles côte à côte (GET /compare). DEUX modes :
//  · PICKING (barre compacte, carte cliquable) — le clic carte AJOUTE une parcelle (motif du clic-
//    sélection d'Assemblage) ; les sélectionnées sont surlignées (moduleMap).
//  · TABLEAU (surimpression) — le flux actuel (fiche → Outils → Comparer) inchangé ; « Ajouter sur la
//    carte » bascule en picking. Lignes : verdict, surface, zone, constructible, SDP, charge, prix
//    terrain nu/zone (M79), contrainte majeure.
import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getCompare, type CompareRow } from '../../lib/api'
import { fmtEurCompact, fmtInt } from '../../lib/format'
import { verdictMeta, type TierV2 } from '../../lib/status'
import { useApp } from '../../store/useApp'

function verdict(r: CompareRow) {
  return verdictMeta((r.status ?? null) as never, (r.tier_v2 ?? null) as TierV2 | null, !!r.etage0)
}

// lignes du tableau (libellé, valeur) — resserrées : les doublons fiche (Capacité, CA estimé) retirés ;
// ajoutés : prix terrain nu/zone (M79) + contrainte majeure explicite.
const ROWS: { label: string; val: (r: CompareRow) => string }[] = [
  { label: 'Surface', val: (r) => r.surface_m2 != null ? `${fmtInt(r.surface_m2)} m²` : '—' },
  { label: 'Zone PLU', val: (r) => r.zone || '—' },
  { label: 'Constructible', val: (r) => r.constructible == null ? '—' : r.constructible ? 'oui' : 'non' },
  { label: 'SDP max estimée', val: (r) => r.sdp_max_m2 != null ? `${fmtInt(r.sdp_max_m2)} m²` : '—' },
  { label: 'Charge foncière /m²', val: (r) => r.charge_fonciere_m2 != null ? `${fmtEurCompact(r.charge_fonciere_m2)}/m²` : '—' },
  { label: 'Prix terrain nu zone', val: (r) => r.terrain_zone_eur_m2 != null ? `${fmtInt(r.terrain_zone_eur_m2)} €/m²` : '—' },
  { label: 'Contrainte majeure', val: (r) => r.contrainte_majeure ?? (r.n_contraintes ? `${r.n_contraintes} signalée(s)` : 'aucune') },
]

export function ComparePanel() {
  const { compareIdus, clearCompare, removeFromCompare, select, setCompareOpen,
    comparePicking, setComparePicking, setModuleMap } = useApp()
  const q = useQuery({ queryKey: ['compare', compareIdus.join(',')], queryFn: () => getCompare(compareIdus), enabled: compareIdus.length > 0 })
  const parcels = q.data?.parcels ?? []

  // surligner les parcelles sélectionnées sur la carte pendant le picking ; nettoyer au démontage.
  useEffect(() => { setModuleMap({ idus: comparePicking ? compareIdus : [], extra: null }) }, [comparePicking, compareIdus, setModuleMap])
  useEffect(() => () => setModuleMap({ idus: [], extra: null }), [setModuleMap])

  // ── MODE PICKING : barre compacte, la carte DERRIÈRE reste cliquable (pointer-events sur la barre seule) ──
  if (comparePicking) return (
    <div className="pointer-events-none absolute inset-x-0 bottom-0 z-40 flex justify-center p-4">
      <div data-compare-picking className="floating pointer-events-auto flex w-full max-w-[560px] flex-col gap-2 p-3">
        <div className="flex items-center justify-between">
          <p className="label-caps">Cliquez des parcelles sur la carte ({compareIdus.length}/3)</p>
          <button onClick={() => { setComparePicking(false); setCompareOpen(false) }} className="text-[11px] text-txt-mut hover:text-txt" aria-label="Fermer">✕</button>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {compareIdus.map((i, n) => (
            <span key={i} className="flex items-center gap-1.5 rounded-lg border border-mint/50 bg-surface-2 px-2 py-1 font-mono text-[11px] text-txt">
              <b className="text-mint">{n + 1}</b>{i.slice(8)}
              <button onClick={() => removeFromCompare(i)} className="text-txt-dim hover:text-st-ecartee" aria-label="Retirer">✕</button>
            </span>
          ))}
          {compareIdus.length === 0 && <span className="text-[11px] text-txt-dim">cliquez une parcelle pour l’ajouter…</span>}
        </div>
        <div className="flex gap-2">
          <button onClick={() => setComparePicking(false)} disabled={compareIdus.length < 1}
            className="flex-1 rounded-lg bg-mint py-1.5 text-xs font-medium text-mint-on transition-[filter] duration-quick hover:brightness-110 disabled:opacity-40">
            Voir la comparaison ({compareIdus.length}) →
          </button>
          {compareIdus.length > 0 && <button onClick={clearCompare} className="rounded-lg border border-line-2 px-3 text-[11px] text-txt-mut hover:text-txt">vider</button>}
        </div>
      </div>
    </div>
  )

  // ── MODE TABLEAU (surimpression) — flux actuel inchangé + « Ajouter sur la carte » ──
  return (
    <div data-compare-panel className="absolute inset-0 z-40 flex items-center justify-center bg-black/50 p-6">
      <div className="floating flex max-h-full w-full max-w-[880px] flex-col overflow-hidden">
        <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
          <p className="label-caps">Comparer les parcelles ({compareIdus.length}/3)</p>
          <div className="flex items-center gap-3 text-[11px]">
            <button data-compare-carte onClick={() => setComparePicking(true)} className="text-mint hover:underline">◉ Ajouter sur la carte</button>
            <button onClick={clearCompare} className="text-txt-mut hover:text-txt">Tout vider</button>
            <button onClick={() => setCompareOpen(false)} className="text-txt-mut hover:text-txt" aria-label="Fermer">✕</button>
          </div>
        </div>
        <div className="min-h-0 flex-1 overflow-auto p-3">
          {compareIdus.length === 0 && (
            <div data-compare-vide className="p-4 text-center text-xs text-txt-dim">
              Aucune parcelle à comparer.
              <button onClick={() => setComparePicking(true)} className="ml-1 text-mint hover:underline">Cliquez-en sur la carte</button> ou ouvrez une fiche → Comparer.
            </div>
          )}
          {compareIdus.length > 0 && q.isPending && <p className="p-4 text-xs text-txt-dim">Chargement…</p>}
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
                  <td className="p-2 align-top text-[10.5px] uppercase tracking-wide text-txt-dim">Détail contraintes</td>
                  {parcels.map((r) => (
                    <td key={r.idu} className="border-l border-line p-2 align-top text-[10.5px] text-txt-mut">
                      {(r.contraintes ?? []).length ? <ul className="list-disc pl-4">{(r.contraintes ?? []).map((c, i) => <li key={i}>{c}</li>)}</ul> : '—'}
                    </td>
                  ))}
                </tr>
              </tbody>
            </table>
          )}
          <p className="mt-3 text-[10.5px] text-txt-dim">Chaque valeur vient du même point de calcul que la fiche (run servi). Ajoutez par la carte, ou depuis une fiche → « Comparer » — jusqu’à 3.</p>
        </div>
      </div>
    </div>
  )
}
