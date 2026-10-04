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
import { Tip } from '../Tip'
import { Bouton } from '../ui/Bouton'
import { Case } from '../ui/Case'
import { Chevron } from '../ui/Chevron'
import { Chip } from '../ui/Chip'
import { useFiltre } from './filtreContext'   // M120 — binding partagé (carte OU cadrage projet)

// ANALYSE-1 — le récapitulatif de la Révélation parle le NOUVEAU moteur (bandes de Score) ; l'ancien
// helper `defTip` (tooltip des paliers Priorité/À suivre…) est retiré avec la ventilation par tier.

// M55-G suite point 3 : CONSTRUCTIBILITE et les chips de verdict/motif ont quitté l'état
// post-analyse (0-caller) — les champs de filtre restent dans le store + l'URL.
// M101 A2 (arbitrage Vic) : DEUX entrées — les tiers internes (saturé/révélé) sortent du
// filtre (information de fiabilité, dite en fiche via le motif). Partition exacte sur
// l'emprise bâtie (seuil 5 %, backend app.py etat_sol) : nu ∪ bâti = parc filtrable.
export const ETAT_SOL = [
  { k: 'nu', l: 'Terrain nu' },
  { k: 'bati', l: 'Terrain bâti' },
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
  const [openFam, setOpenFam] = useState<string | null>(null)
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
      {familles.map((f) => {
        const zonesSelFam = f.zones.filter((z) => selZones.includes(z.zone)).length
        const ouverte = openFam === f.fam
        const enModeFamille = selFam.includes(f.fam)
        return (
          <div key={f.fam} className="rounded-lg border border-line-2 bg-surface-3/60">
            {/* M137-B (Vic) — TOUTE la ligne ouvre l'accordéon (pastille, compte, chevron) : le lien
                « zones… » disparaît, un chevron à droite dit ouvert/fermé. Le choix de la famille
                entière n'est plus sur la ligne — il est le PREMIER item du menu (« U » seul). */}
            <button data-zones-fam={f.fam} aria-expanded={ouverte} onClick={() => setOpenFam(ouverte ? null : f.fam)}
              className="flex w-full items-center gap-2 px-2 py-1 text-left">
              <span className={`rounded-full border px-2.5 py-0.5 text-[11px] ${
                enModeFamille ? 'border-mint bg-mint/20 font-medium text-txt-hi' : 'border-line-2 bg-surface-3 text-txt-mut'}`}>
                {f.fam}
              </span>
              <span className="flex-1 text-[10.5px] text-txt-dim">
                {zq.data ? `${nf.format(f.n)} parcelles · ${f.zones.length} zones` : '…'}
                {zonesSelFam > 0 && <span className="text-mint"> · {zonesSelFam} choisie{zonesSelFam > 1 ? 's' : ''}</span>}
              </span>
              {/* DA-FIX-3 Lot 5 (DA-031) — chevron d'accordéon partagé (fermé ▶ / ouvert ▼). */}
              <Chevron open={ouverte} />
            </button>
            {ouverte && (
              <div className="flex max-h-44 flex-col gap-0.5 overflow-y-auto border-t border-line-2 px-2 py-1.5">
                <button data-zone-toutes={f.fam} onClick={() => choisirFamille(f.fam)}
                  className={`flex items-center gap-2 rounded px-1 py-0.5 text-left text-[11px] transition-colors duration-quick hover:bg-surface-3 ${
                    enModeFamille ? 'font-medium text-mint' : 'text-txt'}`}>
                  <span className="w-3 text-center">{enModeFamille ? '✓' : ''}</span>
                  <span>{f.fam}<span className="text-txt-dim"> seul · toute la famille</span></span>
                  <span className="ml-auto text-[10px] text-txt-dim">{zq.data ? nf.format(f.n) : '…'}</span>
                </button>
                {f.zones.map((z) => {
                  const on = selZones.includes(z.zone)
                  return (
                    <button key={z.zone} data-zone={z.zone} onClick={() => choisirZone(z.zone)}
                      className={`flex items-center gap-2 rounded px-1 py-0.5 text-left text-[11px] transition-colors duration-quick hover:bg-surface-3 ${
                        on ? 'font-medium text-txt-hi' : 'text-txt'}`}>
                      <span className="w-3 text-center text-mint">{on ? '✓' : ''}</span>
                      <span>{z.zone}</span>
                      <span className="ml-auto text-[10px] text-txt-dim">{nf.format(z.n)}</span>
                    </button>
                  )
                })}
                {f.zones.length === 0 && (
                  <p className="px-1 py-1 text-[10.5px] text-txt-dim">
                    Aucune zone de cette famille dans la portée courante.
                  </p>
                )}
              </div>
            )}
          </div>
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

export function NumField({ field, ph, suffix }: { field: keyof Filters; ph: string; suffix?: string }) {
  const { filters, setFilter } = useFiltre()
  const v = filters[field] as number | null
  return (
    <div className="flex items-center gap-1">
      <input type="number" inputMode="numeric" placeholder={ph}
        value={v ?? ''} onChange={(e) => setFilter(field, (e.target.value === '' ? null : Number(e.target.value)) as never)}
        className="w-[68px] rounded-md border border-line-2 bg-transparent px-2 py-1 text-[11px] text-txt-hi placeholder:text-txt-dim focus:border-mint focus:outline-none" />
      {suffix && <span className="text-[10px] text-txt-dim">{suffix}</span>}
    </div>
  )
}

// RECETTE-1 (E2, Vic 04/10) — le GROUPE « CAPACITÉ » (CapaciteSection : logements possibles ≥ N +
// destination ; SDP restante / Déjà bâti d'« Affiner ») est ENTIÈREMENT RETIRÉ. Les clés restent
// inertes côté store ⇒ un vieux hash / une vue / une veille s'ouvre sans erreur (clé ignorée).

// RETOURS-14 P5 — SECTION REPLIABLE « AFFINER LA RECHERCHE », FERMÉE PAR DÉFAUT, tout en bas du panneau.
// Y sont REGROUPÉS (aucun filtre supprimé — simple relocalisation) : ZFANG (zone franche), FRR (ruralités)
// — qui quittent la section « 2 · Le terrain » — et les Signaux de vie — qui quittaient la section « 4 ».
// Chevron de la charte (ui/Chevron), titre au style des autres sections (label-caps text-txt-mut).
function AffinerRecherche() {
  const { filters, setFilter } = useFiltre()
  const [ouvert, setOuvert] = useState(false)
  const nSig = filters.signaux.filter((s) => SIGNAUX_KEYS.includes(s)).length
  // KELFONCIER-FIX-2 (Lot C) — la section repliée accueille désormais les filtres bâti/capacité
  // descendus de la façade (copro, hauteur, emprise, SDP, déjà bâti). Le compteur du repli les
  // recense (sinon, section fermée, un filtre actif serait invisible) — ce n'est PAS le badge
  // « Filtres (N) » global (inchangé), juste l'indicateur local de cette section.
  const nAffiner = nSig + (filters.horsCopro ? 1 : 0)   // RECETTE-1 E2 — plus de SDP/Déjà bâti (Capacité retirée)
    + (filters.hauteurMin != null || filters.hauteurMax != null ? 1 : 0)
    + (filters.empriseMin != null || filters.empriseMax != null ? 1 : 0)
  return (
    <div data-affiner className="mt-4">
      <button data-affiner-toggle aria-expanded={ouvert} onClick={() => setOuvert((v) => !v)}
        className="group flex w-full items-center gap-1.5 text-left transition-colors duration-quick">
        <Chevron open={ouvert} />
        <span className="label-caps text-txt-mut group-hover:text-txt-hi">Affiner la recherche</span>
        {nAffiner > 0 && <span className="ml-auto shrink-0 rounded-full bg-mint/20 px-1.5 py-0.5 text-[10px] font-medium text-mint tabular-nums">{nAffiner}</span>}
      </button>
      {ouvert && (
        <div className="gcard mt-2 flex flex-col gap-3 p-3">
          {/* KELFONCIER-FIX-2 (Lot C) — filtres descendus de la façade (prédicats inchangés). */}
          {/* KELFONCIER-FIX-1 (Lot E) — case « Sans copropriété » : écarte les parcelles en copropriété
              (RNIC/DVF, s2.copro). Backend `hors_copro` (hash hc), compteur/veille/Mes vues/badge câblés. */}
          <div>
            <p className="label-caps text-txt-dim">Copropriété</p>
            <Case data-filtre-hors-copro className="mt-1"
              checked={filters.horsCopro}
              onChange={(e) => setFilter('horsCopro', e.target.checked)}
              label="Sans copropriété" />
            <p className="mt-1 text-[10px] leading-snug text-txt-dim">Écarte les parcelles en copropriété (immatriculation RNIC ou copro DVF).</p>
          </div>
          {/* KELFONCIER-FIX-1 (Lot D) — FILTRES BÂTI : la MÊME donnée que la fiche §3 Bâti. Hauteur LiDAR
              faîtage (batiment_hauteur_lidar, id registre le_bien.hauteur_bati_m) et emprise bâtie en %
              (taux_emprise_pct du run servi, la colonne d'« État du sol »). Compteur SQL, ET avec le reste. */}
          <div>
            <p className="label-caps text-txt-dim">Hauteur du bâti (LiDAR)</p>
            <div className="mt-1 flex items-center gap-1.5"><NumField field="hauteurMin" ph="min" /><span className="text-txt-dim">–</span><NumField field="hauteurMax" ph="max" suffix="m" /></div>
            <p className="mt-1 text-[10px] leading-snug text-txt-dim">Faîtage mesuré au LiDAR HD (la hauteur de la fiche §Bâti) ; les parcelles au bâti non mesuré n’entrent pas dans une fourchette.</p>
          </div>
          <div>
            <p className="label-caps text-txt-dim">Emprise bâtie</p>
            <div className="mt-1 flex items-center gap-1.5"><NumField field="empriseMin" ph="min" /><span className="text-txt-dim">–</span><NumField field="empriseMax" ph="max" suffix="%" /></div>
            <p className="mt-1 text-[10px] leading-snug text-txt-dim">Part de la parcelle déjà couverte par du bâti (run servi) — la même que « État du sol ».</p>
          </div>
          {/* RECETTE-1 (E2) — « SDP restante » et « Déjà bâti » (part de l'encart Capacité) RETIRÉS
              de « Affiner la recherche » avec le reste de la Capacité. */}
          {/* COUCHES-2 point 4 — filtre par STATUT ZFANG / FRR de la commune. SOURCE UNIQUE
              (territoire_fiscal) : le même statut peint la carte et s'affiche sur la fiche commune. */}
          <div>
            <p className="label-caps text-txt-dim">ZFANG — zone franche</p>
            <div className="mt-1"><ChipGroup field="zfangRegime" options={[{ k: 'renforce', l: 'Renforcée' }, { k: 'standard', l: 'Standard' }]} /></div>
          </div>
          <div>
            <p className="label-caps text-txt-dim">FRR — ruralités</p>
            <div className="mt-1"><ChipGroup field="frrClassement" options={[{ k: 'totalite', l: 'Totalité' }, { k: 'partie', l: 'En partie' }, { k: 'hors', l: 'Hors dispositif' }]} /></div>
          </div>
          {/* Signaux de vie (M55-D stage 6 · M55-G suite point 4) — ÉVÉNEMENTS SOURCÉS, filtrables SANS
              analyse (pas des jugements). OU entre signaux du groupe, ET avec le reste. */}
          <div data-signaux-vie>
            <TitreSection titre="Signaux de vie"
              info="Des événements sourcés, cumulables — une parcelle correspond si au moins un des signaux cochés est présent. Chaque signal porte son propre « i » (source)." />
            <div className="gcard mt-2 flex flex-wrap gap-1.5 p-3">
              {SIGNAUX_KEYS.map((k) => <SignalChip key={k} k={k} />)}
            </div>
          </div>
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

// Puce multi-sélection alimentée par les facettes (label + compte n) ; la valeur portée = le code.
function FacetteChip({ code, label, n, on, onToggle, disabled }:
  { code: string; label: string; n: number; on: boolean; onToggle: (code: string) => void; disabled?: boolean }) {
  return (
    <button type="button" disabled={disabled} onClick={() => onToggle(code)}
      className={`flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[11px] transition-colors duration-quick disabled:opacity-40 ${
        on ? 'border-mint bg-mint/20 font-medium text-txt-hi'
          : 'border-line-2 bg-surface-3 text-txt-mut hover:border-mint/50 hover:text-txt'}`}>
      <span>{label}</span>
      <span className="tabular-nums text-txt-dim">{nf.format(n)}</span>
    </button>
  )
}

// KELFONCIER-FIX-1 (Lot B) — les trois TRANCHES d'âge du dirigeant (jamais l'âge exact).
const PM_AGE_TRANCHES = [
  { k: 'moins50', l: '< 50 ans' },
  { k: '50_69', l: '50–69 ans' },
  { k: '70plus', l: '≥ 70 ans' },
]

export function SectionProprietaire() {
  const { filters, setFilter } = useFiltre()
  const [open, setOpen] = useState(false)
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

  return (
    <div data-section-proprietaire className="mt-4">
      <button type="button" onClick={() => setOpen((o) => !o)} aria-expanded={open}
        className="group flex w-full items-center gap-2 text-left">
        <Chevron open={open} />
        <span className="label-caps text-txt-mut group-hover:text-txt-hi">Propriétaire</span>
        {nActifsProp > 0 && (
          <span className="ml-auto rounded-full bg-mint/20 px-1.5 py-0.5 text-[10px] font-medium text-mint tabular-nums">{nActifsProp}</span>
        )}
      </button>

      {open && (
        <div className="gcard mt-2 flex flex-col gap-3 p-3">
          {/* En-tête : source + millésime, et l'état de couverture (jamais un zéro muet). */}
          <p className="text-[10.5px] leading-snug text-txt-dim">
            {fq.isLoading ? 'Chargement…'
              : fac ? <>Source DGFiP · millésime {fac.millesime}</> : 'Données propriétaire indisponibles.'}
          </p>
          {fac && !couvert && (
            <p data-prop-non-couvert className="rounded-md bg-surface-2/80 px-2 py-1 text-[10.5px] text-st-creuser">
              Non couvert pour cette commune — les critères propriétaire sont indisponibles ici.
            </p>
          )}

          {/* ── Qui détient : Particulier / Société (personne morale) / Indifférent ──
              « Particulier » = aucune personne morale connue sur la parcelle (349 597, prédicat de l'audit). */}
          <div>
            <p className="label-caps text-txt-dim">Qui détient</p>
            <div className="mt-1 flex flex-wrap gap-1.5">
              <Chip on={particulier} onClick={() => setParticulier(!particulier)}>Particulier</Chip>
              <Chip on={pmOui} onClick={() => { setFilter('personneMorale', true); setParticulier(false) }}>Société</Chip>
              <Chip on={!pmOui && !particulier} onClick={() => { setFilter('personneMorale', false); setParticulier(false) }}>Indifférent</Chip>
            </div>
            <p className="mt-1 text-[10px] leading-snug text-txt-dim">« Particulier » = aucune société connue sur la parcelle ; « Société » = détenue par une personne morale (SCI, SA…).</p>
          </div>

          {/* Les critères FINS ne valent que sur des personnes morales — grisés si « Particulier ». */}
          <fieldset disabled={dis || particulier} className={(dis || particulier) ? 'pointer-events-none opacity-50' : ''}>
          <div className="flex flex-col gap-3">
            {/* ── Dénomination + autocomplétion ── */}
            <div className="relative">
              <p className="label-caps text-txt-dim">Dénomination</p>
              <input type="text" value={denomInput} placeholder="Ex. SCI du Littoral"
                onChange={(e) => { setDenomInput(e.target.value); setShowSug(true); if (e.target.value.trim() === '') setFilter('pmDenom', null) }}
                onFocus={() => setShowSug(true)}
                onBlur={() => window.setTimeout(() => setShowSug(false), 150)}
                className="mt-1 w-full rounded-md border border-line-2 bg-transparent px-2 py-1 text-[11px] text-txt-hi placeholder:text-txt-dim focus:border-mint focus:outline-none" />
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
              <p className="label-caps text-txt-dim">SIREN</p>
              <input type="text" value={filters.pmSiren ?? ''} placeholder="Un ou plusieurs, séparés par une virgule"
                onChange={(e) => setFilter('pmSiren', e.target.value.trim() === '' ? null : e.target.value)}
                className="mt-1 w-full rounded-md border border-line-2 bg-transparent px-2 py-1 text-[11px] text-txt-hi placeholder:text-txt-dim focus:border-mint focus:outline-none" />
            </div>

            {/* ── Forme juridique (facettes réelles : label + compte, valeur = code) ── */}
            <div>
              <p className="label-caps text-txt-dim">Forme juridique</p>
              {fac && fac.formes.length > 0 ? (
                <div className="mt-1 flex flex-wrap gap-1.5">
                  {fac.formes.map((o) => (
                    <FacetteChip key={o.code} code={o.code} label={o.label} n={o.n}
                      on={filters.pmForme.includes(o.code)} onToggle={toggleForme} disabled={dis} />
                  ))}
                </div>
              ) : <p className="mt-1 text-[10px] text-txt-dim">{fq.isLoading ? '…' : 'Aucune forme dans la portée courante.'}</p>}
            </div>

            {/* ── Code APE / activité (facettes réelles) ── */}
            <div>
              <p className="label-caps text-txt-dim">Code APE / activité</p>
              {fac && fac.apes.length > 0 ? (
                <div className="mt-1 flex flex-wrap gap-1.5">
                  {fac.apes.map((o) => (
                    <FacetteChip key={o.code} code={o.code} label={o.label} n={o.n}
                      on={filters.pmApe.includes(o.code)} onToggle={toggleApe} disabled={dis} />
                  ))}
                </div>
              ) : <p className="mt-1 text-[10px] text-txt-dim">{fq.isLoading ? '…' : 'Aucune activité dans la portée courante.'}</p>}
            </div>

            {/* ── Nombre de dirigeants (min / max) ── */}
            <div>
              <p className="label-caps text-txt-dim">Nombre de dirigeants</p>
              <div className="mt-1 flex items-center gap-1.5">
                <NumField field="pmDirigMin" ph="min" /><span className="text-txt-dim">–</span><NumField field="pmDirigMax" ph="max" />
              </div>
            </div>

            {/* ── KELFONCIER-FIX-1 (Lot B) — TRANCHE d'âge du dirigeant : < 50 / 50-69 / ≥ 70, JAMAIS l'âge
                exact. Filtre sur l'âge MAX des dirigeants (v_pm_propension_vendre), déjà calculé en base.
                OU entre tranches. ── */}
            <div data-prop-age-tranche>
              <p className="label-caps text-txt-dim">Âge du dirigeant (tranche)</p>
              <div className="mt-1 flex flex-wrap gap-1.5">
                {PM_AGE_TRANCHES.map((t) => (
                  <Chip key={t.k} on={filters.pmAge.includes(t.k)} onClick={() => toggleAge(t.k)}>{t.l}</Chip>
                ))}
              </div>
              <p className="mt-1 text-[10px] leading-snug text-txt-dim">Tranche du dirigeant le plus âgé (INPI/RNE) — jamais l'âge exact. Un signal de succession possible.</p>
            </div>
          </div>
          </fieldset>
        </div>
      )}
    </div>
  )
}

// VEILLE-2 (Lot 4) — la CRÉATION d'une veille de recherche depuis les filtres est RETIRÉE (plus de bouton
// « Créer une veille ») ; `enVeille` ne sert plus qu'à masquer le rituel « regard LABUSE » là où ce même
// panneau serait monté hors carte. La page Veille n'a plus que PARCELLE et RADAR.
export function FiltreLabuse({ onRetract, enVeille }: { onRetract?: () => void; enVeille?: boolean } = {}) {
  const { filters, setFilter, setFilters, setVerdict, commune, setCommunesFilter, setAnalyseRecap } = useApp()
  const analyseOn = filters.analyseLabuse
  // M55-D stage 4 : interrupteur UNIFIÉ — analyseLabuse (persisté, URL) ⟺ verdict (carte). Éteint
  // par défaut : plus jamais « analyse active » quand l'utilisateur n'a rien allumé (bug mesuré).
  const setAnalyse = (v: boolean) => { setFilter('analyseLabuse', v); setVerdict(v) }
  // Reset : les DEUX étages + éteint l'interrupteur (retour à l'état vierge). M55-J : coupe
  // aussi le rituel (phase/snapshot) — jamais une carte-phrase orpheline après un reset.
  const resetTout = () => { setFilters(EMPTY_FILTERS); setVerdict(false); setPhase('idle'); setSnapFilters(null); setAnalyseRecap(null) }
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
  const [live, setLive] = useState<number | null>(null)
  const [liveLoading, setLiveLoading] = useState(false)
  useEffect(() => {
    const ctrl = new AbortController()
    setLiveLoading(true)
    const tmr = window.setTimeout(() => {
      getFiltreCount(filters, ctrl.signal)
        .then((r) => { setLive(r.compte); setLiveLoading(false) })
        .catch(() => { /* abort/réseau : on garde le dernier nombre, l'opacité signale le flottement */ })
    }, 400)
    return () => { window.clearTimeout(tmr); ctrl.abort() }
  }, [filters])

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
    timerRef.current = window.setTimeout(() => setPhase((ph) => (ph === 'counting' ? 'revealed' : ph)), RITUEL_MS)
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
      {/* ═══════ 1 · COMMUNES — rang 1, MAÎTRE du périmètre (M55-D stage 6). Multi par code
          postal ; le sélecteur du header n'est plus qu'un REFLET de CE filtre. ═══════ */}
      <div data-communes-filtre>
        <TitreSection titre="1 · Communes"
          info="Le périmètre des résultats. Tout coché = toute l’île — rien coché aussi (aucune restriction)." />
        <div className="gcard mt-2 p-3">
        <div className="flex flex-wrap gap-1">
          {CP_COMMUNES.map(([cp, nom]) => (
            // RECETTE-1 (E4, Vic 04/10) : au survol d'un code commune, l'infobulle (D1 — `garder` →
            // survol) nomme la commune sous la forme « <code> — <commune> ». La valeur filtrée reste le `nom`.
            <Tip key={cp} garder side="top" tip={`${cp} — ${nom}`}>
              <button onClick={() => setCommunesFilter(
                  filters.communes.includes(nom) ? filters.communes.filter((c) => c !== nom) : [...filters.communes, nom])}
                className={`rounded-full border px-2 py-0.5 text-[10.5px] tabular-nums transition-colors duration-quick ${
                  filters.communes.includes(nom) ? 'border-mint bg-mint/20 font-medium text-txt-hi'
                    : 'border-line-2 bg-surface-3 text-txt-mut hover:border-mint/50 hover:text-txt'}`}>
                {cp}
              </button>
            </Tip>
          ))}
        </div>
        <div className="mt-1.5 flex gap-3">
          {/* M55-G point 12 : libellés d'ACTION (« tout » / « rien (toute l'île) » ne disaient
              pas le geste) — le sous-titre de la section garde « tout coché = toute l'île ». */}
          <button data-communes-toutes onClick={() => setCommunesFilter(CP_COMMUNES.map(([, n]) => n))}
            className="text-[10.5px] text-txt-dim underline decoration-txt-dim/40 underline-offset-2 hover:text-mint">Ajouter tout</button>
          <button data-communes-aucune onClick={() => setCommunesFilter([])}
            className="text-[10.5px] text-txt-dim underline decoration-txt-dim/40 underline-offset-2 hover:text-mint">Retirer tout</button>
          {/* FILTRE-NETTOYAGE #2 — forme courte « 12/24 » ; tout coché = « Toute l'île » (cf. le sous-titre
              de section) ; rien coché = pas de mention (aucune restriction, déjà toute l'île). */}
          {nCom > 0 && <span className="text-[10.5px] text-txt-dim">{nCom === CP_COMMUNES.length ? 'Toute l’île' : `${nCom}/${CP_COMMUNES.length}`}</span>}
        </div>
        </div>
      </div>

      {/* ═══════ 2 · LE TERRAIN (faits objectifs, toujours actifs — contraintes EN DERNIER) ═══════ */}
      <TitreSection cls="mt-4" titre="2 · Le terrain"
        info="Des faits objectifs (surface, zonage, état du sol) — valables sans aucune analyse." />
      <div className="gcard mt-2 flex flex-col gap-3 p-3">
        <div>
          <p className="label-caps text-txt-dim">Surface parcelle</p>
          <div className="mt-1 flex items-center gap-1.5"><NumField field="surfaceMin" ph="min" /><span className="text-txt-dim">–</span><NumField field="surfaceMax" ph="max" suffix="m²" /></div>
        </div>
        <div>
          {/* M99 Phase 3 : la saisie libre de zone exacte est remplacée par le sélecteur par
              famille (zones normalisées + comptes calculés) — voir ZoneSelector. */}
          <p className="label-caps text-txt-dim">Zonage</p>
          <ZoneSelector />
        </div>
        <div>
          <p className="label-caps text-txt-dim">État du sol</p>
          {/* RECETTE-1 (E3) — nu + bâti PARTITIONNENT les parcelles → tout coché par défaut, décocher
              restreint, tout décocher = 0 parcelle (plus de « aucune cochée mais 430 k »). */}
          <div className="mt-1"><ChipGroup field="etatSol" options={ETAT_SOL} partition /></div>
          {/* RECETTE-1 (E1, Vic 04/10) — la phrase explicative « Terrain nu = aucune emprise bâtie ≥ 5 %… »
              est RETIRÉE (la clause SQL ne bouge pas, seul l'affichage). */}
        </div>
        {/* KELFONCIER-FIX-2 (Lot C) — « Sans copropriété », « Hauteur du bâti (LiDAR) » et « Emprise bâtie »
            (ex-KELFONCIER-FIX-1 Lot D/E) descendent dans « Affiner la recherche » (façade allégée). Les
            prédicats (horsCopro, hauteurMin/Max, empriseMin/Max) sont inchangés — seul l'emplacement bouge.
            RETOURS-14 P5 — ZFANG/FRR ont aussi quitté « Le terrain » vers « Affiner la recherche ». */}
      </div>
      {/* M55-D stage 7 (décision Vic) : « Contraintes de secteur » a QUITTÉ le panneau Filtres —
          les flags restent visibles en fiche et en couches. Les clés URL legacy (fl=) sont
          ignorées proprement à la lecture (filters.ts). */}

      {/* RECETTE-1 (E2, Vic 04/10) — l'encart « 3 · Capacité » (SDP restante / logements possibles /
          destination) est ENTIÈREMENT RETIRÉ (façade + « Plus de filtres »). Les clés restent ignorées
          sans erreur dans un hash / une vue / une veille existante (cf. lib/filters.ts, tables de hash). */}

      {/* ═══════ RETOURS-14 P5 — « AFFINER LA RECHERCHE » (repliée, fermée par défaut, en bas) :
          ZFANG, FRR et Signaux de vie y sont regroupés (aucun filtre supprimé). ═══════ */}
      <AffinerRecherche />

      {/* ═══════ KELFONCIER-FIX-1 (Lot B) — SECTION « PROPRIÉTAIRE » REMONTÉE dans « Plus de filtres » ═══════
          Facettes DGFiP réelles (forme juridique · APE) + dénomination/SIREN (omnibox) + nb dirigeants
          + tranche d'âge du dirigeant + Particulier. Compteur/veille/Mes vues/badge déjà câblés. */}
      <SectionProprietaire />

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
              {CLIENT.revelation.decompte(live ?? totalIle ?? 0)}…
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
            {/* RECETTE-1 R35 — les boutons ne DÉPENDENT plus de `liveLoading` pour leur couleur/opacité :
                ils sont actionnables quel que soit le compteur en cours de calcul (le débounce 400 ms +
                l'aller-retour donnaient l'illusion d'un bouton « éteint » qui s'allume après coup). L'état
                « en cours » n'est plus signalé que sur le NOMBRE (compteur), pas sur les boutons. */}
            {/* DA-FIX-1 Lot 4 (DA-021) — un seul primaire par écran : « Voir les N parcelles » = primaire
                vert (le geste dominant) ; « Analyser avec LABUSE » = secondaire vert (moteur statistique,
                pas l'IA → jamais mauve). */}
            <Bouton data-voir-factuel niveau="primaire" ton="vert" onClick={voirFactuel} className="w-full">
              {CLIENT.revelation.voirN(live ?? totalIle ?? 0)}
            </Bouton>
            <Bouton data-analyser-btn niveau="secondaire" ton="vert" onClick={lancer} className="group w-full">
              <span>{CLIENT.revelation.boutonFaire.replace(/\s*→\s*$/, '')}</span>
              <svg viewBox="0 0 16 16" aria-hidden="true"
                className="h-[13px] w-[13px] transition-transform duration-quick group-hover:translate-x-0.5">
                <path d="M2.5 8 H13 M9.5 3.5 L14 8 L9.5 12.5" fill="none" stroke="currentColor"
                  strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </Bouton>
            {/* FILTRE-NETTOYAGE #5 — « Réinitialiser » remonte DANS le bloc d'actions (avec « Voir » et
                « Analyser »), plus isolé en bas. Reste secondaire (action de recul) : lien discret centré,
                teinte danger au survol — lisible, jamais un bouton de poids égal. */}
            <button data-reinitialiser onClick={resetTout}
              className="mx-auto min-h-7 px-1 py-0.5 text-[11px] text-txt-dim underline decoration-txt-dim/30 underline-offset-2 transition-colors duration-quick hover:text-danger hover:decoration-danger-line">
              Réinitialiser les filtres
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
