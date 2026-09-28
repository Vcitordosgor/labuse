// RETOURS-13 P6 — PROFIL ALTIMÉTRIQUE (tiroir Terrain). Coupe le long du plus grand axe de la
// parcelle, lue LIVE dans le RGE ALTI (endpoint /parcels/{idu}/profil-altimetrique). Graphique SVG
// (DA) + chiffres au vocabulaire cartes.gouv (distance, dénivelé +/-, pente moyenne, plus forte pente).
// FICHE-FIX-4 (Lot D) — OUVERT PAR DÉFAUT (plus de <details>), sur la parcelle seule ; la mesure
// libre (« Tracer un autre profil ») est RETIRÉE : elle n'a pas sa place dans la fiche.
import { useQuery } from '@tanstack/react-query'
import { getProfilParcelle, type ProfilAltimetrique as Profil } from '../../lib/api'
import { GroupLabel } from './primitives'

// FRONT-CHIFFRES-1 — null → « — » (jamais un 0 fabriqué pour une absence) ; un vrai 0
// (terrain plat, dénivelé nul) reste « 0 ». Le bloc est déjà gardé par `p.disponible`.
const nf = (n: number | null | undefined) => (n == null ? '—' : n.toLocaleString('fr-FR', { maximumFractionDigits: 0 }))
const nf1 = (n: number | null | undefined) => (n == null ? '—' : n.toLocaleString('fr-FR', { maximumFractionDigits: 1 }))

// le tracé SVG : altitude (y, inversé) vs distance (x). Points no-data (alt null) coupent le trait.
function Graphe({ p }: { p: Profil }) {
  const W = 300, H = 108, PAD_L = 30, PAD_R = 8, PAD_T = 8, PAD_B = 18
  const innerW = W - PAD_L - PAD_R, innerH = H - PAD_T - PAD_B
  const valides = p.points.filter((q) => q.alt_m != null) as { dist_m: number; alt_m: number }[]
  if (valides.length < 2) return null
  const dMax = p.points[p.points.length - 1]?.dist_m || 1
  const aMin = p.altitude_min_m ?? Math.min(...valides.map((q) => q.alt_m))
  const aMax = p.altitude_max_m ?? Math.max(...valides.map((q) => q.alt_m))
  const span = Math.max(aMax - aMin, 1)
  const x = (d: number) => PAD_L + (d / dMax) * innerW
  const y = (a: number) => PAD_T + (1 - (a - aMin) / span) * innerH
  // segments continus (rupture sur les trous no-data)
  const segs: string[] = []
  let cur: string[] = []
  for (const q of p.points) {
    if (q.alt_m == null) { if (cur.length) { segs.push(cur.join(' ')); cur = [] }; continue }
    cur.push(`${x(q.dist_m).toFixed(1)},${y(q.alt_m).toFixed(1)}`)
  }
  if (cur.length) segs.push(cur.join(' '))
  const aire = valides.map((q) => `${x(q.dist_m).toFixed(1)},${y(q.alt_m).toFixed(1)}`).join(' ')
  return (
    <svg data-profil-svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="Profil altimétrique">
      {/* cadre + graduation altitude */}
      <line x1={PAD_L} y1={PAD_T} x2={PAD_L} y2={PAD_T + innerH} stroke="var(--line-2)" strokeWidth={1} />
      <line x1={PAD_L} y1={PAD_T + innerH} x2={W - PAD_R} y2={PAD_T + innerH} stroke="var(--line-2)" strokeWidth={1} />
      <text x={PAD_L - 4} y={PAD_T + 4} textAnchor="end" fontSize={8} fill="var(--txt-dim)">{nf(aMax)}</text>
      <text x={PAD_L - 4} y={PAD_T + innerH} textAnchor="end" fontSize={8} fill="var(--txt-dim)">{nf(aMin)}</text>
      <text x={PAD_L} y={H - 4} textAnchor="start" fontSize={8} fill="var(--txt-dim)">0</text>
      <text x={W - PAD_R} y={H - 4} textAnchor="end" fontSize={8} fill="var(--txt-dim)">{nf(dMax)} m</text>
      {/* aire sous la coupe (translucide) + trait */}
      <polygon points={`${x(valides[0].dist_m).toFixed(1)},${(PAD_T + innerH).toFixed(1)} ${aire} ${x(valides[valides.length - 1].dist_m).toFixed(1)},${(PAD_T + innerH).toFixed(1)}`}
        fill="var(--mint)" fillOpacity={0.1} />
      {segs.map((s, i) => (
        <polyline key={i} points={s} fill="none" stroke="var(--mint)" strokeWidth={1.6} strokeLinejoin="round" strokeLinecap="round" />
      ))}
    </svg>
  )
}

