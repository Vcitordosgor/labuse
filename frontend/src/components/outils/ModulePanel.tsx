import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Siren } from '../shared/Siren'   // RETOURS-12 T2 — SIREN cliquable Pappers
import { useEffect, useMemo, useState } from 'react'
import {
  courrierPdf, getCommunes, getCourrierDemandes, getCourrierStatut, getFiche, modBailleur,
  modDueDiligence, modFantome, modParcellePermis, modPatrimoine, modPermis, modPermisCount,
  modPermisFiche, modPromesses, modPromessesCount, modVelocite, postCourrierDemande, postCourrierAdressage,
  postCourrierComposer,
} from '../../lib/api'
import { AddressAutocomplete } from '../AddressAutocomplete'
import { ParcelInput } from '../ParcelInput'
import { TEMPS_MILLESIMES } from '../map/basemaps'
import { fmtInt } from '../../lib/format'
import { iduComplet, iduCourt, estIdu } from '../../lib/format'
import { permisIncoherenceNote } from '../../lib/permis'
import { pointInPolygon } from '../../lib/geo'
import { TOKENS } from '../../lib/tokens'
import { carteEtat, etatColor, type PermisEtat, type PermisEtatCarte } from '../../lib/permisEtats'
import { ChevronSection } from '../panel/ChevronSection'
import { useApp } from '../../store/useApp'
import { Squelette } from '../Loading'
import { EmptyState, ErrorState } from '../States'
import { CalculetteFonciere } from './CalculetteFonciere'
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
import { ProspectionSolaire } from './ProspectionSolaire'
import { EtudeZone } from './EtudeZone'
import { TaxeAmenagement } from './TaxeAmenagement'
import { Gabarit } from './Gabarit'   // GABARIT-1 — outil interne (registry hidden:true, flag admin)
import { MonSecteur } from './MonSecteur'   // SECTEUR-1 (S1) — outil « Mon secteur »
import { ScanPatrimoine } from './ScanPatrimoine'   // RETOURS-4 S7 — fusion Scan patrimoine (possède + construit)
import { OwnerParcelles } from '../OwnerParcelles'   // RECHERCHE-2 Lot 2 — sous-panneau propriétaire → ses parcelles
import { Successions } from './Successions'   // OUTILS-MUSCLER-1 Lot A — radar patrimonial servi en outil
import { Blocs } from './Blocs'   // OUTILS-MUSCLER-3 — assiettes contiguës d'un même propriétaire PM
import { TierBadge } from './TierBadge'
import { ListPaginationFooter, PAGE_SIZE } from '../ListPagination'
import { Bouton } from '../ui/Bouton'
import { Badge } from '../ui/Badge'   // KELFONCIER-FIX-2 (Lot D) — pastille d'état de permis (vert/rouge)
import { Retour } from '../ui/Retour'
import { Chevron } from '../ui/Chevron'
import { Chip } from '../ui/Chip'

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
// RECETTE-1 R8 — `right` (pastille de palier) devient FACULTATIF : les outils ne l'affichent plus.
function Row({ idu, right, sub, fiche, hoverFull }: { idu: string; right?: React.ReactNode; sub?: string; fiche?: [string, string][]; hoverFull?: boolean }) {
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
export function useModuleMap(idus: string[], extra: unknown | null, deps: unknown[]) {
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
    <Bouton niveau="secondaire" ton="vert" data-more onClick={() => q.fetchNextPage()} disabled={q.isFetchingNextPage}
      className="mt-1 min-h-8 shrink-0">
      {q.isFetchingNextPage ? 'Chargement…' : total != null ? `Voir plus — ${fmt(loaded)} / ${fmt(total)} chargés` : `Voir plus — ${fmt(loaded)} chargés`}
    </Bouton>
  )
}

/** M15-G — sélecteur de périmètre EXPLICITE : l'outil n'hérite plus du filtre commune global.
 *  `noteFiltre` (défaut vrai) affiche la mention « choisi ici — pas hérité du filtre global » ;
 *  Successions à venir la masque (OUTILS-MUSCLER-1B pt 5) — le comportement du filtre est inchangé. */
