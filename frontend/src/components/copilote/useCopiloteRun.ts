// M26-B — LE hook SSE du Copilote (unique point d'intégration flux, décision plan).
// -----------------------------------------------------------------------------
// Reprise sans doublon ni trou : `after_seq` = dernier seq reçu. Le back rejoue
// tout ce qui suit, le réducteur dédoublonne — un rafraîchissement/reconnexion
// retombe exactement sur le même fil (critère d'acceptation du mandat).
// Cas gérés : filet serveur 180 s (`fin: flux_expire` → réouverture immédiate),
// coupure réseau (réouverture au dernier seq + indicateur discret), clarification
// (`fin: awaiting_user` → flux fermé, rouvert après la réponse), annulation.
// -----------------------------------------------------------------------------
import { useCallback, useEffect, useRef, useState } from 'react'
import {
  CopiloteQuotaError, copiloteAnnuler, copiloteCreerRun, copiloteEventsUrl,
  copiloteRepondre,
  type CopiloteEvent, type CopiloteKind, type MissionActive,
} from '../../lib/copilote'
import { VUE_INITIALE, reduireEvenements, type VueCopilote } from './reduireEvenements'

// EventSource ne délivre les événements NOMMÉS (event: kind) qu'aux listeners
// explicites — la taxonomie fermée M26-A est donc listée telle quelle.
const KINDS: CopiloteKind[] = [
  'run_started', 'brief_parsed', 'clarification_requested', 'clarification_answered',
  'step_started', 'step_completed', 'step_failed',
  'run_paused', 'run_resumed', 'run_completed', 'run_failed', 'run_cancelled',
]

const REPRISE_MS = 2000   // délai avant réouverture après coupure réseau

export interface CopiloteRun {
  runId: string | null
  vue: VueCopilote
  /** Event log brut reçu (ordonné, dédoublonné) — c'est LE journal montré au client. */
  evenements: CopiloteEvent[]
  /** true entre une coupure du flux et sa reprise — indicateur discret du mandat. */
  fluxInterrompu: boolean
  /** 429 à la création : état 5 — aucun run créé, aucun moteur appelé. */
  quota: CopiloteQuotaError | null
  /** Erreur HTTP hors quota (création/réponse/annulation), message honnête. */
  erreur: string | null
  enCreation: boolean
  instruire: (mission: MissionActive, brief: string) => Promise<void>
  repondre: (texte: string) => Promise<void>
  annuler: () => Promise<void>
  /** Rejoue un run existant depuis seq 0 (liste des runs, lien direct). */
  charger: (runId: string) => void
  reinitialiser: () => void
}

export function useCopiloteRun(): CopiloteRun {
  const [runId, setRunId] = useState<string | null>(null)
  const [vue, setVue] = useState<VueCopilote>(VUE_INITIALE)
  const [evenements, setEvenements] = useState<CopiloteEvent[]>([])
  const [fluxInterrompu, setFluxInterrompu] = useState(false)
  const [quota, setQuota] = useState<CopiloteQuotaError | null>(null)
  const [erreur, setErreur] = useState<string | null>(null)
  const [enCreation, setEnCreation] = useState(false)
  const esRef = useRef<EventSource | null>(null)
  const seqRef = useRef(0)                 // dernier seq reçu — vérité de la reprise
  const runRef = useRef<string | null>(null)
  const repriseRef = useRef<number | null>(null)

  const fermerFlux = useCallback(() => {
    esRef.current?.close()
    esRef.current = null
    if (repriseRef.current != null) { clearTimeout(repriseRef.current); repriseRef.current = null }
  }, [])

  const ouvrir = useCallback((id: string) => {
    fermerFlux()
    const es = new EventSource(copiloteEventsUrl(id, seqRef.current))
    esRef.current = es
    const surEvenement = (me: Event) => {
      setFluxInterrompu(false)
      const e = JSON.parse((me as MessageEvent).data) as CopiloteEvent
      if (e.seq <= seqRef.current) return            // rejeu large : jamais de doublon
      seqRef.current = e.seq
      setEvenements((prev) => [...prev, e])
      setVue((prev) => reduireEvenements([e], prev))
    }
    for (const k of KINDS) es.addEventListener(k, surEvenement)
    es.addEventListener('fin', (me) => {
      const { status } = JSON.parse((me as MessageEvent).data) as { status: string }
      es.close()
      if (esRef.current === es) esRef.current = null
      setFluxInterrompu(false)
      // filet serveur (180 s) : le run continue, on se raccroche au même fil
      if (status === 'flux_expire') ouvrir(id)
      // done/failed/cancelled/awaiting_user : l'état est déjà dans le réducteur
    })
    es.onerror = () => {
      // Coupure (réseau, restart serveur). EventSource retenterait l'URL d'origine avec
      // un after_seq PÉRIMÉ → doublons : on reprend nous-mêmes au dernier seq reçu.
      es.close()
      if (esRef.current === es) esRef.current = null
      setFluxInterrompu(true)
      repriseRef.current = window.setTimeout(() => ouvrir(id), REPRISE_MS)
    }
  }, [fermerFlux])

  useEffect(() => fermerFlux, [fermerFlux])          // démontage : flux fermé, run continue au back

  const instruire = useCallback(async (mission: MissionActive, brief: string) => {
    fermerFlux()
    setQuota(null); setErreur(null); setFluxInterrompu(false)
    setVue(VUE_INITIALE); setEvenements([]); seqRef.current = 0
    setEnCreation(true)
    try {
      const { run_id } = await copiloteCreerRun(mission, brief)
      runRef.current = run_id
      setRunId(run_id)
      ouvrir(run_id)
    } catch (e) {
      if (e instanceof CopiloteQuotaError) setQuota(e)
      else setErreur(e instanceof Error ? e.message : String(e))
    } finally {
      setEnCreation(false)
    }
  }, [fermerFlux, ouvrir])

  const repondre = useCallback(async (texte: string) => {
    const id = runRef.current
    if (!id) return
    try {
      await copiloteRepondre(id, texte)
      ouvrir(id)                                     // le fil CONTINUE (jamais de redémarrage)
    } catch (e) {
      setErreur(e instanceof Error ? e.message : String(e))
    }
  }, [ouvrir])

  const annuler = useCallback(async () => {
    const id = runRef.current
    if (!id) return
    try {
      await copiloteAnnuler(id)
      if (!esRef.current) ouvrir(id)                 // flux fermé (pause) : capter run_cancelled
    } catch (e) {
      setErreur(e instanceof Error ? e.message : String(e))
    }
  }, [ouvrir])

  const charger = useCallback((id: string) => {
    fermerFlux()
    setQuota(null); setErreur(null); setFluxInterrompu(false)
    setVue(VUE_INITIALE); setEvenements([]); seqRef.current = 0
    runRef.current = id
    setRunId(id)
    ouvrir(id)
  }, [fermerFlux, ouvrir])

  const reinitialiser = useCallback(() => {
    fermerFlux()
    runRef.current = null
    setRunId(null); setVue(VUE_INITIALE); setEvenements([]); seqRef.current = 0
    setQuota(null); setErreur(null); setFluxInterrompu(false)
  }, [fermerFlux])

  return { runId, vue, evenements, fluxInterrompu, quota, erreur, enCreation,
           instruire, repondre, annuler, charger, reinitialiser }
}
