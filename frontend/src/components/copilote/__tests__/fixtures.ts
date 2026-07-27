// M26-B — fixtures d'événements FIGÉES (un jeu par état de la maquette B4).
// Chaque payload reproduit le contrat M26-A à l'identique (events.py, executeur.py,
// moteurs.py : _recap/_entonnoir). Si le contrat back bouge, ces fixtures doivent
// bouger PAR MANDAT — jamais en douce.
import type { CopiloteEvent, Restituee } from '../../../lib/copilote'

const PLAN_INSTRUIRE = [
  { moteur: 'criblage', bloquant: true },
  { moteur: 'filtre_geometrique', bloquant: true },
  { moteur: 'faisabilite', bloquant: true },
  { moteur: 'risques', bloquant: true },
  { moteur: 'marche_dvf', bloquant: false },
  { moteur: 'filtre_budget', bloquant: false },
  { moteur: 'mutation', bloquant: false },
  { moteur: 'assemblage', bloquant: true },
]

let seq = 0
let quandMs = 0
const ev = (kind: CopiloteEvent['kind'], payload: Record<string, unknown>): CopiloteEvent => ({
  seq: ++seq, kind, payload,
  created_at: new Date(1_785_000_000_000 + (quandMs += 4000)).toISOString(),
})

const restituee = (i: number, extra: Partial<Restituee> = {}): Restituee => ({
  idu: `97415000BV${String(180 + i).padStart(4, '0')}`,
  commune: 'Saint-Paul',
  surface_m2: 722 - i * 3,
  tier: 'chaude',
  rang: i + 1,
  zone: i % 3 === 0 ? 'UB2' : 'UB1',
  sdp_m2: 486 - i * 2,
  n_signaux_risques: i % 4 === 0 ? 1 : 0,
  charge_fonciere_eur: 385_000 - i * 1_000,
  prix_probable_eur: 412_000 - i * 2_000,
  au_dessus_charge_supportable: i < 3,
  budget: i === 7 ? 'non estimable — non filtrée' : 'dans le budget',
  ...extra,
})

function etapesCompletes(opts: {
  calibrage: Record<string, 'article_plu' | 'regle_generique'>
  mention_sdp: string
  geoEtiquette: string
}): CopiloteEvent[] {
  const communes = Object.keys(opts.calibrage)
  const out: CopiloteEvent[] = []
  const etape = (moteur: string, resultat: Record<string, unknown>, etiquette: string,
                 compteur?: { avant: number; apres: number }) => {
    out.push(ev('step_started', { moteur, params: { communes, n_candidats: compteur?.avant ?? null, n_refs: null } }))
    out.push(ev('step_completed', {
      moteur, resultat, etiquette, duree_ms: 4200,
      ...(compteur ? { compteur } : {}),
    }))
  }
  etape('criblage', { run_servi: 'q_v7_defisc', n_pool: 13_155, n_candidats: 13_155 },
    'sourcé', { avant: 13_155, apres: 13_155 })
  etape('filtre_geometrique', {
    cible_sdp_m2: 420, calibrage: opts.calibrage,
    garde_fou: { plafond: 5000, a_mordu: false, n_non_examinees: 0 }, n_examinees: 4250,
  }, opts.geoEtiquette, { avant: 13_155, apres: 4250 })
  etape('faisabilite', {
    sdp_cible_m2: 420, n_avant: 4250, n_apres: 2947, n_ecartees: 1303,
    calibrage: opts.calibrage, mention_sdp: opts.mention_sdp, sessions_paralleles: 4,
  }, 'estimé', { avant: 4250, apres: 2947 })
  etape('risques', { n_candidats: 2947, flags: { ppr_rouge: 122 }, n_sans_signal: 2620 }, 'sourcé')
  etape('marche_dvf', {
    n_candidats: 2947, n_charge_calculable: 2753, n_indisponible: 194,
    n_prix_probable: 2753, n_au_dessus_charge_supportable: 3, provenance: 'dvf',
  }, 'estimé')
  etape('filtre_budget', {
    applique: true, motif: null, budget_max_eur: 480_000, n_avant: 2947,
    n_dans_budget: 2753, n_non_estimables_non_filtrees: 194, n_ecartees_budget: 0,
  }, 'estimé', { avant: 2947, apres: 2753 })
  etape('mutation', { run_servi: 'q_v7_defisc', n_candidats: 2753, par_tier: { chaude: 900 } }, 'sourcé')
  return out
}

