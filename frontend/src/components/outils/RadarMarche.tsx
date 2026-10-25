// RADAR (pige) · P6 D3 — onglet « Marché » : stats agrégées par commune (24 + total île).
// HONNÊTETÉ STATISTIQUE : chaque mesure porte son n ; sous le seuil (n<5) → « échantillon insuffisant »,
// AUCUN chiffre. Les comptes (actives, nouvelles…) sont des faits bruts. État de démarrage = digne :
// on explique que le corpus se constitue, pas un tableau de tirets qui fait peur. Couleurs source unique.
import { useQuery } from '@tanstack/react-query'
import { getRadarMarche, type RadarMarcheLigne, type RadarMesure } from '../../lib/api'
import { communePastille } from '../../lib/communes'   // RECETTE-OUTILS-1 (point 11) — règle d'article
import { Squelette } from '../Loading'
import { ErrorState } from '../States'

const fmt = (v: number) => v.toLocaleString('fr-FR')
// RECETTE-OUTILS-1 (point 11) — date de la dernière collecte Radar (ISO → jj/mm/aaaa).
const fmtDate = (iso: string | null | undefined) => {
  if (!iso) return null
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? null : d.toLocaleDateString('fr-FR')
}

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
      {/* RECETTE-OUTILS-1 (point 11) — règle d'article des noms de commune (« Les Trois-Bassins » →
          « Trois-Bassins »), sauf Le Port / Le Tampon / La Possession. La ligne « Toute l'île » (pas
          d'article) n'est pas affectée. */}
      <td className="py-1 pr-2">{communePastille(l.commune)}</td>
      <td className="text-right tabular-nums">{l.actives}</td>
      <td className="text-right tabular-nums text-txt-mut">{l.nouvelles_30j}</td>
      <td className="text-right tabular-nums text-txt-mut">{l.retirees_30j}</td>
      {/* RECETTE-OUTILS-1 (point 11) — colonnes « Vend.90j » et « Échec » RETIRÉES : non alimentées
          (0 sur les 24 communes ET l'île ; le back les dérive de `vendue_le`/clôtures que la pige ne
          capte pas). On ne sert pas des zéros. */}
      <td className="text-right"><Mesure m={l.prix_m2_terrain} unit=" €/m²" /></td>
      <td className="text-right"><Mesure m={l.prix_m2_bati} unit=" €/m²" /></td>
      <td className="text-right"><Mesure m={l.delai_median_j} unit=" j" /></td>
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

  const capture = fmtDate(data.derniere_capture_at)
  return (
    <div className="flex flex-col gap-3 p-3">
      {/* RECETTE-OUTILS-1 (point 11) — la DATE de la dernière collecte est affichée dans l'encart du
          haut : le Radar est alimenté par l'extension (pas un cron), donc une collecte en retard (ou en
          pause) devient VISIBLE. « Nouv.30j » se lit relativement à cette date, pas à aujourd'hui. */}
      {capture && (
        <div data-radar-capture className="text-[10.5px] text-txt-dim">
          Dernière collecte : <b className="text-txt-mut">{capture}</b> — les fenêtres « 30 j / 90 j » se comptent à partir de cette date.
        </div>
      )}
      {/* RECETTE-1 (H3, Vic) — DATE de la dernière capture Radar (le bloc lit la même table que le Radar).
          Le Radar est alimenté par l'EXTENSION (Mac), pas un cron VPS : afficher la date rend une capture
          en retard VISIBLE (ex. « 27/09 » un 4/10 = extension non déposée depuis). */}
      {/* RECETTE-2 (E6) — phrase « Dernière capture … Radar alimenté par l'extension … vérifier
          l'extension » retirée (mécanique interne, pas pour le client). */}
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
              <th className="text-right">Retir.30j</th>
              <th className="text-right">€/m² terr.</th><th className="text-right">€/m² bâti</th>
              <th className="text-right">Délai méd.</th><th className="text-right">Part.</th>
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
