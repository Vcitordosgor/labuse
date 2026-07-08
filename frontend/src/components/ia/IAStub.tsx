import { useMutation, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { iaSearch, iaStatus } from '../../lib/api'
import { useApplySearch } from '../../lib/useApplySearch'
import { useApp } from '../../store/useApp'
import { ProjetEntretien } from '../projets/ProjetEntretien'

const EXAMPLES = [
  'les chaudes de Saint-Pierre',
  'les chaudes avec vue mer de plus de 1000 m²',
  'à surveiller avec pollution et score > 70',
  'parcelles avec événement BODACC au Tampon',
  'SDP d’au moins 800 m² à creuser',
  'un terrain pour 3 immeubles R+3 étudiants avec parking',
]

/** Copilote — recherche NL (filtres validés par schéma) OU entretien de cadrage PROJET.
 *  L'IA ne calcule ni ne modifie aucun score, n'accède jamais à la base. */
export function IAStub() {
  const [text, setText] = useState('')
  // copilote-projet : l'entretien s'ouvre sur intention projet (auto) ou bouton « Décrire mon projet »
  const [entretien, setEntretien] = useState<string | null>(null)
  const { setModule, setM22Prefill } = useApp()
  const status = useQuery({ queryKey: ['ia-status'], queryFn: iaStatus })
  const search = useMutation({ mutationFn: iaSearch })
  const apply = useApplySearch()   // chorégraphie partagée (périmètre → filtres → verdict → vol → restitution)

  const run = (t: string) => {
    setText(t)
    search.mutate({ text: t }, {
      onSuccess: (d) => {
        const dd = d as Record<string, unknown>
        if (dd.projet_intent) {          // demande de PROJET → on ouvre l'entretien de cadrage
          setEntretien(t)
          return
        }
        if (dd.programme) {
          setM22Prefill(dd.programme as Record<string, unknown>)
          setModule('programme')          // → formulaire M22 pré-rempli, moteur déterministe
          return
        }
        if (d.filters) apply(d.filters)
      },
    })
  }

  if (entretien !== null) {
    return <ProjetEntretien initial={entretien} onClose={() => setEntretien(null)} />
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
        {(status.data?.provider === 'stub' || status.data?.raison) && (
          <div className="mt-3 rounded-lg border border-st-creuser/40 bg-[#211a10] px-3 py-2 text-[11px] leading-relaxed text-st-creuser">
            <b>Mode dégradé : stub local.</b>{' '}
            {/* C1 : un DIAGNOSTIC, pas une devinette — la cause exacte vient du serveur */}
            Cause : {status.data?.raison ?? 'indéterminée'}.
            {status.data?.provider === 'stub' && (
              <> Pour activer Anthropic : poser
                <code className="mx-1 rounded bg-surface-3 px-1 font-mono text-[10px]">ANTHROPIC_API_KEY=…</code>
                dans le <code className="rounded bg-surface-3 px-1 font-mono text-[10px]">.env</code> à la racine
                (chargé automatiquement quel que soit le lanceur) puis relancer le serveur.</>
            )}
          </div>
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

        {/* copilote-projet — l'autre voie : décrire une OPÉRATION (entretien de cadrage) */}
        <button
          data-decrire-projet
          onClick={() => setEntretien(text.trim() || 'je veux monter une opération immobilière')}
          className="mt-3 flex w-full items-center justify-center gap-2 rounded-xl border border-[#3A4F8F]/50 bg-[#161a2e] py-2.5 text-xs font-medium text-[#B497F0] hover:border-[#B497F0]/60"
        >
          <svg viewBox="0 0 20 20" className="h-4 w-4"><path d="M10 3.5 L11.6 8.4 L16.5 10 L11.6 11.6 L10 16.5 L8.4 11.6 L3.5 10 L8.4 8.4 Z" fill="currentColor" /></svg>
          Décrire mon projet — le copilote vous cadre en 4 questions
        </button>

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
