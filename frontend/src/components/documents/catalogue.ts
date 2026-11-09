// DOCS-1 (Lot A) — LE CATALOGUE des 8 documents de la catégorie « Documents ». Aucune donnée propre :
// chaque entrée décrit une PORTE (nom, badges de format, description d'une ligne, type de cible) et le
// LIBELLÉ du bouton de génération. La génération elle-même lit les fonctions déjà servies (fiche,
// Comparer, Étude de zone) — ici, QUE de la présentation. L'ordre suit la maquette validée (grille 2×4).
//
// « Comparables DVF » est HORS mandat DOCS-1 (le tiroir de la fiche et sa règle de sélection n'existent
// pas encore) : sa carte est présente, grisée, « bientôt », non cliquable (`bientot: true`).

// ANNONCE-3 — `annonce` : deux entrées (une adresse OU un lien d'annonce), comme l'outil Analyser une annonce.
// ECRANS-NOV-1 §4 — `courrier` : la lettre au propriétaire, servie par l'outil Courrier (pont prérempli).
export type DocKind = 'parcelle' | 'multi' | 'zone' | 'annonce' | 'courrier'

// ECRANS-NOV-1 §4 — les quatre COLONNES PAR USAGE de la maquette. L'ordre des colonnes et des cartes
// dans chaque colonne suit la maquette validée.
export type DocUsage = 'comprendre' | 'chiffrer' | 'partager' | 'secteur'
export const USAGES: { key: DocUsage; titre: string }[] = [
  { key: 'comprendre', titre: 'Comprendre la parcelle' },
  { key: 'chiffrer', titre: 'Chiffrer un projet' },
  { key: 'partager', titre: 'Partager et agir' },
  { key: 'secteur', titre: 'Le secteur' },
]

export interface DocBadge {
  label: string
}

export interface DocCatalogue {
  /** clé interne stable (jamais affichée). */
  key: string
  /** nom affiché sur la carte et en tête de la porte. */
  nom: string
  /** type de cible : une parcelle · 2–3 parcelles · une parcelle + rayon · annonce · courrier. */
  kind: DocKind
  /** ECRANS-NOV-1 §4 — la colonne « par usage » où la carte vit. */
  usage: DocUsage
  /** badges de format (PDF ; ZIP pour le pré-dossier). */
  formats: string[]
  /** description d'une ligne (carte). */
  desc: string
  /** libellé du bouton primaire de la porte (« Générer le dossier », …). */
  cta: string
  /** ligne d'explication sous la parcelle résolue (variante parcelle). */
  explication: string
  /** RETOURS-17 — nom du document dans le fichier exporté (« <IDU> — <fichier>.pdf »). Défaut = `nom`.
   *  Sert quand le nom de carte diffère du nom d'export (ex. « Estimation »). */
  fichier?: string
  /** « Comparables DVF » — carte présente mais grisée/non cliquable (hors mandat). */
  bientot?: boolean
}

// ECRANS-NOV-1 §4 — les DIX documents, rangés par usage (quatre colonnes). Descriptions courtes de la
// maquette validée. La parcelle se choisit UNE fois en haut de l'écran ; chaque carte « Génère » dessus.
export const CATALOGUE: DocCatalogue[] = [
  // ── Comprendre la parcelle ──
  {
    key: 'dossier', nom: 'Dossier', kind: 'parcelle', usage: 'comprendre', formats: ['PDF'],
    desc: 'Tout ce que LABUSE sait de la parcelle, en 10 pages. C’est aussi le Flash.',
    cta: 'Générer le dossier',
    explication: '',
  },
  {
    key: 'gabarit', nom: 'Gabarit', kind: 'parcelle', usage: 'comprendre', formats: ['PDF'],
    desc: 'L’enveloppe réglementaire : zone d’implantation, emprise, hauteur, 3D.',
    cta: 'Générer le gabarit',
    explication: '',
  },
  {
    // ANNONCE-3 — miroir de l'outil « Analyser une annonce ». RECETTE-4 / ECRANS-NOV-1 — nom « Estimation ».
    key: 'analyse-annonce', nom: 'Estimation', kind: 'annonce', usage: 'comprendre', formats: ['PDF'],
    fichier: 'Estimation',
    desc: 'Prix au m² du bien d’après les ventes voisines, avec sa fourchette.',
    cta: 'Générer l’estimation',
    explication: '',
  },
  // ── Chiffrer un projet ──
  {
    // IMPLANTATION-4 (LOT A) — ouvre l'écran d'étude complet (scénarios, plan masse), génère le PDF depuis l'écran.
    key: 'etude-faisabilite', nom: 'Étude de faisabilité', kind: 'parcelle', usage: 'chiffrer', formats: ['PDF'],
    desc: 'Un plan masse et un programme possibles, dessinés par le moteur.',
    cta: 'Ouvrir l’étude de faisabilité',
    explication: '',
  },
  {
    // RECETTE-5 / DOCS-1 §4 — le mot « Financier » disparaît côté client : le document s'appelle « Bilan ».
    key: 'bilan', nom: 'Bilan', kind: 'parcelle', usage: 'chiffrer', formats: ['PDF'],
    desc: 'Le bilan promoteur, 45 postes, charge foncière, coûts, CA et marge.',
    cta: 'Générer le bilan',
    explication: '',
  },
  {
    key: 'comparatif', nom: 'Comparatif', kind: 'multi', usage: 'chiffrer', formats: ['PDF'],
    desc: 'Deux à trois parcelles côte à côte, critère par critère.',
    cta: 'Générer le comparatif',
    explication: '',
  },
  // ── Partager et agir ──
  {
    key: 'apporteur', nom: 'Apporteur', kind: 'parcelle', usage: 'partager', formats: ['PDF'],
    desc: 'Le brief confidentiel à remettre à un apporteur d’affaires.',
    cta: 'Générer l’apporteur',
    explication: '',
  },
  {
    // ECRANS-NOV-1 §4 — « Courrier » : la lettre au propriétaire, servie par l'outil Courrier (pont prérempli).
    key: 'courrier', nom: 'Courrier', kind: 'courrier', usage: 'partager', formats: ['PDF'],
    desc: 'La lettre au propriétaire, à votre nom.',
    cta: 'Rédiger le courrier',
    explication: '',
  },
  {
    key: 'pre-dossier', nom: 'Pré-dossier PC', kind: 'parcelle', usage: 'partager', formats: ['ZIP'],
    desc: 'CERFA et pièces PCMI pré-remplis, dans un ZIP.',
    cta: 'Générer le pré-dossier PC',
    explication: '',
  },
  // ── Le secteur ──
  {
    key: 'etude-zone', nom: 'Étude de zone', kind: 'zone', usage: 'secteur', formats: ['PDF'],
    desc: 'Le territoire autour de la parcelle, dans le rayon choisi.',
    cta: 'Générer l’étude de zone',
    explication: '',
  },
]
