// CIRCUIT-P7 (lot 1) — LE CONTENEUR de la page « Données » : un titre, quatre onglets, RIEN d'autre
// dans l'en-tête (plus aucun bouton ni bandeau). Chaque geste vit sur l'onglet dont il répond à la
// question : « Sonder maintenant » et « Envoyer les agents » sur les deux cartes en tête de Sources ;
// « Vérifier que tout coule » dans Circuit, son résultat écrit sous le bouton. Les tâches longues
// (sonde, agents, contrôle, verrous) tournent détachées ; chacune s'affiche là où elle est déclenchée.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'

import {
  getAdminCircuit, getAdminCircuitTaches, getSourcesParElement, postAdminCircuitAgents,
  postAdminCircuitSonder, postAdminCircuitVerifier, postCockpitInjecter,
} from '../../../lib/api'

import { DestinationsDetail } from '../Destinations'

import { CircuitDiagram } from './CircuitDiagram'
import { Detail as DetailPage } from './Detail'
import { ecrireCx, parseCx } from './hash'
import { Journal } from './Journal'
import { Sources } from './Sources'
import { CIRCUIT_CSS } from './style'
import { TableauDeBord } from './TableauDeBord'
import { Usine } from './Usine'
import { type CircuitData } from './types'

// COCKPIT-1b (retour recette) — « L'usine » devient un ONGLET à part entière (plus de page cachée
// derrière « Voir l'usine ») : Tableau de bord · Usine · Sources · Circuit · Journal.
type Onglet = 'tableau' | 'usine' | 'sources' | 'circuit' | 'journal'
// CIRCUIT-P5 — « destinations » : le détail du calibrage PLU par commune (composant Destinations),
// atteint depuis la page de détail de la source GPU (plus par un lien en bas de la page).
type DetailType = 'reservoir' | 'robinet' | 'pompe' | 'compteur' | 'destinations'
type Detail = { type: DetailType; id: number | string } | null
export type Portee = 'sans_amont' | 'g8' | 'tous'

