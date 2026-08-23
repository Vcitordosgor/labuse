import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'
import {
  courrierPdf, getCommunes, getCourrierDemandes, getFiche, modBailleur,
  modDueDiligence, modFantome, modPatrimoine, modPatrimoineSearch, modPermis, modPermisFiche,
  modPromesses, modPromessesCount, modVelocite, postCourrierDemande,
} from '../../lib/api'
import { AddressAutocomplete } from '../AddressAutocomplete'
import { ParcelInput } from '../ParcelInput'
import { fmtEurCompact, fmtInt } from '../../lib/format'
import { iduComplet, iduCourt } from '../../lib/format'
import { pointInPolygon } from '../../lib/geo'
import { TOKENS } from '../../lib/tokens'
import { useApp } from '../../store/useApp'
import { Loading } from '../Loading'
import { EtudierBien } from './EtudierBien'
import { CompareModule } from '../compare/ComparePanel'
import { M22 } from './M22Programme'
// O10Bascules (Quoi de neuf) retiré du produit le 21/08/2026 (DORMANT) — plus importé ici ; le
// composant reste exporté dans ./blocB (endpoint /events vivant via la cloche de notifications).
// O7Carnet (Suivi de secteur) retiré du produit le 21/08/2026 (DORMANT) — plus importé ici ; le
// composant reste exporté dans ./blocB (endpoints /carnet-secteur vivants ; le vrai suivi = la Veille).
import { O5Servitudes } from './blocB'
// M17 (Simulateur ZAN) retiré du produit le 21/08/2026 (DORMANT) — plus monté ; composant exporté au
// dépôt dans ./moteurs. Enveloppe ZAN déplacée dans Communes ; endpoints /moteurs/zan* vivants.
import { M16 } from './moteurs'
// M137-Z — outil « Communes » (fusion Marché·Comparateur·Vélocité·Rareté). O6Comparateur, O9Rarete et
// MarcheCommune ne sont plus montés ici directement : Communes les réutilise.
import { Communes } from './Communes'
import { MODULES, VIOLET } from './registry'
// M137-P/Q — outil PLU UNIFIÉ : le hub monte 2 voies — PluAnnuaire et ProcedureChangement (qui
// réutilise VerifProcedure + M15/simulplu).
import { Plu } from './Plu'
// M137-K : ScoringV2Module (Radar des ventes) retiré du produit (DORMANT) — plus importé/monté ;
// le composant reste au dépôt dans ./ScoringV2 (cf. son en-tête).
import { RenouvellementModule } from './Renouvellement'
import { ProspectionSolaire } from './ProspectionSolaire'
import { TierBadge } from './TierBadge'

/* ───────── primitives partagées (doctrine module : violet, bandeau honnête, liste→fiche) ───────── */

function Banner({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-mint/40 bg-mint/[0.07] px-3 py-2 text-[10.5px] leading-relaxed text-txt-mut">
      {children}
    </div>
  )
}

function Row({ idu, right, sub, fiche }: { idu: string; right: React.ReactNode; sub?: string; fiche?: [string, string][] }) {
  const { select, moduleFiche, setModuleFiche, module } = useApp()
  return (
    <button
      onClick={() => {
        if (fiche && module) setModuleFiche({ ...moduleFiche, [idu]: { module, lines: fiche } })
        select(idu)
      }}
      className="flex w-full shrink-0 items-center gap-2 rounded-lg border border-line-2 bg-surface-3 px-3 py-2 text-left transition-colors duration-quick hover:border-mint/50"
    >
      <div className="min-w-0 flex-1">
        <div className="font-mono text-xs text-txt-hi">{idu.slice(8, 10)} {idu.slice(10)}</div>
        {sub && <div className="truncate text-[10.5px] text-txt-mut">{sub}</div>}
      </div>
      <div className="shrink-0 text-right">{right}</div>
    </button>
  )
}

const V = ({ children }: { children: React.ReactNode }) => (
  <span className="num-key text-sm text-mint">{children}</span>
)

const fmt = fmtInt

