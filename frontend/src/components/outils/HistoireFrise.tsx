/**
 * OUTILS-MUSCLER-2 Lot C — la FRISE DES FAITS de « Remonter le temps ». Sous le comparateur
 * d'orthos (qui ne bouge pas), une frise horizontale sur le MÊME AXE TEMPOREL que les millésimes
 * d'orthophotos (repères TEMPS_MILLESIMES posés à leur année sur un axe linéaire 1950→aujourd'hui).
 * Un fait = un repère daté (marqueur par famille, couleurs de la DA) ; la précision SE VOIT :
 * maille jour = point plein, année = anneau large (moins précis), millésime propriétaire = barre
 * en tirets entre les deux 1ᵉʳ janvier (un écart constaté, pas une date). Clic → détail dans le
 * patron de carte existant + ponts FIX-3 (Permis / fiche-ventes / Scan patrimoine, fil de retour).
 * Aucun calcul métier ici : /moteurs/histoire sert tout (dates déjà à leur maille réelle).
 */
import { useQuery } from '@tanstack/react-query'
import { useEffect, useMemo, useRef, useState } from 'react'
import { getHistoire, type HistoireFait } from '../../lib/api'
import { fmtDateNum, fmtEur, fmtInt } from '../../lib/format'
import { TOKENS } from '../../lib/tokens'
import { useApp } from '../../store/useApp'
import { Squelette } from '../Loading'
import { Siren } from '../shared/Siren'
import { TEMPS_MILLESIMES } from '../map/basemaps'
import { Bouton } from '../ui/Bouton'

// REMONTER-TEMPS-2 Lot A — ÉCHELLE NON LINÉAIRE, FIXE pour tout le monde (prévisible, jamais un zoom
// auto qui change d'une parcelle à l'autre). L'axe linéaire écrasait tous les faits récents sur les
// derniers pixels (1950-2018 vide). On donne la place au récent en 3 segments : 1950-2000 = 20 % de
// la largeur · 2000-2015 = 30 % · 2015-aujourd'hui = 50 %. Bornes FIXES (l'axe des orthos), un fait
// antérieur à 1950 se cale au bord gauche.
const AXE_MIN = 1950
const AXE_MAX = new Date().getFullYear() + 1   // +1 : l'année en cours a de la place à droite

// Segments (année de début, année de fin, % de gauche, % de droite). Contigus, couvrent 0→100 %.
const SEGMENTS = [
  { a: 1950, b: 2000, x0: 0, x1: 20 },
  { a: 2000, b: 2015, x0: 20, x1: 50 },
  { a: 2015, b: AXE_MAX, x0: 50, x1: 100 },
] as const
// Bornes internes (2000, 2015) où l'échelle change de pente — matérialisées sur le rail.
const SEG_BORNES = [{ an: 2000, x: 20 }, { an: 2015, x: 50 }]

function pct(annee: number): number {
  const y = Math.min(AXE_MAX, Math.max(AXE_MIN, annee))
  for (const s of SEGMENTS) if (y <= s.b) return s.x0 + ((y - s.a) / (s.b - s.a)) * (s.x1 - s.x0)
  return 100
}

// Couleur par famille — tokens existants de la DA, rien de nouveau (LOI-0).
const FAM = {
  vente: { c: TOKENS.amber, label: 'Vente' },
  permis: { c: TOKENS.mint, label: 'Permis' },
  // DA-FIX-4 Lot 3 (DA-039) — plus de bleu d'interface : la catégorie « Propriétaire » passe au gris neutre DA.
  proprietaire: { c: TOKENS.stExclue, label: 'Propriétaire' },
  decoupe: { c: TOKENS.violet, label: 'Découpe' },
} as const

/** Date affichée à sa MAILLE RÉELLE (le back la sert déjà à la bonne maille). */
function dateAffichee(f: HistoireFait): string {
  if (f.maille === 'millesime') return `entre le 1ᵉʳ janv. ${f.de_millesime} et le 1ᵉʳ janv. ${f.a_millesime}`
  if (f.maille === 'annee') return `${f.date} (année seule — la source ne publie pas le jour)`
  return fmtDateNum(f.date)
}

