import { useMutation, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { iaSearch, iaStatus } from '../../lib/api'
import { useApplySearch } from '../../lib/useApplySearch'
import { useApp } from '../../store/useApp'
import { ProjetEntretien } from '../projets/ProjetEntretien'

// B5 (mandat calculette) — palette d'exemples VARIÉE : statut, secteur, commune, surface, SDP,
// score, événement, flags, vue mer, combinaisons — donne à voir l'étendue du copilote.
const EXAMPLES = [
  'les chaudes de Saint-Pierre',
  'vue mer de plus de 1 000 m²',
  'à surveiller avec pollution et score > 70',
  'SDP d’au moins 800 m² à creuser',
  'à creuser dans l’Ouest',
  'grandes parcelles avec événement BODACC',
  'hors zone à risque, plus de 2 000 m²',
  'monument historique à proximité au Tampon',
]

const VIOLET = '#B497F0'

/** Copilote — DEUX PORTES à égalité (P1, revue Vic n°3) : la recherche simple (chemin rapide,
 *  menthe) et le montage de projet (chemin accompagné, violet). L'IA est LE produit — elle est
 *  mise en scène, pas noyée dans un champ + un bouton perdu dessous.
 *  Doctrine : l'IA ne calcule ni ne modifie aucun score, n'accède jamais à la base. */
export function IAStub() {
  const [text, setText] = useState('')
  // copilote-projet : l'entretien s'ouvre sur intention projet (auto) ou porte « Montage de projet »
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

  const degrade = status.data?.provider === 'stub' || status.data?.raison

  return (
    <div className="flex min-w-0 flex-1 items-start justify-center overflow-y-auto">
      <div className="w-full max-w-3xl px-8 py-12">
        <div className="flex items-center gap-2.5">
          <svg viewBox="0 0 20 20" className="h-7 w-7 text-mint">
            <path d="M10 3.5 L11.6 8.4 L16.5 10 L11.6 11.6 L10 16.5 L8.4 11.6 L3.5 10 L8.4 8.4 Z"
              fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
          </svg>
          <div>
            <h2 className="font-display text-lg font-bold text-txt-hi">Copilote</h2>
            <p className="text-xs text-txt-mut">Deux façons de trouver votre foncier — choisissez la vôtre.</p>
          </div>
        </div>

        {degrade && (
          <div className="mt-4 rounded-lg border border-st-creuser/40 bg-[#211a10] px-3 py-2 text-[11px] leading-relaxed text-st-creuser">
            <b>Mode dégradé : stub local.</b>{' '}
            {/* C1 : un DIAGNOSTIC, pas une devinette — la cause exacte vient du serveur */}
            Cause : {status.data?.raison ?? 'indéterminée'}.
            {status.data?.provider === 'stub' && (
              <> Pour activer Anthropic : poser
                <code className="mx-1 rounded bg-surface-3 px-1 font-mono text-[10px]">ANTHROPIC_API_KEY=…</code>
                dans le <code className="rounded bg-surface-3 px-1 font-mono text-[10px]">.env</code> à la racine puis relancer le serveur.
                <br />L'entretien de montage a besoin du copilote — en attendant, la recherche simple fonctionne.</>
            )}
          </div>
        )}

        {/* LES DEUX PORTES — à égalité, désirables (cartes, pas un champ + un bouton) */}
        <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2">
          {/* PORTE 1 — Recherche simple (menthe · chemin rapide) */}
          <section data-porte-recherche className="flex flex-col rounded-2xl border border-[#2E6B4F]/60 bg-[#0F1A14] p-5">
            <div className="flex items-center gap-2">
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-mint/15 text-mint">
                <svg viewBox="0 0 20 20" className="h-4 w-4">
                  <circle cx="9" cy="9" r="5.5" fill="none" stroke="currentColor" strokeWidth="1.6" />
                  <line x1="13" y1="13" x2="17" y2="17" stroke="currentColor" strokeWidth="1.6" />
                </svg>
              </span>
              <h3 className="font-display text-sm font-bold text-txt-hi">Recherche simple</h3>
            </div>
            <p className="mt-2 text-xs leading-relaxed text-txt-mut">
              Dites en une phrase ce que vous cherchez — LABUSE en fait des <b className="text-txt">filtres</b> (validés par schéma), appliqués à la carte et à la liste. Le chemin rapide.
            </p>
            <div className="mt-4 flex gap-2">
              <input
                value={text}
                onChange={(e) => setText(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && text.trim() && run(text)}
                placeholder="ex. les chaudes avec vue mer de plus de 1 000 m²"
                className="min-w-0 flex-1 rounded-xl border border-line-2 bg-surface-3 px-3.5 py-2.5 text-sm text-txt placeholder:text-txt-dim focus:border-mint focus:outline-none"
              />
              <button onClick={() => text.trim() && run(text)} disabled={search.isPending}
                className="shrink-0 rounded-xl bg-mint px-4 text-sm font-semibold text-mint-ink hover:brightness-110 disabled:opacity-50">
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
          </section>

          {/* PORTE 2 — Montage de projet (violet · chemin accompagné) */}
          <section data-porte-projet className="flex flex-col rounded-2xl border p-5"
            style={{ borderColor: '#4a3d6b', background: '#161022' }}>
            <div className="flex items-center gap-2">
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg" style={{ background: 'rgba(180,151,240,0.15)', color: VIOLET }}>
                <svg viewBox="0 0 20 20" className="h-4 w-4">
                  <path d="M4 16 V7 L10 3.5 L16 7 V16 Z" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
                  <path d="M8 16 V11 H12 V16" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
                </svg>
              </span>
              <h3 className="font-display text-sm font-bold text-txt-hi">Montage de projet</h3>
            </div>
            <p className="mt-2 text-xs leading-relaxed text-txt-mut">
              Le copilote vous aide à <b style={{ color: VIOLET }}>cadrer votre opération</b> : programme, ampleur, gabarit, périmètre, contraintes. Le chemin accompagné.
            </p>
            <ol className="mt-4 space-y-2">
              {[
                'Il vous pose les bonnes questions (chacune facultative)',
                'Votre fiche projet se remplit sous vos yeux',
                'Il vous montre les parcelles qui portent votre projet',
              ].map((t, i) => (
                <li key={i} className="flex items-start gap-2.5 text-xs text-txt-mut">
                  <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full font-mono text-[10px] font-bold"
                    style={{ background: 'rgba(180,151,240,0.15)', color: VIOLET }}>{i + 1}</span>
                  <span className="leading-snug">{t}</span>
                </li>
              ))}
            </ol>
            <div className="mt-auto pt-4">
              <button
                data-decrire-projet
                onClick={() => setEntretien(text.trim() || 'je veux monter une opération immobilière')}
                className="flex w-full items-center justify-center gap-2 rounded-xl py-2.5 text-sm font-semibold text-[#120d1d] hover:brightness-110"
                style={{ background: VIOLET }}
              >
                <svg viewBox="0 0 20 20" className="h-4 w-4"><path d="M10 3.5 L11.6 8.4 L16.5 10 L11.6 11.6 L10 16.5 L8.4 11.6 L3.5 10 L8.4 8.4 Z" fill="currentColor" /></svg>
                Démarrer le montage
              </button>
              <p className="mt-2 text-center text-[10.5px] text-txt-dim">Entretien guidé · chaque question est facultative</p>
            </div>
          </section>
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
          L'IA ne calcule ni ne modifie aucun score, et n'accède jamais à la base — elle traduit
          votre demande en filtres, le moteur déterministe fait le reste. Chaque appel est journalisé.
        </p>
      </div>
    </div>
  )
}
