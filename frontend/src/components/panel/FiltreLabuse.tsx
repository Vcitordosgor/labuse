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
import { useState } from 'react'

import { getFiltre } from '../../lib/api'
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
// Facettes du cadrage EN ATTENTE DE DONNÉE (P0) — montrées, désactivées, honnêtes.
const DROIT_DIFFERES = ['Plancher de densité', 'EBC partiel', 'Emplacement réservé',
  'Sol naturel / ZAN', 'Fraîcheur PLU (radar M41)']

const nf = new Intl.NumberFormat('fr-FR')

function Chip({ on, onClick, children }: { on: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button onClick={onClick}
      className={`rounded-full border px-2.5 py-0.5 text-[11px] transition-colors duration-quick ${
        on ? 'border-mint bg-mint/10 text-mint' : 'border-line-2 text-txt-mut hover:text-txt'}`}>
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
        <span className="text-txt-dim">{ouvert ? '▾' : '▸'}</span>
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

export function FiltreLabuse() {
  const { filters, setFilter, setFilters, resetFilters } = useApp()
  const [droitOuvert, setDroitOuvert] = useState(true)

  // Compteur SQL des DEUX voies (le « théâtre »). M46 (Lot D) : lever l'ambiguïté du mot « trame »
  // — il désignait 431 663 (barre par défaut) MAIS le sous-ensemble filtré une fois un filtre posé.
  // Un mot = un périmètre : on ne dit plus « trame » mais « AVANT analyse » (le sous-ensemble
  // correspondant AUX FILTRES courants, avant que l'analyse n'en retire les exclusions dures).
  const on = useQuery({ queryKey: ['filtre', filters, true], queryFn: () => getFiltre({ ...filters, analyseLabuse: true }, 0) })
  const off = useQuery({ queryKey: ['filtre', filters, false], queryFn: () => getFiltre({ ...filters, analyseLabuse: false }, 0) })
  const compteAnalyse = on.data?.compte             // retenues par l'analyse (déclassements inclus)
  const compteAvant = off.data?.compte              // mêmes filtres, AVANT analyse (exclusions dures incluses)
  const compteExclues = (compteAvant != null && compteAnalyse != null) ? compteAvant - compteAnalyse : null
  const compteActuel = filters.analyseLabuse ? compteAnalyse : compteAvant

  return (
    <div className="card-elev px-3 py-2">
      {/* En-tête : compteur en direct + interrupteur — chaque nombre DIT son périmètre (réconcilié :
          « avant analyse » = retenues + exclusions dures ; jamais de soustraction laissée au client). */}
      <div className="flex items-center justify-between">
        <div>
          <p className="label-caps">{filters.analyseLabuse ? 'Retenues par l’analyse' : 'Voie manuelle (sans analyse)'}</p>
          <div className="flex items-baseline gap-2">
            <span className="text-[22px] font-semibold text-txt-hi tabular-nums">
              {compteActuel == null ? '…' : nf.format(compteActuel)}</span>
            {filters.analyseLabuse && compteAvant != null && compteExclues != null && (
              <span className="text-[11px] text-txt-dim">
                sur <span className="tabular-nums">{nf.format(compteAvant)}</span> avant analyse
                <span className="mx-1 text-mint">·</span>
                <span className="tabular-nums text-txt-mut">{nf.format(compteExclues)}</span> exclusions dures écartées
              </span>
            )}
            {!filters.analyseLabuse && compteAnalyse != null && (
              <span className="text-[11px] text-txt-dim">dont <span className="tabular-nums text-txt-mut">{nf.format(compteAnalyse)}</span> retenues par l’analyse</span>
            )}
          </div>
        </div>
        <button onClick={() => setFilter('analyseLabuse', !filters.analyseLabuse)}
          title="Analyse LABUSE : appliquer le classement (tiers) ou passer en voie manuelle pure"
          className={`flex items-center gap-2 rounded-full border px-3 py-1 text-[11px] ${
            filters.analyseLabuse ? 'border-mint bg-mint/10 text-mint' : 'border-line-2 text-txt-mut'}`}>
          <span className={`inline-block h-2 w-2 rounded-full ${filters.analyseLabuse ? 'bg-mint' : 'bg-txt-dim'}`} />
          Analyse LABUSE {filters.analyseLabuse ? 'active' : 'coupée'}
        </button>
      </div>

      {/* ── VUES PRÉRÉGLÉES (l'anti-60-checkboxes) : les 6 du cadrage ── */}
      <div className="mt-2 flex flex-wrap gap-1.5">
        {PRESETS.map((p) => (
          <button key={p.nom} onClick={() => setFilters({ ...EMPTY_FILTERS, ...p.f })}
            className="rounded-full border border-line-2 px-2.5 py-0.5 text-[11px] text-txt-mut hover:border-mint hover:text-mint">
            {p.nom}
          </button>
        ))}
      </div>

      {/* ── BARRE NIVEAU 1 ── */}
      <div className="mt-2 divide-y divide-line-2/50">
        <Section title="Constructibilité calibrée" tag="Sourcé">
          <ChipGroup field="constructibilite" options={CONSTRUCTIBILITE} />
        </Section>
        <div className="flex flex-wrap gap-x-6 gap-y-2 py-2">
          <div>
            <p className="label-caps">Surface parcelle</p>
            <div className="mt-1 flex items-center gap-1.5">
              <NumField field="surfaceMin" ph="min" /><span className="text-txt-dim">–</span><NumField field="surfaceMax" ph="max" suffix="m²" />
            </div>
          </div>
          <div>
            <p className="label-caps">SDP résiduelle</p>
            <div className="mt-1 flex items-center gap-1.5">
              <NumField field="sdpMin" ph="min" /><span className="text-txt-dim">–</span><NumField field="sdpMax" ph="max" suffix="m²" />
            </div>
          </div>
          <div>
            <p className="label-caps flex items-center gap-1.5">Capacité logements
              <span className="rounded border border-line-2 px-1 py-px text-[8.5px] uppercase text-txt-dim">Estimé</span></p>
            <div className="mt-1 flex items-center gap-1"><span className="text-[11px] text-txt-dim">≥</span>
              <NumField field="capaciteMin" ph="N" suffix="log." /></div>
          </div>
        </div>
        <Section title="État du sol"><ChipGroup field="etatSol" options={ETAT_SOL} /></Section>
      </div>

      {/* ── TIROIR NIVEAU 2 (témoin) : « Puis-je construire ? » ── */}
      <div className="mt-1 border-t border-line-2/50 pt-1">
        <button onClick={() => setDroitOuvert((o) => !o)}
          className="flex w-full items-center justify-between py-1.5 text-left">
          <span className="text-xs font-medium text-txt-hi">Puis-je construire ? <span className="text-txt-dim">— droit du sol</span></span>
          <span className="text-txt-dim">{droitOuvert ? '▾' : '▸'}</span>
        </button>
        {droitOuvert && (
          <div className="pb-1">
            <Section title="Famille de zonage" tag="Sourcé"><ChipGroup field="zonagePlu" options={ZONE_FAM} /></Section>
            <Section title="Zone PLU exacte">
              <input placeholder="ex. UA, UB, 2AU (séparées par des virgules)"
                value={filters.zonePlu.join(', ')}
                onChange={(e) => setFilter('zonePlu', e.target.value.split(',').map((s) => s.trim()).filter(Boolean))}
                className="mt-1 w-full rounded-md border border-line-2 bg-transparent px-2 py-1 text-[11px] text-txt-hi placeholder:text-txt-dim focus:border-mint focus:outline-none" />
            </Section>
            <Section title="Contraintes de secteur" tag="Sourcé">
              <div className="mt-1 flex flex-wrap gap-1.5">
                {[['cinquante_pas', '50 pas géométriques'], ['parc_national', 'Parc national']].map(([k, l]) => (
                  <Chip key={k} on={filters.flags.includes(k)}
                    onClick={() => setFilter('flags', filters.flags.includes(k) ? filters.flags.filter((x) => x !== k) : [...filters.flags, k])}>{l}</Chip>
                ))}
              </div>
            </Section>
            <div className="pt-1 text-[10px] text-txt-dim">
              En attente de donnée (M45 v1.1) : {DROIT_DIFFERES.join(' · ')} — listés, pas encore filtrables.
            </div>
          </div>
        )}
      </div>

      {/* ── TIROIRS NIVEAU 2 (les autres questions) ── */}
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

      <Tiroir titre="Ça va muter ?" sous="le cœur — voie analyse">
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

      <Tiroir titre="Quels risques, quelles contraintes ?" sous="terrain">
        <Section title="Vigilances par type" tag="Sourcé">
          <div className="mt-1 flex flex-wrap gap-1.5">
            {VIGILANCES.map(([k, l]) => (
              <Chip key={k} on={filters.flags.includes(k)}
                onClick={() => setFilter('flags', filters.flags.includes(k) ? filters.flags.filter((x) => x !== k) : [...filters.flags, k])}>{l}</Chip>
            ))}
          </div>
        </Section>
        <div className="pt-1 text-[10px] text-txt-dim">
          Accès voirie : étiquette « limite BD TOPO » (dette #12). Piscine (M39) : indisponible tant que non basculée.
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

      {/* Écartées : jamais masquées — consultables via la voie manuelle, avec leur motif au verdict. */}
      <div className="mt-1 border-t border-line-2/50 pt-2 text-[10px] text-txt-dim">
        Les écartées ne sont jamais masquées : coupez l’Analyse LABUSE (ou choisissez « Inconstructible /
        Zone fermée » ci-dessus) pour les consulter — chaque parcelle garde son motif de déclassement.
      </div>

      <button onClick={resetFilters}
        className="mt-2 min-h-7 w-full rounded-lg border border-line-2 py-1 text-[11px] text-txt-dim transition-colors duration-quick hover:text-txt">
        Réinitialiser les filtres
      </button>
    </div>
  )
}
