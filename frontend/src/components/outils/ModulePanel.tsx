import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Siren } from '../shared/Siren'   // RETOURS-12 T2 — SIREN cliquable Pappers
import { useEffect, useMemo, useState } from 'react'
import {
  courrierPdf, getCommunes, getCourrierDemandes, getFiche, modBailleur,
  modDueDiligence, modFantome, modParcellePermis, modPatrimoine, modPatrimoineSearch, modPermis, modPermisCount,
  modPermisFiche, modPromesses, modPromessesCount, modVelocite, postCourrierDemande,
} from '../../lib/api'
import { AddressAutocomplete } from '../AddressAutocomplete'
import { ParcelInput } from '../ParcelInput'
import { TEMPS_MILLESIMES } from '../map/basemaps'
import { fmtEurCompact, fmtInt } from '../../lib/format'
import { iduComplet, iduCourt, estIdu } from '../../lib/format'
import { pointInPolygon } from '../../lib/geo'
import { TOKENS } from '../../lib/tokens'
import { carteEtat, etatColor, type PermisEtat, type PermisEtatCarte } from '../../lib/permisEtats'
import { ChevronSection } from '../panel/ChevronSection'
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
import { EtudeZone } from './EtudeZone'
import { TaxeAmenagement } from './TaxeAmenagement'
import { MonSecteur } from './MonSecteur'   // SECTEUR-1 (S1) — outil « Mon secteur »
import { ScanPatrimoine } from './ScanPatrimoine'   // RETOURS-4 S7 — fusion Scan patrimoine (possède + construit)
import { TierBadge } from './TierBadge'
import { ListPaginationFooter, PAGE_SIZE } from '../ListPagination'

/* ───────── primitives partagées (doctrine module : violet, bandeau honnête, liste→fiche) ───────── */

function Banner({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-line-2 bg-mint/[0.05] px-3 py-2 text-[10.5px] leading-relaxed text-txt-mut">
      {children}
    </div>
  )
}

// RETOURS-5 T4.5 — `hoverFull` : survol PLEIN (dégradé vert, encre sombre) sur les lignes de parcelles du
// Scan patrimoine, sans changer le survol léger des autres outils qui réutilisent Row.
function Row({ idu, right, sub, fiche, hoverFull }: { idu: string; right: React.ReactNode; sub?: string; fiche?: [string, string][]; hoverFull?: boolean }) {
  const { select, moduleFiche, setModuleFiche, module } = useApp()
  return (
    <button
      onClick={() => {
        if (fiche && module) setModuleFiche({ ...moduleFiche, [idu]: { module, lines: fiche } })
        select(idu)
      }}
      className={`flex w-full shrink-0 items-center gap-2 rounded-lg border border-line-2 bg-surface-3 px-3 py-2 text-left ${hoverFull ? 'hover-fill' : 'transition-colors duration-quick hover:border-mint/50'}`}
    >
      <div className="min-w-0 flex-1">
        <div className="font-mono text-xs text-txt-hi">{idu.slice(8, 10)} {idu.slice(10)}</div>
        {sub && <div className="truncate text-[10.5px] text-txt-mut">{sub}</div>}
      </div>
      <div className="shrink-0 text-right">{right}</div>
    </button>
  )
}

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

/** RETOURS-18 X1 — barre repliable d'accordéon (panneau Permis, un seul bloc ouvert à la fois). Même
 *  geste que les tiroirs de l'app : en-tête cliquable (titre + résumé quand replié + `ChevronSection`),
 *  corps sous filet. Clavier : Entrée/Espace ouvrent (bouton natif) ; Échap referme. `grow` → le corps
 *  prend la hauteur restante et défile seul (verticalement, jamais horizontalement) — c'est la liste des
 *  permis ; sinon hauteur naturelle. Survol conforme (`.hover-fill` : aplat vert, encre sombre). */
function BlocAccordeon({ id, titre, resume, open, onOpen, onClose, grow, children }: {
  id: string; titre: string; resume?: React.ReactNode; open: boolean
  onOpen: () => void; onClose: () => void; grow?: boolean; children: React.ReactNode
}) {
  return (
    <div data-permis-bloc={id}
      className={`flex flex-col overflow-hidden rounded-lg border border-line-2 ${open && grow ? 'min-h-0 flex-1' : 'shrink-0'}`}>
      <button data-permis-bloc-toggle={id} aria-expanded={open}
        onClick={() => (open ? onClose() : onOpen())}
        onKeyDown={(e) => { if (e.key === 'Escape' && open) { e.stopPropagation(); onClose() } }}
        className="hover-fill group flex w-full shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-left">
        <span className="shrink-0 text-[12px] font-medium text-txt">{titre}</span>
        {!open && resume != null && <span className="min-w-0 flex-1 truncate text-[11px] text-txt-dim">{resume}</span>}
        <span className="ml-auto shrink-0"><ChevronSection open={open} /></span>
      </button>
      {open && (
        <div className={grow
          ? 'flex min-h-0 flex-1 flex-col overflow-hidden border-t border-line-2'
          : 'flex flex-col gap-2 border-t border-line-2 px-2 py-2'}>
          {children}
        </div>
      )}
    </div>
  )
}

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

