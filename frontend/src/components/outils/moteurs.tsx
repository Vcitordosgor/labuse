import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { ListPaginationFooter } from '../ListPagination'
import { RadarMarche } from './RadarMarche'   // RADAR-CATÉGORIE (T5) — le Marché des annonces déménage ici
import { addProfile, getProfiles, getResults, motAssemblage, motBarometre, motMarcheCommune, motSimulPlu, motSimulPluZones, motZan, promoteursActifs, zanParcelle } from '../../lib/api'
import { CLIENT } from '../../lib/strings'
import { fmtEurCompact, fmtInt } from '../../lib/format'
import { TOKENS } from '../../lib/tokens'
import { EMPTY_FILTERS, useApp } from '../../store/useApp'
import { Loading } from '../Loading'
import { Tip } from '../Tip'
import { TierBadge } from './TierBadge'
import { CP_COMMUNES } from '../panel/FiltreLabuse'   // RETOURS-11 T6 — source unique des 24 communes
import { trierCommunes } from '../../lib/communes'

const fmt = fmtInt

function Banner({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-mint/40 bg-mint/[0.07] px-3 py-2 text-[10.5px] leading-relaxed text-txt-mut">
      {children}
    </div>
  )
}

/* ───────────── M15 — SIMULATEUR PLU ───────────── */

// M137-Q — le périmètre est piloté par l'outil PLU unifié (choix EXPLICITE, `communeOverride`).
// Sans prop, repli sur le filtre global (compat) — mais l'outil unifié passe toujours le choix.
export function M15({ communeOverride }: { communeOverride?: string | null } = {}) {
  const globalCommune = useApp((s) => s.commune)
  const commune = communeOverride !== undefined ? communeOverride : globalCommune
  const qc = useQueryClient()
  const zones = useQuery({ queryKey: ['m15z', commune], queryFn: () => motSimulPluZones(commune) })
  const [zone, setZone] = useState<string | null>(null)
  // PLU Lot A — pagination SOCLE : le recalcul à blanc se pagine par `offset` (cap serveur par page)
  // jusqu'à épuisement ; les totaux (n_total, SDP estimée, bascules) sont servis STABLES par le back.
  const sim = useInfiniteQuery({
    queryKey: ['m15', zone, commune],
    queryFn: ({ pageParam, signal }) => motSimulPlu(zone!, commune, pageParam, signal),
    initialPageParam: 0,
    getNextPageParam: (last: any, pages) => { const n = pages.reduce((s, p: any) => s + (p.items?.length ?? 0), 0); return n < (last.n_total ?? 0) ? n : undefined },
    enabled: !!zone,
  })
  useEffect(() => { setZone(null) }, [commune])   // les zones AU diffèrent par commune → on repart à zéro
  const { setModuleMap, select } = useApp()   // fix : la liste était inerte (select non branché)
  const pages = (sim.data?.pages ?? []) as Record<string, any>[]
  const meta = pages[0]
  const items = pages.flatMap((p) => (p.items ?? []) as Record<string, any>[])
  const total = meta?.n_total ?? 0

  // RETOURS-10 (T3) — plus de « Tout charger » : on ne tire jamais tout d'un coup. « Voir 200 de plus ».

  useEffect(() => {
    setModuleMap({ idus: items.filter((i) => i.bascule_potentielle).map((i) => i.idu), extra: null })
    return () => setModuleMap({ idus: [], extra: null })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sim.dataUpdatedAt])

  // Annulation EFFECTIVE (Lot B, UI honnête) : abort la requête en vol + retour au choix de zone.
  const annuler = () => { qc.cancelQueries({ queryKey: ['m15', zone, commune] }); setZone(null) }

  return (
    // §1a — un seul conteneur de défilement (wrapper ModulePanel = overflow-hidden).
    <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto pr-0.5">
      <Banner>Recalcul <b>à blanc</b> — rien n'est persisté. SDP estimée par <b>analogie</b> aux
        parcelles U de la commune (méthode affichée). Le vrai recalcul règlementaire = prochain cycle.</Banner>
      <div className="flex flex-wrap gap-1.5">
        {(zones.data ?? []).map((z) => (
          <button key={z.zone} onClick={() => setZone(z.zone)}
            className={`rounded-full border px-2.5 py-1 text-[11px] ${zone === z.zone ? 'border-mint text-mint' : 'border-line-2 text-txt-mut'}`}>
            {z.zone} → U
          </button>
        ))}
      </div>

      {/* UI DE CHARGEMENT HONNÊTE (Lot B) — squelettes de lignes + Annuler pendant le recalcul (~2 s). */}
      {sim.isLoading && (
        <div data-m15-loading className="flex flex-col gap-1.5">
          <div className="flex items-center justify-between">
            <p className="text-[11px] text-txt-mut">Recalcul à blanc en cours…</p>
            <button data-m15-annuler onClick={annuler} className="text-[11px] text-txt-mut hover:text-st-ecartee">Annuler</button>
          </div>
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-8 animate-pulse rounded-lg bg-surface-3" style={{ opacity: 1 - i * 0.12 }} />
          ))}
        </div>
      )}
      {sim.isError && <p className="text-[11px] text-st-ecartee">Recalcul indisponible — réessayez.</p>}

      {meta && !sim.isLoading && (
        <>
          <div className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-[11px] text-txt-mut">
            <div><b className="text-txt">{fmt(total)}</b> parcelles en {meta.zone} · ratio analogie <b className="text-txt">{meta.ratio_analogie}</b></div>
            <div className="mt-1">SDP estimée totale <b className="tnum text-mint">{fmt(meta.sdp_totale_estimee_m2)} m²</b> ·{' '}
              <b className="tnum text-mint">{fmt(meta.bascules_potentielles)}</b> bascules potentielles (surlignées)</div>
          </div>
          <div className="flex flex-col gap-1">
            {items.map((i) => (
              <button key={i.idu} data-m15-item onClick={() => select(i.idu)}
                title="Ouvrir la parcelle"
                className="flex items-center gap-2 rounded-lg border border-line-2 bg-surface-3 px-3 py-1.5 text-left text-[11px] transition-colors duration-quick hover:border-mint/60">
                <span className="font-mono text-txt-hi">{i.idu.slice(8)}</span>
                <span className="text-txt-dim">{fmt(i.surface_m2)} m²</span>
                <span className={`ml-auto tnum ${i.bascule_potentielle ? 'text-mint' : 'text-txt-dim'}`}>
                  SDP est. {fmt(i.sdp_estimee_m2)} m²{i.bascule_potentielle ? ' ▲' : ''}
                </span>
              </button>
            ))}
          </div>
          {/* PAGINATION SOCLE (RETOURS-10 T3) — « Voir N de plus » seul, compteur toujours visible. */}
          <ListPaginationFooter
            className="flex flex-wrap items-center gap-3 border-t border-line pt-2 text-[11px] text-txt-mut"
            shown={items.length} total={total} step={meta.cap ?? 200}
            onMore={() => sim.fetchNextPage()}>
            {sim.isFetchingNextPage && <span className="text-txt-dim">chargement…</span>}
          </ListPaginationFooter>
        </>
      )}
    </div>
  )
}

