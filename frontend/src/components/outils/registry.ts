// Registre des modules outils — « filtres savants ». Couleur module : VIOLET (doctrine).
import { TOKENS } from '../../lib/tokens'

export const VIOLET = TOKENS.violet
export const VIOLET_DIM = TOKENS.violetDim

// P3 (revue Vic n°3) — CURATION. Les codes M01…M22 sont un langage d'ingénieur : ils restent
// EN INTERNE (`num`, utile aux logs/URL/QA) mais ne s'affichent plus. Chaque outil porte un
// titre clair + une phrase de BÉNÉFICE orientée métier (promoteur / bailleur / marchand de
// biens), un GROUPE d'intention et un flag `phare` (les outils à plus forte valeur, mis en
// avant). Regroupement consigné (DERIVATIONS) : Détecter le foncier · Analyser & simuler ·
// Passer à l'action. Aucune perte de fonctionnalité — tous les outils restent ouvrables.

export type OutilGroup = 'detecter' | 'analyser' | 'agir'

export interface ModuleDef {
  key: string
  num: string          // code interne (M01…M22) — jamais affiché, gardé pour logs/URL/QA
  label: string
  desc: string         // bénéfice métier, orienté « pourquoi je paie »
  group: OutilGroup
  phare?: boolean      // outil à forte valeur → mis en avant
}

//: les 3 intentions métier (ordre = priorité d'affichage ; « Détecter » d'abord = l'argument)
export const GROUPS: { key: OutilGroup; label: string; hint: string }[] = [
  { key: 'detecter', label: 'Détecter le foncier', hint: 'trouver les parcelles à potentiel' },
  { key: 'analyser', label: 'Analyser & simuler', hint: 'jauger une parcelle, un secteur' },
  { key: 'agir', label: 'Passer à l’action', hint: 'contacter, instruire, distribuer' },
]

export const MODULES: ModuleDef[] = [
  // ── Détecter le foncier ──
  { key: 'scoring-v2', num: 'M25', group: 'detecter', phare: true,
    label: 'Scoring v2 (P)', desc: 'Probabilité de mutation à 12 mois — brûlantes v2, réserve foncière, top P' },
  { key: 'programme', num: 'M22', group: 'detecter', phare: true,
    label: 'Faisabilité programme', desc: 'Décrivez votre programme, LABUSE trouve où le poser' },
  { key: 'division', num: 'M01', group: 'detecter', phare: true,
    label: 'Division parcellaire', desc: 'Repérez les grands terrains où détacher un lot à bâtir' },
  { key: 'fantome', num: 'M07', group: 'detecter', phare: true,
    label: 'Foncier fantôme', desc: 'Le constructible verrouillé que les autres ne voient pas' },
  { key: 'patrimoine', num: 'M02', group: 'detecter', phare: true,
    label: 'Scan patrimoine', desc: 'Tout le foncier d’un propriétaire en une recherche' },
  { key: 'bailleur', num: 'M06', group: 'detecter',
    label: 'Mode bailleur', desc: 'Le gisement LLS : QPV, TVA réduite, leviers du logement social' },
  { key: 'o9-rarete', num: 'O9', group: 'detecter',
    label: 'Pipeline rareté', desc: 'Où le foncier s’épuise — l’horizon ZAN par commune, en instrument' },
  { key: 'o10-bascules', num: 'O10', group: 'detecter',
    label: 'Bascules datées', desc: 'Le quoi-de-neuf daté du run — bascules, matches, événements' },
  { key: 'matching', num: 'M19', group: 'detecter',
    label: 'Matching promoteurs', desc: 'Enregistrez vos critères, soyez alerté quand ça matche' },
  // ── Analyser & simuler ──
  // M12-D4 : « Scorer une adresse » quitte la barre d'en-tête et rejoint les Outils.
  { key: 'scoreur-adresse', num: 'O2', group: 'analyser', phare: true,
    label: 'Scorer une adresse', desc: 'Collez l’adresse d’un bien à vendre — seconde opinion avant d’offrir' },
  { key: 'o6-comparateur', num: 'O6', group: 'analyser', phare: true,
    label: 'Comparateur de communes', desc: 'Où investir : 24 communes, indicateurs sourcés, composite réglable' },
  { key: 'o5-servitudes', num: 'O5', group: 'analyser',
    label: 'Servitudes invisibles', desc: 'Les contraintes dormantes d’une parcelle — et ce que la base ne couvre pas' },
  { key: 'assemblage', num: 'M16', group: 'analyser', phare: true,
    label: 'Assemblage', desc: 'Fusionnez des parcelles contiguës en une assiette de projet' },
  { key: 'barometre', num: 'M18', group: 'analyser',
    label: 'Baromètre foncier', desc: 'Un état du marché foncier prêt à distribuer (PDF)' },
  { key: 'permis', num: 'M03', group: 'analyser',
    label: 'Radar permis', desc: 'Qui construit quoi, commune par commune (Sitadel)' },
  { key: 'promesses', num: 'M04', group: 'analyser',
    label: 'Promesses mortes', desc: 'Les permis anciens jamais sortis de terre' },
  { key: 'velocite', num: 'M05', group: 'analyser',
    label: 'Vélocité admin', desc: 'Comparez les rythmes d’instruction des 24 communes' },
  { key: 'simulplu', num: 'M15', group: 'analyser',
    label: 'Simulateur PLU', desc: 'Testez « et si cette zone passait constructible ? »' },
  { key: 'zan', num: 'M17', group: 'analyser',
    label: 'Simulateur ZAN', desc: 'La contrainte d’artificialisation, commune par commune' },
  { key: 'temps', num: 'M08', group: 'analyser',
    label: 'Remonter le temps', desc: 'Comparez 1950 et aujourd’hui pour lire la mutation' },
  // ── Passer à l'action ──
  { key: 'o7-carnet', num: 'O7', group: 'agir',
    label: 'Carnet de secteur', desc: 'Un secteur suivi comme un portefeuille — stock, prix, permis, signaux' },
  { key: 'duediligence', num: 'M10', group: 'agir', phare: true,
    label: 'Due diligence', desc: 'Passez une liste de parcelles au crible avant d’acheter' },
  { key: 'courriers', num: 'M09', group: 'agir',
    label: 'Courrier propriétaire', desc: 'Générez vos courriers d’approche par lot' },
]
