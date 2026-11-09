/**
 * M45 (P2a) — Filtres LABUSE : les DEUX VOIES.
 *  · Barre NIVEAU 1 (toujours visible) : constructibilité calibrée · surface · SDP résiduelle ·
 *    état du sol · capacité logements (Estimé) · interrupteur « Analyse LABUSE ».
 *  · Interrupteur : ACTIF par défaut (le classement pilote). Le coupé = voie manuelle pure ;
 *    la bascule affiche le CONTRASTE (trame entière → têtes du classement).
 *  · Tiroir NIVEAU 2 témoin « Puis-je construire ? » (droit du sol).
 * Le compteur est SQL-exact (endpoint unifié /filtre) — jamais un calcul client. Chaque facette
 * porte son étiquette (Sourcé/Estimé) et sa limite. Aucune facette du cadrage ANTI-FILTRES ici.
 */
import { useQuery } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'

import { getAccueilChiffres, getFiltre, getFiltreCount, getProprietairesAutocomplete, getProprietairesFacettes, getZonageZones } from '../../lib/api'
import { countActiveFilters, resumeCriteres } from '../../lib/filters'
import { BANDE_META, BANDE_ORDER } from '../../lib/status'
import { CLIENT } from '../../lib/strings'
import { EMPTY_FILTERS, useApp, type Filters } from '../../store/useApp'
import { Chargement } from '../Loading'
import { Tip } from '../Tip'
import { Bouton } from '../ui/Bouton'
import { Chevron } from '../ui/Chevron'
import { ChevronSection } from './ChevronSection'   // ECRANS-NOV-1 §2 — chevron de catégorie (accordéon)
import { Chip } from '../ui/Chip'
import { useFiltre } from './filtreContext'   // M120 — binding partagé (carte OU cadrage projet)

// ANALYSE-1 — le récapitulatif de la Révélation parle le NOUVEAU moteur (bandes de Score) ; l'ancien
// helper `defTip` (tooltip des paliers Priorité/À suivre…) est retiré avec la ventilation par tier.

// M55-G suite point 3 : CONSTRUCTIBILITE et les chips de verdict/motif ont quitté l'état
// post-analyse (0-caller) — les champs de filtre restent dans le store + l'URL.
// M101 A2 (arbitrage Vic) : les tiers internes (saturé/révélé) sortent du filtre (information de
// fiabilité, dite en fiche via le motif). NU-B-002 — TROIS états pour une partition RÉELLE :
// nu (emprise < 5 %) ∪ bâti (≥ 5 %) ∪ non mesuré (emprise jamais calculée) = toute la base
// filtrable. Sans le 3e état, les 41,5 % sans emprise disparaissaient en silence des deux seaux.
export const ETAT_SOL = [
  { k: 'nu', l: 'Terrain nu' },
  { k: 'bati', l: 'Terrain bâti' },
  { k: 'non_mesure', l: 'Non mesuré' },
]
// M55-J point 1 : égalité de filtres pour le FILET d'invalidation — toute différence (y compris
// un simple réordonnancement) invalide la carte, ce qui est le comportement conservateur voulu
// (un vide honnête vaut mieux qu'un chiffre périmé).
const filtersEqual = (a: Filters, b: Filters): boolean => JSON.stringify(a) === JSON.stringify(b)

// M55-J point 2 / M55-K point 3 : LE bouton d'action du panneau (un seul endroit pour la
// famille) — trois variantes : `primary` (rempli mint, l'action dominante), `secondary`
// (contour neutre) et `danger` (contour ROUGE `st-ecartee`, fond transparent) pour Désactiver.
const ACTION_STYLES = {
  primary: 'bg-mint font-semibold text-mint-ink hover:brightness-110',
  secondary: 'border border-line-2 bg-surface-3/60 text-txt hover:border-txt-dim/50 hover:bg-surface-3 hover:text-txt-hi',
  danger: 'border border-st-ecartee/60 bg-transparent text-st-ecartee hover:bg-st-ecartee/10 hover:border-st-ecartee',
} as const
function ActionBtn({ variant, onClick, children, dataAttr }:
  { variant: keyof typeof ACTION_STYLES; onClick: () => void; children: React.ReactNode; dataAttr?: string }) {
  const extra = dataAttr ? { [dataAttr]: true } : {}
  return (
    <button {...extra} onClick={onClick}
      className={`flex-1 rounded-lg py-2 text-[12px] font-medium transition-colors duration-quick ${ACTION_STYLES[variant]}`}>
      {children}
    </button>
  )
}

const ZONE_FAM = [{ k: 'U', l: 'U' }, { k: 'AU', l: 'AU' }, { k: 'A', l: 'A' }, { k: 'N', l: 'N' }]
// RETOURS-18 pt 21 — libellé long d'une famille de zonage (« U · urbain »…). Le CODE reste la clé
// du filtre (zonagePlu), seul l'affichage s'étoffe.
const ZONE_FAM_LABEL: Record<string, string> = {
  U: 'U · urbain', N: 'N · naturel', A: 'A · agricole', AU: 'AU · à urbaniser',
}
// M55-G point 7 : PROPRIO_TYPE / ETAT_SOCIETE / COPRO retirés avec les tiroirs pédagogiques
// (0-caller) — les champs de filtre restent dans le store + l'URL.
// M55-D stage 6 — les 24 communes par CODE POSTAL (CP dominant mesuré dans la BAN, table
// adresses). La chip affiche le CP, le « i » (title) nomme la commune. Rang 1 du panneau.
// M55-H point 7 : EXPORTÉE — le menu périmètre du header affiche le même CP (source unique).
export const CP_COMMUNES: [string, string][] = [
  ['97400', 'Saint-Denis'], ['97410', 'Saint-Pierre'], ['97412', 'Bras-Panon'],
  ['97413', 'Cilaos'], ['97414', 'Entre-Deux'], ['97419', 'La Possession'],
  ['97420', 'Le Port'], ['97424', 'Saint-Leu'], ['97425', 'Les Avirons'],
  ['97426', 'Les Trois-Bassins'], ['97427', "L'Étang-Salé"], ['97429', 'Petite-Île'],
  ['97430', 'Le Tampon'], ['97431', 'La Plaine-des-Palmistes'], ['97433', 'Salazie'],
  ['97438', 'Sainte-Marie'], ['97439', 'Sainte-Rose'], ['97440', 'Saint-André'],
  ['97441', 'Sainte-Suzanne'], ['97442', 'Saint-Philippe'], ['97450', 'Saint-Louis'],
  ['97460', 'Saint-Paul'], ['97470', 'Saint-Benoît'], ['97480', 'Saint-Joseph'],
]
// M55-G suite point 4 (décision Vic) — UN SEUL niveau, 7 signaux (les deux niveaux du
// point 11 n'auront vécu qu'une journée) : « Nu détenu par société » et « Cession de fonds »
// SUPPRIMÉS de l'UI (clés URL ignorées proprement dans filters.ts, backend intact).
// Libellés/« i » : CLIENT.signaux. OU de groupe et persistance URL (sv=) inchangés.
// FILTRE-NETTOYAGE #4 — « assemblage » QUITTE les Signaux de vie (c'est un état du bien, pas un
// événement daté) → rendu dans la section « Le bien » ci-dessous. « succession » (veille patrimoniale,
// parcel_veille_succession, 7 129 parcelles) rejoint les signaux. Backend : _SIG_SQL (app.py) gère les
// deux clés ; la carte ET le cadrage projet (FiltreFacettes rend SIGNAUX_KEYS) les servent d'un coup.
export const SIGNAUX_KEYS = ['pm_privee', 'procedure', 'permis_actif', 'permis_caduc',
  'friche', 'defisc', 'succession']


const nf = new Intl.NumberFormat('fr-FR')

// DA-FIX-3 Lot 1 (DA-025) — le Chip LOCAL est remplacé par le Chip partagé (`../ui/Chip`),
// ton par défaut `vert`. Les usages (ChipGroup, SignalChip) mappent on→on, onClick→onClick.

// RECETTE-1 (E3, Vic 04/10) — valeur sentinelle de l'état « tout décoché = 0 parcelle » pour un groupe
// `partition` (voir plus bas). Elle ne correspond à aucune valeur réelle → 0 parcelle au back.
export const AUCUN_SENTINEL = '__aucun__'

// `partition` (E3) : les cases COUVRENT tout l'univers (ex. État du sol : nu + bâti = toutes les
// parcelles, disjoints). Alors « rien de coché » = « pas de restriction » → on affiche TOUT COCHÉ par
// défaut ; décocher restreint ; tout décocher = 0 parcelle (sentinelle). Le stockage garde la
// sémantique « sous-ensemble inclus » (rétro-compatible : un vieux hash `es=nu` = « seulement nu ») :
//   []                → tout coché (aucune restriction, rien sérialisé)
//   ['nu']            → seulement nu (sous-ensemble)
//   [AUCUN_SENTINEL]  → rien coché (0 parcelle)
export function ChipGroup({ field, options, partition }: { field: keyof Filters; options: { k: string; l: string }[]; partition?: boolean }) {
  const { filters, setFilter } = useFiltre()
  const sel = (filters[field] as string[]) ?? []
  if (partition) {
    const allKeys = options.map((o) => o.k)
    // ensemble COCHÉ affiché : vide = tout coché ; sentinelle = rien coché ; sinon le sous-ensemble stocké.
    const cochees = sel.length === 0 ? allKeys : sel.includes(AUCUN_SENTINEL) ? [] : sel
    const toggle = (k: string) => {
      const next = cochees.includes(k) ? cochees.filter((x) => x !== k) : [...cochees, k]
      setFilter(field, (next.length === allKeys.length ? [] : next.length === 0 ? [AUCUN_SENTINEL] : next) as never)
    }
    return (
      <div className="mt-1 flex flex-wrap gap-1.5">
        {options.map((o) => <Chip key={o.k} on={cochees.includes(o.k)} onClick={() => toggle(o.k)}>{o.l}</Chip>)}
      </div>
    )
  }
  const toggle = (k: string) =>
    setFilter(field, (sel.includes(k) ? sel.filter((x) => x !== k) : [...sel, k]) as never)
  return (
    <div className="mt-1 flex flex-wrap gap-1.5">
      {options.map((o) => <Chip key={o.k} on={sel.includes(o.k)} onClick={() => toggle(o.k)}>{o.l}</Chip>)}
    </div>
  )
}

