// RADAR (pige) · P6 D3 — onglet « Marché » : stats agrégées par commune (24 + total île).
// HONNÊTETÉ STATISTIQUE : chaque mesure porte son n ; sous le seuil (n<5) → « échantillon insuffisant »,
// AUCUN chiffre. Les comptes (actives, nouvelles…) sont des faits bruts. État de démarrage = digne :
// on explique que le corpus se constitue, pas un tableau de tirets qui fait peur. Couleurs source unique.
import { useQuery } from '@tanstack/react-query'
import { getRadarMarche, type RadarMarcheLigne, type RadarMesure } from '../../lib/api'
import { Squelette } from '../Loading'
import { ErrorState } from '../States'

const fmt = (v: number) => v.toLocaleString('fr-FR')

// une MESURE : valeur + unité si n≥seuil, sinon « — » (et le n est toujours dit, discrètement).
function Mesure({ m, unit }: { m: RadarMesure; unit: string }) {
  if (m.insuffisant) {
    return <span className="text-txt-dim" aria-label={`échantillon insuffisant (n=${m.n})`}>—</span>
  }
  return <span className="text-txt">{fmt(m.valeur!)}<span className="text-[9px] text-txt-dim">{unit} · n{m.n}</span></span>
}

function Ligne({ l, fort = false }: { l: RadarMarcheLigne; fort?: boolean }) {
  return (
    <tr className={`border-b border-line-2 ${fort ? 'font-medium text-txt-hi' : 'text-txt'}`}>
      <td className="py-1 pr-2">{l.commune}</td>
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
  const { data, isLoading, isError, refetch } = useQuery({ queryKey: ['radar-marche'], queryFn: getRadarMarche })
  if (isLoading) return <Squelette lignes={6} className="p-4" />
  // RETOURS-1 R9 (Vic) — CAUSE du « Chargement… » infini : `isError` n'était pas lu — une erreur
  // (ici : '/radar' absent du proxy vite dev → 404 HTML) laissait isLoading=false et data=undefined,
  // et l'écran restait sur « Chargement… » pour toujours. Désormais : erreur DITE + réessayer.
  if (isError || !data) return (
    <ErrorState message="Le marché du Radar n’a pas pu être chargé — le serveur n’a pas répondu." retry={() => refetch()} />
  )
  // FRONT-CHIFFRES-2 (F25) — le front ne décide plus le seuil « corpus jeune » : il lit le flag servi.
  const jeune = data.corpus_jeune

  return (
    <div className="flex flex-col gap-3 p-3">
      {jeune && (
        <div className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2.5 text-[11.5px] leading-relaxed text-txt-mut">
          Le corpus du Radar se constitue jour après jour (aujourd’hui {data.corpus_total} bien{data.corpus_total > 1 ? 's' : ''} suivi{data.corpus_total > 1 ? 's' : ''}).
          Les cellules encore vides sont normales : une médiane ou un taux n’est servi qu’à partir de {data.seuil_n} biens
          — jamais de fausse précision. Les compteurs, eux, sont exacts dès le premier.
        </div>
      )}
      {/* DA-FIX-4 Lot 4 (DA-030) — plein écran (overlay 1240px, cf. Communes) : table conservée mais
          AUCUNE barre horizontale (overflow-x retiré ; la table tient en pleine largeur). */}
      <div>
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
            <Ligne l={data.ile} fort />
            {data.communes.map((l) => <Ligne key={l.commune} l={l} />)}
          </tbody>
        </table>
      </div>
    </div>
  )
}
