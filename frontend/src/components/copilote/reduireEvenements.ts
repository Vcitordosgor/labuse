// M26-B — réduction de l'event log Copilote en modèle de vue. FONCTION PURE.
// -----------------------------------------------------------------------------
// Miroir front de events.reduce_run (back) : le statut et tout ce qui s'affiche
// sont DÉRIVÉS de la suite d'événements, jamais recalculés à partir des données
// métier. Idempotente au rejeu : un événement de seq déjà vu est ignoré — la
// reconnexion SSE `after_seq` peut rejouer large sans doublon ni trou.
// -----------------------------------------------------------------------------
import type {
  Clarification, CopiloteEvent, CopiloteStatut, EtapePlan, RecapAssemblage,
  RunEchec, RunFinal, StepCompleted,
} from '../../lib/copilote'

// Transitions kind → statut : copie conforme de _TRANSITIONS (events.py). Un état
// terminal est absorbant — tout événement postérieur est ignoré, comme au back.
const TRANSITIONS: Record<string, CopiloteStatut> = {
  run_started: 'interpreting',
  brief_parsed: 'running',
  clarification_requested: 'awaiting_user',
  clarification_answered: 'interpreting',
  step_started: 'running',
  step_completed: 'running',
  step_failed: 'running',
  run_paused: 'paused',
  run_resumed: 'running',
  run_completed: 'done',
  run_failed: 'failed',
  run_cancelled: 'cancelled',
}
const TERMINAL = new Set<CopiloteStatut>(['done', 'failed', 'cancelled'])

export type EtatEtape = 'attente' | 'active' | 'faite' | 'echouee'

export interface EtapeVue {
  moteur: string
  bloquant: boolean
  etat: EtatEtape
  /** step_completed intégral (resultat, etiquette, duree_ms, compteur) — payload brut. */
  fait: StepCompleted | null
  echec: { code_erreur: string; resume: string } | null
}

export interface VueCopilote {
  statut: CopiloteStatut
  dernierSeq: number
  mission: string | null
  briefRaw: string | null
  /** brief_json validé par l'interpréteur (communes, programme, budget…) — payload brut. */
  briefJson: Record<string, unknown> | null
  plan: EtapePlan[]
  etapes: EtapeVue[]
  clarification: Clarification | null
  /** Recap d'assemblage (entonnoir, top-N, calibrage, exhaustif…) — payload brut. */
  recap: RecapAssemblage | null
  final: RunFinal | null
  echec: RunEchec | null
  motifAnnulation: string | null
}

export const VUE_INITIALE: VueCopilote = {
  statut: 'interpreting', dernierSeq: 0, mission: null, briefRaw: null, briefJson: null,
  plan: [], etapes: [], clarification: null, recap: null, final: null,
  echec: null, motifAnnulation: null,
}

const etapesDepuisPlan = (plan: EtapePlan[]): EtapeVue[] =>
  plan.map((e) => ({ moteur: e.moteur, bloquant: e.bloquant, etat: 'attente', fait: null, echec: null }))

const majEtape = (etapes: EtapeVue[], moteur: string, maj: Partial<EtapeVue>): EtapeVue[] =>
  etapes.map((e) => (e.moteur === moteur ? { ...e, ...maj } : e))

// ── état 2 · entonnoir PENDANT le run — projection pure des step_completed ──────────────
// Un étage n'affiche un nombre que si le moteur correspondant a terminé (compteur du
// payload). « examinees » et « restituees » n'existent qu'au recap d'assemblage : ils
// restent en attente (aucun step_progress en M26-A — arbitrage GO, pas de compteur inventé).
const ETAGES_RUN: Array<{ etape: string; moteur: string | null }> = [
  { etape: 'pool', moteur: 'criblage' },
  { etape: 'filtre_geometrique', moteur: 'filtre_geometrique' },
  { etape: 'examinees', moteur: null },
  { etape: 'retenues', moteur: 'faisabilite' },
  { etape: 'dans_budget', moteur: 'filtre_budget' },
  { etape: 'restituees', moteur: null },
]

