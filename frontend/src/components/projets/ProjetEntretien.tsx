import { useMutation, useQuery } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { createProjet, getReperes, iaEntretien, type EntretienQuestion, type EntretienRep, type FicheProjet, type RepereOption } from '../../lib/api'
import { fmtEurCompact, fmtInt } from '../../lib/format'
import { useApp } from '../../store/useApp'
import { Loading } from '../Loading'

const TYPE_LABEL: Record<string, string> = {
  logements: 'Logements', etudiant: 'Logement étudiant', bureaux: 'Bureaux', autre: 'Projet',
}
const CONTRAINTE_LABEL: Record<string, string> = {
  eviter_ppr: 'hors zone à risque (PPR)', eviter_pollution: 'sol non pollué',
  eviter_abf: 'hors ABF', eviter_icpe: 'hors ICPE',
}

// Les 5 « cases » de la fiche que la jauge suit — l'utilisateur voit son projet prendre forme.
// F1 (M12) : Budget est une case à part entière (5e info collectée) — au même titre que les autres.
const SLOTS: { key: string; label: string; rempli: (f: FicheProjet) => string | null }[] = [
  { key: 'type', label: 'Programme', rempli: (f) => f.type_programme ? TYPE_LABEL[f.type_programme] : null },
  {
    key: 'ampleur', label: 'Ampleur', rempli: (f) => {
      const a = f.ampleur ?? {}
      const base = a.logements ? `${a.logements} logements` : a.sdp_m2 ? `${a.sdp_m2} m² SDP` : null
      // le gabarit (R+n) affine l'ampleur — affiché s'il est renseigné
      if (a.niveaux) return base ? `${base} · R+${a.niveaux}` : `R+${a.niveaux}`
      return base
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
  {
    key: 'budget', label: 'Budget', rempli: (f) => f.budget_foncier_eur ? fmtEurCompact(f.budget_foncier_eur) : null,
  },
]

/** Repère sourcé sous un chip de secteur : « N opp · ~P €/m² » (+ pastille carencée SRU). */
function RepereBadge({ opt }: { opt: RepereOption | undefined }) {
  if (!opt) return null
  return (
    <span data-repere className="mt-0.5 block text-[11px] leading-tight text-txt-dim">
      {fmtInt(opt.nb_opportunites)} opp.
      {opt.dvf_median_eur_m2 ? ` · ~${fmtInt(opt.dvf_median_eur_m2)} €/m²` : ''}
      {opt.communes_carencees.length ? <span className="text-st-surveiller"> · SRU carencée</span> : null}
    </span>
  )
}

/** L'ENTRETIEN de cadrage projet — l'IA mène, la fiche se construit à l'écran, chaque question
 *  à chips (repères sourcés sous le secteur), skippable. Fin : « Lancer la recherche ». */
export function ProjetEntretien({ initial, onClose }: { initial: string; onClose: () => void }) {
  const { setOpenProjet } = useApp()
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

  // F5 (M12) — « Lancer la recherche » PERSISTE le projet et ouvre DIRECTEMENT sa vue 3 colonnes
  // (À trier / Retenues / Écartées), pas la carte globale. Le kanban (re)propose les parcelles du
  // jour à l'ouverture (proposerProjet idempotent) → elles atterrissent dans « À trier ». Dédup
  // douce serveur : un projet identique est repris (jamais de doublon).
  const lancer = useMutation({
    mutationFn: () => createProjet({ fiche, nom: nom || undefined }),
    onSuccess: ({ projet }) => {
      setOpenProjet({ id: projet.id, nom: projet.nom })   // → vue kanban 3 colonnes (nav exclusive)
      onClose()   // l'entretien est terminé : ré-ouvrir le copilote = une recherche fraîche
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
          <button onClick={onClose} className="min-h-7 text-xs text-txt-dim transition-colors duration-quick hover:text-txt-mut" title="Quitter l'entretien">
            Fermer
          </button>
        </div>

        {/* jauge : la fiche prend forme. F1 (M12) — PROGRESSION left→right : les `remplis`
            PREMIERS segments s'allument, dans l'ordre (jamais un segment vert isolé au milieu
            parce que l'IA a rempli « Où » avant « Programme »). 5 segments = 5 infos collectées. */}
        <div className="mt-3 flex gap-1" data-entretien-jauge data-remplis={remplis}>
          {SLOTS.map((s, i) => (
            <div key={s.key} className={`h-1 flex-1 rounded-full transition-colors duration-soft ${i < remplis ? 'bg-mint' : 'bg-line-2'}`} />
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
        <div data-entretien-fiche className="card-elev mt-4 p-4">
          <p className="label-caps mb-2">Fiche projet</p>
          <dl className="space-y-1.5">
            {SLOTS.map((s) => {
              const v = s.rempli(fiche)
              return (
                <div key={s.key} className="flex items-baseline gap-3 text-xs">
                  <dt className="w-24 shrink-0 text-txt-dim">{s.label}</dt>
                  <dd className={`${v ? 'text-txt-hi' : 'text-txt-dim/50'}${s.key === 'budget' ? ' tnum' : ''}`}>{v ?? '—'}</dd>
                </div>
              )
            })}
          </dl>
        </div>

        {/* question active (chips + skip) */}
        {loading && <div className="mt-5"><Loading big label="LABUSE réfléchit" /></div>}
        {!loading && active && (
          <div className="mt-5" data-entretien-question data-qid={active.id}>
            <p className="text-sm font-medium text-txt-hi">{active.texte}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {active.chips.map((c, i) => (
                <button
                  key={i}
                  data-entretien-chip
                  onClick={() => send.mutate(c.label)}
                  className="min-h-7 rounded-lg border border-line-2 bg-surface-3 px-3 py-1.5 text-left text-xs text-txt transition-colors duration-quick hover:border-mint/50 hover:text-txt-hi"
                >
                  {c.label}
                  {active.dimension && <RepereBadge opt={repere(c.label)} />}
                </button>
              ))}
              {/* SKIP : un défaut honnête, affiché */}
              <button
                data-entretien-skip
                onClick={() => send.mutate('je ne sais pas encore, passe cette question')}
                className="min-h-7 rounded-lg border border-dashed border-line-2 px-3 py-1.5 text-xs text-txt-mut transition-colors duration-quick hover:text-txt"
                title={active.defaut ?? 'Passer'}
              >
                Je ne sais pas encore
                {active.defaut && <span className="ml-1 text-[11px] text-txt-dim">{active.defaut}</span>}
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
            className="mt-6 w-full rounded-xl bg-mint py-3 text-sm font-semibold text-mint-ink transition-[filter] duration-quick hover:brightness-110 disabled:opacity-50"
          >
            {lancer.isPending ? 'Recherche…' : `Lancer la recherche${questions.length ? ' maintenant' : ''}`}
          </button>
        )}
      </div>
    </div>
  )
}