/** Pousse résultats sur la carte (surlignage violet + géométries propres) — et nettoie en sortie. */
function useModuleMap(idus: string[], extra: unknown | null, deps: unknown[]) {
  const setModuleMap = useApp((s) => s.setModuleMap)
  useEffect(() => {
    setModuleMap({ idus, extra })
    return () => setModuleMap({ idus: [], extra: null })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
}

const featureCollection = (features: unknown[]) => ({ type: 'FeatureCollection', features })

/** Bouton « voir plus » — plafond levé, chargement paginé (offset) sans dump complet. */
function MoreButton({ q, loaded, total }: { q: { hasNextPage: boolean; isFetchingNextPage: boolean; fetchNextPage: () => void }; loaded: number; total?: number }) {
  if (!q.hasNextPage) return null
  return (
    <button data-more onClick={() => q.fetchNextPage()} disabled={q.isFetchingNextPage}
      className="mt-1 min-h-8 shrink-0 rounded-lg border border-mint/40 py-1.5 text-[11px] text-mint transition-colors duration-quick hover:bg-mint/10 disabled:opacity-40">
      {q.isFetchingNextPage ? 'Chargement…' : total != null ? `Voir plus — ${fmt(loaded)} / ${fmt(total)} chargés` : `Voir plus — ${fmt(loaded)} chargés`}
    </button>
  )
}

/** M15-G — sélecteur de périmètre EXPLICITE : l'outil n'hérite plus du filtre commune global. */
export function CommuneScope({ commune, onChange }: { commune: string | null; onChange: (c: string | null) => void }) {
  const communes = useQuery({ queryKey: ['communes'], queryFn: getCommunes })
  return (
    <label className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-txt-mut">
      Périmètre
      <select data-commune-scope value={commune ?? ''} onChange={(e) => onChange(e.target.value || null)}
        className="rounded border border-line-2 bg-surface-3 px-1.5 py-0.5 text-txt focus:border-mint focus:outline-none">
        <option value="">Toute l'île</option>
        {(communes.data ?? []).map((c) => <option key={c.commune} value={c.commune}>{c.commune}</option>)}
      </select>
      <span className="text-[10px] text-txt-dim">choisi ici — pas hérité du filtre global</span>
    </label>
  )
}

/* M129-C (Vic 19/08/2026) : M01 — Division retiré du produit (dormant) — code backend au dépôt. */

/* ───────────────────────────── M02 — PATRIMOINE ───────────────────────────── */

function M02() {
  const { m02Prefill, setM02Prefill, setMsel, setModule, setCourrierPrefill } = useApp()
  const [q, setQ] = useState('')
  const [siren, setSiren] = useState<string | null>(null)
  useEffect(() => {
    if (m02Prefill) { setSiren(m02Prefill); setM02Prefill(null) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [m02Prefill])
  const sug = useQuery({ queryKey: ['m02s', q], queryFn: () => modPatrimoineSearch(q), enabled: q.length >= 2 && !siren })
  const pat = useQuery({ queryKey: ['m02', siren], queryFn: () => modPatrimoine(siren!), enabled: !!siren })
  const d = pat.data as Record<string, any> | undefined
  const items = ((d?.['items'] ?? []) as Record<string, any>[])
  useModuleMap(items.map((i) => i['idu'] as string), null, [pat.dataUpdatedAt])
  return (
    <>
      <input value={q} onChange={(e) => { setQ(e.target.value); setSiren(null) }}
        placeholder="SIREN ou nom (ex. CBO, SCI…)"
        className="rounded-lg border border-line-2 bg-surface-3 px-2 py-1.5 text-xs text-txt focus:border-mint focus:outline-none" />
      {!siren && (sug.data ?? []).map((s) => (
        <button key={s.siren} onClick={() => setSiren(s.siren)}
          className="flex items-center justify-between rounded-lg border border-line-2 bg-surface-3 px-3 py-1.5 text-left text-xs text-txt transition-colors duration-quick hover:border-mint/50">
          <span className="truncate">{s.nom}</span><span className="font-mono text-[11px] text-txt-dim">{s.n} parc.</span>
        </button>
      ))}
      {/* garde : le typeahead plafonne à 12 — on le DIT (jamais une coupe muette). */}
      {!siren && (sug.data?.length ?? 0) >= 12 && (
        <p className="text-[10.5px] text-txt-dim">12 premiers résultats — affinez le nom ou le SIREN.</p>
      )}
      {/* Fix pré-lancement : distinguer un « 0 résultat LÉGITIME » d'une panne — sans ça, une boîte
          absente des fichiers fonciers (ex. VISHOR MATERIAUX) donne un écran muet lu comme « cassé ». */}
      {!siren && q.length >= 2 && !sug.isFetching && (sug.data?.length ?? 0) === 0 && (
        <div data-m02-vide className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-[11px] leading-snug text-txt-mut">
          « <b className="text-txt">{q}</b> » n'a pas de foncier connu dans les fichiers fonciers (DGFiP),
          ou n'y figure pas. Ces fichiers ne recensent que les <b>personnes morales</b> détentrices de
          foncier à La Réunion — une personne physique ou une société sans bien détecté n'apparaît pas.
        </div>
      )}
      {d && (
        <>
          {/* signaux d'APPROCHE : BODACC (procédure) + INPI (société absente du registre = succession /
              sommeil probable). Libellés FACTUELS — jamais « fantôme ». */}
          {d['bodacc'] != null && (
            <div className="rounded-lg border border-st-ecartee/40 bg-st-ecartee/10 px-3 py-2 text-[11px] text-st-ecartee">
              ● BODACC — {(d['bodacc'] as Record<string, string>)['type_procedure']}
            </div>
          )}
          {d['inpi_sans_dirigeant'] === true && (
            <div data-m02-inpi className="rounded-lg border border-st-creuser/40 bg-st-creuser/10 px-3 py-2 text-[11px] text-st-creuser">
              ● Aucun dirigeant au registre INPI — succession ou société en sommeil probable (signal d'approche). À vérifier au registre.
            </div>
          )}
          <div className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-xs">
            <div className="truncate font-medium text-txt-hi">{d['nom'] as string}</div>
            {/* #2 l'agrégat dit l'ACTIONNABLE (hors écartées) + SDP RÉSIDUELLE (c'en est) */}
            <div className="mt-1 flex flex-wrap gap-x-4 gap-y-0.5 text-[11px] text-txt-mut">
              <span><V>{d['n_parcelles'] as number}</V> parcelles</span>
              <span><V>{d['n_actionnables'] as number}</V> actionnables <span className="text-txt-dim">(hors écartées)</span></span>
              <span>SDP résiduelle <V>{fmt(d['sdp_residuelle_m2'] as number)}</V> m²</span>
            </div>
            {/* #3 valorisation indicative du foncier nu (zones U/AU) au référentiel unique prix de zone */}
            {d['valorisation_nu_eur'] != null && (
              <div className="mt-1 text-[11px] text-txt-dim">Valorisation indicative du foncier nu <span className="text-txt-dim">(zones U/AU, DVF terrains)</span> : <b className="tnum text-txt">{fmtEurCompact(d['valorisation_nu_eur'] as number)}</b></div>
            )}
          </div>
          {/* #5 assiette contiguë dans le portefeuille → « Analyser en assiette » (msel + Assemblage) */}
          {(d['assiette_contigue'] as string[])?.length >= 2 && (
            <button data-m02-assiette onClick={() => { setMsel(d['assiette_contigue'] as string[]); setModule('assemblage') }}
              className="rounded-lg border border-mint/40 bg-mint/[0.06] px-3 py-1.5 text-left text-[11px] text-mint transition-colors duration-quick hover:bg-mint/10">
              {(d['assiette_contigue'] as string[]).length} parcelles contiguës dans ce portefeuille — Analyser en assiette →
            </button>
          )}
          <div className="flex min-h-0 flex-1 flex-col gap-1.5 overflow-y-auto">
            {items.map((i) => (
              <div key={i['idu'] as string} className="flex items-stretch gap-1">
                <div className="min-w-0 flex-1">
                  <Row idu={i['idu'] as string}
                    sub={`${i['commune']} · ${fmt(i['surface_m2'] as number)} m² · SDP ${fmt(i['sdp'] as number)}`}
                    right={<TierBadge tier={i['tier_v2'] as string | null} etage0={i['etage0'] as boolean | null} statut={null} />}
                    fiche={[['Propriétaire', String(d['nom'])], ['SIREN', String(d['siren'])],
                      ['Patrimoine', `${d['n_parcelles']} parcelles · SDP résiduelle ${fmt(d['sdp_residuelle_m2'] as number)} m²`]]} />
                </div>
                {/* #5 l'action au bout : courrier de CETTE parcelle, prérempli (patron Assemblage) */}
                <button data-m02-courrier title="Préparer le courrier de cette parcelle"
                  onClick={() => { setCourrierPrefill(i['idu'] as string); setModule('courriers') }}
                  className="shrink-0 rounded-lg border border-mint/40 px-2 text-[11px] text-mint transition-colors duration-quick hover:bg-mint/10">✉</button>
              </div>
            ))}
          </div>
        </>
      )}
    </>
  )
}

/* ───────────────────────────── M03 — RADAR PERMIS ───────────────────────────── */

const NATURES = [['', 'Tout'], ['PC', 'PC'], ['DP', 'DP'], ['PA', 'PA'], ['PD', 'PD']] as const

/** Tiroir « fiche permis » (M10 lot 1.1) — s'ouvre au clic sur un permis, partagé radar/fiche. */
export function PermitDrawer({ permitId, onClose }: { permitId: string; onClose: () => void }) {
  const q = useQuery({ queryKey: ['permis-fiche', permitId], queryFn: () => modPermisFiche(permitId) })
  const d = q.data as Record<string, any> | undefined
  const select = useApp((s) => s.select)      // Fix LOT 2 : localiser la parcelle du permis
  const setFlyTo = useApp((s) => s.setFlyTo)
  // géom du permis (centroïde parcelle) : présente ssi géocodé ; sinon on ne peut pas localiser.
  const geom = d?.['geom'] as { coordinates?: [number, number] } | null | undefined
  const parcelle = (d?.['parcelles'] as string[] | undefined)?.[0]
  const localiser = () => {
    if (!geom?.coordinates) return
    setFlyTo({ center: geom.coordinates, zoom: 18 })
    if (parcelle && parcelle.length === 14) select(parcelle)   // halo sur la parcelle rattachée
    onClose()
  }
  const F = ({ label, value }: { label: string; value: React.ReactNode }) =>
    value == null || value === '' ? null : (
      <div className="flex justify-between gap-3 border-b border-line py-1.5 text-[11px]">
        <span className="text-txt-dim">{label}</span>
        <span className="text-right text-txt">{value}</span>
      </div>
    )
  return (
    <div data-permis-drawer className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 sm:items-center" onClick={onClose}>
      <div className="max-h-[80vh] w-full max-w-md overflow-y-auto rounded-t-2xl border border-mint/40 bg-surface-1 p-4 shadow-elev-3 sm:rounded-2xl"
        onClick={(e) => e.stopPropagation()}>
        {q.isLoading && <Loading />}
        {/* audit-promesses — un permis INTROUVABLE (404) dit clairement pourquoi (avant : drawer vide). */}
        {q.isError && (
          <div data-permis-introuvable className="flex flex-col gap-2">
            <div className="flex items-start justify-between gap-2">
              <div className="font-display text-sm font-bold text-txt-hi">Permis introuvable</div>
              <button onClick={onClose} aria-label="Fermer" className="flex h-7 w-7 items-center justify-center rounded-full border border-line-2 text-[11px] text-txt-mut transition-colors duration-quick hover:text-txt">✕</button>
            </div>
            <p className="rounded-lg border border-st-creuser/40 bg-st-creuser/10 px-3 py-2 text-[11px] leading-snug text-st-creuser">
              Aucun permis <span className="font-mono">{permitId}</span> dans la base SITADEL (dép. 974).
              Vérifiez le numéro (référence exacte de l'autorisation) — la base couvre 2013 à aujourd'hui.
            </p>
          </div>
        )}
        {d && (
          <>
            <div className="mb-2 flex items-start justify-between gap-2">
              <div>
                <div className="font-display text-sm font-bold text-txt-hi">{d['nature_libelle']}</div>
                <div className="font-mono text-[11px] text-txt-mut">{d['permit_id']} · {d['commune']}</div>
              </div>
              <button onClick={onClose} aria-label="Fermer" className="flex h-7 w-7 items-center justify-center rounded-full border border-line-2 text-[11px] text-txt-mut transition-colors duration-quick hover:text-txt">✕</button>
            </div>
            <F label="Statut" value={d['statut']} />
            <F label="Porteur" value={d['porteur'] ?? <span className="text-txt-dim">{d['porteur_note']}</span>} />
            {d['porteur_siren'] && <F label="SIREN" value={<span className="font-mono">{d['porteur_siren']}</span>} />}
            <F label="Nombre de lots" value={d['nb_lots']} />
            <F label="Surface habitable" value={d['surface_hab_m2'] != null ? `${fmt(d['surface_hab_m2'])} m²` : null} />
            <F label="Date de dépôt" value={d['date_depot']} />
            <F label="Date d'autorisation" value={d['date_autorisation']} />
            <F label="Achèvement (DAACT)" value={d['date_achevement']} />
            {d['delai_instruction'] && (
              <F label="Délai d'instruction" value={<span className="font-semibold text-mint">{d['delai_instruction']['libelle']}</span>} />
            )}
            <F label="Parcelle(s)" value={<span className="font-mono text-[10px]">{(d['parcelles'] as string[]).join(', ')}</span>} />
            {/* Fix LOT 2 : localiser la parcelle sur la carte (géocodé) ou message clair (non géocodé) —
                jamais un clic mort. La géom d'un permis = centroïde de la parcelle rattachée. */}
            {geom?.coordinates ? (
              <button data-permis-localiser onClick={localiser}
                className="mt-3 flex w-full items-center justify-center gap-2 rounded-lg border border-mint/40 bg-mint/[0.08] py-2 text-[12px] font-medium text-mint transition-colors duration-quick hover:bg-mint/15">
                ◎ Voir la parcelle sur la carte
              </button>
            ) : (
              <div data-permis-nongeocode className="mt-3 rounded-lg border border-st-creuser/40 bg-st-creuser/10 px-3 py-2 text-[11px] leading-snug text-st-creuser">
                <b>Permis non géocodé</b> — son adresse n'a pas pu être rattachée à une parcelle du
                cadastre, il ne peut pas être localisé sur la carte.
              </div>
            )}
            <p className="mt-2 text-[10px] text-txt-dim">{d['source']}</p>
          </>
        )}
      </div>
    </div>
  )
}

// §3 (23/08/2026) — outil « PERMIS » UNIFIÉ : fusion de « Radar permis » (M03) et « Permis au point
// mort » (M04). Le radar est l'ENTRÉE (tous les permis Sitadel, points cliquables + fiche) ; « Au point
// mort » est un FILTRE qui ne garde que les PC anciens sans achèvement — désormais rendus en POINTS
// CLIQUABLES (comme le radar), plus en surlignage de parcelle. Les DEUX clés internes vivent : `promesses`
// ouvre l'outil avec le filtre déjà actif (deep-link/copilote/QA inchangés, aucun 404).
function M03() {
  const moduleKey = useApp((s) => s.module)
  const [pointMort, setPointMort] = useState(moduleKey === 'promesses')
  const [months, setMonths] = useState(moduleKey === 'promesses' ? 36 : 24)
  const [nature, setNature] = useState('')
  const [open, setOpen] = useState<string | null>(null)
  const [permSearch, setPermSearch] = useState('')
  const zone = useApp((s) => s.zone)
  const commune = useApp((s) => s.commune)
  // radar-permis #2a — un clic sur un point permis de la carte (MapView) demande l'ouverture du drawer
  // via `permitToOpen` ; on le consomme puis on le remet à null (même idiome que parcelPrefill).
  const permitToOpen = useApp((s) => s.permitToOpen)
  const setPermitToOpen = useApp((s) => s.setPermitToOpen)
  const setFlyTo = useApp((s) => s.setFlyTo)
  useEffect(() => { if (permitToOpen) { setOpen(permitToOpen); setPermitToOpen(null) } }, [permitToOpen, setPermitToOpen])
  // la clé d'ouverture (radar `permis` vs filtre `promesses`) fixe le MODE d'entrée + la fenêtre par
  // défaut ; ensuite le toggle local est maître (un deep-link vers l'autre clé re-cale l'écran).
  useEffect(() => { setPointMort(moduleKey === 'promesses'); setMonths(moduleKey === 'promesses' ? 36 : 24) }, [moduleKey])

  const MONTHS_RADAR = [12, 24, 48, 72]
  const MONTHS_PM = [24, 36, 48, 60]   // point mort : 36 = caducité légale du PC (défaut à l'ouverture)
  const togglePm = (on: boolean) => { setPointMort(on); setMonths(on ? 36 : 24) }

  // deux sources, une seule active à la fois (enabled) : RADAR = tous les permis ; POINT MORT = PC
  // anciens sans achèvement (l'endpoint /promesses renvoie désormais aussi la géom → des points).
  const qRadar = useInfiniteQuery({
    queryKey: ['m03', months, nature, commune],
    queryFn: ({ pageParam }) => modPermis(months, nature || null, 300, pageParam as number),
    initialPageParam: 0,
    getNextPageParam: (last, pages) => (last as Record<string, any>)['has_more'] ? pages.length * 300 : undefined,
    enabled: !pointMort,
  })
  const PM_PAGE = 1000  // 1re page légère → affichage rapide ; le reste en « voir plus »
  const qPm = useInfiniteQuery({
    queryKey: ['m04', months, commune],
    queryFn: ({ pageParam }) => modPromesses(months, PM_PAGE, pageParam as number),
    initialPageParam: 0,
    getNextPageParam: (last, pages) => (last as Record<string, any>)['has_more'] ? pages.length * PM_PAGE : undefined,
    enabled: pointMort,
  })
  // total point mort (COUNT ~4 s) DÉCOUPLÉ : arrive en parallèle, ne bloque pas la 1re page
  const qPmCount = useQuery({ queryKey: ['m04-count', months, commune], queryFn: () => modPromessesCount(months), staleTime: 60_000, enabled: pointMort })

  const q = pointMort ? qPm : qRadar
  const pages = (q.data?.pages ?? []) as Record<string, any>[]
  const head = pages[0]  // radar : carte (tous géocodés) + compteurs viennent de la page 0
  const inZone = (i: Record<string, any>) => {
    if (!zone || !i['geom']) return true   // non géocodé → toujours listé
    return pointInPolygon((i['geom'] as { coordinates: [number, number] }).coordinates, zone)
  }
  // liste = items paginés accumulés (« voir plus ») ; la ZONE dessinée filtre les géocodés
  const items = pages.flatMap((p) => (p['items'] ?? []) as Record<string, any>[]).filter(inZone)
  // CARTE = points cliquables. Radar : TOUS les géocodés (page 0, plafond 8 000). Point mort : les items
  // géocodés EUX-MÊMES (chaque PC au point mort est un point, exactement comme le radar).
  const carte = (pointMort
    ? items.filter((i) => i['geom'])
    : ((head?.['carte'] ?? []) as Record<string, any>[])
  ).filter((i) => !zone || pointInPolygon((i['geom'] as { coordinates: [number, number] }).coordinates, zone))
  useModuleMap([],
    featureCollection(carte.map((i) => ({ type: 'Feature', geometry: i['geom'], properties: { kind: 'permis', permit_id: i['permit_id'], label: `${i['type']} ${i['date']}` } }))),
    [pointMort, qRadar.dataUpdatedAt, qPm.dataUpdatedAt, zone])
  const total = pointMort ? qPmCount.data?.total : ((head?.['total'] as number) ?? 0)
  const sansLoc = pointMort ? 0 : ((head?.['sans_localisation'] as number) ?? 0)
  const loaded = pages.flatMap((p) => (p['items'] ?? []) as unknown[]).length

  return (
    <>
      {pointMort
        ? <Banner>PC accordé, <b>aucune déclaration d'achèvement</b>, parcelle toujours non bâtie au
            scoring — « réalisation à vérifier » sur place. Chaque permis est un <b>point cliquable</b> (sa
            fiche : porteur, lots, délai). Codes d'état de la source non documentés (affichés bruts).</Banner>
        : <Banner>Géocodage {String(head?.['pct_geocode'] ?? '…')} % — les non-géocodés restent listés.
            Données jusqu'au <b>{String(head?.['donnees_jusqu_au'] ?? '…')}</b> (flux Sitadel régional).
            Cliquez un permis (carte ou liste) pour sa fiche (porteur, lots, surfaces, délai d'instruction).</Banner>}
      {/* recherche par rue / commune : MÊME autocomplétion BAN que « Étudier un bien » (chemin unique).
          La sélection fait voler la carte sur le lieu — les permis géocodés y apparaissent (cliquables). */}
      <AddressAutocomplete placeholder="Aller à une rue, une commune…"
        onSelect={(sel) => setFlyTo({ center: [sel.lon, sel.lat], zoom: 15 })} />
      {/* saisie DIRECTE d'un numéro de permis → sa fiche, via le MÊME PermitDrawer (aucune 2ᵉ fiche). */}
      <form onSubmit={(e) => { e.preventDefault(); const v = permSearch.trim(); if (v) setOpen(v) }}
        className="flex items-center gap-1.5">
        <input data-permis-num data-promesses-num value={permSearch} onChange={(e) => setPermSearch(e.target.value.trim())}
          placeholder="Numéro de permis (ex. PC97…) → sa fiche"
          className="min-w-0 flex-1 rounded-lg border border-line-2 bg-surface-3 px-2 py-1.5 font-mono text-[11px] text-txt focus:border-mint focus:outline-none" />
        <button type="submit" disabled={!permSearch.trim()}
          className="shrink-0 rounded-lg border border-mint/50 bg-mint/15 px-2.5 py-1.5 text-[11px] font-medium text-mint transition-colors duration-quick hover:bg-mint/25 disabled:opacity-40">
          Voir →</button>
      </form>
      {/* FILTRE « Au point mort » — le cœur de la fusion : bascule radar ↔ PC anciens sans achèvement. */}
      <div className="flex flex-wrap items-center gap-2">
        <button data-permis-pointmort={pointMort ? '1' : '0'} onClick={() => togglePm(!pointMort)}
          className={`rounded-full border px-3 py-1 text-[11px] font-medium transition-colors duration-quick ${pointMort ? 'border-amber-500/60 bg-amber-500/15 text-amber-500' : 'border-line-2 text-txt-mut hover:border-mint/50'}`}>
          ⏸ Au point mort {pointMort ? '✓' : ''}
        </button>
        <span className="text-[10.5px] text-txt-dim">{pointMort ? 'PC anciens jamais réalisés' : 'filtrer les PC jamais réalisés'}</span>
      </div>
      {/* fenêtre : radar 12/24/48/72 ; point mort 24/36/48/60 (la caducité). Nature : radar seul. */}
      <div className="flex flex-wrap gap-1.5">
        {(pointMort ? MONTHS_PM : MONTHS_RADAR).map((m) => (
          <button key={m} onClick={() => setMonths(m)}
            className={`rounded-full border px-2.5 py-1 text-[11px] ${months === m ? 'border-mint text-mint' : 'border-line-2 text-txt-mut'}`}>
            {m} mois{pointMort ? '+' : ''}
          </button>
        ))}
        {!pointMort && (
          <>
            <span className="mx-1 self-center text-line-2">|</span>
            {NATURES.map(([v, l]) => (
              <button key={v} onClick={() => setNature(v)}
                className={`rounded-full border px-2.5 py-1 text-[11px] ${nature === v ? 'border-mint text-mint' : 'border-line-2 text-txt-mut'}`}>
                {l}
              </button>
            ))}
          </>
        )}
      </div>
      {pointMort && qPm.isLoading && <div className="flex flex-1 items-center justify-center py-8"><Loading accent="mint" label="Analyse en cours…" big /></div>}
      <p className="text-[11px] text-txt-dim">
        {pointMort
          ? <>{total != null ? fmt(total) : '…'} permis au point mort · {fmt(carte.length)} sur la carte{total != null && loaded < total ? ` · ${fmt(loaded)} chargés` : ''}</>
          : <>{zone ? `${items.length} permis dans la zone dessinée` : `${fmt(total ?? 0)} permis`} · {fmt(carte.length)} sur la carte
              {/* radar (audit) — carte plafonnée à 8 000 points (perf) ; on le DIT, jamais un plafond muet. */}
              {carte.length < ((head?.['geocodes'] as number) ?? 0) && <span data-permis-carte-plafond className="text-mint/70"
                title="Carte plafonnée à 8 000 points (performance) ; la liste, elle, n'est pas plafonnée (« voir plus »)."> sur {fmt(head?.['geocodes'] as number)} géocodés — carte plafonnée</span>}
              {!zone && sansLoc > 0 && <span data-permis-sansloc className="text-mint/70"
                title="Permis dont l'adresse n'a pas pu être rattachée à une parcelle du cadastre — non localisables sur la carte."> · {fmt(sansLoc)} sans localisation précise</span>}
              {zone && <span className="text-mint/70"> · outil Zone actif</span>}</>}
      </p>
      <div className="flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto">
        {items.map((i, k) => (
          <button key={k} data-permis-row data-geocode={i['geom'] ? '1' : '0'} onClick={() => setOpen(i['permit_id'] as string)}
            className={`flex items-center gap-2 rounded-lg border border-line-2 px-3 py-1.5 text-left text-[11px] transition-colors duration-quick hover:border-mint/50 ${i['geom'] ? 'bg-surface-3' : 'bg-surface-1'}`}>
            <span className="font-mono text-txt">{i['type'] as string}</span>
            <span className="text-txt-mut">{i['date'] as string}</span>
            {pointMort ? (
              <>
                {i['surface_m2'] != null && <span className="text-txt-dim">{fmt(i['surface_m2'] as number)} m²</span>}
                <span className="text-txt-dim">état {String(i['etat'])}</span>
                <span className="ml-auto flex items-center gap-1.5">
                  {!i['geom'] && <span className="text-mint/70" title="Non rattaché à une parcelle du cadastre — non localisable sur la carte.">non géocodé</span>}
                  <TierBadge tier={i['tier_v2'] as string | null} etage0={i['etage0'] as boolean | null} statut={i['statut'] as string | null} />
                </span>
              </>
            ) : (
              <>
                {i['delai_mois'] != null && <span style={{ color: VIOLET }}>{String(i['delai_mois'])} m</span>}
                {i['nb_lgt'] != null && <span className="text-txt-dim">{String(i['nb_lgt'])} lgt</span>}
                {!i['geom'] && <span className="ml-auto text-[11px] text-mint/70"
                  title="Permis dont l'adresse n'a pas pu être rattachée à une parcelle du cadastre — non localisable sur la carte.">non géocodé</span>}
              </>
            )}
          </button>
        ))}
        <MoreButton q={q} loaded={loaded} total={total ?? undefined} />
      </div>
      {open && <PermitDrawer permitId={open} onClose={() => setOpen(null)} />}
    </>
  )
}

/* ── M04 — PERMIS AU POINT MORT : FUSIONNÉ dans l'outil « Permis » (M03 ci-dessus) le 23/08/2026 (§3).
   Devenu un FILTRE (« Au point mort ») du radar, rendu en points cliquables. Le composant M04 autonome
   est supprimé ; la clé `promesses` résout désormais M03 (filtre pré-actif). Endpoint /promesses vivant. */

/* ───────────────────────────── M05 — VÉLOCITÉ ADMIN ───────────────────────────── */
// M137-Z — ABSORBÉ dans l'outil « Communes » (fiche commune → tranche p25–p75). Plus câblé au menu ;
// composant conservé au dépôt (exporté pour rester compilable). Note : le backend ne sert plus
// `rang_delai` (classement par médiane retiré — délais homogènes) ; ce composant dormant dégrade sans.
export function M05() {
  const [nature, setNature] = useState('PC')
  const q = useQuery({ queryKey: ['m05', nature], queryFn: () => modVelocite(nature || null) })
  const d = q.data as Record<string, any> | undefined
  const [sort, setSort] = useState<'n_valide' | 'delai_median_mois'>('delai_median_mois')
  const rows = useMemo(() => ([...((d?.['communes'] ?? []) as Record<string, any>[])])
    .sort((a, b) => Number(b[sort] ?? 0) - Number(a[sort] ?? 0)), [d, sort])
  const natLabel = { PC: 'PC', DP: 'DP', PA: 'PA', PD: 'PD', '': 'toutes natures' }[nature]
  return (
    <>
      <Banner><b>{d?.['indicateur'] ?? 'Délai médian d\'instruction dépôt → autorisation'}</b> ({natLabel},
        cohortes {String(d?.['cohortes'] ?? '…')}). {d?.['note']}
        <div className="mt-1 text-mint/70">▲ {d?.['censure']}</div>
        <div className="mt-1 italic">{d?.['disclaimer']}</div>
      </Banner>
      <div className="flex flex-wrap gap-1.5">
        {NATURES.filter(([v]) => v).map(([v, l]) => (
          <button key={v} onClick={() => setNature(v)}
            className={`rounded-full border px-2.5 py-1 text-[11px] ${nature === v ? 'border-mint text-mint' : 'border-line-2 text-txt-mut'}`}>
            {l}
          </button>
        ))}
        <a href={`/modules/velocite?fmt=csv${nature ? `&nature=${nature}` : ''}`}
          className="ml-auto self-center rounded-lg border border-line-2 px-2.5 py-1 text-[11px] text-txt hover:text-txt-hi">⬇ CSV</a>
      </div>
      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
        <div className="sticky top-0 grid grid-cols-[1fr_64px_60px] gap-1 bg-surface-1 py-1 text-[11px] tracking-wide text-txt-dim">
          <span>COMMUNE (ÎLE)</span>
          {([['delai_median_mois', 'MÉDIANE'], ['n_valide', 'N']] as const).map(([k, l]) => (
            <button key={k} onClick={() => setSort(k)} className={`text-right transition-colors duration-quick ${sort === k ? 'text-mint' : ''}`}>{l} ↓</button>
          ))}
        </div>
        {rows.map((c) => {
          const rang = c['rang_delai'] as number | null
          // rapides (rang bas) en mint, lentes (rang haut) en rouge — repère visuel
          const rgColor = rang == null ? TOKENS.txtDim : rang <= 5 ? TOKENS.mint : rang >= 20 ? TOKENS.stEcartee : VIOLET
          const tend = c['tendance'] as string | null
          const tIcon = tend === 'accelere' ? '↓' : tend === 'ralentit' ? '↑' : tend === 'stable' ? '→' : ''
          const tColor = tend === 'accelere' ? TOKENS.mint : tend === 'ralentit' ? TOKENS.stEcartee : TOKENS.txtDim
          return (
            <div key={c['commune'] as string} className="grid grid-cols-[1fr_64px_60px] gap-1 border-b border-line py-1.5 text-[11px]"
              title={`${c['commune']} : rang ${rang ?? '—'}/24 par vélocité · délai médian ${natLabel} = ${c['delai_median_mois']} mois (IQR ${c['delai_p25_mois']}–${c['delai_p75_mois']}), sur ${c['n_mur']} dossiers mûrs. Tendance : ${tend ?? 'indéterminée (cohortes insuffisantes)'}.`}>
              <span className="flex min-w-0 items-center gap-1.5 truncate text-txt">
                {rang != null && <span className="shrink-0 font-mono text-[9px]" style={{ color: rgColor }}>#{rang}</span>}
                <span className="truncate">{c['commune'] as string}</span>
                {tIcon && <span className="shrink-0" style={{ color: tColor }} title={`Tendance ${tend}`}>{tIcon}</span>}
              </span>
              <span className="text-right font-mono" style={{ color: rgColor }}>{c['delai_median_mois'] == null ? '—' : `${c['delai_median_mois']} m`}</span>
              <span className="text-right font-mono text-txt-mut">{fmt(c['n_mur'] as number)}</span>
            </div>
          )
        })}
        <p className="py-2 text-[11px] text-txt-dim">
          Médiane dépôt→autorisation en mois · N = dossiers mûrs (dépôts &lt; {String(d?.['maturite_cutoff'] ?? '…')}).
          Survolez une ligne pour l'IQR et les exclusions.</p>
      </div>
    </>
  )
}

/* ───────────────────────────── M06 — MODE BAILLEUR ───────────────────────────── */
// M137-N (Vic 20/08/2026) — RETIRÉ du produit le 20/08/2026 (DORMANT). Plus câblé au menu (registry +
// COMPONENTS). Composant conservé au dépôt (exporté pour rester compilable) ; endpoint /modules/bailleur
// + tests conservés.
export function M06() {
  // M15-G : périmètre choisi DANS l'outil (état local), plus d'héritage du filtre commune global.
  const [commune, setCommune] = useState<string | null>(null)
  const q = useQuery({ queryKey: ['m06', commune], queryFn: () => modBailleur(commune) })
  const d = q.data as Record<string, any> | undefined
  const items = ((d?.['items'] ?? []) as Record<string, any>[])
  useModuleMap(items.map((i) => i['idu'] as string), null, [q.dataUpdatedAt])
  return (
    <>
      <Banner>{String(d?.['lecture_lls'] ?? '…')}</Banner>
      <CommuneScope commune={commune} onChange={setCommune} />
      {q.isLoading && <div className="flex flex-1 items-center justify-center py-8"><Loading accent="mint" label="Analyse en cours…" big /></div>}
      {/* Point 33 : contexte SRU (déficit logement social) — commune carencée = forte demande LLS */}
      {(d?.['sru'] as Record<string, any> | undefined) && (
        <div data-bailleur-sru className={`rounded-lg border px-3 py-2 text-[11px] ${d!['sru']['statut'] === 'carencee' ? 'border-st-creuser/50 bg-st-creuser/10' : 'border-line-2 bg-surface-2'}`}>
          <div className="flex items-center gap-2">
            <span className={`font-medium ${d!['sru']['statut'] === 'carencee' ? 'text-st-creuser' : 'text-txt'}`}>
              SRU {String(d!['sru']['statut'])}
            </span>
            <span className="text-txt-dim">· LLS {d!['sru']['taux_lls']}% / objectif {d!['sru']['objectif_pct']}%</span>
          </div>
          {d!['sru']['deficit_logements'] != null && (
            <div className="mt-1 text-txt-mut">Besoin estimé : <b className="tnum text-st-creuser">{fmt(d!['sru']['deficit_logements'] as number)}</b> logements sociaux pour atteindre l'objectif</div>
          )}
        </div>
      )}
      <p className="text-[11px] text-txt-dim">{fmt(d?.['total'] as never)} parcelles promues en QPV{(d?.['affiches'] as number) < (d?.['total'] as number) ? ` · ${fmt(d?.['affiches'] as never)} affichées` : ''}{d?.['n_communes_carencees'] ? ` · ${fmt(d['n_communes_carencees'] as number)} en communes carencées SRU` : ''}</p>
      <div className="flex min-h-0 flex-1 flex-col gap-1.5 overflow-y-auto">
        {items.map((i) => (
          <Row key={i['idu'] as string} idu={i['idu'] as string}
            sub={`${fmt(i['surface_m2'] as number)} m² · SDP ${fmt(i['sdp'] as number)} m²${i['carencee'] ? ' · SRU carencée' : ''}`}
            right={<TierBadge tier={i['tier_v2'] as string | null} etage0={i['etage0'] as boolean | null} statut={i['statut'] as string | null} />}
            fiche={[['Mode bailleur', 'Parcelle en QPV'], ['SRU commune', i['carencee'] ? 'Carencée — forte demande LLS' : '—'],
              ['Leviers LLS', 'TVA 2,1 % · abattement TFPB 30 %'], ['SDP résiduelle', `${fmt(i['sdp'] as number)} m²`]]} />
        ))}
      </div>
    </>
  )
}

/* ───────────────────────────── M07 — FONCIER FANTÔME ───────────────────────────── */
// M137-N (Vic 20/08/2026) — RETIRÉ du produit le 20/08/2026 (DORMANT) : nom non fidèle au contenu
// (74 % successions et structures collectives, pas des sociétés fantômes), levier « dirigeant inactif »
// à 0. Le signal succession sera repris en facette. Plus câblé au menu ; composant conservé au dépôt
// (exporté pour rester compilable) ; endpoint /modules/fantome + tests conservés.
export function M07() {
  // M15-G : périmètre choisi DANS l'outil (état local), plus d'héritage du filtre commune global.
  const [commune, setCommune] = useState<string | null>(null)
  const q = useInfiniteQuery({
    queryKey: ['m07', commune],
    queryFn: ({ pageParam }) => modFantome(300, pageParam as number, commune),
    initialPageParam: 0,
    getNextPageParam: (last, pages) => (last as Record<string, any>)['has_more'] ? pages.length * 300 : undefined,
  })
  const pages = (q.data?.pages ?? []) as Record<string, any>[]
  const items = pages.flatMap((p) => (p['items'] ?? []) as Record<string, any>[])
  const total = (pages[0]?.['total'] as number) ?? 0
  useModuleMap(items.map((i) => i['idu'] as string), null, [q.dataUpdatedAt])
  return (
    <>
      {/* M15 E3 (RG2) : expliquer « fantôme » + le score, sans jargon (Q, RNE). */}
      <Banner>Du foncier <b className="text-txt">constructible mais « fantôme »</b> : le terrain a du
        potentiel, mais son propriétaire est <b>difficile à joindre</b> — société introuvable au
        registre des entreprises, ou dirigeant inactif. C'est le constructible que les autres ne
        voient pas. Le <b className="text-mint">nombre vert</b> = le <b>potentiel constructible
        de la parcelle</b> (0-100). Un levier d'approche est indiqué par cas — vérification notariale
        indispensable.</Banner>
      {/* M15-G : périmètre explicite (RG1, plus hérité du filtre global) */}
      <CommuneScope commune={commune} onChange={setCommune} />
      {/* M15-B : compteur piloté par la pagination (« voir plus ») */}
      <p className="text-[11px] text-txt-dim">{fmt(total)} parcelles gelées{items.length < total ? ` · ${fmt(items.length)} affichées` : ''}</p>
      <div className="flex min-h-0 flex-1 flex-col gap-1.5 overflow-y-auto">
        {items.map((i) => (
          <Row key={i['idu'] as string} idu={i['idu'] as string}
            sub={`${(i['denomination'] as string) ?? ''} · ${i['verrou']}`}
            right={undefined}
            fiche={[['▲ Gelé', String(i['verrou'])], ['Levier', String(i['levier'])],
              ['Propriétaire', `${i['denomination']} (${i['siren']})`]]} />
        ))}
        <MoreButton q={q} loaded={items.length} total={total} />
      </div>
    </>
  )
}

/* ───────────────────────────── M08 — REMONTER LE TEMPS ───────────────────────────── */

// M82 (refonte) — la PARCELLE d'abord : IDU / adresse / clic carte (motif parcelPrefill de M-ENTREE),
// PUIS l'année ancienne (UN seul choix) ; l'« après » est TOUJOURS aujourd'hui (verrouillé). L'accès
// depuis la fiche (bouton « 1950 » → parcelPrefill) reste. Les millésimes ANCIENS réellement dispo.
const TEMPS_AVANT = [{ key: 'bm-ortho-1950', label: '1950-1965' }, { key: 'bm-ortho-2000', label: '2000-2005' }]

function M08() {
  const { cmpLeft, setCmpLeft, setCmpRight, setModule, parcelPrefill, setParcelPrefill, setFlyTo } = useApp()
  const [idu, setIdu] = useState('')
  // « après » = TOUJOURS aujourd'hui (verrouillé) ; « avant » démarre sur 1950 si non-historique.
  useEffect(() => {
    setCmpRight('bm-ortho-now')
    if (cmpLeft !== 'bm-ortho-1950' && cmpLeft !== 'bm-ortho-2000') setCmpLeft('bm-ortho-1950')
  }, [])   // eslint-disable-line react-hooks/exhaustive-deps
  const designer = async (code: string, coords?: [number, number]) => {
    const c = code.trim(); if (c.length < 10) return
    setIdu(c)
    if (coords) { setFlyTo({ center: coords, zoom: 18 }); return }
    try { const f = await getFiche(c); if (f.coords) setFlyTo({ center: f.coords, zoom: 18 }) } catch { /* parcelle recentrée au mieux */ }
  }
  // parcelPrefill (fiche « 1950 », clic carte via parcelAt, Copilote) → désigne la parcelle.
  useEffect(() => {
    if (parcelPrefill) { void designer(parcelPrefill); setParcelPrefill(null) }
  }, [parcelPrefill])   // eslint-disable-line react-hooks/exhaustive-deps

  // ── ÉTAPE 1 — désigner la parcelle ──
  if (!idu) return (
    <>
      <Banner>La <b>parcelle d'abord</b> : son IDU, une adresse, ou <b>cliquez-la sur la carte</b>. Puis
        choisissez l'année à revoir — l'« après » est toujours aujourd'hui.</Banner>
      <div className="flex flex-col gap-2 rounded-lg border border-line-2 bg-surface-2 p-3">
        <p className="label-caps text-[9.5px]">Quelle parcelle voir évoluer ?</p>
        {/* PATRON OMNIBOX (M137) — adresse OU IDU dans le même champ, via ParcelInput partagé */}
        <ParcelInput dataAttr="temps-idu" placeholder="Adresse ou IDU — 97415000CW0658"
          onPick={(id) => void designer(id)} />
      </div>
      <p className="text-[11px] text-txt-mut">Accès direct depuis toute fiche : bouton « 1950 ».</p>
    </>
  )

  // ── ÉTAPE 2 — année ancienne (un seul choix) ; après = aujourd'hui, verrouillé ──
  return (
    <>
      <div className="flex items-center gap-2 rounded-lg border border-line-2 bg-surface-2 px-3 py-2">
        <span className="font-mono text-[12px] text-txt">{idu}</span>
        <button onClick={() => setIdu('')} className="ml-auto text-[10.5px] text-mint hover:underline">changer</button>
      </div>
      <div className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2.5">
        <p className="label-caps text-[9.5px]">L'année à revoir (avant)</p>
        <div className="mt-1.5 flex gap-1.5">
          {TEMPS_AVANT.map((a) => (
            <button key={a.key} data-cmp-left={a.key} onClick={() => setCmpLeft(a.key)}
              className={`flex-1 rounded-md border px-2 py-1.5 text-[11px] ${cmpLeft === a.key ? 'border-mint bg-mint/10 text-mint' : 'border-line-2 text-txt-mut hover:text-txt'}`}>{a.label}</button>
          ))}
        </div>
        <div className="mt-2 flex items-center justify-between rounded-md border border-dashed border-line-2 px-2.5 py-1.5">
          <span className="text-[11px] text-txt-dim">Après</span>
          <span className="text-[11px] text-txt">Aujourd'hui (ortho actuelle)</span>
          <span className="text-[9px] text-txt-dim">🔒 fixe</span>
        </div>
        <p className="mt-2 text-[10.5px] text-txt-dim">Glissez la poignée au centre de la carte pour révéler l'un ou l'autre.</p>
        <button onClick={() => setModule(null)}
          className="mt-2 w-full rounded-md border border-line-2 px-2 py-1 text-[11px] text-txt-mut transition-colors duration-quick hover:border-mint hover:text-txt">✕ Quitter</button>
      </div>
    </>
  )
}

/* ───────────────────────────── M09 — COURRIERS ───────────────────────────── */

// M09 — parcours GUIDÉ en 4 étapes (parcelle → motif → rédaction → demande). C'est une DEMANDE
// d'envoi (l'équipe LABUSE la traite), pas un envoi auto. Le brouillon est GROUNDÉ (faits réels de
// la parcelle, gabarit serveur) et ÉDITABLE. Privacy : adressage générique, aucun particulier nommé.
// COURRIER-SERVICE (refonte 13 outils) — modèles à VARIABLES ({parcelle} {commune} {surface}
// remplacées PAR courrier, un courrier par destinataire). Adressage générique conservé (SPF/CERFA
// côté LABUSE), aucune identité de propriétaire particulier.
const TEMPLATES: { key: string; label: string; corps: string }[] = [
  { key: 'standard', label: 'Approche standard',
    corps: 'Objet : votre parcelle {parcelle}, à {commune}\n\nMadame, Monsieur,\n\n'
      + 'Votre parcelle cadastrée {parcelle} ({surface}), située à {commune}, présente à notre analyse '
      + 'un réel potentiel. Nous accompagnons des porteurs de projets locaux et serions heureux '
      + "d'échanger avec vous, sans aucun engagement, sur les possibilités qu'offre votre bien — y "
      + "compris si vous n'envisagez pas de vendre à court terme.\n\nNous restons à votre disposition."
      + '\n\nCordialement,' },
  { key: 'dormance', label: 'Dormance / succession',
    corps: 'Objet : votre parcelle {parcelle}, à {commune}\n\nMadame, Monsieur,\n\n'
      + "Votre parcelle {parcelle} ({surface}) à {commune} paraît aujourd'hui peu mobilisée. Si elle "
      + "relève d'une succession ou d'une indivision, sa valorisation peut soulever des questions ; "
      + 'nous accompagnons ce type de situation, sans engagement de votre part, et serions heureux '
      + "d'en parler avec vous.\n\nBien cordialement," },
  { key: 'voisin', label: 'Voisin direct',
    corps: 'Objet : votre parcelle {parcelle}, à {commune}\n\nMadame, Monsieur,\n\n'
      + 'Nous étudions un projet à proximité immédiate de votre parcelle {parcelle} ({surface}) à '
      + "{commune}. Votre bien s'y intégrerait naturellement ; nous serions heureux d'échanger avec "
      + 'vous, sans aucun engagement, sur les possibilités.\n\nCordialement,' },
  { key: 'libre', label: 'Libre', corps: '' },
]
type Dest = { idu: string; commune: string; surface: number | null }
// statuts visibles côté client (mandat) — l'ordre EST la timeline.
const COURRIER_STATUTS: [string, string][] = [['demande', 'Demandé'], ['tarif_confirme', 'Tarif confirmé'], ['envoye', 'Envoyé']]

/** COURRIER-SERVICE (refonte 13 outils) — l'outil devient un SERVICE : le client prépare
 *  (① destinataires ② rédaction), puis ③ DEMANDE l'envoi à LABUSE. Trois étapes, variables par
 *  courrier, statut visible (Demandé → Tarif confirmé → Envoyé). PDF relégué en aperçu de relecture.
 *  Exporté pour test (le flux service est le cœur du mandat COURRIER). */
export function M09() {
  const qc = useQueryClient()
  const selectedIdu = useApp((s) => s.selectedIdu)
  const msel = useApp((s) => s.msel)
  const courrierPrefill = useApp((s) => s.courrierPrefill)
  const setCourrierPrefill = useApp((s) => s.setCourrierPrefill)
  const courrierPrefillIdus = useApp((s) => s.courrierPrefillIdus)
  const setCourrierPrefillIdus = useApp((s) => s.setCourrierPrefillIdus)

  const [step, setStep] = useState<1 | 2 | 3>(1)
  const [dest, setDest] = useState<Dest[]>([])
  const [modele, setModele] = useState('standard')
  const [corps, setCorps] = useState(TEMPLATES[0].corps)
  const [demande, setDemande] = useState<{ id: number; statut: string; n: number; communes: string | null } | null>(null)
  const [pdfBusy, setPdfBusy] = useState(false)
  const [pdfErr, setPdfErr] = useState<string | null>(null)

  // Ajoute un destinataire (dédupliqué), puis enrichit commune + surface depuis la fiche (cache partagé).
  const ajouter = (raw: string) => {
    const id = iduComplet(raw).toUpperCase()
    if (id.length < 10) return
    setDest((prev) => prev.some((d) => d.idu === id) ? prev : [...prev, { idu: id, commune: '', surface: null }])
    qc.fetchQuery({ queryKey: ['fiche', id], queryFn: () => getFiche(id) })
      .then((f) => setDest((prev) => prev.map((d) => d.idu === id ? { ...d, commune: f.commune, surface: f.surface_m2 } : d)))
      .catch(() => { /* parcelle introuvable : la chip reste, commune inconnue (jamais inventée) */ })
  }
  const retirer = (id: string) => setDest((prev) => prev.filter((d) => d.idu !== id))

  // Import EN UN GESTE au montage : Assemblage (courrierPrefillIdus) > tuile fiche mono > parcelle sélectionnée.
  useEffect(() => {
    const seed = courrierPrefillIdus?.length ? courrierPrefillIdus
      : courrierPrefill ? [courrierPrefill] : selectedIdu ? [selectedIdu] : []
    if (courrierPrefillIdus) setCourrierPrefillIdus(null)
    if (courrierPrefill) setCourrierPrefill(null)
    seed.forEach(ajouter)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const choisirModele = (k: string) => {
    setModele(k)
    setCorps(TEMPLATES.find((t) => t.key === k)?.corps ?? '')
  }
  // substitution des variables (split/join = pas de dépendance à String.replaceAll / target ≥ es2021).
  const rep = (s: string, a: string, b: string) => s.split(a).join(b)
  const remplir = (tpl: string, d: Dest) => rep(rep(rep(tpl,
    '{parcelle}', iduCourt(d.idu)),
    '{commune}', d.commune || '—'),
    '{surface}', d.surface != null ? `${fmtInt(d.surface)} m²` : '—')
  const recapCommunes = () => {
    const c: Record<string, number> = {}
    dest.forEach((d) => { const k = d.commune || '—'; c[k] = (c[k] || 0) + 1 })
    return Object.entries(c).map(([k, n]) => `${k} ×${n}`).join(' · ')
  }

  const demandes = useQuery({ queryKey: ['courrier-demandes'], queryFn: getCourrierDemandes, enabled: step === 3 })
  const envoyer = useMutation({
    mutationFn: () => postCourrierDemande(dest.map((d) => d.idu), corps, modele, recapCommunes()),
    onSuccess: (d) => { setDemande(d); qc.invalidateQueries({ queryKey: ['courrier-demandes'] }) },
  })
  const apercuPdf = async () => {
    const first = dest[0]; if (!first) return
    setPdfBusy(true); setPdfErr(null)
    try { await courrierPdf(first.idu, modele, remplir(corps, first)) }
    catch { setPdfErr('Le téléchargement du PDF a échoué. Réessayez.') }
    finally { setPdfBusy(false) }
  }

  const STEPS: [1 | 2 | 3, string][] = [[1, 'Destinataires'], [2, 'Rédaction'], [3, 'Envoi']]
  const statutRang = (s: string) => COURRIER_STATUTS.findIndex(([k]) => k === s)

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
      <Banner>Un <b>service d'envoi</b> : vous préparez vos courriers (destinataires + rédaction), LABUSE
        <b> les imprime, les affranchit et les poste</b>. Adressage générique (SPF/CERFA) — aucune identité
        de propriétaire particulier.</Banner>
      {/* stepper 3 étapes */}
      <div className="flex items-center gap-1 text-[10px]">
        {STEPS.map(([n, l], i) => (
          <div key={n} className={`flex items-center gap-1 ${step >= n ? 'text-mint' : 'text-txt-dim'}`}>
            <span className={`flex h-4 w-4 items-center justify-center rounded-full border text-[9px] ${step >= n ? 'border-mint' : 'border-line-2'}`}>{step > n ? '✓' : n}</span>
            {n} · {l}{i < 2 && <span className="text-txt-dim">›</span>}
          </div>
        ))}
      </div>

      {step === 1 && (
        <div className="flex min-h-0 flex-1 flex-col gap-2">
          <p className="text-[11px] text-txt-mut">Les parcelles à démarcher — <b>une barre</b> (adresse ou IDU), autant que voulu :</p>
          <ParcelInput dataAttr="courrier-idu" withCarte={false} placeholder="Adresse ou IDU — puis Entrée"
            onPick={ajouter} />
          {msel.length > 0 && (
            <button data-courrier-import onClick={() => msel.forEach(ajouter)}
              className="self-start text-[11px] font-medium text-mint hover:underline">+ Importer depuis Assemblage ({msel.length})</button>
          )}
          {dest.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {dest.map((d) => (
                <span key={d.idu} data-courrier-dest className="flex items-center gap-1.5 rounded-lg border border-mint/50 bg-surface-2 px-2 py-1 text-[11px]">
                  <span className="font-mono text-txt">{iduCourt(d.idu)}</span>
                  {d.commune && <span className="text-txt-dim">{d.commune}</span>}
                  <button onClick={() => retirer(d.idu)} className="text-txt-dim hover:text-st-ecartee" aria-label="Retirer">✕</button>
                </span>
              ))}
            </div>
          )}
          <p className="text-[10px] text-txt-dim">{dest.length} destinataire{dest.length > 1 ? 's' : ''} — un courrier par parcelle.</p>
          <button data-courrier-next onClick={() => dest.length && setStep(2)} disabled={dest.length === 0}
            className="mt-auto rounded-lg bg-mint py-1.5 text-xs font-medium text-bg transition-[filter] duration-quick hover:brightness-110 disabled:opacity-40">Rédiger ›</button>
        </div>
      )}

      {step === 2 && (
        <div className="flex min-h-0 flex-1 flex-col gap-2">
          <div className="flex flex-wrap gap-1">
            {TEMPLATES.map((t) => (
              <button key={t.key} data-courrier-modele={t.key} onClick={() => choisirModele(t.key)}
                className={`rounded-full border px-2.5 py-1 text-[11px] transition-colors duration-quick ${modele === t.key ? 'border-mint bg-mint/[0.12] text-mint' : 'border-line-2 text-txt-mut hover:text-txt'}`}>
                {t.label}
              </button>
            ))}
          </div>
          <textarea data-courrier-texte value={corps} onChange={(e) => setCorps(e.target.value)}
            placeholder="Votre courrier… (variables {parcelle} {commune} {surface})"
            className="min-h-[160px] flex-1 rounded-lg border border-line-2 bg-surface-3 px-2 py-1.5 text-[11px] leading-snug text-txt focus:border-mint focus:outline-none" />
          <p className="text-[9.5px] text-txt-dim"><b className="text-txt-mut">{'{parcelle} {commune} {surface}'}</b> — remplacés par courrier (un courrier généré par destinataire).</p>
          <div className="flex gap-2">
            <button onClick={() => setStep(1)} className="rounded-lg border border-line-2 px-3 py-1.5 text-[11px] text-txt-mut">‹ Retour</button>
            <button data-courrier-next onClick={() => setStep(3)} disabled={corps.trim().length < 10}
              className="flex-1 rounded-lg bg-mint py-1.5 text-xs font-medium text-bg transition-[filter] duration-quick hover:brightness-110 disabled:opacity-40">Vérifier l'envoi ›</button>
          </div>
        </div>
      )}

      {step === 3 && (
        <div className="flex min-h-0 flex-1 flex-col gap-2">
          {/* récap */}
          <div className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-[11px]">
            <div className="flex justify-between"><span className="text-txt-mut">Courriers</span><b className="tnum text-txt">{dest.length}</b></div>
            <div className="flex justify-between gap-2"><span className="text-txt-mut">Communes</span><span className="text-right text-txt">{recapCommunes() || '—'}</span></div>
            <div className="flex justify-between"><span className="text-txt-mut">Adressage</span><span className="text-txt-dim">générique (SPF/CERFA)</span></div>
          </div>

          {!demande ? (
            <button data-courrier-demander onClick={() => envoyer.mutate()} disabled={envoyer.isPending}
              className="rounded-lg bg-mint py-2 text-xs font-medium text-bg transition-[filter] duration-quick hover:brightness-110 disabled:opacity-40">
              {envoyer.isPending ? 'Envoi de la demande…' : "Demander l'envoi à LABUSE"}</button>
          ) : (
            <div data-courrier-confirm className="rounded-lg border border-mint/40 bg-mint/[0.07] px-3 py-2 text-[11px] leading-snug text-txt-mut">
              <b className="text-mint">✓ Demande transmise.</b> LABUSE vous rappelle sous 24 h ouvrées avec le tarif —
              impression, mise sous pli, affranchissement et suivi compris.
            </div>
          )}
          {envoyer.isError && <p className="text-[10.5px] text-st-ecartee">La demande n'a pas pu être transmise — réessayez.</p>}

          {/* timeline de statut */}
          {demande && (
            <div className="flex items-center gap-1 text-[10px]">
              {COURRIER_STATUTS.map(([k, l], i) => (
                <div key={k} className={`flex items-center gap-1 ${statutRang(demande.statut) >= i ? 'text-mint' : 'text-txt-dim'}`}>
                  <span>{statutRang(demande.statut) >= i ? '●' : '○'}</span>{l}{i < 2 && <span className="text-txt-dim">›</span>}
                </div>
              ))}
            </div>
          )}

          {/* aperçu PDF de RELECTURE (secondaire) — corps rempli pour le 1er destinataire */}
          <button data-courrier-pdf onClick={apercuPdf} disabled={pdfBusy || dest.length === 0}
            className="self-start text-[11px] text-txt-mut hover:text-mint disabled:opacity-40">
            {pdfBusy ? 'Génération…' : '⬇ Télécharger l’aperçu PDF (relecture)'}</button>
          {pdfErr && <p data-courrier-pdf-err className="text-[10.5px] text-st-ecartee">{pdfErr}</p>}

          {/* demandes récentes (leur statut suit ce que Vic passe) */}
          {(demandes.data?.demandes.length ?? 0) > 0 && (
            <div className="mt-1 flex flex-col gap-1">
              <p className="label-caps text-[9px]">Vos demandes</p>
              {demandes.data!.demandes.slice(0, 5).map((d) => (
                <div key={d.id} className="flex items-baseline justify-between gap-2 text-[10.5px]">
                  <span className="min-w-0 truncate text-txt-mut">{d.n} courrier{d.n > 1 ? 's' : ''}{d.communes ? ` · ${d.communes}` : ''}</span>
                  <span className="shrink-0 text-mint">{COURRIER_STATUTS.find(([k]) => k === d.statut)?.[1] ?? d.statut}</span>
                </div>
              ))}
            </div>
          )}

          <button onClick={() => setStep(1)} className="mt-auto self-start text-[11px] text-txt-mut hover:text-txt">‹ Retour aux destinataires</button>
        </div>
      )}
    </div>
  )
}

/* ───────────────────────────── M10 — DUE DILIGENCE ───────────────────────────── */

function M10() {
  const [refs, setRefs] = useState('')
  const [quick, setQuick] = useState('')
  const selectedIdu = useApp((s) => s.selectedIdu)
  // M15-G — les 3 entrées ALIMENTENT le lot (append dédupliqué), le collage en masse reste possible.
  const addRef = (v: string) => {
    const t = v.trim(); if (!t) return
    setRefs((r) => {
      const lines = r.split('\n').map((x) => x.trim()).filter(Boolean)
      return lines.includes(t) ? r : [...lines, t].join('\n') + '\n'
    })
  }
  const run = useMutation({ mutationFn: () => modDueDiligence(refs) })
  const items = (run.data?.items ?? []) as Record<string, any>[]
  return (
    <>
      <Banner>Un rapport par parcelle (PDF individuel réutilisant l'export fiche). Alimentez le lot par
        les <b>3 entrées</b> ci-dessous, ou collez directement une liste (IDU complet ou SECTION+NUMÉRO).</Banner>
      {/* M15-G — 3 entrées : IDU, adresse, clic carte → append au lot */}
      <div className="flex flex-col gap-1.5 rounded-lg border border-line-2 bg-surface-2 px-2.5 py-2">
        <div className="flex gap-1.5">
          <input data-diligence-quick value={quick} onChange={(e) => setQuick(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') { addRef(quick); setQuick('') } }}
            placeholder="IDU ou SECTION+NUMÉRO"
            className="min-w-0 flex-1 rounded border border-line-2 bg-surface-3 px-2 py-1 font-mono text-[10.5px] text-txt focus:border-mint focus:outline-none" />
          <button data-diligence-add onClick={() => { addRef(quick); setQuick('') }} disabled={!quick.trim()}
            className="shrink-0 rounded border border-mint/40 px-2 text-[11px] text-mint transition-colors duration-quick hover:bg-mint/10 disabled:opacity-40">+ ajouter</button>
        </div>
        <AddressAutocomplete placeholder="… ou une adresse"
          onSelect={(sel) => { if (sel.idu) addRef(sel.idu) }} />
        {selectedIdu && (
          <button data-diligence-addsel onClick={() => addRef(selectedIdu)}
            className="self-start text-[10.5px] text-mint hover:underline">+ ajouter la parcelle sélectionnée sur la carte ({selectedIdu.slice(8)})</button>
        )}
      </div>
      <textarea value={refs} onChange={(e) => setRefs(e.target.value)} rows={4}
        placeholder={'97415000AC0253\nAC0254\nBK 63…'}
        className="rounded-lg border border-line-2 bg-surface-3 px-2 py-1.5 font-mono text-[10.5px] text-txt focus:border-mint focus:outline-none" />
      <button onClick={() => refs.trim() && run.mutate()} disabled={!refs.trim() || run.isPending}
        className="rounded-lg bg-mint py-1.5 text-xs font-medium text-bg transition-[filter] duration-quick hover:brightness-110 disabled:opacity-40">
        {run.isPending ? 'Analyse…' : 'Analyser le lot'}
      </button>
      {run.data && (
        <>
          <p className="text-[11px] text-txt-dim">{run.data.n_trouvees}/{run.data.n_demandes} références trouvées</p>
          {/* M137-T — NON COUVERT reporté sur le LOT : un lot sans flag cascade ne doit jamais être un
              « RAS » muet. Le bloc dit ce que la base ne couvre pas, à l'échelle des 60 parcelles. */}
          {(run.data.non_couvert ?? []).length > 0 && (
            <div data-diligence-noncouvert className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2">
              <p className="label-caps text-[9.5px]">Non couvert par la base — à vérifier ailleurs (vaut pour tout le lot)</p>
              <div className="mt-1 space-y-0.5">
                {(run.data.non_couvert as string[]).map((n, i) => <p key={i} className="text-[10.5px] leading-snug text-txt-mut">○ {n}</p>)}
              </div>
            </div>
          )}
          <div className="flex min-h-0 flex-1 flex-col gap-1.5 overflow-y-auto">
            {items.map((i, k) => 'idu' in i ? (() => {
              const risque = i['risque'] as number
              const rColor = risque >= 100 ? TOKENS.stEcartee : risque >= 60 ? TOKENS.stEcartee : risque >= 30 ? TOKENS.stCreuser : TOKENS.mint
              const rLabel = risque >= 100 ? 'bloquant' : risque >= 60 ? 'élevé' : risque >= 30 ? 'modéré' : 'faible'
              const proprio = i['proprio'] as Record<string, any>
              const checklist = (i['checklist'] ?? []) as Record<string, any>[]
              return (
              <div key={k} data-diligence-item className="rounded-lg border border-line-2 bg-surface-3 px-3 py-2">
                <div className="flex items-center gap-2">
                  <Row idu={i['idu'] as string} sub={`${i['commune']} · ${fmt(i['surface_m2'] as number)} m²`}
                    right={<TierBadge tier={i['tier_v2'] as string | null} etage0={i['etage0'] as boolean | null} statut={i['statut'] as string | null} />} />
                </div>
                {/* Point 42 : score de risque consolidé (déterministe) */}
                <div className="mt-1.5 flex items-center gap-2 text-[11px]">
                  <span data-diligence-risque className="rounded-full px-2 py-0.5 font-medium" style={{ background: `${rColor}22`, color: rColor }}>risque {rLabel} · {risque}/100</span>
                  <span className="truncate text-txt-dim" title={proprio['type'] === 'personne_morale' ? `SIREN ${proprio['siren'] ?? '—'}` : 'propriétaire personne physique — non communiqué'}>
                    {proprio['type'] === 'personne_morale' ? proprio['denomination'] : 'propriétaire particulier'}
                  </span>
                </div>
                {/* checklist — points à vérifier avant achat (facteurs cascade existants) */}
                {checklist.length > 0 && (
                  <div className="mt-1.5 flex flex-col gap-0.5">
                    {checklist.slice(0, 5).map((c, ci) => (
                      <div key={ci} className="flex gap-1.5 text-[10.5px] leading-snug">
                        <span style={{ color: c['result'] === 'HARD_EXCLUDE' ? TOKENS.stEcartee : c['severity'] === 'fort' ? TOKENS.stCreuser : TOKENS.txtMut }}>
                          {c['result'] === 'HARD_EXCLUDE' ? '✕' : '☐'}</span>
                        <span className="text-txt-mut"><b className="text-txt">{c['layer']}</b> — {c['detail']}</span>
                      </div>
                    ))}
                    {checklist.length === 0 && <span className="text-[10.5px] text-mint">✓ aucun point de vigilance</span>}
                  </div>
                )}
                {checklist.length === 0 && <p className="mt-1.5 text-[10.5px] text-mint">✓ aucun point de vigilance cascade</p>}
                <a href={i['pdf'] as string} target="_blank" rel="noreferrer" className="mt-1 inline-block text-[10.5px] text-mint/70 transition-colors duration-quick hover:text-mint hover:underline">⬇ PDF</a>
              </div>
              )})() : (
              <div key={k} className="rounded-lg border border-st-ecartee/40 bg-st-ecartee/10 px-3 py-2 text-[11px] text-st-ecartee">
                {i['ref'] as string} — {i['erreur'] as string}
              </div>
            ))}
          </div>
        </>
      )}
    </>
  )
}


/* ───────────────────── OUTIL « RISQUES » (M137-T) — fusion O5 + M10 ─────────────────────
   Deux outils répondaient à la MÊME question (« qu'est-ce qui cloche ? ») avec deux forces.
   Ils fusionnent en UN, deux entrées :
     A — « une parcelle » : lecture géométrique directe + SUP→effet + source/date + NON COUVERT (O5) ;
     B — « un lot »        : jusqu'à 60 parcelles, risque + checklist + PDF + propriétaire (M10),
                             avec le bloc NON COUVERT reporté (fin du RAS muet à l'échelle du lot).
   Le nom ne promet pas l'exhaustivité (pas de « contrôle complet » / « due diligence »). */
function Risques() {
  const selectedIdu = useApp((s) => s.selectedIdu)
  // depuis une fiche (parcelle sélectionnée) → entrée détail ; sinon libre choix, détail par défaut.
  const [entree, setEntree] = useState<'parcelle' | 'lot'>('parcelle')
  return (
    <>
      <div data-risques-entrees className="flex gap-1">
        {([['parcelle', 'Une parcelle'], ['lot', 'Un lot']] as const).map(([k, lbl]) => (
          <button key={k} data-risques-entree={k} onClick={() => setEntree(k)}
            className={`flex-1 rounded-lg border px-2 py-1 text-[11px] font-medium transition-colors duration-quick ${
              entree === k ? 'border-mint/60 bg-mint/10 text-mint' : 'border-line-2 text-txt-mut hover:text-txt'}`}>
            {lbl}
          </button>
        ))}
      </div>
      {/* parcelle : servitudes détail + NON COUVERT ; lot : risque + checklist + NON COUVERT reporté */}
      {entree === 'parcelle' ? <O5Servitudes key={selectedIdu ?? 'o5'} /> : <M10 />}
    </>
  )
}


const COMPONENTS: Record<string, () => JSX.Element> = {
  // §3 — outil « Permis » unifié : `permis` (radar, carte au menu) ET `promesses` (filtre « Au point
  // mort », clé ALIASÉE hidden) résolvent le MÊME composant M03. `promesses` ouvre le filtre pré-actif
  // (deep-link/copilote/QA inchangés). Composant M04 autonome supprimé (absorbé).
  patrimoine: M02, permis: M03, promesses: M03,
  // M137-N (Vic 20/08/2026) : 'bailleur' (M06) et 'fantome' (M07) retirés du produit (DORMANT) —
  // plus câblés au menu. Composants M06/M07 conservés au dépôt (exportés, cf. leur en-tête).
  // M137-T — 'duediligence' (M10) et 'o5-servitudes' (O5) fusionnés dans l'outil « risques ».
  temps: M08, courriers: M09, risques: Risques,
  // COMPARAISON (refonte) — « comparer » devient un outil ANCRÉ : ModulePanel monte son panneau gauche
  // (stepper + chips + « Comparer (n/3) »), la carte reste active à droite, le tableau s'ouvre en overlay.
  comparer: CompareModule,
  // Retiré du produit le 21/08/2026 (DORMANT) : 'zan' (M17, Simulateur ZAN) — enveloppe communale
  // (+ budget en %) déplacée dans l'outil Communes ; signal parcelle = doublon fiche ; liste morte.
  assemblage: M16, programme: M22,
  // Baromètre retiré du menu → clé 'barometre' ALIASÉE vers Communes (l'onglet Évolution y vit) :
  // aucun lien mort (deep-link/copilote historique). M18 reste importé, réutilisé par cet onglet.
  barometre: Communes,
  // M137-Z — outil « Communes » : fusion Marché (MU1) · Comparateur (O6) · Vélocité (M05) · Rareté (O9).
  // Les 4 clés absorbées ('marche', 'o6-comparateur', 'velocite', 'o9-rarete') sont retirées du menu ;
  // leurs composants (MarcheCommune, O6Comparateur, M05, O9Rarete) restent au dépôt, réutilisés par Communes.
  communes: Communes,
  // M137-P — les 3 outils PLU (simulplu · verif-procedure · plu-annuaire) fusionnés dans le hub « plu ».
  plu: Plu,
  // M137-K (Vic 20/08/2026) : 'scoring-v2' (Radar des ventes) retiré du produit (DORMANT) —
  // recouvre l'Analyse LABUSE. Composant ScoringV2Module + endpoints /v2/* conservés au dépôt.
  renouvellement: RenouvellementModule,
  'prospection-solaire': ProspectionSolaire,
  // FUSION « Étudier un bien » (Vic 21/08/2026) : les DEUX clés résolvent le MÊME composant fusionné
  // — 'scoreur-adresse' (créneau phare O2, carte au menu) ET 'calculette-fonciere' (M23 aliasée, hidden :
  // ouverte par la porte fiche/copilote via calcPrefill, jamais un 404). Anciens composants
  // ScoreurAdresse + CalculetteFonciere supprimés (logique absorbée ; endpoint /scoreur-adresse vivant).
  'scoreur-adresse': EtudierBien,
  // Retiré du produit le 21/08/2026 (DORMANT) : 'o7-carnet' (Suivi de secteur) — le vrai suivi = la
  // Veille. Composant O7Carnet conservé au dépôt ; endpoints /carnet-secteur vivants.
  // Retiré du produit le 21/08/2026 (DORMANT) : 'o10-bascules' (Quoi de neuf) — plus monté. Composant
  // O10Bascules conservé au dépôt (exporté) ; son endpoint /events reste vivant (cloche de notifications).
  'calculette-fonciere': EtudierBien,
}

export function ModulePanel() {
  const { module, setModule, toggleOutils } = useApp()
  const def = MODULES.find((m) => m.key === module)
  // M6.1 item 3 : Échap ferme le panneau (cohérent fiche/contexte). La fiche et les
  // tiroirs gardent la priorité : si l'un d'eux est ouvert, c'est LUI qu'Échap ferme.
  // Phase CAPTURE : il faut lire l'état AVANT que le handler de la fiche (bulle,
  // Fiche.tsx) ne fasse select(null) — sinon, fiche montée avant le panneau = un seul
  // Échap fermerait les deux d'un coup (zustand est synchrone).
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return
      const st = useApp.getState()
      // COMPARAISON : tant que le TABLEAU est ouvert, Échap le ferme (ComparePanel) — on ne ferme pas
      // l'outil par-dessous. Le 2ᵉ Échap (tableau fermé) fermera l'outil.
      if (st.selectedIdu || st.sourceLine || st.tool || st.compareOpen) return
      st.setModule(null)
    }
    window.addEventListener('keydown', h, true)
    return () => window.removeEventListener('keydown', h, true)
  }, [])
  if (!def) return null
  const Body = COMPONENTS[def.key]
  return (
    <aside className="flex h-full w-[320px] shrink-0 flex-col border-r border-line bg-surface-1">
      <div className="flex shrink-0 flex-col border-b border-mint/20 bg-mint/[0.07] px-4 py-3">
        {/* M6.1 item 3 : retour direct au menu Outils (fil d'Ariane) — plus besoin de
            repasser par le rail pour changer d'outil. */}
        <div className="flex items-center justify-between gap-2">
          <nav data-module-breadcrumb className="flex min-w-0 items-center gap-2 font-mono text-[10px] tracking-widest">
            {/* Fix cosmétique (point 27) : flèche retour PLUS VISIBLE — pastille bordée mauve, plus
                grosse, zone de clic élargie + libellé « ← Outils » clair (avant : 10 px inline, on la cherchait). */}
            <button data-module-retour onClick={toggleOutils}
              className="flex shrink-0 items-center gap-1 rounded-md border border-mint/40 bg-mint/10 px-2.5 py-1 text-[11px] font-semibold tracking-wide text-mint transition-colors duration-quick hover:border-mint hover:bg-mint/15"
              title="Revenir au menu Outils">
              ← Outils
            </button>
            <span className="text-txt-dim">›</span>
            <span className="truncate text-txt-mut">{def.label.toUpperCase()}</span>
          </nav>
          <button onClick={() => setModule(null)} aria-label="Fermer le module"
            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-txt-mut transition-colors duration-quick hover:bg-mint/10 hover:text-txt-hi"
            title="Fermer le module (Échap)">✕</button>
        </div>
        <div className="mt-1">
          {/* P3 (revue Vic n°3) : plus de code M à l'écran — l'intitulé métier + le bénéfice */}
          <h2 className="text-sm font-medium text-txt-hi">{def.label}</h2>
          <p className="mt-0.5 text-[10.5px] leading-snug text-txt-dim">{def.desc}</p>
        </div>
      </div>
      <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-hidden p-4">
        <Body />
      </div>
    </aside>
  )
}
