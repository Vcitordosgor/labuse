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
  // §2 (Vic 23/08/2026) — MENU PLAT. Les catégories (Trouver/Instruire/Agir/…) et la distinction
  // « phare » (étoile) DISPARAISSENT de l'affichage : Rail rend la liste dans CET ordre, gabarit unique,
  // barre verticale gauche pour CHAQUE outil. L'ORDRE ci-dessous EST l'ordre d'usage probable du
  // promoteur (pas l'alphabet) :
  //   1. instruire le bien qu'on regarde — Étudier → Faisabilité → Risques → PLU → Comparer → Assemblage ;
  //   2. sourcer un propriétaire puis l'approcher — Scan patrimoine → Courrier ;
  //   3. lire le marché — Communes → Permis → Densifier ;
  //   4. l'analyse ponctuelle (rare) en dernier — Remonter le temps.
  // Les champs `group`/`phare` RESTENT en donnée (internes, inertes à l'affichage depuis §2) ; les clés
  // `hidden` sont des alias sans carte.

  // ── 1. Instruire le bien qu'on regarde ──
  // FUSION (Vic 21/08/2026) — scoreur d'adresse (O2) + calculette foncière (M23) = « Étudier un bien »,
  // deux entrées (adresse OU parcelle), un moteur. La clé M23 est ALIASÉE (hidden : résout la porte
  // fiche/copilote sans carte en double, jamais un 404).
  { key: 'scoreur-adresse', num: 'O2', group: 'instruire', phare: true,
    label: 'Étudier un bien', desc: 'Une adresse ou une parcelle — le constat (verdict + charge calibrée), puis vos hypothèses' },
  { key: 'calculette-fonciere', num: 'M23', group: 'instruire', hidden: true,
    label: 'Étudier un bien', desc: 'Une adresse ou une parcelle — le constat (verdict + charge calibrée), puis vos hypothèses' },
  { key: 'programme', num: 'M22', group: 'instruire', phare: true,
    label: 'Faisabilité', desc: 'Ce qu’une parcelle peut accueillir, ou par critères où poser un programme' },
  // K3 (rattrapage KelFoncier) — calculette « Taxe d'aménagement » : assiette, part communale, part
  // départementale, détail ligne par ligne. Barème et taux servis par le backend (jamais en dur).
  { key: 'taxe-amenagement', num: 'K3', group: 'instruire',
    label: 'Taxe d\'aménagement', desc: 'Estimez la taxe d\'aménagement d\'un projet — assiette, part communale, part départementale, détaillé ligne par ligne' },
  // RADAR P3 — l'écran client du Radar (pige d'annonces de Vic) : biens en vente rattachés à la
  // parcelle, filtres + carte (rattachés seuls) + listing (tout). Des faits + un lien, jamais l'annonce.
  { key: 'radar', num: 'R1', group: 'marche',
    label: 'Radar', desc: 'Les biens en vente repérés sur les portails, rattachés à leur parcelle — filtres, carte, et le lien vers l\'annonce source' },
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

  // ── 2. Sourcer un propriétaire, puis l'approcher ──
  { key: 'patrimoine', num: 'M02', group: 'agir', phare: true,
    label: 'Scan patrimoine', desc: 'Un nom de propriétaire, et TOUT son foncier ressort d’un coup — repérez les gros détenteurs à approcher' },
  { key: 'courriers', num: 'M09', group: 'agir',
    label: 'Courrier propriétaire', desc: 'Générez vos courriers d’approche, prêts à télécharger et envoyer' },
  // Prospection solaire (V1 restitution) — sert la donnée solaire DÉJÀ en base (parcel_solar/PVGIS,
  // pente RGE ALTI, piscine ortho, proba occupant), gelée au 11/07/2026 ; export CSV de démarchage.
  { key: 'prospection-solaire', num: 'M26', group: 'agir',
    label: 'Prospection solaire', desc: 'Les parcelles au meilleur potentiel solaire (productible, orientation, toiture) — pour démarcher l’installation photovoltaïque ; export CSV' },

  // ── 3. Lire le marché et le territoire ──
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
  // §3 (Vic 23/08/2026) — FUSION « Radar permis » (M03) + « Permis au point mort » (M04) en UN outil
  // « Permis » : le radar est l'entrée (carte + points cliquables + fiche + recherche rue/numéro) ;
  // « au point mort » devient un FILTRE (PC anciens sans achèvement, rendus en points cliquables, plus
  // en surlignage de parcelle). Même patron que les fusions précédentes : la clé `promesses` reste
  // (URL/QA/concept-route inchangés) mais ALIASÉE (hidden) → pas de 2ᵉ carte au menu ; elle ouvre le
  // filtre pré-actif.
  { key: 'permis', num: 'M03', group: 'marche',
    label: 'Permis', desc: 'Qui construit quoi, commune par commune (Sitadel) — la carte des permis, cliquables ; filtre « Au point mort » pour les PC accordés jamais réalisés' },
  { key: 'promesses', num: 'M04', group: 'marche', hidden: true,
    label: 'Permis', desc: 'Le « point mort » (PC accordés jamais réalisés) est un filtre de l’outil Permis' },
  // §5 — renommé « Densifier l'existant » côté client ; clé interne `renouvellement` INCHANGÉE
  // (URL, QA, tests, endpoint, table). Même patron que Promesses mortes → Permis au point mort.
  { key: 'renouvellement', num: 'MR1', group: 'marche',
    label: 'Densifier l’existant', desc: 'Le bâti qui peut porter davantage — extensions, surélévations : parcelles déjà occupées en zone constructible à capacité résiduelle réelle' },

  // ── 4. Analyse ponctuelle (usage rare) ──
  { key: 'temps', num: 'M08', group: 'temps',
    label: 'Remonter le temps', desc: 'Comparez une année ancienne et aujourd’hui pour lire la mutation d’un terrain' },

  // ── RETIRÉS DU PRODUIT (dormants — composants, endpoints et tests conservés au dépôt) ──
  // M137-K : « Radar des ventes » (M25 — recouvre l'Analyse LABUSE). · M137-N : « Foncier fantôme » (M07,
  // nom non fidèle) & « Mode bailleur » (M06). · M129-C : « division ». · 21/08/2026 : « Simulateur ZAN »
  // (M17 — enveloppe reprise dans Communes), « Quoi de neuf » (O10 — endpoint /events VIVANT : cloche +
  // point du jour), « Suivi de secteur » (O7 — vues reprises ailleurs). · M137-P : « Changement PLU »
  // (M15) rejoint l'outil PLU unifié. Concept-routes Copilote des dormants retirées (answering.py).
]
