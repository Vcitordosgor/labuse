import { useMutation, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { getCommunes, getResults, getStats, iaSearch, iaStatus } from '../../lib/api'
import type { Statut } from '../../lib/types'
import { EMPTY_FILTERS, useApp, type Filters } from '../../store/useApp'

const EXAMPLES = [
  'les chaudes de Saint-Pierre',
  'les chaudes avec vue mer de plus de 1000 m²',
  'à surveiller avec pollution et score > 70',
  'parcelles avec événement BODACC au Tampon',
  'SDP d’au moins 800 m² à creuser',
  'un terrain pour 3 immeubles R+3 étudiants avec parking',
]

/** Copilote — recherche en langage naturel. L'IA ne renvoie QUE des filtres validés par schéma
 *  (jamais un accès base, jamais un score) ; les chips existants font le reste. */
export function IAStub() {
  const [text, setText] = useState('')
  // R2 : cadrage conversationnel — la question en cours + les réponses choisies par chips
  const [cadrage, setCadrage] = useState<null | { texte: string; reformulation: string; questions: { id: string; texte: string; chips: { label: string; value?: string }[] }[] }>(null)
  const [reponses, setReponses] = useState<Record<string, { label: string; value?: string }>>({})
  const communesQ = useQuery({ queryKey: ['communes'], queryFn: getCommunes })
  const { setFilters, setView, setModule, setM22Prefill, setCommune, setVerdict, setFlyTo, setIaRestitution } = useApp()
  const status = useQuery({ queryKey: ['ia-status'], queryFn: iaStatus })
  const search = useMutation({ mutationFn: iaSearch })

  const apply = async (f: Record<string, unknown>) => {
    // la commune est un filtre de PÉRIMÈTRE : « les chaudes de Saint-Pierre » bascule le
    // sélecteur ; un SECTEUR du cadreur (communes multiples) passe le périmètre à l'île
    // avec le filtre communes. Une phrase sans commune ne touche pas au périmètre courant.
    const communes = (f.communes as string[]) ?? []
    if (communes.length > 0) setCommune(null)
    else if (typeof f.commune === 'string' && f.commune) setCommune(f.commune)
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
      communes,
    }
    setFilters(next)
    setVerdict(true)          // le copilote ALLUME le tri — c'est sa mise en scène
    setView('cartes')
    // vol de caméra vers le périmètre (bbox de la commune, union du secteur, ou île)
    const infos = communesQ.data ?? []
    const cible = communes.length ? communes : (typeof f.commune === 'string' && f.commune ? [f.commune] : [])
    const boxes = infos.filter((c) => cible.includes(c.commune)).map((c) => c.bbox)
    if (boxes.length) {
      const x1 = Math.min(...boxes.map((b) => b[0])), y1 = Math.min(...boxes.map((b) => b[1]))
      const x2 = Math.max(...boxes.map((b) => b[2])), y2 = Math.max(...boxes.map((b) => b[3]))
      setFlyTo({ center: [(x1 + x2) / 2, (y1 + y2) / 2], zoom: boxes.length > 1 ? 10.2 : 11.5 })
    } else {
      setFlyTo({ center: [55.53, -21.13], zoom: 9.7 })
    }
    // restitution : compteur + les 3 meilleures, cliquables
    try {
      const [st, top] = await Promise.all([getStats(next), getResults(next)])
      setIaRestitution({
        n: st.chaude + st.a_surveiller + st.a_creuser,
        phrase: 'parcelles correspondent — voici les 3 meilleures',
        top: top.slice(0, 3).map((t) => ({ idu: t.idu, commune: t.commune, q_score: t.q_score })),
      })
    } catch { /* restitution best-effort : les filtres sont déjà appliqués */ }
  }

  const run = (t: string, history?: { role: string; content: string }[]) => {
    setText(t)
    search.mutate({ text: t, history }, {
      onSuccess: (d) => {
        const dd = d as Record<string, unknown>
        if (dd.programme) {
          setM22Prefill(dd.programme as Record<string, unknown>)
          setModule('programme')          // → formulaire M22 pré-rempli, moteur déterministe
          return
        }
        if (dd.cadrage) {                 // R2 : le copilote CADRE avant d'exécuter
          setCadrage({ texte: t, ...(dd.cadrage as { reformulation: string; questions: never[] }) })
          setReponses({})
          return
        }
        if (d.filters) { setCadrage(null); apply(d.filters) }
      },
    })
  }

  // toutes les questions répondues → suivi automatique avec l'historique court
  const repondre = (qid: string, chip: { label: string; value?: string }) => {
    if (!cadrage) return
    const next = { ...reponses, [qid]: chip }
    setReponses(next)
    if (Object.keys(next).length === cadrage.questions.length) {
      const recap = cadrage.questions
        .map((q) => `${q.id} = ${next[q.id].label}${next[q.id].value ? ` (${next[q.id].value})` : ''}`)
        .join(' ; ')
      run(`Réponses de cadrage : ${recap}`, [
        { role: 'user', content: cadrage.texte },
        { role: 'assistant', content: JSON.stringify({ cadrage: { reformulation: cadrage.reformulation, questions: cadrage.questions } }) },
      ])
      setCadrage(null)
    }
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

        <div className="mt-3 flex flex-wrap gap-1.5">
          {EXAMPLES.map((e) => (
            <button key={e} onClick={() => run(e)}
              className="rounded-full border border-line-2 px-2.5 py-1 text-[11px] text-txt-mut hover:border-[#2E6B4F] hover:text-txt">
              {e}
            </button>
          ))}
        </div>

        {cadrage && (
          <div data-cadrage className="mt-4 rounded-xl border border-[#2E6B4F] bg-[#0F1A14] px-4 py-3">
            <p className="text-xs text-txt">{cadrage.reformulation}</p>
            {cadrage.questions.map((q) => (
              <div key={q.id} className="mt-3">
                <p className="text-[11px] font-medium text-txt-mut">{q.texte}</p>
                <div className="mt-1.5 flex flex-wrap gap-1.5">
                  {q.chips.map((c) => (
                    <button key={c.label} data-cadrage-chip onClick={() => repondre(q.id, c)}
                      className={`rounded-full border px-2.5 py-1 text-[11px] ${
                        reponses[q.id]?.label === c.label ? 'border-mint bg-[#12241a] text-mint' : 'border-line-2 text-txt hover:border-[#2E6B4F]'}`}>
                      {c.label}
                    </button>
                  ))}
                </div>
              </div>
            ))}
            <p className="mt-2 text-[9.5px] text-txt-dim">Répondez aux {cadrage.questions.length > 1 ? 'deux questions' : 'questions'} — la recherche part toute seule.</p>
          </div>
        )}
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
