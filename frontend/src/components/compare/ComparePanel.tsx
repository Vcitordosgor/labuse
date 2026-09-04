// M54-EXPO-3 A8 / COMPARAISON (refonte 13 outils) — comparateur 2 à 3 parcelles côte à côte.
// L'outil est ANCRÉ dans Outils : `CompareModule` = le panneau gauche (stepper ① clic-carte ②
// tableau ③ retour, chips de sélection, note SOCLE) ; `ComparePanel` = le TABLEAU en surimpression
// (contenu/colonnes INCHANGÉS, mandat point 4). La carte reste active à droite pendant le picking.
import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getCompare, type CompareRow } from '../../lib/api'
import { fmtEurCompact, fmtInt, iduCourt } from '../../lib/format'
import { PERIM_POTENTIEL_COURT, PERIM_RESIDUEL_COURT } from '../../lib/perimetres'
import { verdictMeta, type TierV2 } from '../../lib/status'
import { useApp } from '../../store/useApp'

function verdict(r: CompareRow) {
  return verdictMeta((r.status ?? null) as never, (r.tier_v2 ?? null) as TierV2 | null, !!r.etage0)
}

// lignes du tableau (libellé, valeur) — resserrées : les doublons fiche (Capacité, CA estimé) retirés ;
// ajoutés : prix terrain nu/zone (M79) + contrainte majeure explicite.
// O9(d) — `num` + `best` permettent de surligner en vert la meilleure valeur de la ligne (front-side,
// comme la table Communes) : `best:'hi'` = la plus grande gagne (surface, capacité), `best:'lo'` = la
// plus basse gagne (charge foncière = moins cher). Les lignes booléennes/texte n'ont pas de gagnant.
// `title` (O9-c) = infobulle définissant la ligne au survol du libellé.
type Row = {
  label: string
  val: (r: CompareRow) => string
  num?: (r: CompareRow) => number | null
  best?: 'hi' | 'lo'
  title?: string
}
const ROWS: Row[] = [
  { label: 'Surface', val: (r) => r.surface_m2 != null ? `${fmtInt(r.surface_m2)} m²` : '—', num: (r) => r.surface_m2 ?? null, best: 'hi' },
  { label: 'Zone PLU', val: (r) => r.zone || '—' },
  { label: 'Constructible', val: (r) => r.constructible == null ? '—' : r.constructible ? 'oui' : 'non' },
  // O2-5 — chaque capacité porte son périmètre (source unique lib/perimetres) : la « max » suppose le
  // terrain libéré, la « résiduelle » suppose le bâti conservé — sinon les deux se contredisent à l'œil.
  { label: `SDP max estimée · ${PERIM_POTENTIEL_COURT}`, val: (r) => r.sdp_max_m2 != null ? `${fmtInt(r.sdp_max_m2)} m²` : '—', num: (r) => r.sdp_max_m2 ?? null, best: 'hi' },
  { label: `SDP résiduelle · ${PERIM_RESIDUEL_COURT}`, val: (r) => r.sdp_residuelle_m2 != null ? `${fmtInt(r.sdp_residuelle_m2)} m²` : '—', num: (r) => r.sdp_residuelle_m2 ?? null, best: 'hi' },
  { label: 'Emprise au sol max', val: (r) => r.taux_emprise_pct != null ? `${fmtInt(r.taux_emprise_pct)} %` : '—', num: (r) => r.taux_emprise_pct ?? null, best: 'hi', title: 'Part maximale du terrain que le PLU autorise à couvrir au sol.' },
  { label: 'Sous-densité', val: (r) => r.sous_densite == null ? '—' : r.sous_densite ? 'oui' : 'non', title: 'Le bâti existant est nettement en-dessous de ce que le PLU permet : il reste un potentiel à construire.' },
  { label: 'Charge foncière /m²', val: (r) => r.charge_fonciere_m2 != null ? `${fmtEurCompact(r.charge_fonciere_m2)}/m²` : '—', num: (r) => r.charge_fonciere_m2 ?? null, best: 'lo', title: 'Coût du foncier ramené au m² de surface de plancher constructible — plus bas = plus intéressant.' },
  { label: 'Prix terrain nu zone', val: (r) => r.terrain_zone_eur_m2 != null ? `${fmtInt(r.terrain_zone_eur_m2)} €/m²` : '—', num: (r) => r.terrain_zone_eur_m2 ?? null, best: 'lo', title: 'Prix moyen du terrain nu observé dans la zone — plus bas = plus intéressant.' },
  // RETOURS-11F M13 (O9) — lignes utiles ajoutées, toutes de la fiche servie (aucun second moteur).
  { label: 'Prix bâti secteur', val: (r) => r.prix_secteur_bati_m2 != null ? `${fmtInt(r.prix_secteur_bati_m2)} €/m²` : '—', num: (r) => r.prix_secteur_bati_m2 ?? null, title: 'Médiane DVF du bâti (maison/appartement) dans le secteur — même source que la fiche Marché.' },
  { label: 'Logements possibles', val: (r) => r.logements_possibles != null ? `${fmtInt(r.logements_possibles)}` : '—', num: (r) => r.logements_possibles ?? null, best: 'hi', title: 'Borne haute de la fourchette de logements estimée (au sol ou sous-sol).' },
  { label: 'Bâti existant', val: (r) => r.bati_existant_pct != null ? `${fmtInt(r.bati_existant_pct)} % du terrain` : '—', num: (r) => r.bati_existant_pct ?? null, best: 'lo', title: 'Part du terrain déjà couverte par le bâti (emprise au sol / surface) — plus bas = plus de place à bâtir.' },
  { label: 'Gabarit max', val: (r) => r.gabarit_niveaux_max != null ? `R+${Math.max(0, r.gabarit_niveaux_max - 1)}` : '—', num: (r) => r.gabarit_niveaux_max ?? null, best: 'hi', title: 'Nombre de niveaux maximum autorisé (gabarit PLU).' },
  { label: 'Accès & réseaux', val: (r) => r.acces_reseaux ?? '—', title: 'Un seul verdict de viabilisation (accès voirie + réseaux) — le même que la fiche Réseaux et accès.' },
  { label: 'Assainissement', val: (r) => r.assainissement ?? '—' },
  { label: 'Propriétaire', val: (r) => r.proprietaire === 'morale' ? 'personne morale' : r.proprietaire === 'particulier' ? 'particulier' : '—', title: 'Personne morale (société) ou particulier — issu du fichier DGFiP.' },
  { label: 'Contrainte majeure', val: (r) => r.contrainte_majeure ?? (r.n_contraintes ? `${r.n_contraintes} signalée(s)` : 'aucune') },
]

