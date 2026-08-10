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
  // ── M55-D stage 6 · SIGNAUX DE VIE — 8 signaux validés Vic (phase 1 mesurée). Chaque « i »
  //    est SOURCÉ, daté, et dit le partiel. Libellés validés au STOP. ──
  signaux: {
    labels: {
      procedure: 'Procédure collective',
      permis_actif: 'Permis actif',
      permis_caduc: 'Permis abandonné',
      defisc: 'Sortie de défisc',
      nu_pm: 'Nu détenu par société',
      friche: 'Friche recensée',
      cession: 'Cession de fonds',
      assemblage: 'Assemblage même proprio',
    } as Record<string, string>,
    infos: {
      procedure: 'Le propriétaire (société) a connu une procédure collective — sauvegarde, redressement ou liquidation, en cours ou récente (BODACC, maj 07/2026). Ne couvre que les propriétaires personnes morales identifiés.',
      permis_actif: 'Un permis de construire accordé depuis moins de 3 ans, non repéré caduc (Sitadel, arrêté 06/2026 — rattachement à la parcelle tel que déclaré au permis).',
      permis_caduc: 'Permis accordé jamais suivi de travaux repérés — caducité ESTIMÉE par LABUSE (croisement Sitadel × bâti, calcul 08/2026) ; à vérifier en mairie.',
      defisc: 'La fenêtre de revente fiscale (défiscalisation estimée sur l’année d’achat neuf) est ouverte — le propriétaire peut vendre sans reprise d’avantage (ESTIMATION LABUSE, maj 07/2026).',
      nu_pm: 'Parcelle quasi nue (emprise bâtie < 5 %) détenue par une société privée (fichiers fonciers MAJIC 2025).',
      friche: 'La parcelle touche une friche de l’inventaire national Cartofriches (maj 07/2026) — inventaire NON exhaustif : l’absence du signal ne prouve rien.',
      cession: 'Le propriétaire (société) a vendu ou cédé un fonds dans les 24 derniers mois (BODACC, maj 07/2026). Propriétaires personnes morales identifiés seulement.',
      assemblage: 'Le propriétaire (société privée) détient 3 parcelles ou plus sur l’île (MAJIC 2025) — négociation groupée possible.',
    } as Record<string, string>,
  },
  // ── M55-D stage 8 · PAGE D'ACCUEIL — présentation SOBRE et FACTUELLE (aucun superlatif :
  //    la doctrine — rien n'est masqué, chaque chiffre a sa source — est elle-même l'argument).
  //    L'UNIQUE CTA d'analyse vit dans le panneau Filtres ; ici, un seul lien : « Commencer → ». ──
  accueil: {
    // M55-D stage 9 ter — TEXTE FINAL FIGÉ VIC (10/08) : DEUX blocs et le lien, rien d'autre.
    // Les chiffres du bloc 1 restent SERVIS par /accueil/chiffres (affichage dynamique, « i »
    // sourcé sur chacun) — le texte figé donne les valeurs actuelles, jamais des counts en dur.
    b1Titre: 'LABUSE, c’est tout le foncier de La Réunion. Au même endroit.',
    segParcelles: (n: string) => `${n} parcelles`,
    segCommunes: (n: string) => `${n} communes`,
    segSources: (n: string) => `${n} sources publiques branchées`,
    b1Suite: ' — cadastre, PLU, permis, ventes, risques, procédures BODACC. Chaque donnée porte sa date — toujours la plus fraîche disponible.',
    src: {
      parcelles: 'Compte exact du classement servi (run versionné), recalculé à chaque mise à jour majeure.',
      communes: 'Cadastre DGFiP — toutes les communes de La Réunion, sans exception.',
      sources: 'Catalogue Sources : connecteurs publics actifs (DEAL, DGFiP, INSEE, BODACC, Sitadel…) — voir l’onglet Sources.',
    },
    commencer: 'Commencer →',
  },
  // ── M55-D stage 7 · COMPTEUR VIVANT — le funnel en bas de la section Filtres. Toujours la
  //    réponse /filtre réelle (debounce 400 ms, appels obsolètes annulés), jamais une estimation. ──
  compteur: {
    correspondent: (n: number) => `${n.toLocaleString('fr-FR')} parcelles correspondent à vos critères`,
    zero: 'Aucune parcelle ne correspond — élargissez vos critères.',
  },
  // ── M55-D stage 5 · LA RÉVÉLATION — tout le texte du rituel d'analyse. RÈGLE D'HONNÊTETÉ :
  //    le score est PRÉ-CALCULÉ (run servi versionné) ; pendant le décompte on APPLIQUE des
  //    critères, on ne « calcule » aucun score. Aucun mot ne doit prétendre le contraire. ──
  revelation: {
    contexte: (n: number, date: string | null) =>
      `${n.toLocaleString('fr-FR')} parcelles notées par LABUSE` +
      (date ? ` — classement du ${date}` : ''),
    contexteSous: 'Classement versionné, recalculé à chaque mise à jour majeure.',
    bouton: 'Analyser les parcelles',
    // M55-D stage 7 : bouton CONTEXTUEL — N = le compteur vivant (réponse /filtre réelle) ;
    // zéro filtre posé → le parc du périmètre.
    // M55-D stage 8 : avec des filtres posés le bouton renvoie au nombre affiché juste au-dessus
    // (compteur + bandeau, MÊME état) — « les », pas un second chiffre qui pourrait diverger.
    boutonFaire: 'Les faire analyser par LABUSE →',
    boutonParc: (n: number) => `Analyser les ${n.toLocaleString('fr-FR')} parcelles`,
    decompte: (n: number) => `application de vos critères aux ${n.toLocaleString('fr-FR')} parcelles`,
    decompteFin: 'parcelles analysées',
    phraseIntro: (n: number, perimetre: string) =>
      `LABUSE a analysé les ${n.toLocaleString('fr-FR')} parcelles de ${perimetre}.`,
    // le récap des critères s'insère AVANT le deux-points : « Selon vos critères (3 communes, …) : »
    phraseSelon: (recap: string | null) =>
      recap ? `Selon vos critères (${recap}) :` : 'Selon vos critères :',
    phraseZero: 'aucune parcelle retenue — élargissez vos critères (surface, zonage, verdict).',
    // M55-F point 2 — la phrase COMPLÈTE son compte : l'arithmétique boucle (analysé = retenues
    // + écartées ; retenues = ventilation complète, à-creuser et déclassées inclus).
    retenuesLbl: (n: number) => `${n.toLocaleString('fr-FR')} retenues`,
    ventDeclassees: (n: number) => `${n.toLocaleString('fr-FR')} déclassées`,
    ecarteesLbl: (n: number) => `${n.toLocaleString('fr-FR')} écartées par l’analyse`,
    ecarteesMotifs: 'domaine public, inconstructibles…',
    voirPourquoi: 'voir pourquoi',
    ecarteesTip: 'Les écartées ne sont jamais masquées : exclusions dures de l’étage 0 (domaine public, RNU, inconstructible réglementaire…). Chaque parcelle garde son motif — visible en fiche, coupez l’analyse pour les explorer.',
    voir: 'Voir les parcelles',
    relancer: 'Relancer l’analyse',
    desactiver: 'désactiver l’analyse',
    erreur: 'L’analyse n’a pas pu aboutir — le serveur n’a pas répondu. Vos critères sont conservés.',
    reessayer: 'Réessayer',
    // définitions d'une ligne des tiers — la pédagogie au survol, au moment où elle sert
    defTiers: {
      brulante: 'Brûlante — la plus forte probabilité de changer de main à court terme, tête du classement.',
      chaude: 'Chaude — forte probabilité de mutation, juste derrière les brûlantes.',
      reserve_fonciere: 'Potentiel long terme — prometteuse mais à horizon plus lointain (réserve foncière).',
      a_creuser: 'À creuser — signal présent mais plus faible, à confirmer au cas par cas.',
      declassees: 'Déclassées — retenues par l’analyse mais rétrogradées pour un motif (bâti saturé, zone fermée…) ; visibles avec leur motif.',
    } as Record<string, string>,
  },
  // ── M-U · bloc « Marché » par commune (Agent Prix). Libellés client sobres (LOI-3). ──
  marche: {
    banner: 'Le marché d’une commune, ligne par ligne — chaque chiffre porte sa source et sa date. '
      + 'Aucune annonce, aucune source privée : uniquement les actes (DVF) et les autorisations (Sitadel).',
    signal: 'Signal de marché',
    signalIndispo: 'Signal de marché non calculable (liquidité ou offre indisponible).',
    nonCalculable: 'non calculable',
    note: 'Chaque ligne porte sa propre date de source amont — le bloc ne prétend pas à un millésime unique.',
    lignes: {
      prix_ancien_median: 'Prix ancien médian (€/m²)',
      prix_terrain_nu_par_zone: 'Prix du terrain nu, par zone (U / AU)',
      prix_sortie_neuf: 'Prix de sortie neuf (€/m²)',
      tendance_12m: 'Tendance 12 mois',
      liquidite: 'Liquidité (mutations/trimestre)',
      offre_engagee: 'Offre engagée (logements autorisés)',
      gisement_constructible: 'Offre potentielle (gisement constructible)',
      pression_dpe: 'Pression DPE (F/G)',
      loyer_median: 'Loyer médian (€/m²)',
    },
  },
  // ── EXPRESS-01 · Volet B — AVIS IA (au mot près). SOURCE UNIQUE, réutilisée par TOUTES
  //    les surfaces front où l'IA s'exprime (fiche AskBar/faisa/traducteur, recherche IA,
  //    entretien, Copilote) via <AvisIA>. Jumelle Python `AVIS_IA`, défini dans ai/avis.py
  //    (source unique, importé par export.py et banquier.py) — à garder identique au mot
  //    près. Ne jamais recopier ce texte ailleurs. ──
  avisIa: "L'IA ne juge pas le sentiment d'une communauté, n'évalue pas le risque politique d'un processus d'autorisation, et ne remplace pas les éléments relationnels du sourcing.",

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
    multTip: 'Trie par le ×N : combien de fois la parcelle est plus susceptible d’être vendue que la moyenne de l’île',
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
        p: 'Une parcelle « ×13 » est jugée 13 fois plus susceptible d’être vendue que la moyenne. ' +
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
    adresseAbsente: 'adresse non rattachée (Absent)',   // M30 item 4 — jamais un champ vide, étiquette boussole
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
      // M54-EXPO-2 — synthèse IA de toute la fiche
      synthese: 'Synthèse IA',
      syntheseTip: 'Une synthèse en prose de la fiche (verdict, capacité, points de vigilance), rédigée par l’IA à partir des seules données servies.',
      syntheseEnCours: 'L’IA rédige la synthèse…',
      syntheseErreur: 'Synthèse indisponible — réessayez.',
      syntheseStub: 'Synthèse automatique (repli déterministe — analyse IA enrichie non servie).',
    },
    // C6 · « Banquier » renommé — 3 pistes étudiées, la 1re retenue :
    //   1. « Note de financement » (RETENU — dit l'objet : un document pour financer)
    //   2. « Dossier financeur »
    //   3. « Présentation banque »
    export: {
      // M54-EXPO — exports « document » branchés (One-pager comité, Pré-dossier PC, courrier SPF).
      onepager: 'One-pager',
      onepagerTip: 'One-pager A4 imprimable — le document de comité (verdict, capacité, résiduel, bilan, contraintes, mini-carte).',
      preDossier: 'Pré-dossier PC',
      preDossierTip: 'Pack pré-dossier de permis : CERFA pré-rempli + plan de situation + fiche règles du zonage (réservé au plan Intégral).',
      preDossierGate: 'Réservé au plan Intégral',
      spf: 'Courrier SPF',
      spfTip: 'Génère le courrier de demande au Service de la Publicité Foncière, pré-rempli avec la référence cadastrale (voie légale d’identification du propriétaire).',
      // M54-EXPO A4 — retour promoteur (POST /feedback)
      fbAccroche: 'Ce lead vous est-il utile ?',
      fbGood: 'Bonne piste',
      fbNot: 'Pas intéressé',
      fbFalse: 'Faux positif',
      fbComment: 'Un mot (facultatif)…',
      fbSend: 'Envoyer',
      fbMerci: 'Merci — votre retour affine le moteur.',
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

  // ── M26-B · écran Copilote ─────────────────────────────────────────────────
  // L'écran est une projection de l'event log M26-A : TOUT chiffre et toute
  // étiquette (Sourcé/Estimé/Absent) viennent du payload, jamais d'ici. Ici ne
  // vivent que les libellés fixes. Les formulations de calibrage sont IMPOSÉES
  // par le mandat : sur commune non calibrée, jamais « tracé(e) par article ».
  copilote: {
    crumb: 'Copilote',
    statuts: {
      interpreting: 'Interprétation', awaiting_user: 'En pause', running: 'Instruction',
      paused: 'En pause', done: 'Terminé', failed: 'Échec', cancelled: 'Annulée',
    } as Record<string, string>,
    h1Ligne1: 'Décrivez le besoin.',
    h1Ligne2Avant: 'Le Copilote ',
    h1Ligne2Em: 'instruit le dossier',
    h1Ligne2Apres: '.',
    lede: 'Il ne calcule rien. Il séquence les moteurs LABUSE, journalise chaque étape et étiquette chaque chiffre. ',
    ledeFort: 'C’est pour ça que vous pouvez l’emmener en comité.',
    placeholder: 'Décrivez le besoin — commune, programme, budget, contraintes…',
    instruire: 'Instruire',
    annuler: 'Annuler l’instruction',
    serment: 'Moteurs déterministes journalisés',
    // Les 5 missions du Copilote — 2 actives (M26-A/B), 3 « bientôt » (mandats dédiés).
    missions: [
      { key: 'instruire', label: 'Instruire un besoin', actif: true },
      { key: 'shortlist', label: 'Shortlist', actif: true },
      { key: 'verifier_adresse', label: 'Vérifier des références', actif: false },
      { key: 'aide_dossier', label: 'Aide sur un dossier', actif: false },
      { key: 'brief_matin', label: 'Brief du matin', actif: false },
    ] as ReadonlyArray<{ key: string; label: string; actif: boolean }>,
    bientot: 'bientôt',
    // états transitoires — AUCUN résultat partiel pendant l'instruction (règle 5)
    interpretationEnCours: 'Interprétation du besoin en cours…',
    enCours: 'Les parcelles s’afficheront à la fin de l’instruction.',
    enCoursNote: 'Aucune liste partielle n’est montrée — elle laisserait croire à un examen terminé.',
    enCoursSerment: (fait: number, total: number) => `${fait} moteur${fait > 1 ? 's' : ''} appelé${fait > 1 ? 's' : ''} sur ${total}`,
    enAttenteBouton: 'En attente',
    suspendue: 'Instruction suspendue',
    fluxInterrompu: 'Flux interrompu — reconnexion…',
    annulee: 'Instruction annulée.',
    // état 3 · demande de précision — le run REPREND, il ne redémarre pas
    precisionTitre: 'Précision nécessaire',
    precisionReprendre: 'Reprendre l’instruction',
    precisionPlaceholder: 'Ou saisissez votre réponse…',
    interpretation: {
      nom: 'Interprétation',
      faite: 'besoin interprété',
      active: 'analyse du besoin',
      pause: 'précision demandée — le Copilote ne devine pas',
    },
    entonnoir: {
      titre: 'Le gisement se resserre',
      sousTitre: 'Un étage par moteur — le détail est en dessous.',
      cap: 'Instruction',
      capEnCours: 'Instruction en cours',
      sousTitreEnCours: 'Les étages s’affichent au fur et à mesure.',
      enAttenteEtage: '—',
      // libellés des étages (les n et étiquettes viennent du payload entonnoir)
      etages: {
        pool: 'pool servi', filtre_geometrique: 'filtre géométrique', examinees: 'examinées',
        retenues: 'retenues', dans_budget: 'dans le budget', restituees: 'restituées',
      } as Record<string, string>,
      badgeExhaustif: 'Examen exhaustif',
      badgePartiel: 'Examen partiel',
      // formulation IMPOSÉE (mandat §2.2) — verrouillée par test
      badgeCalibre: 'PLU calibré — tracé par article',
      badgeGenerique: 'Règle générique — PLU non calibré',
    },
    fil: {
      titre: 'Fil d’instruction',
      meta: (n: number) => `${n} moteurs · journal joint`,
      metaEtape: (i: number, n: number) => `étape ${i} sur ${n}`,
      metaPause: 'en pause',
      enAttente: 'en attente',
      moteurs: {
        criblage: { nom: 'Criblage', desc: 'pool servi · zones et contraintes du brief' },
        filtre_geometrique: { nom: 'Filtre géométrique', desc: 'SDP cible inatteignable écartée par la géométrie' },
        faisabilite: { nom: 'Faisabilité', desc: 'SDP résiduelle par parcelle' },
        risques: { nom: 'Risques', desc: 'signaux PPR, ABF et couches de risques' },
        marche_dvf: { nom: 'Charge foncière', desc: 'prix probable du foncier · comparables DVF' },
        filtre_budget: { nom: 'Filtre budget', desc: 'retenues confrontées au budget du brief' },
        mutation: { nom: 'Mutation', desc: 'classement des retenues · modèle P' },
        assemblage: { nom: 'Assemblage', desc: 'restitution motivée · journal joint' },
        assemblage_court: { nom: 'Assemblage', desc: 'restitution courte · journal joint' },
        scoreur_unitaire: { nom: 'Scoreur unitaire', desc: 'références retrouvées et scorées' },
        assemblage_verdict: { nom: 'Verdicts', desc: 'un verdict par référence' },
      } as Record<string, { nom: string; desc: string }>,
    },
    resultats: {
      titre: (n: number) => `${n} parcelle${n > 1 ? 's' : ''} restituée${n > 1 ? 's' : ''}`,
      titreEnCours: 'Résultats',
      meta: (nRetenues: number) => `sur ${nRetenues} retenues`,
      // règle 4 (mandat) : TOUJOURS visible quand retenues > restituées — verrouillé par test.
      // En deux morceaux : le « N autres retenues » est mis en gras par le composant.
      autresRetenuesFort: 'autres retenues',
      autresRetenuesSuite: (rang: number) =>
        `, non restituées — classées après le rang ${rang}.`,
      sdp: 'SDP résiduelle',
      surface: 'surface parcelle',
      prixProbable: 'Prix probable du foncier',
      chargeSupportable: 'Charge foncière supportable',
      signauxRisques: (n: number) => `${n} signal${n > 1 ? 'aux' : ''} de risques`,
      tier: 'Tier',
      // règle 7 : information, jamais un filtre — la parcelle reste restituée
      chargeFlag: (charge: string) =>
        `Au-dessus de la charge supportable (${charge}) — dans votre budget, mais l’opération ne supporte pas ce prix.`,
      // décision produit (revue B) : charge ≤ 0 = information forte, jamais un montant nu.
      // La valeur brute reste visible, le sens est donné.
      chargeNonViable: (charge: string) =>
        `Opération non viable — la charge supportable est nulle ou négative (${charge}), même à foncier gratuit.`,
      chargeNonViableCourt: (charge: string) => `opération non viable (${charge})`,
      chargeSupportableCourt: (charge: string) => `charge supportable ${charge}`,
      zeroTitre: 'Aucune parcelle ne satisfait ce besoin.',
      zeroNote: 'Aucun critère n’a été assoupli — l’entonnoir ci-dessus montre où le besoin s’est heurté au réel.',
      // relances NON CHIFFRÉES (arbitrage GO) : elles pré-remplissent la console avec le
      // brief d'origine, l'utilisateur ajuste lui-même. Aucun chiffre inventé par l'écran.
      relanceBudget: 'Relancer en ajustant le budget',
      relanceCommunes: 'Élargir à d’autres communes',
    },
    livrable: {
      titre: 'Note d’opportunité',
      desc: (nR: number, nE: number, nMoteurs: number) =>
        `${nR} restituée${nR > 1 ? 's' : ''} argumentée${nR > 1 ? 's' : ''} · ${nE} écartées motivées · journal des ${nMoteurs} appels moteurs joint.`,
      journal: 'Voir le journal',
      pdf: 'Télécharger le PDF',
      pdfBientot: 'bientôt', // livrable PDF = mandat M26-C
    },
    // état 5 · quota atteint AVANT création du run — aucun moteur appelé
    quota: {
      pill: 'Indisponible aujourd’hui',
      titre: (n: number | null) =>
        n != null ? `Vos ${n} instructions du jour sont utilisées.` : 'Quota du jour atteint.',
      aucunRun: 'Cette instruction n’a pas été lancée : aucun moteur n’a été appelé, rien n’a été décompté de plus.',
      distinct: 'Le quota agentique est distinct du quota Dossier — vos exports restent disponibles.',
    },
    journal: {
      titre: 'Journal d’instruction',
      sousTitre: 'L’event log intégral du run — ce que la note joint en annexe.',
      fermer: 'Fermer le journal',
    },
  },
} as const

export type ClientStrings = typeof CLIENT
