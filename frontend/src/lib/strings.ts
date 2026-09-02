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
  // M55-G suite point 4 (décision Vic) : UN SEUL niveau, 7 signaux — « Nu détenu par société »
  // (nu_pm) et « Cession de fonds » (cession) SUPPRIMÉS de l'UI (backend intact, clés URL sv=
  // inconnues ignorées à la lecture, cf. filters.ts SIGNAUX_VALIDES).
  signaux: {
    labels: {
      pm_privee: 'Détenu par une société',
      procedure: 'Procédure collective',
      permis_actif: 'Permis actif',
      permis_caduc: 'Permis abandonné',
      friche: 'Friche recensée',
      assemblage: 'Assemblage même proprio',
      defisc: 'Sortie de défisc',
      succession: 'Succession',
    } as Record<string, string>,
    // FILTRE-NETTOYAGE #1 — les « i » ne portent plus la date de mise à jour ni d'ingestion
    // (« maj 07/2026 », « arrêté 06/2026 », « calcul 08/2026 », millésime « 2025 ») : la SOURCE reste,
    // la date part (elle vit sur la page Sources). Le fond des libellés est inchangé.
    infos: {
      pm_privee: 'La parcelle — nue ou bâtie — est détenue par une société privée (personne morale hors État, collectivités et bailleurs sociaux ; fichiers fonciers MAJIC). 33 622 parcelles sur l’île.',
      procedure: 'Le propriétaire (société) a connu une procédure collective — sauvegarde, redressement ou liquidation, en cours ou récente (BODACC). Ne couvre que les propriétaires personnes morales identifiés. L’événement BODACC du classement n’est évalué que sur les parcelles classées et, de façon ciblée, sur les écartées dont le propriétaire est sous procédure — une écartée sans procédure connue ne porte jamais d’événement (exclusion délibérée, M103).',
      permis_actif: 'Un permis de construire accordé depuis moins de 3 ans, non repéré caduc (Sitadel — rattachement à la parcelle tel que déclaré au permis).',
      permis_caduc: 'Permis accordé jamais suivi de travaux repérés — caducité ESTIMÉE par LABUSE (croisement Sitadel × bâti) ; à vérifier en mairie.',
      defisc: 'La fenêtre de revente fiscale (défiscalisation estimée sur l’année d’achat neuf) est ouverte — le propriétaire peut vendre sans reprise d’avantage (ESTIMATION LABUSE).',
      friche: 'La parcelle touche une friche de l’inventaire national Cartofriches — inventaire NON exhaustif : l’absence du signal ne prouve rien.',
      assemblage: 'Le propriétaire (société privée) détient 3 parcelles ou plus sur l’île (MAJIC) — négociation groupée possible.',
      succession: 'Le propriétaire est une société exposée à une succession — SCI dormante ou dirigeant âgé (registres RNE / fichiers fonciers). 7 129 parcelles. Signal patrimonial, pas un événement daté ; ne couvre que les propriétaires personnes morales identifiés.',
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
    // M65 P2a — bandeau 3 cases : le CHIFFRE (servi, dynamique) au-dessus, le LIBELLÉ court en
    // dessous. Les valeurs restent servies par /accueil/chiffres (jamais en dur). « sources » = le
    // comptage réel des sources BRANCHÉES (data_sources status='connecte') — cf. rapport M65.
    labelParcelles: 'parcelles',
    labelCommunes: 'communes',
    labelSources: 'sources',
    b1Suite: ' — cadastre, PLU, permis, ventes, risques, procédures BODACC. Chaque donnée porte sa date — toujours la plus fraîche disponible.',
    // M55-J point 3 : les 3 infobulles « i » (accueil.src) sont RETIRÉES — aucune ne portait de
    // réserve d'honnêteté ; le sourcing détaillé vit sur la page Sources. Chaînes supprimées.
    commencer: 'Commencer →',
    // M65 P2c — second bouton (mauve) : ouvre l'onglet Copilote (« IA »).
    // M61 P6b : verbe retiré → « LABUSE IA » (tient sur une ligne à côté de « Commencer »).
    decouvrir: 'LABUSE IA',
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
    // M55-G suite point 5 : le bandeau « N parcelles notées par LABUSE — classement du … »
    // (contexte/contexteSous) est SUPPRIMÉ — la date du classement vit dans la modale
    // « comprendre le classement » (algo.dateRun).
    bouton: 'Analyser les parcelles',
    // M55-G suite point 6 (renommage Vic, remplace « Révéler les opportunités → » du point 2) :
    // « Demander à LABUSE → » — on demande un AVIS pré-calculé (run servi versionné), le mot
    // reste vrai. (boutonParc retiré : 0-caller depuis le stage 8.)
    boutonFaire: 'Demander à LABUSE →',
    // M55-F point 3 : choix sobre — voir la liste + carte en TRI FACTUEL, sans l'opinion LABUSE.
    voirN: (n: number) => `Voir les ${n.toLocaleString('fr-FR')} parcelles`,
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
    // M55-H point 10 : « déclassées » → « en potentiel épuisé » (même famille partout)
    ventDeclassees: (n: number) => `${n.toLocaleString('fr-FR')} faible`,
    ecarteesLbl: (n: number) => `${n.toLocaleString('fr-FR')} écartées par l’analyse`,
    ecarteesMotifs: 'zonage inconstructible, PPR rouge, impossibilités physiques…',
    voirPourquoi: 'voir pourquoi',
    ecarteesTip: 'Les écartées ne sont jamais masquées : exclusions LÉGALES et PHYSIQUES (zonage inconstructible, PPR rouge, emprise de voirie, eau…). Chaque parcelle garde son motif, consultable en fiche — coupez l’analyse pour les explorer.',
    voir: 'Voir les parcelles',
    // M55-M point 2 (décision Vic) : « Relancer l’analyse » → « Changer les filtres ». CONSTAT
    // documenté (rapport) : l'ancien bouton relançait le rituel sur des filtres FIGÉS (même
    // entrée → même résultat), il ne CHANGEAIT rien. Le libellé promettait faux. L'action est
    // rendue honnête (défiger les filtres et rendre la main sur le panneau — cf. changerFiltres()
    // dans FiltreLabuse) et le libellé dit désormais vrai. Clé renommée (l'ancienne `relancer`
    // n'existe plus).
    changerFiltres: 'Changer les filtres',
    // M55-J point 2 : « désactiver » devient un vrai bouton (majuscule initiale).
    desactiver: 'Désactiver l’analyse',
    erreur: 'L’analyse n’a pas pu aboutir — le serveur n’a pas répondu. Vos critères sont conservés.',
    reessayer: 'Réessayer',
    // M55-J point 1 · FILET : les critères ont bougé sous l'analyse (chemin externe) → la carte
    // s'invalide plutôt que d'afficher un chiffre périmé.
    perime: 'Vos critères ont changé depuis cette analyse — les chiffres affichés ne les décrivent plus.',
    relancerCta: 'Relancer sur les nouveaux critères',
    // définitions d'une ligne des tiers — la pédagogie au survol, au moment où elle sert
    // M137 — le « i » des paliers montre LE CHIP D'ABORD (le mot servi partout : chips, bande,
    // cartes, fiche, PDF), PUIS son explication. `defTiers[key]` = l'explication (« libellé long :
    // sens ») ; le CHIP est préfixé au rendu (tierChipLabel, source unique status.ts) → le client
    // relie le « Priorité » qu'il voit sur les cartes à sa définition. Nombres/couleurs inchangés.
    defTiers: {
      brulante: 'à contacter en priorité : la plus forte probabilité de vente sous 1 an, tête du classement.',
      chaude: 'à suivre de près : forte probabilité de vente sous 1 an, juste derrière la priorité.',
      reserve_fonciere: 'à revoir dans 1-2 ans : prometteuse, mais à horizon plus lointain.',
      a_creuser: 'sans signal particulier : rien de marquant pour l’instant.',
      declassees: 'peu de potentiel : analysée et conservée ; motif et état du bien en fiche.',
      ecartee: 'exclusion légale ou physique : motif consultable en fiche.',
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

  // ── M55-H point 10 · le « i » de la ventilation — les TROIS familles, une phrase chacune ──
  ventilation: {
    familles: 'Servables — les 4 tiers d’opportunité (Priorité, À suivre, Long terme, Neutre). '
      + 'Potentiel épuisé — analysée, verdict motivé (le potentiel résiduel ne paie plus l’opération standard) ; les chiffres sont en fiche. '
      + 'Écartées — exclusions légales et physiques, motifs consultables.',
  },

  // ── B1/B2 · métrique ×N et libellés de liste ──────────────────────────────
  // M135 — la PROBABILITÉ en FRACTION humaine (« 1/5 sous 1 an »), plus jamais un « ×N ».
  mult: {
    unite: 'sous 1 an',               // sous la fraction (« 1/5 »)
    faible: 'peu probable',           // sous le « — » (proba sous 1/50)
    absent: 'Classement non disponible',
    // infobulle carte : la lecture de la fraction (calibrée sur les ventes réelles)
    fractionBadge: (f: string) =>
      `${f} ≈ une chance sur ${f.split('/')[1]} qu’une vente intervienne dans l’année. ` +
      `Estimation calibrée sur les ventes réelles 2017-2025.`,
  },

  // ── B1/B3 · barre de tri ──────────────────────────────────────────────────
  // M13-F3 (QA-57) : libellés de tri parlants. « commune » retiré (demande Vic).
  //  · rang → « classement » (le title dit CE QUI est classé : les parcelles).
  //  · ×N → libellé explicite. 3 options étudiées, la 1re retenue :
  //      1. « mutation ×N »  (RETENU — compact, dit ce que ×N multiplie)
  //      2. « probabilité de mutation »
  //      3. « ×N susceptibilité »
  //    Le title détaille la sémantique complète.
  // M55-F point 6 — le tri parle CLIENT : les libellés disent la valeur, pas la mécanique.
  // M55-G suite point 2 — libellés COURTS (une seule ligne de pills) ; les libellés longs
  // (« Meilleures opportunités », « Plus susceptibles de se vendre ») migrent dans le « i ».
  tri: {
    // M55-I point 3 (arbitrage Vic, option A) : le tri « Mutation » (×N seul) est RETIRÉ —
    // doublon prouvé du classement (top-50 identiques, aucune inversion sur 431 663, mesuré
    // M55-H). Restent deux tris ; « Opportunités » se renomme « Probabilité de vente » : c'est
    // honnêtement ce qu'il trie (la probabilité apprise, ex æquo départagés par la qualité).
    rang: 'Probabilité de vente sous 1 an',
    surface: 'Surface',
    rangTip: 'Le classement LABUSE — la probabilité de vente sous 1 an, apprise sur dix ans de ventes réelles, les ex æquo départagés par la qualité du terrain ; copropriétés en queue',
    surfaceTip: 'Trie par surface de parcelle',
    // M69 A — le tri « Probabilité de vente » (défaut, analyse) groupe la liste par tier ; les
    // tris de colonne (Surface) s'appliquent GLOBALEMENT. Ce libellé dit l'état pour lever le
    // malentendu (« pourquoi ce n'est pas monotone ? » = parce que c'est groupé par tier).
    groupe: 'groupée par priorité d’action (priorité → faible) · trier par Surface pour un ordre global',
    // M135 — le « i » de la barre TRIER : la lecture de la fraction + les deux tris.
    lunettes: '« 1/5 sous 1 an » ≈ une chance sur cinq qu’une vente intervienne dans l’année — estimation calibrée sur les ventes réelles 2017-2025. Sous 1/50, un tiret « — » (peu probable). '
      + 'La liste est classée par cette probabilité (ex æquo départagés par la qualité du terrain, copropriétés en queue) ; Surface = la plus grande d’abord, re-cliquer inverse.',
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
    // M55-J point 5 : DEUX entrées jumelles dans le bandeau — le classement (méthode) et le
    // scoring (sens des paliers), chacune sa modale. Le lien isolé du bas des résultats disparaît.
    // M55-K point 2 : libellés COURTS (« Info … ») pour que les deux tiennent côte à côte sur
    // UNE ligne, même à la largeur de panneau la plus étroite. Destinations inchangées.
    bouton: 'Info classement',
    boutonScoring: 'Info scoring',
    // M55-H point 11 : la ligne de date du run (dateRun) est SUPPRIMÉE — détail technique,
    // jamais visible côté client (la date reste côté admin/ops).
    boutonAlt: ['Comment LABUSE classe', 'Sur quoi repose ce classement ?'],
    titre: 'Comment LABUSE classe les parcelles',
    // M55-G point 6 — version RESSERRÉE (trame Vic), chaque fait MESURÉ contre le modèle servi
    // q_v8_calibre (12/08/2026, preuves au rapport M55-G) :
    //  · entraînement : ventes réelles 2023, vérifié sur 2024 (train.py m3-p-model, FREEZE.json) ;
    //  · signaux appris (features.py) : âge de détention (tenure_bin), permis (permis_bin), état
    //    du bâti (friche/végétation/emprise), contraintes PLU, marché du secteur (DVF) — les
    //    anciens « procédures / succession / dirigeant » sont des signaux du Score V, PAS des
    //    features du modèle P → retirés (« dirigeant » : avis avocat P2-34 en attente, jamais
    //    dans la liste publique) ; « divisions / changements d'usage » non encodés → retirés ;
    //  · ×N : AUCUN plafond codé — max MESURÉ ×64,36 (3 parcelles / 431 663), un sommet, pas un cap.
    corps: [
      {
        h: 'Ce que mesure le classement',
        p: 'Une seule chose : la probabilité qu’une parcelle change de main à court terme. ' +
          'Pas sa valeur, pas sa beauté — sa probabilité de vente.',
      },
      {
        h: 'Comment',
        p: 'Le modèle a appris sur les ventes réelles de La Réunion (année 2023, vérifié sur ' +
          'les ventes 2024) : il a repéré les motifs qui précèdent une vente (âge de détention, ' +
          'permis, état du bâti, marché du secteur, règles PLU…) et les cherche sur les ' +
          'parcelles d’aujourd’hui.',
      },
      {
        h: 'La probabilité en fraction',
        p: '« 1/5 sous 1 an » ≈ une chance sur cinq qu’une vente intervienne dans l’année — ' +
          'la probabilité calibrée sur les ventes réelles 2017-2025, arrondie à un palier humain ' +
          '(1/2, 1/3, 1/4, 1/5, 1/10, 1/20, 1/50). Sous 1/50, un tiret « — » (peu probable).',
      },
      {
        h: 'Ce qu’il ne dit pas',
        p: 'Ni que le propriétaire veut vendre, ni le prix, ni la rentabilité. Il trie ' +
          '431 663 parcelles pour dire lesquelles regarder en premier — la décision reste ' +
          'votre métier.',
      },
    ] as { h: string; p: string }[],
    // M55-J point 5 · MODALE SCORING — le SENS des paliers (distinct du classement/méthode).
    // Les définitions elles-mêmes viennent de defTiers (source unique, réutilisée) — ici, juste
    // le cadre (titre + intro). Ordre des paliers servis par le composant ScoringExplainer.
    scoringTitre: 'Ce que veulent dire les paliers',
    scoringIntro: 'Après le classement, chaque parcelle reçoit un palier — du plus prometteur au moins mobilisable.',
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
    // M55-L point 2 — le « i » qui dit POURQUOI l'adresse manque : une absence RÉELLE dans la
    // source, pas un défaut de l'outil. Chiffres = mesure interne M55-G (rattachement BAN, portée
    // les parcelles), cités avec leur provenance (jamais un count live).
    adresseAbsenteInfo:
      'Aucune adresse de la Base Adresse Nationale (BAN) n’est rattachée à cette parcelle. '
      + 'Ce rattachement couvre environ la moitié des parcelles de l’île (227 545 sur 431 663 — '
      + 'mesure interne M55-G) : les parcelles naturelles ou sans bâti n’ont le plus souvent pas '
      + 'd’adresse. C’est une absence réelle dans la source, pas un défaut de l’outil.',
    // C2 · le lien Pages Jaunes, renommé et assumé (jaune côté JSX)
    pagesJaunes: 'Voir sur Pages Jaunes',
    pagesJaunesTip:
      "Recherche externe à cette adresse (Pages Jaunes) — s'ouvre dans un nouvel onglet, rien n'est stocké.",
    // C4 · l'œil devient cloche (cohérent avec les notifications M16)
    suivre: 'Suivre cette parcelle (alertes sans passer par le CRM)',   // M55-L point 9 : plus de « pipeline » à l'écran
    suivreActif: 'Suivie — les événements alimentent la cloche',
    // C1 · le motif d'écartement passe à côté du badge
    ecarteeVoir: 'voir pourquoi →',
    ecarteeVoirTip: "Ouvre l'onglet « Pourquoi pas » — motifs sourcés de l'écartement.",
    // M55-L point 5 — verdict à la demande : à l'ouverture, un bouton remplace le bloc verdict
    // (l'avis n'est jamais imposé à qui veut d'abord des informations). Au clic, le bloc se déploie.
    demanderAnalyse: 'Demander à LABUSE d’analyser la parcelle',   // M55-N point 4 (libellé Vic)
    demanderAnalyseSous: 'Le verdict, le score et « pourquoi » — à la demande.',
    // M55-N point 5 — libellé honnête du tiroir « Les données » : dit CE QU'IL COMPTE (les sources
    // qui alimentent CETTE fiche, cf. audit M55-L P13), pas un manque. Chiffre servi (jamais en dur).
    sourcesUtilisees: (n: number) => `${n} sources utilisées sur cette fiche`,
    // M55-N point 6 — la jauge du tiroir Règles DIT ce qu'elle mesure : la part de SDP maximale
    // déjà consommée par le bâti (échelle 0-100 %), + infobulle (sens + source + résiduel).
    sdpConsommee: (pct: number) => `${pct} % SDP consommée`,
    sdpConsommeeTip: (resid: number | null) =>
      `Part de la SDP maximale déjà bâtie sur la parcelle (échelle 0–100 %) — le reste${resid != null ? ` (~${resid.toLocaleString('fr-FR')} m²)` : ''} est le potentiel résiduel constructible. Estimé — potentiel de transformation.`,
    // M55-L point 9 — « + Pipeline » → « + CRM » (source unique). Plus aucun « Pipeline » sur le
    // bouton ni ses infobulles (la vue CRM garde son vocabulaire propre en interne).
    crmAjouter: '+ CRM',
    crmDedans: '✓ Dans le CRM',
    crmAjouterTip: 'Ajouter au CRM (suivi de prospection)',
    crmDedansTip: 'Déjà dans le CRM — voir la vue CRM',
    // C8 · le bloc IA en une ligne, accroche client
    ia: {
      accroche: 'Une question sur cette parcelle ?',
      // RETOURS-9 (Q10.3) — token `premium` retiré : l'essai voit tout, il n'y a pas de premium.
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
      // M54-EXPO — exports « document » branchés (Pré-dossier PC, courrier SPF). M93 — one-pager retiré.
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
      a: 'Accès & desserte : voirie, réseaux, commerces et services à proximité (0-100).',
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
    // M133 — l'ancien hero (la promesse d'instruction) est RETIRÉ : mort depuis M118 et l'accueil
    // v3 sert désormais son propre hero. Ces 6 clés (h1Ligne*/lede/ledeFort) n'étaient plus lues.
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
        mutation: { nom: 'Probabilité de vente', desc: 'classement par probabilité de vente sous 1 an' },
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
