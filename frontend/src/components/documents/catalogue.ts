// DOCS-1 (Lot A) — LE CATALOGUE des 8 documents de la catégorie « Documents ». Aucune donnée propre :
// chaque entrée décrit une PORTE (nom, badges de format, description d'une ligne, type de cible) et le
// LIBELLÉ du bouton de génération. La génération elle-même lit les fonctions déjà servies (fiche,
// Comparer, Étude de zone) — ici, QUE de la présentation. L'ordre suit la maquette validée (grille 2×4).
//
// « Comparables DVF » est HORS mandat DOCS-1 (le tiroir de la fiche et sa règle de sélection n'existent
// pas encore) : sa carte est présente, grisée, « bientôt », non cliquable (`bientot: true`).

export type DocKind = 'parcelle' | 'multi' | 'zone'

export interface DocBadge {
  label: string
}

export interface DocCatalogue {
  /** clé interne stable (jamais affichée). */
  key: string
  /** nom affiché sur la carte et en tête de la porte. */
  nom: string
  /** type de cible : une parcelle · 2–3 parcelles · une parcelle + rayon. */
  kind: DocKind
  /** badges de format (PDF ; PDF + Excel pour le Bilan). */
  formats: string[]
  /** description d'une ligne (carte). */
  desc: string
  /** libellé du bouton primaire de la porte (« Générer le dossier », …). */
  cta: string
  /** ligne d'explication sous la parcelle résolue (variante parcelle). */
  explication: string
  /** « Comparables DVF » — carte présente mais grisée/non cliquable (hors mandat). */
  bientot?: boolean
}

// L'ordre EST celui de la maquette : 2 rangées de 4.
export const CATALOGUE: DocCatalogue[] = [
  {
    key: 'dossier', nom: 'Dossier', kind: 'parcelle', formats: ['PDF'],
    desc: 'La fiche parcelle complète, imprimable : zonage, capacité, risques, marché, réseaux.',
    cta: 'Générer le dossier',
    explication: 'La fiche parcelle complète, telle qu’elle est aujourd’hui. Le PDF apparaît dans Mes documents.',
  },
  {
    // RECETTE-5 / DOCS-1 §4 — le mot « Financier » disparaît côté client : le document s'appelle « Bilan ».
    key: 'bilan', nom: 'Bilan', kind: 'parcelle', formats: ['PDF', 'Excel'],
    desc: 'Charge foncière, coûts, CA et marge, avec vos propres ratios. Prix connu, ou prix maximum du terrain pour votre marge.',
    cta: 'Générer le bilan',
    explication: 'Se calcule sur les données de la fiche et vos ratios. Le PDF apparaît dans Mes documents.',
  },
  {
    key: 'apporteur', nom: 'Apporteur', kind: 'parcelle', formats: ['PDF'],
    desc: 'Présenter un terrain à un acheteur en une page : plan, faits, dernière vente, contact.',
    cta: 'Générer l’apporteur',
    explication: 'Une page depuis la fiche. Le PDF apparaît dans Mes documents.',
  },
  {
    key: 'pre-dossier', nom: 'Pré-dossier PC', kind: 'parcelle', formats: ['PDF'],
    desc: 'Ce que le PLU permet et exige ici, l’enveloppe réglementaire et la liste des pièces à joindre.',
    cta: 'Générer le pré-dossier PC',
    explication: 'Règles du PLU, enveloppe réglementaire, pièces à joindre. Le PDF apparaît dans Mes documents.',
  },
  {
    key: 'gabarit', nom: 'Gabarit', kind: 'parcelle', formats: ['PDF'],
    desc: 'Zone d’implantation, plafond d’emprise, hauteur : le plan, les règles appliquées et celles non intégrées.',
    cta: 'Générer le gabarit',
    explication: 'Le plan et les règles, depuis l’outil Gabarit. Absent si le calcul est incomplet.',
  },
  {
    key: 'comparables', nom: 'Comparables DVF', kind: 'parcelle', formats: ['PDF'],
    desc: 'Les ventes comparables autour de la parcelle : date, type, surface, prix, distance, médiane et rayon retenu.',
    cta: 'Générer les comparables',
    explication: '',
    bientot: true,
  },
  {
    key: 'comparatif', nom: 'Comparatif', kind: 'multi', formats: ['PDF'],
    desc: 'Deux ou trois parcelles côte à côte sur les 17 lignes de Comparer, en page paysage.',
    cta: 'Générer le comparatif',
    explication: 'Les 17 lignes de Comparer, côte à côte. Le PDF apparaît dans Mes documents.',
  },
  {
    key: 'etude-zone', nom: 'Étude de zone', kind: 'zone', formats: ['PDF'],
    desc: 'Population, économie, immobilier, foncier, contraintes, équipements, dynamique — autour d’une parcelle, dans le rayon choisi.',
    cta: 'Générer l’étude de zone',
    explication: 'Les 7 sections et la carte du périmètre. Le PDF apparaît dans Mes documents.',
  },
]
