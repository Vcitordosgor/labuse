// CIRCUIT-P (lot 2) — LE CONTENEUR : trois onglets (Résumé par défaut, Circuit, Journal), deux
// boutons à droite (« Envoyer les agents sur tout », « Vérifier que tout coule »), rien d'autre en
// haut. Les pastilles de l'ancien bandeau ont disparu : elles sont devenues les lignes du Résumé.
// Une ligne du Résumé emmène vers l'onglet Circuit, sur sa cible (détail ou groupe).
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { getAdminCircuit, postAdminCircuitVerifier } from '../../../lib/api'

import { Resume } from './Resume'
import { CIRCUIT_CSS } from './style'
import { focusDeCible, type Cible, type CircuitData, type Focus } from './types'

type Onglet = 'resume' | 'circuit' | 'journal'

export function CircuitSection() {
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['admin-circuit'], queryFn: getAdminCircuit, refetchInterval: 60_000 })
  const [onglet, setOnglet] = useState<Onglet>('resume')
  const [focus, setFocus] = useState<Focus>(null)

  const verifier = useMutation({
    mutationFn: postAdminCircuitVerifier,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-circuit'] }),
  })

  const d = q.data as CircuitData | undefined

  const allerVersCircuit = (c: Cible) => { setFocus(focusDeCible(c)); setOnglet('circuit') }

  if (q.isLoading) return <div className="cxp"><style>{CIRCUIT_CSS}</style><div className="muted">Circuit — chargement…</div></div>
  if (!d) return <div className="cxp"><style>{CIRCUIT_CSS}</style><div className="muted">Circuit indisponible.</div></div>

  return (
    <div className="cxp">
      <style>{CIRCUIT_CSS}</style>

      <div className="tabs">
        <button className={onglet === 'resume' ? 'on' : ''} onClick={() => setOnglet('resume')}>
          Résumé<span className="n">{d.resume.total || ''}</span>
        </button>
        <button className={onglet === 'circuit' ? 'on' : ''} onClick={() => setOnglet('circuit')}>Circuit</button>
        <button className={onglet === 'journal' ? 'on' : ''} onClick={() => setOnglet('journal')}>
          Journal<span className="n">aujourd'hui</span>
        </button>
        <div className="actions">
          <button className="btn mauve" disabled
            title="Agents prêts (labuse agent source) — bouton câblé au premier crédit API.">
            Envoyer les agents sur tout
          </button>
          <button className="btn mint" disabled={verifier.isPending}
            onClick={() => { verifier.mutate(); setOnglet('circuit') }}>
            {verifier.isPending ? 'Vérification…' : 'Vérifier que tout coule'}
          </button>
        </div>
      </div>

      <section className={`tab ${onglet === 'resume' ? 'on' : ''}`}>
        <Resume data={d} onCible={allerVersCircuit} />
      </section>

      <section className={`tab ${onglet === 'circuit' ? 'on' : ''}`}>
        {/* lot 3 — le circuit par familles + lot 4 — les pages de détail. */}
        <div className="muted">Le circuit — lot 3 (diagramme par familles) et lot 4 (pages de détail).{focus ? ` Cible : ${JSON.stringify(focus)}` : ''}</div>
      </section>

      <section className={`tab ${onglet === 'journal' ? 'on' : ''}`}>
        {/* lot 5 — le journal (tableau, filtres, pagination). */}
        <div className="muted">Le journal — lot 5.</div>
      </section>
    </div>
  )
}