/** Détail d'un fait (patron de carte existant) : libellé, chiffres, source, date à sa maille + pont. */
function FaitDetail({ f, idu, onClose }: { f: HistoireFait; idu: string; onClose: () => void }) {
  const select = useApp((s) => s.select)
  const setModule = useApp((s) => s.setModule)
  const setPermitToOpen = useApp((s) => s.setPermitToOpen)
  const setM02Prefill = useApp((s) => s.setM02Prefill)
  const setFicheTiroir = useApp((s) => s.setFicheTiroir)
  const pushOutilRetour = useApp((s) => s.pushOutilRetour)
  // FIX-3 : le pont navigue PUIS empile le retour — le fil restaure l'outil temps sur SA parcelle.
  const RETOUR = { module: 'temps', label: 'Remonter le temps', restore: { parcelPrefill: idu } } as const
  const ch = f.chiffres
  return (
    <div data-histoire-detail className="flex w-full max-w-[460px] flex-col gap-1.5 self-start rounded-lg border border-line-2 bg-surface-2 px-3 py-2">
      <div className="flex items-start gap-2">
        <span aria-hidden className="mt-1 h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: FAM[f.famille].c }} />
        <div className="min-w-0 flex-1">
          <p className="text-[11.5px] font-medium leading-snug text-txt-hi">{f.libelle}</p>
          <p className="text-[10.5px] text-txt-mut">{dateAffichee(f)}</p>
          {/* E2 — vente ré-attribuée : sa date précède la découpe DFI de cette parcelle → elle portait
              sur la parcelle mère. On garde la date vraie, on le dit (pas un ordre chronologique faux). */}
          {f.sur_parcelle_mere && (
            <p data-histoire-sur-mere className="mt-0.5 text-[10px] leading-snug text-cp-amber">
              sur la parcelle mère (avant la découpe de cette parcelle)
            </p>
          )}
        </div>
        <button onClick={onClose} aria-label="Fermer le détail" className="shrink-0 text-txt-mut hover:text-txt-hi">✕</button>
      </div>
      {/* chiffres associés, avec leur statut — uniquement ceux que la source porte */}
      <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-[10.5px] text-txt">
        {ch.prix_eur != null && <span>{fmtEur(ch.prix_eur)} <span className="text-txt-dim">(mutation entière)</span></span>}
        {ch.surface_bati_m2 != null && <span>{fmtInt(ch.surface_bati_m2)} m² bâti</span>}
        {ch.surface_terrain_m2 != null && <span>{fmtInt(ch.surface_terrain_m2)} m² terrain</span>}
        {ch.nb_logements != null && <span>{fmtInt(ch.nb_logements)} logement{ch.nb_logements > 1 ? 's' : ''}</span>}
        {ch.surf_hab_m2 != null && <span>{fmtInt(ch.surf_hab_m2)} m² hab.</span>}
        <span className="rounded bg-mint/15 px-1 text-[8.5px] font-medium text-mint">{ch.statut}</span>
      </div>
      {f.famille === 'proprietaire' && f.avant && f.apres && (
        <p className="text-[10.5px] leading-snug text-txt">
          <span className="text-txt-mut">{f.avant.denomination ?? '—'}</span>
          {f.avant.siren && <> · <Siren value={f.avant.siren} className="font-mono text-[9.5px] text-txt-dim" /></>}
          <span className="text-txt-dim"> → </span>
          <span>{f.apres.denomination ?? '—'}</span>
          {f.apres.siren && <> · <Siren value={f.apres.siren} className="font-mono text-[9.5px] text-txt-dim" /></>}
        </p>
      )}
      {f.famille === 'decoupe' && f.n_parcelles_liees != null && f.n_parcelles_liees > 0 && (
        <p className="text-[10px] leading-snug text-txt-dim">
          {fmtInt(f.n_parcelles_liees)} parcelle{f.n_parcelles_liees > 1 ? 's' : ''} liée{f.n_parcelles_liees > 1 ? 's' : ''}
          {(f.parcelles_liees?.length ?? 0) < (f.n_parcelles_liees ?? 0) && ` (${f.parcelles_liees?.length} affichées)`}
          {' '}: <span className="font-mono text-[9.5px]">{(f.parcelles_liees ?? []).join(' · ')}</span>
        </p>
      )}
      <p className="text-[9.5px] text-txt-dim">{f.source}</p>
      {/* ponts C4 — mêmes mécanismes que le reste de l'app (permitToOpen / ficheTiroir / m02Prefill) */}
      <div className="flex flex-wrap gap-2">
        {f.famille === 'permis' && f.permit_id && (
          <Bouton niveau="lien" data-histoire-pont-permis
            onClick={() => { setPermitToOpen(f.permit_id!); setModule('permis'); pushOutilRetour(RETOUR) }}>Voir dans Permis →</Bouton>
        )}
        {f.famille === 'vente' && (
          /* pas de fil de retour ici : la fiche est un OVERLAY au-dessus de l'outil temps resté
             ouvert (la fermer y ramène) — le fil FIX-3 est réservé aux ponts outil→outil. */
          <Bouton niveau="lien" data-histoire-pont-vente
            onClick={() => { setFicheTiroir(idu, 'marche'); select(idu) }}>Voir la fiche — ventes →</Bouton>
        )}
        {f.famille === 'proprietaire' && f.apres?.siren && (
          <Bouton niveau="lien" data-histoire-pont-scan
            onClick={() => { setM02Prefill(f.apres!.siren!.replace(/\D/g, '').slice(0, 9)); setModule('patrimoine'); pushOutilRetour(RETOUR) }}>Scan patrimoine →</Bouton>
        )}
      </div>
    </div>
  )
}

