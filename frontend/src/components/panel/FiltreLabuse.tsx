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
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { deleteSearch, getFiltre, getSavedSearches, renameSearch, saveSearch } from '../../lib/api'
import { filtersFromHash, filtersToHash, hasOpinion } from '../../lib/filters'
import { DECLASSE_ORDER, TIER_DECLASSE_META, TIER_V2_META, type FilterTier, type TierV2 } from '../../lib/status'
import { EMPTY_FILTERS, useApp, type Filters } from '../../store/useApp'

const CONSTRUCTIBILITE = [
  { k: 'constructible', l: 'Constructible' },
  { k: 'au_conditionnelle', l: 'AU conditionnelle' },
  { k: 'fermee', l: 'Zone fermée' },
  { k: 'inconstructible', l: 'Inconstructible' },
  { k: 'rnu', l: 'RNU / hors-PLU' },
]
const ETAT_SOL = [
  { k: 'nu', l: 'Nu' },
  { k: 'bati_marginal', l: 'Bâti marginal' },
  { k: 'bati_sature', l: 'Bâti saturé' },
  { k: 'bati_revele', l: 'Bâti révélé' },
]
const ZONE_FAM = [{ k: 'U', l: 'U' }, { k: 'AU', l: 'AU' }, { k: 'A', l: 'A' }, { k: 'N', l: 'N' }]
const PROPRIO_TYPE = [{ k: 'pm', l: 'PM identifiée (SIREN)' }, { k: 'bailleur', l: 'Bailleur (HLM/SEM)' }, { k: 'pp', l: 'Particulier / non déterminable' }]
const ETAT_SOCIETE = [{ k: 'procedure', l: 'Procédure collective' }, { k: 'cessee', l: 'Cessée' }, { k: 'radiee', l: 'Radiée' }]
const COPRO = [{ k: 'avec', l: 'En copropriété' }, { k: 'sans', l: 'Hors copropriété' }]
const VIGILANCES: [string, string][] = [
  ['pente', 'Pente'], ['bruit_route', 'Bruit routier'], ['sol_pollue', 'SIS / pollution'],
  ['cavite', 'Cavité'], ['mvt', 'Mouvement de terrain'], ['ravine', 'Ravine'], ['icpe', 'ICPE'],
]
// M55-D stage 4 : ÉTAGE① « Contraintes de secteur » = régime foncier (50 pas, Parc) + vigilances
// (pollution/ICPE/risques) — des FAITS de terrain, valables sans analyse.
const CONTRAINTES: [string, string][] = ([['cinquante_pas', '50 pas géométriques'],
  ['parc_national', 'Parc national']] as [string, string][]).concat(VIGILANCES)
// Facettes du cadrage EN ATTENTE DE DONNÉE (P0) — montrées, désactivées, honnêtes.
const DROIT_DIFFERES = ['Plancher de densité', 'EBC partiel', 'Emplacement réservé',
  'Sol naturel / ZAN', 'Fraîcheur PLU (radar M41)']

const nf = new Intl.NumberFormat('fr-FR')

// M55-D stage 4 : différenciation SÉLECTIONNÉ / disponible plus lisible que le tout-gris —
// disponible = fond léger + survol menthe (ça s'active) ; sélectionné = rempli menthe, texte franc.
function Chip({ on, onClick, children }: { on: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button onClick={onClick}
      className={`rounded-full border px-2.5 py-0.5 text-[11px] transition-colors duration-quick ${
        on ? 'border-mint bg-mint/20 font-medium text-txt-hi'
          : 'border-line-2 bg-surface-3 text-txt-mut hover:border-mint/50 hover:text-txt'}`}>
      {children}
    </button>
  )
}

function ChipGroup({ field, options }: { field: keyof Filters; options: { k: string; l: string }[] }) {
  const { filters, setFilter } = useApp()
  const sel = (filters[field] as string[]) ?? []
  const toggle = (k: string) =>
    setFilter(field, (sel.includes(k) ? sel.filter((x) => x !== k) : [...sel, k]) as never)
  return (
    <div className="mt-1 flex flex-wrap gap-1.5">
      {options.map((o) => <Chip key={o.k} on={sel.includes(o.k)} onClick={() => toggle(o.k)}>{o.l}</Chip>)}
    </div>
  )
}