/** État 1 — instruction terminée, exhaustif, commune calibrée, 20/2753 restituées. */
export function etat1Calibre(): CopiloteEvent[] {
  seq = 0; quandMs = 0
  const calibrage = { 'Saint-Paul': 'article_plu' as const }
  const recap = {
    entonnoir: [
      { etape: 'pool', n: 13_155, etiquette: 'sourcé' },
      { etape: 'filtre_geometrique', n: 4250, etiquette: 'sourcé/estimé selon calibrage' },
      { etape: 'examinees', n: 4250, etiquette: 'sourcé' },
      { etape: 'retenues', n: 2947, etiquette: 'estimé (faisabilité)' },
      { etape: 'dans_budget', n: 2753, etiquette: 'estimé (prix probable)' },
      { etape: 'restituees', n: 20, etiquette: 'sourcé (tri champion P)' },
    ],
    n_retenues: 2753, n_ecartees: 1303, n_non_examinees: 0, n_restituees: 20,
    exhaustif: true, calibrage,
    mention_sdp: 'SDP tracée par article (PLU calibré)',
    motifs_ecartement: ['SDP résiduelle sous la cible', 'prix probable au-dessus du budget'],
    n_au_dessus_charge_supportable: 3,
    restituees: Array.from({ length: 20 }, (_, i) => restituee(i)),
  }
  return [
    ev('run_started', {
      mission: 'instruire',
      brief_raw: 'Terrain pour un collectif de 6 logements à Saint-Paul, budget foncier 480 k€, hors zone rouge PPR',
      plan: PLAN_INSTRUIRE,
    }),
    ev('brief_parsed', {
      brief_json: {
        communes: ['Saint-Paul'], programme: { logements: 6, sdp_cible_m2: 420 },
        budget_max_eur: 480_000,
        contraintes: { exclure_ppr_rouge: true, exclure_abf: false, zones: ['U', 'AU'] },
        surface_min_m2: null,
      },
    }),
    ...etapesCompletes({ calibrage, mention_sdp: 'SDP tracée par article (PLU calibré)', geoEtiquette: 'sourcé' }),
    ev('step_started', { moteur: 'assemblage', params: { communes: ['Saint-Paul'], n_candidats: 2753, n_refs: null } }),
    ev('step_completed', { moteur: 'assemblage', resultat: recap, etiquette: 'sourcé',
      duree_ms: 900, compteur: { avant: 4250, apres: 20 } }),
    ev('run_completed', { n_retenues: 2753, n_ecartees: 1303, duree_totale_ms: 56_000 }),
  ]
}

/** Variante verrous — commune NON calibrée + garde-fou mordu (exhaustif: false). */
export function etat1GeneriqueGardeFou(): CopiloteEvent[] {
  seq = 0; quandMs = 0
  const calibrage = { Cilaos: 'regle_generique' as const }
  const mention = 'SDP estimée — règle générique, PLU non calibré'
  const recap = {
    entonnoir: [
      { etape: 'pool', n: 9800, etiquette: 'sourcé' },
      { etape: 'filtre_geometrique', n: 6100, etiquette: 'sourcé/estimé selon calibrage' },
      { etape: 'examinees', n: 5000, etiquette: 'sourcé' },
      { etape: 'retenues', n: 32, etiquette: 'estimé (faisabilité)' },
      { etape: 'dans_budget', n: 28, etiquette: 'estimé (prix probable)' },
      { etape: 'restituees', n: 4, etiquette: 'sourcé (tri champion P)' },
    ],
    n_retenues: 28, n_ecartees: 4972, n_non_examinees: 1100, n_restituees: 4,
    exhaustif: false, calibrage,
    mention_sdp: mention,
    motifs_ecartement: ['SDP résiduelle sous la cible'],
    n_au_dessus_charge_supportable: 1,
    requalification: 'Résultat NON exhaustif : 28 retenue(s) parmi les 5 000 examinées '
      + 'sur 6 100 candidates — jamais « aucune opportunité ».',
    restituees: Array.from({ length: 4 }, (_, i) =>
      restituee(i, { commune: 'Cilaos', au_dessus_charge_supportable: i === 0 })),
  }
  return [
    ev('run_started', {
      mission: 'instruire',
      brief_raw: 'Terrain pour 12 logements à Cilaos, budget 800 k€',
      plan: PLAN_INSTRUIRE,
    }),
    ev('brief_parsed', {
      brief_json: {
        communes: ['Cilaos'], programme: { logements: 12, sdp_cible_m2: 840 },
        budget_max_eur: 800_000,
        contraintes: { exclure_ppr_rouge: false, exclure_abf: false, zones: null },
        surface_min_m2: null,
      },
    }),
    ...etapesCompletes({ calibrage, mention_sdp: mention, geoEtiquette: 'estimé' }),
    ev('step_started', { moteur: 'assemblage', params: { communes: ['Cilaos'], n_candidats: 28, n_refs: null } }),
    ev('step_completed', { moteur: 'assemblage', resultat: recap, etiquette: 'sourcé',
      duree_ms: 300, compteur: { avant: 6100, apres: 4 } }),
    ev('run_completed', { n_retenues: 28, n_ecartees: 4972, duree_totale_ms: 61_000 }),
  ]
}
