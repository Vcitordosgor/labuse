// Registre des modules outils — « filtres savants ».
// M82 #DA (M61) : le mauve est RÉSERVÉ à l'IA. La couleur des outils passe au VERT (--mint) : l'action,
// pas l'IA. Les noms d'export restent (VIOLET/VIOLET_DIM = ~120 usages) mais pointent le vert — point
// unique de bascule. Ce constant est outils-only (page Outils + un bloc fiche non-IA) ; le Copilote,
// lui, garde le mauve (classes Tailwind cp-violet, indépendantes de ce token).
import { TOKENS } from '../../lib/tokens'

export const VIOLET = TOKENS.mint
export const VIOLET_DIM = TOKENS.vizGreenDeep

// Les codes M01…M22 restent EN INTERNE (`num`, logs/URL/QA), jamais affichés. Chaque outil porte un
// titre clair + une phrase de bénéfice, un GROUPE d'intention et un flag `phare`.
// M82 (tri validé Vic) — CINQ groupes dans l'ordre du geste client : Trouver · Instruire · Agir ·
// Comprendre le marché · Suivre le temps. « Trouver » = partir sans cible (repérage parcellaire) ;
// « Instruire » = jauger CE terrain / ce projet ; « Agir » = préparer et lancer l'approche ;
// « Comprendre le marché » = lectures de territoire (prix, rythmes, prospective) ; « Suivre le temps » =
// évolution et veille. (Matching promoteurs retiré en M82.)

export type OutilGroup = 'trouver' | 'instruire' | 'agir' | 'marche' | 'temps'

export interface ModuleDef {
  key: string
  num: string          // code interne (M01…M22) — jamais affiché, gardé pour logs/URL/QA
  label: string
  desc: string         // bénéfice, orienté « pourquoi je paie »
  group: OutilGroup
  phare?: boolean      // outil à forte valeur → mis en avant
}

//: les 5 intentions, dans l'ordre du geste (affichage). Le client comprend en 5 s ce qui sert.
export const GROUPS: { key: OutilGroup; label: string; hint: string }[] = [
  { key: 'trouver', label: 'Trouver', hint: 'repérer le foncier à potentiel, sans cible au départ' },
  { key: 'instruire', label: 'Instruire', hint: 'jauger CE terrain, ce projet' },
  { key: 'agir', label: 'Agir', hint: 'préparer et lancer l’approche' },
  { key: 'marche', label: 'Comprendre le marché', hint: 'prix, rythmes, lecture de territoire' },
  { key: 'temps', label: 'Suivre le temps', hint: 'l’évolution, la veille' },
]

