// CIRCUIT-P (lot 2) / CIRCUIT-P2 (lot 3) — LE CONTENEUR : trois onglets (Résumé, Circuit, Journal),
// deux boutons à droite. « Vérifier que tout coule » et « Envoyer les agents » lancent des TÂCHES
// détachées ; une ligne de progression apparaît sous les onglets et RESTE visible quel que soit
// l'onglet (elle vit dans le conteneur). À la fin, le Résumé se rafraîchit seul et un message dit
// le résultat. « Envoyer les agents » n'est JAMAIS grisé : sans crédit API, un clic dit pourquoi.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'

import {
  getAdminCircuit, getAdminCircuitTaches, postAdminCircuitAgents, postAdminCircuitVerifier,
} from '../../../lib/api'

import { CircuitDiagram } from './CircuitDiagram'
import { Detail as DetailPage } from './Detail'
import { ecrireCx, parseCx } from './hash'
import { Journal } from './Journal'
import { Resume } from './Resume'
import { CIRCUIT_CSS } from './style'
import { focusDeCible, type Cible, type CircuitData } from './types'

type Onglet = 'resume' | 'circuit' | 'journal'
type DetailType = 'reservoir' | 'robinet' | 'pompe' | 'compteur'
type Detail = { type: DetailType; id: number | string } | null

