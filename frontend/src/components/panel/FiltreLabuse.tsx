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
import { useApp, type Filters } from '../../store/useApp'

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
  const { filters, setFilter, resetFilters } = useApp()
  const [droitOuvert, setDroitOuvert] = useState(true)

  // Compteur SQL des DEUX voies (le « théâtre »). analyse = hors exclusions dures ; trame = tout.
  const on = useQuery({ queryKey: ['filtre', filters, true], queryFn: () => getFiltre({ ...filters, analyseLabuse: true }, 0) })
  const off = useQuery({ queryKey: ['filtre', filters, false], queryFn: () => getFiltre({ ...filters, analyseLabuse: false }, 0) })
  const compteAnalyse = on.data?.compte             // ce que l'analyse RETIENT (déclassements inclus)
  const compteTrame = off.data?.compte              // toute la trame (le cadastre analysé)
  const compteExclues = (compteTrame != null && compteAnalyse != null) ? compteTrame - compteAnalyse : null
  const compteActuel = filters.analyseLabuse ? compteAnalyse : compteTrame

  return (
    <div className="card-elev px-3 py-2">
      {/* En-tête : compteur en direct + interrupteur — chaque nombre DIT son périmètre (réconcilié :
          trame = retenues par l'analyse + exclusions dures ; jamais de soustraction laissée au client). */}
      <div className="flex items-center justify-between">
        <div>
          <p className="label-caps">{filters.analyseLabuse ? 'Retenues par l’analyse' : 'Toute la trame'}</p>
          <div className="flex items-baseline gap-2">
            <span className="text-[22px] font-semibold text-txt-hi tabular-nums">
              {compteActuel == null ? '…' : nf.format(compteActuel)}</span>
            {filters.analyseLabuse && compteTrame != null && compteExclues != null && (
              <span className="text-[11px] text-txt-dim">
                sur <span className="tabular-nums">{nf.format(compteTrame)}</span> de la trame
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

      {/* ── BARRE NIVEAU 1 ── */}
      <div className="mt-1 divide-y divide-line-2/50">
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

      <button onClick={resetFilters}
        className="mt-2 min-h-7 w-full rounded-lg border border-line-2 py-1 text-[11px] text-txt-dim transition-colors duration-quick hover:text-txt">
        Réinitialiser les filtres
      </button>
    </div>
  )
}
