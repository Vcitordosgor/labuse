// M26-B — client de l'API Copilote (M26-A) : types du contrat d'événements + appels HTTP.
// -----------------------------------------------------------------------------
// L'écran est une PROJECTION de l'event log : ces types décrivent les payloads
// tels qu'émis par le back (src/labuse/copilote/{events,executeur,moteurs}.py),
// rien de plus. Aucune donnée dérivée, aucun recalcul — si un champ manque ici,
// il manque au back : STOP et rapport (règle du mandat), pas de bricolage front.
// -----------------------------------------------------------------------------
import { ApiError } from './api'

// Missions M26-A servies par le back (POST /runs → 422 sinon). Les missions à venir
// (M26-C/D) n'existent que côté écran, désactivées — voir CLIENT.copilote.missions.
export type MissionActive = 'instruire' | 'shortlist'

export type CopiloteStatut =
  | 'interpreting' | 'awaiting_user' | 'running' | 'paused'
  | 'done' | 'failed' | 'cancelled'

export type CopiloteKind =
  | 'run_started' | 'brief_parsed' | 'clarification_requested' | 'clarification_answered'
  | 'step_started' | 'step_completed' | 'step_failed'
  | 'run_paused' | 'run_resumed' | 'run_completed' | 'run_failed' | 'run_cancelled'

/** Un événement du fil, tel que servi par le SSE et par events_after (rejeu). */
export interface CopiloteEvent {
  seq: number
  kind: CopiloteKind
  payload: Record<string, unknown>
  created_at: string
}

export interface EtapePlan { moteur: string; bloquant: boolean }

/** Étage d'entonnoir — l'étiquette est une CHAÎNE LIBRE du back (« sourcé »,
 *  « estimé (faisabilité) », « sourcé/estimé selon calibrage »…), affichée telle quelle. */
export interface EntonnoirEtage { etape: string; n: number; etiquette: string }

export interface Clarification {
  question: string
  champ_manquant: string
  options?: string[] | null
}

export interface StepCompleted {
  moteur: string
  resultat: Record<string, unknown>
  etiquette: string
  duree_ms: number
  compteur?: { avant: number; apres: number } | null
}

export interface Restituee {
  idu: string
  commune: string
  surface_m2: number
  tier: string
  rang: number | null
  zone: string | null
  sdp_m2: number | null
  n_signaux_risques: number
  charge_fonciere_eur: number | null
  prix_probable_eur: number | null
  au_dessus_charge_supportable: boolean | null
  budget: string | null
}

/** Recap d'assemblage (resultat du step_completed « assemblage » / « assemblage_court »). */
export interface RecapAssemblage {
  entonnoir: EntonnoirEtage[]
  n_retenues: number
  n_ecartees: number
  n_non_examinees: number
  n_restituees: number
  exhaustif: boolean
  calibrage: Record<string, 'article_plu' | 'regle_generique'>
  mention_sdp: string
  motifs_ecartement: string[]
  n_au_dessus_charge_supportable: number
  requalification?: string
  restituees?: Restituee[]
  restituees_idu?: string[]
}

export interface RunFinal { n_retenues: number; n_ecartees: number; duree_totale_ms: number }
export interface RunEchec { code: string; message: string; detail?: string }

/** 429 à la création : aucun run créé, aucun moteur appelé (état 5). Le corps du back
 *  porte detail + quota + gel_jusqua — on le conserve intégralement pour l'écran. */
export class CopiloteQuotaError extends Error {
  detail: string
  quota: number | null
  gelJusqua: string | null
  constructor(detail: string, quota: number | null, gelJusqua: string | null) {
    super(detail)
    this.detail = detail
    this.quota = quota
    this.gelJusqua = gelJusqua
  }
}

async function jc<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, init)
  if (!r.ok) {
    const corps = (await r.json().catch(() => null)) as
      { detail?: unknown; quota?: unknown; gel_jusqua?: unknown } | null
    const detail = typeof corps?.detail === 'string' ? corps.detail : undefined
    if (r.status === 429)
      throw new CopiloteQuotaError(detail ?? 'Quota Copilote atteint.',
        typeof corps?.quota === 'number' ? corps.quota : null,
        typeof corps?.gel_jusqua === 'string' ? corps.gel_jusqua : null)
    throw new ApiError(url, r.status, detail)
  }
  return r.json() as Promise<T>
}

// SUITE-1 S9 — un seul Copilote (v2). Les missions lourdes (RECHERCHE/VERIFICATION) sont servies par
// le moteur run-scopé sous le préfixe /api/copilote-v2/runs* (les URL v1 /api/copilote/* n'existent
// plus). Quota UNIFIÉ (comme /ask). Le contrat d'événements/SSE est INCHANGÉ.
export const copiloteCreerRun = (mission: MissionActive, brief_raw: string) =>
  jc<{ run_id: string }>('/api/copilote-v2/runs', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mission, brief_raw }),
  })

export const copiloteRepondre = (runId: string, reponse: string) =>
  jc<{ run_id: string; status: string }>(`/api/copilote-v2/runs/${runId}/answer`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reponse }),
  })

export const copiloteAnnuler = (runId: string) =>
  jc<{ run_id: string; status: string }>(`/api/copilote-v2/runs/${runId}/cancel`, { method: 'POST' })

export const copiloteRuns = (limit = 20, offset = 0) =>
  jc<{ runs: Array<{ run_id: string; mission: string; status: CopiloteStatut; brief_raw: string
       created_at: string; finished_at: string | null }>; limit: number; offset: number }>(
    `/api/copilote-v2/runs?limit=${limit}&offset=${offset}`)

/** URL du flux SSE — reprise sans doublon ni trou : after_seq = dernier seq reçu. */
export const copiloteEventsUrl = (runId: string, afterSeq: number) =>
  `/api/copilote-v2/runs/${runId}/events?after_seq=${afterSeq}`
