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
  descSmall?: boolean  // RETOURS-7 Z3 — la desc dépasse la largeur du panneau même en nowrap : on réduit
                       // la police d'un point (10,5 → 9,5 px) plutôt que d'ellipser. Mesuré, pas deviné.
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
  // RETOURS-3 R11 — descriptions réécrites au mot (une phrase, droit au but). Vic 31/08.
  // RETOURS-3 R5 — FUSION « Étudier un bien » × « Mon secteur » : la desc prend la formule R5 (adresse →
  // secteur ; parcelle → étude complète). « Mon secteur » passe hidden (redirection interne conservée).
  // RETOURS-7 Z3 — descriptions raccourcies pour tenir sur UNE ligne à la largeur du panneau (320px).
  { key: 'scoreur-adresse', num: 'O2', group: 'instruire', phare: true,
    label: 'Étudier un bien', desc: 'Le secteur, puis l’étude complète du bien.' },
  { key: 'calculette-fonciere', num: 'M23', group: 'instruire', hidden: true,
    label: 'Étudier un bien', desc: 'Le secteur, puis l’étude complète du bien.' },
  { key: 'programme', num: 'M22', group: 'instruire', phare: true,
    label: 'Faisabilité', desc: 'Ce que le PLU laisse construire sur la parcelle.' },
  // K3 (rattrapage KelFoncier) — calculette « Taxe d'aménagement » : assiette, part communale, part
  // départementale, détail ligne par ligne. Barème et taux servis par le backend (jamais en dur).
  { key: 'taxe-amenagement', num: 'K3', group: 'instruire',
    label: 'Taxe d\'aménagement', desc: 'La taxe du projet, calculée d\'avance.' },
  // RADAR-CATÉGORIE (T1, Vic) — le Radar a QUITTÉ le menu Outils : c'est une CATÉGORIE de premier
  // niveau (rail, plein écran, view 'radar'). Plus d'entrée 'radar' ici. Back pige/* réutilisé tel quel.
  // M137-T — « Contrôle avant achat » (M10) + « Servitudes invisibles » (O5) fusionnés en UN outil
  // « Risques », deux entrées (une parcelle en détail / un lot au crible). Le nom ne promet pas
  // l'exhaustivité (l'outil dit ce que la base ne couvre pas) — ni « contrôle complet » ni « due diligence ».
  { key: 'risques', num: 'M10', group: 'instruire', phare: true,
    label: 'Pièges et risques', desc: 'Ce qui peut bloquer le projet, avant d\'acheter.' },
  // M137-P/Q — outil PLU UNIFIÉ : Annuaire PLU (O13) + « Procédure & changement » (M137-Q : Vérif
  // procédure O11 + Changement PLU M15 fusionnés, communes en procédure reliées à leur simulation).
  // Le hub (Plu.tsx) monte 2 voies ; les composants existants sont réutilisés inchangés.
  { key: 'plu', num: 'O13', group: 'instruire', phare: true,
    label: 'PLU', desc: 'Chaque zone, son règlement, articles cités.' },
  { key: 'comparer', num: 'A8', group: 'instruire',
    label: 'Comparer des parcelles', desc: 'Des parcelles côte à côte, critère par critère.' },
  { key: 'assemblage', num: 'M16', group: 'instruire', phare: true,
    label: 'Assemblage', desc: 'Le potentiel de parcelles voisines réunies.' },

  // ── 2. Sourcer un propriétaire, puis l'approcher ──
  // RETOURS-4 S7 — Scan patrimoine ABSORBE Veille promoteurs (2 onglets : possède / construit).
  { key: 'patrimoine', num: 'M02', group: 'agir', phare: true,
    label: 'Scan patrimoine', desc: 'Ce qu\'un propriétaire possède et construit.' },
  { key: 'courriers', num: 'M09', group: 'agir',
    label: 'Courrier propriétaire', desc: 'Écrivez au propriétaire, LABUSE envoie.' },
  // Prospection solaire (V1 restitution) — sert la donnée solaire DÉJÀ en base (parcel_solar/PVGIS,
  // pente RGE ALTI, piscine ortho, proba occupant), gelée au 11/07/2026 ; export CSV de démarchage.
  { key: 'prospection-solaire', num: 'M26', group: 'agir',
    label: 'Prospection solaire', desc: 'Les toits bien exposés, les piscines à équiper.' },

  // ── 3. Lire le marché et le territoire ──
  // M137-Z — outil « Communes » : fusion de Marché (MU1) · Comparateur (O6) · Vélocité (M05) ·
  // Rareté (O9). Entrée = la table des 24 communes ; clic → fiche commune (tous ses indicateurs) +
  // « Voir ses parcelles → ». Les 4 clés absorbées sont retirées du registre (composants au dépôt,
  // endpoints /comparateur-communes, /moteurs/marche, /modules/velocite, /pipeline-rarete servis).
  { key: 'communes', num: 'O6', group: 'marche', phare: true, descSmall: true,
    label: 'Communes', desc: 'Les 24 communes en chiffres : marché, rareté, rythme.' },
  // SECTEUR-1 (S1) — « Mon secteur » : les prix DU SECTEUR autour d'une parcelle. Même moteur que
  // « Marché et secteur » de la fiche + la médiane locale de FICHE-COMMUNE-2 C5.
  // RETOURS-3 R5 — « Mon secteur » RETIRÉ du menu (hidden) : fusionné dans « Étudier un bien » (bloc secteur
  // dès l'adresse). La clé reste résolvante (redirection interne conservée : deep-link/copilote historique).
  { key: 'mon-secteur', num: 'S1', group: 'marche', hidden: true,
    label: 'Mon secteur', desc: 'Les prix du secteur sont désormais dans « Étudier un bien » (dès l’adresse).' },
  // SECTEUR-1 (S3) — « Veille promoteurs » : permis déposés par promoteurs / bailleurs / SEM + leurs
  // acquisitions foncières (Scan patrimoine, même SIREN). Comptes SQL, millésime Sitadel affiché.
  // RETOURS-4 S7 — RETIRÉ du menu (hidden) : fusionné dans « Scan patrimoine » (onglet « Ce qu'ils
  // construisent »). Clé résolvante conservée (redirection interne → ScanPatrimoine defaultTab construit).
  { key: 'veille-promoteurs', num: 'S3', group: 'marche', hidden: true,
    label: 'Veille promoteurs', desc: 'Les opérations sont désormais dans « Scan patrimoine » (onglet « Ce qu\'ils construisent »).' },
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
  { key: 'permis', num: 'M03', group: 'marche', descSmall: true,
    label: 'Permis', desc: 'Qui construit quoi, commune par commune — et les permis au point mort.' },
  { key: 'promesses', num: 'M04', group: 'marche', hidden: true,
    label: 'Permis', desc: 'Le « point mort » (PC accordés jamais réalisés) est un filtre de l’outil Permis' },
  // §5 — renommé « Densifier l'existant » côté client ; clé interne `renouvellement` INCHANGÉE
  // (URL, QA, tests, endpoint, table). Même patron que Promesses mortes → Permis au point mort.
  { key: 'renouvellement', num: 'MR1', group: 'marche',
    label: 'Densifier l’existant', desc: 'Le bâti en zone U qui peut porter davantage.' },
  // ÉTUDE DE ZONE Z4 — la chalandise : une zone atteignable (isochrone IGN), qui y vit, qui y travaille,
  // quels concurrents (SIRENE) ; le même moteur alimente le tiroir « Autour de cette parcelle » (fiche).
  { key: 'etude-zone', num: 'M27', group: 'marche', descSmall: true,
    label: 'Étude de zone', desc: 'Habitants, emplois, concurrents : la zone autour d\'un point.' },

  // ── 4. Analyse ponctuelle (usage rare) ──
  { key: 'temps', num: 'M08', group: 'temps',
    label: 'Remonter le temps', desc: 'La parcelle vue du ciel, année après année.' },

  // ── RETIRÉS DU PRODUIT (dormants — composants, endpoints et tests conservés au dépôt) ──
  // M137-K : « Radar des ventes » (M25 — recouvre l'Analyse LABUSE). · M137-N : « Foncier fantôme » (M07,
  // nom non fidèle) & « Mode bailleur » (M06). · M129-C : « division ». · 21/08/2026 : « Simulateur ZAN »
  // (M17 — enveloppe reprise dans Communes), « Quoi de neuf » (O10 — endpoint /events VIVANT : cloche +
  // point du jour), « Suivi de secteur » (O7 — vues reprises ailleurs). · M137-P : « Changement PLU »
  // (M15) rejoint l'outil PLU unifié. Concept-routes Copilote des dormants retirées (answering.py).
]
