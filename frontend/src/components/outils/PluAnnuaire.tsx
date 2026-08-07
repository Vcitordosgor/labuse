import { useMutation, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { pluAnnuaireSearch, pluAnnuaireCommunes, type PluExtrait } from '../../lib/api'

// M51 — ANNUAIRE PLU : recherche full-text dans le règlement écrit OPPOSABLE des communes (source
// Géoportail de l'Urbanisme). SERT DU VERBATIM SOURCÉ — commune, document, article, PAGE PDF, lien —
// jamais un résumé ni un reformulé. Le doute et la pagination ambiguë sont DITS à l'écran. RNU et
// communes non réconciliées : réponse honnête, jamais un trou masqué.
export function PluAnnuaire() {
  const [q, setQ] = useState('')
  const [insee, setInsee] = useState('')
  const communes = useQuery({ queryKey: ['plu-communes'], queryFn: pluAnnuaireCommunes })
  const m = useMutation({ mutationFn: () => pluAnnuaireSearch(q.trim(), insee || undefined) })
  const d = m.data
  const run = () => { if (q.trim().length >= 2) m.mutate() }
  const nomInsee = (code: string | null) => communes.data?.communes.find((c) => c.insee === code)?.commune

  return (
    <div data-plu-annuaire className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
      <div className="flex flex-col gap-2 rounded-lg border border-line-2 bg-surface-2 p-3">
        <p className="text-[10.5px] leading-snug text-txt-mut">
          Cherchez dans le règlement écrit opposable (source Géoportail de l’Urbanisme). Le résultat est
          le VERBATIM du règlement + sa référence exacte (article, page PDF, lien) — jamais un résumé.
          Vérifiez toujours au document ; ceci n’est pas un conseil juridique.
        </p>
        <div className="flex gap-2">
          <select value={insee} onChange={(e) => setInsee(e.target.value)}
            className="rounded-md border border-line-2 bg-surface-3 px-2 py-1.5 text-[12px] text-txt">
            <option value="">Toute l’île</option>
            {communes.data?.communes.map((c) => (
              <option key={c.insee} value={c.insee} disabled={c.statut !== 'servable'}>
                {c.commune}{c.statut !== 'servable'
                  ? ` — ${c.statut === 'rnu' ? 'RNU, pas de règlement' : c.statut === 'revision' ? 'révision, non servi' : 'non ingéré'}`
                  : ''}
              </option>
            ))}
          </select>
          <input data-plu-q value={q} onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') run() }}
            placeholder="ex. hauteur clôture, stationnement, emprise au sol"
            className="flex-1 rounded-md border border-line-2 bg-surface-3 px-2 py-1.5 text-[12px] text-txt" />
          <button onClick={run} disabled={q.trim().length < 2 || m.isPending}
            className="rounded-md border border-violet/50 bg-violet/15 px-3 py-1.5 text-[12px] font-medium text-violet disabled:opacity-40">
            {m.isPending ? '…' : 'Chercher'}
          </button>
        </div>
        {communes.data && (
          <div className="text-[10px] text-txt-dim">
            {communes.data.servables}/24 communes servables — les autres (RNU, révision en cours) sont
            dites, jamais masquées.
          </div>
        )}
      </div>

      {m.isError && (
        <div className="rounded-lg border border-st-ecartee/40 bg-st-ecartee/10 px-3 py-2 text-[11px] text-st-ecartee">
          Erreur de recherche.
        </div>
      )}

      {d?.message && (
        <div className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-[11.5px] text-txt-mut">
          <span className="mr-1">🕓</span>{d.message}
        </div>
      )}

      {d && !d.message && (
        <div data-plu-results className="flex flex-col gap-2">
          <div className="text-[11px] text-txt-mut">
            {d.n} extrait{d.n > 1 ? 's' : ''} — {d.insee ? nomInsee(d.insee) : 'toute l’île'}
          </div>
          {d.resultats.map((r: PluExtrait, i: number) => (
            <div key={i} className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2">
              <div className="flex flex-wrap items-baseline gap-x-2 text-[11px]">
                <span className="font-medium text-violet">{r.article_ref}</span>
                {r.zone && <span className="text-txt-mut">zone {r.zone}</span>}
                <span className="text-txt-mut">{r.commune}</span>
                <span className="text-txt-dim">p. PDF {r.page_pdf}</span>
                {r.doute && (
                  <span className="rounded bg-st-ecartee/15 px-1 text-[9.5px] text-st-ecartee">
                    doute — vérifier au PDF
                  </span>
                )}
              </div>
              <pre className="mt-1 whitespace-pre-wrap font-sans text-[11px] leading-snug text-txt">{r.texte_verbatim}</pre>
              <div className="mt-1 flex flex-wrap gap-x-2 text-[10px] text-txt-dim">
                <span>{r.document}{r.millesime ? ` · ${r.millesime}` : ''}</span>
                <a href={r.source_url} target="_blank" rel="noreferrer" className="text-violet hover:underline">archive GPU ↗</a>
                {r.pagination_note && <span className="text-st-creuser">⚠ {r.pagination_note}</span>}
              </div>
            </div>
          ))}
          {d.avis && <div className="text-[10px] text-txt-dim">{d.avis}</div>}
        </div>
      )}
    </div>
  )
}