export const MODULES: ModuleDef[] = [
  // ── Trouver — repérer le foncier, sans cible au départ ──
  { key: 'scoring-v2', num: 'M25', group: 'trouver', phare: true,
    label: 'Radar des ventes', desc: 'Probabilité de vente sous 1 an — brûlantes, potentiel long terme, tête de classement' },
  { key: 'division', num: 'M01', group: 'trouver', phare: true,
    label: 'Division parcellaire', desc: 'Repérez les grands terrains où détacher un lot à bâtir' },
  { key: 'fantome', num: 'M07', group: 'trouver', phare: true,
    label: 'Foncier fantôme', desc: 'Le constructible verrouillé que les autres ne voient pas' },
  { key: 'bailleur', num: 'M06', group: 'trouver',
    label: 'Mode bailleur', desc: 'Repérez le foncier taillé pour le logement social — quartiers prioritaires, TVA réduite, leviers du bailleur' },

  // ── Instruire — jauger CE terrain, ce projet ──
  { key: 'programme', num: 'M22', group: 'instruire', phare: true,
    label: 'Faisabilité', desc: 'Ce qu’une parcelle peut accueillir, ou par critères où poser un programme' },
  { key: 'scoreur-adresse', num: 'O2', group: 'instruire', phare: true,
    label: 'Scorer une adresse', desc: 'Collez l’adresse d’un bien à vendre — seconde opinion avant d’offrir' },
  { key: 'calculette-fonciere', num: 'M23', group: 'instruire',
    label: 'Calculette foncière', desc: 'Ce qu’un terrain peut supporter selon vos hypothèses de coût et de marge' },
  { key: 'duediligence', num: 'M10', group: 'instruire', phare: true,
    label: 'Contrôle avant achat', desc: 'Passez une liste de parcelles au crible avant d’acheter' },
  { key: 'verif-procedure', num: 'O11', group: 'instruire',
    label: 'Vérif procédure PLU', desc: 'Un IDU — la commune est-elle en procédure PLU (sursis à statuer possible, veille AU) ?' },
  { key: 'plu-annuaire', num: 'O13', group: 'instruire',
    label: 'Annuaire PLU', desc: 'Cherchez dans le règlement des communes — verbatim sourcé (article, page, lien), jamais un résumé' },
  { key: 'o5-servitudes', num: 'O5', group: 'instruire',
    label: 'Servitudes invisibles', desc: 'Les contraintes dormantes d’une parcelle — et ce que la base ne couvre pas' },
  { key: 'comparer', num: 'A8', group: 'instruire',
    label: 'Comparer des parcelles', desc: 'Mettez 2 à 3 parcelles côte à côte — verdict, contraintes, capacité, charge foncière, marché' },
  { key: 'assemblage', num: 'M16', group: 'instruire', phare: true,
    label: 'Assemblage', desc: 'Fusionnez des parcelles contiguës en une assiette de projet' },

  // ── Agir — préparer et lancer l'approche ──
  { key: 'courriers', num: 'M09', group: 'agir',
    label: 'Courrier propriétaire', desc: 'Générez vos courriers d’approche, prêts à télécharger et envoyer' },
  { key: 'patrimoine', num: 'M02', group: 'agir', phare: true,
    label: 'Scan patrimoine', desc: 'Un nom de propriétaire, et TOUT son foncier ressort d’un coup — repérez les gros détenteurs à approcher' },

  // ── Comprendre le marché — prix, rythmes, lecture de territoire ──
  { key: 'marche', num: 'MU1', group: 'marche', phare: true,
    label: 'Marché', desc: 'Le marché d’une commune, 9 lignes sourcées et datées : prix ancien, terrain nu par zone (U/AU), neuf, tendance, liquidité, offre engagée et potentielle, pression DPE, loyer' },
  { key: 'o6-comparateur', num: 'O6', group: 'marche', phare: true,
    label: 'Comparateur de communes', desc: 'Où investir : 24 communes, indicateurs sourcés, composite réglable' },
  { key: 'barometre', num: 'M18', group: 'marche',
    label: 'Baromètre foncier', desc: 'Un état du marché foncier prêt à distribuer (PDF)' },
  { key: 'permis', num: 'M03', group: 'marche',
    label: 'Radar permis', desc: 'Qui construit quoi, commune par commune (Sitadel)' },
  { key: 'velocite', num: 'M05', group: 'marche',
    label: 'Vélocité admin', desc: 'Comparez les rythmes d’instruction des 24 communes' },
  { key: 'promesses', num: 'M04', group: 'marche',
    label: 'Promesses mortes', desc: 'Les permis anciens jamais sortis de terre' },
  { key: 'zan', num: 'M17', group: 'marche',
    label: 'Simulateur ZAN', desc: 'La contrainte d’artificialisation, commune par commune' },
  { key: 'renouvellement', num: 'MR1', group: 'marche',
    label: 'Renouvellement', desc: 'Le potentiel de renouvellement urbain d’un territoire : parcelles occupées en zone constructible à capacité restante (densifier, diviser, reconstruire)' },
  { key: 'o9-rarete', num: 'O9', group: 'marche',
    label: 'Rareté du foncier', desc: 'Où le foncier se raréfie : combien de constructible reste-t-il par commune, et pour combien de temps (horizon ZAN)' },
  { key: 'simulplu', num: 'M15', group: 'marche',
    label: 'Changement PLU', desc: 'Prospective de territoire — « et si cette zone passait constructible ? »' },

  // ── Suivre le temps — l'évolution, la veille ──
  { key: 'o10-bascules', num: 'O10', group: 'temps',
    label: 'Quoi de neuf', desc: 'Le quoi-de-neuf daté — bascules, événements du secteur' },
  { key: 'o7-carnet', num: 'O7', group: 'temps',
    label: 'Suivi de secteur', desc: 'Un secteur suivi comme un portefeuille — stock, prix, permis, signaux' },
  { key: 'temps', num: 'M08', group: 'temps',
    label: 'Remonter le temps', desc: 'Comparez une année ancienne et aujourd’hui pour lire la mutation d’un terrain' },
]
