/**
 * Outil « Blocs fonciers » — OUTILS-MUSCLER-3. Sert la table `parcel_blocs` (batch
 * `labuse blocs-build`) : les parcelles CONTIGUËS (0,5 m) d'un même propriétaire personne morale
 * (SIREN), regroupées en une assiette, sur toute l'île. Le propriétaire est TOUJOURS une PM nommée
 * (les particuliers, sans identité stable d'une parcelle à l'autre, sont hors périmètre — dit à
 * l'écran). Aucun calcul métier au front (/modules/blocs sert tout) ; aucun badge de score ; aucun
 * export ; aucune surface IA. SDP résiduelle agrégée = Estimé (somme des résiduels de la fiche).
 * Patrons SOCLE : CommuneScope (choix explicite), filtres à paliers, cartes empilées, pagination
 * 200, tiroir méthode, fil de retour. Ponts : Courrier (sélection), Scan patrimoine (SIREN) et
 * Assembler (les IDU du bloc) par carte, « Voir la fiche » sur chaque IDU du détail.
 */
import { useQuery, useInfiniteQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { BLOCS_PAGE, getBlocDetail, getBlocs, type BlocItem } from '../../lib/api'
import { fmtInt } from '../../lib/format'
import { useApp } from '../../store/useApp'
import { ListPaginationFooter } from '../ListPagination'
import { Squelette } from '../Loading'
import { ErrorState } from '../States'
import { Siren } from '../shared/Siren'
import { Tip } from '../Tip'
import { CommuneScope, useModuleMap } from './ModulePanel'
import { Bouton } from '../ui/Bouton'
import { Case } from '../ui/Case'
import { Chevron } from '../ui/Chevron'
import { Select } from '../ui/Select'   // U3 (RECETTE-OUTILS-4) — menu déroulant partagé

const fmtM2 = (v: number | null | undefined) => (v == null ? '—' : `${fmtInt(v)} m²`)

// Paliers fixes (un select tient dans les 320 px ; le tri serveur reste résiduel décroissant).
const SURFACE_MIN = [
  { v: 0, label: 'toutes' }, { v: 1000, label: '≥ 1 000 m²' }, { v: 5000, label: '≥ 5 000 m²' },
  { v: 10000, label: '≥ 1 ha' }, { v: 50000, label: '≥ 5 ha' },
]
const SDP_MIN = [
  { v: 0, label: 'tous' }, { v: 200, label: '≥ 200 m²' }, { v: 500, label: '≥ 500 m²' },
  { v: 1000, label: '≥ 1 000 m²' }, { v: 5000, label: '≥ 5 000 m²' },
]
const N_MIN = [
  { v: 2, label: '≥ 2' }, { v: 3, label: '≥ 3' }, { v: 6, label: '≥ 6' }, { v: 11, label: '≥ 11' },
]

const Estime = () => (
  <span className="rounded bg-amber-500/15 px-1 text-[8.5px] font-medium text-amber-500">Estimé</span>
)

// Détail d'un bloc (ouvert au clic) — les IDU, chacun avec surface + zone + « Voir la fiche »,
// et l'emprise du bloc mise en surbrillance sur la carte (mécanisme moduleMap).
function BlocDetail({ blocId, siren }: { blocId: number; siren: string | null }) {
  const select = useApp((s) => s.select)
  const setMselPrefill = useApp((s) => s.setMselPrefill)
  const setM02Prefill = useApp((s) => s.setM02Prefill)
  const setModule = useApp((s) => s.setModule)
  const pushOutilRetour = useApp((s) => s.pushOutilRetour)
  const q = useQuery({ queryKey: ['bloc', blocId], queryFn: () => getBlocDetail(blocId) })
  const membres = q.data?.membres ?? []
  // Emprise = les parcelles du bloc surlignées sur la carte tant que le détail est ouvert.
  useModuleMap(membres.map((m) => m.idu), null, [q.dataUpdatedAt])

  if (q.isLoading) return <div className="px-2 py-1"><Squelette lignes={3} /></div>
  if (q.isError || !q.data) return null
  return (
    <div className="mt-1.5 flex flex-col gap-0.5 border-t border-line-2 pt-1.5">
      {/* RECETTE-1 R21 — cliquer la LIGNE (IDU) ouvre la fiche parcelle. */}
      {membres.map((m) => (
        <div key={m.idu} data-bloc-membre data-bloc-fiche role="button" tabIndex={0}
          onClick={(e) => { e.stopPropagation(); select(m.idu) }}
          onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); e.stopPropagation(); select(m.idu) } }}
          className="flex cursor-pointer items-center gap-1.5 rounded px-1 py-0.5 text-[10.5px] hover-fill">
          <span className="font-mono text-txt-hi">{m.idu}</span>
          <span className="text-txt-dim">{fmtM2(m.surface_m2)}</span>
          {m.zone && <span className="text-txt-dim">· {m.zone}</span>}
          <span className="ml-auto tnum text-txt-mut">{fmtM2(m.sdp_residuelle_m2)}</span>
        </div>
      ))}
      {/* OUTILS-REFONTE-1 (9d) — les actions du bloc vivent DANS le détail ouvert (la carte, elle, n'a plus
          de bouton) : Assembler (IDU du bloc) · Scan patrimoine (SIREN). Fil de retour vers Blocs. */}
      <div className="mt-1 flex flex-wrap gap-1.5">
        <Bouton niveau="secondaire" ton="vert" data-bloc-assembler
          onClick={(e) => { e.stopPropagation(); setMselPrefill(membres.map((m) => m.idu)); setModule('assemblage'); pushOutilRetour({ module: 'blocs-fonciers', label: 'Blocs fonciers' }) }}>
          ⛶ Assembler ce bloc →
        </Bouton>
        {siren && (
          <Bouton niveau="secondaire" ton="vert" data-bloc-scan
            onClick={(e) => { e.stopPropagation(); setM02Prefill(siren); setModule('patrimoine'); pushOutilRetour({ module: 'blocs-fonciers', label: 'Blocs fonciers' }) }}>
            Scan patrimoine →
          </Bouton>
        )}
      </div>
    </div>
  )
}