/* ───────────── M16 — ASSEMBLAGE ───────────── */

export function M16() {
  const { msel, setMsel, setModuleMap, parcelPrefill, setParcelPrefill, setModule, setCourrierPrefillIdus } = useApp()
  const run = useMutation({ mutationFn: () => motAssemblage(msel) })
  // M-ENTREE — porte fiche → Assemblage : la parcelle devient la 1ʳᵉ du lot (motif parcelPrefill
  // partagé, consommation-puis-reset) ; l'utilisateur agrège les contiguës au clic-carte.
  useEffect(() => {
    if (parcelPrefill) { setMsel([parcelPrefill]); setParcelPrefill(null) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [parcelPrefill])
  useEffect(() => {
    setModuleMap({ idus: msel, extra: null })
    return () => setModuleMap({ idus: [], extra: null })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [msel])
  // GB-010 (patron LOT7 Courrier) : la sélection msel NE SURVIT PAS à l'outil — purgée au démontage de
  // l'Assemblage, pour qu'elle ne réapparaisse pas à la réouverture ni ne fuie vers un autre outil.
  useEffect(() => () => setMsel([]), [])  // eslint-disable-line react-hooks/exhaustive-deps
  // M15 A1 : la visibilité des parcelles (couche de picking violette `ile-pick`) est gérée par
  // MapView quand `module === 'assemblage'` — les contours de toutes les parcelles apparaissent,
  // bien lisibles, dès qu'on zoome (les tuiles se chargent). Voir MapView `ile-pick`.
  const d = run.data
  // CONNEXIONS-2 Lot 9.3 (KO-15) — le ratio (2 déc.) ET le pourcentage sont désormais SERVIS par le
  // backend (api/moteurs.py) : le front NE RE-DIVISE PLUS (fini les deux expressions du même ratio).
  const ratio = d?.gain_ratio ?? null
  const ratioStr = ratio != null ? ratio.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : null
  const pct = d?.gain_pct ?? null
  return (
    // §1a — UN SEUL conteneur de défilement (wrapper ModulePanel = overflow-hidden) : on accède à
    // la suite (analyse, propriétaires, courriers) au lieu d'un bas d'écran coupé.
    <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto pr-0.5">
      {/* M15 A1 : la cause du « ne fonctionne pas » = à l'échelle de l'île aucune parcelle n'est
          chargée ni cliquable. On guide explicitement : ZOOMER d'abord fait apparaître les contours. */}
      <Banner><b>Zoomez sur le secteur</b> pour faire apparaître les contours des parcelles, puis
        <b> cliquez-les</b> pour composer l'assiette (re-cliquer retire). Le <b>bilan réel</b> de
        l'assiette (capacité + charge foncière cumulées) — le <b>règlement d'ensemble reste à instruire</b>.</Banner>
      <div className="flex flex-wrap gap-1">
        {msel.map((i) => (
          <button key={i} onClick={() => setMsel(msel.filter((x) => x !== i))}
            className="min-h-7 rounded-full border border-mint/60 px-2 py-0.5 font-mono text-[11px] text-mint transition-colors duration-quick hover:bg-mint/10"
            title="Retirer de la sélection">
            {i.slice(8)} ×
          </button>
        ))}
        {msel.length === 0 && <span className="text-[11px] text-txt-dim">aucune parcelle sélectionnée</span>}
      </div>
      <div className="flex gap-2">
        <button onClick={() => msel.length >= 2 && run.mutate()} disabled={msel.length < 2 || run.isPending}
          className="flex-1 rounded-lg bg-mint py-1.5 text-xs font-medium text-bg transition-[filter] duration-quick hover:brightness-110 disabled:opacity-40">
          Analyser l'assiette ({msel.length})
        </button>
        {msel.length > 0 && (
          <button onClick={() => setMsel([])} className="rounded-lg border border-line-2 px-2 text-[11px] text-txt-dim hover:text-txt">vider</button>
        )}
      </div>
      {run.isError && <p className="text-[11px] text-st-ecartee">Erreur — au moins 2 parcelles valides ?</p>}
      {d && (
        <>
          {d.tronquee && <p className="text-[10.5px] text-st-creuser">Assiette limitée aux {fmt(d.cap)} premières parcelles.</p>}
          {/* #3 — le SCORE a disparu (doctrine M120 : pas de « qualité N/100 »). À la place, les FAITS
              qu'il agrégeait, dits séparément : d'un seul tenant · N interlocuteurs · ×gain. */}
          <div data-asm-faits className="flex flex-wrap items-center gap-1.5 text-[11px]">
            <span className={`rounded-full px-2 py-0.5 ${d.contigu ? 'bg-mint/10 text-mint' : 'bg-st-ecartee/10 text-st-ecartee'}`}>
              {d.contigu ? "d'un seul tenant" : 'NON contiguë'}</span>
            <span className="rounded-full bg-surface-3 px-2 py-0.5 text-txt-mut">{d.n_proprietaires} interlocuteur(s)</span>
            {(d.n_personnes_morales > 0 || d.n_particuliers > 0) && (
              <span className="rounded-full bg-surface-3 px-2 py-0.5 text-txt-mut">{d.n_personnes_morales} PM · {d.n_particuliers} particulier(s)</span>
            )}
          </div>

          <div className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-[11px]">
            {/* CAS I — assiette sans potentiel : on le DIT, pas de bloc gain trompeur. */}
            {d.sans_potentiel ? (
              <div data-asm-sans-potentiel className="rounded-md bg-st-ecartee/[0.08] px-2 py-1.5 text-[11px] leading-snug text-st-ecartee">
                Assiette sans capacité (ou parcelles écartées du run) — <b>aucun potentiel de projet en l'état</b>. La contiguïté seule ne fait pas une opération.
              </div>
            ) : (
              <>
                {/* point 1 — DEUX GRANDEURS DISTINCTES : surface d'assiette ≠ SDP cumulée (fini
                    « assiette 11 065 m² SDP » qui mélangeait tout). + logements + ×gain (point 2). */}
                <div className="grid grid-cols-2 gap-1.5">
                  <div data-asm-kpi="surface" className="rounded-md bg-surface-3 px-2 py-1.5">
                    <div className="text-[9px] text-txt-dim">Surface d'assiette</div>
                    <div className="tnum text-[14px] font-semibold text-txt">{fmt(d.surface_totale_m2)} m²</div>
                  </div>
                  {/* FIX-INTEGRATION I1 — « SDP estimée » (par analogie DVF, cf. ratio ci-dessus) cumulée
                      sur l'assiette. ≠ « SDP gabarit » de la Faisabilité (capacité PLU) ≠ « SHAB vendable »
                      (× rendement 0,8). Le titre le dit pour éviter toute comparaison entre outils. */}
                  <div data-asm-kpi="sdp" className="rounded-md bg-surface-3 px-2 py-1.5"
                    title="SDP ESTIMÉE par analogie (parcelles comparables), cumulée sur l'assiette — pas la SDP au gabarit PLU de la Faisabilité, ni la SHAB vendable">
                    <div className="text-[9px] text-txt-dim">SDP estimée cumulée</div>
                    <div className="tnum text-[14px] font-semibold text-mint">{fmt(d.sdp_combinee_m2)} m²</div>
                  </div>
                  <div className="rounded-md bg-surface-3 px-2 py-1.5">
                    <div className="text-[9px] text-txt-dim">Logements</div>
                    <div className="tnum text-[14px] font-semibold text-txt">{fmt(d.logements_combine?.[0])}–{fmt(d.logements_combine?.[1])}</div>
                  </div>
                  {ratio != null && (
                    <div data-asm-kpi="ratio" className="rounded-md bg-surface-3 px-2 py-1.5">
                      <div className="text-[9px] text-txt-dim">vs meilleure seule</div>
                      <div className="tnum text-[14px] font-semibold text-txt">×{ratioStr} <span className="text-[9px] font-normal text-mint">{pct != null && pct >= 0 ? '+' : ''}{pct} %</span></div>
                    </div>
                  )}
                </div>
                {/* point 3 — CHARGE CUMULÉE : négative = MÊME traitement que « Étudier un bien » (bloc
                    rouge + phrase), avec la référence marché à côté. */}
                {d.charge_fonciere && (() => {
                  const c = d.charge_fonciere.central as number
                  const neg = c < 0
                  return (
                    <div data-asm-charge data-neg={neg ? '1' : '0'} className={`rounded-lg border px-3 py-2 text-[11px] leading-snug ${neg ? 'border-st-ecartee/40 bg-st-ecartee/[0.07]' : 'border-mint/40 bg-mint/[0.06]'}`}>
                      <span className={neg ? 'text-st-ecartee' : 'text-mint'}>Charge foncière cumulée : <b>{fmtEurCompact(c)}</b> ({fmt(d.charge_fonciere.par_m2_terrain)} €/m² de terrain)</span>
                      {neg
                        ? <span className="text-txt-dim"> — négative : l'<b>ensemble ne finance pas ce foncier</b> à ces hypothèses.</span>
                        : <span className="text-txt-dim"> — CA cumulé ~{fmtEurCompact(d.ca?.central)}.</span>}
                      {d.terrain_zone_eur_m2 != null && <span className="text-txt-dim"> Marché zone : <b className="text-txt">{fmt(d.terrain_zone_eur_m2)} €/m²</b> (DVF · fiab. {String(d.terrain_zone_fiabilite ?? '—')}{d.zones_mixtes ? ' · zones mixtes' : ''}).</span>}
                      {d.n_chiffrables < d.n && <span className="text-st-creuser"> · {d.n_chiffrables}/{d.n} parcelles chiffrables</span>}
                    </div>
                  )
                })()}
                <div className="mt-1 text-[10.5px] leading-snug text-txt-dim">{d.note_sdp}</div>
              </>
            )}
          </div>

          {/* B — approche propriétaire (privacy : PM nommée / particulier masqué) */}
          <div data-asm-proprio className={`rounded-lg border px-3 py-1.5 text-[11px] ${d.tous_personnes_morales ? 'border-mint/40 bg-mint/[0.06]' : 'border-line-2 bg-surface-2'}`}>
            {d.tous_personnes_morales ? (
              <span className="text-mint">✓ Approche simplifiée — {d.n_personnes_morales} propriétaire(s) <b>personne(s) morale(s)</b>, aucun particulier</span>
            ) : (
              <span className="text-txt-mut">{d.n_personnes_morales} personne(s) morale(s) · <b className="text-st-creuser">{d.n_particuliers} particulier(s)</b> (approche plus lourde)</span>
            )}
            {(d.proprietaires_pm as string[]).length > 0 && (
              <div className="mt-0.5 truncate text-txt-dim" title={(d.proprietaires_pm as string[]).join(' · ')}>PM : {(d.proprietaires_pm as string[]).join(' · ')}</div>
            )}
          </div>

          <div className="flex flex-col gap-1">
            {(d.items as Record<string, any>[]).map((i) => {
              const pr = i.proprio as Record<string, any>
              return (
              <div key={i.idu} className="rounded-lg border border-line-2 bg-surface-3 px-3 py-1.5 text-[11px]">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-txt-hi">{i.idu.slice(8)}</span>
                  <span className="text-txt-dim">{fmt(i.surface_m2)} m² · SDP {fmt(i.sdp_m2)}</span>
                  <span className="ml-auto">
                    <TierBadge tier={i.tier_v2 as string | null} etage0={i.etage0 as boolean | null} statut={null} />
                  </span>
                </div>
                <div className="mt-0.5 flex items-center gap-2">
                  {/* PRIVACY : PM = dénomination + SIREN (public) ; particulier = jamais nommé */}
                  <div className="min-w-0 flex-1 truncate text-[11px] text-txt-dim" title={pr.type === 'personne_morale' ? `SIREN ${pr.siren ?? '—'}${pr.groupe ? ' · ' + pr.groupe : ''}` : 'personne physique — non communiqué'}>
                    {pr.type === 'personne_morale'
                      ? <><span className="text-txt">{pr.denomination}</span>{pr.siren ? <span> · SIREN {pr.siren}</span> : null}</>
                      : <span className="italic">propriétaire particulier — non communiqué</span>}
                  </div>
                  {/* point 4 : plus de bouton courrier PAR parcelle — un seul geste en pied (pont Courrier). */}
                </div>
              </div>
            )})}
          </div>
          {/* point 4 — PONT COURRIER : un seul geste ouvre l'outil Courrier prérempli avec TOUTES les
              parcelles de l'assemblage (patron courrierPrefillIdus, comme l'import Assemblage côté Courrier). */}
          {(d.items as Record<string, any>[]).length > 0 && (
            <button data-asm-courrier onClick={() => { setCourrierPrefillIdus((d.items as Record<string, any>[]).map((i) => i.idu as string)); setModule('courriers') }}
              className="rounded-lg border border-mint/50 bg-mint/10 py-1.5 text-[11px] font-medium text-mint transition-colors duration-quick hover:bg-mint/20">
              ✉ Préparer les courriers ({(d.items as Record<string, any>[]).length}) → Courrier propriétaire
            </button>
          )}
          {/* C — indivision non détectable en base (honnête, pas fabriqué) */}
          <p className="shrink-0 text-[10px] leading-snug text-txt-dim">Indivision : non détectable en open data (aucune structure de propriété physique publiée) — signal non affiché plutôt qu'inventé.</p>
        </>
      )}
    </div>
  )
}

/* ───────────── M17 — ZAN ───────────── */

// Étiquette Sourcé (observé, vert) / Estimé (dérivé, ambre) — la boussole d'honnêteté (comme DVF).
const SrcTag = ({ src }: { src: boolean }) => (
  <span className={`ml-1 rounded px-1 py-0.5 align-middle text-[8.5px] font-medium ${src ? 'bg-mint/10 text-mint' : 'bg-st-creuser/10 text-st-creuser'}`}>{src ? 'Sourcé' : 'Estimé'}</span>
)

/** Indicateur ZAN d'une commune : consommé (Sourcé) + budget/reste (Estimé) + caveat loi TRACE. */
function IndicateurCommune({ ind, caveat }: { ind: Record<string, any>; caveat: string }) {
  const dep = ind.depasse
  return (
    <div className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-[11px]">
      <div className="flex items-center justify-between">
        <span className="font-medium text-txt">{ind.commune} — enveloppe ZAN (estimée)</span>
      </div>
      {/* audit-zan — le budget en POURCENTAGE d'abord (c'est lui qui parle) ; le caveat ESTIMÉ juste à
          côté (un « % restant » se lit trop vite comme un droit ferme), pas seulement en bas de bloc. */}
      {ind.pct_consomme != null && (
        <div className="mt-1.5 rounded-md bg-surface-3 px-2.5 py-1.5">
          <div className="flex items-baseline gap-1.5">
            <b className={`tnum text-[16px] ${dep ? 'text-st-ecartee' : 'text-st-creuser'}`}>{ind.pct_consomme} %</b>
            <span className="text-[10.5px] text-txt-mut">du budget consommé</span>
            <span className={`ml-auto tnum text-[11.5px] ${dep ? 'text-st-ecartee' : 'text-txt'}`}>{ind.pct_restant} % restant</span>
          </div>
          <p className="mt-0.5 text-[9px] leading-snug text-st-creuser">
            <b>Estimé</b> (budget = conso 2011-21 × 0,5, SAR non territorialisé) — <b>pas un droit à construire</b>.</p>
        </div>
      )}
      {/* les hectares restent à côté — la donnée source */}
      <div className="mt-1.5 grid grid-cols-2 gap-x-3 gap-y-0.5 text-txt-mut">
        <span>Consommé 2011-21 : <b className="text-txt">{ind.conso_2011_2021_ha}</b> ha<SrcTag src /></span>
        <span>Consommé 2021-24 : <b className="text-txt">{ind.conso_2021_2024_ha}</b> ha<SrcTag src /></span>
        <span>Budget 2021-31 : <b className="tnum text-st-creuser">{ind.budget_2021_2031_ha}</b> ha<SrcTag src={false} /></span>
        <span>Reste (théorique) : <b className={`tnum ${dep ? 'text-st-ecartee' : 'text-st-creuser'}`}>{ind.reste_theorique_ha}</b> ha<SrcTag src={false} /></span>
      </div>
      {dep && <p className="mt-1 text-[10.5px] text-st-ecartee">▲ Rythme déjà « dépassé » sur la période estimée (reste négatif).</p>}
      <p className="mt-1 text-[10px] italic leading-snug text-st-creuser">{caveat}</p>
      <p className="mt-0.5 text-[9px] text-txt-dim">Observé : {ind.source} · {ind.millesime}</p>
    </div>
  )
}

// DORMANT — outil « Simulateur ZAN » retiré du produit le 21/08/2026 (plus câblé au menu : registry +
// ModulePanel COMPONENTS). Mesuré avant retrait : ses 3 briques étaient (1) une LISTE MORTE « parcelles
// alignées ZAN » (filtre ocs_ge weight>0, jamais >0 → 0 en permanence — un mensonge silencieux), (2) un
// SIGNAL PARCELLE déjà servi sur la fiche (doublon), (3) l'ENVELOPPE communale = même formule que la
// section « Rareté & ZAN » de l'outil Communes. L'enveloppe (dont le budget en %) vit désormais dans
// Communes. Composant conservé au dépôt (exporté, compilable) ; endpoints /moteurs/zan* vivants (lus par
// briques_pdf). Le retrait de l'outil suffit à ne plus AFFICHER ni la liste morte ni le doublon.
export function M17() {
  const q = useQuery({ queryKey: ['m17'], queryFn: motZan })
  const { setModuleMap, select, selectedIdu } = useApp()
  const d = q.data
  const [idu, setIdu] = useState(selectedIdu ?? '')
  useEffect(() => { if (selectedIdu) setIdu(selectedIdu) }, [selectedIdu])
  const sig = useQuery({ queryKey: ['zan-parc', idu], queryFn: () => zanParcelle(idu.trim()), enabled: idu.trim().length >= 10 })
  const s = sig.data
  useEffect(() => {
    const items = (d?.zan_compatibles ?? []) as Record<string, any>[]
    setModuleMap({ idus: items.map((i) => i.idu), extra: null })
    return () => setModuleMap({ idus: [], extra: null })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q.dataUpdatedAt])
  const sigColor = s?.signal === 'aligne' ? TOKENS.mint : s?.signal === 'contrainte' ? TOKENS.stEcartee : TOKENS.txtMut
  const sigLabel = s?.signal === 'aligne' ? 'Aligné ZAN' : s?.signal === 'contrainte' ? 'Sous contrainte ZAN' : 'À instruire'
  return (
    <>
      <Banner>{d?.bandeau ?? '…'}</Banner>
      {q.isLoading && <div className="flex flex-1 items-center justify-center py-8"><Loading accent="mint" label="Analyse en cours…" big /></div>}

      {/* SIGNAL PAR PARCELLE (mène — robuste, sourcé, indépendant des quotas) */}
      <p className="label-caps">Signal ZAN par parcelle</p>
      <input data-zan-idu value={idu} onChange={(e) => setIdu(e.target.value.trim())}
        placeholder="IDU (ou sélectionnez une parcelle sur la carte)"
        className="rounded-lg border border-line-2 bg-surface-3 px-2 py-1.5 font-mono text-[11px] text-txt focus:border-mint focus:outline-none" />
      {s && (
        <div data-zan-signal className="flex flex-col gap-1.5 rounded-lg border px-3 py-2" style={{ borderColor: `${sigColor}55` }}>
          <div className="flex items-center gap-2">
            <span className="rounded-full px-2 py-0.5 text-[11px] font-medium" style={{ background: `${sigColor}22`, color: sigColor }}>{sigLabel}</span>
            <span className="text-[10.5px] text-txt-dim">{s.commune}</span>
          </div>
          {(s.raisons as string[]).map((r, i) => (
            <div key={i} className="flex gap-1.5 text-[10.5px] text-txt-mut"><span style={{ color: sigColor }}>•</span><span>{r}<SrcTag src /></span></div>
          ))}
          {s.exemption_sru && (
            <div className="rounded border border-mint/40 bg-mint/[0.06] px-2 py-1 text-[10.5px] text-mint">★ {s.exemption_sru}<SrcTag src /></div>
          )}
        </div>
      )}
      {/* CONTEXTE COMMUNE : indicateur estimé + caveat */}
      {s?.indicateur && <IndicateurCommune ind={s.indicateur} caveat={s.caveat as string} />}

      {/* audit-zan #1 — les 24 communes (la donnée est complète : commune_conso_enaf = 24/24). Le
          « .slice(0, 8) » était un LIMIT d'affichage caché, comme celui du baromètre : retiré. Chaque
          ligne dit son % de budget CONSOMMÉ (Estimé), avec les ha (consommé / budget) à côté. */}
      <p className="label-caps mt-1">Budget ZAN par commune — les {((d?.indicateurs ?? []) as unknown[]).length}
        <span className="ml-1 normal-case text-txt-dim">(% consommé <span className="text-st-creuser">Estimé</span> · ha observés)</span></p>
      <div className="flex max-h-48 shrink-0 flex-col overflow-y-auto">
        {((d?.indicateurs ?? []) as Record<string, any>[]).map((c) => (
          <button key={c.commune} onClick={() => setIdu('')}
            className="flex items-center gap-2 border-b border-line py-1 text-left text-[11px]"
            title={`${c.commune} : ${c.pct_consomme} % du budget estimé consommé (${c.conso_2021_2024_ha} sur ${c.budget_2021_2031_ha} ha) — estimation, pas un droit`}>
            <span className="min-w-0 flex-1 truncate text-txt">{c.commune}</span>
            <span className={`w-12 text-right font-mono tnum ${c.depasse ? 'text-st-ecartee' : 'text-st-creuser'}`}>{c.pct_consomme != null ? `${c.pct_consomme} %` : '—'}</span>
            <span className="w-[86px] text-right font-mono text-[10px] text-txt-dim">{c.conso_2021_2024_ha}/{c.budget_2021_2031_ha} ha</span>
          </button>
        ))}
      </div>
      <p className="text-[11px] text-txt-dim">{fmt((d?.zan_compatibles ?? []).length)} parcelles déjà artificialisées promues (surlignées) — <b className="text-mint">alignées ZAN</b></p>
      <div className="flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto">
        {((d?.zan_compatibles ?? []) as Record<string, any>[]).slice(0, 60).map((i) => (
          <button key={i.idu} onClick={() => { setIdu(i.idu); select(i.idu) }}
            className="flex items-center gap-2 rounded-lg border border-line-2 bg-surface-3 px-3 py-1.5 text-left text-[11px] transition-colors duration-quick hover:border-mint/50">
            <span className="font-mono text-txt-hi">{i.idu.slice(8)}</span>
            <span className="text-txt-dim">{fmt(i.surface_m2)} m²</span>
            <span className="ml-auto">
              <TierBadge tier={i.tier_v2 as string | null} etage0={i.etage0 as boolean | null} statut={i.statut as string | null} />
            </span>
          </button>
        ))}
      </div>
    </>
  )
}

/* ───────────── M18 — BAROMÈTRE → onglet « Évolution » de Communes ─────────────
   L'outil autonome a disparu du menu ; ce composant est l'onglet « Évolution » du hub Communes.
   Trois séries (ancien bâti, terrain nu, permis) + tendance annuelle + neuf en référence + PDF. */

// une série trimestrielle : barres (volume) + médiane ; un trimestre PARTIEL est GRISÉ et dit
// « données partielles (délai DVF) » — jamais une barre courte muette (§1a véracité).
function SerieTrim({ titre, tip, rows, volKey, medKey, unite, pct }:
  { titre: string; tip: string; rows: Record<string, any>[]; volKey: string; medKey?: string; unite?: string; pct?: number | null }) {
  const max = Math.max(1, ...rows.map((r) => Number(r[volKey]) || 0))
  return (
    <div className="flex shrink-0 flex-col gap-1">
      <p className="label-caps flex items-center gap-1.5">
        {titre}
        <Tip tip={tip}><span className="cursor-help rounded-full border border-line-2 px-1 text-[8px] text-txt-dim">i</span></Tip>
        {pct != null && <span className={`ml-auto text-[10.5px] font-medium ${pct >= 0 ? 'text-mint' : 'text-st-ecartee'}`}>{pct >= 0 ? '+' : ''}{pct} % / an</span>}
      </p>
      {rows.map((r) => (
        <div key={r.trimestre} className={`flex items-center gap-2 text-[11px] ${r.partiel ? 'opacity-45' : ''}`}>
          <span className="w-24 font-mono text-txt-dim">{r.trimestre}{r.partiel && <span className="text-st-creuser"> ·partiel</span>}</span>
          <span className="relative h-2.5 min-w-0 flex-1 overflow-hidden rounded-full bg-line">
            <span className={`absolute left-0 top-0 h-full rounded-full ${r.partiel ? 'bg-txt-dim' : 'bg-mint'}`} style={{ width: `${(100 * (Number(r[volKey]) || 0)) / max}%` }} />
          </span>
          <span className="w-12 text-right font-mono text-txt-mut">{fmt(r[volKey])}</span>
          {medKey && <span className="w-20 text-right font-mono text-txt-dim">{fmt(r[medKey])} {unite}</span>}
        </div>
      ))}
      {rows.some((r) => r.partiel) && <p className="text-[9.5px] text-st-creuser">· dernier trimestre partiel (délai de publication DVF) — grisé, hors tendance.</p>}
    </div>
  )
}

export function M18() {
  const q = useQuery({ queryKey: ['m18'], queryFn: motBarometre })
  const d = q.data as Record<string, any> | undefined
  const nr = d?.neuf_reference as Record<string, any> | undefined
  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
      {/* M141 Partie 1 — bouton « Rapport PDF » RETIRÉ (le baromètre ne sort plus en PDF, décision Vic).
          L'onglet Évolution reste inchangé ; seul l'export disparaît. */}
      <div className="flex items-center gap-2">
        <span className="text-[10.5px] text-txt-mut">Île entière (DVF 24 communes, Sitadel régional) — 8 derniers trimestres.</span>
      </div>
      {nr && (
        <p className="text-[10.5px] text-txt-dim">Neuf : <b className="text-txt">~{fmt(nr.prix_m2_neuf)} €/m²</b> (référence actuelle, sur {fmt(nr.n)} ventes)
          <Tip tip="La VEFA (neuf) est trop rare dans DVF (0-4 ventes/trimestre) pour une série trimestrielle honnête : on sert le prix de sortie neuf ACTUEL (référence île), pas une fausse courbe."><span className="ml-1 cursor-help rounded-full border border-line-2 px-1 text-[8px] text-txt-dim">i</span></Tip>
        </p>
      )}
      {d && <SerieTrim titre="Ancien bâti · €/m²" pct={d.tendance_ancien_pct}
        tip="Médiane €/m² BÂTI, ventes strictes DVF (nature 'Vente', prix > 1 000 €, €/m² ∈ [100, 12 000] ; VEFA/neuf exclu). Volume = nombre de ventes retenues."
        rows={d.dvf_trimestres} volKey="mutations" medKey="median_eur_m2_bati" unite="€/m²" />}
      {d && <SerieTrim titre="Terrain nu · €/m²" pct={d.tendance_terrain_pct}
        tip="Médiane €/m² TERRAIN, ventes de terrain nu (bâti = 0), €/m² dédupliqué par mutation (valeur ÷ terrain total). Source dvf_mutations_parcelle."
        rows={d.terrain_trimestres ?? []} volKey="mutations" medKey="median_eur_m2_terrain" unite="€/m²" />}
      {d && <SerieTrim titre="Permis autorisés (Sitadel)" pct={d.tendance_permis_pct}
        tip="Nombre de permis autorisés par trimestre (Sitadel régional, toutes destinations)."
        rows={d.permis_trimestres ?? []} volKey="permis" />}

      {/* RADAR-CATÉGORIE (T5) — le « Marché des annonces (Radar) » a QUITTÉ le Radar : ses agrégats
          par commune (pige/marche.py, réutilisé — socle R9) vivent ICI, sous les stats de marché.
          Chaque mesure porte son n ; sous 5 = « échantillon insuffisant » ; état de démarrage digne. */}
      <div className="mt-3 border-t border-line-2 pt-3">
        <p className="label-caps text-[9.5px]">Marché des annonces (Radar)</p>
        <p className="mt-0.5 text-[10px] leading-snug text-txt-dim">
          Les biens en vente repérés par le Radar, agrégés par commune. Faits bruts (compteurs) exacts
          dès le premier ; une médiane ou un taux n’est servi qu’à partir de 5 biens — jamais de fausse précision.
        </p>
        <RadarMarche />
      </div>
    </div>
  )
}


/* ───────────── M-U — MARCHÉ PAR COMMUNE (Agent Prix) ───────────── */

// RETOURS-11 T6 — dérivé du référentiel unique CP_COMMUNES, trié sans tenir compte de l'article.
const MU_COMMUNES = trierCommunes(CP_COMMUNES.map(([, nom]) => nom), (n) => n)

const MU_FIAB: Record<string, string> = { bonne: TOKENS.mint, moyenne: TOKENS.stCreuser,
  faible: TOKENS.txtMut, insuffisant: TOKENS.txtDim }

function MuSignal({ sig }: { sig: Record<string, any> | undefined }) {
  if (!sig?.disponible) return <p className="text-[10.5px] text-txt-dim">{CLIENT.marche.signalIndispo}</p>
  const col = sig.label === 'favorable' ? TOKENS.mint : sig.label === 'prudence' ? TOKENS.stEcartee : TOKENS.stCreuser
  return (
    <div data-marche-signal className="rounded-lg border px-3 py-2" style={{ borderColor: `${col}55` }}>
      <span className="rounded-full px-2 py-0.5 text-[11px] font-medium" style={{ background: `${col}22`, color: col }}>
        {CLIENT.marche.signal} : {sig.label}</span>
      {/* jamais un mot nu : les 2 composantes DVF/Sitadel sont toujours affichées */}
      {(sig.composantes as Record<string, any>[]).map((c, i) => (
        <div key={i} className="mt-1 flex gap-1.5 text-[10.5px] text-txt-mut">
          <span style={{ color: col }}>{c.sens}</span><span>{c.cle} — {c.valeur}</span></div>
      ))}
      <p className="mt-1 text-[9px] text-txt-dim">{sig.source}</p>
    </div>
  )
}

function MuLigne({ l }: { l: Record<string, any> }) {
  const label = CLIENT.marche.lignes[l.cle as keyof typeof CLIENT.marche.lignes] ?? l.cle
  return (
    <div className="border-b border-line py-1.5 text-[11px]">
      <div className="flex items-start gap-2">
        <span className="min-w-0 flex-1 text-txt">{label}</span>
        <span className={`shrink-0 text-right font-mono tnum ${l.calculable ? 'text-txt-hi' : 'text-txt-dim'}`}>
          {l.calculable ? muValeur(l) : CLIENT.marche.nonCalculable}
        </span>
      </div>
      <div className="mt-0.5 flex items-center gap-2 text-[9.5px] text-txt-dim">
        <span>{l.etiquette}</span>
        {l.date_amont && <span>· {l.date_amont}</span>}
        {!l.calculable && l.motif && <span className="text-st-ecartee">· {l.motif}</span>}
        <span className="ml-auto rounded px-1" style={{ color: MU_FIAB[l.fiabilite] ?? TOKENS.txtDim }}>{l.fiabilite}</span>
      </div>
    </div>
  )
}

function muValeur(l: Record<string, any>): string {
  const v = l.valeurs ?? {}
  switch (l.cle) {
    case 'prix_ancien_median': return `${fmt(v.median_eur_m2)} €/m² (q1 ${fmt(v.q1)}–q3 ${fmt(v.q3)}, n${v.n})`
    case 'prix_terrain_nu_par_zone': {
      const cell = (z: string) => v.par_zone?.[z]?.calculable ? `${fmt(v.par_zone[z].median_eur_m2)} €/m²` : '—'
      return `U ${cell('U')} · AU ${cell('AU')}`
    }
    case 'prix_sortie_neuf': return `${fmt(v.prix_eur_m2)} €/m²`
    case 'tendance_12m': return `${v.delta_pct > 0 ? '↑' : v.delta_pct < 0 ? '↓' : '→'} ${v.delta_pct}% (${v.sens})`
    case 'liquidite': return `${fmt(v.mutations_dernier_trim)} mut./trim (${v.delta_pct_an ?? '—'}% an)`
    case 'offre_engagee': return `${fmt(v.logements_12m)} lgt./12 m`
    case 'gisement_constructible': return `${fmt(v.sdp_residuelle_m2)} m² SDP`
    case 'pression_dpe': return `${v.pct_fg}% F/G (${v.fg}/${v.dpe_connus})`
    case 'loyer_median': return `${v.loyer_eur_m2} €/m²`
    default: return '—'
  }
}

// M137-Z — `communeProp` : quand l'outil Communes pilote la fiche, la commune vient de la table
// (sélecteur interne masqué, bannière masquée). Sans prop = ancien comportement autonome.
export function MarcheCommune({ communeProp }: { communeProp?: string } = {}) {
  const appCommune = useApp((s) => s.commune)
  const [commune, setCommune] = useState(communeProp ?? (appCommune && MU_COMMUNES.includes(appCommune) ? appCommune : 'Saint-Paul'))
  useEffect(() => {
    if (communeProp) setCommune(communeProp)
    else if (appCommune && MU_COMMUNES.includes(appCommune)) setCommune(appCommune)
  }, [communeProp, appCommune])
  const q = useQuery({ queryKey: ['mu-marche', commune], queryFn: () => motMarcheCommune(commune) })
  const d = q.data
  const groupes: [string, string][] = [['PRIX', 'Prix'], ['DYNAMIQUE', 'Dynamique'], ['OFFRE', 'Offre'], ['LOYER', 'Loyer']]
  return (
    <>
      {!communeProp && <Banner>{CLIENT.marche.banner}</Banner>}
      {!communeProp && (
      <select data-marche-commune value={commune} onChange={(e) => setCommune(e.target.value)}
        className="self-start rounded-lg border border-line-2 bg-surface-3 px-2 py-1.5 text-[12px] text-txt focus:border-mint focus:outline-none">
        {MU_COMMUNES.map((c) => <option key={c} value={c}>{c}</option>)}
      </select>)}
      {q.isLoading && <div className="flex flex-1 items-center justify-center py-8"><Loading accent="mint" label="Marché…" big /></div>}
      {d && <>
        {/* M137-Z : le signal est HISSÉ dans l'en-tête sticky de la fiche commune (Communes) — on ne le
            re-rend ici que dans l'usage AUTONOME (sans communeProp) pour ne pas le doublonner. */}
        {!communeProp && <MuSignal sig={d.market_signal} />}
        {/* Mandat COMMUNES (fix scroll) : embarqué dans la fiche (communeProp), on NE crée PAS de
            conteneur de défilement propre — la fiche a un scroll unique et ce div interne le bridait
            (flex-1 collapsé → contenu sous la ligne de flottaison inatteignable). Autonome = inchangé. */}
        <div className={communeProp ? 'flex flex-col' : 'flex min-h-0 flex-1 flex-col overflow-y-auto'}>
          {groupes.map(([g, titre]) => {
            const lignes = (d.lignes as Record<string, any>[]).filter((l) => l.groupe === g)
            if (!lignes.length) return null
            // data-anchor : cible des ancres du header sticky de la fiche (prix / dynamique / offre / loyer).
            return <div key={g} data-anchor={g.toLowerCase()}>
              <p className="label-caps mt-1">{titre}</p>
              {lignes.map((l) => <MuLigne key={l.cle} l={l} />)}
            </div>
          })}
        </div>
        <p className="text-[9.5px] italic text-txt-dim">{CLIENT.marche.note}</p>
      </>}
    </>
  )
}


/* ───────────── M19 — MATCHING TERRAIN ↔ PROMOTEUR ───────────── */


// M15 A3 — REFONTE. DÉMO/RÉEL nettement séparés (le client ne doit jamais douter du réel).
// Les cartes de PROFIL (démo) sont cliquables : un clic ALLUME les parcelles matchées sur la carte
// (un seul profil actif à la fois) ; cliquer une parcelle allumée ouvre sa fiche avec la RAISON du
// match en tête. L'outil démarre VIERGE — rien n'est hérité du filtre carte (RG1).
export function M19() {
  const profiles = useQuery({ queryKey: ['m19'], queryFn: getProfiles })
  const setModuleMap = useApp((s) => s.setModuleMap)
  const setModuleFiche = useApp((s) => s.setModuleFiche)
  const [activeId, setActiveId] = useState<number | null>(null)
  const [nom, setNom] = useState('')
  const [smin, setSmin] = useState('')
  const add = useMutation({ mutationFn: () => addProfile({ nom, surface_min: smin ? Number(smin) : null }),
    onSuccess: () => { setNom(''); setSmin(''); profiles.refetch() } })

  const list = (profiles.data ?? []) as Record<string, any>[]
  const active = list.find((p) => p.id === activeId) ?? null

  // parcelles matchées = les critères du profil (surface/SDP/commune) appliqués comme FILTRE via
  // /parcels (aucun nouveau back). Vierge tant qu'aucun profil n'est actif (RG1 : rien d'hérité).
  const matched = useQuery({
    queryKey: ['m19-matched', activeId],
    queryFn: () => getResults({ ...EMPTY_FILTERS,
      surfaceMin: active?.surface_min ?? null, surfaceMax: active?.surface_max ?? null,
      sdpMin: active?.sdp_min ?? null, communes: active?.commune ? [active.commune] : [] }, 400),
    enabled: activeId != null,
  })

  // ALLUMER les parcelles matchées + poser la RAISON du match sur chaque fiche (moduleFiche).
  useEffect(() => {
    if (activeId == null || !active) { setModuleMap({ idus: [], extra: null }); setModuleFiche({}); return }
    const items = (matched.data ?? []) as Record<string, any>[]
    setModuleMap({ idus: items.map((i) => i.idu as string), extra: null })
    const lines: [string, string][] = [
      ['Correspond au profil', String(active.nom)],
      ['Surface', `${fmt(active.surface_min ?? 0)}–${fmt(active.surface_max ?? 0)} m² ✓`],
    ]
    if (active.sdp_min) lines.push(['SDP résiduelle', `≥ ${fmt(active.sdp_min)} m² ✓`])
    if (active.commune) lines.push(['Commune', `${active.commune} ✓`])
    const mf: Record<string, { module: string; lines: [string, string][] }> = {}
    for (const i of items) mf[i.idu as string] = { module: 'matching', lines }
    setModuleFiche(mf)
    return () => { setModuleMap({ idus: [], extra: null }); setModuleFiche({}) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [matched.dataUpdatedAt, activeId])

  const nMatch = (matched.data as Record<string, any>[] | undefined)?.length ?? 0

  return (
    <>
      <Banner>Deux blocs bien distincts. <b className="text-mint">Profils de démonstration</b>
        (des exemples, pour illustrer) et les <b className="text-mint">promoteurs réellement actifs</b>
        du secteur (donnée SITADEL). <b>Cliquez un profil</b> : les parcelles qui lui correspondent
        <b> s'allument sur la carte</b> — cliquez-en une pour ouvrir sa fiche avec la raison du match.</Banner>

      {/* ── DÉMO — profils cliquables (un seul actif à la fois) ── */}
      <div className="flex items-center gap-1.5">
        <p className="label-caps">Profils de recherche</p>
        <span className="rounded bg-mint/15 px-1.5 py-0.5 text-[8px] font-medium text-mint">DÉMO · EXEMPLES</span>
      </div>
      <div className="flex flex-col gap-1.5">
        {list.map((p) => {
          const on = p.id === activeId
          return (
            <button key={p.id} data-m19-profil aria-pressed={on}
              onClick={() => setActiveId(on ? null : p.id)}
              className={`rounded-lg border px-3 py-2 text-left text-[11px] transition-colors duration-quick ${
                on ? 'border-mint bg-mint/10' : 'border-line-2 bg-surface-3 hover:border-mint/50'}`}>
              <div className="flex items-center gap-2">
                <span className={`font-medium ${on ? 'text-mint' : 'text-txt'}`}>{on ? '● ' : ''}{p.nom}</span>
                <span className="ml-auto text-[9px] text-txt-dim">{on ? 'actif — voir la carte' : 'cliquer pour voir'}</span>
              </div>
              <div className="mt-0.5 text-[10.5px] text-txt-dim">
                {p.commune ?? 'toute commune'} · surface {fmt(p.surface_min)}–{fmt(p.surface_max)} m² · SDP ≥ {p.sdp_min ?? '—'}
              </div>
              {on && <div className="mt-1 text-[10.5px] text-mint">{matched.isFetching ? 'recherche des parcelles…' : `${fmt(nMatch)} parcelle(s) allumée(s) sur la carte — cliquez-en une`}</div>}
            </button>
          )
        })}
      </div>
      {/* ajout d'un profil de démo */}
      <div className="flex gap-1.5">
        <input value={nom} onChange={(e) => setNom(e.target.value)} placeholder="Nouveau profil…"
          className="min-w-0 flex-1 rounded border border-line-2 bg-surface-3 px-2 py-1 text-[11px] text-txt focus:border-mint focus:outline-none" />
        <input value={smin} onChange={(e) => setSmin(e.target.value)} placeholder="surf. min" type="number"
          className="w-20 rounded border border-line-2 bg-surface-3 px-2 py-1 text-[11px] text-txt focus:border-mint focus:outline-none" />
        <button onClick={() => nom.trim() && add.mutate()} disabled={!nom.trim()} title="Ajouter le profil" aria-label="Ajouter le profil"
          className="rounded bg-mint px-2 text-[11px] font-medium text-bg transition-[filter] duration-quick hover:brightness-110 disabled:opacity-40">+</button>
      </div>

      {/* ── RÉEL — promoteurs actifs SITADEL (commune du profil actif) ── */}
      <div className="mt-1 flex items-center gap-1.5">
        <p className="label-caps min-w-0 truncate">Promoteurs actifs du secteur</p>
        <span className="shrink-0 whitespace-nowrap rounded bg-mint/10 px-1.5 py-0.5 text-[8px] font-medium text-mint">RÉEL · SITADEL</span>
      </div>
      <PromoteursActifs commune={active?.commune ?? null} />
    </>
  )
}

// RÉEL — promoteurs SITADEL du secteur (pilotés par la commune du profil actif ; pas d'héritage carte).
function PromoteursActifs({ commune }: { commune: string | null }) {
  const actifs = useQuery({ queryKey: ['m19-actifs', commune], queryFn: () => promoteursActifs(commune!), enabled: !!commune })
  if (!commune) return <p className="text-[10.5px] text-txt-dim">Choisissez un profil ciblant une commune pour voir les promoteurs réellement actifs (SITADEL).</p>
  if (!actifs.data) return <Loading accent="mint" label="Promoteurs actifs…" />
  const promos = (actifs.data.promoteurs as Record<string, any>[]) ?? []
  return (
    <div data-m19-actifs className="flex max-h-48 flex-col gap-1 overflow-y-auto">
      <p className="text-[9.5px] leading-snug text-txt-dim">{actifs.data.source}</p>
      {promos.map((p, k) => (
        <div key={k} className="rounded-lg border border-mint/25 bg-mint/[0.04] px-3 py-1.5 text-[11px]">
          <div className="truncate text-txt" title={`SIREN ${p.siren}`}>{p.nom}</div>
          <div className="text-[10.5px] text-txt-dim">SIREN {p.siren} · <b className="text-txt-mut">{p.n_permis}</b> permis (5 ans){p.logements ? ` · ${p.logements} logements` : ''}</div>
        </div>
      ))}
      {promos.length === 0 && <p className="text-[10.5px] text-txt-dim">Aucun promoteur (personne morale) avec ≥ 2 permis récents ici.</p>}
    </div>
  )
}
