import { useMutation, useQuery } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { deriveProjet, getReperes, iaEntretien, type EntretienQuestion, type EntretienRep, type FicheProjet, type RepereOption } from '../../lib/api'
import { useApplySearch } from '../../lib/useApplySearch'
import { useApp } from '../../store/useApp'

const TYPE_LABEL: Record<string, string> = {
  logements: 'Logements', etudiant: 'Logement étudiant', bureaux: 'Bureaux', autre: 'Projet',
}
const CONTRAINTE_LABEL: Record<string, string> = {
  eviter_ppr: 'hors zone à risque (PPR)', eviter_pollution: 'sol non pollué',
  eviter_abf: 'hors ABF', eviter_icpe: 'hors ICPE',
}

// Les 4 « cases » de la fiche que la jauge suit — l'utilisateur voit son projet prendre forme.
const SLOTS: { key: string; label: string; rempli: (f: FicheProjet) => string | null }[] = [
  { key: 'type', label: 'Programme', rempli: (f) => f.type_programme ? TYPE_LABEL[f.type_programme] : null },
  {
    key: 'ampleur', label: 'Ampleur', rempli: (f) => {
      const a = f.ampleur ?? {}
      return a.logements ? `${a.logements} logements` : a.sdp_m2 ? `${a.sdp_m2} m² SDP` : null
    },
  },
  {
    key: 'perimetre', label: 'Où', rempli: (f) => {
      const p = f.perimetre
      if (!p) return null
      if (p.mode === 'ile') return "toute l'île"
      if (p.mode === 'secteur') return `secteur ${p.secteur}`
      const cs = p.communes ?? []
      return cs.length === 1 ? cs[0] : cs.length ? `${cs.length} communes` : null
    },
  },
  {
    key: 'contraintes', label: 'Contraintes', rempli: (f) =>
      f.contraintes?.length ? f.contraintes.map((c) => CONTRAINTE_LABEL[c] ?? c).join(' · ') : null,
  },
]

/** Repère sourcé sous un chip de secteur : « N opp · ~P €/m² » (+ pastille carencée SRU). */
function RepereBadge({ opt }: { opt: RepereOption | undefined }) {
  if (!opt) return null
  return (
    <span data-repere className="mt-0.5 block text-[9.5px] leading-tight text-txt-dim">
      {opt.nb_opportunites.toLocaleString('fr-FR')} opp.
      {opt.dvf_median_eur_m2 ? ` · ~${opt.dvf_median_eur_m2.toLocaleString('fr-FR')} €/m²` : ''}
      {opt.communes_carencees.length ? <span className="text-st-surveiller"> · SRU carencée</span> : null}
    </span>
  )
}

/** L'ENTRETIEN de cadrage projet — l'IA mène, la fiche se construit à l'écran, chaque question
 *  à chips (repères sourcés sous le secteur), skippable. Fin : « Lancer la recherche ». */