export function CircuitSection() {
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['admin-circuit'], queryFn: getAdminCircuit, refetchInterval: 60_000 })
  const [onglet, setOnglet] = useState<Onglet>('resume')
  const [detail, setDetail] = useState<Detail>(null)
  const [groupe, setGroupe] = useState<(number | string)[] | null>(null)
  const [nJour, setNJour] = useState<number | null>(null)
  const [msgLocal, setMsgLocal] = useState<string | null>(null)   // crédit absent / rien à envoyer
  const [ferme, setFerme] = useState<string | null>(null)         // message de fin déjà refermé

  // CIRCUIT-P2 (lot 3.2/3.3) — suit les tâches longues ; ne sonde que tant qu'une tourne.
  const taches = useQuery({
    queryKey: ['circuit-taches'], queryFn: getAdminCircuitTaches,
    refetchInterval: (query) => {
      const d = query.state.data as any
      return d && (d.verifier?.etat === 'en_cours' || d.agents?.etat === 'en_cours') ? 1500 : false
    },
  })
  const tv = taches.data?.verifier as any
  const ta = taches.data?.agents as any

  const verifier = useMutation({
    mutationFn: postAdminCircuitVerifier,
    onSuccess: () => { setMsgLocal(null); setFerme(null); taches.refetch() },
  })
  const agents = useMutation({
    mutationFn: () => postAdminCircuitAgents(),
    onSuccess: (r: any) => {
      if (r && r.ok === false) setMsgLocal(r.message || 'Crédit API indisponible.')
      else if (r && r.lance === false) setMsgLocal(r.message || null)
      else { setMsgLocal(null); setFerme(null); taches.refetch() }
    },
  })

  // à la fin d'une tâche (en_cours → autre), le Résumé se rafraîchit seul.
  const prevEtat = useRef<{ v?: string; a?: string }>({})
  useEffect(() => {
    const v = tv?.etat, a = ta?.etat
    if ((prevEtat.current.v === 'en_cours' && v !== 'en_cours') ||
        (prevEtat.current.a === 'en_cours' && a !== 'en_cours')) {
      qc.invalidateQueries({ queryKey: ['admin-circuit'] })
    }
    prevEtat.current = { v, a }
  }, [tv?.etat, ta?.etat, qc])

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
    // le compteur n'est pas deep-linké (page transitoire d'agrégat) : il ne s'écrit pas au hash.
    const cx = detail && detail.type !== 'compteur'
      ? (detail as { type: 'reservoir' | 'robinet' | 'pompe'; id: number | string }) : null
    const suivant = ecrireCx(window.location.hash, cx)
    if (suivant !== window.location.hash) window.history.replaceState(null, '', suivant || window.location.pathname + window.location.search)
  }, [detail])

  const allerVersCircuit = (c: Cible) => {
    const f = focusDeCible(c)
    if (f?.kind === 'detail') { setDetail({ type: f.type, id: f.id }); setGroupe(null) }
    else if (f?.kind === 'groupe') { setGroupe(f.ids); setDetail(null) }
    setOnglet('circuit')
  }
  const ouvrirDetail = (type: DetailType, id: number | string) => {
    setDetail({ type, id }); setGroupe(null); setOnglet('circuit')
  }
  const fermerDetail = () => setDetail(null)

  if (q.isLoading) return <div className="cxp"><style>{CIRCUIT_CSS}</style><div className="muted">Circuit — chargement…</div></div>
  if (!d) return <div className="cxp"><style>{CIRCUIT_CSS}</style><div className="muted">Circuit indisponible.</div></div>

  // ── la ligne de progression / message, sous les onglets (visible quel que soit l'onglet) ──
  const enCours = tv?.etat === 'en_cours' ? tv : ta?.etat === 'en_cours' ? ta : null
  const finie = [tv, ta].filter((t: any) => t && (t.etat === 'termine' || t.etat === 'echec'))
    .sort((a: any, b: any) => (a.maj < b.maj ? 1 : -1))[0]
  let barre: { ton: string; txt: string; pct?: number; fermable?: boolean } | null = null
  if (msgLocal) barre = { ton: 'info', txt: msgLocal, fermable: true }
  else if (enCours) barre = { ton: 'run', txt: enCours.message || 'En cours…',
    pct: enCours.total ? Math.round((enCours.fait / enCours.total) * 100) : undefined }
  else if (finie && finie.message !== ferme) barre = {
    ton: finie.etat === 'echec' ? 'echec' : 'ok', txt: finie.message, fermable: true }

  return (
    <div className="cxp">
      <style>{CIRCUIT_CSS}</style>

      <div className="tabs">
        <button className={onglet === 'resume' ? 'on' : ''} onClick={() => setOnglet('resume')}>
          Résumé<span className="n">{d.resume.total || ''}</span>
        </button>
        <button className={onglet === 'circuit' ? 'on' : ''} onClick={() => setOnglet('circuit')}>Circuit</button>
        <button className={onglet === 'journal' ? 'on' : ''} onClick={() => setOnglet('journal')}>
          Journal{nJour ? <span className="n">{nJour}</span> : ''}
        </button>
        <div className="actions">
          <button className="btn mauve" disabled={agents.isPending || ta?.etat === 'en_cours'}
            onClick={() => { agents.mutate(); setOnglet('circuit') }}>
            {ta?.etat === 'en_cours' ? `${ta.fait} / ${ta.total} agents…` : 'Envoyer les agents sur tout'}
          </button>
          <button className="btn mint" disabled={verifier.isPending || tv?.etat === 'en_cours'}
            onClick={() => { verifier.mutate(); setOnglet('circuit') }}>
            {tv?.etat === 'en_cours' ? 'Contrôle en cours…' : 'Vérifier que tout coule'}
          </button>
        </div>
      </div>

      {barre && (
        <div className={`tbar ${barre.ton}`}>
          {barre.pct != null && <span className="pct"><i style={{ width: `${barre.pct}%` }} /></span>}
          <span className="tx">{barre.txt}</span>
          {barre.fermable && <button className="x" onClick={() => { setMsgLocal(null); if (finie) setFerme(finie.message) }}>✕</button>}
        </div>
      )}

      <section className={`tab ${onglet === 'resume' ? 'on' : ''}`}>
        <Resume data={d} onCible={allerVersCircuit} />
      </section>

      <section className={`tab ${onglet === 'circuit' ? 'on' : ''}`}>
        {detail
          ? <DetailPage type={detail.type} id={detail.id} data={d} onClose={fermerDetail} onOpen={ouvrirDetail} />
          : <CircuitDiagram data={d} groupe={groupe} onOpen={ouvrirDetail} />}
      </section>

      <section className={`tab ${onglet === 'journal' ? 'on' : ''}`}>
        <Journal data={d} onOpen={ouvrirDetail} onAujourdhui={setNJour} />
      </section>
    </div>
  )
}
