import { useMutation, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { iaSearch, iaStatus } from '../../lib/api'
import type { Statut } from '../../lib/types'
import { EMPTY_FILTERS, useApp, type Filters } from '../../store/useApp'

const EXAMPLES = [
  'les chaudes avec vue mer de plus de 1000 m²',
  'à surveiller avec pollution et score > 70',
  'parcelles avec événement BODACC',
  'SDP d’au moins 800 m² à creuser',
]

/** Copilote — recherche en langage naturel. L'IA ne renvoie QUE des filtres validés par schéma
 *  (jamais un accès base, jamais un score) ; les chips existants font le reste. */
export function IAStub() {
  const [text, setText] = useState('')
  const { setFilters, setView } = useApp()
  const status = useQuery({ queryKey: ['ia-status'], queryFn: iaStatus })
  const search = useMutation({ mutationFn: iaSearch })

  const apply = (f: Record<string, unknown>) => {
    const next: Filters = {
      ...EMPTY_FILTERS,
      statuts: (f.statuts as Statut[]) ?? [],
      scoreMin: (f.scoreMin as number | null) ?? null,
      surfaceMin: (f.surfaceMin as number | null) ?? null,
      surfaceMax: (f.surfaceMax as number | null) ?? null,
      sdpMin: (f.sdpMin as number | null) ?? null,
      evenement: !!f.evenement,
      vueMer: !!f.vueMer,
      flags: (f.flags as string[]) ?? [],
    }
    setFilters(next)
    setView('cartes')
  }

  const run = (t: string) => {
    setText(t)
    search.mutate(t, { onSuccess: (d) => { if (d.filters) apply(d.filters) } })
  }

  return (
    <div className="flex min-w-0 flex-1 items-start justify-center overflow-y-auto">
      <div className="w-full max-w-xl px-8 py-12">
        <svg viewBox="0 0 20 20" className="h-8 w-8 text-mint">
          <path d="M10 3.5 L11.6 8.4 L16.5 10 L11.6 11.6 L10 16.5 L8.4 11.6 L3.5 10 L8.4 8.4 Z"
            fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
        </svg>
        <h2 className="mt-3 font-display text-lg font-bold text-txt-hi">Copilote</h2>
        <p className="mt-1 text-xs text-txt-mut">
          Décrivez ce que vous cherchez — la demande devient des <b>filtres</b> (validés par schéma),
          appliqués à la carte et à la liste.
        </p>
        {status.data?.provider === 'stub' && (
          <p className="mt-2 inline-block rounded-full border border-line-2 bg-surface-3 px-2.5 py-0.5 text-[10px] text-txt-dim"
            title="Ajoutez ANTHROPIC_API_KEY dans .env pour activer le provider Anthropic">
            mode stub local — clé IA absente
          </p>
        )}

        <div className="mt-5 flex gap-2">
          <input
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && text.trim() && run(text)}
            placeholder="ex. les chaudes avec vue mer de plus de 1 000 m²"
            className="min-w-0 flex-1 rounded-xl border border-line-2 bg-surface-3 px-4 py-2.5 text-sm text-txt placeholder:text-txt-dim focus:border-mint focus:outline-none"
          />
          <button onClick={() => text.trim() && run(text)} disabled={search.isPending}
            className="rounded-xl bg-mint px-4 text-sm font-medium text-mint-ink disabled:opacity-50">
            {search.isPending ? '…' : 'Chercher'}
          </button>
        </div>

        <div className="mt-3 flex flex-wrap gap-1.5">
          {EXAMPLES.map((e) => (
            <button key={e} onClick={() => run(e)}
              className="rounded-full border border-line-2 px-2.5 py-1 text-[11px] text-txt-mut hover:border-[#2E6B4F] hover:text-txt">
              {e}
            </button>
          ))}
        </div>

        {search.data?.out_of_scope && (
          <div className="mt-4 rounded-lg border border-line-2 bg-surface-2 px-4 py-3 text-xs text-txt-mut">
            {search.data.out_of_scope}
          </div>
        )}
        {search.data?.explanation && (
          <div className="mt-4 rounded-lg border border-[#2E6B4F] bg-[#0F1A14] px-4 py-3 text-xs text-txt">
            ✓ {search.data.explanation}{' '}
            <span className="text-txt-dim">— appliqué sur la carte{search.data.stub ? ' (stub)' : ''}.</span>
          </div>
        )}
        {search.isError && (
          <div className="mt-4 rounded-lg border border-[#5a2420] bg-[#2a1210] px-4 py-3 text-xs text-st-ecartee">
            Erreur réseau — réessayez (serveur à relancer ?).
          </div>
        )}

        <p className="mt-8 text-[10.5px] leading-relaxed text-txt-dim">
          Doctrine : l'IA ne calcule ni ne modifie aucun score, et n'accède jamais à la base — elle
          traduit votre demande en filtres, le moteur déterministe fait le reste. Chaque appel est
          journalisé (modèle, tokens, coût).
        </p>
      </div>
    </div>
  )
}