export function ProjetEntretien({ initial, onClose }: { initial: string; onClose: () => void }) {
  const apply = useApplySearch()
  const { setView } = useApp()
  const [fiche, setFiche] = useState<FicheProjet>({})
  const [reformulation, setReformulation] = useState('')
  const [questions, setQuestions] = useState<EntretienQuestion[]>([])
  const [nom, setNom] = useState('')
  const [pret, setPret] = useState(false)
  const [fallback, setFallback] = useState<string | null>(null)
  const [neutralise, setNeutralise] = useState(false)
  const history = useRef<{ role: string; content: string }[]>([])
  const started = useRef(false)

  const send = useMutation({
    mutationFn: (text: string) => iaEntretien({ text, fiche, history: history.current.slice(-6) }),
    onSuccess: (d: EntretienRep, text) => {
      if (d.fallback) { setFallback(d.message ?? 'Entretien indisponible.'); return }
      history.current.push({ role: 'user', content: text })
      history.current.push({ role: 'assistant', content: JSON.stringify({ fiche: d.fiche, questions: d.questions }) })
      setFiche(d.fiche ?? {})
      setReformulation(d.reformulation ?? '')
      setQuestions(d.questions ?? [])
      setNom(d.nom ?? '')
      setPret(!!d.pret)
      setNeutralise(!!d.doctrine_neutralise)
    },
  })

  // premier tour : la demande initiale amorce l'entretien
  useEffect(() => {
    if (started.current) return
    started.current = true
    send.mutate(initial)
  }, [initial]) // eslint-disable-line react-hooks/exhaustive-deps

  const active = questions[0]
  const reperesQ = useQuery({
    queryKey: ['reperes', active?.dimension],
    queryFn: () => getReperes(active!.dimension!),
    enabled: !!active?.dimension,
  })
  const repere = (label: string): RepereOption | undefined =>
    (reperesQ.data?.options ?? []).find((o) => o.key === label || o.label === label)

  const lancer = useMutation({
    mutationFn: () => deriveProjet({ fiche, nom }),
    onSuccess: async (d) => {
      await apply(d.filtres, `parcelles pour « ${d.nom} » — voici les 3 meilleures`)
      setView('cartes')
      // transmet la fiche+dérivation à la restitution (bouton « Enregistrer ce projet », V3)
      useApp.getState().setProjetBrouillon({ fiche: fiche as Record<string, unknown>, nom: d.nom, filtres: d.filtres, sdp_besoin_m2: d.sdp_besoin_m2 })
    },
  })

  const remplis = SLOTS.filter((s) => s.rempli(fiche)).length
  const loading = send.isPending

  if (fallback) {
    return (
      <div className="flex min-w-0 flex-1 items-start justify-center overflow-y-auto">
        <div className="w-full max-w-xl px-8 py-16 text-center">
          <p data-entretien-fallback className="text-sm text-txt-mut">{fallback}</p>
          <button onClick={onClose} className="mt-4 text-xs font-medium text-mint hover:underline">
            → Recherche directe
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-w-0 flex-1 items-start justify-center overflow-y-auto" data-entretien>
      <div className="w-full max-w-xl px-8 py-10">
        <div className="flex items-center justify-between">
          <h2 className="font-display text-lg font-bold text-txt-hi">Votre projet</h2>
          <button onClick={onClose} className="text-xs text-txt-dim hover:text-txt-mut" title="Quitter l'entretien">
            Fermer
          </button>
        </div>

        {/* jauge : la fiche prend forme */}
        <div className="mt-3 flex gap-1" data-entretien-jauge data-remplis={remplis}>
          {SLOTS.map((s) => (
            <div key={s.key} className={`h-1 flex-1 rounded-full ${s.rempli(fiche) ? 'bg-mint' : 'bg-line-2'}`} />
          ))}
        </div>

        {/* reformulation */}
        {reformulation && (
          <p data-entretien-reformulation className="mt-4 text-sm leading-relaxed text-txt">
            {reformulation}
          </p>
        )}
        {neutralise && (
          <p className="mt-1 text-[11px] text-txt-dim">
            (Je reste neutre : les repères chiffrés viennent de la base, pas d'un avis.)
          </p>
        )}

        {/* la FICHE qui se construit à l'écran */}
        <div data-entretien-fiche className="mt-4 rounded-xl border border-line-2 bg-surface-2 p-4">
          <p className="mb-2 font-mono text-[10px] tracking-widest text-txt-dim">FICHE PROJET</p>
          <dl className="space-y-1.5">
            {SLOTS.map((s) => {
              const v = s.rempli(fiche)
              return (
                <div key={s.key} className="flex items-baseline gap-3 text-xs">
                  <dt className="w-24 shrink-0 text-txt-dim">{s.label}</dt>
                  <dd className={v ? 'text-txt-hi' : 'text-txt-dim/50'}>{v ?? '—'}</dd>
                </div>
              )
            })}
            {fiche.budget_foncier_eur ? (
              <div className="flex items-baseline gap-3 text-xs">
                <dt className="w-24 shrink-0 text-txt-dim">Budget</dt>
                <dd className="text-txt-hi">{(fiche.budget_foncier_eur / 1000).toLocaleString('fr-FR')} k€</dd>
              </div>
            ) : null}
          </dl>
        </div>

        {/* question active (chips + skip) */}
        {loading && <p className="mt-5 text-xs text-txt-dim">Le copilote réfléchit…</p>}
        {!loading && active && (
          <div className="mt-5" data-entretien-question data-qid={active.id}>
            <p className="text-sm font-medium text-txt-hi">{active.texte}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {active.chips.map((c, i) => (
                <button
                  key={i}
                  data-entretien-chip
                  onClick={() => send.mutate(c.label)}
                  className="rounded-lg border border-line-2 bg-surface-3 px-3 py-1.5 text-left text-xs text-txt hover:border-mint/50 hover:text-txt-hi"
                >
                  {c.label}
                  {active.dimension && <RepereBadge opt={repere(c.label)} />}
                </button>
              ))}
              {/* SKIP : un défaut honnête, affiché */}
              <button
                data-entretien-skip
                onClick={() => send.mutate('je ne sais pas encore, passe cette question')}
                className="rounded-lg border border-dashed border-line-2 px-3 py-1.5 text-xs text-txt-mut hover:text-txt"
                title={active.defaut ?? 'Passer'}
              >
                Je ne sais pas encore
                {active.defaut && <span className="ml-1 text-[10px] text-txt-dim">{active.defaut}</span>}
              </button>
            </div>
          </div>
        )}

        {/* lancer la recherche (dès que l'essentiel est cadré) */}
        {!loading && pret && (
          <button
            data-entretien-lancer
            onClick={() => lancer.mutate()}
            disabled={lancer.isPending}
            className="mt-6 w-full rounded-xl bg-mint py-3 text-sm font-semibold text-[#06130C] hover:brightness-110 disabled:opacity-50"
          >
            {lancer.isPending ? 'Recherche…' : `Lancer la recherche${questions.length ? ' maintenant' : ''}`}
          </button>
        )}
      </div>
    </div>
  )
}
