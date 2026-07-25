// strings.ts — TEXTE CLIENT CENTRALISÉ (M12 · règle R3)
// -----------------------------------------------------------------------------
// TOUS les libellés produits par les lots B (B1/B4/B5/B8) et C (C2) vivent ICI,
// pas dispersés dans les composants. Vic réécrit sa voix ici, sans toucher au JSX.
//
// Voir docs/LEXIQUE_CLIENT.md pour la table de correspondance terme technique →
// formulation client. Aucun de ces textes n'altère un calcul (A3 : le lift est
// correct — on réhabille l'affichage, jamais le scoring).
// -----------------------------------------------------------------------------

export const CLIENT = {
  // ── B1/B2 · métrique ×N et libellés de liste ──────────────────────────────
  mult: {
    // le nombre nu (×13.1) ne s'affiche jamais sans cette unité de sens
    unite: 'plus probable',
    // infobulle carte (le détail, pas le sens de base)
    tip: (n: string) =>
      `Cette parcelle est classée ${n} fois plus haut que la moyenne du parc analysé. ` +
      `Plafond ×64 = certitude maximale du modèle.`,
    absent: 'Classement non disponible',
  },

  // ── B1/B3 · barre de tri ──────────────────────────────────────────────────
  // M13-F3 (QA-57) : libellés de tri parlants. « commune » retiré (demande Vic).
  //  · rang → « classement » (le title dit CE QUI est classé : les parcelles).
  //  · ×N → libellé explicite. 3 options étudiées, la 1re retenue :
  //      1. « mutation ×N »  (RETENU — compact, dit ce que ×N multiplie)
  //      2. « probabilité de mutation »
  //      3. « ×N susceptibilité »
  //    Le title détaille la sémantique complète.
  tri: {
    rang: 'classement',
    mult: 'mutation ×N',
    surface: 'surface',
    rangTip: 'Classe les parcelles par ordre de priorité (n°1 = la plus prometteuse) — copropriétés en queue',
    multTip: 'Trie par le ×N : combien de fois la parcelle est plus susceptible de muter que la moyenne de l’île',
    surfaceTip: 'Trie par surface de parcelle, de la plus grande à la plus petite',
  },

  // ── B1 · scores ───────────────────────────────────────────────────────────
  scoreQ: {
    label: 'Potentiel constructible',
    tip: 'Qualité intrinsèque de la parcelle : règles PLU, risques, terrain (0-100, 100 = idéal).',
  },
  sdp: {
    label: 'Surface constructible restante',
    tip: 'Surface de plancher encore mobilisable sur la parcelle, après le bâti existant (m²). ' +
      'Les parcelles sans mesure de surface résiduelle ne sont pas retournées par ce filtre.',
  },
  completude: {
    label: 'Complétude des données',
    tip: 'Part des sources disponibles pour cette parcelle. N’est PAS une note de qualité du terrain.',
  },

  // ── B4 · bloc modèle de scoring (Sources) ─────────────────────────────────
  // Visible par défaut : le point de CONFIANCE (le classement reste fiable).
  // Le détail technique (version/sha/gel/recalage) est replié derrière « détail technique ».
  modele: {
    confiance:
      'Les ventes récentes mettent 1 à 3 ans à apparaître dans les bases publiques (DVF). ' +
      'Les niveaux de prix les plus récents sont donc provisoires — mais le CLASSEMENT ENTRE ' +
      'PARCELLES, lui, reste fiable.',
    detailToggle: 'détail technique',
  },

  // ── B5 · statuts de fraîcheur des sources ─────────────────────────────────
  // Point central : « à vérifier » ≠ « donnée douteuse ». Deux choses opposées.
  fraicheur: {
    a_jour: {
      label: 'À jour',
      court: 'donnée dans le rythme de publication de la source',
      title: 'Donnée dans la cadence de publication du producteur.',
    },
    maj_attendue: {
      label: 'Mise à jour dispo',
      court: 'une version plus récente est probablement parue',
      title: 'Le producteur a probablement publié plus récent — rafraîchissement à lancer.',
    },
    // le libellé qui inverse l'effet « rien n'est à jour »
    a_verifier: {
      label: 'Cadence non sondable',
      court: 'ce producteur n’expose pas de calendrier vérifiable automatiquement',
      title: 'Ce producteur ne publie pas de calendrier sondable automatiquement. ' +
        'La donnée affichée est bien la dernière version que nous ayons ingérée — ' +
        'ce n’est pas une donnée douteuse.',
    },
    // en-tête du tableau Sources (faute corrigée : « à » → « a »)
    entete: 'Chaque source a sa fraîcheur maximale, prouvée.',
  },

  // ── B7 · en-tête « preuve » de la page Sources (précision mesurée fusionnée) ─
  preuve: {
    titre: 'Ce que LABUSE mesure — et ne devine pas',
    intro:
      'La seule question sérieuse face à une app qui parle d’IA : « est-ce qu’elle invente ? ». ' +
      'La réponse est un chiffre mesuré et une garantie d’architecture.',
    // chaque ligne est cliquable → détail (méthode, échantillon, date de mesure)
    lignes: [
      {
        titre: 'Adresses (rattachement BAN)',
        valeur: '99,99 %',
        methode:
          'Rattachement parcelle ↔ adresse certifiée Base Adresse Nationale, sur l’île entière. ' +
          'Échantillon : les 431 663 parcelles. Mesure interne consignée.',
      },
      {
        titre: 'Recherche en langage naturel → filtres',
        valeur: 'jamais de SQL généré',
        methode:
          'Chaque traduction d’une phrase en filtres est validée par un schéma : le moteur ne ' +
          'fabrique jamais de requête libre. Jeu de recette interne (20/20). C’est la garantie ' +
          'd’architecture contre « l’IA invente ».',
      },
      // La ligne ANC est ajoutée dynamiquement (A8 : le signal ANC est partagé — Flash — donc conservé).
    ] as { titre: string; valeur: string; methode: string }[],
    ancLigne: {
      titre: 'Assainissement non collectif (signal ANC)',
      valeur: 'calé Office de l’eau',
      methode:
        'Zonages SPANC + EGOUL RP à l’IRIS — signal de priorisation, pas un diagnostic. ' +
        'Conservé car utilisé aussi par le diagnostic FLASH.',
    },
  },

  // ── B8 · « Comprendre l'algorithme » ──────────────────────────────────────
  algo: {
    // libellé RETENU (les 2 alternatives sont consignées au rapport final)
    bouton: 'Comprendre le classement',
    boutonAlt: ['Comment LABUSE classe', 'Sur quoi repose ce classement ?'],
    titre: 'Comment LABUSE classe les parcelles',
    // trame de contenu — écrite pour un client, VALIDÉE par Vic avant prod
    corps: [
      {
        h: 'Ce que le classement mesure',
        p: 'Une seule chose : la probabilité qu’une parcelle CHANGE DE MAIN ou de destination ' +
          'à court terme. Pas la valeur du terrain, pas la constructibilité — la mutabilité. ' +
          'Le n°1 est la parcelle la plus susceptible de bouger, pas forcément la plus chère.',
      },
      {
        h: 'Sur quoi il est entraîné',
        p: 'Sur l’historique réel des mutations foncières de La Réunion (ventes, divisions, ' +
          'changements d’usage) croisé avec des signaux publics : âge de détention, procédures, ' +
          'succession, dirigeant, état du bâti, contraintes PLU. Le modèle apprend les motifs ' +
          'qui ont précédé les mutations passées, puis les cherche sur les parcelles d’aujourd’hui.',
      },
      {
        h: 'Le « ×N »',
        p: 'Une parcelle « ×13 » est jugée 13 fois plus susceptible de muter que la moyenne. ' +
          'Le plafond est ×64 : une poignée de parcelles atteignent la certitude maximale du ' +
          'modèle et partagent donc ce même score de tête.',
      },
      {
        h: 'Ce qu’il ne dit PAS',
        p: 'Il ne dit pas que le propriétaire VEUT vendre, ni à quel prix, ni si l’opération est ' +
          'rentable. Il trie 431 663 parcelles pour vous dire lesquelles regarder en premier. ' +
          'La décision, la négociation et le montage restent votre métier.',
      },
    ] as { h: string; p: string }[],
  },

  // ── M14-F2 (QA-52) · projet — le bouton « + Chercher plus » est retiré ────────
  // Remplacé par cette invitation : on ajoute une parcelle à un projet depuis SA
  // fiche (bouton « Projet »), au fil de l'exploration — plus de recherche en lot.
  projet: {
    ajouterDepuisFiche:
      'Une parcelle en tête ailleurs ? Ajoutez-la à ce projet à tout moment depuis ' +
      'sa fiche, avec le bouton « Projet ».',
  },

  // ── M19 · fiche parcelle (refonte) — LOT C + explications de scores (P1.2) ──
  // Tout le texte client de la refonte fiche vit ici (R3) : Vic réécrit sans toucher au JSX.
  fiche: {
    adresseAbsente: 'Adresse non disponible',
    // C2 · le lien Pages Jaunes, renommé et assumé (jaune côté JSX)
    pagesJaunes: 'Voir sur Pages Jaunes',
    pagesJaunesTip:
      "Recherche externe à cette adresse (Pages Jaunes) — s'ouvre dans un nouvel onglet, rien n'est stocké.",
    // C4 · l'œil devient cloche (cohérent avec les notifications M16)
    suivre: 'Suivre cette parcelle (alertes sans pipeline)',
    suivreActif: 'Suivie — les événements alimentent la cloche',
    // C1 · le motif d'écartement passe à côté du badge
    ecarteeVoir: 'voir pourquoi →',
    ecarteeVoirTip: "Ouvre l'onglet « Pourquoi pas » — motifs sourcés de l'écartement.",
    // C8 · le bloc IA en une ligne, accroche client
    ia: {
      accroche: 'Une question sur cette parcelle ?',
      premium: 'Premium',
      demander: 'demander →',
      gardee: 'dernière réponse gardée — rouvrir →',
    },
    // C6 · « Banquier » renommé — 3 pistes étudiées, la 1re retenue :
    //   1. « Note de financement » (RETENU — dit l'objet : un document pour financer)
    //   2. « Dossier financeur »
    //   3. « Présentation banque »
    export: {
      banquier: 'Note de financement',
      banquierPret: 'Note — prête',
      banquierEnCours: 'Note…',
      banquierErreur: 'Note — réessayer',
      banquierTip:
        'Note de financement PDF (synthèse exécutive, bilan & charge foncière, comparables DVF/SITADEL, risques) — présentation financeur.',
      // C7 · ouvre le cadastre officiel externe, paramétré sur la parcelle
      cadastre: 'Cadastre ↗',
      cadastreTip:
        'Ouvre la parcelle sur le cadastre officiel (Géoportail — parcellaire express IGN) dans un nouvel onglet.',
      // ── M20 · barre à 7 tuiles ────────────────────────────────────────────
      // M20-B2 · « Financier » (9 c.) ne tient plus sur 7 colonnes (~55 px). 3 pistes courtes
      // étudiées, la 1re retenue :
      //   1. « Finance »  (RETENU — garde le sens « document de financement », tient sans troncature)
      //   2. « Banque »   (clair mais évoque un contact, pas un document)
      //   3. « Note fin. » (abréviation, moins lisible)
      finance: 'Finance',
      // M20-A · tuile « Courrier propriétaire » — ouvre le module M09 (un seul moteur, cf. Outils)
      // avec la parcelle courante pré-remplie. Boussole : aucune identité de personne physique
      // (le module adresse génériquement — identification via workflow SPF/CERFA).
      courrier: 'Courrier',
      courrierTip:
        'Écrire au propriétaire — ouvre le module Courrier avec cette parcelle pré-remplie. ' +
        'Aucune identité de personne physique n’est exposée (adressage générique ; identification via SPF/CERFA).',
    },
    // P1.2 · explications de scores rendues VISIBLES (plus seulement en survol)
    scores: {
      q: 'Qualité du terrain au regard des règles PLU, des risques et de l’accès (0-100, 100 = idéal).',
      a: 'Accès & desserte : voirie, réseaux et aménités à proximité (0-100).',
      v: 'Indices publics qu’un propriétaire pourrait céder (procédures, détention longue, succession, dirigeant).',
      icd: 'Part des sources renseignées pour CETTE parcelle. Ce n’est pas une note de qualité du terrain.',
      completude: 'Part des couches de données disponibles pour cette parcelle.',
    },
  },
} as const

export type ClientStrings = typeof CLIENT
