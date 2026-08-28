// RADAR (pige) · P6 D3 — onglet « Marché » : stats agrégées par commune (24 + total île).
// HONNÊTETÉ STATISTIQUE : chaque mesure porte son n ; sous le seuil (n<5) → « échantillon insuffisant »,
// AUCUN chiffre. Les comptes (actives, nouvelles…) sont des faits bruts. État de démarrage = digne :
// on explique que le corpus se constitue, pas un tableau de tirets qui fait peur. Couleurs source unique.
import { useQuery } from '@tanstack/react-query'
import { getRadarMarche, type RadarMarcheLigne, type RadarMesure } from '../../lib/api'

const fmt = (v: number) => v.toLocaleString('fr-FR')

// une MESURE : valeur + unité si n≥seuil, sinon « — » (et le n est toujours dit, discrètement).
function Mesure({ m, unit }: { m: RadarMesure; unit: string }) {
  if (m.insuffisant) {
    return <span className="text-txt-dim" title={`échantillon insuffisant (n=${m.n})`}>—</span>
  }
  return <span className="text-txt">{fmt(m.valeur!)}<span className="text-[9px] text-txt-dim">{unit} · n{m.n}</span></span>
}

// mini-heatmap : intensité d'activité par commune (opacité du vert de marque selon les annonces actives).
function Chaleur({ n, max }: { n: number; max: number }) {
  const op = max > 0 ? Math.min(1, 0.12 + 0.88 * (n / max)) : 0
  return <span className="inline-block h-2.5 w-2.5 rounded-[3px]" style={{ background: n ? `rgba(74,222,128,${op})` : 'transparent', outline: n ? 'none' : '1px solid var(--line-2)' }} />
}

function Ligne({ l, max, fort = false }: { l: RadarMarcheLigne; max: number; fort?: boolean }) {
  return (
    <tr className={`border-b border-line-2 ${fort ? 'font-medium text-txt-hi' : 'text-txt'}`}>
      <td className="flex items-center gap-1.5 py-1 pr-2">{!fort && <Chaleur n={l.actives} max={max} />}{l.commune}</td>
      <td className="text-right tabular-nums">{l.actives}</td>
      <td className="text-right tabular-nums text-txt-mut">{l.nouvelles_30j}</td>
      <td className="text-right tabular-nums text-txt-mut">{l.retirees_30j}</td>
      <td className="text-right tabular-nums text-txt-mut">{l.vendues_90j}</td>
      <td className="text-right"><Mesure m={l.prix_m2_terrain} unit=" €/m²" /></td>
      <td className="text-right"><Mesure m={l.prix_m2_bati} unit=" €/m²" /></td>
      <td className="text-right"><Mesure m={l.delai_median_j} unit=" j" /></td>
      <td className="text-right"><Mesure m={l.taux_echec_pct} unit=" %" /></td>
      <td className="text-right"><Mesure m={l.part_particuliers_pct} unit=" %" /></td>
    </tr>
  )
}

export function RadarMarche() {
  const { data, isLoading } = useQuery({ queryKey: ['radar-marche'], queryFn: getRadarMarche })
  if (isLoading || !data) return <div className="p-4 text-[12px] text-txt-dim">Chargement…</div>
  const max = Math.max(1, ...data.communes.map((c) => c.actives))
  const jeune = data.corpus_total < 40

  return (
    <div className="flex flex-col gap-3 p-3">
      {jeune && (
        <div className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2.5 text-[11.5px] leading-relaxed text-txt-mut">
          Le corpus du Radar se constitue jour après jour (aujourd’hui {data.corpus_total} bien{data.corpus_total > 1 ? 's' : ''} suivi{data.corpus_total > 1 ? 's' : ''}).
          Les cellules encore vides sont normales : une médiane ou un taux n’est servi qu’à partir de {data.seuil_n} biens
          — jamais de fausse précision. Les compteurs, eux, sont exacts dès le premier.
        </div>
      )}
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-[11px]">
          <thead>
            <tr className="border-b border-line-3 font-mono text-[9px] uppercase tracking-wider text-txt-dim">
              <th className="py-1 text-left">Commune</th>
              <th className="text-right">Actives</th><th className="text-right">Nouv.30j</th>
              <th className="text-right">Retir.30j</th><th className="text-right">Vend.90j</th>
              <th className="text-right">€/m² terr.</th><th className="text-right">€/m² bâti</th>
              <th className="text-right">Délai méd.</th><th className="text-right">Échec</th><th className="text-right">Part.</th>
            </tr>
          </thead>
          <tbody>
            <Ligne l={data.ile} max={max} fort />
            {data.communes.map((l) => <Ligne key={l.commune} l={l} max={max} />)}
          </tbody>
        </table>
      </div>
      <p className="text-[10px] text-txt-dim">« — » = échantillon insuffisant (moins de {data.seuil_n} biens). Hors scoring. Données issues de la collecte manuelle.</p>
    </div>
  )
}