export function CommuneScope({ commune, onChange, noteFiltre = true }: { commune: string | null; onChange: (c: string | null) => void; noteFiltre?: boolean }) {
  const communes = useQuery({ queryKey: ['communes'], queryFn: getCommunes })
  return (
    <label className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-txt-mut">
      Périmètre
      <select data-commune-scope value={commune ?? ''} onChange={(e) => onChange(e.target.value || null)}
        className="rounded border border-line-2 bg-surface-3 px-1.5 py-0.5 text-txt focus:border-mint focus:outline-none">
        <option value="">Toute l'île</option>
        {(communes.data ?? []).map((c) => <option key={c.commune} value={c.commune}>{c.commune}</option>)}
      </select>
      {noteFiltre && <span className="text-[10px] text-txt-dim">choisi ici — pas hérité du filtre global</span>}
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
  // KELFONCIER-FIX-2 (Lot B) — les ponts Courrier (setCourrierPrefillIdus) et Comparer (addToCompare/
  // openCompare), le fil de retour (pushOutilRetour) et la sélection multiple (`sel`) ne servaient
  // qu'aux deux actions retirées du Scan patrimoine → supprimés ici. Ils restent portés par les
  // outils qui en ont besoin (Courrier, Comparateur), ailleurs dans le produit.
  const [sirenState, setSiren] = useState<string | null>(null)
  // RETOURS-12 O5 — le bandeau (nom + 3 chiffres + détail) est REPLIABLE en accordéon pour laisser
  // toute la place à la liste des parcelles (bug : la liste ne s'ouvrait pas, noyée sous le bandeau).
  const [bandeauReplie, setBandeauReplie] = useState(false)
  const siren = embedded ? (sirenProp ?? null) : sirenState
  useEffect(() => { setBandeauReplie(false) }, [siren])   // nouveau propriétaire → bandeau déplié
  useEffect(() => {
    // en mode embarqué, le SIREN vient de la fusion (sirenProp) — on ne consomme pas m02Prefill (pas de course).
    if (!embedded && m02Prefill) { setSiren(m02Prefill); setM02Prefill(null) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [m02Prefill, embedded])
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
      {/* RECHERCHE-2 Lot 2 (décision Vic) — la barre de recherche INTERNE de M02 (SIREN/nom, avec son
          typeahead maison) est RETIRÉE : c'était un doublon de l'outil Scan patrimoine (ParcelInput,
          4 familles) et elle était MORTE en production (le menu « patrimoine » rend ScanPatrimoine, qui
          embarque M02 SANS cette barre). M02 ne se pilote plus que par SIREN (fusion embarquée, ou pont
          m02Prefill). Sans SIREN → le message d'invite ci-dessous (la recherche vit dans la barre du haut). */}
      {!siren && <p className="text-[11px] leading-snug text-txt-dim">Cherchez un propriétaire (nom, SIREN/SIRET, IDU ou adresse) dans la barre du haut pour voir ce qu'il possède.</p>}
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
          {/* OUTILS-FIX-4 A1 — MILLÉSIME MAJIC en tête de l'onglet Possession : ces parcelles sont celles
              détenues d'après les fichiers fonciers DGFiP d'une année donnée — on la dit (fraîcheur), au
              même vocabulaire que le reste de l'app. Servi par la base (millesime_majic) ; jamais inventé. */}
          {d['millesime_majic'] && (
            <p data-m02-millesime className="text-[10px] text-txt-dim">Fichiers fonciers DGFiP · situation {String(d['millesime_majic'])}</p>
          )}
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
          {/* DONNEES-1 lot 2.3 — dépôts de comptes BODACC : un dépôt récent = société vivante ; un
              silence prolongé = société en sommeil (signal d'approche). Factuel. */}
          {d['depot_comptes'] != null && (
            <div data-m02-depot className="text-[10.5px] text-txt-dim">
              Dépôt de comptes — {(() => {
                const dc = d['depot_comptes'] as { annee: number | null; depuis_ans: number | null }
                if (dc.depuis_ans != null && dc.depuis_ans >= 3) return `aucun dépôt depuis ${dc.depuis_ans} ans (société en sommeil probable)`
                return `dernier exercice déposé : ${dc.annee ?? '—'}`
              })()}
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
              {/* RETOURS-15 B5 (P10) — 4 chiffres FACTUELS et sourcés pour notaires / agences / apporteurs /
                  architectes (plus « actionnables » ni « valorisation », qui parlaient au promoteur). La SDP
                  résiduelle n'est plus un chiffre-titre : elle reste visible parcelle par parcelle dans la liste. */}
              <div className="grid grid-cols-2 gap-2">
                {[
                  { v: fmt(d['n_parcelles'] as number), lbl: 'parcelles' },
                  { v: `${(((d['surface_totale_m2'] as number) ?? 0) / 1e4).toLocaleString('fr-FR', { maximumFractionDigits: 1 })} ha`, lbl: 'surface totale' },
                  { v: `${fmt(d['n_terrains_nus'] as number)} / ${fmt(d['n_terrains_batis'] as number)}`, lbl: 'terrains nus / bâtis' },
                  { v: fmt(d['n_constructible_u_au'] as number), lbl: 'en zone U ou AU' },
                ].map((c) => (
                  <div key={c.lbl} data-m02-kpi className="min-w-0 rounded-lg border border-line-2 bg-surface-2 px-2.5 py-2.5">
                    <div className="num-key whitespace-nowrap text-[16px] tabular-nums text-mint">{c.v}</div>
                    <div className="mt-0.5 text-[10px] leading-tight text-txt-mut">{c.lbl}</div>
                  </div>
                ))}
              </div>
            </>
          )}
          {/* RETOURS-15 C9 — pont Blocs fonciers : les GROUPES de parcelles contiguës du propriétaire
              (même moteur que l'outil Blocs, table parcel_blocs). Ligne « Blocs contigus : N » + les
              groupes cliquables (→ fiche de leur parcelle représentative). */}
          {(() => {
            const bc = d['blocs_contigus'] as { n: number; items: { bloc_id: number; n_parcelles: number; surface_m2: number; communes: string[]; sdp_residuelle_m2: number; idu_repr: string | null }[] } | undefined
            if (!bc || bc.n === 0) return null
            return (
              <div data-m02-blocs className="rounded-lg border border-line-2 bg-surface-2 px-2.5 py-1.5">
                <div className="text-[11px] font-medium text-txt-mut">Blocs contigus : <b className="text-txt">{fmt(bc.n)}</b></div>
                <div className="mt-1 flex flex-col gap-0.5">
                  {bc.items.map((bl) => (
                    <button key={bl.bloc_id} data-m02-bloc
                      onClick={() => bl.idu_repr && useApp.getState().focusParcelle(bl.idu_repr, { fiche: true })}
                      className="hover-fill flex items-baseline justify-between gap-2 rounded px-1.5 py-0.5 text-left text-[10.5px] text-txt-mut transition-colors duration-quick">
                      <span><b className="text-txt">{fmt(bl.n_parcelles)}</b> parcelles · {(bl.communes ?? []).join(', ')}</span>
                      <span className="tnum shrink-0 text-txt-dim">{fmt(bl.surface_m2)} m²</span>
                    </button>
                  ))}
                </div>
              </div>
            )
          })()}
          {/* RETOURS-12 O5 — en fusion (ScanPatrimoine), « Voir ses parcelles → » REPLIE le bandeau pour
              ouvrir la liste (les opérations restent dans l'onglet « Construction »). Hors fusion (M02
              seul), le pont historique « Voir ses opérations → » vers Veille promoteurs est conservé. */}
          {d['siren'] != null && (embedded ? (
            !bandeauReplie && (
              <Bouton niveau="secondaire" ton="vert" data-scan-voir-parcelles onClick={() => setBandeauReplie(true)} className="w-full">
                Voir ses parcelles →</Bouton>
            )
          ) : (
            <Bouton niveau="secondaire" ton="vert" data-m02-operations
              onClick={() => { const s = String(d['siren']); setVeilleFocusSiren(s); setModule('veille-promoteurs') }}
              className="w-full">
              Voir ses opérations →</Bouton>
          ))}
          {/* liste — RETOURS-5 T4.5 : lignes en survol plein (hoverFull).
              RETOURS-13 R18 — en fusion, UN SEUL ÉTAT à la fois : au chargement la liste est
              REPLIÉE (bandeau déplié + bouton « Voir ses parcelles → ») ; le clic replie le
              bandeau ET ouvre la liste. Plus de doublon bouton + liste déjà affichée. */}
          {(!embedded || bandeauReplie) && (<>
          {/* KELFONCIER-FIX-2 (Lot B) — les deux actions « ✉ Préparer les courriers » et « Comparer »
              sont RETIRÉES du Scan patrimoine (l'outil observe, il ne démarche pas). La sélection
              multiple (cases) ne servait QU'à ces deux ponts → retirée aussi (plus de case morte).
              Les composants (Courrier, Comparateur) et leurs endpoints restent, joignables ailleurs. */}
          <div className="flex min-h-0 flex-1 flex-col gap-1.5 overflow-y-auto">
            {items.map((i) => {
              const idu = i['idu'] as string
              return (
              <div key={idu} className="min-w-0">
                {/* RECETTE-1 R8 — pastille de palier (scoring q_v14) retirée du Scan patrimoine. */}
                {/* KELFONCIER-FIX-1 (Lot H) — « occupé par N établissements » (SIRENE rattaché par
                    l'adresse BAN, même source que la fiche §3). Silencieux si 0. */}
                <Row idu={idu} hoverFull
                  sub={`${i['commune']} · ${fmt(i['surface_m2'] as number)} m² · SDP ${fmt(i['sdp'] as number)}`
                    + (Number(i['n_etablissements']) > 0 ? ` · occupé par ${fmt(i['n_etablissements'] as number)} établissement${Number(i['n_etablissements']) > 1 ? 's' : ''}` : '')}
                  fiche={[['Propriétaire', String(d['nom'])], ['SIREN', String(d['siren'])],
                    ['Patrimoine', `${d['n_parcelles']} parcelles · SDP résiduelle ${fmt(d['sdp_residuelle_m2'] as number)} m²`]]} />
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
        {q.isLoading && <Squelette lignes={5} />}
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
            {/* KELFONCIER-FIX-2 (Lot D) — statut en pastille (rouge si annulé, vert sinon), même
                fonction que la fiche (etat_libelle/annule servis par /permis/{id}). */}
            <F label="Statut" value={d['statut'] ? <Badge ton={d['annule'] ? 'rouge' : 'vert'}>{String(d['statut'])}</Badge> : null} />
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
              <Bouton niveau="secondaire" ton="vert" data-permis-scan-patrimoine
                onClick={() => { setM02Prefill(String(d['porteur_siren']).replace(/\D/g, '').slice(0, 9)); setModule('patrimoine'); onClose(); pushOutilRetour({ module: 'permis', label: 'Permis', restore: { permitToOpen: permitId } }) }}
                className="mt-1.5 w-full">
                Scan patrimoine du porteur →</Bouton>
            )}
            <F label="Nombre de lots" value={d['nb_lots']} />
            <F label="Surface habitable" value={d['surface_hab_m2'] != null ? `${fmt(d['surface_hab_m2'])} m²` : null} />
            {d['geoloc_note'] && <p className="mt-1 text-[10px] leading-snug text-txt-dim">Position : {String(d['geoloc_note'])}.</p>}
            <F label="Date de dépôt" value={d['date_depot']} />
            <F label="Date d'autorisation" value={d['date_autorisation']} />
            {/* DONNEES-6/7 — dates JAMAIS réordonnées : dépôt après autorisation = incohérence du
                producteur SDES/Dido, qualifiée par l'écart (au-delà d'1 mois = modificatif/transféré
                probable). Le délai d'instruction reste non servi. Voir lib/permis.ts. */}
            {(() => {
              const note = permisIncoherenceNote(d['date_depot'] as string | null, d['date_autorisation'] as string | null)
              return note ? <p className="mt-1 text-[10px] leading-snug text-st-ecartee">{note} — délai d'instruction non calculé.</p> : null
            })()}
            <F label="Achèvement (DAACT)" value={d['date_achevement']} />
            {d['delai_instruction'] && (
              <F label="Délai d'instruction" value={<span className="font-semibold text-mint">{d['delai_instruction']['libelle']}</span>} />
            )}
            <F label="Parcelle(s)" value={<span className="font-mono text-[10px]">{(d['parcelles'] as string[]).join(', ')}</span>} />
            {/* Fix LOT 2 : localiser la parcelle sur la carte (géocodé) ou message clair (non géocodé) —
                jamais un clic mort. La géom d'un permis = centroïde de la parcelle rattachée. */}
            {geom?.coordinates ? (
              <Bouton niveau="secondaire" ton="vert" data-permis-localiser onClick={localiser} className="mt-3 w-full">
                ◎ Voir la parcelle sur la carte
              </Bouton>
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
  const select = useApp((s) => s.select)   // PERMIS-CHECK-2 pt 2 — lever une fiche stale avant de focus
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
  // base : date du millésime, lue du compteur « Tous » (PERMIS-CHECK-1 P4 : la ligne « … localisés »
  // du bloc total est retirée ; `baseJusquAu` sert encore la coupure 24 mois `cut24`).
  const baseJusquAu = qTousEntry.data?.donnees_jusqu_au
  const setPermitHover = useApp((s) => s.setPermitHover)
  useEffect(() => () => setPermitHover(null), [setPermitHover])   // nettoyage au démontage

  // O17 (g) — RECHERCHE PAR PARCELLE : un IDU complet (14 car.) saisi dans la barre, OU une adresse/
  // parcelle choisie dans le suggest, interroge /modules/parcelle-permis. On distingue un IDU (14 car.)
  // d'un n° de permis Sitadel (chaîne alphanumérique plus courte) sur la longueur — un seul champ, deux sens.
  // PERMIS-CHECK-1 P2 — avant, une parcelle SANS permis ne montrait rien d'utile et une parcelle AVEC
  // permis ouvrait d'office le 1er permis (l'utilisateur ne voyait pas le compte). Désormais on affiche
  // TOUJOURS une phrase de résultat (0 / X permis) et on laisse le client cliquer les points sur la carte.
  const [parcelIdu, setParcelIdu] = useState<string | null>(null)
  // RETOURS-15 B1 — le bloc « N permis à moins de 200 m… » est un ACCORDÉON repliable, ouvert par défaut.
  const [resProximiteOuvert, setResProximiteOuvert] = useState(true)
  // RECHERCHE-2 Lot 2 — propriétaire choisi dans la barre permis → sous-panneau de ses parcelles.
  const [permisOwner, setPermisOwner] = useState<{ siren: string; nom: string } | null>(null)
  const qParcelPermis = useQuery({ queryKey: ['parcelle-permis-search', parcelIdu],
    queryFn: () => modParcellePermis(parcelIdu!), enabled: !!parcelIdu })
  // date du millésime Sitadel servi — lue du compteur radar (fenêtre 24 m, TOUJOURS actif).
  const donneesJusquAu = (qRadarEntry.data as Record<string, any> | undefined)?.['donnees_jusqu_au'] as string | undefined

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
  // PERMIS-CHECK-2 pt 1 — parcelle CIBLÉE : la carte montre EXACTEMENT les permis de la parcelle
  // (/modules/parcelle-permis, ≤ 200 m, géolocalisés), INDÉPENDAMMENT du filtre d'état — sinon la
  // phrase « X permis » comptait la proximité (tous états) mais la carte ne peignait que le radar filtré
  // (constat BZ1065 : 11 permis annoncés, 0 point car tous > 24 mois et « Récent » actif). Couleur =
  // récence PROPRE du permis (récent ≤ 24 m vert, sinon gris), jamais le segment. Ces permis portent
  // `nature` (pas `type`) → feature dédiée. Hors ciblage, la carte garde le radar/point mort habituel.
  const parcelPermisItems = (parcelIdu
    ? (((qParcelPermis.data as Record<string, any> | undefined)?.['items'] ?? []) as Record<string, any>[])
    : []).filter((i) => i['geom'])
  const featParcelle = (i: Record<string, any>) => ({ type: 'Feature' as const, geometry: i['geom'],
    properties: { kind: 'permis', etat: (String(i['date'] ?? '') >= cut24 ? 'recent' : 'gris') as PermisEtatCarte,
      permit_id: i['permit_id'], label: `${i['nature'] ?? ''} ${i['date']}`.trim() } })
  useModuleMap([],
    // W3 — `etat` (recent|dormant|gris) voyage dans les properties ; la carte peint depuis la MÊME source
    // de couleurs que les pastilles (lib/permisEtats). En « Tous », le corail dormant est posé APRÈS le
    // gris/vert → il prime visuellement (un PC dormant reste corail même sous un point gris).
    featureCollection(parcelIdu
      ? parcelPermisItems.map(featParcelle)
      : [...carteRadar.map((i) => _feat(i, carteEtat(radarEtat(i)))), ...cartePm.map((i) => _feat(i, 'dormant'))]),
    // O17 (i) — `geoFiltre` en dép. : le filtre géocodage resynchronise la carte avec la liste.
    // pt 1 — `parcelIdu`/données en dép. : cibler une parcelle bascule la carte sur ses permis.
    [seg, pointMort, tous, qRadar.dataUpdatedAt, qPm.dataUpdatedAt, zone, geoFiltre, parcelIdu, qParcelPermis.dataUpdatedAt])
  const total = pointMort ? qPmCount.data?.total : ((head?.['total'] as number) ?? 0)
  const loaded = pages.flatMap((p) => (p['items'] ?? []) as unknown[]).length

  // RETOURS-18 X1 — les cinq états (Tous + 4 partition), source unique du rendu ET des résumés d'accordéon.
  // DA-FIX-4 verif (task 1) — « Tous » TOUJOURS en dernier à droite (charte 5.2 / RETOURS-15 U3).
  const ETATS = [
    ['cours', 'Récent', 'recent', radarEntryTotal, 'autorisé ≤ 24 mois'],
    ['mort', 'Dormant', 'dormant', pmEntryTotal, 'ancien PC sans achèvement'],
    ['acheve', 'Achevés', 'acheve', acheveEntryTotal, 'travaux déclarés (DAACT)'],
    ['autre', 'Autres', 'autre', autreEntryTotal, 'ni récent, ni dormant, ni achevé'],
    ['tous', 'Tous', null, tousEntryTotal, 'toute la base'],
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
          // RECHERCHE-2 Lot 2 — + PROPRIÉTAIRE / SIREN : un pick propriétaire déroule ses parcelles
          // (sous-panneau partagé) ; en choisir une CIBLE la parcelle et cherche ses permis (comme un IDU).
          grammaires={['adresse', 'cadastre', 'commune', 'proprietaire', 'siren']}
          onPick={(it) => {
            if (it.type === 'commune' && it.commune) setCommune(it.commune)
            else if ((it.type === 'proprietaire' || it.type === 'siren') && it.siren) setPermisOwner({ siren: it.siren, nom: it.label })
          }}
          // PERMIS-CHECK-1 P2 — choisir une adresse/parcelle dans le suggest CIBLE la parcelle (zoom +
          // délimitation) ET déclenche la recherche de ses permis → phrase de résultat (0 / X), comme un
          // IDU saisi. Avant, un choix de suggestion recadrait la carte SANS jamais dire s'il y a un permis.
          // PERMIS-CHECK-2 pt 2 — `select(null)` AVANT focusParcelle : la carte cible `selectedIdu ?? focusIdu`
          // (MapView) ; si une fiche est restée ouverte sur une parcelle A (clic carte/liste), elle MASQUAIT
          // le focus B demandé ici → la carte ne bougeait pas (constat Vic). On lève la sélection stale pour
          // que la barre RECENTRE TOUJOURS sur la parcelle choisie, qu'une fiche soit ouverte ou non.
          onSelect={(sel) => { if (sel.idu) { const c = iduComplet(sel.idu); select(null); focusParcelle(c); setParcelIdu(c) } else setFlyTo({ center: [sel.lon, sel.lat], zoom: 15 }) }}
          // RETOURS-15 B1 — « le mot effacer disparaît ; vider le champ suffit » : vider la barre lève la
          // parcelle ciblée (et donc le bloc de proximité et les points de la carte).
          onClear={() => setParcelIdu(null)}
          onEnterRaw={(t) => {
            const v = iduComplet(t)
            // RETOURS-12 O12.2 — IDU cadastral complet (14 car.) → la carte ZOOME et DÉLIMITE la parcelle
            // (focusParcelle, même geste que O1/J1) EN PLUS de chercher ses permis (O17 g).
            // pt 2 — `select(null)` d'abord : le focus barre prime sur une fiche stale (cf. onSelect).
            if (v.length === 14 && estIdu(v)) { select(null); focusParcelle(v); setParcelIdu(v); return }
            // sinon une référence Sitadel compacte → fiche permis
            if (/^[0-9][0-9a-z]{6,}$/i.test(v)) setOpen(v)
          }} />
        {/* RECHERCHE-2 Lot 2 — propriétaire → ses parcelles ; en choisir une cible la parcelle (zoom +
            délimitation) et cherche ses permis, exactement comme un IDU saisi. */}
        {permisOwner && (
          <div className="mt-1.5">
            <OwnerParcelles siren={permisOwner.siren} nom={permisOwner.nom}
              onPick={(idu) => { const c = iduComplet(idu); select(null); focusParcelle(c); setParcelIdu(c); setPermisOwner(null) }}
              onChanger={() => setPermisOwner(null)} />
          </div>
        )}
        {/* PERMIS-CHECK-1 P2 — parcelle CIBLÉE : phrase de résultat, TOUJOURS affichée. Le compte vient de
            /modules/parcelle-permis (permis autorisés géolocalisés ≤ 200 m, source du signal viabilisation),
            non fenêtré → N = profondeur MAX de l'outil (max(MONTHS_RADAR) = 240 m = toute la profondeur
            Sitadel servie). 0 → phrase honnête datée ; ≥ 1 → le compte, puis le client clique les points. */}
        {parcelIdu && qParcelPermis.data && (() => {
          // PERMIS-CHECK-2 pt 1 — le compte affiché = les permis DESSINABLES (avec géom), pour que la
          // phrase et la carte ne se contredisent jamais : « X permis » ⇒ X points cliquables à l'écran.
          // La source ne renvoie que du géolocalisé ≤ 200 m ; `nonLoc` (rare) est dit à part. Le libellé
          // dit « à moins de 200 m » (et non « sur cette parcelle ») : ce sont les permis du voisinage
          // ≤ 200 m — la même assiette que le signal viabilisation (constat BZ1065 : 0 permis LITTÉRALEMENT
          // sur la parcelle, 11 dans les 200 m).
          const items = (((qParcelPermis.data as Record<string, any>)['items'] ?? []) as Record<string, any>[])
          const loc = items.filter((i) => i['geom']).length
          const nonLoc = items.length - loc
          const nonLocTxt = nonLoc > 0 ? ` (${fmt(nonLoc)} non localisé${nonLoc > 1 ? 's' : ''}, sans point sur la carte)` : ''
          const vide = items.length === 0
          const ton = loc === 0 ? 'border-st-creuser/40 bg-st-creuser/10 text-st-creuser' : 'border-mint/50 bg-mint/10 text-mint'
          // RETOURS-15 B1 — ACCORDÉON (Chevron de la charte), ouvert par défaut, repliable. En-tête =
          // le compte (toujours visible) ; corps repliable = le détail « cliquez les points ». Plus de
          // lien « effacer » (vider le champ suffit → onClear).
          const titre = vide
            ? <>Aucun permis à moins de 200 m de <span className="font-mono">{iduCourt(parcelIdu)}</span></>
            : loc === 0
              ? <><b className="tnum">{fmt(nonLoc)}</b> permis à moins de 200 m de <span className="font-mono">{iduCourt(parcelIdu)}</span>, non localisés</>
              : <><b className="tnum">{fmt(loc)}</b> permis à moins de 200 m de <span className="font-mono">{iduCourt(parcelIdu)}</span></>
          return (
            <div data-permis-parcelle-resultat {...(loc === 0 ? { 'data-permis-parcelle-vide': '1' } : {})}
              className={`mt-1 rounded-lg border text-[11px] leading-snug ${ton}`}>
              <button type="button" data-permis-proximite-toggle onClick={() => setResProximiteOuvert((o) => !o)}
                className="flex w-full items-center gap-2 px-3 py-2 text-left">
                <Chevron open={resProximiteOuvert} />
                <span className="min-w-0 flex-1">{titre}</span>
              </button>
              {resProximiteOuvert && (
                <div className="-mt-0.5 px-3 pb-2 pl-[30px]">
                  {vide
                    ? <>sur les {Math.max(...MONTHS_RADAR)} derniers mois{donneesJusquAu ? ` (Sitadel au ${donneesJusquAu})` : ''}.</>
                    : loc === 0
                      ? <>aucun point à afficher.</>
                      : <>cliquez les points sur la carte{nonLocTxt}.</>}
                </div>
              )}
            </div>
          )
        })()}
      </div>

      {/* RETOURS-17 W2 — BLOC TOTAL en tête : le total sort des chips (constat Vic 05/09 : « 50k » lu
          comme une part alors que c'est le total). Nombre 24px + « permis autorisés en base ».
          PERMIS-CHECK-1 P4 — la 2e ligne (« … localisés sur la carte · toute la profondeur Sitadel,
          jusqu'au … ») est RETIRÉE (constat Vic) : le total et la mention Sitadel ci-dessous suffisent. */}
      <div data-permis-total className="shrink-0 rounded-lg border border-line-2 bg-surface-1 px-3 py-2">
        <div className="flex items-baseline gap-2">
          <span className="tnum text-[24px] font-semibold leading-none text-txt-hi">{tousEntryTotal != null ? fmt(tousEntryTotal) : '…'}</span>
          <span className="text-[12px] text-txt-mut">permis autorisés en base</span>
        </div>
      </div>

      {/* RETOURS-18 X1 — bandeau Sitadel PERMANENT. RETOURS-19 Y5 — tient sur UNE ligne (phrase resserrée
          + `whitespace-nowrap`) ; `overflow-hidden`/ellipse en garde-fou : la section ne défile JAMAIS
          latéralement (l'infobulle porte la phrase entière si jamais elle était tronquée). */}
      <p className="shrink-0 -mt-0.5 truncate px-0.5 text-[9.5px] leading-snug text-txt-dim">
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
                  ? <> · <span data-permis-plafond>les {fmt(loaded)} plus anciens chargés — zoomez pour affiner</span></> : ''}</>
              : <>{fmt(carteRadar.length)} sur la carte
                  {total != null && loaded < total ? <> · {fmt(loaded)} / {fmt(total)} chargés</> : null}</>}
            {zone && <span className="text-mint/70"> · {items.length} dans la zone dessinée</span>}
          </p>

          {pointMort && qPm.isLoading && <Squelette bloc className="py-8" />}

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
            <span className="h-[7px] w-[7px] shrink-0 rounded-full" style={{ background: etatColor(et) }} aria-label={etTitre} />
            {/* KELFONCIER-FIX-2 (Lot D) — le TYPE (PC / PA / DP) est TOUJOURS dans le libellé (même en
                mode Dormant, où il vaut « PC ») : le mandat le demande explicitement, et c'est cohérent
                avec la pastille d'état à droite. */}
            <span className="shrink-0 rounded border border-line-2 px-1.5 py-0.5 font-mono text-[10px] text-txt-hi">{i['type'] as string}</span>
            {/* O17 (h) — DATE = date réelle d'autorisation du permis (par ligne), PAS la date du fichier. */}
            <span className="shrink-0 font-mono text-txt-mut">{i['date'] as string}</span>
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
              {!i['geom'] && <span data-permis-badge-nongeo className="whitespace-nowrap rounded-full bg-st-creuser/15 px-1.5 py-0.5 text-[9px] font-medium text-st-creuser">
                {i['geoloc'] ? 'approx. (adresse)' : 'non localisé'}</span>}
              {!pointMort && i['delai_mois'] != null && <span style={{ color: VIOLET }}>{String(i['delai_mois'])} m</span>}
              {pointMort
                ? <span data-permis-badge-mort className="whitespace-nowrap rounded-full bg-st-ecartee/15 px-1.5 py-0.5 text-[9px] font-medium text-st-ecartee">Sans DAACT{ans != null ? ` · ${ans} an${ans > 1 ? 's' : ''}` : ''}</span>
                /* KELFONCIER-FIX-2 (Lot D) — pastille d'état par la MÊME fonction que la fiche
                   (etat_libelle/annule servis par /permis) : annulé → rouge, autorisé / travaux
                   commencés / achevés → vert. Absent (dormant / non servi) : pas de pastille. */
                : i['etat_libelle'] && <Badge data-permis-etat ton={i['annule'] ? 'rouge' : 'vert'}>{i['etat_libelle'] as string}</Badge>}
            </span>
          </button>
          )
        })}
        {/* O17 (i) — ÉTAT VIDE : message clair quand aucun permis ne correspond aux filtres. */}
        {!q.isLoading && items.length === 0 && (
          <div data-permis-vide>
            <EmptyState title={`Aucun permis ne correspond aux filtres${commune ? ` pour ${commune}` : ''}${zone ? ' dans la zone dessinée' : ''}.`}
              hint="Élargissez la période ou effacez un filtre." />
          </div>
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
        {/* OUTILS-FIX-3 Lot E — lien ⬇ CSV (/modules/velocite?fmt=csv) retiré côté écran ; l'endpoint back reste. */}
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
            <div key={c['commune'] as string} className="grid grid-cols-[1fr_64px_60px] gap-1 border-b border-line py-1.5 text-[11px]">
              <span className="flex min-w-0 items-center gap-1.5 truncate text-txt">
                {rang != null && <span className="shrink-0 font-mono text-[9px]" style={{ color: rgColor }}>#{rang}</span>}
                <span className="truncate">{c['commune'] as string}</span>
                {tIcon && <span className="shrink-0" style={{ color: tColor }} aria-label={`Tendance ${tend}`}>{tIcon}</span>}
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
      {q.isLoading && <Squelette bloc className="py-8" />}
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
  const { cmpLeft, setCmpLeft, setCmpRight, parcelPrefill, setParcelPrefill, setFlyTo, setTempsPinIdu } = useApp()
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

  // DA-FIX-2 Lot 2 (DA-004) — OMNIBOX PERMANENTE : le champ « désigner la parcelle » reste EN TÊTE,
  // même une fois la parcelle choisie (plus de bandeau + « changer » qui la masquaient). La frise des
  // millésimes apparaît DESSOUS dès qu'une parcelle est désignée ; changer de parcelle = retaper.
  return (
    <>
      <Banner>La <b>parcelle d'abord</b> : son IDU, une adresse, ou <b>cliquez-la sur la carte</b>. Puis
        choisissez l'année à revoir — l'« après » est toujours aujourd'hui.</Banner>
      <div className="flex flex-col gap-2 rounded-lg border border-line-2 bg-surface-2 p-3">
        <p className="label-caps text-[9.5px]">Quelle parcelle voir évoluer ?</p>
        {/* PATRON OMNIBOX (M137) — adresse OU IDU dans le même champ, via ParcelInput partagé */}
        <ParcelInput dataAttr="temps-idu" placeholder="Adresse, IDU ou référence (BW0917)"
          onPick={(id) => void designer(id)} />
      </div>
      {!idu ? (
        <p className="text-[11px] text-txt-mut">Accès direct depuis toute fiche : bouton « 1950 ».</p>
      ) : (
      <div className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2.5">
        <p className="label-caps text-[9.5px]">L'année à revoir (avant)</p>
        {/* RETOURS-15 C2 (P16) — une rangée de Chip par millésime (lisible, sans troncature : flex-wrap),
            le millésime actif en vert plein (Chip on). « Aujourd'hui » est la borne « après » verrouillée. */}
        <div data-temps-frise className="mt-2 flex flex-wrap gap-1.5">
          {TEMPS_MILLESIMES.map((m) => {
            // libellé COURT : « 1950 », « 1980 », « 2000 »… ; les cartes anciennes (SCAN 50 / EduGéo)
            // gardent leur année + « (carte) » pour ne pas se confondre avec l'ortho de la même décennie.
            const carte = m.an.startsWith('scan') || m.an.startsWith('edugeo')
            const court = m.an.replace('scan', '').replace('edugeo', '')
            return (
              <Chip key={m.key} data-cmp-left={m.key} on={cmpLeft === m.key} ton="vert"
                aria-label={m.label} onClick={() => setCmpLeft(m.key)}>
                {court}{carte ? ' (carte)' : ''}
              </Chip>
            )
          })}
          <Chip data-cmp-aujourdhui on disabled ton="vert" aria-label="Aujourd'hui (verrouillé)">Aujourd'hui</Chip>
        </div>
        <p className="mt-2 text-[11px] text-txt">
          <span className="text-mint">{TEMPS_MILLESIMES.find((m) => m.key === cmpLeft)?.label ?? '—'}</span>
          <span className="text-txt-dim"> vs </span>Aujourd'hui{/* F7 (OUTILS-3) — mention « 🔒 après fixe » retirée : sans sens pour le client. */}
        </p>
        <p className="mt-2 text-[10.5px] text-txt-dim">Glissez la poignée au centre de la carte pour révéler l'un ou l'autre.</p>
      </div>
      )}
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
// RECETTE-5 (V22, décision Vic) — LE FOND DU COURRIER RÉÉCRIT. Cette lettre part dans une boîte aux
// lettres et doit donner envie de répondre. Structure gravée, dans cet ordre :
//   1. QUI ÉCRIT — LABUSE, l'outil d'intelligence foncière de La Réunion (une phrase, sans jargon, qui
//      rassure sur le sérieux ; le nom LABUSE est VISIBLE — c'est ce qui donne une raison de répondre) ;
//   2. POURQUOI CETTE PARCELLE — une raison concrète et vraie, portée par le modèle choisi (potentiel
//      restant / secteur qui bouge / projet à proximité). L'émetteur choisit le modèle qui correspond au
//      fait ; jamais une raison inventée ;
//   3. CE QU'ON PROPOSE — une étude gratuite de sa parcelle, ou simplement un échange. Sans engagement,
//      y compris s'il ne vend pas ;
//   4. COMMENT RÉPONDRE — par mail à victor@labuse.immo, expert LABUSE.
// Ton : posé, respectueux, jamais commercial agressif. La mise en page reste celle de la DA.
// COURRIER-2 Lot 3 — les anciens gabarits ({parcelle}, « potentiel »/« valorisation ») sont RETIRÉS :
// la lettre est composée serveur (ouverture A→E sur les faits), même texte que le PDF. « Ne pas
// reformuler » (Vic). `remplirGabaritCourrier` (substitution pure, sans champ vide) reste exportée
// pour ses tests, mais n'est plus branchée dans le flux M09.
type Dest = { idu: string; commune: string; surface: number | null }

// OUTILS-S2 Lot B — montant TTC avec les centimes (tarif courrier 4,04 € l'unité), virgule décimale FR.
const fmtEur2 = (n: number) => `${n.toFixed(2).replace('.', ',')} €`

// RECETTE-2 (S8) — substitution PURE d'un gabarit de courrier, exportée pour être verrouillée par test.
// RÈGLE : un champ vide ne s'imprime JAMAIS (ni « — », ni « (—) », ni « à — ») dans une lettre qui part
// dans une boîte aux lettres. Commune/surface absente → le SEGMENT entier disparaît, la phrase se
// reformule sans lui. Les gabarits restent lisibles à l'écriture (aucun marqueur).
export function remplirGabaritCourrier(tpl: string, parcelleCourt: string, commune: string, surfaceTxt: string): string {
  const rep = (s: string, a: string, b: string) => s.split(a).join(b)
  let s = rep(tpl, '{parcelle}', parcelleCourt)
  s = rep(s, ' ({surface})', surfaceTxt ? ` (${surfaceTxt})` : '')
  s = rep(s, '({surface})', surfaceTxt ? `(${surfaceTxt})` : '')
  s = rep(s, '{surface}', surfaceTxt)
  if (commune) {
    s = rep(s, '{commune}', commune)
  } else {
    for (const pat of [', située à {commune}', ', à {commune}', ' située à {commune}', ' à {commune}', '{commune}'])
      s = rep(s, pat, '')
  }
  return s
    .replace(/\(\s*\)/g, '')
    .replace(/ {2,}/g, ' ')
    .replace(/ +([,.])/g, '$1')
    .replace(/,\s*,/g, ',')
    .replace(/ +\n/g, '\n')
}
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
  const [modele, setModele] = useState('auto')
  const [corps, setCorps] = useState('')
  const [demande, setDemande] = useState<{ id: number; rang_compte?: number; statut: string; n: number; communes: string | null } | null>(null)
  const [pdfBusy, setPdfBusy] = useState(false)
  const [pdfErr, setPdfErr] = useState<string | null>(null)
  // OUTILS-S2 Lot B — un pli « à l'occupant » n'atteint personne sur un terrain nu ou sans adresse :
  // l'ajout est REFUSÉ et l'on renvoie au Courrier SPF (identification du propriétaire via la fiche).
  const [ajoutBloque, setAjoutBloque] = useState<{ idu: string; code: string; motif: string } | null>(null)
  const select = useApp((s) => s.select)

  // Enrichit commune + surface depuis la fiche (cache partagé) une fois le destinataire retenu.
  const _enrichir = (id: string) => {
    setDest((prev) => prev.some((d) => d.idu === id) ? prev : [...prev, { idu: id, commune: '', surface: null }])
    qc.fetchQuery({ queryKey: ['fiche', id], queryFn: () => getFiche(id) })
      .then((f) => setDest((prev) => prev.map((d) => d.idu === id ? { ...d, commune: f.commune, surface: f.surface_m2 } : d)))
      .catch(() => { /* parcelle introuvable : la chip reste, commune inconnue (jamais inventée) */ })
  }
  // Ajoute un destinataire (dédupliqué). OUTILS-S2 Lot B : on résout d'abord l'adressabilité ; un
  // terrain nu / sans adresse (aucun occupant joignable) bloque l'ajout avec un message + renvoi SPF.
  // L'opposition n'est PAS bloquée ici (traitée au dépôt, étape 3). Adressage indisponible → repli : on
  // ajoute sans blocage (jamais un faux blocage sur une panne réseau).
  const AJOUT_REFUSE = new Set(['nu', 'sans_adresse', 'sans_canal', 'inconnue'])
  const ajouter = (raw: string) => {
    const id = iduComplet(raw).toUpperCase()
    if (id.length < 10 || dest.some((d) => d.idu === id)) return
    setAjoutBloque(null)
    postCourrierAdressage([id])
      .then((r) => {
        const res = r.resolutions[0]
        if (res?.bloque && res.code && AJOUT_REFUSE.has(res.code)) {
          setAjoutBloque({ idu: id, code: res.code, motif: res.motif ?? '' })
        } else _enrichir(id)
      })
      .catch(() => _enrichir(id))
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

  const recapCommunes = () => {
    const c: Record<string, number> = {}
    dest.forEach((d) => { const k = d.commune || '—'; c[k] = (c[k] || 0) + 1 })
    return Object.entries(c).map(([k, n]) => `${k} ×${n}`).join(' · ')
  }

  // OUTILS-FIX-4 D1/D2 — l'état du service (disponible/indisponible) et le plafond du jour (avec le reste)
  // sont lus À L'OUVERTURE, affichés avant toute saisie — plus seulement découverts au moment d'envoyer.
  const statut = useQuery({ queryKey: ['courrier-statut'], queryFn: getCourrierStatut, staleTime: 60_000 })
  const demandes = useQuery({ queryKey: ['courrier-demandes'], queryFn: getCourrierDemandes, enabled: step === 3 })
  // COURRIER-2 Lot 3 — le courrier est COMPOSÉ serveur (ouverture A→E sur les faits) ; l'étape ② est un
  // APERÇU (lecture seule) du 1ᵉʳ destinataire — même texte que le PDF. « Ne pas reformuler » (Vic).
  const apercu = useQuery({ queryKey: ['courrier-apercu', dest[0]?.idu], enabled: step === 2 && !!dest[0],
    queryFn: () => postCourrierComposer(dest[0].idu) })
  useEffect(() => {
    if (apercu.data) { setCorps(apercu.data.recto); setModele(`auto-${apercu.data.ouverture}`) }
  }, [apercu.data])
  // COURRIER-2 Lot 2 — adressage résolu (destinataire + adresse d'envoi + bien + motif de blocage).
  const iduKey = dest.map((d) => d.idu).join(',')
  const adressage = useQuery({ queryKey: ['courrier-adressage', iduKey], enabled: step === 3 && dest.length > 0,
    queryFn: () => postCourrierAdressage(dest.map((d) => d.idu)) })
  const resolutions = adressage.data?.resolutions ?? []
  const bloquees = resolutions.filter((r) => r.bloque)
  const depotBloque = resolutions.length > 0 && bloquees.length > 0
  const envoyer = useMutation({
    mutationFn: () => postCourrierDemande(dest.map((d) => d.idu), corps, modele, recapCommunes(), rattach ?? undefined),
    onSuccess: (d) => { setDemande(d); qc.invalidateQueries({ queryKey: ['courrier-demandes'] }); qc.invalidateQueries({ queryKey: ['pipeline'] }) },
  })
  const apercuPdf = async () => {
    const first = dest[0]; if (!first) return
    setPdfBusy(true); setPdfErr(null)
    try { await courrierPdf(first.idu, modele, corps || '(aperçu)') }
    catch { setPdfErr('Le téléchargement du PDF a échoué. Réessayez.') }
    finally { setPdfBusy(false) }
  }

  const STEPS: [1 | 2 | 3, string][] = [[1, 'Destinataires'], [2, 'Rédaction'], [3, 'Envoi']]

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
      <Banner>Un <b>service d'envoi</b> : vous préparez vos courriers (destinataires + rédaction), LABUSE
        <b> les imprime, les affranchit et les poste</b>. Adressage générique (SPF/CERFA) — aucune identité
        de propriétaire particulier.</Banner>
      {/* OUTILS-FIX-4 D1/D2 — ÉTAT DU SERVICE + PLAFOND DU JOUR, à l'ouverture, avant toute saisie.
          RECETTE-1 R27 — l'encadré « Envoi automatique indisponible — L'envoi postal n'est pas encore
          disponible » est RETIRÉ : la carte d'état ne s'affiche QUE quand le service est disponible
          (elle porte alors le plafond du jour). Rien à l'écran quand l'envoi n'est pas encore ouvert. */}
      {statut.data?.disponible && (
        <div data-courrier-etat className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 rounded-lg border border-line-2 bg-surface-2 px-3 py-1.5 text-[11px]">
          <span className="flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-mint" />
            <span className="text-mint">Service d’envoi disponible</span>
          </span>
          {statut.data.plafond_jour != null && (
            <span data-courrier-plafond className="whitespace-nowrap text-txt-mut">Plafond du jour : <b className="tnum text-txt">{statut.data.reste_jour}</b>/{statut.data.plafond_jour} restant{(statut.data.reste_jour ?? 0) > 1 ? 's' : ''}</span>
          )}
        </div>
      )}
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
          <ParcelInput dataAttr="courrier-idu" placeholder="Adresse, IDU ou référence (BW0917)"
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
          {/* OUTILS-S2 Lot B — terrain nu / sans adresse : aucun occupant à qui écrire → ajout refusé,
              renvoi vers le Courrier SPF (ouvre la fiche, qui porte le pli SPF d'identification). */}
          {ajoutBloque && (
            <div data-courrier-ajout-bloque className="rounded-lg border border-st-ecartee/50 bg-st-ecartee/[0.06] px-3 py-2 text-[11px] leading-snug text-txt-mut">
              <span className="text-st-ecartee">⛔ {iduCourt(ajoutBloque.idu)} — </span>
              {ajoutBloque.code === 'nu'
                ? 'Terrain nu, aucun occupant à qui écrire'
                : ajoutBloque.code === 'inconnue' ? 'Parcelle inconnue'
                : 'Aucune adresse d’envoi (aucun occupant joignable)'}
              {ajoutBloque.code !== 'inconnue' && <> — passez par le <b className="text-txt-mut">Courrier SPF</b> pour identifier le propriétaire.</>}
              {ajoutBloque.code !== 'inconnue' && (
                <button data-courrier-spf-lien onClick={() => select(ajoutBloque.idu)}
                  className="mt-1 block text-mint hover:underline">Ouvrir la fiche (Courrier SPF) →</button>
              )}
            </div>
          )}
          <p className="text-[10px] text-txt-dim">{dest.length} destinataire{dest.length > 1 ? 's' : ''} — un courrier par parcelle.</p>
          <Bouton niveau="primaire" ton="vert" data-courrier-next onClick={() => dest.length && setStep(2)} disabled={dest.length === 0}
            className="mt-auto">Rédiger ›</Bouton>
        </div>
      )}

      {step === 2 && (
        <div className="flex min-h-0 flex-1 flex-col gap-2">
          <p className="text-[10.5px] text-txt-mut">
            Lettre <b className="text-txt">générée automatiquement</b> à partir des données réelles de la
            parcelle — un courrier par destinataire, adapté à ses faits. Aperçu du 1ᵉʳ destinataire :
          </p>
          {apercu.isLoading && <Squelette lignes={4} />}
          {apercu.data && (
            <>
              <div data-courrier-apercu className="min-h-[160px] flex-1 overflow-auto whitespace-pre-wrap rounded-lg border border-line-2 bg-surface-3 px-3 py-2 text-[11px] leading-snug text-txt">
                {apercu.data.recto}
              </div>
              {apercu.data.verso.length > 0 && (
                <details className="rounded-lg border border-line-2 bg-surface-2 px-3 py-1.5 text-[10.5px] text-txt-mut">
                  <summary className="cursor-pointer text-txt-dim">Au dos — synthèse de la parcelle</summary>
                  <div className="mt-1 whitespace-pre-wrap">{apercu.data.verso.join('\n')}</div>
                </details>
              )}
            </>
          )}
          <div className="flex gap-2">
            <Retour label="Destinataires" onClick={() => setStep(1)} />
            <Bouton niveau="primaire" ton="vert" data-courrier-next onClick={() => setStep(3)} disabled={!apercu.data || corps.trim().length < 10}
              className="flex-1">Vérifier l'envoi ›</Bouton>
          </div>
        </div>
      )}

      {step === 3 && (
        <div className="flex min-h-0 flex-1 flex-col gap-2">
          {/* récap */}
          <div className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-[11px]">
            <div className="flex justify-between"><span className="text-txt-mut">Courriers</span><b className="tnum text-txt">{dest.length}</b></div>
            <div className="flex justify-between gap-2"><span className="text-txt-mut">Communes</span><span className="text-right text-txt">{recapCommunes() || '—'}</span></div>
          </div>

          {/* COURRIER-2 Lot 2 — ADRESSAGE par destinataire : Destinataire · Adresse d'envoi · Bien concerné.
              Aucune substitution silencieuse : un blocage (nu / sans adresse / opposition) porte son motif. */}
          <div data-courrier-adressage className="flex flex-col gap-1.5">
            {adressage.isLoading && <Squelette lignes={2} />}
            {resolutions.map((r) => (
              <div key={r.idu} data-courrier-resolution={r.idu}
                className={`rounded-lg border px-3 py-2 text-[11px] ${r.bloque ? 'border-st-ecartee/50 bg-st-ecartee/[0.06]' : 'border-line-2 bg-surface-2'}`}>
                {r.bloque ? (
                  <div className="flex items-start justify-between gap-2">
                    <span className="font-mono text-txt-mut">{r.bien.reference}{r.bien.commune ? ` · ${r.bien.commune}` : ''}</span>
                    <span data-courrier-motif className="text-right text-st-ecartee">⛔ {r.motif}</span>
                  </div>
                ) : (
                  <div className="flex flex-col gap-0.5">
                    <div className="flex justify-between gap-2"><span className="text-txt-mut">Destinataire</span><span className="text-right text-txt">{r.destinataire}</span></div>
                    <div className="flex justify-between gap-2"><span className="text-txt-mut">Adresse d’envoi</span><span className="text-right text-txt">{r.adresse_envoi}</span></div>
                    <div className="flex justify-between gap-2"><span className="text-txt-mut">Bien concerné</span><span className="text-right text-txt-dim">{r.bien.adresse ?? r.bien.reference} · {r.bien.reference}</span></div>
                    {r.mention && <div className="text-[10px] text-txt-dim">{r.mention}</div>}
                  </div>
                )}
              </div>
            ))}
            {depotBloque && (
              <p data-courrier-bloque className="text-[10.5px] text-st-ecartee">
                {bloquees.length} pli{bloquees.length > 1 ? 's' : ''} bloqué{bloquees.length > 1 ? 's' : ''} — retirez-le{bloquees.length > 1 ? 's' : ''} pour déposer.
              </p>
            )}
          </div>

          {/* OUTILS-S2 Lot B (décision Vic) — ligne de prix DISCRÈTE avant le bouton : N × tarif unitaire
              = total TTC. Tarif lu du back (config/param admin), jamais codé ici. Repli honnête si absent. */}
          {!demande && (
            <p data-courrier-tarif className="text-[10.5px] leading-snug text-txt-dim">
              {statut.data?.tarif_unitaire_eur != null ? (
                <>{dest.length} courrier{dest.length > 1 ? 's' : ''} × {fmtEur2(statut.data.tarif_unitaire_eur)} = <b className="text-txt-mut">{fmtEur2(statut.data.tarif_unitaire_eur * dest.length)} TTC</b> — impression, mise sous pli, affranchissement, suivi.</>
              ) : 'Tarif communiqué sous 24 h ouvrées.'}
            </p>
          )}
          {!demande ? (
            <Bouton niveau="primaire" ton="vert" data-courrier-demander onClick={() => envoyer.mutate()} disabled={envoyer.isPending || depotBloque || adressage.isLoading}>
              {envoyer.isPending ? 'Envoi de la demande…' : depotBloque ? 'Dépôt bloqué — voir les motifs' : "Demander l'envoi à LABUSE"}</Bouton>
          ) : (
            // OUTILS-1 A4/B6 — la confirmation porte le N° DE DEMANDE et renvoie vers le suivi. AUCUN
            // état interne (imprimé/posté) côté client : décision Vic — moins de surface, moins de bugs.
            // RECETTE-1 R13 — le numéro montré est le rang PROPRE AU COMPTE (1, 2, 3…), plus le `id`
            // PK global (qui fuitait le volume plateforme : « n° 44 » au 1ᵉʳ courrier). Repli sur id.
            <div data-courrier-confirm className="rounded-lg border border-line-2 bg-mint/[0.05] px-3 py-2 text-[11px] leading-snug text-txt-mut">
              <b className="text-mint">✓ Demande n° {demande.rang_compte ?? demande.id} transmise.</b>
              {/* OUTILS-S2 Lot B — le MÊME montant qu'à l'étape 3 est repris ici. */}
              {statut.data?.tarif_unitaire_eur != null
                ? <> {demande.n} courrier{demande.n > 1 ? 's' : ''} × {fmtEur2(statut.data.tarif_unitaire_eur)} = <b className="text-txt-mut">{fmtEur2(statut.data.tarif_unitaire_eur * demande.n)} TTC</b> — impression, mise sous pli, affranchissement et suivi compris.</>
                : ' LABUSE vous rappelle sous 24 h ouvrées avec le tarif — impression, mise sous pli, affranchissement et suivi compris.'}
              <span className="mt-1.5 block text-[10.5px] text-txt-dim">Retrouvez vos demandes dans <b className="text-txt-mut">Projets → Mes courriers</b>.</span>
            </div>
          )}
          {envoyer.isError && <ErrorState message="La demande n'a pas pu être transmise — réessayez." retry={() => envoyer.mutate()} />}

          {/* aperçu PDF de RELECTURE (secondaire) — corps rempli pour le 1er destinataire */}
          <Bouton niveau="lien" data-courrier-pdf onClick={apercuPdf} disabled={pdfBusy || dest.length === 0} className="self-start">
            {pdfBusy ? 'Génération…' : '⬇ Télécharger l’aperçu PDF (relecture)'}</Bouton>
          {pdfErr && <p data-courrier-pdf-err className="text-[10.5px] text-st-ecartee">{pdfErr}</p>}

          {/* OUTILS-1 A4 — récap des demandes du client : N° + volume + communes, SANS état interne
              (le suivi d'exécution reste chez LABUSE). La vue complète est « Projets → Mes courriers ». */}
          {(demandes.data?.demandes.length ?? 0) > 0 && (
            <div className="mt-1 flex flex-col gap-1">
              <p className="label-caps text-[9px]">Vos demandes</p>
              {demandes.data!.demandes.slice(0, 5).map((d) => (
                <div key={d.id} className="flex items-baseline justify-between gap-2 text-[10.5px]">
                  <span className="min-w-0 truncate text-txt-mut">n° {d.rang_compte ?? d.id} · {d.n} courrier{d.n > 1 ? 's' : ''}{d.communes ? ` · ${d.communes}` : ''}</span>
                  <span className="shrink-0 font-mono text-[9.5px] text-txt-dim">{String(d.ts).slice(0, 10)}</span>
                </div>
              ))}
            </div>
          )}

          <Retour label="Destinataires" onClick={() => setStep(1)} className="mt-auto" />
        </div>
      )}
    </div>
  )
}

/* ───────────────────────────── M10 — DUE DILIGENCE ───────────────────────────── */

// Exporté pour test (le flux « Un lot » est le cœur du mandat PIEGES).
export function M10() {
  // PIEGES-RISQUES-2 (Lot A) — « un lot » = l'UNION des contraintes des parcelles, lues par la MÊME
  // fonction que « une parcelle » (couches en direct). Plus de score de risque ni de checklist cascade :
  // l'outil ne dépend plus de l'ancien scoring. Chaque contrainte porte « N parcelles sur M ».
  const [lot, setLot] = useState<string[]>([])
  const [paste, setPaste] = useState('')
  const [msg, setMsg] = useState<string | null>(null)
  const setCourrierPrefillIdus = useApp((s) => s.setCourrierPrefillIdus)
  const setModule = useApp((s) => s.setModule)
  // PIEGES-RISQUES-1 pt2 — ajouter une parcelle au lot AMÈNE la carte dessus (zoom + surbrillance de la
  // DERNIÈRE ajoutée), même geste que la barre « une parcelle » (select(null) avant focusParcelle, O1/Permis).
  const select = useApp((s) => s.select)
  const focusParcelle = useApp((s) => s.focusParcelle)
  // O6(b) — n'ajoute QUE des références cadastrales résolues (IDU complet ou SECTION+NUMÉRO).
  // Une adresse brute non rattachée à une parcelle NE DOIT JAMAIS entrer dans le lot comme chip.
  const ajouter = (v: string) => {
    const t = iduComplet(v).toUpperCase(); if (!t) return
    if (!estIdu(t)) return   // pas une référence cadastrale (ex. adresse brute) → ignorée
    setMsg(null)
    setLot((l) => l.includes(t) ? l : [...l, t])
    select(null); focusParcelle(t)   // PIEGES-RISQUES-1 pt2 — zoom sur la dernière ajoutée
  }
  const ajouterListe = () => {
    paste.split(/[\n,;]+/).map((x) => x.trim()).filter(Boolean).forEach(ajouter)
    setPaste('')
  }
  const retirer = (t: string) => setLot((l) => l.filter((x) => x !== t))
  const run = useMutation({ mutationFn: () => modDueDiligence(lot.join('\n')) })
  const d = run.data
  const iduxResolus = (d?.parcelles ?? []).map((p) => p.idu)
  return (
    // O6(c) — le PANNEAU ENTIER scrolle (le wrapper d'outil est overflow-hidden).
    <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
      <Banner>Passez plusieurs parcelles au crible d'un coup : la même lecture des couches que « Une
        parcelle », mais réunie — chaque contrainte est listée une fois, avec le nombre de parcelles du
        lot qu'elle touche. Ajoutez-les en tapant une adresse ou un IDU, ou en cliquant la carte.</Banner>
      {/* BARRE UNIQUE (SOCLE) + « + Ajouter » → chips du lot */}
      <div className="flex flex-col gap-1.5 rounded-lg border border-line-2 bg-surface-2 px-2.5 py-2">
        <ParcelInput dataAttr="diligence-idu" placeholder="Adresse, IDU ou référence (BW0917)"
          onPick={ajouter}
          onAddress={() => setMsg("Cette adresse n'a pas de parcelle rattachée — saisissez un IDU ou cliquez la parcelle sur la carte.")} />
        {msg && <p data-diligence-msg className="text-[10.5px] leading-snug text-st-creuser">{msg}</p>}
        <details className="text-[10.5px] text-txt-dim">
          <summary className="cursor-pointer hover:text-txt-mut">ou collez une liste (une par ligne)</summary>
          <div className="mt-1.5 flex flex-col gap-1.5">
            <textarea data-diligence-paste value={paste} onChange={(e) => setPaste(e.target.value)} rows={3}
              placeholder={'97415000AC0253\nAC0254\nBK 63…'}
              className="rounded-lg border border-line-2 bg-surface-3 px-2 py-1.5 font-mono text-[10.5px] text-txt focus:border-mint focus:outline-none" />
            <Bouton niveau="secondaire" ton="vert" data-diligence-add onClick={ajouterListe} disabled={!paste.trim()} className="self-start">+ Ajouter la liste</Bouton>
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

      <Bouton niveau="primaire" ton="vert" data-diligence-analyser onClick={() => lot.length && run.mutate()} disabled={lot.length === 0 || run.isPending}>
        {run.isPending ? 'Analyse…' : `Analyser le lot (${lot.length})`}
      </Bouton>
      {d && (
        <>
          <p className="text-[11px] text-txt-dim">
            <b className="text-txt-hi">{d.n_trouvees}</b> parcelle{d.n_trouvees > 1 ? 's' : ''} sur {d.n_demandes} · {' '}
            <b className="text-txt-hi">{d.contraintes.length}</b> contrainte{d.contraintes.length > 1 ? 's' : ''} distincte{d.contraintes.length > 1 ? 's' : ''}
          </p>
          {/* références non résolues — dites, jamais avalées */}
          {d.erreurs.length > 0 && (
            <div data-diligence-erreurs className="rounded-lg border border-st-ecartee/40 bg-st-ecartee/10 px-3 py-2 text-[10.5px] text-st-ecartee">
              {d.erreurs.length} référence{d.erreurs.length > 1 ? 's' : ''} introuvable{d.erreurs.length > 1 ? 's' : ''} : {d.erreurs.join(', ')}
            </div>
          )}
          {/* NON COUVERT reporté sur le LOT (source unique servitudes.NON_COUVERT) — jamais un « RAS » muet. */}
          {(d.non_couvert ?? []).length > 0 && (
            <div data-diligence-noncouvert className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2">
              <p className="label-caps text-[9.5px]">Non couvert par la base — à vérifier ailleurs (vaut pour tout le lot)</p>
              <div className="mt-1 space-y-0.5">
                {d.non_couvert.map((n, i) => <p key={i} className="text-[10.5px] leading-snug text-txt-mut">○ {n}</p>)}
              </div>
            </div>
          )}
          {/* UNION PAR CONTRAINTE — même carte que « Une parcelle » (catégorie · Sourcé · source·date · effet),
              + badge « N parcelles sur M ». Les libellés/source/date sont ceux du mode parcelle, à l'identique. */}
          <div className="flex flex-col gap-1.5">
            {d.contraintes.map((c, k) => (
              <div key={k} data-diligence-contrainte className="rounded-lg bg-surface-3 px-3 py-2 shadow-elev-1">
                <div className="flex flex-wrap items-baseline gap-1.5">
                  <b className="text-[11.5px] text-txt-hi">{c.categorie}</b>
                  <span className="rounded-full border border-mint/40 bg-mint/10 px-1.5 text-[8.5px] font-medium text-mint">Sourcé</span>
                  <span className="text-[9.5px] text-txt-dim">{c.source}{c.date ? ` · ${c.date}` : ''}</span>
                  <span data-diligence-part className="ml-auto rounded-full bg-surface-2 px-1.5 py-0.5 text-[9.5px] text-txt-mut">
                    {c.n_parcelles} parcelle{c.n_parcelles > 1 ? 's' : ''} sur {d.n_parcelles}
                  </span>
                </div>
                <p className="mt-1 text-[11px] leading-snug text-txt">{c.effet}</p>
              </div>
            ))}
            {d.n_trouvees > 0 && d.contraintes.length === 0 && (
              <p className="rounded-lg bg-surface-2/60 px-3 py-2 text-[11px] text-txt-mut">
                Aucune contrainte dormante détectée sur les {d.n_trouvees} parcelle{d.n_trouvees > 1 ? 's' : ''} du lot (couches ingérées).</p>
            )}
          </div>
          {/* PONT COURRIER — le lot s'exporte vers l'outil Courrier pré-rempli (courrierPrefillIdus). */}
          {iduxResolus.length > 0 && (
            <Bouton niveau="secondaire" ton="vert" data-diligence-courrier
              onClick={() => { setCourrierPrefillIdus(iduxResolus); setModule('courriers') }}>
              ✉ Préparer les courriers ({iduxResolus.length})
            </Bouton>
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
  // RETOURS-15 B8 (P14) — le mode « Un lot » est RETIRÉ : l'outil ne fait plus que « Une parcelle »
  // (plus de bascule d'entrée). M10 (le flux lot) reste exporté pour son test unitaire, mais n'est
  // plus câblé à l'outil.
  return <O5Servitudes key={selectedIdu ?? 'o5'} />
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
  // DENSIFIER-PLI (PISCINES-2 Lot B) — 'renouvellement' (Densifier l'existant) retiré du menu et plié
  // dans le filtre Capacité (« Déjà bâti » + « SDP restante »).
  'prospection-solaire': ProspectionSolaire,
  // OUTILS-MUSCLER-1 Lot A — « Successions » (parcel_veille_succession, succession PROBABLE jamais
  // « en succession »). Ponts : Courrier/Comparer sur sélection, « Assembler → » par carte (Lot B).
  successions: Successions,
  // OUTILS-MUSCLER-3 — « Blocs fonciers » : les assiettes CONTIGUËS d'un même propriétaire PM
  // (parcel_blocs, batch blocs-build). PM seulement (particuliers hors périmètre). Ponts : Courrier
  // (sélection), Scan patrimoine (SIREN) et Assembler (les IDU du bloc) par carte.
  'blocs-fonciers': Blocs,
  // ÉTUDE DE ZONE Z4 — l'outil de chalandise (isochrones IGN + INSEE/SIRENE/BPE).
  'etude-zone': EtudeZone,
  // ETUDIER-BIEN-2 (Lot C) — l'outil « Étudier un bien » (clé 'scoreur-adresse', EtudierBien) est
  // SUPPRIMÉ : ses 3 faits de marché uniques vivent dans la §Marché de la fiche (Lot A), l'entrée par
  // adresse dans la barre de recherche → fiche. Ne reste que la CALCULETTE FONCIÈRE (M23), restaurée
  // en hôte minimal du <Calculette> partagé (CalculetteFonciere) — clé résolvante, ouverte par la fiche
  // §11 / Constructibilité / RadarView / copilote via calcPrefill (jamais un 404). Le composant
  // EtudierBien et le binding front scoreurAdresse sont retirés ; l'endpoint /scoreur-adresse (dormant,
  // partage `_geocode`) reste au dépôt.
  // Retiré du produit le 21/08/2026 (DORMANT) : 'o7-carnet' (Suivi de secteur) — le vrai suivi = la
  // Veille. Composant O7Carnet conservé au dépôt ; endpoints /carnet-secteur vivants.
  // Retiré du produit le 21/08/2026 (DORMANT) : 'o10-bascules' (Quoi de neuf) — plus monté. Composant
  // O10Bascules conservé au dépôt (exporté) ; son endpoint /events reste vivant (cloche de notifications).
  'calculette-fonciere': CalculetteFonciere,
  // K3 (rattrapage KelFoncier) — calculette « Taxe d'aménagement ». Marche à vide ; s'ouvre aussi
  // depuis une parcelle sélectionnée (getTaxePrefill : commune + zone en référence, surface saisie).
  'taxe-amenagement': TaxeAmenagement,
  gabarit: Gabarit,   // GABARIT-1 — résout la clé (carte masquée) ; s'ouvre sur fixtures / deep-link admin
  // RETOURS-3 R5 — « Mon secteur » est hidden au menu (fusionné dans « Étudier un bien »), mais la clé
  // reste RÉSOLVANTE ici : deep-link/copilote historique ouvrent toujours l'outil autonome (redirection conservée).
  'mon-secteur': MonSecteur,   // SECTEUR-1 (S1)
  // 'veille-promoteurs' est mappé plus haut (→ ScanPatrimoine, onglet construit) — RETOURS-4 S7.
  // RADAR-CATÉGORIE (T1) — 'radar' n'est plus un module du panneau Outils : c'est la view 'radar'
  // (catégorie plein écran, RadarView). Ancien composant RadarClient supprimé.
}

// DA-FIX-2 Lot 1 (DA-011) — LE retour du panneau outil, un seul composant `<Retour/>` en haut à gauche.
// Après un pont (pile `outilRetour` non vide) il restitue l'outil de DÉPART (« ← [outil de départ] ») ;
// sinon il ramène au menu Outils (« ← Outils »). Remplace l'ancien fil « ← Outils » ET l'ancien
// `RetourOutil` post-pont (deux mécanismes fusionnés en un).
function PanelRetour() {
  const stack = useApp((s) => s.outilRetour)
  const retourOutil = useApp((s) => s.retourOutil)
  const toggleOutils = useApp((s) => s.toggleOutils)
  const top = stack.length ? stack[stack.length - 1] : null
  return <Retour label={top ? top.label : 'Outils'} onClick={top ? retourOutil : toggleOutils} />
}

export function ModulePanel() {
  const { module, setModule } = useApp()
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
      // COMPARAISON : tant que le TABLEAU est ouvert, Échap le ferme (ComparePanel) — on ne recule pas
      // l'outil par-dessous. Le 2ᵉ Échap (tableau fermé) reculera l'outil.
      if (st.selectedIdu || st.sourceLine || st.tool || st.compareOpen) return
      // DA-FIX-2 Lot 1 (DA-012) : Échap RECULE, il ne FERME plus. Après un pont → outil de départ
      // restitué ; sinon → menu Outils. La croix ✕ reste le seul geste de fermeture du panneau.
      if (st.outilRetour.length) st.retourOutil()
      else st.toggleOutils()
    }
    window.addEventListener('keydown', h, true)
    return () => window.removeEventListener('keydown', h, true)
  }, [])
  if (!def) return null
  const Body = COMPONENTS[def.key]
  return (
    <aside className="apparition flex h-full w-[320px] shrink-0 flex-col border-r border-line bg-surface-1">
      <div className="flex shrink-0 flex-col border-b border-mint/20 bg-mint/[0.07] px-4 py-3">
        {/* M6.1 item 3 : retour direct au menu Outils (fil d'Ariane) — plus besoin de
            repasser par le rail pour changer d'outil. */}
        {/* DA-FIX-2 Lot 1 : le RETOUR unique en haut à gauche (← Outils / ← outil de départ après un
            pont), la croix ✕ en haut à droite FERME le panneau (elle ne recule jamais). */}
        <div className="flex items-center justify-between gap-2">
          <PanelRetour />
          <button onClick={() => setModule(null)} aria-label="Fermer le module"
            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-txt-mut transition-colors duration-quick hover:bg-mint/10 hover:text-txt-hi">✕</button>
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