function NumField({ field, ph, suffix }: { field: keyof Filters; ph: string; suffix?: string }) {
  const { filters, setFilter } = useApp()
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

function BoolChip({ field, label }: { field: keyof Filters; label: string }) {
  const { filters, setFilter } = useApp()
  const on = !!filters[field]
  return <Chip on={on} onClick={() => setFilter(field, !on as never)}>{label}</Chip>
}

function Tiroir({ titre, sous, defaut = false, children }: { titre: string; sous?: string; defaut?: boolean; children: React.ReactNode }) {
  const [ouvert, setOuvert] = useState(defaut)
  return (
    <div className="border-t border-line-2/50">
      <button onClick={() => setOuvert((o) => !o)} className="flex w-full items-center justify-between py-1.5 text-left">
        <span className="text-xs font-medium text-txt-hi">{titre}{sous && <span className="text-txt-dim"> — {sous}</span>}</span>
        {/* M55-A point 4 : même patron que « Couches » — fermé → gauche (⌄ pivoté), ouvert → bas. */}
        <span className={`text-txt-dim transition-transform duration-quick ${ouvert ? '' : 'rotate-90'}`} aria-hidden="true">⌄</span>
      </button>
      {ouvert && <div className="pb-1">{children}</div>}
    </div>
  )
}

// M45-B (L2) — curseur mode B : une valeur de SESSION unique (travaux + loyer + rendement),
// partagée fiche ↔ filtre, rien persisté. Pilote le filtre « Mode B rentable » ET le calcul de la fiche.
function ModeBCurseur() {
  const modeB = useApp((s) => s.modeB)
  const setModeB = useApp((s) => s.setModeB)
  const Champ = ({ k, label, suffix, step }: { k: 'travauxM2' | 'loyerM2' | 'rendementPct'; label: string; suffix: string; step?: number }) => (
    <label className="flex items-center gap-1 text-[11px] text-txt-mut">
      {label}
      <input type="number" step={step ?? 1} value={modeB[k]}
        onChange={(e) => setModeB({ [k]: Number(e.target.value) })}
        className="w-[62px] rounded-md border border-line-2 bg-transparent px-1.5 py-0.5 text-[11px] text-txt-hi focus:border-mint focus:outline-none" />
      <span className="text-[9.5px] text-txt-dim">{suffix}</span>
    </label>
  )
  return (
    <div className="mt-1 rounded-lg border border-line-2/60 bg-surface-2/40 px-2.5 py-2">
      <p className="label-caps">Curseur mode B <span className="text-[9px] font-normal normal-case text-txt-dim">— session partagée avec la fiche</span></p>
      <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1.5">
        <Champ k="travauxM2" label="Travaux" suffix="€/m²" step={50} />
        <Champ k="loyerM2" label="Loyer" suffix="€/m²/mois" step={0.5} />
        <Champ k="rendementPct" label="Rendement" suffix="%" step={0.5} />
      </div>
    </div>
  )
}

// Les 6 vues préréglées du cadrage — combinaisons nommées (setFilters). L'anti-60-checkboxes.
const PRESETS: { nom: string; f: Partial<Filters> }[] = [
  { nom: 'Terrain nu constructible', f: { constructibilite: ['constructible'], etatSol: ['nu'], sdpMin: 100 } },
  { nom: 'Prêt à démarcher', f: { tiers: ['brulante', 'chaude'], flags: ['acces'], proprietaireType: ['pm'] } },
  { nom: 'Division en or', f: { divisionOr: true } },
  { nom: 'Réhab rentable', f: { etatSol: ['bati_sature', 'bati_revele'], modeBRentable: true } },
  { nom: 'Veille AU', f: { analyseLabuse: false, constructibilite: ['fermee', 'au_conditionnelle'] } },
  { nom: 'Mon budget', f: { budgetMax: 200000 } },   // M45-B : preset FONCTIONNEL (charge foncière ≤ budget)
]

function Section({ title, tag, children }: { title: string; tag?: string; children: React.ReactNode }) {
  return (
    <div className="py-2">
      <p className="label-caps flex items-center gap-1.5">
        {title}
        {tag && <span className="rounded border border-line-2 px-1 py-px text-[8.5px] font-normal uppercase tracking-wide text-txt-dim">{tag}</span>}
      </p>
      {children}
    </div>
  )
}

/** M52 L5 — VUES SAUVEGARDÉES (reste M45) : nom + combinaison de filtres courante, stockage CÔTÉ
 *  COMPTE (table `saved_searches`, jamais partagé entre comptes). Appliquer (clic) / renommer /
 *  supprimer. Une vue nommée EST aussi une veille (même objet) — cohérent, pas dupliqué. */
function MesVues() {
  const { filters, zone, setFilters, setZone } = useApp()
  const qc = useQueryClient()
  const [nom, setNom] = useState('')
  const [editId, setEditId] = useState<number | null>(null)
  const [editNom, setEditNom] = useState('')
  const vues = useQuery({ queryKey: ['searches'], queryFn: getSavedSearches })
  const inval = () => qc.invalidateQueries({ queryKey: ['searches'] })
  const add = useMutation({ mutationFn: () => saveSearch(nom.trim(), filtersToHash(filters, zone) || '#f=1'), onSuccess: () => { setNom(''); inval() } })
  const del = useMutation({ mutationFn: deleteSearch, onSuccess: inval })
  const ren = useMutation({ mutationFn: ({ id, n }: { id: number; n: string }) => renameSearch(id, n), onSuccess: () => { setEditId(null); inval() } })
  const appliquer = (hash: string) => {
    const parsed = filtersFromHash(hash)
    setFilters({ ...EMPTY_FILTERS, ...(parsed?.filters ?? {}) })
    setZone(parsed?.zone ?? null)
  }
  const liste = vues.data ?? []
  return (
    <div data-mes-vues className="mt-2">
      <div className="flex items-center gap-2">
        <p className="label-caps">Mes vues</p>
        <span className="text-[10px] text-txt-dim">enregistrées sur votre compte</span>
      </div>
      {liste.length > 0 && (
        <div className="mt-1 flex flex-wrap gap-1.5">
          {liste.map((v) => (
            editId === v.id ? (
              <input key={v.id} autoFocus value={editNom} onChange={(e) => setEditNom(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter' && editNom.trim()) ren.mutate({ id: v.id, n: editNom.trim() }); if (e.key === 'Escape') setEditId(null) }}
                onBlur={() => editNom.trim() && editNom !== v.nom ? ren.mutate({ id: v.id, n: editNom.trim() }) : setEditId(null)}
                className="rounded-full border border-mint bg-surface-3 px-2 py-0.5 text-[11px] text-txt focus:outline-none" />
            ) : (
              <span key={v.id} className="group inline-flex items-center gap-1 rounded-full border border-line-2 py-0.5 pl-2.5 pr-1 text-[11px] text-txt-mut hover:border-mint">
                <button onClick={() => appliquer(v.hash)} title={`Appliquer « ${v.nom} »`} className="hover:text-mint">{v.nom}</button>
                <button onClick={() => { setEditId(v.id); setEditNom(v.nom) }} aria-label="Renommer" title="Renommer" className="text-txt-dim hover:text-mint">✎</button>
                <button onClick={() => del.mutate(v.id)} aria-label="Supprimer" title="Supprimer" className="flex h-4 w-4 items-center justify-center rounded-full text-txt-dim hover:bg-surface-3 hover:text-st-ecartee">×</button>
              </span>
            )
          ))}
        </div>
      )}
      <div className="mt-1.5 flex gap-1.5">
        <input value={nom} onChange={(e) => setNom(e.target.value)} placeholder="Nommer la combinaison de filtres actuelle…"
          onKeyDown={(e) => { if (e.key === 'Enter' && nom.trim()) add.mutate() }}
          className="min-w-0 flex-1 rounded border border-line-2 bg-surface-3 px-2 py-1 text-[11px] text-txt focus:border-mint focus:outline-none" />
        <button onClick={() => nom.trim() && add.mutate()} disabled={!nom.trim() || add.isPending}
          className="shrink-0 rounded border border-mint/50 px-2 text-[11px] text-mint transition-colors duration-quick hover:bg-mint/10 disabled:opacity-40">
          Enregistrer la vue</button>
      </div>
    </div>
  )
}

// M52-B — SÉLECTEUR DE PROFIL « Vous cherchez ? », le DERNIER geste : à l'activation de l'analyse,
// le promoteur dit s'il veut du terrain nu, du bâti (réhab/démolition) ou les deux. Le choix
// PRÉ-APPLIQUE des filtres qui EXISTENT DÉJÀ (état du sol + mode B rentable) — zéro calcul nouveau,
// zéro endpoint. La donnée « année de construction » n'existe pas à l'échelle (BDNB hors 974, DPE
// non obligatoire avant 2028) : ce sélecteur ne l'invente pas, il ouvre le bâti à celui qui l'accepte.
// La puce active est DÉRIVÉE de l'état réel des filtres (jamais un état fantôme) → toujours cohérente
// avec le compteur « Retenues par l'analyse ». Re-cliquable à tout moment (chips visibles, pas un tunnel).
const BATI_SOLS = ['bati_marginal', 'bati_sature', 'bati_revele']
type Profil = 'nu' | 'bati' | 'deux'
const PROFILS: { k: Profil; l: string; sous?: string }[] = [
  { k: 'nu', l: 'Terrain nu' },
  { k: 'bati', l: 'Bâti', sous: 'réhab / démolition' },
  { k: 'deux', l: 'Les deux' },
]
const memeSet = (a: string[], b: string[]) => a.length === b.length && [...a].sort().join('|') === [...b].sort().join('|')

function ProfilSelecteur() {
  const { filters, setFilters } = useApp()
  // Dérivation : la puce active REFLÈTE les filtres réels. Hors des 3 combinaisons (l'utilisateur
  // a affiné l'état du sol à la main), aucune puce n'est allumée — on ne ment pas sur le périmètre.
  const profil: Profil | null =
    memeSet(filters.etatSol, ['nu']) && !filters.modeBRentable ? 'nu'
      : memeSet(filters.etatSol, BATI_SOLS) && filters.modeBRentable ? 'bati'
        : filters.etatSol.length === 0 && !filters.modeBRentable ? 'deux'
          : null
  const appliquer = (k: Profil) => {
    const patch = k === 'nu' ? { etatSol: ['nu'], modeBRentable: false }
      : k === 'bati' ? { etatSol: [...BATI_SOLS], modeBRentable: true }
        : { etatSol: [], modeBRentable: false }
    setFilters({ ...filters, ...patch })   // ne touche QUE état du sol + mode B — le reste des filtres reste
  }
  return (
    <div data-profil-selecteur className="mb-2 rounded-lg border border-line-2/60 bg-surface-2/40 px-2.5 py-2">
      <p className="label-caps flex flex-wrap items-center gap-x-1.5">Vous cherchez ?
        <span className="text-[9px] font-normal normal-case text-txt-dim">— pré-règle l’état du sol + le mode B, rien d’autre</span></p>
      <div className="mt-1.5 flex flex-wrap gap-1.5">
        {PROFILS.map((p) => (
          <button key={p.k} data-profil={p.k} onClick={() => appliquer(p.k)}
            title={p.k === 'nu' ? 'État du sol : Nu' : p.k === 'bati' ? 'État du sol : bâti marginal/saturé/révélé + Mode B rentable en avant' : 'Aucune restriction d’état du sol (défaut)'}
            className={`rounded-full border px-3 py-0.5 text-[11px] transition-colors duration-quick ${
              profil === p.k ? 'border-mint bg-mint/10 text-mint' : 'border-line-2 text-txt-mut hover:text-txt'}`}>
            {p.l}{p.sous && <span className="ml-1 text-[9.5px] opacity-70">{p.sous}</span>}
          </button>
        ))}
      </div>
      {/* Honnêteté (point 2 + cohérence M48) : le segment bâti est servi par le MÊME tri (signal
          d'activité), mais le backtest ne mesure QUE le classement principal — on le DIT. */}
      {profil === 'bati' && (
        <p data-profil-bati-note className="mt-1.5 text-[10px] leading-snug text-txt-dim">
          Segment bâti trié par <b className="text-txt-mut">signal d’activité</b> — performance non
          mesurée séparément (le backtest couvre le classement principal). Cohérent avec le segment
          Renouvellement : les occupées gardent leur motif, jamais masquées.
        </p>
      )}
    </div>
  )
}

export function FiltreLabuse() {
  const { filters, setFilter, setFilters, setVerdict } = useApp()
  const analyseOn = filters.analyseLabuse
  const TIERS_V2: TierV2[] = ['brulante', 'chaude', 'reserve_fonciere', 'a_creuser', 'ecartee']
  const toggleTier = (t: FilterTier) =>
    setFilter('tiers', filters.tiers.includes(t) ? filters.tiers.filter((x) => x !== t) : [...filters.tiers, t])
  const toggleFlag = (k: string) =>
    setFilter('flags', filters.flags.includes(k) ? filters.flags.filter((x) => x !== k) : [...filters.flags, k])
  // M55-D stage 4 : interrupteur UNIFIÉ — analyseLabuse (persisté, URL) ⟺ verdict (carte). Éteint
  // par défaut : plus jamais « analyse active » quand l'utilisateur n'a rien allumé (bug mesuré).
  const setAnalyse = (v: boolean) => { setFilter('analyseLabuse', v); setVerdict(v) }
  // Un pré-réglage portant un critère d'OPINION ALLUME l'interrupteur (visiblement).
  const applyPreset = (pf: Partial<Filters>) => {
    const nf = { ...EMPTY_FILTERS, ...pf }
    const on = Boolean(nf.analyseLabuse) || hasOpinion(nf)
    setFilters({ ...nf, analyseLabuse: on }); setVerdict(on)
  }
  // Reset : les DEUX étages + éteint l'interrupteur (retour à l'état vierge).
  const resetTout = () => { setFilters(EMPTY_FILTERS); setVerdict(false) }
  // Compteurs : parc FACTUEL (analyse coupée) et RETENUES (analyse). La transition raconte l'effet.
  const off = useQuery({ queryKey: ['filtre', filters, false], queryFn: () => getFiltre({ ...filters, analyseLabuse: false }, 0) })
  const on = useQuery({ queryKey: ['filtre', filters, true], queryFn: () => getFiltre({ ...filters, analyseLabuse: true }, 0) })
  const parc = off.data?.compte
  const retenues = on.data?.compte

  return (
    <div className="card-elev px-3 py-2">
      {/* ═══════ ÉTAGE ① — LE TERRAIN (faits objectifs, toujours actifs, ordonnés par usage) ═══════ */}
      <p className="label-caps text-txt-mut">① Le terrain
        <span className="ml-1.5 text-[9px] font-normal normal-case text-txt-dim">faits, sans analyse</span></p>
      <div className="mt-1.5 flex flex-col gap-3">
        <div>
          <p className="label-caps text-txt-dim">Surface parcelle</p>
          <div className="mt-1 flex items-center gap-1.5"><NumField field="surfaceMin" ph="min" /><span className="text-txt-dim">–</span><NumField field="surfaceMax" ph="max" suffix="m²" /></div>
        </div>
        <div>
          <p className="label-caps text-txt-dim">Zonage <span className="normal-case text-[8.5px] text-txt-dim">— famille U/AU/A/N + zone exacte</span></p>
          <div className="mt-1"><ChipGroup field="zonagePlu" options={ZONE_FAM} /></div>
          <input placeholder="zone exacte : UA, UB, 2AU (séparées par des virgules)"
            value={filters.zonePlu.join(', ')}
            onChange={(e) => setFilter('zonePlu', e.target.value.split(',').map((s) => s.trim()).filter(Boolean))}
            className="mt-1.5 w-full rounded-md border border-line-2 bg-surface-3 px-2 py-1 text-[11px] text-txt-hi placeholder:text-txt-dim focus:border-mint focus:outline-none" />
        </div>
        <div>
          <p className="label-caps text-txt-dim">État du sol</p>
          <div className="mt-1"><ChipGroup field="etatSol" options={ETAT_SOL} /></div>
        </div>
        <div>
          <p className="label-caps text-txt-dim">Contraintes de secteur <span className="normal-case text-[8.5px] text-txt-dim">Sourcé</span></p>
          <div className="mt-1 flex flex-wrap gap-1.5">
            {CONTRAINTES.map(([k, l]) => (<Chip key={k} on={filters.flags.includes(k)} onClick={() => toggleFlag(k)}>{l}</Chip>))}
          </div>
        </div>
      </div>

      {/* ═══════ ÉTAGE ② — LE REGARD LABUSE (interrupteur en vedette, ÉTEINT par défaut) ═══════ */}
      <div className={`mt-4 rounded-xl border p-3 transition-colors duration-soft ${analyseOn ? 'border-mint/60 bg-mint/[0.07]' : 'border-line-2 bg-surface-2/40'}`}>
        <button data-analyse-toggle onClick={() => setAnalyse(!analyseOn)} aria-pressed={analyseOn}
          className="flex w-full items-center gap-2.5 text-left" title="Appliquer le regard LABUSE (classement, potentiel, SDP…) — ou rester au tri factuel.">
          <span className={`flex h-5 w-9 shrink-0 items-center rounded-full px-0.5 transition-colors duration-quick ${analyseOn ? 'bg-mint' : 'bg-line-2'}`}>
            <span className={`h-4 w-4 rounded-full bg-white shadow transition-transform duration-quick ${analyseOn ? 'translate-x-4' : ''}`} />
          </span>
          <span className={`font-display text-[13px] font-bold ${analyseOn ? 'text-mint' : 'text-txt'}`}>② Afficher l’analyse LABUSE</span>
        </button>
        {/* compteur — la transition « parc → retenues » rend visible ce que l'analyse RETIENT. */}
        <p className="mt-2 text-[11.5px] leading-snug text-txt-dim tabular-nums">
          {analyseOn ? (
            <><span className="text-txt-mut">{parc == null ? '…' : nf.format(parc)}</span>
              <span className="mx-1.5 text-mint">→</span>
              <span className="text-[15px] font-semibold text-txt-hi">{retenues == null ? '…' : nf.format(retenues)}</span> retenues par l’analyse</>
          ) : (
            <><span className="text-txt">{parc == null ? '…' : nf.format(parc)}</span> parcelles · <span className="text-txt-mut">tri factuel</span></>
          )}
        </p>
        {analyseOn && (
          <div className="mt-3 flex flex-col gap-3">
            <div>
              <p className="label-caps text-txt-dim">Verdict · tiers</p>
              <div className="mt-1 flex flex-wrap gap-1.5">
                {TIERS_V2.map((t) => (
                  <Chip key={t} on={filters.tiers.includes(t)} onClick={() => toggleTier(t)}>
                    <span className="mr-1 inline-block h-1.5 w-1.5 rounded-full align-middle" style={{ background: TIER_V2_META[t].color }} />{TIER_V2_META[t].label}
                  </Chip>
                ))}
              </div>
            </div>
            <div>
              <p className="label-caps text-txt-dim">Déclassées · motif</p>
              <div className="mt-1 flex flex-wrap gap-1.5">
                {DECLASSE_ORDER.map((t) => (
                  <Chip key={t} on={filters.tiers.includes(t)} onClick={() => toggleTier(t)}>
                    <span className="mr-1 inline-block h-1.5 w-1.5 rounded-full align-middle" style={{ background: TIER_DECLASSE_META[t].color }} />{TIER_DECLASSE_META[t].label.replace('Déclassée — ', '')}
                  </Chip>
                ))}
              </div>
              <p className="mt-1 text-[10px] leading-snug text-txt-dim">Les écartées ne sont jamais masquées — choisissez un motif pour les consulter, chacune garde son verdict.</p>
            </div>
            <Section title="Constructibilité calibrée" tag="Sourcé"><ChipGroup field="constructibilite" options={CONSTRUCTIBILITE} /></Section>
            <div className="flex flex-wrap items-end gap-x-6 gap-y-2">
              <div><p className="label-caps text-txt-dim">Potentiel ≥ /100</p><div className="mt-1"><NumField field="scoreMin" ph="70" /></div></div>
              <div><p className="label-caps text-txt-dim">SDP résiduelle</p><div className="mt-1 flex items-center gap-1.5"><NumField field="sdpMin" ph="min" /><span className="text-txt-dim">–</span><NumField field="sdpMax" ph="max" suffix="m²" /></div></div>
              <div><p className="label-caps flex items-center gap-1 text-txt-dim">Capacité <span className="rounded border border-line-2 px-1 text-[8px] uppercase">Est.</span></p><div className="mt-1 flex items-center gap-1"><span className="text-[11px] text-txt-dim">≥</span><NumField field="capaciteMin" ph="N" suffix="log." /></div></div>
            </div>
            <div className="flex flex-wrap gap-1.5">
              <BoolChip field="evenement" label="Événement (BODACC)" />
              <BoolChip field="veille" label="Veille succession" />
              <BoolChip field="horsCopro" label="Masquer copropriétés" />
            </div>

      {/* ── TIROIRS d'analyse (économie / mutation / propriété / niches) — dans l'étage ② ── */}
      <Tiroir titre="Combien ça coûte, ça rapporte ?" sous="économie">
        <div className="flex flex-wrap gap-x-6 gap-y-2 py-2">
          <div><p className="label-caps flex items-center gap-1.5">Prix d’achat max ≤ budget
            <span className="rounded border border-line-2 px-1 py-px text-[8.5px] uppercase text-txt-dim">Estimé</span></p>
            <div className="mt-1 flex items-center gap-1"><NumField field="budgetMax" ph="€" suffix="€" /></div></div>
          <div><p className="label-caps">Charge foncière (€)</p>
            <div className="mt-1 flex items-center gap-1.5"><NumField field="chargeMin" ph="min" /><span className="text-txt-dim">–</span><NumField field="chargeMax" ph="max" /></div></div>
        </div>
        <div className="flex flex-wrap gap-x-6 gap-y-2 py-2">
          <div><p className="label-caps flex items-center gap-1.5">Prix marché DVF (€/m²)
            <span className="rounded border border-line-2 px-1 py-px text-[8.5px] uppercase text-txt-dim">Sourcé</span></p>
            <div className="mt-1 flex items-center gap-1.5"><NumField field="prixMarcheMin" ph="min" /><span className="text-txt-dim">–</span><NumField field="prixMarcheMax" ph="max" suffix="€/m²" /></div></div>
          <div><p className="label-caps flex items-center gap-1.5">Bilan CA
            <span className="rounded border border-line-2 px-1 py-px text-[8.5px] uppercase text-txt-dim">Estimé</span></p>
            <div className="mt-1 flex items-center gap-1"><span className="text-[11px] text-txt-dim">≥</span><NumField field="caMin" ph="€" suffix="€" /></div></div>
        </div>
        <Section title="Repères">
          <div className="mt-1 flex flex-wrap gap-1.5">
            <BoolChip field="marcheFiable" label="Données marché fiables (n≥3)" />
            <BoolChip field="sousDensite" label="Bâti en sous-densité" />
            <BoolChip field="modeBRentable" label="Mode B rentable (au paramètre)" />
          </div>
        </Section>
        <ModeBCurseur />
      </Tiroir>

      <Tiroir titre="Ça va se vendre ?" sous="le cœur — voie analyse">
        <div className="flex flex-wrap gap-x-6 gap-y-2 py-2">
          <div><p className="label-caps">Probabilité ×N</p>
            <div className="mt-1 flex items-center gap-1"><span className="text-[11px] text-txt-dim">≥</span><NumField field="multMin" ph="N" suffix="×" /></div></div>
          <div><p className="label-caps">Têtes (rang P)</p>
            <div className="mt-1 flex items-center gap-1"><span className="text-[11px] text-txt-dim">≤</span><NumField field="rangMax" ph="N" /></div></div>
        </div>
        <Section title="Segments">
          <div className="mt-1 flex flex-wrap gap-1.5">
            <BoolChip field="renouvellement" label="Renouvellement" />
            <BoolChip field="divisionOr" label="Division en or (O12)" />
          </div>
          {/* M48 : le segment Renouvellement = des parcelles ÉCARTÉES par conception → 0 retenue par
              l'analyse. On le DIT quand le filtre est actif, pour lever le « 0 » déroutant du compteur. */}
          {filters.renouvellement && (
            <p className="mt-1.5 text-[10px] leading-snug text-txt-dim">
              Segment consultable via la <b className="text-txt-mut">voie manuelle</b> — coupez
              l’Analyse LABUSE pour l’explorer : ces parcelles occupées sont écartées du classement
              principal par conception (d’où 0 retenue par l’analyse).
            </p>
          )}
        </Section>
      </Tiroir>

      <Tiroir titre="À qui c’est, puis-je l’acheter ?" sous="propriété">
        <Section title="Type de propriétaire" tag="Sourcé"><ChipGroup field="proprietaireType" options={PROPRIO_TYPE} /></Section>
        <Section title="État de la société" tag="Sourcé (M43)"><ChipGroup field="etatSociete" options={ETAT_SOCIETE} /></Section>
        <Section title="Copropriété (RNIC)"><ChipGroup field="copro" options={COPRO} /></Section>
        <div className="pt-1 text-[10px] text-txt-dim">
          Dormance / succession : absent (attend avocat). Gérant âgé : jamais un critère (RGPD).
        </div>
      </Tiroir>

      <Tiroir titre="Veille & niches" sous="les différenciants">
        <Section title="Niches">
          <div className="mt-1 flex flex-wrap gap-1.5">
            <BoolChip field="npnru" label="Proximité NPNRU / QPV" />
            <BoolChip field="adresseAbsente" label="Adresse absente (BAN)" />
          </div>
        </Section>
        <div className="pt-1 text-[10px] text-txt-dim">
          Motif de déclassement : coupe l’Analyse LABUSE pour explorer les écartées (jamais masquées) ·
          potentiel solaire APER : M45 v1.1.
        </div>
      </Tiroir>

          </div>
        )}
      </div>

      {/* ═══════ ÉTAGE ③ — RACCOURCIS (pré-réglages, vues, pédagogie discrète) ═══════ */}
      <div className="mt-4">
        <p className="label-caps flex items-center gap-1.5 text-txt-mut">③ Pré-réglages
          <span className="text-[9px] font-normal normal-case text-txt-dim">— cochent des filtres visibles, à défaire un par un</span></p>
        <div className="mt-1 flex flex-wrap gap-1.5">
          {PRESETS.map((p) => (
            <button key={p.nom} onClick={() => applyPreset(p.f)}
              className="rounded-full border border-dashed border-line-2 bg-surface-3 px-2.5 py-0.5 text-[11px] text-txt-mut hover:border-mint hover:text-mint">{p.nom}</button>
          ))}
        </div>
        <div className="mt-2"><ProfilSelecteur /></div>
        <MesVues />
        <Tiroir titre="Puis-je construire ?" sous="droit du sol — repères">
          <p className="text-[11px] leading-snug text-txt-dim">
            Le zonage (famille + zone exacte) et l’état du sol se règlent dans l’étage ① « Le terrain ».
            En attente de donnée (M45 v1.1) : {DROIT_DIFFERES.join(' · ')}.
          </p>
        </Tiroir>
      </div>

      <button onClick={resetTout}
        title="Efface les DEUX étages et éteint l'interrupteur — retour à l'état vierge."
        className="mt-3 min-h-8 w-full rounded-lg border border-line-2 py-1.5 text-[11px] text-txt-dim transition-colors duration-quick hover:border-st-ecartee/50 hover:text-txt">
        Réinitialiser — terrain, analyse &amp; interrupteur
      </button>
    </div>
  )
}