// Exporté pour test (SCAN — le retrait de l'action courrier est le cœur du mandat).
// RETOURS-4 S7 — « Ce qu'ils POSSÈDENT », onglet 1 de la fusion Scan patrimoine. En mode `embedded`, la
// barre de recherche interne DISPARAÎT (la fusion en fournit une seule, partagée) et le propriétaire vient
// de `sirenProp` ; le pont « Voir ses opérations » devient une BASCULE D'ONGLET (`onVoirOperations`).
export function M02({ embedded, sirenProp }: { embedded?: boolean; sirenProp?: string | null } = {}) {
  const { m02Prefill, setM02Prefill } = useApp()
  // RETOURS-3 R4.3 — pont Scan patrimoine → Veille promoteurs (« Voir ses opérations », même SIREN).
  const setVeilleFocusSiren = useApp((s) => s.setVeilleFocusSiren)
  const setModule = useApp((s) => s.setModule)
  // OUTILS-FIX-2 A1 — pont Scan patrimoine → Courrier ; A5 — pont Listes → Comparer. Le propriétaire
  // est déjà résolu : le Courrier reçoit les IDU (jamais les noms). Comparer se limite à 3 côté outil.
  const setCourrierPrefillIdus = useApp((s) => s.setCourrierPrefillIdus)
  const addToCompare = useApp((s) => s.addToCompare)
  const openCompare = useApp((s) => s.openCompare)
  const pushOutilRetour = useApp((s) => s.pushOutilRetour)   // OUTILS-FIX-3 Lot D — fil de retour
  const [sel, setSel] = useState<Set<string>>(new Set())
  const [q, setQ] = useState('')
  const [sirenState, setSiren] = useState<string | null>(null)
  // RETOURS-12 O5 — le bandeau (nom + 3 chiffres + détail) est REPLIABLE en accordéon pour laisser
  // toute la place à la liste des parcelles (bug : la liste ne s'ouvrait pas, noyée sous le bandeau).
  const [bandeauReplie, setBandeauReplie] = useState(false)
  const siren = embedded ? (sirenProp ?? null) : sirenState
  useEffect(() => { setBandeauReplie(false); setSel(new Set()) }, [siren])   // nouveau propriétaire → bandeau déplié + sélection vidée
  useEffect(() => {
    // en mode embarqué, le SIREN vient de la fusion (sirenProp) — on ne consomme pas m02Prefill (pas de course).
    if (!embedded && m02Prefill) { setSiren(m02Prefill); setM02Prefill(null) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [m02Prefill, embedded])
  const sug = useQuery({ queryKey: ['m02s', q], queryFn: () => modPatrimoineSearch(q), enabled: q.length >= 2 && !siren })
  // RETOURS-11 (T4) — la LISTE du patrimoine est paginée par 200 (« Voir plus »), plus jamais tronquée
  // muettement. L'endpoint sert des pages (limit/offset) : la page 0 porte aussi les agrégats (`d`).
  const M02_PAGE = 200
  const pat = useInfiniteQuery({
    queryKey: ['m02-liste', siren],
    queryFn: ({ pageParam }) => modPatrimoine(siren!, M02_PAGE, pageParam as number),
    initialPageParam: 0,
    getNextPageParam: (last, pages) => (last as Record<string, any>)['tronquee'] ? pages.length * M02_PAGE : undefined,
    enabled: !!siren,
  })
  const pages = (pat.data?.pages ?? []) as Record<string, any>[]
  const d = pages[0]  // page 0 = agrégats (nom, n_parcelles, n_actionnables, sdp…) + 1re tranche d'items
  const items = pages.flatMap((p) => (p['items'] ?? []) as Record<string, any>[])
  const total = (d?.['n_parcelles'] as number) ?? 0
  useModuleMap(items.map((i) => i['idu'] as string), null, [pat.dataUpdatedAt])
  return (
    <>
      {/* RETOURS-4 S7 — la barre de recherche interne n'existe QUE hors fusion (embedded → recherche unique en tête). */}
      {!embedded && <input value={q} onChange={(e) => { setQ(e.target.value); setSiren(null) }}
        placeholder="SIREN ou nom (ex. CBO, SCI…)"
        className="rounded-lg border border-line-2 bg-surface-3 px-2 py-1.5 text-xs text-txt focus:border-mint focus:outline-none" />}
      {!embedded && !siren && (sug.data ?? []).map((s) => (
        <button key={s.siren} onClick={() => setSiren(s.siren)}
          className="flex items-center justify-between rounded-lg border border-line-2 bg-surface-3 px-3 py-1.5 text-left text-xs text-txt transition-colors duration-quick hover:border-mint/50">
          <span className="truncate">{s.nom}</span><span className="font-mono text-[11px] text-txt-dim">{s.n} parc.</span>
        </button>
      ))}
      {/* garde : le typeahead plafonne à 12 — on le DIT (jamais une coupe muette). */}
      {!embedded && !siren && (sug.data?.length ?? 0) >= 12 && (
        <p className="text-[10.5px] text-txt-dim">12 premiers résultats — affinez le nom ou le SIREN.</p>
      )}
      {/* Fix pré-lancement : distinguer un « 0 résultat LÉGITIME » d'une panne — sans ça, une boîte
          absente des fichiers fonciers (ex. VISHOR MATERIAUX) donne un écran muet lu comme « cassé ». */}
      {!embedded && !siren && q.length >= 2 && !sug.isFetching && (sug.data?.length ?? 0) === 0 && (
        <div data-m02-vide className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-[11px] leading-snug text-txt-mut">
          « <b className="text-txt">{q}</b> » n'a pas de foncier connu dans les fichiers fonciers (DGFiP),
          ou n'y figure pas. Ces fichiers ne recensent que les <b>personnes morales</b> détentrices de
          foncier à La Réunion — une personne physique ou une société sans bien détecté n'apparaît pas.
        </div>
      )}
      {embedded && !siren && <p className="text-[11px] leading-snug text-txt-dim">Cherchez un propriétaire (nom, SIREN/SIRET, IDU ou adresse) dans la barre du haut pour voir ce qu'il possède.</p>}
      {/* OUTILS-FIX-3 B2 — donnée réellement vide : on le DIT, au lieu d'aligner trois zéros (0 parcelle ·
          0 actionnable · 0 m² SDP) doublés d'un encart d'interprétation. Le SIREN est bien résolu (le
          pont/la recherche a rendu un résultat), l'entreprise ne détient simplement rien à La Réunion —
          cas fréquent d'un pétitionnaire de permis basé hors de l'île (constat Vic, SIREN 392801130). */}
      {d && (d['n_parcelles'] as number) === 0 && (
        <div data-m02-aucune-parcelle className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-[11px] leading-snug text-txt-mut">
          {d['nom'] ? <b className="text-txt">{d['nom'] as string}</b> : <>Cette entreprise (<span className="font-mono">{d['siren'] as string}</span>)</>}
          {' '}ne détient <b>aucune parcelle à La Réunion</b> dans les fichiers fonciers (DGFiP). Ces fichiers
          ne recensent que les personnes morales détentrices de foncier sur l'île — une société qui n'y possède
          rien n'y figure pas.
        </div>
      )}
      {d && (d['n_parcelles'] as number) > 0 && (
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
          {/* RETOURS-12 O5 — BANDEAU repliable : replié, une barre compacte rouvrable ; déplié, le nom +
              les 3 chiffres + le détail. Replier libère toute la hauteur pour la LISTE des parcelles. */}
          {bandeauReplie ? (
            <button data-scan-bandeau-rouvrir onClick={() => setBandeauReplie(false)}
              className="flex w-full items-center justify-between rounded-lg border border-line-2 bg-surface-2 px-3 py-1.5 text-left text-[11.5px] text-txt-dim transition-colors duration-quick hover:text-txt">
              <span className="min-w-0 truncate"><b className="text-txt">{d['nom'] as string}</b> · {fmt(total)} parcelles</span>
              <span className="shrink-0 text-txt-mut">détail ▾</span>
            </button>
          ) : (
            <>
              <div className="truncate text-xs font-medium text-txt-hi">{d['nom'] as string}</div>
              {/* RETOURS-5 T4.1 — TROIS chiffres qui comptent, en grille de 3 cartes. Rien d'autre au 1er niveau. */}
              <div className="grid grid-cols-3 gap-2">
                {([['n_parcelles', 'parcelles'], ['n_actionnables', 'actionnables'], ['sdp_residuelle_m2', 'm² SDP résiduelle']] as const).map(([k, lbl]) => (
                  <div key={k} className="min-w-0 rounded-lg border border-line-2 bg-surface-2 px-2.5 py-2.5">
                    <div className="num-key whitespace-nowrap text-[16px] tabular-nums text-mint">{fmt(d[k] as number)}</div>
                    <div className="mt-0.5 text-[10px] leading-tight text-txt-mut">{lbl}</div>
                  </div>
                ))}
              </div>
              {/* RETOURS-5 T4.2 — tout le reste REPLIÉ : détail des actionnables, valorisation, périmètre, nature. */}
              <details className="text-xs">
                <summary className="cursor-pointer list-none py-1.5 text-[11.5px] text-txt-dim marker:hidden hover:text-mint">Détail et méthode ▾</summary>
                <div className="flex flex-col">
                  {/* CONNEXIONS-2 Lot 4 (KO-10) — « hors écartées par vous » SEULEMENT si ce compte a écarté
                      des parcelles (projets/pistes). Sinon « actionnables » sans mention (pas de faux ami). */}
                  <div className="flex justify-between gap-3 py-1 text-[11.5px] text-txt-mut"><span>Actionnables</span><span><b className="text-txt">{fmt(d['n_actionnables'] as number)}</b>{d['hors_ecartees_par_vous'] ? ` hors ${fmt(d['n_ecartees_par_vous'] as number)} écartée(s) par vous` : ''}</span></div>
                  {d['valorisation_nu_eur'] != null && (
                    <div className="flex justify-between gap-3 py-1 text-[11.5px] text-txt-mut"><span>Valorisation du foncier nu</span><span><b className="tnum text-txt">{fmtEurCompact(d['valorisation_nu_eur'] as number)}</b></span></div>
                  )}
                  <div className="flex justify-between gap-3 py-1 text-[11.5px] text-txt-mut"><span>Périmètre</span><span className="text-txt-dim">zones U/AU · DVF terrains</span></div>
                  <div className="flex justify-between gap-3 py-1 text-[11.5px] text-txt-mut"><span>Nature</span><span className="text-txt-dim">estimation indicative</span></div>
                </div>
              </details>
            </>
          )}
          {/* RETOURS-12 O5 — en fusion (ScanPatrimoine), « Voir ses parcelles → » REPLIE le bandeau pour
              ouvrir la liste (les opérations restent dans l'onglet « Construction »). Hors fusion (M02
              seul), le pont historique « Voir ses opérations → » vers Veille promoteurs est conservé. */}
          {d['siren'] != null && (embedded ? (
            !bandeauReplie && (
              <button data-scan-voir-parcelles onClick={() => setBandeauReplie(true)}
                className="hover-fill w-full rounded-lg border border-mint/35 py-2 text-center text-[12.5px] text-mint" title="Replier le bandeau et voir la liste des parcelles">
                Voir ses parcelles →</button>
            )
          ) : (
            <button data-m02-operations
              onClick={() => { const s = String(d['siren']); setVeilleFocusSiren(s); setModule('veille-promoteurs') }}
              className="hover-fill w-full rounded-lg border border-mint/35 py-2 text-center text-[12.5px] text-mint" title="Ce qu'il construit — ses opérations">
              Voir ses opérations →</button>
          ))}
          {/* liste — RETOURS-5 T4.5 : lignes en survol plein (hoverFull).
              RETOURS-13 R18 — en fusion, UN SEUL ÉTAT à la fois : au chargement la liste est
              REPLIÉE (bandeau déplié + bouton « Voir ses parcelles → ») ; le clic replie le
              bandeau ET ouvre la liste. Plus de doublon bouton + liste déjà affichée. */}
          {(!embedded || bandeauReplie) && (<>
          {/* OUTILS-FIX-2 A1/A5 — sur sélection : pont Courrier (IDU du propriétaire résolu) + pont Comparer. */}
          {sel.size > 0 && (
            <div className="flex flex-wrap items-center gap-2">
              {/* OUTILS-FIX-3 Lot D — fil de retour : le Courrier/Comparer cible affiche « ← Scan patrimoine »,
                  qui rouvre ce propriétaire (m02Prefill = SIREN résolu). */}
              <button data-scan-courrier onClick={() => { setCourrierPrefillIdus([...sel]); setModule('courriers'); pushOutilRetour({ module: 'patrimoine', label: 'Scan patrimoine', restore: { m02Prefill: String(d['siren']) } }) }}
                className="rounded-lg border border-mint/50 bg-mint/10 px-2.5 py-1 text-[11px] font-medium text-mint transition-colors duration-quick hover:bg-mint/20">
                ✉ Préparer les courriers ({sel.size})
              </button>
              <button data-scan-comparer onClick={() => { [...sel].slice(0, 3).forEach(addToCompare); openCompare(); pushOutilRetour({ module: 'patrimoine', label: 'Scan patrimoine', restore: { m02Prefill: String(d['siren']) } }) }}
                className="rounded-lg border border-mint/50 bg-mint/10 px-2.5 py-1 text-[11px] font-medium text-mint transition-colors duration-quick hover:bg-mint/20">
                Comparer ({Math.min(sel.size, 3)}) →
              </button>
              {sel.size > 3 && <span className="text-[10px] text-txt-dim">Comparer se limite à 3.</span>}
            </div>
          )}
          <div className="flex min-h-0 flex-1 flex-col gap-1.5 overflow-y-auto">
            {items.map((i) => {
              const idu = i['idu'] as string
              return (
              <div key={idu} className="flex min-w-0 items-center gap-2">
                <input type="checkbox" data-scan-parc-sel className="h-3 w-3 shrink-0 accent-mint" checked={sel.has(idu)}
                  onChange={() => setSel((s) => { const n = new Set(s); n.has(idu) ? n.delete(idu) : n.add(idu); return n })} />
                <div className="min-w-0 flex-1">
                <Row idu={idu} hoverFull
                  sub={`${i['commune']} · ${fmt(i['surface_m2'] as number)} m² · SDP ${fmt(i['sdp'] as number)}`}
                  right={<TierBadge tier={i['tier_v2'] as string | null} etage0={i['etage0'] as boolean | null} statut={null} />}
                  fiche={[['Propriétaire', String(d['nom'])], ['SIREN', String(d['siren'])],
                    ['Patrimoine', `${d['n_parcelles']} parcelles · SDP résiduelle ${fmt(d['sdp_residuelle_m2'] as number)} m²`]]} />
                </div>
              </div>
            )})}
          </div>
          {/* RETOURS-11 T4 — pied de liste PARTAGÉ (SOCLE) : compteur exact « n / total affichées » +
              « Voir 200 de plus » (jamais de dump, jamais de « Tout charger »). Trié par probabilité. */}
          <div className="shrink-0">
            <ListPaginationFooter shown={items.length} total={total} step={M02_PAGE}
              onMore={() => pat.fetchNextPage()}>
              {pat.isFetchingNextPage && <span className="text-txt-dim">chargement…</span>}
              <span className="text-txt-off">· triées par probabilité</span>
            </ListPaginationFooter>
          </div>
          </>)}
        </>
      )}
    </>
  )
}

/* ───────────────────────────── M03 — RADAR PERMIS ───────────────────────────── */

// RETOURS-15 U3 — règle d'ordre : la case « Tout » / « Tous » est TOUJOURS la dernière à droite.
const NATURES = [['PC', 'PC'], ['DP', 'DP'], ['PA', 'PA'], ['PD', 'PD'], ['', 'Tout']] as const

// RETOURS-17 W3 — coupure « récent » (24 mois avant la fin du flux Sitadel), format 'AAAA-MM-JJ'.
// Le serveur ancre récent sur `date >= dmax - interval '24 months'` ; ici on reproduit la MÊME coupure
// pour colorer chaque point de la carte (comparaison lexicographique de dates ISO = comparaison réelle).
const minus24m = (iso?: string): string => {
  if (!iso) return '9999-99-99'   // pas de date → jamais « récent » (sécurité : reste gris)
  const [y, m, d] = iso.split('-')
  return `${Number(y) - 2}-${m}-${d}`
}
// 'AAAA-MM-JJ' → 'JJ.MM.AAAA' (format daté du bloc total, W2).
const frDate = (iso?: string): string => (iso ? iso.split('-').reverse().join('.') : '')

/** Tiroir « fiche permis » (M10 lot 1.1) — s'ouvre au clic sur un permis, partagé radar/fiche. */
export function PermitDrawer({ permitId, onClose }: { permitId: string; onClose: () => void }) {
  const q = useQuery({ queryKey: ['permis-fiche', permitId], queryFn: () => modPermisFiche(permitId) })
  const d = q.data as Record<string, any> | undefined
  const select = useApp((s) => s.select)      // Fix LOT 2 : localiser la parcelle du permis
  const setFlyTo = useApp((s) => s.setFlyTo)
  // OUTILS-FIX-2 A4 — pont Permis → Scan patrimoine (SIREN du porteur → m02Prefill, consommé par ScanPatrimoine).
  const setModule = useApp((s) => s.setModule)
  const setM02Prefill = useApp((s) => s.setM02Prefill)
  const pushOutilRetour = useApp((s) => s.pushOutilRetour)   // OUTILS-FIX-3 Lot D — fil de retour
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
            {/* RETOURS-13 R30 — la DESTINATION est dite (hôtels, bureaux, commerce…) ; une position
                estimée par l'adresse (parcelle du permis disparue du cadastre) est signalée. */}
            <F label="Destination" value={d['destination_libelle']} />
            <F label="Porteur" value={d['porteur'] ?? <span className="text-txt-dim">{d['porteur_note']}</span>} />
            {d['porteur_siren'] && <F label="SIREN" value={<Siren value={String(d['porteur_siren'])} className="font-mono text-txt" />} />}
            {/* OUTILS-FIX-2 A4 — pont Scan patrimoine (porteur avec SIREN seulement ; rien pour un particulier).
                OUTILS-FIX-3 B2 — on TRONQUE à la source aux 9 chiffres du SIREN : Scan interroge
                parcelle_personne_morale.siren (9 chiffres) ; un SIRET (14) passé tel quel ne matcherait jamais
                (zéro muet). `porteur_siren` est déjà un SIREN aujourd'hui — la garde couvre le jour où la
                source SITADEL n'exposerait qu'un SIRET. */}
            {d['porteur_siren'] && (
              <button data-permis-scan-patrimoine
                onClick={() => { setM02Prefill(String(d['porteur_siren']).replace(/\D/g, '').slice(0, 9)); setModule('patrimoine'); onClose(); pushOutilRetour({ module: 'permis', label: 'Permis', restore: { permitToOpen: permitId } }) }}
                className="hover-fill mt-1.5 w-full rounded-lg border border-mint/35 py-1.5 text-center text-[11px] text-mint" title="Voir tout ce que ce porteur possède">
                Scan patrimoine du porteur →</button>
            )}
            <F label="Nombre de lots" value={d['nb_lots']} />
            <F label="Surface habitable" value={d['surface_hab_m2'] != null ? `${fmt(d['surface_hab_m2'])} m²` : null} />
            {d['geoloc_note'] && <p className="mt-1 text-[10px] leading-snug text-txt-dim">Position : {String(d['geoloc_note'])}.</p>}
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
// Exporté pour test (double entrée + lignes enrichies + survol = cœur du mandat PERMIS).
// RETOURS-11 O17 — sélecteur de commune de l'outil Permis, alimenté par la liste réelle des communes
// servies. Écrit le filtre commune GLOBAL (`setCommune`) — le même que lisent déjà `modPermis` /
// `modPromesses` via `cq()` : un seul état, aucune divergence liste/carte.
function CommunePermisSelect({ value, onChange }: { value: string | null; onChange: (c: string | null) => void }) {
  const communes = useQuery({ queryKey: ['communes'], queryFn: getCommunes })
  return (
    <select data-permis-commune value={value ?? ''} onChange={(e) => onChange(e.target.value || null)}
      className="w-full rounded-lg border border-line-2 bg-surface-3 px-2 py-1 text-[11px] text-txt focus:border-mint focus:outline-none">
      <option value="">Toutes les communes</option>
      {(communes.data ?? []).map((c) => <option key={c.commune} value={c.commune}>{c.commune}</option>)}
    </select>
  )
}

export function M03() {
  const moduleKey = useApp((s) => s.module)
  // RETOURS-17 W2 — SEGMENT à CINQ états qui PARTITIONNENT la base (somme = total ; constat Vic 05/09 :
  // trois chips lues comme une répartition alors que deux étaient des fenêtres de temps et la 3e un total) :
  //   Tous · Récent (autorisé ≤ 24 mois) · Dormant (PC ancien sans achèvement) · Achevé (DAACT) · Autre.
  // `pointMort` = le Dormant (endpoint /promesses, jointure parcelle+run) ; `etatSeg` = le paramètre serveur
  // recent|acheve|autre pour les états servis par /permis. La couleur sépare la veille des opportunités.
  const [seg, setSeg] = useState<'cours' | 'mort' | 'tous' | 'acheve' | 'autre'>(moduleKey === 'promesses' ? 'mort' : 'cours')
  const pointMort = seg === 'mort'
  // F2 (OUTILS-3) — « Tous » = tous les états SUPERPOSÉS sur la carte, chacun sa couleur (récent vert,
  // dormant corail, achevé/autre gris) — avant, tout était peint en vert (« 47 000 verts, lit 5 580 »).
  const tous = seg === 'tous'
  // RETOURS-17 W2 — état de cycle servi par /permis (dormant reste sur /promesses).
  const etatSeg = seg === 'acheve' ? 'acheve' : seg === 'autre' ? 'autre' : null
  const [months, setMonths] = useState(moduleKey === 'promesses' ? 36 : 24)
  const [nature, setNature] = useState('')
  const [open, setOpen] = useState<string | null>(null)
  // RETOURS-18 X1 — panneau en ACCORDÉON : sous le bloc total (permanent) et le bandeau Sitadel
  // (permanent), trois blocs repliables dont UN SEUL est ouvert (Filtrer par état · Affiner · Voir les
  // permis). Ouvrir l'un referme les autres. « Filtrer par état » ouvert au départ (la liste ne s'affiche
  // plus d'emblée — constat Vic : tout ouvert d'un coup, on ne voit pas le bas).
  const [bloc, setBloc] = useState<'etat' | 'affiner' | 'liste' | null>('etat')
  // O17 (e) — « non géocodés » devient un FILTRE : tous | seuls les géocodés | seuls les non géocodés.
  const [geoFiltre, setGeoFiltre] = useState<'tous' | 'geo' | 'nongeo'>('tous')
  const zone = useApp((s) => s.zone)
  const commune = useApp((s) => s.commune)
  const setCommune = useApp((s) => s.setCommune)
  // radar-permis #2a — un clic sur un point permis de la carte (MapView) demande l'ouverture du drawer
  // via `permitToOpen` ; on le consomme puis on le remet à null (même idiome que parcelPrefill).
  const permitToOpen = useApp((s) => s.permitToOpen)
  const setPermitToOpen = useApp((s) => s.setPermitToOpen)
  const setFlyTo = useApp((s) => s.setFlyTo)
  const focusParcelle = useApp((s) => s.focusParcelle)   // RETOURS-12 O12.2 — zoom+surbrillance commun (O1)
  useEffect(() => { if (permitToOpen) { setOpen(permitToOpen); setPermitToOpen(null) } }, [permitToOpen, setPermitToOpen])
  // la clé d'ouverture (radar `permis` vs filtre `promesses`) fixe le MODE d'entrée + la fenêtre par
  // défaut ; ensuite le toggle local est maître (un deep-link vers l'autre clé re-cale l'écran).
  useEffect(() => { const s = moduleKey === 'promesses' ? 'mort' : 'cours'; setSeg(s); setMonths(s === 'mort' ? 36 : 24) }, [moduleKey])

  const MONTHS_RADAR = [12, 24, 48, 72, 240]   // 240 = « Tout » (≈ toute la profondeur Sitadel servie)
  const MONTHS_PM = [24, 36, 48, 60]   // point mort : 36 = caducité légale du PC (défaut à l'ouverture)
  // RETOURS-17 — Dormant garde sa fenêtre de caducité (36 mois) ; Récent = 24 mois ; Tous/Achevé/Autre
  // travaillent sur toute la profondeur (240 mois), l'état de cycle fait le tri côté serveur.
  const choisirSeg = (s: 'cours' | 'mort' | 'tous' | 'acheve' | 'autre') => {
    setSeg(s); setMonths(s === 'mort' ? 36 : s === 'cours' ? 24 : 240)
  }

  // deux sources, une seule active à la fois (enabled) : RADAR = tous les permis ; POINT MORT = PC
  // anciens sans achèvement (l'endpoint /promesses renvoie désormais aussi la géom → des points).
  // RETOURS-11 (T4) — pagination par 200 partout (doctrine SOCLE) : plus de pages de 300/1000.
  const RADAR_PAGE = 200
  const qRadar = useInfiniteQuery({
    queryKey: ['m03', months, nature, commune, etatSeg],
    queryFn: ({ pageParam }) => modPermis(months, nature || null, RADAR_PAGE, pageParam as number, etatSeg),
    initialPageParam: 0,
    getNextPageParam: (last, pages) => (last as Record<string, any>)['has_more'] ? pages.length * RADAR_PAGE : undefined,
    enabled: !pointMort,
  })
  const PM_PAGE = 200  // RETOURS-11 (T4) — 1re page par 200 (SOCLE) → affichage rapide ; le reste en « voir plus »
  // F2 — le `months` du point mort mesure la DORMANCE (« PC plus vieux que N mois ») : sémantique
  // INVERSE du radar (« derniers N mois »). En « Tous », le radar élargit à 240 (tout), mais le point
  // mort DOIT garder sa fenêtre de caducité (36 mois) — sinon « plus vieux que 240 mois » = 0 résultat
  // (le bug F2 : aucun point mort en « Tous »). Décoré ici, une seule source de vérité.
  const pmMonths = pointMort ? months : 36
  const qPm = useInfiniteQuery({
    queryKey: ['m04', pmMonths, commune],
    queryFn: ({ pageParam }) => modPromesses(pmMonths, PM_PAGE, pageParam as number),
    initialPageParam: 0,
    getNextPageParam: (last, pages) => (last as Record<string, any>)['has_more'] ? pages.length * PM_PAGE : undefined,
    enabled: pointMort || tous,   // F2 — le point mort alimente aussi la carte en mode « Tous »
  })
  // total point mort (COUNT ~4 s) DÉCOUPLÉ : arrive en parallèle, ne bloque pas la 1re page
  const qPmCount = useQuery({ queryKey: ['m04-count', pmMonths, commune], queryFn: () => modPromessesCount(pmMonths), staleTime: 60_000, enabled: pointMort || tous })

  // PERMIS (refonte) — les DEUX entrées affichent un compteur RÉEL : radar = total de la page 0
  // (cache react-query, chargée à l'arrivée = entrée par défaut) ; point mort = count fixe (caducité
  // 36 mois), toujours servi, indépendant de la fenêtre active.
  const qPmEntry = useQuery({ queryKey: ['pm-entry', commune], queryFn: () => modPromessesCount(36), staleTime: 60_000 })
  // F2 — compteur « En cours » STABLE (fenêtre 24 m fixe), indépendant du segment actif : sinon le
  // libellé du segment changeait quand « Tous » élargissait la fenêtre radar.
  const qRadarEntry = useQuery({ queryKey: ['radar-entry', commune], queryFn: () => modPermis(24, null, 1, 0), staleTime: 60_000 })
  const radarEntryTotal = (qRadarEntry.data as Record<string, any> | undefined)?.['total'] as number | undefined
  // RETOURS-16 V4 — le chip « Tous » disait la SOMME de deux fenêtres (Récent 24 m + Dormant 36 m+,
  // « Tous 21 038 ») quand le bas d'écran comptait la base entière (50 544) : deux totaux différents
  // sans périmètre dit (constat Vic). « Tous » = désormais le VRAI total en base (count_only, léger).
  const qTousEntry = useQuery({ queryKey: ['tous-entry', commune], queryFn: () => modPermisCount(240), staleTime: 60_000 })
  const tousEntryTotal = qTousEntry.data?.total
  // RETOURS-17 W1 — mesuré : 70 % des « autres » sont des permis ACHEVÉS (DAACT) — 40 % de la base entière.
  // Ils méritent leur propre ligne (décision Vic 05/09) plutôt que d'être noyés dans « Autres ». Compteur léger.
  const qAcheveEntry = useQuery({ queryKey: ['acheve-entry', commune], queryFn: () => modPermisCount(240, 'acheve'), staleTime: 60_000 })
  const acheveEntryTotal = qAcheveEntry.data?.total
  const pmEntryTotal = qPmEntry.data?.total
  // RETOURS-17 W2 — « Autre » DÉRIVÉ = total − récent − dormant − achevé : garantit que la somme des états
  // fait TOUJOURS le total (partition exacte), sans payer le COUNT « autre » (≈ 560 ms) à chaque montage.
  const autreEntryTotal = (tousEntryTotal != null && radarEntryTotal != null && pmEntryTotal != null && acheveEntryTotal != null)
    ? Math.max(0, tousEntryTotal - radarEntryTotal - pmEntryTotal - acheveEntryTotal) : undefined
  // base : localisés + date du millésime (bloc total en tête), lus du compteur « Tous ».
  const baseLocalises = qTousEntry.data?.geocodes
  const baseJusquAu = qTousEntry.data?.donnees_jusqu_au
  const setPermitHover = useApp((s) => s.setPermitHover)
  useEffect(() => () => setPermitHover(null), [setPermitHover])   // nettoyage au démontage

  // O17 (g) — RECHERCHE PAR PARCELLE : un IDU complet (14 car.) saisi dans la barre interroge
  // /modules/parcelle-permis ; s'il n'a AUCUN permis rattaché, on le dit clairement (« Aucun permis
  // rattaché à cette parcelle »), sinon on ouvre le 1er permis. On distingue un IDU (14 car.) d'un n°
  // de permis Sitadel (chaîne alphanumérique plus courte) sur la longueur — un seul champ, deux sens.
  const [parcelIdu, setParcelIdu] = useState<string | null>(null)
  const qParcelPermis = useQuery({ queryKey: ['parcelle-permis-search', parcelIdu],
    queryFn: () => modParcellePermis(parcelIdu!), enabled: !!parcelIdu })
  // date du millésime Sitadel servi — lue du compteur radar (fenêtre 24 m, TOUJOURS actif).
  const donneesJusquAu = (qRadarEntry.data as Record<string, any> | undefined)?.['donnees_jusqu_au'] as string | undefined
  useEffect(() => {
    if (!parcelIdu) return
    const d = qParcelPermis.data as Record<string, any> | undefined
    const found = (d?.['items'] ?? []) as Record<string, any>[]
    if (d && found.length > 0) { setOpen(found[0]['permit_id'] as string); setParcelIdu(null) }
  }, [parcelIdu, qParcelPermis.data])

  const q = pointMort ? qPm : qRadar
  const pages = (q.data?.pages ?? []) as Record<string, any>[]
  const head = pages[0]  // radar : carte (tous géocodés) + compteurs viennent de la page 0
  const inZone = (i: Record<string, any>) => {
    if (!zone || !i['geom']) return true   // non géocodé → toujours listé
    return pointInPolygon((i['geom'] as { coordinates: [number, number] }).coordinates, zone)
  }
  // O17 (e) — filtre géocodage appliqué à la liste ET à la carte (elles restent synchrones, item i).
  const passeGeo = (i: Record<string, any>) => geoFiltre === 'tous' || (geoFiltre === 'geo' ? !!i['geom'] : !i['geom'])
  // liste = items paginés accumulés (« voir plus ») ; la ZONE dessinée filtre les géocodés
  const items = pages.flatMap((p) => (p['items'] ?? []) as Record<string, any>[]).filter(inZone).filter(passeGeo)
  const geomInZone = (i: Record<string, any>) => !zone || pointInPolygon((i['geom'] as { coordinates: [number, number] }).coordinates, zone)
  // CARTE = points cliquables. RETOURS-17 W3 : la COULEUR SUIT L'ÉTAT (avant, tout radar était peint
  // en vert → « 47 000 verts, lit 5 580 récents », constat Vic). carteRadar = les points servis par
  // /permis (leur état dépend du segment/date) ; cartePm = les dormants (corail), superposés en « Tous ».
  // O17 (d/i) — le filtre « non géocodés seuls » vide la carte ; liste et carte suivent les mêmes filtres.
  const carteRadar = (pointMort || geoFiltre === 'nongeo' ? [] : ((head?.['carte'] ?? []) as Record<string, any>[])).filter(geomInZone)
  const cartePm = ((pointMort || tous) && geoFiltre !== 'nongeo'
    ? (qPm.data?.pages ?? []).flatMap((p) => (p['items'] ?? []) as Record<string, any>[]).filter((i) => i['geom'])
    : []).filter(geomInZone)
  // RETOURS-17 W3 — état de PANNEAU d'une ligne/point radar : Récent (≤ 24 mois) vert · Achevé/Autre gris.
  // Le segment fixe l'état sauf en « Tous » où la coupure 24 mois (cut24) distingue récent du reste.
  const cut24 = minus24m(baseJusquAu ?? donneesJusquAu)
  const radarEtat = (i: Record<string, any>): PermisEtat =>
    seg === 'acheve' ? 'acheve' : seg === 'autre' ? 'autre'
    : (String(i['date'] ?? '') >= cut24 ? 'recent' : 'autre')
  const _feat = (i: Record<string, any>, etat: PermisEtatCarte) => ({ type: 'Feature' as const, geometry: i['geom'],
    properties: { kind: 'permis', etat, permit_id: i['permit_id'], label: `${i['type']} ${i['date']}` } })
  useModuleMap([],
    // W3 — `etat` (recent|dormant|gris) voyage dans les properties ; la carte peint depuis la MÊME source
    // de couleurs que les pastilles (lib/permisEtats). En « Tous », le corail dormant est posé APRÈS le
    // gris/vert → il prime visuellement (un PC dormant reste corail même sous un point gris).
    featureCollection([...carteRadar.map((i) => _feat(i, carteEtat(radarEtat(i)))), ...cartePm.map((i) => _feat(i, 'dormant'))]),
    // O17 (i) — `geoFiltre` en dép. : le filtre géocodage resynchronise la carte avec la liste.
    [seg, pointMort, tous, qRadar.dataUpdatedAt, qPm.dataUpdatedAt, zone, geoFiltre])
  const total = pointMort ? qPmCount.data?.total : ((head?.['total'] as number) ?? 0)
  const loaded = pages.flatMap((p) => (p['items'] ?? []) as unknown[]).length

  // RETOURS-18 X1 — les cinq états (Tous + 4 partition), source unique du rendu ET des résumés d'accordéon.
  const ETATS = [
    ['tous', 'Tous', null, tousEntryTotal, 'toute la base'],
    ['cours', 'Récent', 'recent', radarEntryTotal, 'autorisé ≤ 24 mois'],
    ['mort', 'Dormant', 'dormant', pmEntryTotal, 'ancien PC sans achèvement'],
    ['acheve', 'Achevés', 'acheve', acheveEntryTotal, 'travaux déclarés (DAACT)'],
    ['autre', 'Autres', 'autre', autreEntryTotal, 'ni récent, ni dormant, ni achevé'],
  ] as const
  const actE = ETATS.find((e) => e[0] === seg) ?? ETATS[0]
  // résumé « Filtrer par état » replié : l'état actif + son compte (« Tous — 50 544 »).
  const resumeEtat = `${actE[1]} — ${actE[3] != null ? fmt(actE[3]) : '…'}`
  // résumé « Affiner » replié : les filtres actifs, ou « aucun filtre » quand tout est au défaut.
  const monthsDefaut = pointMort ? 36 : seg === 'cours' ? 24 : 240
  const aucunFiltre = nature === '' && !commune && geoFiltre === 'tous' && months === monthsDefaut
  const resumeAffiner = aucunFiltre ? 'aucun filtre' : [
    !pointMort && nature ? NATURES.find(([v]) => v === nature)?.[1] : null,
    !pointMort && months >= 240 ? 'Tout' : `${months} m${pointMort ? '+' : ''}`,
    commune || null,
    geoFiltre !== 'tous' ? (geoFiltre === 'geo' ? 'géocodés' : 'non géocodés') : null,
  ].filter(Boolean).join(' · ')
  // résumé « Voir les permis » replié : le compte de la sélection courante (filtres appliqués).
  const resumeListe = `${total != null ? fmt(total) : '…'} dans la sélection`

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2">
      {/* ZONE 1 — RECHERCHE. O2-1 — UN champ INTELLIGENT en tête, PLEINE LARGEUR : adresse | commune
          (autocomplete → recadre la carte) OU n° de permis OU IDU de parcelle. À la saisie Entrée sans
          suggestion, on distingue : un IDU cadastral complet (14 car.) → recherche des permis rattachés à
          la parcelle (O17 g) ; sinon une chaîne alphanumérique compacte → n° de permis (ouvre la fiche).
          F3 : enveloppe NON-flex — le wrapper interne `flex-1` d'AddressAutocomplete grandissait
          VERTICALEMENT dans ce flex-col (vide de ~300 px). */}
      <div className="shrink-0">
        <AddressAutocomplete data-testid="permis-recherche" placeholder="Adresse, commune, n° de permis ou parcelle…"
          // RETOURS-16 V5 — la barre permis accepte adresse + parcelle + COMMUNE : le suggest
          // unifié propose les trois à la frappe ; choisir une commune pose le filtre commune.
          grammaires={['adresse', 'cadastre', 'commune']}
          onPick={(it) => { if (it.type === 'commune' && it.commune) setCommune(it.commune) }}
          onSelect={(sel) => { if (sel.idu) focusParcelle(iduComplet(sel.idu)); else setFlyTo({ center: [sel.lon, sel.lat], zoom: 15 }) }}
          onEnterRaw={(t) => {
            const v = iduComplet(t)
            // RETOURS-12 O12.2 — IDU cadastral complet (14 car.) → la carte ZOOME et DÉLIMITE la parcelle
            // (focusParcelle, même geste que O1/J1) EN PLUS de chercher ses permis (O17 g).
            if (v.length === 14 && estIdu(v)) { focusParcelle(v); setParcelIdu(v); return }
            // sinon une référence Sitadel compacte → fiche permis
            if (/^[0-9][0-9a-z]{6,}$/i.test(v)) setOpen(v)
          }} />
        {/* O17 (g) — parcelle SANS permis rattaché : message honnête daté du millésime Sitadel servi. */}
        {parcelIdu && qParcelPermis.data && ((qParcelPermis.data as Record<string, any>)['items'] ?? []).length === 0 && (
          <p data-permis-parcelle-vide className="mt-1 rounded-lg border border-st-creuser/40 bg-st-creuser/10 px-3 py-2 text-[11px] leading-snug text-st-creuser">
            Aucun permis rattaché à cette parcelle <span className="font-mono">{iduCourt(parcelIdu)}</span>
            {donneesJusquAu ? ` (Sitadel au ${donneesJusquAu})` : ' (Sitadel)'}.
            <button onClick={() => setParcelIdu(null)} className="ml-2 underline">effacer</button>
          </p>
        )}
      </div>

      {/* RETOURS-17 W2 — BLOC TOTAL en tête : le total sort des chips (constat Vic 05/09 : « 50k » lu
          comme une part alors que c'est le total). Nombre 24px + « permis autorisés en base » ; dessous,
          les localisés + la profondeur + la date du millésime servi. */}
      <div data-permis-total className="shrink-0 rounded-lg border border-line-2 bg-surface-1 px-3 py-2">
        <div className="flex items-baseline gap-2">
          <span className="tnum text-[24px] font-semibold leading-none text-txt-hi">{tousEntryTotal != null ? fmt(tousEntryTotal) : '…'}</span>
          <span className="text-[12px] text-txt-mut">permis autorisés en base</span>
        </div>
        <p className="mt-1 text-[12px] leading-snug text-txt-dim">
          {baseLocalises != null ? `${fmt(baseLocalises)} localisés sur la carte` : 'localisation en cours'}
          {' · toute la profondeur Sitadel'}{baseJusquAu ? `, jusqu'au ${frDate(baseJusquAu)}` : ''}
        </p>
      </div>

      {/* RETOURS-18 X1 — bandeau Sitadel PERMANENT. RETOURS-19 Y5 — tient sur UNE ligne (phrase resserrée
          + `whitespace-nowrap`) ; `overflow-hidden`/ellipse en garde-fou : la section ne défile JAMAIS
          latéralement (l'infobulle porte la phrase entière si jamais elle était tronquée). */}
      <p title="Sitadel (974) ne publie que les permis autorisés — l'instruction déposée n'y figure pas."
        className="shrink-0 -mt-0.5 truncate px-0.5 text-[9.5px] leading-snug text-txt-dim">
        Sitadel : les permis <b className="text-txt-mut">autorisés</b>, pas l'instruction en cours.
      </p>

      {/* RETOURS-18 X1/X2 — ACCORDÉON : un seul bloc ouvert à la fois (ouvrir l'un referme les autres).
          Le bloc « Voir les permis » (grow) prend la hauteur restante et défile seul ; les autres sont à
          hauteur naturelle. X2 : la RÉGION défile (overflow-y-auto) en secours quand la fenêtre est courte
          (560 px) — avant, le wrapper d'outil était overflow-hidden et tout était ouvert d'un coup, la liste
          se retrouvait écrasée à ~0 px et le bas devenait inatteignable. Les en-têtes des blocs repliés
          restent visibles ; la liste ne s'affiche plus d'emblée. */}
      <div data-permis-accordeon className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto overflow-x-hidden">
        {/* RETOURS-17 W2 — « Filtrer par état » : quatre états empilés (+ Tous) dont la somme fait le total
            (partition exacte, W1). Pastille (= couleur de carte, source unique lib/permisEtats) · nom ·
            définition courte · compte. Un seul actif (fond accent), les autres en contour hairline. */}
        <BlocAccordeon id="etat" titre="Filtrer par état" resume={resumeEtat}
          open={bloc === 'etat'} onOpen={() => setBloc('etat')} onClose={() => setBloc(null)}>
          <div data-permis-segment className="flex flex-col gap-1">
            {ETATS.map(([k, label, etat, n, def]) => {
              const actif = seg === k
          return (
            <button key={k} data-permis-seg={k} onClick={() => choisirSeg(k)} aria-pressed={actif}
              className={`group flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-left transition-colors duration-quick ${
                actif ? 'bg-mint text-mint-ink' : 'border border-line-2 text-txt hover:bg-mint hover:text-mint-ink'}`}>
              {/* pastille = couleur de carte de l'état ; « Tous » n'a pas UNE couleur → anneau neutre. */}
              {etat
                ? <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: etatColor(etat) }} />
                : <span className="h-2 w-2 shrink-0 rounded-full border border-current opacity-50" />}
              <span className="shrink-0 text-[12px] font-medium">{label}</span>
              <span className={`min-w-0 flex-1 truncate text-[11px] ${actif ? 'text-mint-ink/70' : 'text-txt-mut group-hover:text-mint-ink/70'}`}>{def}</span>
                  <span className="shrink-0 tnum text-[12px] font-medium">{n != null ? fmt(n) : '…'}</span>
                </button>
              )
            })}
          </div>
        </BlocAccordeon>

        {/* RETOURS-18 X1 — « Affiner » : période · type · commune · géocodage. Résumé replié = filtres
            actifs (« PC · 24 m · Saint-Denis ») ou « aucun filtre ». Le corps (filet + padding) est fourni
            par BlocAccordeon. */}
        <BlocAccordeon id="affiner" titre="Affiner" resume={resumeAffiner}
          open={bloc === 'affiner'} onOpen={() => setBloc('affiner')} onClose={() => setBloc(null)}>
            {/* PÉRIODE — pleine largeur (segments pleins). Aucun libellé tronqué (flex-wrap si besoin). */}
            <div className="flex flex-wrap overflow-hidden rounded-lg border border-line-2">
              {(pointMort ? MONTHS_PM : MONTHS_RADAR).map((m, i) => (
                <button key={m} onClick={() => setMonths(m)}
                  className={`flex-1 basis-0 border-line-2 px-1.5 py-1 text-[11px] ${i > 0 ? 'border-l' : ''} ${months === m ? 'bg-mint font-medium text-mint-ink' : 'text-txt-mut hover:text-txt'}`}>
                  {!pointMort && m >= 240 ? 'Tout' : `${m} m${pointMort ? '+' : ''}`}
                </button>
              ))}
            </div>

            {/* TYPE (nature) — masqué au point mort (PC seul par construction). */}
            {!pointMort && (
              <div className="flex flex-wrap overflow-hidden rounded-lg border border-line-2">
                {NATURES.map(([v, l], i) => (
                  <button key={v || 'tout'} onClick={() => setNature(v)}
                    className={`flex-1 basis-0 border-line-2 px-1.5 py-1 text-[11px] ${i > 0 ? 'border-l' : ''} ${nature === v ? 'bg-mint font-medium text-mint-ink' : 'text-txt-mut hover:text-txt'}`}>
                    {l}
                  </button>
                ))}
              </div>
            )}

            {/* COMMUNE (O17 f) — filtre commune, liste réelle, jamais tronqué (select). */}
            <CommunePermisSelect value={commune} onChange={setCommune} />

            {/* GÉOCODAGE (O17 e) — « non géocodés » filtre à part entière ; U3 : « Tous » en dernier. */}
            <div className="flex flex-wrap overflow-hidden rounded-lg border border-line-2">
              {([['geo', 'Sur la carte'], ['nongeo', 'Non géocodés'], ['tous', 'Tous']] as const).map(([k, l], i) => (
                <button key={k} data-permis-geo={k} onClick={() => setGeoFiltre(k)}
                  className={`flex-1 basis-0 border-line-2 px-1.5 py-1 text-[11px] ${i > 0 ? 'border-l' : ''} ${geoFiltre === k ? 'bg-mint font-medium text-mint-ink' : 'text-txt-mut hover:text-txt'}`}>
                  {l}
                </button>
              ))}
            </div>
        </BlocAccordeon>

        {/* RETOURS-18 X1 — « Voir les permis » : la liste ne s'affiche PLUS d'emblée. Ouverte, elle prend
            la hauteur restante et défile SEULE, verticalement (X2 — le blocage « on ne voit pas le bas »).
            Résumé replié = le compte de la sélection (filtres appliqués). */}
        <BlocAccordeon id="liste" titre="Voir les permis" resume={resumeListe} grow
          open={bloc === 'liste'} onOpen={() => setBloc('liste')} onClose={() => setBloc(null)}>
          {/* RETOURS-17 W2 — pied : le vivant de la vue active (carte · zone · chargement) ; le total, les
              localisés et la date vivent dans le bloc en tête. shrink-0 : reste visible au-dessus de la liste. */}
          <p data-permis-pied className="shrink-0 px-2 pt-2 text-[11px] text-txt-dim">
            {pointMort
              ? <>{fmt(cartePm.length)} dormants sur la carte{total != null && loaded < total
                  ? <> · <span data-permis-plafond title="Les dormants peuvent compter des milliers de PC : on charge d'abord les plus anciens (les plus dormants) ; affinez en zoomant/filtrant.">les {fmt(loaded)} plus anciens chargés — zoomez pour affiner</span></> : ''}</>
              : <>{fmt(carteRadar.length)} sur la carte
                  {total != null && loaded < total ? <> · {fmt(loaded)} / {fmt(total)} chargés</> : null}</>}
            {zone && <span className="text-mint/70"> · {items.length} dans la zone dessinée</span>}
          </p>

          {pointMort && qPm.isLoading && <div className="flex flex-1 items-center justify-center py-8"><Loading accent="mint" label="Analyse en cours…" big /></div>}

          {/* RETOURS-15 U4 — la liste ne déborde JAMAIS en largeur : elle défile verticalement seule. */}
          <div className="flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto overflow-x-hidden px-2 py-2">
        {items.map((i, k) => {
          // R6 — items sur UNE ligne : pastille · type · date · logements/surface · commune, puis le badge
          // d'état À DROITE de la même ligne. Pastille VERTE (en cours) / ROUGE (point mort) = même code que
          // la carte. Le badge point mort porte l'ANCIENNETÉ CALCULÉE (« Sans DAACT · X ans ») : c'est elle
          // qui mesure la dormance, donc l'intérêt. Année depuis la date d'autorisation (AAAA-…).
          const an = Number(String(i['date'] ?? '').slice(0, 4))
          const ans = an ? new Date().getFullYear() - an : null
          // O17 (b) — commune si connue ; à défaut la section-parcelle (IDU rattaché). Jamais un « — » nu.
          const commuLbl = (i['commune'] as string) || ''
          const iduLbl = i['idu'] ? iduCourt(i['idu'] as string) : ''
          const gaucheL2 = commuLbl || (iduLbl ? `Parcelle ${iduLbl}` : '')
          // RETOURS-17 W3 — la pastille de la LIGNE = la couleur de son ÉTAT (source unique lib/permisEtats),
          // la MÊME que le point sur la carte : Récent vert · Dormant corail · Achevé/Autre gris.
          const et: PermisEtat = pointMort ? 'dormant' : radarEtat(i)
          const etTitre = { recent: 'Récent — autorisé dans les 24 derniers mois.',
            dormant: 'Dormant — permis de construire de plus de 36 mois, sans déclaration d\'achèvement (DAACT) et parcelle toujours non bâtie.',
            acheve: 'Achevé — travaux déclarés terminés (DAACT).',
            autre: 'Autre — ni récent, ni dormant, ni achevé (autre nature, permis non rattaché, ou période intermédiaire).' }[et]
          return (
          <button key={k} data-permis-row data-geocode={i['geom'] ? '1' : '0'} data-point-mort={pointMort ? '1' : '0'} data-permis-row-etat={et}
            onClick={() => setOpen(i['permit_id'] as string)}
            onMouseEnter={() => i['geom'] && setPermitHover(i['geom'])} onMouseLeave={() => setPermitHover(null)}
            className={`flex w-full items-center gap-2 rounded-lg border border-line-2 px-3 py-1.5 text-left text-[11px] transition-colors duration-quick hover:border-mint/60 ${i['geom'] ? 'bg-surface-3' : 'bg-surface-1'}`}>
            {/* RETOURS-11 R6 — puce sur UNE seule ligne (moitié moins haute) : pastille · type · date ·
                lgt/surface · commune (tronquée) à gauche, badge d'état (Autorisé / Sans DAACT / non géocodé)
                aligné À DROITE de la MÊME ligne (avant : le badge décrochait sur une 2ᵉ ligne). */}
            {/* RETOURS-17 W3 — pastille = couleur d'état (source unique) ; sa définition tient dans l'infobulle. */}
            <span className="h-[7px] w-[7px] shrink-0 rounded-full" style={{ background: etatColor(et) }} title={etTitre} />
            {/* RETOURS-16 V2.3 — chip type masqué en mode Dormant : l'endpoint ne sert QUE des PC
                (WHERE type='PC'), la valeur ne varie jamais — une constante n'est pas une information. */}
            {!pointMort && <span className="shrink-0 rounded border border-line-2 px-1.5 py-0.5 font-mono text-[10px] text-txt-hi">{i['type'] as string}</span>}
            {/* O17 (h) — DATE = date réelle d'autorisation du permis (par ligne), PAS la date du fichier. */}
            <span className="shrink-0 font-mono text-txt-mut" title="Date d'autorisation du permis">{i['date'] as string}</span>
            {i['nb_lgt'] != null && <b className="shrink-0 tnum text-txt">{String(i['nb_lgt'])} lgt{Number(i['nb_lgt']) > 1 ? 's' : ''}</b>}
            {pointMort && i['surface_m2'] != null && <span className="shrink-0 tnum text-txt-dim">{fmt(i['surface_m2'] as number)} m²</span>}
            {/* commune / parcelle en clair — tronquée pour laisser la place au badge. */}
            {gaucheL2 && <span className="min-w-0 truncate text-txt-mut">{gaucheL2}</span>}
            {/* badges poussés à droite, sur la même ligne. RETOURS-16 V2 — la puce de LOCALISATION
                passe EN PREMIER (elle s'affiche en entier, jamais tronquée — constat Vic « puce
                coupée ») ; le chip « Autorisé » n'arrive plus (état 2 muet côté serveur : constant
                au 974, l'information vit dans la phrase d'explication en tête d'outil). */}
            <span className={`flex shrink-0 items-center gap-1.5 ${gaucheL2 ? '' : 'ml-auto'}`}>
              {/* RETOURS-14 S5.1 — un permis à parcelle incertaine ne pose JAMAIS de point : la
                  liste le dit. RETOURS-15 U4 — libellé COURT, le complet vit dans l'infobulle. */}
              {!i['geom'] && <span data-permis-badge-nongeo className="whitespace-nowrap rounded-full bg-st-creuser/15 px-1.5 py-0.5 text-[9px] font-medium text-st-creuser"
                title={String(i['geoloc'] ? `Localisation approximative (adresse) — ${i['geoloc']}` : "Parcelle d'origine disparue du cadastre et adresse non rattachable — non localisable sur la carte.")}>
                {i['geoloc'] ? 'approx. (adresse)' : 'non localisé'}</span>}
              {!pointMort && i['delai_mois'] != null && <span style={{ color: VIOLET }} title="Délai d'instruction">{String(i['delai_mois'])} m</span>}
              {pointMort
                ? <span data-permis-badge-mort className="whitespace-nowrap rounded-full bg-st-ecartee/15 px-1.5 py-0.5 text-[9px] font-medium text-st-ecartee"
                    title="Aucune déclaration d'achèvement (DAACT) au fichier Sitadel — le commencement n'est pas tracé, ce n'est PAS une preuve de non-réalisation.">Sans DAACT{ans != null ? ` · ${ans} an${ans > 1 ? 's' : ''}` : ''}</span>
                : i['etat_label'] && <span data-permis-etat className="whitespace-nowrap rounded-full bg-surface-2 px-1.5 py-0.5 text-[9px] font-medium text-txt-mut">{i['etat_label'] as string}</span>}
            </span>
          </button>
          )
        })}
        {/* O17 (i) — ÉTAT VIDE : message clair quand aucun permis ne correspond aux filtres. */}
        {!q.isLoading && items.length === 0 && (
          <p data-permis-vide className="px-1 py-6 text-center text-[11px] text-txt-dim">
            Aucun permis ne correspond aux filtres{commune ? ` pour ${commune}` : ''}
            {zone ? ' dans la zone dessinée' : ''}. Élargissez la période ou effacez un filtre.
          </p>
        )}
        {/* O17 (c) — pagination SOCLE par 200 (ListPaginationFooter) au lieu du bouton « voir plus » ad hoc.
            `shown` = lignes chargées du serveur (loaded, avant filtre client) ; `total` = compteur serveur ;
            le bouton « Voir 200 de plus » ne pagine que s'il reste des pages (hasNextPage). */}
        {loaded > 0 && (
          <ListPaginationFooter
            shown={loaded}
            total={total != null ? Math.max(total, loaded) : (q.hasNextPage ? loaded + PAGE_SIZE : loaded)}
            onMore={() => { if (q.hasNextPage) q.fetchNextPage() }} />
        )}
          </div>
        </BlocAccordeon>
      </div>
      {open && <PermitDrawer permitId={open} onClose={() => setOpen(null)} />}
    </div>
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
// PUIS l'année ancienne (UN seul choix, via la FRISE des millésimes) ; l'« après » est TOUJOURS
// aujourd'hui (verrouillé). L'accès depuis la fiche (bouton « 1950 » → parcelPrefill) reste.
// TEMPS (refonte) — les millésimes de la frise sont ceux VÉRIFIÉS servant des dalles sur le 974
// (cf. TEMPS_MILLESIMES / basemaps.ts). La parcelle désignée est ÉPINGLÉE sur les deux fonds.
const TEMPS_KEYS = TEMPS_MILLESIMES.map((m) => m.key) as string[]

// Exporté pour test (TEMPS — la frise des millésimes + l'épingle de la parcelle sont le cœur du mandat).
export function M08() {
  const { cmpLeft, setCmpLeft, setCmpRight, setModule, parcelPrefill, setParcelPrefill, setFlyTo, setTempsPinIdu } = useApp()
  const [idu, setIdu] = useState('')
  // « après » = TOUJOURS aujourd'hui (verrouillé) ; « avant » démarre sur 1950 si hors frise.
  useEffect(() => {
    setCmpRight('bm-ortho-now')
    if (!TEMPS_KEYS.includes(cmpLeft)) setCmpLeft('bm-ortho-1950')
  }, [])   // eslint-disable-line react-hooks/exhaustive-deps
  const designer = async (code: string, coords?: [number, number]) => {
    const c = code.trim(); if (c.length < 10) return
    setIdu(c)
    setTempsPinIdu(c)   // épingle le contour de LA parcelle sur les deux fonds
    if (coords) { setFlyTo({ center: coords, zoom: 18 }); return }
    try { const f = await getFiche(c); if (f.coords) setFlyTo({ center: f.coords, zoom: 18 }) } catch { /* parcelle recentrée au mieux */ }
  }
  // parcelPrefill (fiche « 1950 », clic carte via parcelAt, Copilote) → désigne la parcelle.
  useEffect(() => {
    if (parcelPrefill) { void designer(parcelPrefill); setParcelPrefill(null) }
  }, [parcelPrefill])   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => () => setTempsPinIdu(null), [])   // eslint-disable-line react-hooks/exhaustive-deps

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
        <button onClick={() => { setTempsPinIdu(null); setIdu('') }} className="ml-auto text-[10.5px] text-mint hover:underline">changer</button>
      </div>
      <div className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2.5">
        <p className="label-caps text-[9.5px]">L'année à revoir (avant)</p>
        {/* FRISE des millésimes — l'« avant » se choisit le long d'une frise chronologique ; l'« après »
            est épinglé à droite sur aujourd'hui (verrouillé). Seuls les millésimes servant réellement
            des dalles sur le 974 y figurent (TEMPS_MILLESIMES, vérifiés par GetTile). */}
        <div data-temps-frise className="mt-2">
          <div className="flex items-end gap-0.5">
            {TEMPS_MILLESIMES.map((m) => {
              const on = cmpLeft === m.key
              return (
                <button key={m.key} data-cmp-left={m.key} onClick={() => setCmpLeft(m.key)}
                  title={m.label} aria-pressed={on}
                  className="group flex flex-1 flex-col items-center gap-1 pt-0.5">
                  <span className={`font-mono text-[10px] leading-none ${on ? 'text-mint' : 'text-txt-dim group-hover:text-txt'}`}>{m.an}</span>
                  <span className={`h-2.5 w-2.5 rounded-full border ${on ? 'border-mint bg-mint' : 'border-line-2 bg-transparent group-hover:border-txt-mut'}`} />
                </button>
              )
            })}
            {/* borne « après » = aujourd'hui, verrouillée */}
            <div className="flex flex-1 flex-col items-center gap-1 pt-0.5" title="Après — ortho actuelle (verrouillé)">
              <span className="font-mono text-[10px] leading-none text-txt-dim">Auj.</span>
              <span className="h-2.5 w-2.5 rounded-full border border-dashed border-txt-dim bg-transparent" />
            </div>
          </div>
          {/* rail de la frise */}
          <div className="mt-1 h-px bg-line-2" />
        </div>
        <p className="mt-2 text-[11px] text-txt">
          <span className="text-mint">{TEMPS_MILLESIMES.find((m) => m.key === cmpLeft)?.label ?? '—'}</span>
          <span className="text-txt-dim"> vs </span>Aujourd'hui{/* F7 (OUTILS-3) — mention « 🔒 après fixe » retirée : sans sens pour le client. */}
        </p>
        <p className="mt-2 text-[10.5px] text-txt-dim">Glissez la poignée au centre de la carte pour révéler l'un ou l'autre.</p>
        <button onClick={() => { setTempsPinIdu(null); setModule(null) }}
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
// OUTILS-1 A4/B6 — les états internes (Demandé → Imprimé → Posté) ne sont PLUS exposés côté client
// (décision Vic : le suivi d'exécution reste chez LABUSE). La timeline client a été retirée ; l'admin
// (Tour de contrôle) garde le cycle complet.

/** COURRIER-SERVICE (refonte 13 outils) — l'outil devient un SERVICE : le client prépare
 *  (① destinataires ② rédaction), puis ③ DEMANDE l'envoi à LABUSE. Trois étapes, variables par
 *  courrier, statut visible (Demandé → Imprimé → Posté). PDF relégué en aperçu de relecture.
 *  Exporté pour test (le flux service est le cœur du mandat COURRIER). */
export function M09() {
  const qc = useQueryClient()
  const courrierPrefill = useApp((s) => s.courrierPrefill)
  const setCourrierPrefill = useApp((s) => s.setCourrierPrefill)
  const courrierPrefillIdus = useApp((s) => s.courrierPrefillIdus)
  const setCourrierPrefillIdus = useApp((s) => s.setCourrierPrefillIdus)
  const courrierPrefillPiste = useApp((s) => s.courrierPrefillPiste)
  const setCourrierPrefillPiste = useApp((s) => s.setCourrierPrefillPiste)

  const [step, setStep] = useState<1 | 2 | 3>(1)
  const [dest, setDest] = useState<Dest[]>([])
  // CONNEXIONS-2 Lot 4 (KO-6) — rattachement de la demande à la piste d'origine (courrier depuis le CRM).
  const [rattach, setRattach] = useState<{ pipeline_entry_id: number; projet_id: number | null } | null>(null)
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

  // LOT7 (OUTILS-FINALE) — le prefill se consomme UNE fois au montage et ne persiste NULLE PART.
  // SEULS les ponts intentionnels one-shot amorcent des destinataires : Assemblage / Pièges
  // (courrierPrefillIdus, posé par « Préparer les courriers (n) ») > tuile fiche mono (courrierPrefill).
  // On NE lit plus `selectedIdu` (la parcelle sélectionnée sur la carte n'est PAS un import demandé —
  // c'est elle qui pré-remplissait un chip fantôme « ET 2164 » à l'ouverture, sans geste utilisateur).
  useEffect(() => {
    // KO-6 — la piste (courrierPrefillPiste) est prioritaire : elle amorce le destinataire ET rattache
    // la demande à la piste d'origine (statut relu ensuite dans le Kanban / Mes courriers / dashboard).
    const seed = courrierPrefillPiste ? [courrierPrefillPiste.idu]
      : courrierPrefillIdus?.length ? courrierPrefillIdus
      : courrierPrefill ? [courrierPrefill] : []
    if (courrierPrefillPiste) {
      setRattach({ pipeline_entry_id: courrierPrefillPiste.pipeline_entry_id, projet_id: courrierPrefillPiste.projet_id })
      setCourrierPrefillPiste(null)
    }
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
    mutationFn: () => postCourrierDemande(dest.map((d) => d.idu), corps, modele, recapCommunes(), rattach ?? undefined),
    onSuccess: (d) => { setDemande(d); qc.invalidateQueries({ queryKey: ['courrier-demandes'] }); qc.invalidateQueries({ queryKey: ['pipeline'] }) },
  })
  const apercuPdf = async () => {
    const first = dest[0]; if (!first) return
    setPdfBusy(true); setPdfErr(null)
    try { await courrierPdf(first.idu, modele, remplir(corps, first)) }
    catch { setPdfErr('Le téléchargement du PDF a échoué. Réessayez.') }
    finally { setPdfBusy(false) }
  }

  const STEPS: [1 | 2 | 3, string][] = [[1, 'Destinataires'], [2, 'Rédaction'], [3, 'Envoi']]

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
          {/* LOT7 — l'import Assemblage passe UNIQUEMENT par le pont one-shot « Préparer les courriers (n) »
              (Assemblage → courrierPrefillIdus, consommé au montage ci-dessus). L'ancien bouton lisait le
              `msel` DURABLE (sélection d'assiette qui survivait au changement d'outil) → compteur fantôme
              « Importer depuis Assemblage (118) » sans import demandé. Supprimé : plus de lecture durable. */}
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
            // OUTILS-1 A4/B6 — la confirmation porte le N° DE DEMANDE (= id en base, identique côté admin)
            // et renvoie vers le suivi. AUCUN état interne (imprimé/posté) côté client : décision Vic —
            // moins de surface, moins de bugs. Le suivi vit dans « Projets → Mes courriers ».
            <div data-courrier-confirm className="rounded-lg border border-line-2 bg-mint/[0.05] px-3 py-2 text-[11px] leading-snug text-txt-mut">
              <b className="text-mint">✓ Demande n° {demande.id} transmise.</b> LABUSE vous rappelle sous 24 h ouvrées avec le tarif —
              impression, mise sous pli, affranchissement et suivi compris.
              <span className="mt-1.5 block text-[10.5px] text-txt-dim">Retrouvez vos demandes dans <b className="text-txt-mut">Projets → Mes courriers</b>.</span>
            </div>
          )}
          {envoyer.isError && <p className="text-[10.5px] text-st-ecartee">La demande n'a pas pu être transmise — réessayez.</p>}

          {/* aperçu PDF de RELECTURE (secondaire) — corps rempli pour le 1er destinataire */}
          <button data-courrier-pdf onClick={apercuPdf} disabled={pdfBusy || dest.length === 0}
            className="self-start text-[11px] text-txt-mut hover:text-mint disabled:opacity-40">
            {pdfBusy ? 'Génération…' : '⬇ Télécharger l’aperçu PDF (relecture)'}</button>
          {pdfErr && <p data-courrier-pdf-err className="text-[10.5px] text-st-ecartee">{pdfErr}</p>}

          {/* OUTILS-1 A4 — récap des demandes du client : N° + volume + communes, SANS état interne
              (le suivi d'exécution reste chez LABUSE). La vue complète est « Projets → Mes courriers ». */}
          {(demandes.data?.demandes.length ?? 0) > 0 && (
            <div className="mt-1 flex flex-col gap-1">
              <p className="label-caps text-[9px]">Vos demandes</p>
              {demandes.data!.demandes.slice(0, 5).map((d) => (
                <div key={d.id} className="flex items-baseline justify-between gap-2 text-[10.5px]">
                  <span className="min-w-0 truncate text-txt-mut">n° {d.id} · {d.n} courrier{d.n > 1 ? 's' : ''}{d.communes ? ` · ${d.communes}` : ''}</span>
                  <span className="shrink-0 font-mono text-[9.5px] text-txt-dim">{String(d.ts).slice(0, 10)}</span>
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

// Exporté pour test (le flux « Un lot » est le cœur du mandat PIEGES).
export function M10() {
  // PIEGES (refonte) : BARRE UNIQUE (SOCLE ParcelInput) + « + Ajouter » → chips du LOT (la liste du bas).
  // Le collage en masse reste offert (SECTION+NUMÉRO, une par ligne). Plus d'export PDF (retiré).
  const [lot, setLot] = useState<string[]>([])
  const [paste, setPaste] = useState('')
  const [msg, setMsg] = useState<string | null>(null)
  const setCourrierPrefillIdus = useApp((s) => s.setCourrierPrefillIdus)
  const setModule = useApp((s) => s.setModule)
  // O6(b) — n'ajoute QUE des références cadastrales résolues (IDU complet ou SECTION+NUMÉRO).
  // Une adresse brute non rattachée à une parcelle NE DOIT JAMAIS entrer dans le lot comme chip :
  // ParcelInput ne câble pas onAddress → l'adresse résolue arrive par onPick, l'adresse non résolue
  // affiche son propre message (« aucune parcelle rattachée »). Le collage garde le même garde-fou.
  const ajouter = (v: string) => {
    const t = iduComplet(v).toUpperCase(); if (!t) return
    if (!estIdu(t)) return   // pas une référence cadastrale (ex. adresse brute) → ignorée
    setMsg(null)
    setLot((l) => l.includes(t) ? l : [...l, t])
  }
  const ajouterListe = () => {
    paste.split(/[\n,;]+/).map((x) => x.trim()).filter(Boolean).forEach(ajouter)
    setPaste('')
  }
  const retirer = (t: string) => setLot((l) => l.filter((x) => x !== t))
  const run = useMutation({ mutationFn: () => modDueDiligence(lot.join('\n')) })
  const items = (run.data?.items ?? []) as Record<string, any>[]
  const iduxResolus = items.filter((i) => 'idu' in i).map((i) => i['idu'] as string)
  return (
    // O6(c) — le PANNEAU ENTIER scrolle : le wrapper d'outil (ModulePanel) est overflow-hidden, donc
    // M10 porte lui-même un unique conteneur défilant (flex-1 min-h-0 overflow-y-auto). Avant, seule la
    // liste des items scrollait et le bouton « Préparer les courriers » + le bas étaient coupés.
    <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
      <Banner>Passez plusieurs parcelles au crible d'un coup : risques, points de vigilance,
        propriétaire — parcelle par parcelle. Ajoutez-les en tapant une adresse ou un IDU dans la
        barre, ou en cliquant les parcelles sur la carte.</Banner>
      {/* BARRE UNIQUE (SOCLE) + « + Ajouter » → chips du lot */}
      <div className="flex flex-col gap-1.5 rounded-lg border border-line-2 bg-surface-2 px-2.5 py-2">
        {/* O6(b) — onPick ajoute l'IDU RÉSOLU ; onAddress (adresse sans parcelle rattachée) ne pousse
            JAMAIS la chaîne brute dans le lot : il affiche un message. Fin du chip « ELACITERNE,… ». */}
        <ParcelInput dataAttr="diligence-idu" placeholder="IDU, SECTION+NUMÉRO ou adresse — puis Entrée"
          onPick={ajouter}
          onAddress={() => setMsg("Cette adresse n'a pas de parcelle rattachée — saisissez un IDU ou cliquez la parcelle sur la carte.")} />
        {msg && <p data-diligence-msg className="text-[10.5px] leading-snug text-st-creuser">{msg}</p>}
        <details className="text-[10.5px] text-txt-dim">
          <summary className="cursor-pointer hover:text-txt-mut">ou collez une liste (une par ligne)</summary>
          <div className="mt-1.5 flex flex-col gap-1.5">
            <textarea data-diligence-paste value={paste} onChange={(e) => setPaste(e.target.value)} rows={3}
              placeholder={'97415000AC0253\nAC0254\nBK 63…'}
              className="rounded-lg border border-line-2 bg-surface-3 px-2 py-1.5 font-mono text-[10.5px] text-txt focus:border-mint focus:outline-none" />
            <button data-diligence-add onClick={ajouterListe} disabled={!paste.trim()}
              className="self-start rounded border border-mint/40 px-2 py-1 text-[11px] text-mint transition-colors duration-quick hover:bg-mint/10 disabled:opacity-40">+ Ajouter la liste</button>
          </div>
        </details>
      </div>

      {/* LA LISTE DU BAS — chips retirables (le lot en cours) */}
      {lot.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {lot.map((t) => (
            <span key={t} data-diligence-chip className="flex items-center gap-1.5 rounded-lg border border-mint/50 bg-surface-2 px-2 py-1 font-mono text-[10.5px] text-txt">
              {t.length >= 14 ? t.slice(8) : t}
              <button onClick={() => retirer(t)} className="text-txt-dim hover:text-st-ecartee" aria-label="Retirer">✕</button>
            </span>
          ))}
        </div>
      )}
      <p className="text-[10px] text-txt-dim">{lot.length} référence{lot.length > 1 ? 's' : ''} dans le lot.</p>

      <button data-diligence-analyser onClick={() => lot.length && run.mutate()} disabled={lot.length === 0 || run.isPending}
        className="rounded-lg bg-mint py-1.5 text-xs font-medium text-bg transition-[filter] duration-quick hover:brightness-110 disabled:opacity-40">
        {run.isPending ? 'Analyse…' : `Analyser le lot (${lot.length})`}
      </button>
      {run.data && (
        <>
          {/* O6(d) — compteur COHÉRENT : dérivé des items réellement renvoyés (trouvées = items avec IDU,
              demandées = nombre de lignes du résultat), plus des champs n_trouvees/n_demandes qui pouvaient
              diverger du lot affiché. « 5/7 » contre « 6 références » disparaît. */}
          <p className="text-[11px] text-txt-dim">{iduxResolus.length}/{items.length} référence{items.length > 1 ? 's' : ''} trouvée{iduxResolus.length > 1 ? 's' : ''}</p>
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
          <div className="flex flex-col gap-1.5">
            {items.map((i, k) => 'idu' in i ? (() => {
              const risque = i['risque'] as number
              const rColor = risque >= 100 ? TOKENS.stEcartee : risque >= 60 ? TOKENS.stEcartee : risque >= 30 ? TOKENS.stCreuser : TOKENS.mint
              const rLabel = risque >= 100 ? 'bloquant' : risque >= 60 ? 'élevé' : risque >= 30 ? 'modéré' : 'faible'
              const proprio = i['proprio'] as Record<string, any>
              const isPM = proprio['type'] === 'personne_morale'
              // PIEGES point 4 : la règle « age_dirigeant » (PM sans dirigeant physique daté) n'a de sens
              // que pour une PERSONNE MORALE — sur un particulier, la cascade émet un UNKNOWN hors sujet
              // (run précalculé, non rejouable ici) ; on le MASQUE à l'affichage. Fix côté présentation.
              const checklist = ((i['checklist'] ?? []) as Record<string, any>[])
                .filter((c) => isPM || c['layer'] !== 'age_dirigeant')
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
                {/* PIEGES point 3 : export PDF RETIRÉ (ni par parcelle, ni pour le lot) — l'analyse se lit ici. */}
              </div>
              )})() : (
              <div key={k} className="rounded-lg border border-st-ecartee/40 bg-st-ecartee/10 px-3 py-2 text-[11px] text-st-ecartee">
                {i['ref'] as string} — {i['erreur'] as string}
              </div>
            ))}
          </div>
          {/* PONT COURRIER (mandat COURRIER, addendum) : le lot analysé s'exporte vers l'outil Courrier
              pré-rempli — même canal que l'import Assemblage (courrierPrefillIdus). */}
          {iduxResolus.length > 0 && (
            <button data-diligence-courrier
              onClick={() => { setCourrierPrefillIdus(iduxResolus); setModule('courriers') }}
              className="rounded-lg border border-mint/50 bg-mint/10 py-1.5 text-[11px] font-medium text-mint transition-colors duration-quick hover:bg-mint/20">
              ✉ Préparer les courriers ({iduxResolus.length})
            </button>
          )}
        </>
      )}
    </div>
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
  // RETOURS-4 S7 — « patrimoine » ouvre l'outil FUSIONNÉ (onglets possède/construit) ; « veille-promoteurs »
  // (hidden au menu) redirige vers le MÊME outil, onglet « Ce qu'ils construisent » (redirection conservée).
  patrimoine: ScanPatrimoine, permis: M03, promesses: M03,
  'veille-promoteurs': () => <ScanPatrimoine defaultTab="construit" />,
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
  // ÉTUDE DE ZONE Z4 — l'outil de chalandise (isochrones IGN + INSEE/SIRENE/BPE).
  'etude-zone': EtudeZone,
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
  // K3 (rattrapage KelFoncier) — calculette « Taxe d'aménagement ». Marche à vide ; s'ouvre aussi
  // depuis une parcelle sélectionnée (getTaxePrefill : commune + zone en référence, surface saisie).
  'taxe-amenagement': TaxeAmenagement,
  // RETOURS-3 R5 — « Mon secteur » est hidden au menu (fusionné dans « Étudier un bien »), mais la clé
  // reste RÉSOLVANTE ici : deep-link/copilote historique ouvrent toujours l'outil autonome (redirection conservée).
  'mon-secteur': MonSecteur,   // SECTEUR-1 (S1)
  // 'veille-promoteurs' est mappé plus haut (→ ScanPatrimoine, onglet construit) — RETOURS-4 S7.
  // RADAR-CATÉGORIE (T1) — 'radar' n'est plus un module du panneau Outils : c'est la view 'radar'
  // (catégorie plein écran, RadarView). Ancien composant RadarClient supprimé.
}

// OUTILS-FIX-3 Lot D — fil de retour UNIQUE entre outils : rendu en tête de CHAQUE outil (un seul
// composant, un seul mécanisme = la pile `outilRetour`). N'apparaît QUE si l'outil a été ouvert par un
// pont FIX-2 (la pile est vidée à toute nav manuelle) ; le clic rouvre l'outil de DÉPART dans son état.
function RetourOutil() {
  const stack = useApp((s) => s.outilRetour)
  const retourOutil = useApp((s) => s.retourOutil)
  if (!stack.length) return null
  const top = stack[stack.length - 1]
  return (
    <button data-outil-retour onClick={retourOutil} title={`Revenir à ${top.label}`}
      className="hover-fill flex shrink-0 items-center gap-1.5 self-start rounded-lg border border-mint/40 bg-mint/10 px-2.5 py-1 text-[11px] font-medium text-mint transition-colors duration-quick">
      ← {top.label}
    </button>
  )
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
            {/* RETOURS-19 Y5 — infobulle « Revenir au menu Outils » retirée (le libellé le dit déjà).
                Y1 : l'indicateur « menu Outils ouvert » = l'entrée Outils du rail (vert opaque, `.rail-item.active`) ;
                ce fil d'Ariane est un RETOUR (jamais affiché quand le menu Outils est ouvert — ouvrir Outils
                démonte le panneau), gardé en pastille mint bordée. */}
            <button data-module-retour onClick={toggleOutils}
              className="flex shrink-0 items-center gap-1 rounded-md border border-mint/40 bg-mint/10 px-2.5 py-1 text-[11px] font-semibold tracking-wide text-mint transition-colors duration-quick hover:border-mint hover:bg-mint/15">
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
        <RetourOutil />
        <Body />
      </div>
    </aside>
  )
}
