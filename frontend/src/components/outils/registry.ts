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
  hidden?: boolean     // clé RÉSOLVANTE (en-tête + composant) mais PAS de carte au menu — pour une clé
                       // ALIASÉE vers un outil fusionné (ex. M23 calculette → « Étudier un bien »),
                       // qu'une porte/deep-link/copilote ouvre sans jamais 404, sans doublonner la carte.
}

//: les 5 intentions, dans l'ordre du geste (affichage). menu-sous-titres — les sous-titres (hint) sont
//: retirés du menu : seuls les TITRES de groupe restent. (Le groupe « trouver » est VIDE après les
//: retraits de la semaine — Rail.tsx ne rend pas un groupe sans outil, il n'apparaît donc pas.)
export const GROUPS: { key: OutilGroup; label: string }[] = [
  { key: 'trouver', label: 'Trouver' },
  { key: 'instruire', label: 'Instruire' },
  { key: 'agir', label: 'Agir' },
  { key: 'marche', label: 'Comprendre le marché' },
  { key: 'temps', label: 'Suivre le temps' },
]

export const MODULES: ModuleDef[] = [
  // ── Trouver — repérer le foncier, sans cible au départ ──
  // M137-K (Vic 20/08/2026) : outil « Radar des ventes » (scoring-v2, M25) retiré du produit
  // (DORMANT) — recouvre l'Analyse LABUSE (même table parcel_p_score_v2, même run, même classement),
  // sans carte ni filtres. Composant + endpoints /v2/* + tests conservés au dépôt.
  // M137-N (Vic 20/08/2026) : outil « Foncier fantôme » (fantome, M07) retiré du produit (DORMANT) —
  // nom non fidèle au contenu (74 % successions et structures collectives, pas des sociétés fantômes),
  // levier « dirigeant inactif » à 0. Le signal succession sera repris en facette. Composant M06/M07 +
  // endpoints /modules/fantome & /modules/bailleur + tests conservés au dépôt.
  // M137-N (Vic 20/08/2026) : outil « Mode bailleur » (bailleur, M06) retiré du produit (DORMANT).
  // M129-C (Vic 19/08/2026) : outil « division » retiré du produit (dormant) — code au dépôt.

  // ── Instruire — jauger CE terrain, ce projet ──
  { key: 'programme', num: 'M22', group: 'instruire', phare: true,
    label: 'Faisabilité', desc: 'Ce qu’une parcelle peut accueillir, ou par critères où poser un programme' },
  // FUSION (Vic 21/08/2026) — scoreur d'adresse (O2) + calculette foncière (M23) = « Étudier un bien »,
  // deux entrées (adresse OU parcelle), un moteur. Le créneau PHARE O2 est conservé (clé inchangée) ;
  // la clé M23 est ALIASÉE (hidden : résout la porte fiche/copilote sans carte en double, jamais un 404).
  { key: 'scoreur-adresse', num: 'O2', group: 'instruire', phare: true,
    label: 'Étudier un bien', desc: 'Une adresse ou une parcelle — le constat (verdict + charge calibrée), puis vos hypothèses' },
  { key: 'calculette-fonciere', num: 'M23', group: 'instruire', hidden: true,
    label: 'Étudier un bien', desc: 'Une adresse ou une parcelle — le constat (verdict + charge calibrée), puis vos hypothèses' },
  // M137-T — « Contrôle avant achat » (M10) + « Servitudes invisibles » (O5) fusionnés en UN outil
  // « Risques », deux entrées (une parcelle en détail / un lot au crible). Le nom ne promet pas
  // l'exhaustivité (l'outil dit ce que la base ne couvre pas) — ni « contrôle complet » ni « due diligence ».
  { key: 'risques', num: 'M10', group: 'instruire', phare: true,
    label: 'Pièges et risques', desc: 'Ce qui cloche sur une parcelle — servitudes dormantes, risques, propriétaire ; une parcelle en détail ou un lot au crible. Dit aussi ce que la base ne couvre pas' },
  // M137-P/Q — outil PLU UNIFIÉ : Annuaire PLU (O13) + « Procédure & changement » (M137-Q : Vérif
  // procédure O11 + Changement PLU M15 fusionnés, communes en procédure reliées à leur simulation).
  // Le hub (Plu.tsx) monte 2 voies ; les composants existants sont réutilisés inchangés.
  { key: 'plu', num: 'O13', group: 'instruire', phare: true,
    label: 'PLU', desc: 'Le PLU des 24 communes : consulter le règlement, vérifier une procédure en cours, simuler une bascule de zone' },
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
  // M137-Z — outil « Communes » : fusion de Marché (MU1) · Comparateur (O6) · Vélocité (M05) ·
  // Rareté (O9). Entrée = la table des 24 communes ; clic → fiche commune (tous ses indicateurs) +
  // « Voir ses parcelles → ». Les 4 clés absorbées sont retirées du registre (composants au dépôt,
  // endpoints /comparateur-communes, /moteurs/marche, /modules/velocite, /pipeline-rarete servis).
  { key: 'communes', num: 'O6', group: 'marche', phare: true,
    label: 'Communes', desc: 'Les 24 communes comparées, puis la fiche de chacune : marché (9 lignes sourcées), rareté et horizon ZAN, rythme d’instruction — et un saut vers ses parcelles' },
  // L'outil « Baromètre foncier » a QUITTÉ le menu : l'évolution du marché (île, 8 trimestres) + le
  // Rapport PDF vivent désormais dans l'onglet « Évolution » de Communes. Clé ALIASÉE (hidden) →
  // Communes, aucun lien mort (deep-link/copilote historique). Composant M18 réutilisé par l'onglet.
  { key: 'barometre', num: 'M18', group: 'marche', hidden: true,
    label: 'Communes', desc: 'L’évolution du marché et le Rapport PDF sont dans l’onglet « Évolution » de Communes' },
  { key: 'permis', num: 'M03', group: 'marche',
    label: 'Radar permis', desc: 'Qui construit quoi, commune par commune (Sitadel)' },
  // audit-promesses (add 2) — renommé « Promesses mortes » → « Permis au point mort » : le calcul dit
  // « au point mort » (accordé, sans achèvement, parcelle non bâtie), pas la caducité juridique certaine.
  // La clé reste `promesses` (URL/QA/concept-route inchangés). Défaut passé à 36 mois (caducité PC).
  { key: 'promesses', num: 'M04', group: 'marche',
    label: 'Permis au point mort', desc: 'Les PC accordés mais jamais réalisés — sans achèvement, parcelle toujours non bâtie (à partir de 3 ans, la caducité légale)' },
  // Retiré du produit le 21/08/2026 (DORMANT) : outil « Simulateur ZAN » (zan, M17). Mesuré : ses 3
  // briques étaient soit MORTES (liste « parcelles alignées ZAN » = filtre ocs_ge weight>0, jamais >0 → 0),
  // soit des DOUBLONS (signal parcelle déjà sur la fiche ; enveloppe communale = même formule que la
  // section « Rareté & ZAN » de l'outil Communes, rarete.py). L'enveloppe (dont le budget en %) vit
  // désormais dans Communes. Composant M17 + endpoints /moteurs/zan* + tests conservés au dépôt.
  { key: 'renouvellement', num: 'MR1', group: 'marche',
    label: 'Renouvellement', desc: 'Le potentiel de renouvellement urbain d’un territoire : parcelles occupées en zone constructible à capacité restante (densifier, diviser, reconstruire)' },
  // M137-P — « Changement PLU » (M15/simulplu) a rejoint l'outil PLU unifié (groupe Instruire).

  // ── Suivre le temps — l'évolution, la veille ──
  // Retiré du produit le 21/08/2026 (DORMANT) : outil « Quoi de neuf » (o10-bascules, O10) — plus câblé
  // au menu (registry + COMPONENTS). Le composant O10Bascules reste au dépôt (exporté, cf. blocB.tsx) ;
  // son unique source, l'endpoint /events, reste VIVANT (consommé par la cloche de notifications + le
  // « point du jour »), donc rien d'orphelin. Concept-route Copilote retirée (answering.py).
  // Retiré du produit le 21/08/2026 (DORMANT) : outil « Suivi de secteur » (o7-carnet, O7). Mesuré :
  // son nom promettait un suivi qu'il ne faisait pas (consult-only ; le VRAI suivi = la Veille), 0 état,
  // 0 usage, plafond muet 30/478. Sa vue existe en grande partie ailleurs (prix secteur → fiche parcelle ;
  // ZAN → Communes ; permis → radar permis) ; SEUL le compte d'opportunités AGRÉGÉ par section n'a pas
  // d'autre foyer (visible à l'œil sur la carte). Composant O7Carnet + endpoints /carnet-secteur + tests
  // conservés au dépôt. Concept-route Copilote retirée (answering.py).
  { key: 'temps', num: 'M08', group: 'temps',
    label: 'Remonter le temps', desc: 'Comparez une année ancienne et aujourd’hui pour lire la mutation d’un terrain' },
]