// O9(d) — indices des cellules gagnantes d'une ligne (peut être plusieurs en cas d'égalité).
// Ne renvoie rien si < 2 valeurs numériques (rien à comparer) : on ne surligne pas un « gagnant » seul.
function bestIdx(row: Row, parcels: CompareRow[]): Set<number> {
  const out = new Set<number>()
  if (!row.num || !row.best) return out
  const nums = parcels.map((p) => row.num!(p))
  const present = nums.filter((v): v is number => v != null)
  if (present.length < 2) return out
  const target = row.best === 'hi' ? Math.max(...present) : Math.min(...present)
  nums.forEach((v, i) => { if (v != null && v === target) out.add(i) })
  return out
}

// ── LE PANNEAU GAUCHE (outil « comparer », hôte ModulePanel) — ancré dans Outils, carte active à droite.
export function CompareModule() {
  const compareIdus = useApp((s) => s.compareIdus)
  const selectedIdu = useApp((s) => s.selectedIdu)   // O9(e) — parcelle courante (fiche ouverte)
  const addToCompare = useApp((s) => s.addToCompare)
  const removeFromCompare = useApp((s) => s.removeFromCompare)
  const clearCompare = useApp((s) => s.clearCompare)
  const setCompareOpen = useApp((s) => s.setCompareOpen)
  const setComparePicking = useApp((s) => s.setComparePicking)
  const setModuleMap = useApp((s) => s.setModuleMap)
  const n = compareIdus.length
  // panneau monté = picking ON (le clic-carte AJOUTE) + surlignage de la sélection ; nettoyage au démontage.
  useEffect(() => {
    setComparePicking(true)
    return () => { setComparePicking(false); setModuleMap({ idus: [], extra: null }) }
  }, [setComparePicking, setModuleMap])
  useEffect(() => { setModuleMap({ idus: compareIdus, extra: null }) }, [compareIdus, setModuleMap])

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
      <p className="text-[11px] text-txt-mut">Jusqu'à 3 parcelles, côte à côte, aux <b>mêmes points de calcul que la fiche</b>.</p>

      {/* ① cliquez les parcelles sur la carte + chips */}
      <div className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2">
        <div className="flex items-start gap-2">
          <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full border border-mint text-[9px] font-medium text-mint">1</span>
          <div className="min-w-0 flex-1">
            <p className="text-[11px] font-medium text-txt">Cliquez les parcelles sur la carte</p>
            <p className="text-[10px] text-txt-dim">la carte reste visible à droite — ou depuis une fiche → « Comparer »</p>
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              {compareIdus.map((i, k) => (
                <span key={i} data-compare-chip className="flex items-center gap-1.5 rounded-lg border border-mint/50 bg-surface-2 px-2 py-1 font-mono text-[11px] text-txt">
                  <b className="text-mint">{k + 1}</b>{iduCourt(i)}
                  <button onClick={() => removeFromCompare(i)} className="text-txt-dim hover:text-st-ecartee" aria-label="Retirer">✕</button>
                </span>
              ))}
              {Array.from({ length: Math.max(0, 3 - n) }).map((_, k) => (
                <span key={`libre-${k}`} className="rounded-lg border border-dashed border-line-2 px-2 py-1 text-[11px] text-txt-dim">+ 1 libre</span>
              ))}
            </div>
            {/* O9(e) — ajouter la parcelle courante (fiche ouverte) sans avoir à la re-cliquer sur la carte.
                Visible seulement s'il y a une parcelle courante, qu'elle n'est pas déjà dans la liste, et qu'il reste une place. */}
            {selectedIdu && !compareIdus.includes(selectedIdu) && n < 3 && (
              <button data-compare-ajouter-courante onClick={() => addToCompare(selectedIdu)}
                className="hover-fill mt-1.5 block rounded-lg border border-mint/50 px-2 py-1 text-[10.5px] text-mint transition-colors duration-quick">
                + Ajouter la parcelle courante ({iduCourt(selectedIdu)})
              </button>
            )}
            {n > 0 && <button data-compare-vider onClick={clearCompare} className="mt-1.5 text-[10px] text-txt-dim hover:text-txt">tout vider</button>}
          </div>
        </div>
      </div>

      {/* ② ouvrez le tableau */}
      <div className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2">
        <div className="flex items-center gap-2">
          <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full border border-mint text-[9px] font-medium text-mint">2</span>
          <p className="text-[11px] font-medium text-txt">Ouvrez le tableau</p>
        </div>
        <button data-compare-ouvrir onClick={() => setCompareOpen(true)} disabled={n < 1}
          className="mt-1.5 w-full rounded-lg bg-mint py-1.5 text-xs font-medium text-mint-on transition-[filter] duration-quick hover:brightness-110 disabled:opacity-40">
          Comparer ({n}/3)
        </button>
      </div>

      {/* ③ revenez à la carte */}
      <div className="flex items-start gap-2 px-1 text-txt-dim">
        <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full border border-line-2 text-[9px]">3</span>
        <p className="text-[10.5px] leading-snug">Revenez à la carte — <b>✕ ou Échap</b> — votre sélection reste dans ce panneau.</p>
      </div>

      <div className="mt-auto rounded-lg bg-surface-2 px-3 py-2 text-[9.5px] leading-snug text-txt-dim">
        En quittant l'outil, le tableau se ferme ; votre sélection est <b>gardée 15 min</b> si vous revenez.
      </div>
    </div>
  )
}