export interface EtageEnCours { etape: string; n: number | null; etiquette: string | null }

export function entonnoirEnCours(vue: VueCopilote): EtageEnCours[] {
  const auPlan = new Set(vue.plan.map((e) => e.moteur))
  return ETAGES_RUN
    .filter((s) => s.moteur == null || auPlan.has(s.moteur))
    .map((s) => {
      const fait = s.moteur ? vue.etapes.find((e) => e.moteur === s.moteur)?.fait : null
      return { etape: s.etape, n: fait?.compteur?.apres ?? null, etiquette: fait?.etiquette ?? null }
    })
}

/** Calibrage dès qu'un moteur l'a émis (filtre géométrique ou faisabilité) — payload brut. */
export function calibrageConnu(vue: VueCopilote): Record<string, string> | null {
  for (const m of ['faisabilite', 'filtre_geometrique']) {
    const r = vue.etapes.find((e) => e.moteur === m)?.fait?.resultat as
      { calibrage?: Record<string, string> } | undefined
    if (r?.calibrage && Object.keys(r.calibrage).length) return r.calibrage
  }
  return null
}

/** État de la ligne « Interprétation » du fil (avant les moteurs). */
export type EtatInterpretation = 'faite' | 'active' | 'pause'
export function etatInterpretation(vue: VueCopilote): EtatInterpretation {
  if (vue.clarification != null || vue.statut === 'awaiting_user') return 'pause'
  if (vue.briefJson != null) return 'faite'
  return vue.statut === 'interpreting' ? 'active' : 'faite'
}

export function reduireEvenements(evts: CopiloteEvent[], base: VueCopilote = VUE_INITIALE): VueCopilote {
  let vue = base
  // rejeu large toléré : tri par seq + dédoublonnage strict sur dernierSeq
  const tries = [...evts].sort((a, b) => a.seq - b.seq)
  for (const e of tries) {
    if (e.seq <= vue.dernierSeq) continue
    if (TERMINAL.has(vue.statut)) return vue        // absorbant, comme reduce_run
    const p = e.payload as Record<string, unknown>
    const statut = TRANSITIONS[e.kind] ?? vue.statut
    vue = { ...vue, dernierSeq: e.seq, statut }
    switch (e.kind) {
      case 'run_started': {
        const plan = (p.plan ?? []) as EtapePlan[]
        vue = { ...vue, mission: (p.mission as string | undefined) ?? null,
                briefRaw: (p.brief_raw as string | undefined) ?? null,
                plan, etapes: etapesDepuisPlan(plan) }
        break
      }
      case 'clarification_requested':
        vue = { ...vue, clarification: p as unknown as Clarification }
        break
      case 'clarification_answered':
        vue = { ...vue, clarification: null }
        break
      case 'step_started':
        vue = { ...vue, etapes: majEtape(vue.etapes, p.moteur as string, { etat: 'active' }) }
        break
      case 'step_completed': {
        const fait = p as unknown as StepCompleted
        let recap = vue.recap
        if (fait.moteur === 'assemblage' || fait.moteur === 'assemblage_court')
          recap = fait.resultat as unknown as RecapAssemblage
        vue = { ...vue, recap, etapes: majEtape(vue.etapes, fait.moteur, { etat: 'faite', fait }) }
        break
      }
      case 'step_failed':
        vue = { ...vue, etapes: majEtape(vue.etapes, p.moteur as string,
          { etat: 'echouee',
            echec: { code_erreur: p.code_erreur as string, resume: p.resume as string } }) }
        break
      case 'run_completed':
        vue = { ...vue, final: p as unknown as RunFinal }
        break
      case 'run_failed':
        vue = { ...vue, echec: p as unknown as RunEchec }
        break
      case 'run_cancelled':
        vue = { ...vue, motifAnnulation: (p.motif as string | undefined) ?? null }
        break
      case 'brief_parsed':
        vue = { ...vue, briefJson: (p.brief_json as Record<string, unknown> | undefined) ?? null }
        break
      default:
        break                                        // pause/reprise : statut seul
    }
  }
  return vue
}