function Chiffre({ l, v, tone }: { l: string; v: string; tone?: 'up' | 'down' }) {
  return (
    <div className="flex flex-col">
      <span className="text-[9px] uppercase tracking-wide text-txt-dim">{l}</span>
      <span className={`text-[12px] font-medium ${tone === 'up' ? 'text-mint' : tone === 'down' ? 'text-[#C08A6E]' : 'text-txt-hi'}`}>{v}</span>
    </div>
  )
}

function Corps({ p }: { p: Profil }) {
  if (!p.disponible) {
    return <p className="py-1 text-[11px] text-txt-mut">{p.motif ?? 'Relief non disponible sur cette emprise.'}</p>
  }
  return (
    <div className="flex flex-col gap-2">
      <Graphe p={p} />
      {/* COHERENCE-FIX-1 (lot D) — une mesure absente s'affiche « — », jamais « 0 m » / « 0 % »
          (les `?? 0` servaient un faux zéro quand le profil ne portait pas la mesure). */}
      <div className="grid grid-cols-3 gap-x-3 gap-y-2">
        {/* fusion COHERENCE-FIX-1 × FRONT-CHIFFRES-1 : les deux côtés tuaient le même faux zéro —
            on garde la garde PAR CHAMP (« — » sec, jamais « — m » que donnerait nf(null) + unité),
            et le nf/nf1 null-safe de main sert le graphe. */}
        <Chiffre l="Distance" v={p.distance_m != null ? `${nf(p.distance_m)} m` : '—'} />
        <Chiffre l="Dénivelé +" v={p.denivele_positif_m != null ? `+${nf(p.denivele_positif_m)} m` : '—'} tone="up" />
        <Chiffre l="Dénivelé −" v={p.denivele_negatif_m != null ? `−${nf(p.denivele_negatif_m)} m` : '—'} tone="down" />
        <Chiffre l="Pente moyenne" v={p.pente_moyenne_pct != null ? `${nf1(p.pente_moyenne_pct)} %` : '—'} />
        <Chiffre l="Plus forte pente" v={p.pente_max_pct != null ? `${nf1(p.pente_max_pct)} %` : '—'} />
        <Chiffre l="Altitude" v={p.altitude_min_m != null && p.altitude_max_m != null
          ? `${nf(p.altitude_min_m)}–${nf(p.altitude_max_m)} m` : '—'} />
      </div>
      <p className="text-[9px] leading-snug text-txt-dim">
        {p.axe === 'trace' ? 'Le long de la ligne tracée. ' : 'Le long du plus grand axe de la parcelle. '}
        Source {p.source}. Vocabulaire cartes.gouv (pente moyenne = grade absolu moyen).
      </p>
    </div>
  )
}

export function ProfilAltimetrique({ idu }: { idu: string }) {
  // coupe le long du plus grand axe de la parcelle (RGE ALTI), OUVERTE par défaut (Lot D).
  const axeQ = useQuery({ queryKey: ['profil', idu], queryFn: () => getProfilParcelle(idu), retry: false, staleTime: 5 * 60 * 1000 })
  const data = axeQ.data
  return (
    <div data-profil-altimetrique className="border-t border-line-2 pt-2">
      <GroupLabel>Profil altimétrique</GroupLabel>
      <div className="mt-2 flex flex-col gap-2">
        {axeQ.isLoading && <p className="py-1 text-[11px] text-txt-mut">Lecture du relief (RGE ALTI)…</p>}
        {!axeQ.isLoading && axeQ.isError && (
          <p className="py-1 text-[11px] text-st-ecartee">Profil indisponible — réessayez.</p>
        )}
        {!axeQ.isLoading && data && <Corps p={data} />}
      </div>
    </div>
  )
}
