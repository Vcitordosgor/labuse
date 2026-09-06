// CIRCUIT-P (lot 2) — LE CONTENEUR : trois onglets (Résumé par défaut, Circuit, Journal), deux
// boutons à droite (« Envoyer les agents sur tout », « Vérifier que tout coule »), rien d'autre en
// haut. Les pastilles de l'ancien bandeau ont disparu : elles sont devenues les lignes du Résumé.
// Une ligne du Résumé emmène vers l'onglet Circuit, sur sa cible (détail ou groupe).
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'

import { getAdminCircuit, postAdminCircuitVerifier } from '../../../lib/api'

import { CircuitDiagram } from './CircuitDiagram'
import { Detail as DetailPage } from './Detail'
import { ecrireCx, parseCx } from './hash'
import { Resume } from './Resume'
import { CIRCUIT_CSS } from './style'
import { focusDeCible, type Cible, type CircuitData } from './types'

type Onglet = 'resume' | 'circuit' | 'journal'
type Detail = { type: 'reservoir' | 'robinet' | 'pompe'; id: number | string } | null

export function CircuitSection() {
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['admin-circuit'], queryFn: getAdminCircuit, refetchInterval: 60_000 })
  const [onglet, setOnglet] = useState<Onglet>('resume')
  const [detail, setDetail] = useState<Detail>(null)
  const [groupe, setGroupe] = useState<(number | string)[] | null>(null)

  const verifier = useMutation({
    mutationFn: postAdminCircuitVerifier,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-circuit'] }),
  })

  const d = q.data as CircuitData | undefined

  // deep-link : ouvre le détail porté par le hash (#…&cx=reservoir:42) au montage et sur hashchange.
  useEffect(() => {
    const lire = () => { const c = parseCx(window.location.hash); if (c) { setDetail(c); setOnglet('circuit') } }
    lire()
    window.addEventListener('hashchange', lire)
    return () => window.removeEventListener('hashchange', lire)
  }, [])
  // reflète le détail ouvert dans le hash (fusion, sans écraser les autres paramètres).
  useEffect(() => {
    const suivant = ecrireCx(window.location.hash, detail)
    if (suivant !== window.location.hash) window.history.replaceState(null, '', suivant || window.location.pathname + window.location.search)
  }, [detail])

  const allerVersCircuit = (c: Cible) => {
    const f = focusDeCible(c)
    if (f?.kind === 'detail') { setDetail({ type: f.type, id: f.id }); setGroupe(null) }
    else if (f?.kind === 'groupe') { setGroupe(f.ids); setDetail(null) }
    setOnglet('circuit')
  }
  const ouvrirDetail = (type: 'reservoir' | 'robinet' | 'pompe', id: number | string) => {
    setDetail({ type, id }); setGroupe(null); setOnglet('circuit')
  }
  const fermerDetail = () => setDetail(null)

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
        {detail
          ? <DetailPage type={detail.type} id={detail.id} data={d} onClose={fermerDetail} onOpen={ouvrirDetail} />
          : <CircuitDiagram data={d} groupe={groupe} onOpen={ouvrirDetail} />}
      </section>

      <section className={`tab ${onglet === 'journal' ? 'on' : ''}`}>
        {/* lot 5 — le journal (tableau, filtres, pagination). */}
        <div className="muted">Le journal — lot 5.</div>
      </section>
    </div>
  )
}
