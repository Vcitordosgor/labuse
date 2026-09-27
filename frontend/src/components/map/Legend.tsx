import { useQuery } from '@tanstack/react-query'
import { useState, type ReactNode } from 'react'
import { LEGEND_ORDER, LEGEND_V2_ORDER, STATUT_META, TIER_V2_META, ZONE_FAM_META, ZONE_FAM_ORDER } from '../../lib/status'
import { useApp } from '../../store/useApp'
import { Tip } from '../Tip'
import { ChevronSection } from '../panel/ChevronSection'

// Correctif M5 : quand un run scoring v2 existe, la carte colore par le tier v2 — la légende suit.
export function useV2Actif(): boolean {
  const q = useQuery({
    queryKey: ['v2-actif'],
    queryFn: async () => (await fetch('/v2/modele')).ok,
    retry: false, staleTime: Infinity,
  })
  return q.data === true
}

// SECTEUR-1 (S4) — état repli/déplié + groupes ouverts MÉMORISÉS (localStorage).
const LEG_LS = 'labuse.legende'
function readLeg(): { open: boolean; groupes: Record<string, boolean> } {
  try { return { open: false, groupes: {}, ...JSON.parse(localStorage.getItem(LEG_LS) || '{}') } }
  catch { return { open: false, groupes: {} } }
}
function writeLeg(v: { open: boolean; groupes: Record<string, boolean> }) {
  try { localStorage.setItem(LEG_LS, JSON.stringify(v)) } catch { /* indisponible : la légende reste fonctionnelle */ }
}

/** SECTEUR-1 (S4) — chaque groupe de la légende est un accordéon. La note de SOURCE passe dans le « i »
 *  du groupe (« DEAL Réunion… »), jamais dans le corps de la légende. */
function Groupe({ titre, note, open, onToggle, children }: {
  titre: ReactNode; note?: string; open: boolean; onToggle: () => void; children: ReactNode
}) {
  return (
    <div data-legend-groupe className="border-t border-line py-1.5 first:border-t-0 first:pt-0">
      <button onClick={onToggle} aria-expanded={open} aria-label={open ? 'Replier' : 'Déplier'}
        className="flex w-full items-center gap-1.5 text-left">
        <span className="label-caps flex-1">{titre}</span>
        {note && (
          <Tip garder side="top" tip={note}>
            <span role="button" tabIndex={0} aria-label="Source"
              className="flex h-[13px] w-[13px] items-center justify-center rounded-full border border-line-2 text-[8px] font-bold text-txt-dim hover:border-mint hover:text-mint">i</span>
          </Tip>
        )}
        <ChevronSection open={open} />
      </button>
      {open && <div className="mt-1.5">{children}</div>}
    </div>
  )
}

/** `inline` : rendu dans le tiroir mobile « Couches » au lieu du coin de carte. */
export function Legend({ inline = false }: { inline?: boolean }) {
  const verdict = useApp((s) => s.verdict)
  const analyse = useApp((s) => s.filters.analyseLabuse)
  const peint = useApp((s) => s.mapPeint)
  const v2 = useV2Actif()
  const [leg, setLeg] = useState(readLeg)
  const set = (v: typeof leg) => { setLeg(v); writeLeg(v) }

  // NETTOYAGE-1 (lot 1) — le store `layers` V1 (retiré à COUCHES-RETRAIT-1) n'était plus alimenté ; le
  // compteur « · N couches » qui le lisait affichait donc toujours « · 0 couche », et les groupes de
  // légende `if (layers.X)` des anciennes couches overlay ne rendaient jamais (remplacées par le tuyau →
  // `TuyauLegend`). Tous supprimés. Restent les légendes de PEINTURE, bien vivantes : le verdict (mode
  // analyse), le zonage PLU (aplat servi), les permis (outil Permis) — pilotées par `mapPeint`/`module`.
  const opinion = verdict && analyse
  const verdictPeint = opinion && peint.parcelles && !peint.zonage
  const zonagePeint = peint.zonage

  // SECTEUR-1 (S4) — les GROUPES actifs, dans l'ordre. Seuls ceux réellement peints apparaissent.
  const groupes: { id: string; titre: ReactNode; note?: string; body: ReactNode }[] = []
  // RETOURS-15 B1 (P2) — la légende « Permis (par état) » est RETIRÉE de la carte (demande Vic).
  // Les points restent colorés par état ; le panneau « Filtrer par état » porte déjà les couleurs.
  if (verdictPeint) groupes.push({
    id: 'verdict',
    titre: v2 ? 'Verdict · Classement servi' : 'Verdict · Classement historique',
    note: v2 ? 'Couleurs du classement servi (tiers Priorité → Écartée).' : 'Classement historique (repli) — le classement servi n\'est pas joignable sur cette vue.',
    body: (
      <div className="flex flex-col gap-1.5">
        {(v2 ? LEGEND_V2_ORDER : LEGEND_ORDER).map((t) => (
          <div key={t} className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full" style={{ background: v2 ? TIER_V2_META[t as keyof typeof TIER_V2_META].color : STATUT_META[t as keyof typeof STATUT_META].color }} />
            <span className="text-[11px] text-txt">{v2 ? TIER_V2_META[t as keyof typeof TIER_V2_META].label : STATUT_META[t as keyof typeof STATUT_META].label}</span>
          </div>
        ))}
      </div>
    ),
  })
  if (zonagePeint) groupes.push({
    id: 'zonage', titre: 'Zonage PLU (par type)',
    body: <div className="flex flex-col gap-1.5">{ZONE_FAM_ORDER.map((f) => (
      <div key={f} className="flex items-center gap-2"><span className="h-2 w-2 rounded-full" style={{ background: ZONE_FAM_META[f].color }} /><span className="text-[11px] text-txt">{ZONE_FAM_META[f].label}</span></div>
    ))}</div>,
  })

  if (!groupes.length) return null

  // SECTEUR-1 (S4) — repliée par défaut ; le PREMIER groupe s'ouvre par défaut, les autres repliés.
  const grpOpen = (id: string, i: number) => leg.groupes[id] ?? (i === 0)
  const toggleGrp = (id: string) => set({ ...leg, groupes: { ...leg.groupes, [id]: !grpOpen(id, groupes.findIndex((g) => g.id === id)) } })

  const shell = inline ? 'rounded-xl bg-surface-2' : 'floating absolute bottom-4 right-4 hidden sm:block'
  return (
    <div data-legend className={`${shell} w-[240px]`}>
      <button data-legend-toggle onClick={() => set({ ...leg, open: !leg.open })} aria-expanded={leg.open}
        aria-label={leg.open ? 'Replier la légende' : 'Déplier la légende'}
        className="flex w-full items-center gap-2 px-3.5 py-2 text-left">
        {/* NETTOYAGE-1 — le compteur « · N couches » (store layers V1 mort) est retiré : plus que « Légende ». */}
        <span className="label-caps flex-1">Légende</span>
        <ChevronSection open={leg.open} />
      </button>
      {leg.open && (
        <div data-legend-corps className="max-h-[min(70vh,34rem)] overflow-y-auto overscroll-contain border-t border-line px-3.5 py-2">
          {groupes.map((g, i) => (
            <Groupe key={g.id} titre={g.titre} note={g.note} open={grpOpen(g.id, i)} onToggle={() => toggleGrp(g.id)}>{g.body}</Groupe>
          ))}
        </div>
      )}
    </div>
  )
}
