// DOCS-1 (Lot A) — LE CATALOGUE des 8 documents de la catégorie « Documents ». Aucune donnée propre :
// chaque entrée décrit une PORTE (nom, badges de format, description d'une ligne, type de cible) et le
// LIBELLÉ du bouton de génération. La génération elle-même lit les fonctions déjà servies (fiche,
// Comparer, Étude de zone) — ici, QUE de la présentation. L'ordre suit la maquette validée (grille 2×4).
//
// « Comparables DVF » est HORS mandat DOCS-1 (le tiroir de la fiche et sa règle de sélection n'existent
// pas encore) : sa carte est présente, grisée, « bientôt », non cliquable (`bientot: true`).

// ANNONCE-3 — `annonce` : deux entrées (une adresse OU un lien d'annonce), comme l'outil Analyser une annonce.
export type DocKind = 'parcelle' | 'multi' | 'zone' | 'annonce'

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

// L'ordre EST celui de la maquette : 2 rangées de 4 + ANNONCE-3 (9e carte « Analyse d'annonce »,
// la grille `grid-cols-4` s'adapte : 2 rangées pleines + 1 carte à la 3e).
export const CATALOGUE: DocCatalogue[] = [
  {
    key: 'dossier', nom: 'Dossier', kind: 'parcelle', formats: ['PDF'],
    desc: 'La fiche parcelle complète, imprimable : zonage, capacité, risques, marché, réseaux.',
    cta: 'Générer le dossier',
    explication: '',   // RECETTE-2 (E2) — phrase « La fiche parcelle complète … Mes documents » retirée
  },
  {
    // RECETTE-5 / DOCS-1 §4 — le mot « Financier » disparaît côté client : le document s'appelle « Bilan ».
    // DOCS-FIX-1 (P12) — badge « Excel » RETIRÉ : l'export Excel n'existe pas (`_EXCEL_DISPONIBLE`
    // vide côté back) → le badge promettait un format jamais servi. À réintroduire le jour où
    // l'export existe (la plomberie `r.excel`/bouton Excel de LigneDoc reste en place).
    key: 'bilan', nom: 'Bilan', kind: 'parcelle', formats: ['PDF'],
    desc: 'Charge foncière, coûts, CA et marge, avec vos propres ratios. Prix connu, ou prix maximum du terrain pour votre marge.',
    cta: 'Générer le bilan',
    explication: 'Se calcule sur les données de la fiche et vos ratios.',
  },
  {
    key: 'apporteur', nom: 'Apporteur', kind: 'parcelle', formats: ['PDF'],
    desc: 'Présenter un terrain à un acheteur en une page : plan, faits, dernière vente, contact.',
    cta: 'Générer l’apporteur',
    explication: 'Une page depuis la fiche.',
  },
  {
    key: 'pre-dossier', nom: 'Pré-dossier PC', kind: 'parcelle', formats: ['PDF'],
    desc: 'Ce que le PLU permet et exige ici, l’enveloppe réglementaire et la liste des pièces à joindre.',
    cta: 'Générer le pré-dossier PC',
    explication: 'Règles du PLU, enveloppe réglementaire, pièces à joindre.',
  },
  {
    key: 'gabarit', nom: 'Gabarit', kind: 'parcelle', formats: ['PDF'],
    desc: 'Zone d’implantation, plafond d’emprise, hauteur : le plan, les règles appliquées et celles non intégrées.',
    cta: 'Générer le gabarit',
    explication: 'Le plan et les règles, depuis l’outil Gabarit. Absent si le calcul est incomplet.',
  },
  // RECETTE-OUTILS-1 (point 50) — carte « Comparables DVF » (jamais faite, `bientot`) RETIRÉE du catalogue.
  {
    key: 'comparatif', nom: 'Comparatif', kind: 'multi', formats: ['PDF'],
    desc: 'Deux ou trois parcelles côte à côte sur les 19 lignes de Comparer, en page paysage.',
    cta: 'Générer le comparatif',
    explication: '',   // RECETTE-OUTILS-2 (R8) — « Les 19 lignes de Comparer, côte à côte. » retirée.
  },
  {
    key: 'etude-zone', nom: 'Étude de zone', kind: 'zone', formats: ['PDF'],
    desc: 'Population, économie, immobilier, foncier, contraintes, équipements, dynamique — autour d’une parcelle, dans le rayon choisi.',
    cta: 'Générer l’étude de zone',
    explication: 'Les 7 sections et la carte du périmètre.',
  },
  {
    // IMPLANTATION-4 (LOT A) — 9e carte : l'Étude de faisabilité a QUITTÉ les Outils, elle vit ICI. La
    // carte n'exporte plus un PDF « par défaut » : elle OUVRE l'écran d'étude complet (configuration,
    // scénarios A/B/C, plan masse DESSINÉ, hypothèses), sur le modèle du Bilan — on génère le PDF DEPUIS
    // l'écran, une fois le scénario choisi. Même composant (M22), même API (POST /modules/etude).
    key: 'etude-faisabilite', nom: 'Étude de faisabilité', kind: 'parcelle', formats: ['PDF'],
    desc: 'Scénarios d’implantation collectif : fourchette de logements, plan masse dessiné, contrôles des règles du PLU — pré-faisabilité.',
    cta: 'Ouvrir l’étude de faisabilité',
    explication: 'Ouvre l’écran d’étude : configuration, scénarios A/B/C, plan masse, puis « Générer le PDF ».',
  },
  {
    // ANNONCE-3 — miroir de l'outil « Analyser une annonce » : une adresse (rapport parcelle) OU un
    // lien d'annonce Leboncoin (rapport commune). Le PDF Docs est identique à celui de l'outil.
    // RECETTE-4 — nom affiché « Estimer un bien » (clé/kind internes inchangés).
    key: 'analyse-annonce', nom: 'Estimer un bien', kind: 'annonce', formats: ['PDF'],
    desc: 'Une adresse ou un lien d’annonce : LABUSE croise le bien avec le marché et le foncier.',
    cta: 'Générer l’estimation',
    explication: 'Une adresse → rapport parcelle (tuiles, prix, foncier) ; un lien → rapport commune.',
  },
]