// la date d'un contrôle / passage, lisible (« 24/09 02:05 »).
const quandCourt = (iso?: string | null) =>
  iso ? new Date(iso).toLocaleString('fr-FR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : '—'

export function CircuitSection() {
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['admin-circuit'], queryFn: getAdminCircuit, refetchInterval: 60_000 })
  const [onglet, setOnglet] = useState<Onglet>('tableau')
  const [detail, setDetail] = useState<Detail>(null)
  const [srcDetail, setSrcDetail] = useState<number | null>(null)   // CIRCUIT-P7 (lot 2) — la fiche source (page Sources)
  const [groupe, setGroupe] = useState<(number | string)[] | null>(null)
  const [nJour, setNJour] = useState<number | null>(null)
  const [msgLocal, setMsgLocal] = useState<string | null>(null)   // crédit absent / rien à envoyer / rien à sonder
  const [ferme, setFerme] = useState<string | null>(null)         // message de fin déjà refermé

  // CIRCUIT-P2 (lot 3.2/3.3) — suit les tâches longues ; ne sonde que tant qu'une tourne.
  const taches = useQuery({
    queryKey: ['circuit-taches'], queryFn: getAdminCircuitTaches,
    refetchInterval: (query) => {
      const d = query.state.data as any
      return d && (d.verifier?.etat === 'en_cours' || d.agents?.etat === 'en_cours'
        || d.verrous?.etat === 'en_cours' || d.sonde?.etat === 'en_cours') ? 1500 : false
    },
  })
  const tv = taches.data?.verifier as any
  const ta = taches.data?.agents as any
  const tso = taches.data?.sonde as any        // CIRCUIT-P7 (lot 1) — la tâche « Sonder maintenant »
  const tverr = taches.data?.verrous as any   // DASHBOARD-4 D2 — la tâche « verrous »
  // CIRCUIT-P7 (lot 3) — le registre inversé (élément → sources), fourni au dessin pour la recherche unique.
  const elements = useQuery({ queryKey: ['sources-par-element'], queryFn: getSourcesParElement, staleTime: 5 * 60_000 }).data?.elements ?? []

  const verifier = useMutation({
    mutationFn: postAdminCircuitVerifier,
    onSuccess: () => { setMsgLocal(null); setFerme(null); taches.refetch() },
  })
  const sonder = useMutation({
    mutationFn: () => postAdminCircuitSonder(),
    onSuccess: () => { setMsgLocal(null); setFerme(null); taches.refetch() },
  })
  // COCKPIT-1 (Lot D) — « Injecter » depuis le bandeau de propagation du Circuit.
  const injecterProp = useMutation({
    mutationFn: (sourceId: number) => postCockpitInjecter([sourceId]),
    onSuccess: () => { setMsgLocal('Injection lancée — suivi dans le Journal.'); qc.invalidateQueries({ queryKey: ['admin-circuit'] }) },
  })
  const agents = useMutation({
    mutationFn: (arg?: { portee?: Portee; sourceId?: number }) => postAdminCircuitAgents(arg),
    onSuccess: (r: any) => {
      if (r && r.ok === false) setMsgLocal(r.message || 'Crédit API indisponible.')
      else if (r && r.lance === false) setMsgLocal(r.message || null)
      else { setMsgLocal(null); setFerme(null); taches.refetch() }
    },
  })

  // à la fin d'une tâche (en_cours → autre), la page se rafraîchit seule.
  const prevEtat = useRef<{ v?: string; a?: string; w?: string; s?: string }>({})
  useEffect(() => {
    const v = tv?.etat, a = ta?.etat, w = tverr?.etat, s = tso?.etat
    if ((prevEtat.current.v === 'en_cours' && v !== 'en_cours') ||
        (prevEtat.current.a === 'en_cours' && a !== 'en_cours') ||
        (prevEtat.current.w === 'en_cours' && w !== 'en_cours') ||
        (prevEtat.current.s === 'en_cours' && s !== 'en_cours')) {
      qc.invalidateQueries({ queryKey: ['admin-circuit'] })
    }
    prevEtat.current = { v, a, w, s }
  }, [tv?.etat, ta?.etat, tverr?.etat, tso?.etat, qc])

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
    // le compteur et les destinations ne sont pas deep-linkés (pages transitoires) : hors du hash.
    const cx = detail && detail.type !== 'compteur' && detail.type !== 'destinations'
      ? (detail as { type: 'reservoir' | 'robinet' | 'pompe'; id: number | string }) : null
    const suivant = ecrireCx(window.location.hash, cx)
    if (suivant !== window.location.hash) window.history.replaceState(null, '', suivant || window.location.pathname + window.location.search)
  }, [detail])

  const ouvrirDetail = (type: DetailType, id: number | string) => {
    setDetail({ type, id }); setGroupe(null); setSrcDetail(null); setOnglet('circuit')
  }
  const fermerDetail = () => setDetail(null)
  // CIRCUIT-P7 (lot 2) — clic sur une ligne de Sources : la FICHE de la source, une vraie page qui
  // reste dans l'onglet Sources (retour « ← Sources », Échap). Un clic vers un robinet depuis la
  // fiche bascule sur Circuit (ouvrirDetail, qui referme la fiche source).
  const ouvrirSource = (sid: number) => { setSrcDetail(sid); setOnglet('sources') }

  if (q.isLoading) return <div className="cxp"><style>{CIRCUIT_CSS}</style><div className="muted">Circuit — chargement…</div></div>
  if (!d) return <div className="cxp"><style>{CIRCUIT_CSS}</style><div className="muted">Circuit indisponible.</div></div>

  // ── la ligne de progression / message générique (verrous + messages locaux) sous les onglets.
  //    La sonde, les agents et le contrôle ont désormais leur PLACE (cartes de Sources, bouton de
  //    Circuit) ; seule la tâche verrous (déclenchée depuis le détail de la pompe) reste ici. ──
  let barre: { ton: string; txt: string; pct?: number; fermable?: boolean } | null = null
  const finieW = tverr && (tverr.etat === 'termine' || tverr.etat === 'echec') ? tverr : null
  if (msgLocal) barre = { ton: 'info', txt: msgLocal, fermable: true }
  else if (tverr?.etat === 'en_cours') barre = { ton: 'run', txt: tverr.message || 'Verrous en cours…',
    pct: tverr.total ? Math.round((tverr.fait / tverr.total) * 100) : undefined }
  else if (finieW && finieW.message !== ferme) barre = {
    ton: finieW.etat === 'echec' ? 'echec' : 'ok', txt: finieW.message, fermable: true }

  return (
    <div className="cxp">
      <style>{CIRCUIT_CSS}</style>

      {/* OUTILS-S2 Lot C (C.2) — le titre « Données » + sous-titre était rendu DEUX FOIS : ici et dans
          l'en-tête générique d'AdminView (commun à toutes les sections admin). Doublon retiré : seul
          l'en-tête d'AdminView porte désormais le titre. On garde directement les quatre onglets. */}
      <div className="tabs">
        {/* COCKPIT-1b — Tableau de bord · Usine · Sources · Circuit · Journal. */}
        <button className={onglet === 'tableau' ? 'on' : ''} onClick={() => setOnglet('tableau')}>Tableau de bord</button>
        <button className={onglet === 'usine' ? 'on' : ''} onClick={() => setOnglet('usine')}>Usine</button>
        <button className={onglet === 'sources' ? 'on' : ''} onClick={() => setOnglet('sources')}>
          Sources{d.etats_sources?.vitrine ? <span className="n neutre">{d.etats_sources.vitrine}</span> : ''}
        </button>
        <button className={onglet === 'circuit' ? 'on' : ''} onClick={() => setOnglet('circuit')}>Circuit</button>
        <button className={onglet === 'journal' ? 'on' : ''} onClick={() => setOnglet('journal')}>
          Journal{nJour ? <span className="n neutre">{nJour}</span> : ''}
        </button>
      </div>

      {barre && (
        <div className={`tbar ${barre.ton}`}>
          {barre.pct != null && <span className="pct"><i style={{ width: `${barre.pct}%` }} /></span>}
          <span className="tx">{barre.txt}</span>
          {barre.fermable && <button className="x" onClick={() => { setMsgLocal(null); if (finieW) setFerme(finieW.message) }}>✕</button>}
        </div>
      )}

      <section className={`tab ${onglet === 'tableau' ? 'on' : ''}`}>
        <TableauDeBord data={d} onVoirUsine={() => setOnglet('usine')} onDepotManuel={() => setOnglet('sources')} />
      </section>

      <section className={`tab ${onglet === 'usine' ? 'on' : ''}`}>
        {onglet === 'usine' && <Usine data={d} />}
      </section>

      <section className={`tab ${onglet === 'sources' ? 'on' : ''}`}>
        {/* CIRCUIT-P7 (lot 2) — une ligne de Sources ouvre la FICHE de la source (page, ← Sources). */}
        {srcDetail != null
          ? <DetailPage type="reservoir" id={srcDetail} data={d}
              onClose={() => setSrcDetail(null)} onOpen={ouvrirDetail} retour="← Sources" />
          : <Sources data={d} onOpen={ouvrirSource}
              tacheSonde={tso} tacheAgents={ta}
              onSonder={() => sonder.mutate()} onAgents={(portee) => agents.mutate({ portee })} />}
      </section>

      <section className={`tab ${onglet === 'circuit' ? 'on' : ''}`}>
        {/* CIRCUIT-P7 (lot 1) — « Vérifier que tout coule » vit ICI ; son résultat s'écrit sous le
            bouton (plus de bandeau « Contrôle terminé », plus de ligne « plafond agents »). */}
        {!detail && (
          <div className="cx-verif">
            <button className="btn" disabled={verifier.isPending || tv?.etat === 'en_cours'}
              onClick={() => verifier.mutate()}>
              {tv?.etat === 'en_cours' ? 'Contrôle en cours…' : 'Vérifier que tout coule'}
            </button>
            <div className="cx-verif-res">
              {tv?.etat === 'en_cours'
                ? <span className="muted">{tv.message || 'Contrôle en cours…'}</span>
                : <ResultatControle d={d} tv={tv} onAfaire={() => setOnglet('tableau')} />}
            </div>
          </div>
        )}
        {/* CIRCUIT-P7 (lot 3) — le sens inverse est fondu dans la recherche unique du dessin. */}
        {detail
          ? (detail.type === 'destinations'
            ? <DestinationsDetail onBack={fermerDetail} />
            : <DetailPage type={detail.type} id={detail.id} data={d} onClose={fermerDetail} onOpen={ouvrirDetail} />)
          : <CircuitDiagram data={d} groupe={groupe} onOpen={ouvrirDetail} elements={elements}
              onInjecter={(id) => injecterProp.mutate(id)} />}
      </section>

      <section className={`tab ${onglet === 'journal' ? 'on' : ''}`}>
        <Journal data={d} onOpen={ouvrirDetail} onAujourdhui={setNJour} />
      </section>
    </div>
  )
}

