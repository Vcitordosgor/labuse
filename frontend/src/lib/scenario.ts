// ECRANS-NOV-2 — vocabulaire et ordonnancement de l'écran « Analyse LABUSE par scénario ».
// Les LIBELLÉS sont ceux du mandat (« À vérifier », « À différer », « Aucun ajout », « Hors
// projet », « Calcul à compléter ») ; les BANDES et le SIGNAL réutilisent la DA gravée (status.ts).
// Rien n'est calculé ici : ce module ne fait que nommer et ordonner ce que l'API sert.
import { BANDE_META, SIGNAL_META, type Bande } from './status'

export type Objectif = 'sale' | 'potential'
export type ScnScenario = 'keep' | 'rebuild'

// Statuts NON estimés (les estimés s'affichent par leur bande A/B/C/D). Teinte = ambre pour la file
// de travail / à vérifier / différer ; neutre pour « aucun ajout » et « hors projet ».
export const STATUT_SCN_META: Record<string, { label: string; color: string }> = {
  TO_VERIFY: { label: 'À vérifier', color: '#E0A94F' },
  DEFERRED: { label: 'À différer', color: '#E0A94F' },
  COMPUTE_PENDING: { label: 'Calcul à compléter', color: '#C99A52' },
  NO_MARGIN: { label: 'Aucun ajout', color: '#5C7268' },
  OUTSIDE_OBJECTIVE: { label: 'Hors projet', color: '#6B7280' },
  PRESTUDY: { label: 'Préétude', color: '#46A0E0' },
}

// La rangée de puces de POTENTIEL : les 4 bandes (parcelles estimées) PUIS les statuts nommés.
export const BANDES_CHIP = ['A', 'B', 'C', 'D'] as const
export const STATUTS_CHIP = ['TO_VERIFY', 'DEFERRED', 'NO_MARGIN', 'OUTSIDE_OBJECTIVE', 'COMPUTE_PENDING'] as const

// La rangée de puces de PROSPECTION : niveaux de Signal, « non évalué » en fin.
export type NiveauChip = 'fort' | 'moyen' | 'faible' | 'non_evalue'
export const NIVEAUX_CHIP: NiveauChip[] = ['fort', 'moyen', 'faible', 'non_evalue']
export const NIVEAU_META: Record<NiveauChip, { label: string; color: string }> = {
  fort: { label: 'Fort', color: SIGNAL_META.fort.color },
  moyen: { label: 'Moyen', color: SIGNAL_META.moyen.color },
  faible: { label: 'Faible', color: SIGNAL_META.faible.color },
  non_evalue: { label: 'Non évalué', color: '#5C7268' },
}

// Couleur d'une parcelle pour la barre de répartition / la puce de carte : bande si estimée,
// sinon la teinte de son statut nommé.
export function couleurParcelle(statut: string, bande: string | null): string {
  if (statut === 'ESTIMATED' && bande && BANDE_META[bande as Bande]) return BANDE_META[bande as Bande].color
  return STATUT_SCN_META[statut]?.color ?? '#5C7268'
}

// Le libellé de bande pour une puce de carte / le détail (Excellente / Bonne / …).
export function bandeLabel(bande: string | null): string | null {
  return (bande && BANDE_META[bande as Bande]?.label) || null
}

// La phrase qui dit TOUJOURS ce qui classe (mandat §2).
export function phraseClassement(objectif: Objectif, scenario: ScnScenario): string {
  if (objectif === 'sale')
    return 'Classées par Signal de mutation à 12 mois. La bande foncière est indicative, elle ne classe pas.'
  if (scenario === 'rebuild')
    return 'Classées par bande, puis par capacité du nouveau projet. Le gain net est signé.'
  return 'Classées par bande, puis par surface de plancher supplémentaire.'
}

// Le résumé replié des choix (étape « La liste ») : objectif · scénario · cohortes cochées.
export function resumeFiltres(objectif: Objectif, scenario: ScnScenario, cohortes: string[]): string {
  const choix = cohortes.length ? cohortes.join(', ') : 'aucune'
  if (objectif === 'sale') return `Prospection · ${choix}`
  const scn = scenario === 'rebuild' ? 'Reconstruction' : 'Bâti conservé'
  return `Potentiel · ${scn} · ${choix}`
}