// M99 Phase 3 (arbitrage Vic) — SÉLECTEUR DE ZONAGE PAR FAMILLE. Une déroulante RECHERCHABLE
// par famille (386 zones normalisées : une liste plate est illisible), dans l'ordre du volume
// RÉEL servi par /zonage/zones — comptes CALCULÉS, jamais en dur, ils suivent les recalibrages
// PLU. M137-B (Vic) — TOUTE la ligne de famille ouvre l'accordéon (pastille, compte, chevron à
// droite ; plus de lien « zones… ») ; le PREMIER item du menu, « U seul », coche la famille
// entière (champ zonagePlu, sémantique inchangée) ; cocher des zones = filtre exact (champ zonePlu, graphie réglementaire
// MAJUSCULE = zone_filtre, le critère unique côté table). PORTÉE DYNAMIQUE : l'île par défaut,
// les communes filtrées sinon — une zone à 0 parcelle dans la portée est ABSENTE de la liste,
// et le bandeau de portée le dit (comportement explicite, pas un masquage silencieux). La
// fiche, elle, garde la graphie officielle de sa commune (zone_lib, jamais écrasé).
// M99-B — CHOIX PUR, AUCUNE FRAPPE (correctif Vic sur M99) : tout champ de saisie laisse taper
// une valeur inexistante (uc, U-C, faute) → résultat vide inexpliqué. Ici, uniquement des clics :
// « U seul » (tête du menu = toute la famille, le geste par défaut), ou des sous-zones (défilant,
// « U seul » y revient au mode famille). Aucun <input> dans ce bloc.
// EXCLUSIVITÉ familles/sous-zones (M99-B) : côté backend `zonage` (familles) et `zone_plu`
// (zones) se combinent en ET — un mélange inter-familles (famille A + zone UC) rendrait ZÉRO
// en silence. Le menu est donc exclusif : choisir une sous-zone passe le bloc en mode
// sous-zones (familles vidées) ; choisir une famille repasse en mode familles (zones vidées).
// Multi-sélection libre À L'INTÉRIEUR de chaque mode (U+AU, ou UC+UB+1AUB). L'aide le dit.
// PORTÉE (Phase 2) : île par défaut, communes filtrées sinon ; une sous-zone sélectionnée qui
// SORT de la portée est RETIRÉE du filtre et ANNONCÉE — jamais de filtre fantôme qui renvoie
// zéro. Purge UNIQUEMENT sur données chargées (jamais sur erreur réseau : on ne vide pas un
// filtre sur une panne).
export function ZoneSelector() {
  const { filters, setFilter } = useFiltre()
  const [retirees, setRetirees] = useState<string[]>([])
  const zq = useQuery({
    queryKey: ['zonage-zones', [...filters.communes].sort().join('|')],
    queryFn: () => getZonageZones(filters.communes), staleTime: 300_000,
  })
  const selFam = filters.zonagePlu
  const selZones = filters.zonePlu
  const familles = zq.data?.familles ?? ZONE_FAM.map((f) => ({ fam: f.k, n: 0, zones: [] }))
  // Phase 2.4 — purge annoncée des sous-zones sorties de la portée (données chargées seulement).
  const dispo = zq.data ? zq.data.familles.flatMap((f) => f.zones.map((z) => z.zone)) : null
  useEffect(() => {
    if (!dispo) return
    const absentes = selZones.filter((z) => !dispo.includes(z))
    if (absentes.length) {
      setFilter('zonePlu', selZones.filter((z) => dispo.includes(z)))
      setRetirees(absentes)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [zq.data])
  const choisirFamille = (fam: string) => {          // mode famille : zones vidées (exclusivité)
    setFilter('zonePlu', [])
    setFilter('zonagePlu', selFam.includes(fam) ? selFam.filter((x) => x !== fam) : [...selFam, fam])
    setRetirees([])
  }
  const choisirZone = (z: string) => {               // mode sous-zones : familles vidées
    setFilter('zonagePlu', [])
    setFilter('zonePlu', selZones.includes(z) ? selZones.filter((x) => x !== z) : [...selZones, z])
    setRetirees([])
  }
  return (
    <div className="mt-1 flex flex-col gap-1">
      {/* FILTRE-NETTOYAGE #3 — phrase d'aide « Une famille = toutes ses zones · … » retirée. */}
      {retirees.length > 0 && (
        <p data-zones-retirees className="rounded-md bg-surface-2/80 px-2 py-1 text-[10.5px] text-st-creuser">
          {retirees.length > 1 ? `Zones ${retirees.join(', ')} retirées du filtre` : `Zone ${retirees[0]} retirée du filtre`}
          {' '}: absente{retirees.length > 1 ? 's' : ''} de la portée courante.
        </p>
      )}
      {/* RETOURS-18 pt 21 — chaque famille est un SOUS-ACCORDÉON « U · urbain » avec son COMPTE à
          droite, qui se déplie sur ses sous-zones en `LigneChoix` (vert opaque + coche si choisie).
          Le PREMIER item « U seul · toute la famille » coche la famille entière (zonagePlu) ; les
          sous-zones cochent zonePlu (exclusivité famille/zones conservée via choisirFamille/choisirZone).
          data-zones-fam / data-zone-toutes / data-zone préservés (hooks QA). */}
      {familles.map((f) => {
        const zonesSelFam = f.zones.filter((z) => selZones.includes(z.zone)).length
        const enModeFamille = selFam.includes(f.fam)
        return (
          <SousAccordion key={f.fam} dataAttr="data-zone-fam"
            label={<span>{ZONE_FAM_LABEL[f.fam] ?? f.fam}
              {zonesSelFam > 0 && <span className="ml-1.5 text-[10.5px] font-normal text-mint">{zonesSelFam} choisie{zonesSelFam > 1 ? 's' : ''}</span>}</span>}
            count={zq.data ? nf.format(f.n) : '…'}>
            <LigneChoix dataAttr="data-zone-toutes"
              label={<>{f.fam}<span className="font-normal opacity-70"> seul · toute la famille</span></>}
              on={enModeFamille} onClick={() => choisirFamille(f.fam)}
              sub={zq.data ? nf.format(f.n) : '…'} />
            {f.zones.map((z) => (
              <LigneChoix key={z.zone} dataAttr="data-zone" label={z.zone}
                on={selZones.includes(z.zone)} onClick={() => choisirZone(z.zone)} sub={nf.format(z.n)} />
            ))}
            {f.zones.length === 0 && (
              <p className="px-1 py-1 text-[10.5px] text-txt-dim">
                Aucune zone de cette famille dans la portée courante.
              </p>
            )}
          </SousAccordion>
        )
      })}
      {selZones.length > 0 && (
        <button data-zones-vider onClick={() => { setFilter('zonePlu', []); setRetirees([]) }}
          className="self-start text-[10.5px] text-txt-dim underline decoration-txt-dim/40 underline-offset-2 hover:text-mint">
          Vider les {selZones.length} zone{selZones.length > 1 ? 's' : ''} choisie{selZones.length > 1 ? 's' : ''}
        </button>
      )}
    </div>
  )
}

// M55-G point 11 : chip + « i » d'un signal de vie — partagé entre larges et niches
export function SignalChip({ k }: { k: string }) {
  const { filters, setFilter } = useFiltre()
  return (
    <span className="flex items-center gap-1">
      <Chip on={filters.signaux.includes(k)}
        onClick={() => setFilter('signaux', (filters.signaux.includes(k)
          ? filters.signaux.filter((x) => x !== k) : [...filters.signaux, k]) as never)}>
        {CLIENT.signaux.labels[k]}
      </Chip>
      <Tip garder side="top" tip={CLIENT.signaux.infos[k]}>
        <span role="button" tabIndex={0} aria-label={`En savoir plus : ${CLIENT.signaux.labels[k]}`}
          className="flex h-[13px] w-[13px] items-center justify-center rounded-full border border-line-2 text-[8px] font-bold leading-none text-txt-dim hover:border-mint hover:text-mint">i</span>
      </Tip>
    </span>
  )
}

// M55-G suite point 7 : les titres de sections n'ont PLUS de sous-texte — l'explication vit
// dans un « i » (même patron que les signaux), au survol.
export function TitreSection({ titre, info, cls = '' }: { titre: string; info: string; cls?: string }) {
  return (
    <p className={`label-caps flex items-center gap-1.5 text-txt-mut ${cls}`}>{titre}
      <Tip garder side="top" tip={info}>
        <span role="button" tabIndex={0} aria-label={`En savoir plus : ${titre}`}
          className="flex h-[13px] w-[13px] items-center justify-center rounded-full border border-line-2 text-[8px] font-bold normal-case leading-none text-txt-dim hover:border-mint hover:text-mint">i</span>
      </Tip>
    </p>
  )
}

// ECRANS-NOV-1 §2 / RETOURS-18 pt 21 — une CATÉGORIE DE FILTRES en ACCORDÉON NUMÉROTÉ (1 · Communes,
// 2 · Le terrain, 3 · Affiner la recherche, 4 · Le propriétaire). Le titre porte le petit numéro gris
// PUIS le titre blanc gras, SUR UNE LIGNE (truncate). `badge` = le RÉSUMÉ du choix à droite, montré
// quand la catégorie est fermée (« Toutes », « 2 choix », « — »…). Le chevron pointe vers le bas à l'ouvert.
// CONTRÔLE : si `open`+`onToggle` sont fournis, l'accordéon est piloté de l'extérieur (ouverture
// EXCLUSIVE depuis le parent) ; sinon il garde un état interne (usage autonome, p. ex. le cadrage projet).
export function AccordionCat({ titre, info, num, defaultOpen = false, badge, cls = '', open, onToggle, children }:
  { titre: string; info?: string; num?: string; defaultOpen?: boolean; badge?: React.ReactNode; cls?: string;
    open?: boolean; onToggle?: () => void; children: React.ReactNode }) {
  const [openInner, setOpenInner] = useState(defaultOpen)
  const controlled = open !== undefined && onToggle !== undefined
  const isOpen = controlled ? open! : openInner
  const toggle = controlled ? onToggle! : () => setOpenInner((o) => !o)
  return (
    <div className={`gcard overflow-hidden ${cls}`}>
      <button type="button" data-cat-toggle aria-expanded={isOpen} onClick={toggle}
        className="flex w-full items-center gap-2 px-3 py-2.5 text-left">
        <span className="flex min-w-0 items-center gap-1.5">
          <span className="flex min-w-0 items-center gap-2 truncate">
            {num && <span className="shrink-0 text-[12px] text-txt-dim tabular-nums">{num}</span>}
            <span className="truncate text-[13px] font-semibold text-txt-hi">{titre}</span>
          </span>
          {info && (
            <Tip garder side="top" tip={info}>
              <span role="button" tabIndex={0} aria-label={`En savoir plus : ${titre}`}
                className="flex h-[13px] w-[13px] shrink-0 items-center justify-center rounded-full border border-line-2 text-[8px] font-bold normal-case leading-none text-txt-dim hover:border-mint hover:text-mint">i</span>
            </Tip>
          )}
        </span>
        <span className="ml-auto flex shrink-0 items-center gap-2">
          {!isOpen && badge && <span className="text-[10.5px] text-txt-dim">{badge}</span>}
          <ChevronSection open={isOpen} />
        </span>
      </button>
      {isOpen && <div className="px-3 pb-3">{children}</div>}
    </div>
  )
}

// RETOURS-18 pt 21 — un SOUS-ACCORDÉON (dans « Le terrain » zonage, ou « Le propriétaire » forme/activité) :
// un en-tête avec son COMPTE à droite (mêmes comptes servis), qui se déplie sur des `LigneChoix`. Le head
// est lui-même stylé comme une `LigneChoix` sombre (pas de sélection), avec un chevron à droite. L'état
// d'ouverture est LOCAL (plusieurs sous-accordéons peuvent coexister ouverts dans une même catégorie).
export function SousAccordion({ label, count, children, dataAttr, defaultOpen = false }:
  { label: React.ReactNode; count?: React.ReactNode; children: React.ReactNode; dataAttr?: string; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen)
  const extra = dataAttr ? { [dataAttr]: true } : {}
  return (
    <div className="rounded-md">
      <button type="button" {...extra} aria-expanded={open} onClick={() => setOpen((o) => !o)}
        className="flex w-full items-start gap-2 rounded-md border border-line-2 bg-surface-3/60 px-2.5 py-1.5 text-left text-[12px] font-medium text-txt transition-colors duration-quick hover:border-mint/50 hover:text-txt-hi">
        {/* RETOURS-19 (pt 7) — libellé long passe À LA LIGNE (jamais coupé) ; le compte reste visible à droite. */}
        <span className="min-w-0 flex-1 break-words leading-snug">{label}</span>
        <span className="ml-auto flex shrink-0 items-center gap-1.5">
          {count != null && <span className="text-[10.5px] tabular-nums text-txt-dim">{count}</span>}
          <Chevron open={open} />
        </span>
      </button>
      {open && <div className="mt-0.5 flex flex-col gap-0.5 pl-3">{children}</div>}
    </div>
  )
}

// ECRANS-NOV-1 §2 — une LIGNE de liste sélectionnable (commune, sous-zone…) : UN seul état sélectionné
// partout — vert OPAQUE, texte sombre, coche à DROITE ; au repos, survol vert léger. Plus de liseré.
export function LigneChoix({ label, on, onClick, sub, dataAttr }:
  { label: React.ReactNode; on: boolean; onClick: () => void; sub?: React.ReactNode; dataAttr?: string }) {
  const extra = dataAttr ? { [dataAttr]: true } : {}
  return (
    <button type="button" {...extra} aria-pressed={on} onClick={onClick}
      className={`flex w-full items-start gap-2 rounded-md px-2.5 py-1.5 text-left text-[12px] transition-colors duration-quick ${
        on ? 'bg-mint font-medium text-mint-on' : 'text-txt-mut hover:bg-mint/15 hover:text-txt'}`}>
      {/* RETOURS-19 (pt 7) — libellé long À LA LIGNE (plus de texte coupé) ; le compte reste visible à droite. */}
      <span className="min-w-0 flex-1 break-words leading-snug">{label}</span>
      {sub != null && <span className={`mt-px shrink-0 text-[10.5px] tabular-nums ${on ? 'text-mint-on/70' : 'text-txt-dim'}`}>{sub}</span>}
      {on && (
        <svg aria-hidden viewBox="0 0 12 12" className="h-3 w-3 shrink-0">
          <polyline points="2.5,6.5 5,9 9.5,3.5" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      )}
    </button>
  )
}

export function NumField({ field, ph, suffix }: { field: keyof Filters; ph: string; suffix?: string }) {
  const { filters, setFilter } = useFiltre()
  const v = filters[field] as number | null
  return (
    <div className="flex items-center gap-1">
      <input type="number" inputMode="numeric" placeholder={ph}
        value={v ?? ''} onChange={(e) => setFilter(field, (e.target.value === '' ? null : Number(e.target.value)) as never)}
        className="w-[68px] rounded-md border border-line-2 bg-transparent px-2 py-1 text-[11px] text-txt-hi placeholder:text-txt-dim focus:outline-none" />
      {suffix && <span className="text-[10px] text-txt-dim">{suffix}</span>}
    </div>
  )
}

// RECETTE-1 (E2, Vic 04/10) — le GROUPE « CAPACITÉ » (CapaciteSection : logements possibles ≥ N +
// destination ; SDP restante / Déjà bâti d'« Affiner ») est ENTIÈREMENT RETIRÉ. Les clés restent
// inertes côté store ⇒ un vieux hash / une vue / une veille s'ouvre sans erreur (clé ignorée).

// RETOURS-18 pt 21 — nombre de critères actifs de « Affiner la recherche » (copro + risques + hauteur
// + emprise + ZFANG + FRR + signaux). Sert le badge du head quand la catégorie est fermée.
export function nAffinerActifs(filters: Filters): number {
  const nSig = filters.signaux.filter((s) => SIGNAUX_KEYS.includes(s)).length
  const risqueAvec = filters.flags.includes('risques')
  const risqueSans = filters.flagsExclus.includes('risques')
  return nSig + (filters.horsCopro ? 1 : 0)
    + (filters.hauteurMin != null || filters.hauteurMax != null ? 1 : 0)
    + (filters.empriseMin != null || filters.empriseMax != null ? 1 : 0)
    + (risqueAvec || risqueSans ? 1 : 0)
    + ((filters.zfangRegime?.length ?? 0) > 0 ? 1 : 0)
    + ((filters.frrClassement?.length ?? 0) > 0 ? 1 : 0)
}

// RETOURS-18 pt 21 — le CORPS de « Affiner la recherche » : chaque interrupteur devient une `LigneChoix`
// (vert opaque + coche si actif ; survol vert léger sinon), SANS case ni pastille. Les fourchettes
// chiffrées (hauteur / emprise LiDAR) restent des champs numériques (ce ne sont pas des interrupteurs).
// AUCUN prédicat ne change — seuls les écritures store existantes (horsCopro, flags/flagsExclus 'risques',
// zfangRegime, frrClassement, signaux, empriseSature) sont pilotées par les mêmes gestes.
export function AffinerBody() {
  const { filters, setFilter } = useFiltre()
  // FIX-NU3-2 (G-001) — RISQUES exclusifs (off / avec / sans) : prédicat inchangé.
  const risqueAvec = filters.flags.includes('risques')
  const risqueSans = filters.flagsExclus.includes('risques')
  const setRisque = (mode: 'off' | 'avec' | 'sans') => {
    setFilter('flags', filters.flags.filter((f) => f !== 'risques').concat(mode === 'avec' ? ['risques'] : []))
    setFilter('flagsExclus', filters.flagsExclus.filter((f) => f !== 'risques').concat(mode === 'sans' ? ['risques'] : []))
  }
  const zfang = filters.zfangRegime ?? []
  const frr = filters.frrClassement ?? []
  const toggleArr = (field: 'zfangRegime' | 'frrClassement', k: string) => {
    const cur = (filters[field] as string[] | undefined) ?? []
    setFilter(field, (cur.includes(k) ? cur.filter((x) => x !== k) : [...cur, k]) as never)
  }
  const toggleSignal = (k: string) => setFilter('signaux',
    (filters.signaux.includes(k) ? filters.signaux.filter((x) => x !== k) : [...filters.signaux, k]) as never)
  return (
    <div className="flex flex-col gap-4">
      {/* Copropriété — un seul interrupteur (sans copropriété). */}
      <div data-filtre-hors-copro>
        <TitreSection titre="Copropriété" info="Écarte les parcelles en copropriété (immatriculation RNIC ou copro DVF)." />
        <div className="mt-1 flex flex-col gap-0.5">
          <LigneChoix label="Sans copropriété" on={filters.horsCopro} onClick={() => setFilter('horsCopro', !filters.horsCopro)} />
        </div>
      </div>
      {/* Risques (PPR / aléa) — trois états exclusifs. */}
      <div data-filtre-risques>
        <TitreSection titre="Risques (PPR / aléa)" info="PPR (zones rouge/bleue) et aléas Géorisques. « Sans risque » écarte toute parcelle portant un de ces signaux." />
        <div className="mt-1 flex flex-col gap-0.5">
          {([['off', 'Peu importe'], ['avec', 'Avec un risque'], ['sans', 'Sans risque']] as const).map(([k, l]) => {
            const on = k === 'avec' ? risqueAvec : k === 'sans' ? risqueSans : (!risqueAvec && !risqueSans)
            return <LigneChoix key={k} dataAttr={`data-risque-${k}`} label={l} on={on} onClick={() => setRisque(k)} />
          })}
        </div>
      </div>
      {/* Hauteur / emprise LiDAR — fourchettes chiffrées (pas des interrupteurs). */}
      <div>
        <TitreSection titre="Hauteur du bâti (LiDAR)" info="Faîtage mesuré au LiDAR HD (la hauteur de la fiche §Bâti) ; les parcelles au bâti non mesuré n’entrent pas dans une fourchette." />
        <div className="mt-1 flex items-center gap-1.5"><NumField field="hauteurMin" ph="min" /><span className="text-txt-dim">–</span><NumField field="hauteurMax" ph="max" suffix="m" /></div>
      </div>
      <div>
        <TitreSection titre="Emprise bâtie" info="Part de l'emprise constructible déjà couverte par du bâti (run servi). La même que « État du sol »." />
        <div className="mt-1 flex items-center gap-1.5"><NumField field="empriseMin" ph="min" /><span className="text-txt-dim">–</span><NumField field="empriseMax" ph="max" suffix="%" /></div>
        <div className="mt-1 flex flex-col gap-0.5">
          <LigneChoix dataAttr="data-filtre-emprise-sature" label="Saturé (bâti au-delà du plafond)"
            on={filters.empriseSature} onClick={() => setFilter('empriseSature', !filters.empriseSature)} />
        </div>
      </div>
      {/* ZFANG / FRR — statut de la commune (territoire_fiscal), multi-sélection. */}
      <div>
        <TitreSection titre="ZFANG — zone franche" info="Statut ZFANG de la commune (source unique territoire_fiscal)." />
        <div className="mt-1 flex flex-col gap-0.5">
          {[['renforce', 'Renforcée'], ['standard', 'Standard']].map(([k, l]) => (
            <LigneChoix key={k} dataAttr="data-zfang" label={l} on={zfang.includes(k)} onClick={() => toggleArr('zfangRegime', k)} />
          ))}
        </div>
      </div>
      <div>
        <TitreSection titre="FRR — ruralités" info="Classement FRR de la commune (source unique territoire_fiscal)." />
        <div className="mt-1 flex flex-col gap-0.5">
          {[['totalite', 'Totalité'], ['partie', 'En partie'], ['hors', 'Hors dispositif']].map(([k, l]) => (
            <LigneChoix key={k} dataAttr="data-frr" label={l} on={frr.includes(k)} onClick={() => toggleArr('frrClassement', k)} />
          ))}
        </div>
      </div>
      {/* Signaux de vie — événements sourcés, cumulables (OU de groupe). Chaque signal garde son « i ». */}
      <div data-signaux-vie>
        <TitreSection titre="Signaux de vie"
          info="Des événements sourcés, cumulables — une parcelle correspond si au moins un des signaux cochés est présent." />
        <div className="mt-1 flex flex-col gap-0.5">
          {SIGNAUX_KEYS.map((k) => (
            <LigneChoix key={k} dataAttr="data-signal" label={
              <span className="inline-flex items-center gap-1.5">{CLIENT.signaux.labels[k]}
                <Tip garder side="top" tip={CLIENT.signaux.infos[k]}>
                  {/* RETOURS-21 (pt 4) — le « i » suit la couleur du TEXTE de la ligne (cercle COMPRIS) :
                      `border-current` (et non `border-current/40`, qui ne génère pas de classe valide et
                      retombait en gris clair). Sur une ligne sélectionnée (encre sombre), le cercle devient
                      sombre et reste lisible sur le vert. */}
                  <span role="button" tabIndex={0} aria-label={`En savoir plus : ${CLIENT.signaux.labels[k]}`}
                    className="flex h-[13px] w-[13px] items-center justify-center rounded-full border border-current text-[8px] font-bold leading-none opacity-70 hover:opacity-100">i</span>
                </Tip>
              </span>}
              on={filters.signaux.includes(k)} onClick={() => toggleSignal(k)} />
          ))}
        </div>
      </div>
    </div>
  )
}

// RETOURS-14 P5 — SECTION REPLIABLE « AFFINER LA RECHERCHE » — usage AUTONOME (cadrage projet) : garde son
// propre chevron + état interne. Sur la CARTE, elle est rendue comme AccordionCat numéroté « 3 · » (contrôlé
// par le parent, ouverture exclusive) — voir FiltreLabuse. Le corps est le MÊME (AffinerBody), zéro copie.
export function AffinerRecherche() {
  const { filters } = useFiltre()
  const [ouvert, setOuvert] = useState(false)
  const nAffiner = nAffinerActifs(filters)
  return (
    <div data-affiner className="mt-4">
      <button data-affiner-toggle aria-expanded={ouvert} onClick={() => setOuvert((v) => !v)}
        className="group flex w-full items-center gap-1.5 text-left transition-colors duration-quick">
        <Chevron open={ouvert} />
        <span className="label-caps text-txt-mut group-hover:text-txt-hi">Affiner la recherche</span>
        {nAffiner > 0 && <span className="ml-auto shrink-0 rounded-full bg-mint/20 px-1.5 py-0.5 text-[10px] font-medium text-mint tabular-nums">{nAffiner}</span>}
      </button>
      {ouvert && (
        <div className="gcard mt-2 p-3">
          <AffinerBody />
        </div>
      )}
    </div>
  )
}

// M55-G point 7 / suite point 3 : Tiroir, ModeBCurseur, BoolChip, Section retirés avec le
// contenu de l'état allumé (0-caller ici ; le curseur mode B de SESSION reste porté par le
// store — la fiche continue de le lire).

// ═══════ KELFONCIER-FIX-1 (Lot B) — SECTION « PROPRIÉTAIRE » REMONTÉE ═══════
// Ré-expose la section propriétaire retirée le 28/08/2026 (commit 79523a24) dans « Plus de filtres ».
// Branchée sur les facettes DGFiP RÉELLES (millésime 2025, comptes vivants, jamais de valeur en dur).
// La portée facettes = la commune active du filtre quand une SEULE est cochée (sinon portée par défaut
// du back). NOUVEAUTÉS KELFONCIER : (1) chip « Particulier » = aucune PM connue sur la parcelle
// (proprietaireType 'pp', 349 597 parcelles, prédicat SQL de l'audit) ; (2) TRANCHE d'âge du dirigeant
// (< 50 / 50-69 / ≥ 70, JAMAIS l'âge exact) sur `v_pm_propension_vendre.age_max_dirigeant` (pmAge).
// DA : vert #4ADE80 (mint), composants de la charte, jamais de mauve.

// Un débounce court sur la dénomination : on interroge l'autocomplétion au fil de la frappe (250 ms).
function useDebounced<T>(value: T, ms: number): T {
  const [v, setV] = useState(value)
  useEffect(() => {
    const t = window.setTimeout(() => setV(value), ms)
    return () => window.clearTimeout(t)
  }, [value, ms])
  return v
}

// RETOURS-18 pt 21 — la puce de facette `FacetteChip` est retirée : les formes/activités sont désormais
// rendues en `LigneChoix` sous des sous-accordéons (voir SectionProprietaire).

// KELFONCIER-FIX-1 (Lot B) — les trois TRANCHES d'âge du dirigeant (jamais l'âge exact).
// RETOURS-18 pt 21 — libellés de la maquette (« Moins de 50 ans »…) ; les CLÉS (pmAge) sont inchangées.
const PM_AGE_TRANCHES = [
  { k: 'moins50', l: 'Moins de 50 ans' },
  { k: '50_69', l: '50 à 69 ans' },
  { k: '70plus', l: '70 ans et plus' },
]

// RETOURS-18 pt 21 — REGROUPEMENT d'affichage des FORMES juridiques en 3 familles (maquette :
// « Collectivités et État », « Sociétés », « Associations et autres »). Le GROUPE n'est qu'une
// présentation : chaque forme réelle (code DGFiP servi par les facettes) reste cochée/décochée
// individuellement (pmForme, écriture store inchangée). Une forme absente de ces listes retombe
// dans « Associations et autres » (jamais masquée). L'ORDRE de la famille « Sociétés » suit la
// maquette (SCI, SAS, SARL, SA) ; les autres codes de la famille viennent ensuite.
const FORME_GROUPES: { k: string; l: string; codes: string[] }[] = [
  { k: 'public', l: 'Collectivités et État',
    codes: ['COM', 'DEPT', 'REG', 'ETAT', 'COLL', 'EPCI', 'EPIC', 'SEM', 'HLM', 'SAFR', 'COAG'] },
  { k: 'societe', l: 'Sociétés',
    codes: ['SCI', 'SAS', 'SARL', 'SA', 'SC', 'SCP', 'SCM', 'SCCV', 'SCA', 'SNC', 'GIE', 'SCA'] },
  { k: 'autre', l: 'Associations et autres',
    codes: ['ASS', 'GFA', 'EARL', 'GAEC', 'AUPM'] },
]

// RETOURS-18 pt 21 — REGROUPEMENT d'affichage des codes APE/activité (maquette : « Immobilier »,
// « Construction et promotion », « Autres »). Préfixe NAF → famille ; même principe (pmApe inchangé).
function apeGroupe(code: string): 'immobilier' | 'construction' | 'autre' {
  if (code.startsWith('41.') || code.startsWith('43.') || code.startsWith('42.')) return 'construction'
  if (code.startsWith('68.') || code.startsWith('70.') || code.startsWith('64.')) return 'immobilier'
  return 'autre'
}
const APE_GROUPES: { k: 'immobilier' | 'construction' | 'autre'; l: string }[] = [
  { k: 'immobilier', l: 'Immobilier' },
  { k: 'construction', l: 'Construction et promotion' },
  { k: 'autre', l: 'Autres' },
]

export function SectionProprietaire({ open: openProp, onToggle }: { open?: boolean; onToggle?: () => void } = {}) {
  const { filters, setFilter } = useFiltre()
  const [openInner, setOpenInner] = useState(false)
  const controlled = openProp !== undefined && onToggle !== undefined
  const open = controlled ? openProp! : openInner
  const setOpen = () => { if (controlled) onToggle!(); else setOpenInner((o) => !o) }
  // Portée facettes : une commune SEULE cochée → cette commune ; sinon portée par défaut du back.
  const commune = filters.communes.length === 1 ? filters.communes[0] : undefined
  const fq = useQuery({
    queryKey: ['prop-facettes', commune ?? '__ile__'],
    queryFn: () => getProprietairesFacettes(commune),
    staleTime: 300_000,
  })
  const fac = fq.data
  const couvert = fac ? fac.couverture.couvert : true   // avant chargement : on ne grise pas
  const dis = !couvert

  // ── Dénomination + autocomplétion (débounce 250 ms) ──
  const [denomInput, setDenomInput] = useState(filters.pmDenom ?? '')
  const [showSug, setShowSug] = useState(false)
  const debDenom = useDebounced(denomInput.trim(), 250)
  const aq = useQuery({
    queryKey: ['prop-autocomplete', debDenom, commune ?? '__ile__'],
    queryFn: () => getProprietairesAutocomplete(debDenom, commune),
    enabled: !dis && debDenom.length >= 2,
    staleTime: 60_000,
  })

  // ── multi-sélections (formes / apes / tranche d'âge) ──
  const toggleForme = (code: string) => setFilter('pmForme',
    filters.pmForme.includes(code) ? filters.pmForme.filter((x) => x !== code) : [...filters.pmForme, code])
  const toggleApe = (code: string) => setFilter('pmApe',
    filters.pmApe.includes(code) ? filters.pmApe.filter((x) => x !== code) : [...filters.pmApe, code])
  const toggleAge = (code: string) => setFilter('pmAge',
    filters.pmAge.includes(code) ? filters.pmAge.filter((x) => x !== code) : [...filters.pmAge, code])

  // Personne morale (oui / indifférent) ET « Particulier » (aucune PM connue) sont MUTUELLEMENT
  // exclusifs : proprietaireType 'pp' ⇒ pas de PM, donc « Oui » les vide, et « Particulier » vide
  // les critères PM (qui n'auraient aucun sens sur une parcelle sans PM).
  const pmOui = filters.personneMorale === true
  const particulier = filters.proprietaireType.includes('pp')
  const setParticulier = (on: boolean) => {
    if (on) { setFilter('proprietaireType', ['pp']); setFilter('personneMorale', false) }
    else setFilter('proprietaireType', filters.proprietaireType.filter((x) => x !== 'pp'))
  }

  const nActifsProp = (filters.personneMorale ? 1 : 0) + (particulier ? 1 : 0) + (filters.pmDenom ? 1 : 0)
    + (filters.pmSiren ? 1 : 0) + filters.pmForme.length + filters.pmApe.length + filters.pmAge.length
    + (filters.pmDirigMin != null ? 1 : 0) + (filters.pmDirigMax != null ? 1 : 0)

  // RETOURS-18 pt 21 — FORME JURIDIQUE en SOUS-ACCORDÉONS (3 familles) : chaque groupe réunit les
  // formes RÉELLES servies par les facettes qui lui appartiennent, le head porte le COMPTE cumulé
  // (somme des n), et le corps liste chaque forme en `LigneChoix` (toggle pmForme — écriture inchangée).
  const formesByGroupe = FORME_GROUPES.map((g) => {
    const dansGroupe = (fac?.formes ?? []).filter((o) =>
      (g.k === 'autre'
        ? !FORME_GROUPES.filter((x) => x.k !== 'autre').some((x) => x.codes.includes(o.code))
        : g.codes.includes(o.code)))
    // ordre maquette pour « Sociétés » (SCI, SAS, SARL, SA…) : trie par position dans g.codes, puis n.
    const ordre = (o: { code: string }) => { const i = g.codes.indexOf(o.code); return i < 0 ? 999 : i }
    const items = [...dansGroupe].sort((a, b) => ordre(a) - ordre(b) || b.n - a.n)
    return { ...g, items, total: items.reduce((s, o) => s + o.n, 0),
      nSel: items.filter((o) => filters.pmForme.includes(o.code)).length }
  })
  // RETOURS-18 pt 21 — ACTIVITÉ (code APE) en SOUS-ACCORDÉONS (Immobilier / Construction / Autres).
  const apesByGroupe = APE_GROUPES.map((g) => {
    const items = (fac?.apes ?? []).filter((o) => apeGroupe(o.code) === g.k)
    return { ...g, items, total: items.reduce((s, o) => s + o.n, 0),
      nSel: items.filter((o) => filters.pmApe.includes(o.code)).length }
  })

  // ECRANS-NOV-1 §2 / RETOURS-18 pt 21 — « 4 · Le propriétaire » : carrosserie AccordionCat numérotée.
  const badge = nActifsProp > 0 ? `${nActifsProp} choix` : '—'
  return (
    <div data-section-proprietaire className="mt-3">
      <AccordionCat num="4" titre="Le propriétaire" open={open} onToggle={setOpen} badge={badge}
        info="Qui détient la parcelle (DGFiP, millésime récent) : particulier ou société, forme juridique, activité, âge du dirigeant.">
        <div className="flex flex-col gap-4">
          {/* En-tête : source + millésime, et l'état de couverture (jamais un zéro muet). */}
          <p className="text-[10.5px] leading-snug text-txt-dim">
            {fq.isLoading ? <Chargement variant="inline" />
              : fac ? <>Source DGFiP · millésime {fac.millesime}</> : 'Données propriétaire indisponibles.'}
          </p>
          {fac && !couvert && (
            <p data-prop-non-couvert className="rounded-md bg-surface-2/80 px-2 py-1 text-[10.5px] text-st-creuser">
              Non couvert pour cette commune — les critères propriétaire sont indisponibles ici.
            </p>
          )}

          {/* ── QUI DÉTIENT : Particulier / Société / Indifférent (3 LigneChoix, Indifférent = défaut). ── */}
          <div>
            <TitreSection titre="Qui détient" info="« Particulier » = aucune société connue sur la parcelle ; « Société » = détenue par une personne morale (SCI, SA…) ; « Indifférent » = sans restriction." />
            <div className="mt-1 flex flex-col gap-0.5">
              <LigneChoix dataAttr="data-prop-particulier" label="Particulier"
                on={particulier} onClick={() => setParticulier(!particulier)} />
              <LigneChoix dataAttr="data-prop-societe" label="Société"
                on={pmOui} onClick={() => { setFilter('personneMorale', true); setParticulier(false) }} />
              <LigneChoix dataAttr="data-prop-indifferent" label="Indifférent"
                on={!pmOui && !particulier} onClick={() => { setFilter('personneMorale', false); setParticulier(false) }} />
            </div>
          </div>

          {/* Les critères FINS ne valent que sur des personnes morales — grisés si « Particulier ». */}
          <fieldset disabled={dis || particulier} className={(dis || particulier) ? 'pointer-events-none opacity-50' : ''}>
          <div className="flex flex-col gap-4">
            {/* ── Dénomination + autocomplétion (conservée — texte, pas un interrupteur). ── */}
            <div className="relative">
              <TitreSection titre="Dénomination" info="Nom de la société (autocomplétion sur les entités réelles)." />
              <input type="text" value={denomInput} placeholder="Ex. SCI du Littoral"
                onChange={(e) => { setDenomInput(e.target.value); setShowSug(true); if (e.target.value.trim() === '') setFilter('pmDenom', null) }}
                onFocus={() => setShowSug(true)}
                onBlur={() => window.setTimeout(() => setShowSug(false), 150)}
                className="mt-1 w-full rounded-md border border-line-2 bg-transparent px-2 py-1 text-[11px] text-txt-hi placeholder:text-txt-dim focus:outline-none" />
              {showSug && debDenom.length >= 2 && aq.data && aq.data.suggestions.length > 0 && (
                <ul data-prop-suggestions className="absolute z-20 mt-1 max-h-44 w-full overflow-y-auto rounded-md border border-line-2 bg-surface-2 py-1 shadow-lg">
                  {aq.data.suggestions.map((s) => (
                    <li key={s.siren || s.denomination}>
                      <button type="button"
                        onMouseDown={(e) => { e.preventDefault(); setDenomInput(s.denomination); setFilter('pmDenom', s.denomination); setShowSug(false) }}
                        className="flex w-full items-center gap-2 px-2 py-1 text-left text-[11px] text-txt transition-colors duration-quick hover:bg-surface-3 hover:text-txt-hi">
                        <span className="flex-1 truncate">{s.denomination}</span>
                        <span className="shrink-0 tabular-nums text-[10px] text-txt-dim">{nf.format(s.n)} parc.</span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* ── SIREN (un ou plusieurs, séparés par virgule) ── */}
            <div>
              <TitreSection titre="SIREN" info="Un ou plusieurs SIREN, séparés par une virgule." />
              <input type="text" value={filters.pmSiren ?? ''} placeholder="Un ou plusieurs, séparés par une virgule"
                onChange={(e) => setFilter('pmSiren', e.target.value.trim() === '' ? null : e.target.value)}
                className="mt-1 w-full rounded-md border border-line-2 bg-transparent px-2 py-1 text-[11px] text-txt-hi placeholder:text-txt-dim focus:outline-none" />
            </div>

            {/* ── FORME JURIDIQUE — sous-accordéons par famille (compte cumulé), formes en LigneChoix. ── */}
            <div>
              <TitreSection titre="Forme juridique" info="Regroupée en familles ; chaque forme (code DGFiP réel) reste cochable individuellement." />
              {fac && fac.formes.length > 0 ? (
                <div className="mt-1 flex flex-col gap-1">
                  {formesByGroupe.filter((g) => g.items.length > 0).map((g) => (
                    <SousAccordion key={g.k} dataAttr="data-forme-groupe"
                      label={<span>{g.l}{g.nSel > 0 && <span className="ml-1.5 text-[10.5px] font-normal text-mint">{g.nSel} choix</span>}</span>}
                      count={nf.format(g.total)}>
                      {g.items.map((o) => (
                        <LigneChoix key={o.code} dataAttr="data-forme-juridique" label={o.label} sub={nf.format(o.n)}
                          on={filters.pmForme.includes(o.code)} onClick={() => toggleForme(o.code)} />
                      ))}
                    </SousAccordion>
                  ))}
                </div>
              ) : <p className="mt-1 text-[10px] text-txt-dim">{fq.isLoading ? '…' : 'Aucune forme dans la portée courante.'}</p>}
            </div>

            {/* ── ACTIVITÉ (code APE) — sous-accordéons (Immobilier / Construction / Autres). ── */}
            <div>
              <TitreSection titre="Activité" info="Code APE/NAF (SIRENE), regroupé par famille ; chaque activité reste cochable individuellement." />
              {fac && fac.apes.length > 0 ? (
                <div className="mt-1 flex flex-col gap-1">
                  {apesByGroupe.filter((g) => g.items.length > 0).map((g) => (
                    <SousAccordion key={g.k} dataAttr="data-ape-groupe"
                      label={<span>{g.l}{g.nSel > 0 && <span className="ml-1.5 text-[10.5px] font-normal text-mint">{g.nSel} choix</span>}</span>}
                      count={nf.format(g.total)}>
                      {g.items.map((o) => (
                        <LigneChoix key={o.code} dataAttr="data-ape" label={o.label} sub={nf.format(o.n)}
                          on={filters.pmApe.includes(o.code)} onClick={() => toggleApe(o.code)} />
                      ))}
                    </SousAccordion>
                  ))}
                </div>
              ) : <p className="mt-1 text-[10px] text-txt-dim">{fq.isLoading ? '…' : 'Aucune activité dans la portée courante.'}</p>}
            </div>

            {/* ── Nombre de dirigeants (min / max) — fourchette chiffrée. ── */}
            <div>
              <TitreSection titre="Nombre de dirigeants" info="Fourchette du nombre de dirigeants (INPI/RNE)." />
              <div className="mt-1 flex items-center gap-1.5">
                <NumField field="pmDirigMin" ph="min" /><span className="text-txt-dim">–</span><NumField field="pmDirigMax" ph="max" />
              </div>
            </div>

            {/* ── DIRIGEANTS — tranche d'âge (Moins de 50 / 50 à 69 / 70 et plus), LigneChoix. JAMAIS l'âge exact. ── */}
            <div data-prop-age-tranche>
              <TitreSection titre="Dirigeants" info="Tranche du dirigeant le plus âgé (INPI/RNE) — jamais l'âge exact. Un signal de succession possible." />
              <div className="mt-1 flex flex-col gap-0.5">
                {PM_AGE_TRANCHES.map((t) => (
                  <LigneChoix key={t.k} dataAttr="data-prop-age" label={t.l}
                    on={filters.pmAge.includes(t.k)} onClick={() => toggleAge(t.k)} />
                ))}
              </div>
            </div>
          </div>
          </fieldset>
        </div>
      </AccordionCat>
    </div>
  )
}

// VEILLE-2 (Lot 4) — la CRÉATION d'une veille de recherche depuis les filtres est RETIRÉE (plus de bouton
// « Créer une veille ») ; `enVeille` ne sert plus qu'à masquer le rituel « regard LABUSE » là où ce même
// panneau serait monté hors carte. La page Veille n'a plus que PARCELLE et RADAR.
export function FiltreLabuse({ onRetract, enVeille }: { onRetract?: () => void; enVeille?: boolean } = {}) {
  const { filters, setFilter, setFilters, setVerdict, commune, setCommunesFilter, setAnalyseRecap } = useApp()
  const analyseOn = filters.analyseLabuse
  // RETOURS-18 pt 21 — les QUATRE catégories sont EXCLUSIVES : une seule ouverte à la fois, toutes
  // fermées à l'ouverture du panneau. L'état d'ouverture est LEVÉ ici ; chaque AccordionCat est piloté.
  type Cat = 'communes' | 'terrain' | 'affiner' | 'proprietaire'
  const [openCat, setOpenCat] = useState<null | Cat>(null)
  const toggleCat = (c: Cat) => setOpenCat((o) => (o === c ? null : c))
  // RETOURS-18 pt 21 — « montrer plus » de communes : ~10 d'abord, puis « … N autres ».
  const [communesTout, setCommunesTout] = useState(false)
  const COMMUNES_INIT = 10
  // RETOURS-18 pt 21 — ÉTAT DU SOL en LigneChoix (3 lignes) avec la MÊME partition que l'ancien
  // ChipGroup : [] = tout coché (sans restriction) ; [AUCUN_SENTINEL] = rien coché ; sinon le
  // sous-ensemble stocké. Écriture store `etatSol` inchangée (rétro-compatible avec les vieux hash).
  const etatSolKeys = ETAT_SOL.map((o) => o.k)
  const etatSolSel = (filters.etatSol as string[]) ?? []
  const etatSolCoche = etatSolSel.length === 0 ? etatSolKeys
    : etatSolSel.includes(AUCUN_SENTINEL) ? [] : etatSolSel
  const toggleEtatSol = (k: string) => {
    const next = etatSolCoche.includes(k) ? etatSolCoche.filter((x) => x !== k) : [...etatSolCoche, k]
    setFilter('etatSol', (next.length === etatSolKeys.length ? [] : next.length === 0 ? [AUCUN_SENTINEL] : next) as never)
  }
  // RETOURS-18 pt 21 — résumés de choix pour les têtes fermées.
  const nZonage = filters.zonagePlu.length + filters.zonePlu.length
  const etatSolRestreint = etatSolCoche.length !== etatSolKeys.length
  const nTerrain = (filters.surfaceMin != null || filters.surfaceMax != null ? 1 : 0)
    + (nZonage > 0 ? 1 : 0) + (etatSolRestreint ? 1 : 0)
  const terrainBadge = nTerrain > 0 ? `${nTerrain} choix` : '—'
  const nAffiner = nAffinerActifs(filters)
  // M55-D stage 4 : interrupteur UNIFIÉ — analyseLabuse (persisté, URL) ⟺ verdict (carte). Éteint
  // par défaut : plus jamais « analyse active » quand l'utilisateur n'a rien allumé (bug mesuré).
  const setAnalyse = (v: boolean) => { setFilter('analyseLabuse', v); setVerdict(v) }
  // Reset : les DEUX étages + éteint l'interrupteur (retour à l'état vierge). M55-J : coupe
  // aussi le rituel (phase/snapshot) — jamais une carte-phrase orpheline après un reset.
  const resetTout = () => { setFilters(EMPTY_FILTERS); setVerdict(false); setPhase('idle'); setSnapFilters(null); setAnalyseRecap(null); setOpenCat(null); setCommunesTout(false) }
  // ANALYSE-1 — la TRAME entière (analyse coupée = tous les tiers) porte la ventilation par BANDE du
  // nouveau moteur (`bandes` dans la réponse /filtre). C'est la seule source du récapitulatif ; la
  // requête « retenues » (tier) a été retirée (le nouveau moteur ne parle plus de tiers).
  const trameQ = useQuery({ queryKey: ['filtre', filters, false], queryFn: () => getFiltre({ ...filters, analyseLabuse: false }, 0) })

  // ═══ M55-D stage 7 · COMPTEUR VIVANT — « N parcelles correspondent », mis à jour à chaque
  // changement de filtre : debounce 400 ms + AbortController (les appels obsolètes sont annulés).
  // TOUJOURS la réponse /filtre réelle (état courant de l'interrupteur), jamais une estimation.
  // Registre DISCRET — le rituel 3 s de la Révélation reste la cérémonie, intacte.
  const nActifs = countActiveFilters(filters)
  // FRONT-CHIFFRES-1 — le total de repli du rituel n'est plus un littéral figé (431 663, périmé à
  // chaque bascule de run) : on lit la notion servie `n_parcelles_ile` (/accueil/chiffres). Le
  // décompte réel reste `live` ; ce total ne sert que de cible d'animation quand `live` n'a pas
  // encore répondu, et disparaît (0) si l'endpoint échoue — jamais un chiffre inventé.
  const totalIleQ = useQuery({ queryKey: ['accueil-chiffres'], queryFn: getAccueilChiffres, staleTime: 60 * 60 * 1000 })
  const totalIle = totalIleQ.data?.parcelles ?? null
  // RETOURS-21 (pt 8) — compteur « N parcelles correspondent » sous 300 ms :
  //   · debounce ramené 400 → 120 ms (la frappe ne déclenche plus une rafale, mais l'actualisation
  //     démarre bien plus tôt) ;
  //   · passage à react-query (clé = filtres débouncés) : une COMBINAISON DÉJÀ VUE (staleTime 30 s)
  //     s'affiche INSTANTANÉMENT depuis le cache, sans réseau (≈ le débounce, bien < 300 ms) ;
  //   · `placeholderData` = valeur précédente : pour une combinaison NEUVE (comptage serveur ~1 s à
  //     froid), l'ANCIEN nombre reste affiché tout de suite (flottant, opacité), puis se CORRIGE à
  //     l'arrivée du compte exact — « estimé affiché tout de suite puis corrigé ».
  const [filtresDebounced, setFiltresDebounced] = useState(filters)
  useEffect(() => {
    const t = window.setTimeout(() => setFiltresDebounced(filters), 120)
    return () => window.clearTimeout(t)
  }, [filters])
  const countQ = useQuery({
    queryKey: ['filtre-count', filtresDebounced],
    queryFn: ({ signal }) => getFiltreCount(filtresDebounced, signal),
    staleTime: 30_000,
    placeholderData: (prev) => prev,
  })
  const live = countQ.data?.compte ?? null
  const liveLoading = countQ.isFetching

  // ═══ M55-D stage 5 · LA RÉVÉLATION — couche de PRÉSENTATION par-dessus l'état stage 4 (al/verdict
  // intouchés jusqu'au geste final). Décompte 3 s CONSTANT (rituel, décision Vic) ; pendant
  // l'animation la VRAIE requête /filtre part (refetch) — le résultat attend la fin pour se révéler.
  // Échec réseau pendant le décompte → interruption propre (jamais un faux succès). Le score est
  // PRÉ-CALCULÉ : le texte dit « application de vos critères », jamais « calcul du score ». ═══
  type Phase = 'idle' | 'counting' | 'revealed' | 'error'
  const [phase, setPhase] = useState<Phase>('idle')
  const phaseRef = useRef<Phase>('idle')
  phaseRef.current = phase
  const [countVal, setCountVal] = useState(0)
  // ═══ M55-J point 1 — INVARIANT : la carte d'analyse ne mélange JAMAIS deux runs. Tout ce
  // qu'elle affiche (effectif analysé, retenues, ventilation, récap des critères, périmètre)
  // provient du SNAPSHOT pris au lancement — pas des filtres live. Trois pièces figées à
  // `lancer()` : `fresh` (retenues + ventilation), `freshTrame` (effectif analysé = trame),
  // `snapFilters` (les critères du run, pour le récap/périmètre + le filet d'invalidation). ═══
  // ANALYSE-1 — le snapshot du run pour le récapitulatif = `freshTrame` (trame entière, avec la
  // ventilation par bande). L'ancien `fresh` (retenues/tier) a été retiré.
  const [freshTrame, setFreshTrame] = useState<Awaited<ReturnType<typeof getFiltre>> | null>(null)
  const [snapFilters, setSnapFilters] = useState<Filters | null>(null)
  const timerRef = useRef<number | null>(null)
  const rafRef = useRef<number | null>(null)
  // M55-G suite point 5 : la requête v2-modele (date du run pour le bandeau) est partie avec
  // le bandeau — la date du classement vit dans la modale « comprendre le classement ».
  // prefers-reduced-motion : décompte remplacé par une transition simple (courte)
  const reduced = typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  const RITUEL_MS = reduced ? 400 : 3000
  const lancer = () => {
    setPhase('counting'); setCountVal(0); setFreshTrame(null)
    // M55-J point 1 : SNAPSHOT du run — on fige les critères et on tire LES DEUX effectifs
    // (retenues + trame analysée) sur CES critères-là. La carte ne lira plus jamais les filtres
    // live : elle décrit ce run, un point c'est tout.
    const snap = filters
    setSnapFilters(snap)
    // M55-M point 3 : on FIGE aussi le récap des critères du run (complet, max=∞ → aucun « … » ;
    // la troncature d'affichage est CSS dans le bandeau). C'est CE snapshot que le bandeau
    // « ✓ Analyse LABUSE » portera — jamais l'état courant des filtres (même invariant M55-J p1).
    setAnalyseRecap(resumeCriteres(snap, CLIENT.signaux.labels, Infinity))
    // la VRAIE requête part MAINTENANT (appel direct, SANS retry : un échec interrompt le rituel
    // au lieu d'être masqué par les retries react-query au-delà des 3 s). ANALYSE-1 : son résultat
    // n'est plus stocké (le récapitulatif lit la trame `freshTrame`), mais l'appel reste — c'est LUI
    // qui DÉTECTE un échec réseau du run et bascule proprement en `error` (jamais un faux succès).
    getFiltre({ ...snap, analyseLabuse: true }, 0)
      .then(() => { /* succès : la révélation se fait à la fin du décompte */ })
      .catch(() => {
        if (phaseRef.current !== 'counting') return
        if (timerRef.current) window.clearTimeout(timerRef.current)
        if (rafRef.current) cancelAnimationFrame(rafRef.current)
        setPhase('error')
      })
    // la trame (effectif ANALYSÉ) du même run — le dénominateur de « retenues / analysées »
    getFiltre({ ...snap, analyseLabuse: false }, 0).then((r) => setFreshTrame(r)).catch(() => { /* filet plus bas */ })
    if (!reduced) {
      const t0 = performance.now()
      const cible = live ?? totalIle ?? 0
      const tick = (now: number) => {
        const p = Math.min(1, (now - t0) / RITUEL_MS)
        setCountVal(Math.round(cible * p * p * p))   // easing cubique : les chiffres ACCÉLÈRENT
        if (p < 1) rafRef.current = requestAnimationFrame(tick)
      }
      rafRef.current = requestAnimationFrame(tick)
    }
    // RETOURS-20 (pt 5) — fin du décompte : on arrive DIRECTEMENT sur les résultats (plus d'étape
    // de résumé « LABUSE a analysé… Voir les parcelles »). Si le run a échoué, le `.catch` a déjà
    // basculé en 'error' et vidé ce timer — on ne force donc jamais les résultats sur un échec.
    timerRef.current = window.setTimeout(() => { if (phaseRef.current === 'counting') voirParcelles() }, RITUEL_MS)
  }
  // ANALYSE-1 : l'échec réseau du run est détecté par le `.catch` de l'appel direct dans `lancer()`
  // (ci-dessus) ; l'ancien useEffect sur `on.isError` (requête retirée) n'a plus lieu d'être.
  useEffect(() => () => {   // démontage : aucun timer orphelin
    if (timerRef.current) window.clearTimeout(timerRef.current)
    if (rafRef.current) cancelAnimationFrame(rafRef.current)
  }, [])
  // geste final : l'analyse s'ALLUME (état stage 4, biunivoque) et la section se rétracte
  const voirParcelles = () => { setPhase('idle'); setAnalyse(true); onRetract?.() }
  // M55-F point 3 — le tri factuel : montrer la liste + la carte SANS l'opinion LABUSE. verdict
  // ON (les résultats s'affichent) mais analyseLabuse OFF (tri factuel, toutes les parcelles).
  // C'est le SEUL geste qui découple verdict de analyseLabuse (le bandeau des résultats le dit).
  const voirFactuel = () => { setPhase('idle'); setFilter('analyseLabuse', false); setVerdict(true); onRetract?.() }
  // M55-M point 2 — « Changer les filtres » (ex-« Relancer l'analyse »). CONSTAT : l'ancien bouton
  // rejouait le rituel sur les filtres FIGÉS (même entrée → même résultat) — il ne changeait rien.
  // L'action HONNÊTE = DÉFIGER les filtres et rendre la main : on coupe `analyseLabuse` (le formulaire
  // redevient éditable, `analyseActive` retombe) SANS toucher `verdict` — le listing reste affiché
  // (il passe en tri factuel) pendant qu'on ajuste les critères, puis on relance « Demander à LABUSE ».
  // (≠ « Désactiver l'analyse » qui, lui, quitte la vue résultats : setAnalyse(false) éteint verdict.)
  const changerFiltres = () => { setFilter('analyseLabuse', false); setPhase('idle'); setSnapFilters(null); setAnalyseRecap(null) }
  // M55-J point 1 : « analyse active » = le rituel est lancé (décompte/révélation) OU l'analyse
  // est allumée. Dans cet état les FILTRES SONT FIGÉS (fieldset désactivé plus bas) — un seul run
  // décrit, un seul effectif à l'écran.
  const analyseActive = analyseOn || phase === 'counting' || phase === 'revealed'
  // M55-J point 1 : la carte décrit le SNAPSHOT (snapFilters), pas les filtres live. Hors analyse
  // (état d'appel), il n'y a pas de carte-phrase → on retombe sur les filtres live sans effet.
  const cardFilters = snapFilters ?? filters
  const nCom = cardFilters.communes.length
  const perimetre = nCom === 1 ? cardFilters.communes[0] : nCom > 1 ? `${nCom} communes` : (commune ?? 'La Réunion')
  const recap = resumeCriteres(cardFilters, CLIENT.signaux.labels)
  // ANALYSE-1 — le récapitulatif décrit le SNAPSHOT (freshTrame), pas les filtres live. `analyseTotal`
  // = total de la trame analysée ; `bandesReveal` = ventilation par BANDE du nouveau moteur (comptes
  // bruts, aucun quota/rang/percentile). En phase revealed/counting on lit le snapshot ; ailleurs le live.
  const analyseTotal = (phase === 'revealed' || phase === 'counting') ? freshTrame?.compte : trameQ.data?.compte
  const bandesReveal = ((phase === 'revealed' || phase === 'counting') ? freshTrame?.bandes : trameQ.data?.bandes) ?? null
  const bandeTotalReveal = bandesReveal ? BANDE_ORDER.reduce((a, b) => a + (bandesReveal[b] ?? 0), 0) : null
  // M55-J point 1 · FILET DE SÉCURITÉ : si un chemin EXTERNE (sélecteur commune du header, URL,
  // retour arrière) déplace les filtres live pendant que le rituel décrit un run, la carte
  // s'INVALIDE (état neutre invitant à relancer) plutôt que d'afficher un chiffre périmé.
  const stale = phase === 'revealed' && snapFilters != null && !filtersEqual(filters, snapFilters)

  return (
    <div className="card-elev px-3 py-2">
      {/* ═══════ M55-J points 1 & 6 / M55-M point 3 — LES FILTRES SONT FIGÉS PENDANT L'ANALYSE ═══════
          Arbitrage « faire DISPARAÎTRE » : pendant l'analyse (analyseActive), les contrôles de
          filtres sont retirés → impossible d'éditer un filtre, aucun run mixte, et la section reste
          compacte pour libérer la hauteur au listing (M55-M point 1).
          M55-M point 3 : le bloc « ANALYSE EN COURS / Filtres figés — … » est SUPPRIMÉ partout
          (y compris décompte et post-analyse) — les critères du run vivent désormais dans le
          bandeau « ✓ Analyse LABUSE » (store.analyseRecap, figé au lancement). Ici, quand l'analyse
          est active, on ne rend simplement RIEN (le formulaire réapparaît via « Changer les
          filtres » ou « Désactiver »). */}
      {!analyseActive && (
      <>
      {/* ═══════ RETOURS-18 pt 21 — QUATRE catégories EXCLUSIVES, toutes fermées à l'ouverture, un
          seul numéro gris + titre blanc gras sur une ligne, le résumé du choix à droite au repli. ═══════ */}

      {/* ─── 1 · COMMUNES — maître du périmètre. « Toutes les communes » en tête ET par défaut ;
          ~10 communes puis « … N autres » (montrer plus). Multi-sélection, style unique vert/coche. ─── */}
      <div data-communes-filtre>
        <AccordionCat num="1" titre="Communes" open={openCat === 'communes'} onToggle={() => toggleCat('communes')}
          badge={filters.communes.length ? (filters.communes.length === 1 ? filters.communes[0] : `${filters.communes.length} choix`) : 'Toutes'}
          info="Le périmètre des résultats. « Toutes les communes » = toute l’île (aucune restriction).">
          <div className="flex flex-col gap-0.5">
            <LigneChoix dataAttr="data-communes-toutes" label="Toutes les communes"
              on={filters.communes.length === 0} onClick={() => setCommunesFilter([])} />
            {(communesTout ? CP_COMMUNES : CP_COMMUNES.slice(0, COMMUNES_INIT)).map(([cp, nom]) => (
              <LigneChoix key={cp} label={nom} on={filters.communes.includes(nom)}
                onClick={() => setCommunesFilter(
                  filters.communes.includes(nom) ? filters.communes.filter((c) => c !== nom) : [...filters.communes, nom])} />
            ))}
            {!communesTout && CP_COMMUNES.length > COMMUNES_INIT && (
              <button type="button" data-communes-plus onClick={() => setCommunesTout(true)}
                className="rounded-md px-2.5 py-1.5 text-left text-[12px] text-txt-dim transition-colors duration-quick hover:bg-mint/15 hover:text-txt">
                … {CP_COMMUNES.length - COMMUNES_INIT} autres
              </button>
            )}
          </div>
        </AccordionCat>
      </div>

      {/* ─── 2 · LE TERRAIN — surface + zonage (sous-accordéons par famille) + état du sol (LigneChoix). ─── */}
      <AccordionCat cls="mt-3" num="2" titre="Le terrain" open={openCat === 'terrain'} onToggle={() => toggleCat('terrain')}
        badge={terrainBadge}
        info="Des faits objectifs (surface, zonage, état du sol) — valables sans aucune analyse.">
      <div className="flex flex-col gap-4">
        <div>
          <p className="label-caps text-txt-dim">Surface de la parcelle</p>
          <div className="mt-1 flex items-center gap-1.5"><NumField field="surfaceMin" ph="min" /><span className="text-txt-dim">–</span><NumField field="surfaceMax" ph="max" suffix="m²" /></div>
        </div>
        <div>
          <p className="label-caps text-txt-dim">Zonage</p>
          <ZoneSelector />
        </div>
        <div>
          <p className="label-caps text-txt-dim">État du sol</p>
          {/* RETOURS-18 pt 21 — nu + bâti PARTITIONNENT les parcelles (tout coché = sans restriction) ;
              rendus en LigneChoix (vert opaque + coche si inclus), MÊME logique que l'ancien ChipGroup
              partition (vide = tout ; sentinelle = rien ; sinon sous-ensemble) — écriture store inchangée. */}
          <div className="mt-1 flex flex-col gap-0.5">
            {ETAT_SOL.map((o) => (
              <LigneChoix key={o.k} dataAttr="data-etat-sol" label={o.l}
                on={etatSolCoche.includes(o.k)} onClick={() => toggleEtatSol(o.k)} />
            ))}
          </div>
        </div>
      </div>
      </AccordionCat>

      {/* ─── 3 · AFFINER LA RECHERCHE — copro / risques / hauteur / emprise / ZFANG / FRR / signaux. ─── */}
      <AccordionCat cls="mt-3" num="3" titre="Affiner la recherche" open={openCat === 'affiner'} onToggle={() => toggleCat('affiner')}
        badge={nAffiner > 0 ? `${nAffiner} choix` : '—'}
        info="Des critères complémentaires (copropriété, risques, dispositifs fiscaux, signaux de vie).">
        <AffinerBody />
      </AccordionCat>

      {/* ─── 4 · LE PROPRIÉTAIRE — qui détient / forme juridique / activité / dirigeants (DGFiP). ─── */}
      <SectionProprietaire open={openCat === 'proprietaire'} onToggle={() => toggleCat('proprietaire')} />

      {/* ═══════ SECTION « LE BIEN » RETIRÉE DU PANNEAU (FILTRE, Vic 23/08/2026) ═══════
          Les 4 facettes M137 (« On peut encore construire » / « Construite au maximum » = droitsResiduels ;
          « Propriétaire public » = proprietaireType 'public' ; « Assemblage même proprio » = signaux
          'assemblage') NE S'AFFICHENT PLUS ici. Le BACKEND ne bouge pas — les critères restent servis
          pour qui les demande (api.ts envoie toujours droits_residuels / proprietaire_type / signaux).
          ACCÈS RESTANTS après retrait :
            · 'assemblage' → toujours posable par le COPILOTE (compter_parcelles, param signaux ; setFilters
              direct, hors hash) + deep-link URL — PAS orphelin.
            · droitsResiduels ('encore'/'maximum') et proprietaireType 'public' → PLUS AUCUNE UI ni route
              Copilote (seul le deep-link URL les porte encore). Le panneau était leur SEUL accès visible.
          NETTOYAGE de l'état résiduel : App.tsx purge ces 3 clés à la restauration depuis l'URL, pour
          qu'aucun filtre coché avant le retrait ne reste actif sans contrôle pour le décocher. */}

      {/* ═══════ COMPTEUR VIVANT (stage 7) — visible dès qu'un filtre est posé ═══════ */}
      {nActifs > 0 && (
        <p data-compteur-vivant aria-live="polite"
          className={`mt-3 text-[11.5px] tabular-nums transition-opacity duration-quick ${liveLoading ? 'opacity-50' : 'opacity-100'} ${live === 0 ? 'text-st-creuser' : 'text-txt-mut'}`}>
          {live == null ? '…' : live === 0 ? CLIENT.compteur.zero
            : <><b className="text-txt">{nf.format(live)}</b> parcelles correspondent à vos critères</>}
        </p>
      )}
      {/* VEILLE-2 (Lot 4) — la CRÉATION d'une veille de recherche est RETIRÉE (plus de bouton « Créer une
          veille » depuis les filtres) : la page Veille n'a plus que PARCELLE et RADAR. */}
      </>
      )}

      {/* ═══════ ÉTAGE ② — LE REGARD LABUSE (stage 5 : LA RÉVÉLATION — appel, décompte, phrase) ═══════
          M55-K point 3 : le CADRE vert n'entoure QUE le rituel (décompte/révélation). À l'état
          post-analyse (analyseOn + idle : Relancer/Désactiver) le cadre DISPARAÎT — les deux
          boutons vivent seuls, sans conteneur encadré. L'appel garde son groupe sobre.
          RECETTE-2 LOT B : en VEILLE (critères), ce bloc est RETIRÉ — « Voir les parcelles » et
          « Demander une analyse LABUSE » n'y ont pas leur place (on y déclare ce qu'on surveille ;
          explorer/analyser se fait ailleurs). Retrait de surface : aucun endpoint touché. */}
      {!enVeille && (
      <div className={`mt-4 transition-colors duration-soft ${
        phase === 'counting' || phase === 'revealed' ? 'rounded-xl border border-mint/60 bg-mint/[0.07] p-3'
          : analyseOn ? '' : 'rounded-xl border border-line-2 bg-surface-2/40 p-3'}`}>
        {phase === 'counting' ? (
          /* ── 2. LE DÉCOMPTE — 3 s constantes ; texte honnête (on APPLIQUE des critères) ── */
          <div data-decompte className="py-2 text-center" aria-live="polite">
            <p className="font-display text-[24px] font-bold text-mint tabular-nums">
              {reduced ? '…' : nf.format(countVal)}
              {!reduced && live != null && countVal >= live && <span aria-hidden> ✓</span>}
            </p>
            <p className="mt-1 text-[11px] leading-snug text-txt-dim">
              {/* RETOURS-20 (pt 4) — « LABUSE croise ses 99 sources (…) pour classer les N parcelles
                  de [commune]… », avec le N et la commune réels (périmètre du run). */}
              {CLIENT.revelation.decompteCroise(live ?? totalIle ?? 0, perimetre)}…
            </p>
          </div>
        ) : phase === 'error' ? (
          /* ── échec réseau : état d'erreur honnête, jamais un faux succès ── */
          <div data-analyse-erreur className="py-1">
            <p className="text-[12px] leading-snug text-st-ecartee">{CLIENT.revelation.erreur}</p>
            <button onClick={lancer}
              className="mt-2 rounded-lg border border-line-2 px-3 py-1 text-[11.5px] text-txt transition-colors duration-quick hover:border-mint hover:text-mint">
              {CLIENT.revelation.reessayer}
            </button>
          </div>
        ) : phase === 'revealed' && stale ? (
          /* ── FILET (M55-J point 1) : les filtres ont bougé par un chemin externe → carte
             invalidée, jamais un chiffre périmé. Un seul geste : relancer sur les nouveaux
             critères (le rituel repart proprement sur un snapshot frais). ── */
          <div data-analyse-perimee className="py-1">
            <p className="text-[12px] leading-snug text-st-creuser">{CLIENT.revelation.perime}</p>
            <button onClick={lancer}
              className="mt-2 w-full rounded-lg bg-mint py-2 font-display text-[12.5px] font-bold text-mint-ink transition-[filter] duration-quick hover:brightness-110">
              {CLIENT.revelation.relancerCta}
            </button>
          </div>
        ) : phase === 'revealed' ? (
          /* ── 3. LA PHRASE — nombres RÉELS de /filtre (compte + ventilation par tier).
             M55-G point 7 : la phrase ne vit QU'AU moment du reveal — le panneau ré-ouvert
             après analyse ne la répète plus (le récit des nombres vit dans la zone résultats,
             un seul récit, M55-F point 1). ── */
          <div data-phrase>
            <p className="text-[11.5px] leading-relaxed text-txt-mut">
              {/* M55-H point 10 : jamais « 0 parcelles » pendant que la trame charge — la phrase
                  d'intro attend un total connu (le reste s'affiche sans elle). M55-J point 1 :
                  l'effectif ANALYSÉ vient UNIQUEMENT du snapshot (freshTrame → analyseTotal),
                  JAMAIS du live — sinon on afficherait brièvement les retenues comme analysées. */}
              {analyseTotal != null && <>{CLIENT.revelation.phraseIntro(analyseTotal, perimetre)}{' '}</>}
              {CLIENT.revelation.phraseSelon(recap)}
            </p>
            {bandeTotalReveal === 0 ? (
              <p data-phrase-zero className="mt-1 text-[12.5px] font-medium leading-snug text-st-creuser">{CLIENT.revelation.phraseZero}</p>
            ) : bandesReveal && (
              /* ANALYSE-1 — la ventilation par BANDE du nouveau moteur : Excellente / Bonne / À étudier /
                 Faible / Sans potentiel constructible / Analyse incomplète. Comptes bruts (aucun quota),
                 couleurs franches (BANDE_META), jamais un chiffre de score. « Sans potentiel » et
                 « Analyse incomplète » ne sont jamais masqués. */
              <div data-phrase-bandes className="mt-1.5 flex flex-wrap gap-x-3 gap-y-1 text-[12px] leading-snug">
                {BANDE_ORDER.map((b) => (bandesReveal[b] ?? 0) > 0 && (
                  <Tip key={b} side="top" tip={BANDE_META[b].long}>
                    <span className="inline-flex items-center gap-1">
                      <span className="inline-flex h-2 w-2 rounded-full" style={{ background: BANDE_META[b].color }} />
                      <b className="tabular-nums" style={{ color: BANDE_META[b].color }}>{nf.format(bandesReveal[b] ?? 0)}</b>
                      <span className="text-txt-dim">{BANDE_META[b].label}</span>
                    </span>
                  </Tip>
                ))}
              </div>
            )}
            {phase === 'revealed' && (
              /* ── 4. LE GESTE FINAL — l'analyse s'allume, la section se rétracte ── */
              <Bouton data-voir-parcelles niveau="primaire" ton="vert" onClick={voirParcelles} className="mt-3 w-full">
                {CLIENT.revelation.voir}
              </Bouton>
            )}
          </div>
        ) : !analyseOn ? (
          /* ── 1. L'APPEL — LES deux boutons, sans bandeau (M55-G suite point 5). M55-H
             point 3 : GROUPE net — marges constantes (gap-2), même largeur, secondaire
             franc (fond + bordure visibles) AU-DESSUS, primaire dominant (plus haut, flèche
             dessinée — même patron que « Commencer »). La carte ne bouge QU'AU geste. ── */
          <div data-appel className="flex flex-col gap-2">
            {/* RETOURS-19 (pt 8) — ORDRE du pied : « Voir la liste brute » D'ABORD (secondaire franc),
                PUIS « Analyser avec LABUSE » (primaire dominant), PUIS « Réinitialiser » (lien discret).
                La ligne « N à instruire · N écartées » reste retirée (le compteur de correspondances suffit). */}
            <Bouton data-voir-factuel niveau="secondaire" ton="vert" onClick={voirFactuel} className="w-full">
              Voir la liste brute
            </Bouton>
            <Bouton data-analyser-btn niveau="primaire" ton="vert" onClick={lancer} className="w-full">
              Analyser avec LABUSE
            </Bouton>
            <button data-reinitialiser onClick={resetTout}
              className="mx-auto min-h-7 px-1 py-0.5 text-[11px] text-txt-dim underline decoration-txt-dim/30 underline-offset-2 transition-colors duration-quick hover:text-danger hover:decoration-danger-line">
              Réinitialiser
            </button>
          </div>
        ) : null}
        {analyseOn && phase === 'idle' && (
          <div className="mt-3 flex flex-col gap-3">
            {/* M55-G suite point 3 (décision Vic) : l'état post-analyse ne porte PLUS AUCUN
                contenu — chips verdict/tiers, motifs, constructibilité, potentiel, SDP,
                capacité, veille, copros et notes RETIRÉS (0-caller). Ne restent que les deux
                gestes : « Relancer l'analyse » et « désactiver l'analyse ». Conséquence actée :
                le filtrage par tier post-analyse quitte ce panneau (les champs gardent leur
                persistance URL — vieux liens compatibles). */}

            {/* M55-J point 2 / M55-K point 3 / M55-M point 2 : DEUX BOUTONS (ActionBtn) —
                « Changer les filtres » = action principale (primary, mint plein) : défige les
                filtres et rend la main (le listing reste, en tri factuel) ; « Désactiver
                l'analyse » = contour ROUGE (danger) : quitte la vue résultats. Traitement visuel
                inchangé (fond vert pour l'action principale). Marges constantes, même largeur. */}
            <div className="flex gap-2 pt-1">
              <ActionBtn variant="primary" dataAttr="data-changer-filtres" onClick={changerFiltres}>
                {CLIENT.revelation.changerFiltres}
              </ActionBtn>
              <ActionBtn variant="danger" dataAttr="data-desactiver"
                onClick={() => { setAnalyse(false); setSnapFilters(null); setPhase('idle'); setAnalyseRecap(null) }}>
                {CLIENT.revelation.desactiver}
              </ActionBtn>
            </div>
          </div>
        )}
      </div>
      )}

      {/* M55-D stage 7 (décision Vic) : plus AUCUNE section pédagogique dans le panneau —
          « Puis-je construire ? » retirée (les repères droit du sol vivent en fiche). */}

      {/* FILTRE-NETTOYAGE #5 — le bloc « Réinitialiser » isolé en bas (filet + respiration) est
          RETIRÉ : le geste vit désormais dans le bloc d'actions (data-appel), avec « Voir » et
          « Analyser ». Toujours masqué pendant l'analyse (les filtres sont figés — Désactiver d'abord). */}
    </div>
  )
}