// COCKPIT-1b (retour recette, point 3) — UNE seule phrase sous « Vérifier que tout coule » : « Tout
// coule » ou « N fuite(s) → voir » (lien vers le Tableau de bord). Plus de compteurs eau ancienne /
// verrous ici (ils vivent dans le Tableau de bord et l'Usine), plus de lien « voir dans À faire »
// (l'onglet a disparu). Jamais un recompte au front — on lit la dernière ligne de contrôle.
function ResultatControle({ d, tv, onAfaire }:
  { d: CircuitData; tv: any; onAfaire: () => void }) {
  const c: any = d.dernier_controle
  if (!c && tv?.etat !== 'termine') return <span className="muted">Pas encore de contrôle. Lance-le.</span>
  const fuites = tv?.resultat?.fuites_ouvertes ?? c?.fuites_ouvertes ?? 0
  const ts = tv?.etat === 'termine' ? (tv.maj || tv.fin) : c?.ts
  return (
    <>
      <span className="muted">Dernier contrôle {quandCourt(ts)} — </span>
      {fuites > 0
        ? <><b className="r">{fuites} fuite{fuites > 1 ? 's' : ''}</b>{' '}
            <button className="lienc" onClick={onAfaire}>→ voir</button></>
        : <b>Tout coule.</b>}
    </>
  )
}