// RECETTE-OUTILS-3 (pt 41 — « variante B · Cartes ») — une carte par bloc, trois lignes :
// (1) chevron + dénomination + « Commune · SIREN » / pastille « N parcelles » ;
// (2) deux tuiles Surface totale / SDP résiduelle estimée ;
// (3) zonages PLU + petit bouton « Scan patrimoine → » (pt 42). Détail des parcelles à l'ouverture.
function Carte({ it, ouvert, onToggle }: { it: BlocItem; ouvert: boolean; onToggle: () => void }) {
  // OUTILS-REFONTE-1 (9d) — zonages PLU : 5 puces au maximum, « +N » déplie le reste au clic.
  const [zonesDepliees, setZonesDepliees] = useState(false)
  const commune = it.communes[0]   // commune principale (première listée)
  const ZONES_MAX = 5
  const zonesVisibles = zonesDepliees ? it.zonages : it.zonages.slice(0, ZONES_MAX)
  const zonesCachees = it.zonages.length - ZONES_MAX
  return (
    // OUTILS-REFONTE-1 (9d) — carte CLIQUABLE, SANS bouton : nom · SIREN · commune · N parcelles ·
    // surface · plancher restant · zones. Un clic ouvre le bloc (parcelles, carte, Scan patrimoine).
    <div data-bloc-row role="button" tabIndex={0} onClick={onToggle}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onToggle() } }}
      className="cursor-pointer rounded-lg border border-line-2 bg-surface-3 px-3 py-2.5 transition-colors duration-quick hover:border-mint/50">
      {/* ligne 1 : dénomination · SIREN (droite, vert) */}
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 break-words text-[14px] font-semibold leading-tight text-txt">{it.denomination ?? '—'}</div>
        {it.siren && (
          <span className="shrink-0 whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
            <Siren value={it.siren} className="font-mono text-[11px] text-mint" />
          </span>
        )}
      </div>
      {/* ligne 2 : commune · N parcelles */}
      <div className="mt-0.5 text-[10.5px] text-txt-mut">
        {commune ?? '—'} · <span className="tnum">{it.n_parcelles}</span> parcelles
      </div>
      {/* ligne 3 : surface · plancher restant (vert) */}
      <div className="mt-1.5 flex items-start gap-8">
        <div>
          <div className="tnum text-[13px] text-txt">{fmtM2(it.surface_totale_m2)}</div>
          <div className="text-[9px] uppercase tracking-wide text-txt-dim">surface</div>
        </div>
        <div>
          <div className="tnum text-[13px] font-medium text-mint">{fmtM2(it.sdp_residuelle_m2)}</div>
          <div className="text-[9px] uppercase tracking-wide text-txt-dim">plancher restant <Estime />
            {it.sdp_couverture < it.n_parcelles && <span className="normal-case"> · sur {it.sdp_couverture}/{it.n_parcelles}</span>}
          </div>
        </div>
      </div>
      {/* ligne 4 : zonages PLU en puces (5 max + « +N » dépliable) */}
      <div className="mt-1.5 flex flex-wrap items-center gap-1">
        {it.zonages.length === 0 && <span className="font-mono text-[10.5px] text-txt-dim">—</span>}
        {zonesVisibles.map((z, i) => (
          <span key={i} data-bloc-zone className="rounded-full border border-line-2 px-1.5 py-0.5 font-mono text-[10px] text-txt-dim">{z}</span>
        ))}
        {!zonesDepliees && zonesCachees > 0 && (
          <button data-bloc-zones-plus onClick={(e) => { e.stopPropagation(); setZonesDepliees(true) }}
            className="rounded-full border border-line-2 px-1.5 py-0.5 font-mono text-[10px] text-mint hover:underline">+{zonesCachees}</button>
        )}
      </div>

      {ouvert && <BlocDetail blocId={it.bloc_id} siren={it.siren} />}
    </div>
  )
}

