// RADAR (pige) · P6 D3 — onglet « Marché » : stats agrégées par commune (24 + total île).
// HONNÊTETÉ STATISTIQUE : chaque mesure porte son n ; sous le seuil (n<5) → « échantillon insuffisant »,
// AUCUN chiffre. Les comptes (actives, nouvelles…) sont des faits bruts. État de démarrage = digne :
// on explique que le corpus se constitue, pas un tableau de tirets qui fait peur. Couleurs source unique.
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getRadarMarche, getRadarSignaux, type RadarEcart, type RadarMarcheLigne, type RadarMesure } from '../../lib/api'

// RADAR-HTML (Lot 4) — « écart demandé/acté » d'une commune : médiane Radar (demandé) vs médiane DVF
// (acté). C'est la marge de négociation du moment. Écart CONSTATÉ entre deux sources datées, aucun verdict.
function EcartLigne({ label, e }: { label: string; e: RadarEcart }) {
  if (!e.calculable) {
    return <div className="flex items-center justify-between py-1 text-[11px] text-txt-dim"><span>{label}</span><span title={e.motif}>— (échantillon insuffisant)</span></div>
  }
  const baisse = (e.ecart_pct ?? 0) > 0
  return (
    <div className="flex items-center justify-between py-1 text-[11.5px]">
      <span className="text-txt-mut">{label}</span>
      <span className="tabular-nums text-txt">
        {e.demande_eur_m2!.toLocaleString('fr-FR')}<span className="text-[9px] text-txt-dim"> €/m² dem. · n{e.n_demande}</span>
        {' → '}{e.acte_eur_m2!.toLocaleString('fr-FR')}<span className="text-[9px] text-txt-dim"> acté · n{e.n_acte}</span>
        <span className={`ml-1.5 rounded px-1 py-0.5 text-[10px] ${baisse ? 'bg-amber/12 text-amber' : 'bg-mint/12 text-mint'}`}>{(e.ecart_pct! > 0 ? '+' : '')}{e.ecart_pct}%</span>
      </span>
    </div>
  )
}

function SignauxCommune({ communes }: { communes: string[] }) {
  const [commune, setCommune] = useState('')
  const { data } = useQuery({ queryKey: ['radar-signaux', commune], queryFn: () => getRadarSignaux(commune), enabled: !!commune })
  return (
    <div className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2.5">
      <div className="mb-1.5 flex items-center gap-2">
        <span className="font-mono text-[10px] uppercase tracking-wider text-txt-dim">Marge de négociation — écart demandé / acté</span>
        <select value={commune} onChange={(e) => setCommune(e.target.value)}
          className="ml-auto rounded border border-line-2 bg-surface-1 px-1.5 py-0.5 text-[11px] text-txt">
          <option value="">choisir une commune…</option>
          {communes.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>
      {commune && data && (
        <div className="flex flex-col divide-y divide-line-2">
          {/* RADAR-DEPOT-2 D5 — chaque famille DIT son périmètre : un chiffre sans périmètre n'est pas
              un fait. Le bâti recouvre maisons + appartements (copros embasées, comptées ici). */}
          <EcartLigne label={`Terrain${data.ecart_demande_acte.perimetre_terrain ? ` (${data.ecart_demande_acte.perimetre_terrain})` : ''}`} e={data.ecart_demande_acte.terrain} />
          <EcartLigne label={`Bâti${data.ecart_demande_acte.perimetre_bati ? ` (${data.ecart_demande_acte.perimetre_bati})` : ''}`} e={data.ecart_demande_acte.bati} />
          <p className="pt-1.5 text-[10px] text-txt-dim">Prix affiché du Radar (Sourcé portail) contre médiane DVF actée. Écart constaté, jamais une estimation ni une prévision.</p>
        </div>
      )}
      {!commune && <p className="text-[11px] text-txt-dim">Choisir une commune pour voir l’écart entre prix demandés (annonces) et prix actés (DVF).</p>}
    </div>
  )
}

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
  const { data, isLoading, isError, refetch } = useQuery({ queryKey: ['radar-marche'], queryFn: getRadarMarche })
  if (isLoading) return <div className="p-4 text-[12px] text-txt-dim">Chargement…</div>
  // RETOURS-1 R9 (Vic) — CAUSE du « Chargement… » infini : `isError` n'était pas lu — une erreur
  // (ici : '/radar' absent du proxy vite dev → 404 HTML) laissait isLoading=false et data=undefined,
  // et l'écran restait sur « Chargement… » pour toujours. Désormais : erreur DITE + réessayer.
  if (isError || !data) return (
    <div className="flex flex-col items-start gap-2 p-4 text-[12px] text-txt-mut">
      <p>Le marché du Radar n’a pas pu être chargé — le serveur n’a pas répondu.</p>
      <button onClick={() => refetch()} className="rounded-md border border-mint/50 bg-mint/10 px-2.5 py-1 text-[11px] font-medium text-mint hover:bg-mint/20">
        Réessayer
      </button>
    </div>
  )
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
      <SignauxCommune communes={data.communes.map((c) => c.commune)} />
      <p className="text-[10px] text-txt-dim">« — » = échantillon insuffisant (moins de {data.seuil_n} biens). Hors scoring. Données issues de la collecte manuelle.</p>
    </div>
  )
}