/** La frise elle-même : rail linéaire 1950→aujourd'hui, repères d'orthos dessous, faits dessus. */
export function HistoireFrise({ idu }: { idu: string }) {
  const q = useQuery({ queryKey: ['histoire', idu], queryFn: () => getHistoire(idu), retry: false })
  const [sel, setSel] = useState<number | null>(null)
  const racineRef = useRef<HTMLDivElement>(null)
  useEffect(() => setSel(null), [idu])
  // la barre change la hauteur du comparateur → les cartes maplibre se recalent (trackResize).
  useEffect(() => { window.dispatchEvent(new Event('resize')) }, [q.data?.n])
  // Lot A2 — un seul encart ouvert à la fois (état `sel` unique) ; fermeture AU CLIC AILLEURS
  // (hors frise et hors encart). Le clic sur un point rouvre/bascule (géré sur le point lui-même).
  useEffect(() => {
    if (sel == null) return
    const surClicAilleurs = (e: MouseEvent) => {
      if (racineRef.current && !racineRef.current.contains(e.target as Node)) setSel(null)
    }
    document.addEventListener('mousedown', surClicAilleurs)
    return () => document.removeEventListener('mousedown', surClicAilleurs)
  }, [sel])

  // Empilement C3 : les faits qui tombent le MÊME MOIS se posent sur des RANGÉES successives (aucun
  // masqué) ; les faits de mois différents partagent la rangée 0 et se répartissent sur l'axe (avec
  // l'échelle non linéaire, le récent a la place de s'étaler). Clé de position = année-mois pour un
  // jour, année seule pour un anneau/tiret (qui occupent déjà de la largeur).
  const lanes = useMemo(() => {
    const vus = new Map<string, number>()
    return (q.data?.faits ?? []).map((f) => {
      const cle = f.maille === 'jour' && f.date ? f.date.slice(0, 7) : `y${f.annee ?? AXE_MIN}`
      const lane = vus.get(cle) ?? 0
      vus.set(cle, lane + 1)
      return lane
    })
  }, [q.data?.faits])
  const maxLane = lanes.length ? Math.max(...lanes) : 0

  const faits = q.data?.faits ?? []
  return (
    <div ref={racineRef} data-histoire-frise className="flex shrink-0 flex-col gap-2 border-t border-line bg-surface-1 px-4 pb-2 pt-1.5">
      <div className="min-w-0">
        {/* bandeau C6 — millésimes des sources servies, même forme que les mentions de fraîcheur */}
        <p data-histoire-sources className="truncate text-[9.5px] text-txt-dim">
          Faits datés — {(q.data?.sources ?? []).filter((s) => s.maj)
            .map((s) => `${s.nom} : ${/^\d{4}-/.test(s.maj!) ? fmtDateNum(s.maj) : s.maj}`).join(' · ') || '…'}
        </p>
        {q.isLoading && <Squelette lignes={1} className="py-2" />}
        {q.isError && <p className="py-2 text-[10.5px] text-txt-mut">Faits momentanément indisponibles — les orthos restent comparables.</p>}
        {q.data && q.data.n === 0 && (
          /* C5 — état vide honnête : la frise ne bloque rien, les orthos restent comparables */
          <p data-histoire-vide className="py-2 text-[10.5px] text-txt-mut">
            Aucun fait daté connu pour cette parcelle (ventes, permis, propriétaire, découpes).
          </p>
        )}
        {q.data && q.data.n > 0 && (
          <div className="relative mt-1" style={{ height: 34 + maxLane * 14 }}>
            {/* faits — au-dessus du rail, une rangée par fait d'une même année */}
            {faits.map((f, i) => {
              const on = sel === i
              const bottom = 22 + lanes[i] * 14
              const key = `${f.famille}-${i}`
              const title = `${f.libelle} — ${dateAffichee(f)}${f.sur_parcelle_mere ? ' · sur la parcelle mère' : ''}`
              if (f.maille === 'millesime' && f.de_millesime && f.a_millesime) {
                // barre en tirets entre les deux 1ᵉʳ janvier : un écart, pas une date
                const l = pct(f.de_millesime), w = Math.max(1.2, pct(f.a_millesime) - l)
                return (
                  <button key={key} data-histoire-fait={f.famille} aria-label={title} aria-pressed={on}
                    onClick={() => setSel(on ? null : i)}
                    className="absolute h-2 rounded-sm border border-dashed"
                    style={{ left: `${l}%`, width: `${w}%`, bottom, borderColor: FAM[f.famille].c,
                             background: on ? `${FAM[f.famille].c}44` : `${FAM[f.famille].c}1a` }} />
                )
              }
              if (f.maille === 'annee') {
                // année seule : anneau LARGE (toute l'année) — visiblement moins précis qu'un point
                const l = pct(f.annee ?? AXE_MIN), w = Math.max(1.2, pct((f.annee ?? AXE_MIN) + 1) - l)
                return (
                  <button key={key} data-histoire-fait={f.famille} aria-label={title} aria-pressed={on}
                    onClick={() => setSel(on ? null : i)}
                    className="absolute h-2.5 rounded-full border-2 bg-transparent"
                    style={{ left: `${l}%`, width: `${w}%`, bottom, borderColor: FAM[f.famille].c,
                             background: on ? `${FAM[f.famille].c}33` : undefined }} />
                )
              }
              const dayFrac = f.date && /^\d{4}-(\d{2})-(\d{2})/.test(f.date)
                ? (new Date(f.date).getMonth() + 0.5) / 12 : 0.5
              return (
                <button key={key} data-histoire-fait={f.famille} aria-label={title} aria-pressed={on}
                  onClick={() => setSel(on ? null : i)}
                  className="absolute h-2.5 w-2.5 -translate-x-1/2 rounded-full"
                  style={{ left: `${pct((f.annee ?? AXE_MIN) + dayFrac)}%`, bottom,
                           background: FAM[f.famille].c, outline: on ? `2px solid ${FAM[f.famille].c}66` : undefined }} />
              )
            })}
            {/* rail + repères des millésimes d'orthophotos (même axe temporel que le comparateur) */}
            <div className="absolute inset-x-0 bottom-[18px] h-px bg-line-2" />
            {/* Lot A1 — bornes des segments (2000, 2015) où l'échelle change de pente : trait vertical
                léger de haut en bas du rail, pour que la rupture d'échelle SE VOIE. */}
            {SEG_BORNES.map((s) => (
              <span key={s.an} aria-hidden className="absolute bottom-[16px] top-0 w-px bg-line-3/70"
                style={{ left: `${s.x}%` }} />
            ))}
            {TEMPS_MILLESIMES.map((m) => (
              <span key={m.key} className="absolute bottom-0 -translate-x-1/2 font-mono text-[9px] leading-none text-txt-dim"
                style={{ left: `${pct(Number(m.an))}%` }}>
                <span className="absolute -top-[7px] left-1/2 h-[5px] w-px -translate-x-1/2 bg-line-3" />{m.an}
              </span>
            ))}
            <span className="absolute bottom-0 right-0 font-mono text-[9px] leading-none text-txt-dim">Auj.</span>
          </div>
        )}
        {q.data && q.data.n > 0 && (
          /* légende des familles — mêmes couleurs que les repères */
          <div data-histoire-legende className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-[9.5px] text-txt-dim">
            {(Object.keys(FAM) as (keyof typeof FAM)[]).map((k) => (
              <span key={k} className="flex items-center gap-1">
                <span aria-hidden className="h-2 w-2 rounded-full" style={{ background: FAM[k].c }} />{FAM[k].label}
              </span>
            ))}
            <span className="text-txt-faint">point = jour · anneau = année seule · tirets = entre deux millésimes</span>
          </div>
        )}
      </div>
      {sel != null && faits[sel] && <FaitDetail f={faits[sel]} idu={idu} onClose={() => setSel(null)} />}
    </div>
  )
}