export function Blocs() {
  // OUTILS-S1 (Lot D) — plus de pont Courrier ici : `setModule`/`pushOutilRetour` restent portés par
  // les cartes (Scan patrimoine, Assembler), pas par le conteneur.
  const [commune, setCommune] = useState<string | null>(null)   // Toute l'île par défaut
  const [surfMin, setSurfMin] = useState(0)
  const [sdpMin, setSdpMin] = useState(0)
  const [nMin, setNMin] = useState(2)
  const [inclurePublics, setInclurePublics] = useState(false)   // publics écartés par défaut
  const [openId, setOpenId] = useState<number | null>(null)
  // RECETTE-1 R21 — deux temps : (1) on pose ses filtres ; (2) on clique « Voir les parcelles »,
  // le listing s'ouvre et le bloc de filtres se replie en accordéon. `montre` gouverne les deux.
  const [montre, setMontre] = useState(false)
  const [filtresOuverts, setFiltresOuverts] = useState(true)
  const voir = () => { setMontre(true); setFiltresOuverts(false) }
  const select = useApp((s) => s.select)             // RECETTE-1 F3 — fermer la fiche ouverte par un bloc
  const selectedIdu = useApp((s) => s.selectedIdu)

  // OUTILS-S1 (Lot D) — la sélection multiple ne servait QU'au pont Courrier (retiré) : plus de cases
  // à cocher par bloc (hors DA des autres outils). Le seul geste par bloc = « Scan patrimoine → ».
  const reset = () => { setOpenId(null) }
  // RECETTE-1 (F3) — Réinitialiser : remet TOUS les filtres au défaut, replie le listing, rouvre les
  // filtres, ferme la fiche éventuellement ouverte par un bloc. Reste dans l'outil.
  const dirty = montre || commune !== null || surfMin > 0 || sdpMin > 0 || nMin !== 2 || inclurePublics
  const resetAll = () => {
    setCommune(null); setSurfMin(0); setSdpMin(0); setNMin(2); setInclurePublics(false)
    setOpenId(null); setMontre(false); setFiltresOuverts(true)
    if (selectedIdu) select(null)
  }
  // RECETTE-OUTILS-3 (pt 39) — résumé court des filtres actifs, à droite de l'en-tête replié.
  // Portée commune + seuls les paliers qui diffèrent du défaut ; tout au défaut → juste la portée.
  const resumeFiltres = (() => {
    const bouts: string[] = [commune ?? "Toute l'île"]
    if (nMin !== 2) bouts.push(`${N_MIN.find((o) => o.v === nMin)?.label ?? `≥ ${nMin}`} parcelles`)
    else bouts.push('≥ 2 parcelles')
    if (surfMin > 0) bouts.push(`surface ${SURFACE_MIN.find((o) => o.v === surfMin)?.label ?? `≥ ${surfMin} m²`}`)
    if (sdpMin > 0) bouts.push(`résiduel ${SDP_MIN.find((o) => o.v === sdpMin)?.label ?? `≥ ${sdpMin} m²`}`)
    return bouts.join(' · ')
  })()
  const q = useInfiniteQuery({
    queryKey: ['blocs', commune, surfMin, sdpMin, nMin, inclurePublics],
    queryFn: ({ pageParam }) => getBlocs(commune, surfMin, sdpMin, nMin, inclurePublics, pageParam),
    initialPageParam: 0,
    getNextPageParam: (last, pages) => { const n = pages.reduce((s, p) => s + p.items.length, 0); return n < last.total ? n : undefined },
    enabled: montre,   // R21 — rien ne charge tant que « Voir les parcelles » n'est pas cliqué
  })
  const items = q.data?.pages.flatMap((p) => p.items) ?? []
  const meta = q.data?.pages[0]
  const total = meta?.total ?? 0

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
      {/* RECETTE-OUTILS-1 (T5) — plus de « Réinitialiser » en tête : le lien « Réinitialiser les filtres »
          vit DANS le bloc Filtres (ci-dessous), visible seulement quand un filtre diffère du défaut. */}
      {/* RETOURS-25 (pt 11) — bandeau d'intro « Les parcelles contiguës d'un même propriétaire… » retiré. */}

      {/* RECETTE-OUTILS-3 (pt 39) — contrôles de filtres : même rendu, qu'on soit AVANT (déployés,
          sans chrome d'accordéon) ou APRÈS « Voir les parcelles » (repliés dans l'accordéon). */}
      {(() => {
        const controles = (
          <div className="flex flex-col gap-2">
            <CommuneScope commune={commune} noteFiltre={false} onChange={(c) => { setCommune(c); reset() }} />
            {/* OUTILS-REFONTE-1 (9d) — 4 menus compacts (commune + 3 paliers), en grille 2×2. */}
            <div className="grid grid-cols-2 gap-1.5 text-[11px] text-txt-mut">
              <label className="flex items-center gap-1.5">Surface
                <Select data-blocs-surf-min value={surfMin} onChange={(e) => { setSurfMin(Number(e.target.value)); reset() }}
                  className="h-8 min-w-0 flex-1 rounded-md border border-line-2 bg-surface-3 px-2 text-txt focus:outline-none">
                  {SURFACE_MIN.map((o) => <option key={o.v} value={o.v}>{o.label}</option>)}
                </Select>
              </label>
              <label className="flex items-center gap-1.5">Plancher restant
                <Select data-blocs-sdp-min value={sdpMin} onChange={(e) => { setSdpMin(Number(e.target.value)); reset() }}
                  className="h-8 min-w-0 flex-1 rounded-md border border-line-2 bg-surface-3 px-2 text-txt focus:outline-none">
                  {SDP_MIN.map((o) => <option key={o.v} value={o.v}>{o.label}</option>)}
                </Select>
              </label>
              <label className="flex items-center gap-1.5">Parcelles
                <Select data-blocs-n-min value={nMin} onChange={(e) => { setNMin(Number(e.target.value)); reset() }}
                  className="h-8 min-w-0 flex-1 rounded-md border border-line-2 bg-surface-3 px-2 text-txt focus:outline-none">
                  {N_MIN.map((o) => <option key={o.v} value={o.v}>{o.label}</option>)}
                </Select>
              </label>
            </div>
            {/* OUTILS-REFONTE-1 (9d) — case « Inclure les propriétaires publics » (écartés par défaut) ·
                « Réinitialiser » à droite (vert), visible dès qu'un filtre diffère du défaut. */}
            <div className="flex items-center gap-2 text-[11px] text-txt-mut">
              <Case data-blocs-inclure-publics
                checked={inclurePublics} onChange={(e) => { setInclurePublics(e.target.checked); reset() }}
                label="Inclure les propriétaires publics" />
              <Tip garder tip="Communes, État, Région/Département/EPCI, établissements publics (dont EPF) et SEM — classés par leur catégorie juridique (fichiers des personnes morales, DGFiP), jamais par une liste de noms. Écartés par défaut car rarement cessibles à un promoteur.">
                <span className="cursor-help rounded-full border border-line-2 px-1 text-[8px] text-txt-dim">i</span>
              </Tip>
              {dirty && (
                <Bouton niveau="lien" ton="vert" data-blocs-reset-filtres onClick={resetAll} className="ml-auto">
                  Réinitialiser
                </Bouton>
              )}
            </div>
          </div>
        )
        // AVANT « Voir les parcelles » : filtres DÉPLOYÉS, sans en-tête repliable (rien derrière).
        if (!montre) {
          return (
            <div data-blocs-filtres className="flex flex-col gap-2">
              <div className="py-0.5 text-[11px] font-medium text-txt-dim">Filtres</div>
              {controles}
            </div>
          )
        }
        // APRÈS : accordéon « › Filtres » FERMÉ, résumé des filtres actifs à DROITE de l'en-tête.
        return (
          <details data-blocs-filtres open={filtresOuverts}
            onToggle={(e) => setFiltresOuverts((e.target as HTMLDetailsElement).open)}
            className="flex flex-col gap-2">
            <summary className="flex cursor-pointer list-none items-center gap-1.5 py-0.5 text-[11px] font-medium text-txt-dim marker:hidden hover:text-mint">
              <Chevron open={filtresOuverts} />Filtres
              <span data-blocs-filtres-resume className="ml-2 min-w-0 flex-1 truncate text-[10.5px] font-normal text-txt-mut">
                {resumeFiltres}
              </span>
            </summary>
            <div className="mt-1">{controles}</div>
          </details>
        )
      })()}

      {/* RECETTE-1 R21 — le geste explicite : ouvrir le listing (et replier les filtres). */}
      {!montre && (
        <Bouton niveau="primaire" ton="vert" data-blocs-voir onClick={voir} className="shrink-0">
          Voir les parcelles
        </Bouton>
      )}

      {q.isLoading && <Squelette lignes={6} />}
      {q.isError && <ErrorState message="Signal momentanément indisponible — réessayez." retry={() => q.refetch()} />}
      {meta && total === 0 && (
        // ÉTAT VIDE HONNÊTE — jamais de zéros : le périmètre est nommé.
        <p data-blocs-vide className="rounded-lg bg-surface-2 px-3 py-2 text-[11px] leading-snug text-txt-mut">
          Aucun bloc de deux parcelles ou plus
          {commune ? <> à <b className="text-txt">{commune}</b></> : ' sur l’île'}
          {surfMin ? ` (surface ≥ ${fmtInt(surfMin)} m²)` : ''}{sdpMin ? ` (résiduel ≥ ${fmtInt(sdpMin)} m²)` : ''}
          {nMin > 2 ? ` (≥ ${nMin} parcelles)` : ''}.{/* RETOURS-25 (pt 11) — date « au … » retirée. */}
          {!inclurePublics && meta.n_publics > 0 && (
            <> {fmtInt(meta.n_publics)} propriétaire{meta.n_publics > 1 ? 's' : ''} public{meta.n_publics > 1 ? 's' : ''} écarté{meta.n_publics > 1 ? 's' : ''} (cochez « inclure les propriétaires publics » pour les voir).</>
          )}
        </p>
      )}
      {meta && total > 0 && (
        <>
          {/* OUTILS-REFONTE-1 (9d) — compteur : « N blocs · personnes morales DGFiP ». */}
          <div data-blocs-bandeau className="rounded-lg bg-surface-2 px-3 py-2 text-[10.5px] leading-snug text-txt-mut">
            <b data-blocs-total className="tnum text-txt">{fmtInt(total)}</b> bloc{total > 1 ? 's' : ''} ·
            <b className="text-txt"> personnes morales DGFiP</b>{commune ? ` — ${commune}` : ''}
            {!inclurePublics && meta.n_publics > 0 && (
              <span data-blocs-ecartes className="text-txt-dim"> · {fmtInt(meta.n_publics)} public{meta.n_publics > 1 ? 's' : ''} écarté{meta.n_publics > 1 ? 's' : ''}</span>
            )}
          </div>

          {/* OUTILS-S1 (Lot D) — plus de « Tout sélectionner » ni de case par bloc : la sélection multiple
              ne servait qu'au Courrier (retiré). Chaque carte porte son seul geste : « Scan patrimoine → ». */}
          <div className="flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto">
            {items.map((it) => (
              <Carte key={it.bloc_id} it={it} ouvert={openId === it.bloc_id}
                onToggle={() => setOpenId((o) => (o === it.bloc_id ? null : it.bloc_id))} />
            ))}
          </div>
          <ListPaginationFooter shown={items.length} total={total} step={BLOCS_PAGE} onMore={() => q.fetchNextPage()}>
            {q.isFetchingNextPage && <span className="text-txt-dim">chargement…</span>}
          </ListPaginationFooter>
          {/* OUTILS-REFONTE-1 (9d) — ligne discrète : ce qu'un clic sur une carte ouvre. */}
          <p className="shrink-0 text-[9.5px] leading-snug text-txt-dim">Un clic ouvre le bloc : parcelles, carte, Scan patrimoine.</p>
        </>
      )}
      {/* OUTILS-S1 (Lot D) — pied retiré : « Détail et méthode » remonté dans le « i » de l'en-tête ;
          raccourci « Préparer les courriers » supprimé (pont Courrier + sélection multiple abandonnés). */}
    </div>
  )
}
