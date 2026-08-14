import { useMutation, useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { pluAnnuaireSearch, pluAnnuaireCommunes, type PluExtrait } from '../../lib/api'
import { useApp } from '../../store/useApp'

// M51 / M82 (refonte BIBLIOTHÈQUE) — ANNUAIRE PLU : les communes sont VISIBLES d'emblée (servables
// cliquables, non-servables grisées AVEC leur raison — jamais masquées) ; on entre dans une commune, on
// cherche dans SON règlement ; la recherche île-entière reste possible. Le résultat est le VERBATIM
// opposable sourcé (commune, article, PAGE PDF, lien GPU) — jamais un résumé. Tout vertical, aucun
// scroll horizontal. Source Géoportail de l'Urbanisme.
const RAISON: Record<string, string> = {
  rnu: 'RNU — pas de règlement communal',
  revision: 'révision en cours — vérifier en mairie',
  non_ingere: 'non ingéré',
}

export function PluAnnuaire() {
  const [q, setQ] = useState('')
  const [insee, setInsee] = useState('')                     // '' = bibliothèque / île ; sinon une commune
  const [zone, setZone] = useState('')                       // filtre zone (lien contextuel fiche → O13)
  const pluPrefill = useApp((s) => s.pluPrefill)
  const setPluPrefill = useApp((s) => s.setPluPrefill)
  const communes = useQuery({ queryKey: ['plu-communes'], queryFn: pluAnnuaireCommunes })
  const m = useMutation({ mutationFn: () => pluAnnuaireSearch(q.trim(), insee || undefined, zone || undefined) })
  const d = m.data
  const run = () => { if (q.trim().length >= 2) m.mutate() }

  // Ouvert depuis une fiche : la commune + la zone servie sont pré-remplies (verbatim de CETTE zone).
  useEffect(() => {
    if (pluPrefill) {
      setInsee(pluPrefill.insee)
      setZone(pluPrefill.zone ?? '')
      setPluPrefill(null)
    }
  }, [pluPrefill, setPluPrefill])

  const info = (code: string) => communes.data?.communes.find((c) => c.insee === code)
  const nomInsee = (code: string | null) => (code ? info(code)?.commune : null)
  const entrer = (code: string) => { setInsee(code); setQ(''); m.reset() }
  const bibliotheque = () => { setInsee(''); setZone(''); setQ(''); m.reset() }

  return (
    <div data-plu-annuaire className="flex min-h-0 flex-1 flex-col gap-2 overflow-x-hidden overflow-y-auto">
      {/* fil d'Ariane — dans une commune */}
      {insee && (
        <div className="flex flex-wrap items-center gap-1.5 text-[11px] text-txt-mut">
          <button data-plu-retour onClick={bibliotheque} className="text-mint hover:underline">‹ Bibliothèque</button>
          <span>·</span><b className="text-txt">{nomInsee(insee) ?? insee}</b>
          {info(insee)?.statut === 'servable'
            ? <span className="font-mono text-[9px] text-mint/70">règlement à jour</span>
            : <span className="font-mono text-[9px] text-cp-amber">{RAISON[info(insee)?.statut ?? ''] ?? ''}</span>}
        </div>
      )}

      {/* barre de recherche — verticale, aucun débordement (input flex-1 min-w-0, bouton shrink-0) */}
      <div className="flex flex-col gap-2 rounded-lg border border-line-2 bg-surface-2 p-3">
        <p className="text-[10.5px] leading-snug text-txt-mut">
          {insee ? <>Cherchez dans le règlement de <b className="text-txt">{nomInsee(insee)}</b> — verbatim
            sourcé (article, page, lien), jamais un résumé.</>
            : <>Cherchez dans le règlement écrit opposable (Géoportail de l’Urbanisme) — verbatim sourcé,
              jamais un résumé. Ouvrez une commune ci-dessous, ou cherchez sur toute l’île.</>}
        </p>
        <div className="flex gap-2">
          <input data-plu-q value={q} onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') run() }}
            placeholder={insee ? `dans ${nomInsee(insee)} — ex. hauteur de clôture` : 'ex. hauteur de clôture, stationnement, emprise au sol'}
            className="min-w-0 flex-1 rounded-md border border-line-2 bg-surface-3 px-2.5 py-1.5 text-[12px] text-txt focus:border-mint focus:outline-none" />
          <button onClick={run} disabled={q.trim().length < 2 || m.isPending}
            className="shrink-0 whitespace-nowrap rounded-md border border-mint/50 bg-mint/15 px-3.5 py-1.5 text-[12px] font-medium text-mint disabled:opacity-40">
            {m.isPending ? '…' : 'Chercher'}
          </button>
        </div>
        {zone && (
          <div className="flex items-center gap-1.5 text-[10.5px] text-txt-mut">
            <span>Filtré sur la <span className="font-mono text-mint">zone {zone}</span> (depuis la fiche)</span>
            <button onClick={() => setZone('')} className="rounded bg-surface-3 px-1 text-txt-dim hover:text-txt">✕ retirer</button>
          </div>
        )}
      </div>

      {/* BIBLIOTHÈQUE — les communes visibles d'emblée (aucune ouverte, aucun résultat encore) */}
      {!insee && !d && communes.data && (
        <div data-plu-biblio>
          <p className="mb-1.5 px-0.5 font-mono text-[9px] uppercase tracking-[.14em] text-txt-dim">
            {communes.data.servables} règlements interrogeables · les {communes.data.n_communes - communes.data.servables} autres
            (RNU, révision) sont dits, jamais masqués
          </p>
          <div className="grid grid-cols-2 gap-1.5">
            {communes.data.communes.map((c) => {
              const servable = c.statut === 'servable'
              return (
                <button key={c.insee} data-plu-commune={c.insee} disabled={!servable}
                  onClick={servable ? () => entrer(c.insee) : undefined}
                  className={`flex items-center justify-between gap-2 rounded-lg border px-2.5 py-2 text-left ${
                    servable ? 'border-line bg-surface-2 hover:border-mint/40 cursor-pointer'
                             : 'border-line/60 bg-surface-1 cursor-default'}`}>
                  <span className={`truncate text-[11.5px] ${servable ? 'text-txt' : 'text-txt-dim'}`}>{c.commune}</span>
                  {servable
                    ? <span className="shrink-0 font-mono text-[8.5px] text-mint/70">à jour</span>
                    : <span className="shrink-0 whitespace-nowrap font-mono text-[8px] text-cp-amber" title={c.message ?? ''}>
                        {c.statut === 'rnu' ? 'RNU' : c.statut === 'revision' ? 'révision' : 'non ingéré'}</span>}
                </button>
              )
            })}
          </div>
        </div>
      )}

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
                <span className="font-medium text-mint">{r.article_ref}</span>
                {r.zone && <span className="text-txt-mut">zone {r.zone}</span>}
                <span className="text-txt-mut">{r.commune}</span>
                <span className="text-txt-dim">p. PDF {r.page_pdf}</span>
                {r.doute && (
                  <span className="rounded bg-st-ecartee/15 px-1 text-[9.5px] text-st-ecartee">
                    doute — vérifier au PDF
                  </span>
                )}
              </div>
              <pre className="mt-1 whitespace-pre-wrap break-words font-sans text-[11px] leading-snug text-txt">{r.texte_verbatim}</pre>
              <div className="mt-1 flex flex-wrap gap-x-2 text-[10px] text-txt-dim">
                <span>{r.document}{r.millesime ? ` · ${r.millesime}` : ''}</span>
                <a href={r.source_url} target="_blank" rel="noreferrer" className="text-mint hover:underline">archive GPU ↗</a>
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
