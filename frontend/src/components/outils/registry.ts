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
  // RECETTE-1 R18 (Vic 08/09/2026) — MENU PLAT dont l'ORDRE EST FIXÉ par le mandat. Rail rend
  // `MODULES.filter((m) => !m.hidden)` dans CET ordre, gabarit unique :
  //   1 PLU · 2 Permis · 3 Commune · 4 Étudier un bien · 5 Scan patrimoine · 6 Assemblage ·
  //   7 Comparer des parcelles · 8 Pièges et risques · 9 Étude de zone · 10 Remonter le temps ·
  //   11 Faisabilité · 12 Taxe d'aménagement · 13 Prospection solaire · 14 Densifier l'existant ·
  //   15 Blocs fonciers · 16 Successions à venir · 17 Courrier propriétaire.
  // Les champs `group`/`phare` RESTENT en donnée (internes, inertes à l'affichage) ; les clés `hidden`
  // sont des ALIAS sans carte, placées près de l'outil qui les résout (ordre sans effet sur le menu).

  // 1. PLU — M137-P/Q : Annuaire PLU (O13) + « Procédure & changement » unifiés (hub Plu.tsx, 2 voies).
  { key: 'plu', num: 'O13', group: 'instruire', phare: true,
    label: 'PLU', desc: 'Chaque zone, son règlement, articles cités.' },

  // 2. Permis — §3 : Radar permis (M03) + « au point mort » (M04, devenu un filtre ; clé promesses aliasée).
  { key: 'permis', num: 'M03', group: 'marche', descSmall: true,
    label: 'Permis', desc: 'Qui construit quoi, commune par commune — et les permis dormants.' },
  { key: 'promesses', num: 'M04', group: 'marche', hidden: true,
    label: 'Permis', desc: 'Les « dormants » (PC accordés jamais réalisés) sont un filtre de l’outil Permis' },

  // 3. Commune — M137-Z : « Communes » (Marché · Comparateur · Vélocité · Rareté) ; onglet Évolution =
  // Baromètre (M18 aliasé). Entrée = table des 24 communes, clic → fiche commune.
  { key: 'communes', num: 'O6', group: 'marche', phare: true, descSmall: true,
    label: 'Communes', desc: 'Les 24 communes en chiffres : marché, rareté, rythme.' },
  { key: 'barometre', num: 'M18', group: 'marche', hidden: true,
    label: 'Communes', desc: 'L’évolution du marché et le Rapport PDF sont dans l’onglet « Évolution » de Communes' },

  // 4. Étudier un bien — FUSION scoreur d'adresse (O2) + calculette foncière (M23) + Mon secteur (S1).
  // Les clés M23/S1 sont ALIASÉES (hidden : résolvent porte/deep-link/copilote, sans carte en double).
  { key: 'scoreur-adresse', num: 'O2', group: 'instruire', phare: true,
    label: 'Étudier un bien', desc: 'Le secteur, puis l’étude complète du bien.' },
  { key: 'calculette-fonciere', num: 'M23', group: 'instruire', hidden: true,
    label: 'Étudier un bien', desc: 'Le secteur, puis l’étude complète du bien.' },
  { key: 'mon-secteur', num: 'S1', group: 'marche', hidden: true,
    label: 'Mon secteur', desc: 'Les prix du secteur sont désormais dans « Étudier un bien » (dès l’adresse).' },

  // 5. Scan patrimoine — RETOURS-4 S7 : absorbe « Veille promoteurs » (S3 aliasé, onglet « Ce qu'ils construisent »).
  { key: 'patrimoine', num: 'M02', group: 'agir', phare: true,
    label: 'Scan patrimoine', desc: 'Ce qu\'un propriétaire possède et construit.' },
  { key: 'veille-promoteurs', num: 'S3', group: 'marche', hidden: true,
    label: 'Veille promoteurs', desc: 'Les opérations sont désormais dans « Scan patrimoine » (onglet « Ce qu\'ils construisent »).' },

  // 6. Assemblage — le potentiel de parcelles voisines réunies.
  { key: 'assemblage', num: 'M16', group: 'instruire', phare: true,
    label: 'Assemblage', desc: 'Le potentiel de parcelles voisines réunies.' },

  // 7. Comparer des parcelles.
  { key: 'comparer', num: 'A8', group: 'instruire',
    label: 'Comparer des parcelles', desc: 'Des parcelles côte à côte, critère par critère.' },

  // 8. Pièges et risques — M137-T : Contrôle avant achat (M10) + Servitudes invisibles (O5) fusionnés.
  { key: 'risques', num: 'M10', group: 'instruire', phare: true,
    label: 'Pièges et risques', desc: 'Ce qui peut bloquer le projet, avant d\'acheter.' },

  // 9. Étude de zone — Z4 : la chalandise (isochrone IGN, habitants/emplois/concurrents SIRENE).
  { key: 'etude-zone', num: 'M27', group: 'marche', descSmall: true,
    label: 'Étude de zone', desc: 'Habitants, emplois, concurrents : la zone autour d\'un point.' },

  // 10. Remonter le temps — la frise des faits datés + le comparateur d'orthos.
  { key: 'temps', num: 'M08', group: 'temps',
    label: 'Remonter le temps', desc: 'La parcelle vue du ciel, année après année.' },

  // 11. Faisabilité — M22 : ce que le PLU laisse construire (2 entrées : par critères / par parcelle).
  { key: 'programme', num: 'M22', group: 'instruire', phare: true,
    label: 'Faisabilité', desc: 'Ce que le PLU laisse construire sur la parcelle.' },

  // 12. Taxe d'aménagement — K3 : assiette, part communale/départementale, barème servi par le back.
  { key: 'taxe-amenagement', num: 'K3', group: 'instruire',
    label: 'Taxe d\'aménagement', desc: 'La taxe du projet, calculée d\'avance.' },

  // 13. Prospection solaire — M26 : toits exposés + piscines (parcel_solar/PVGIS, gelé 11/07/2026).
  { key: 'prospection-solaire', num: 'M26', group: 'agir',
    label: 'Prospection solaire', desc: 'Les toits bien exposés, les piscines à équiper.' },

  // 14. Densifier l'existant — §5 : clé interne `renouvellement` inchangée (URL/QA/tests/endpoint/table).
  { key: 'renouvellement', num: 'MR1', group: 'marche',
    label: 'Densifier l’existant', desc: 'Le bâti en zone U qui peut porter davantage.' },

  // 15. Blocs fonciers — OUTILS-MUSCLER-3 : assiettes contiguës d'un même propriétaire PM (parcel_blocs).
  { key: 'blocs-fonciers', num: 'M29', group: 'agir', descSmall: true,
    label: 'Blocs fonciers', desc: 'Les assiettes d’un même propriétaire, sur toute l’île.' },

  // 16. Successions à venir — OUTILS-MUSCLER-1 A : radar patrimonial (jamais « est en succession »).
  { key: 'successions', num: 'M28', group: 'agir',
    label: 'Successions à venir', desc: 'Le foncier dont le propriétaire approche une succession.' },

  // 17. Courrier propriétaire — M09 : le client prépare, LABUSE envoie.
  { key: 'courriers', num: 'M09', group: 'agir',
    label: 'Courrier propriétaire', desc: 'Écrivez au propriétaire, LABUSE envoie.' },

  // ── RETIRÉS DU PRODUIT (dormants — composants, endpoints et tests conservés au dépôt) ──
  // M137-K : « Radar des ventes » (M25 — recouvre l'Analyse LABUSE). · M137-N : « Foncier fantôme » (M07,
  // nom non fidèle) & « Mode bailleur » (M06). · M129-C : « division ». · 21/08/2026 : « Simulateur ZAN »
  // (M17 — enveloppe reprise dans Communes), « Quoi de neuf » (O10 — endpoint /events VIVANT : cloche +
  // point du jour), « Suivi de secteur » (O7 — vues reprises ailleurs). · M137-P : « Changement PLU »
  // (M15) rejoint l'outil PLU unifié. Concept-routes Copilote des dormants retirées (answering.py).
]