// ── LE TABLEAU (surimpression plein écran) — contenu/colonnes INCHANGÉS (mandat point 4).
export function ComparePanel() {
  const { compareIdus, clearCompare, removeFromCompare, select, setCompareOpen } = useApp()
  const q = useQuery({ queryKey: ['compare', compareIdus.join(',')], queryFn: () => getCompare(compareIdus), enabled: compareIdus.length > 0 })
  const parcels = q.data?.parcels ?? []

  // Échap ferme LE TABLEAU (retour carte + panneau) — capture, pour passer AVANT le handler « Échap =
  // fermer le module » de ModulePanel (qui, lui, ignore Échap tant que le tableau est ouvert).
  useEffect(() => {
    const h = (e: KeyboardEvent) => { if (e.key === 'Escape') { e.stopImmediatePropagation(); setCompareOpen(false) } }
    window.addEventListener('keydown', h, true)
    return () => window.removeEventListener('keydown', h, true)
  }, [setCompareOpen])

  return (
    <div data-compare-panel className="absolute inset-0 z-40 flex items-center justify-center bg-black/50 p-6">
      <div className="floating flex max-h-full w-full max-w-[880px] flex-col overflow-hidden">
        <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
          <p className="label-caps">Comparer les parcelles ({compareIdus.length}/3)</p>
          <div className="flex items-center gap-3 text-[11px]">
            {/* retour à la carte pour continuer le picking (le panneau + la sélection restent) */}
            <button data-compare-carte onClick={() => setCompareOpen(false)} className="text-mint hover:underline">◉ Retour à la carte</button>
            <button onClick={clearCompare} className="text-txt-mut hover:text-txt">Tout vider</button>
            <button onClick={() => setCompareOpen(false)} className="text-txt-mut hover:text-txt" aria-label="Fermer">✕</button>
          </div>
        </div>
        <div className="min-h-0 flex-1 overflow-auto p-3">
          {compareIdus.length === 0 && (
            <div data-compare-vide className="p-4 text-center text-xs text-txt-dim">
              Aucune parcelle à comparer.
              <button onClick={() => setCompareOpen(false)} className="ml-1 text-mint hover:underline">Cliquez-en sur la carte</button> ou ouvrez une fiche → Comparer.
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
                        <div className="mt-1 flex flex-wrap items-center gap-1">
                          {/* puce d'ACTION servie (M137) — dérivée de tier_v2 + étage 0, plus « Classement historique » */}
                          <span className="inline-block rounded-full px-2 py-0.5 text-[10px]" style={{ color: v.color, border: `1px solid ${v.color}55` }}>{v.label}</span>
                          {/* raison dominante M135 (chip court), comme sur la carte/la liste */}
                          {r.raison && <span data-compare-raison className="inline-block rounded-full border border-mint/40 bg-mint/10 px-1.5 py-0.5 text-[9px] font-medium text-mint">{r.raison}</span>}
                        </div>
                        {/* O9(a) — commune · fraction M135 (« 1/5 sous 1 an »). Le rang GLOBAL servi (ex.
                            « rang 271 141 » sur 431 663) ne veut rien dire pour l'utilisateur ; l'action
                            utile (le tier) est déjà portée par la puce ci-dessus. Un rang DANS LA COMMUNE
                            serait parlant mais n'existe pas dans le payload → non affiché (voir rapport). */}
                        <p className="mt-0.5 text-[10px] font-normal text-txt-dim">{r.commune}{r.fraction ? ` · ${r.fraction} sous 1 an` : ''}</p>
                      </th>
                    )
                  })}
                </tr>
              </thead>
              <tbody>
                {ROWS.map((row) => {
                  const winners = bestIdx(row, parcels)   // O9(d) — cellules gagnantes de la ligne
                  return (
                    <tr key={row.label} className="border-t border-line">
                      <td className="p-2 text-[10.5px] uppercase tracking-wide text-txt-dim">
                        {row.title
                          ? <span title={row.title} className="cursor-help border-b border-dotted border-line-2">{row.label}</span>
                          : row.label}
                      </td>
                      {parcels.map((r, i) => {
                        const win = winners.has(i)   // vert = meilleure valeur (comme la table Communes)
                        return (
                          <td key={r.idu} className={`border-l border-line p-2 ${win ? 'font-semibold text-mint' : 'text-txt'}`}>
                            {row.val(r)}
                          </td>
                        )
                      })}
                    </tr>
                  )
                })}
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
