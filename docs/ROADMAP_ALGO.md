# ROADMAP ALGO LABUSE — juillet 2026

Document de référence issu de la session stratégie post-cartographie. Les mandats futurs s'y réfèrent.

> **État d'exécution (ajout éditorial, non modificatif)** : ce document est la **stratégie d'origine**.
> L'exécution a avancé — Phase 0 close, Phase A au **plateau (2/2) → M7**. Pour l'état courant (ce qui est
> servi, en réserve datée, reporté post-M7), voir **`docs/mandats/PHASEA_BILAN.md`** et le compteur canonique
> **`docs/mandats/A1_BILAN.md`**. La stratégie ci-dessous reste la référence des **règles** (sortie, doctrine,
> « Rejeté »).

**Règle de sortie :** on améliore tant que les challengers battent le champion sur le harnais. Deux cycles
d'ablation sans victoire = plateau atteint = on déploie. Pas de « mieux » sans fin.

**Garde-fous permanents :**
- La boussole rend la fonction de perte asymétrique : un gain de rappel payé en faux positifs servis = refus,
  quel que soit le RR global.
- Interprétabilité non négociable (« chaque chiffre tracé ») : pas de boîte noire en production.
- L'arène est le portier rapide ; le **walk-forward 6 folds reste le juge final** pour tout changement de modèle.
- Toute évolution de modèle = événement versionné (M4.0, M4.1…), gel sha256, hystérésis de migration, nouveau
  run label. Jamais de bricolage continu.

---

## Phase 0 — Le Juge *(en cours)*

- **J1 ✅ mergé** : 77 tests du chemin critique (étage 0 étendu, engine, phase 2, SQL du modèle P,
  anti-leakage as-of).
- **J2** : arène `labuse arene` livrée, baseline `q_v6_m8` = RR@1158 13,17 [11,93–15,00], ECE 0,0167.
  **J2-bis à faire** : réconcilier 13,17 vs 6,73 (in-sample vs hors-temps — documenter dans la baseline),
  bootstrap apparié sur la différence, canari de dégradation en test permanent.
- **J3** : golden 32 → ~120, stratifié communes × tiers × motifs. STOP validation Vic ligne à ligne avant gel.

## Phase A — Gains rapides, zéro retrain

- **A1 — Fenêtres de tir** *(tête de phase — meilleure idée de la session)* :
  - **Sortie de défiscalisation** : biens achetés VEFA 2013-2018 (signature visible dans
    `dvf_mutations_histo`, remonte à 2014) arrivant en fin d'engagement Girardin/Pinel DOM 6/9/12 ans.
    Attaque l'angle mort personnes physiques **sans toucher à une identité** — boussole-compatible par
    construction.
  - **PC caducs** : permis accordé, jamais construit, > 3 ans — propriétaire qui a prouvé la constructibilité
    et échoué à faire.
  - **Passoires DPE F/G bailleurs privés** vs calendrier d'interdiction de location (calendrier DOM décalé —
    À VÉRIFIER précisément avant usage).
  - Devenir : features candidates M4.0 **et** signaux V, jugés par l'arène.
- **A2 — Score V v2** : trancher les poids BODACC (LJ/RJ/sauvegarde, « TODO v2 ») et la famille B neutralisée,
  par backtest (`scripts/score-v/backtest.py`), pas à l'intuition.
- **A3 — Matrice Q×A** : brancher les signaux *qualité* dormants (bruit, SUP, cinquante pas, friches…) via
  `matrice-simulate`, convention versionnée. Amélioration d'algo sans toucher au modèle gelé.

## Phase B — M4.0 (retrain)

- Features candidates testées **une par une** en ablation sur le harnais : fenêtres de tir (A1),
  **contagion spatiale** (vente/permis récents en voisinage immédiat, construits as-of depuis les précalculs
  `EvalContext`), signaux *propension* dormants (DPE, âge dirigeant, dynamique permis), achats récents de
  promoteurs par secteur (DVF × PM NAF promo — variante de contagion).
- **Shadow GBM** (`p_model/shadow.py`) : miner les interactions, réinjecter les 3-4 meilleures à la main dans
  la logistique.
- Anti-leakage as-of non négociable (verrouillé par les tests J1). M4.0 n'existe que s'il bat M3.6 au
  walk-forward.
- **Piste à étudier (pas décidée)** : ingénierie de la cible — label alternatif « permis déposé sous 24 mois »,
  plus proche du besoin promoteur que « mutera ».

## Phase C — Calibration fine

ECE par commune/bassin ; recalage par groupe si dérive sur les petites communes.

## Chantiers C / produit *(parallèles — ne touchent pas au modèle gelé)*

- **Score É — la marge cachée** : charge foncière supportable (bilan à rebours) − prix probable du foncier
  (`dvf_secteur_medianes`) = classement de l'île **en euros**. Étiquette Estimé, traçable. Modificateur
  **rareté ZAN** (communes proches du quota ENAF → le U existant s'apprécie).
- **Assemblages à débloquer** : unions de 2-3 parcelles de propriétaires DIFFÉRENTS où SDP(union) −
  Σ SDP(chacune) franchit un seuil. Croisé au score V de chaque propriétaire (BODACC = clé d'entrée).
  Combinatoire bornée (contiguïté, même zone).
- **Risques de transaction** (axe anti-KelFoncier) : risque de **préemption** (couches DPU/ZAD déjà ingérées),
  **coût de portage** (vélocité admin M05 × coût mensuel, injecté au bilan), **absorption** (logements
  autorisés Sitadel vs ventes VEFA DVF par secteur).
- **« Ton top 50, pas le top 50 »** : modulation du classement par profil projet (bailleur SRU / promoteur
  R+3 / lotisseur), sur la base des projets existants.

## Tier 1 — changements de nature du signal (dépendances externes)

Convention DGFiP/EPF/AGORAH pour les **personnes physiques** (le vrai saut) · **fraîcheur J+2** (crons
post-VPS) · **feedback clients** (démarre au lancement — le moat que KelFoncier n'aura jamais).

## Rejeté (et pourquoi)

- Prédire la **date** de mutation : sur-promesse à ~1 % de taux de base — la boussole dit non.
- Identité des personnes physiques par moyens détournés : non, structurellement.
- Modèles boîte noire pour quelques points de RR : le moat est l'interprétabilité.

## Le plafond, dit une fois

Taux de base ~1 %/an : même à RR doublé, ~85 % du top ne mutera pas dans l'année — les déterminants principaux
(succession, divorce, liquidités) sont invisibles depuis l'open data. Passé le plateau, les points restants
sont dans le tier 1 et dans la solidité de **C** : pour le client, l'algo c'est P × C, et un faux positif de
constructibilité coûte plus cher qu'un point de RR.
