# COMPTE-RENDU — CIRCUIT-4 (la règle : chaque calcul adossé à sa référence)

Branche : `feat/circuit-4` · worktree `~/Desktop/labuse-audit` · créée depuis `origin/main`
(`feat/circuit-page` — CIRCUIT-P/P2/P3 — y est MERGÉE ; vérifié `merge-base --is-ancestor`).
Rien n'est mergé. Un commit + un push par lot. La liste d'exceptions au registre reste VIDE.
Reprise : « continue CIRCUIT-4 depuis docs/CIRCUIT/COMPTE-RENDU-CIRCUIT-4.md ».

## Étape 0

- pwd/arbre propres ; CIRCUIT-3 et CIRCUIT-P clos (comptes-rendus présents, DoD atteintes).
- Suite de DÉPART (origin/main) : **2 535 passed / 15 failed PRÉ-EXISTANTS / 38 skipped** —
  échecs notés (copilote_moteurs ×5, copilote_v1_run_scope ×2, non_contradiction ×5,
  deps_declared, front_reliquats, plu_destinations) : AUCUN touché par ce mandat, revérifiés
  identiques en fin (voir bilan).
- Lu : comptes-rendus 1→3/P, `registre/donnees.py` (168 données : 113 moteur · 52 passe-plats ·
  3 constantes), `registre/moteurs/` (5 modules, 27 fonctions publiques), `moteurs.csv`
  (30 moteurs), les références connues (loi 2025-1129, CDAC, ZFANG 2026-421, calibration 23 PLU +
  Saint-Philippe RNU, prix de secteur, seuil 30, m36-l2f-2026).

## Lot 1 — L'inventaire des calculs ✅ (commit « CIRCUIT-4 lot 1 »)

- `src/labuse/regles/` : le REGISTRE DES RÈGLES. `FicheRegle` (formule codée FR+math écrite
  DEPUIS le code, entrées, classe, référence à extrait daté, verdict, exemple témoin, valide_par,
  verifie_le) + VERROUS à la construction : « conforme »/« partiel » sans extrait daté =
  ValueError (règle 2) ; choix sans définition = refusé ; une donnée couverte deux fois = refusé.
- **64 fiches** (une par CALCUL, fichier `<donnee_id>.py`) couvrant les **113/113** données
  `calcul == "moteur"` et les **27/27** fonctions de `registre/moteurs/` (0 manquant des deux
  côtés, vérifié).
- `docs/CIRCUIT/CALCULS-INVENTAIRE.md` généré DEPUIS les fiches (classement lot 1.2 + couverture).
- Garde 1.3 : `tests/test_circuit4_lot1.py` (couverture bilatérale + verrous).

## Lot 2 — Les règles externes ✅ (commit « CIRCUIT-4 lot 2 »)

- **Agent « règle »** : surface `agent_regle` (SURFACES) + `src/labuse/agent_regle.py` — même
  façade qu'agent_source (web_search natif, JSON strict, ANTI-INVENTION : verdict positif sans
  référence datée FORCÉ à introuvable, `page_js` noté « navigateur nécessaire ») ; écrit
  `regle_agent_rapports` + journal ; n'écrit JAMAIS les fiches (le code est la vérité, un humain
  relit) ; `fiches_a_reverifier(180 j)` prépare le job 5.4.
- **Extraits réellement lus** (Légifrance, service-public, INSEE, SDES, data.gouv — lu_le
  2026-09-06), cités dans les fiches :
  R111-22 (texte intégral SDP) · CGI 1635 quater H (892/1 011 €, vigueur 01/07/2026) + I
  (abattement 50 %) + service-public A15416 (07/01/2026 : piscine 251, parking 2 928, PV 10,
  éolienne 3 000 — TOUTES les valeurs du YAML vérifiées) · L151-36 (loi 2025-1129 art. 20,
  vigueur 28/11/2025 : « à moins de 800 m », max 1 place) + L151-35 (0,5 aire) · L752-1
  (« supérieure à 1 000 m² ») · R151-18 (zones U) · Filosofi 200 m (i_est_200, seuil 11 ménages)
  · SIRENE tranches d'effectifs (00→53) · INSEE c1059 (logement vacant) · SDES Sitadel (DOC,
  date réelle) · DVF data.gouv (décret 2018-1350, DOM couverts, màj 07/04/2026) · règlements PLU
  calibrés (mixité Le Tampon Uc2 / L'Étang-Salé AU 1.3 / Saint-Paul 1 500 ; hauteur U1a par
  bande) · L121-45 (50 pas, 81,20 m) · décret ZFANG 2026-421 (les 6 communes du seed, EXACTES).
- `docs/CIRCUIT/REGLES-ECARTS.md` : **E1→E7** + références des passe-plats vérifiées (50 pas,
  ZFANG, DPE métropole → question DOM posée, PPR) + introuvables avec ce qui a été tenté.

## Lot 3 — Méthodes, choix, modèle ✅ (commit « CIRCUIT-4 lot 3 »)

- Méthodes ancrées à extrait technique : `percentile_cont` (PostgreSQL, interpolation linéaire)
  pour TOUTES les médianes ; min-max (formule MinMaxScaler scikit-learn) pour le composite ;
  médiane tronquée 5 % (sector_price, seuils LABUSE mesurés dits).
- Modèle (3.3) : fiche `tier_opportunite` aux MÉTRIQUES du modèle SERVI — m36-l2f-2026, artifact
  gelé sha256 00a58008… (12/07/2026), WoE + logistique C=5.0 seed 974, calibration isotonique
  2025, recalage d'intercept seul par run ; walk-forward RR@1158 hors copro 9,41/8,61/8,63
  (IC95), ECE ≤ 0,0033 (extraits SCORING_SPEC §4) ; golden 119.
- `docs/CIRCUIT/CHOIX-LABUSE.md` : **49 choix** écrits (définition + pourquoi + validation) +
  choix transverses (isochrones IGN Géoplateforme à dégradé honnête, hypothèses de faisabilité,
  cadences proposées) — pour Vic, rien de bloqué.

## Lot 4 — Les exemples témoins ✅ (commit « CIRCUIT-4 lot 4 »)

- `tests/regles/` : **18 fichiers, 57 témoins** — chaque témoin RECALCULE la donnée depuis les
  entrées brutes avec la formule de la référence (statistics, pyproj, recomptes à la main,
  géométries seedées), JAMAIS via le moteur vérifié. Sélection : taxe ligne à ligne ; enveloppe
  SDP posée dans l'ordre du règlement ; parts de zonage 20/10/50/20 ; ppr 3/4 = 75 % ; zone
  dominante 60/40 par aires ; KNN vs pyproj (±1 m) ; médianes vs statistics.median ; filtre DVF
  gardées+écartées=total avec motifs ; point mort 1/3 ; bascules de tiers 1/3 ; périmètre
  WHERE_AFFICHEES ≡ prédicat Python.
- 4.2 : xfail STRICT motivé sur E1 (levé au lot 6). 4.3 : suite normale (testpaths).
- Garde lot 4 : toute fiche conforme/choix pointe un test qui EXISTE (fichier + fonction
  vérifiés) ; **3 gaps assumés et verrouillés** : `divisible_classe` (builder q_v10 gelé),
  `ecart_candidat_pct`, `evenements_proprietaire_liste` (assemblage réseau) — témoins liés à
  leur chantier. Témoins « existence/clé vide » assumés pour 4 délégations lourdes
  (patrimoine PM, notifications, copilote facette, compteurs délégués) — l'égalité complète de
  la facette copilote est déjà verrouillée par la suite copilote existante.
- TROUVAILLE en écrivant les témoins : la fiche `population_zone` initiale (écrite lot 1) disait
  « carreau intersectant » quand le CODE agrège au CENTROÏDE du carreau — corrigée depuis le code
  (la règle du mandat « formule écrite depuis le code » a fonctionné) ; témoin épinglé.

## Lot 5 — La règle sur le circuit ✅ (commit « CIRCUIT-4 lot 5 »)

- 5.1 `registre_chiffres` + `classe_regle`/`verdict_regle`/`valide_par`/`verifie_le`/
  `reference_regle` (jsonb), ALTER idempotent, `labuse registre sync` les écrit depuis les fiches.
- 5.2 `/admin/circuit` sert `regle` par donnée (TIROIR DE TRACE : ligne « règle » colorée +
  lien référence) ; `/admin/circuit/robinet/{id}` sert la règle par chiffre → bloc « La règle
  derrière ces calculs » dans `Detail.tsx` (l'accroche CIRCUIT-P branchée) : conforme mint ·
  écart rouge · introuvable/partiel ambre · choix gris (définition au survol) · modèle mauve ;
  « référence ↗ » (titre, article, version, extrait au survol). Le détail robinet met l'écart
  dans son ctx (détail ≡ liste, leçon P3).
- 5.3 Résumé : « écarts à la règle » (rouge — robinets servant une donnée de fiche
  verdict=ecart, dans l'ÉTAT et le Résumé) et « choix LABUSE à confirmer » (gris — fiches choix
  `en_attente`, ligne + navigation). Test d'égalité stricte P3 mis à jour (attendu dérivé des
  fiches — le code est la vérité).
- 5.4 Job `regles-references` (mensuel) : EXISTE au registre, **DÉSACTIVÉ** (jamais posé au
  crontab — même doctrine qu'agents-sources, verrou test lot 8 mis à jour) ;
  `jobs_impl.regles_references` relance les agents sur les références > 6 mois (rapports
  seulement).

## Lot 6 — L'arithmétique pure ✅ (commit « CIRCUIT-4 lot 6 »)

- **A1 (= E1)** : `proche = d <= 800` → `proche = d < 800` (app.py) — L151-36 dit « à MOINS de » ;
  avant/après : SEUL d = 800 exact change (distance entière) ; xfail STRICT du lot 4 LEVÉ
  (le témoin passe au vert) ; fiche `distance_arret_m` → verdict conforme.
- `docs/CIRCUIT/CORRECTIONS-ARITHMETIQUE.md` : la correction + ce qui n'a PAS été corrigé (YAML
  H/I = documentaire → Vic ; E2 SDP = lecture de texte → Vic). Les 57 témoins indépendants sont
  tombés justes du premier coup face au moteur — aucune autre erreur d'arithmétique détectée.

## Verdicts finaux (64 fiches, 113 données)

**17 conforme** (extraits datés) · **5 partiel** (partie non implémentée, dite) · **0 ecart**
(E1 corrigé) · **33 choix_assume** · **1 modele_valide** · **8 reference_introuvable** (tenté
noté : BD TOPO attrs, PVGIS, Cerema ENAF, statuts d'occupation INSEE, EGOUL détail, loyers
DOUTE, bilan promoteur sans texte canonique).

## Décisions prises en autonomie (récapitulatif)

1. **Une fiche = un CALCUL** (couvrant ses données via `donnees`) — le fichier porte la donnée
   représentative ; « une fiche par donnée » est satisfait par le mapping (garde bilatérale).
2. **Choix « à confirmer » : ligne du Résumé + badges, SANS griser l'état des robinets** — 30
   fiches choix en_attente toucheraient l'essentiel de la colonne droite ; on ne noie pas le
   diagramme pour des décisions non bloquantes (la ligne grise « À décider » les porte toutes).
3. **Fiches conformes des méthodes ancrées sur la doc technique de l'implémentation**
   (PostgreSQL percentile_cont, scikit min-max) — la « source statistique ou technique » du
   mandat ; les seuils maison restent des choix dits.
4. **L'agent règle n'écrit jamais les fiches** (rapports en base + journal seulement) — le code
   est la vérité, la mise à jour d'une fiche reste un geste humain relu.
5. **P3 strict test étendu aux écarts de fiches** (l'attendu se dérive tables + registre +
   fiches) — jamais ajusté « pour passer » : la dérivation reste indépendante du rendu.
6. **Job 5.4 jamais posé au crontab** (comme agents-sources, décision Vic n° 8 étendue à l'IA
   des règles).

## Ce qui n'a pas pu être fait (écrit, pas caché)

- Exemples témoins « par commune » du mandat (BW0917, un projet témoin de taxe PAR commune, une
  parcelle U par commune calibrée) : la base de TEST n'a pas les parcelles réelles — les témoins
  sont épinglés sur clés SYNTHÉTIQUES sèches (mêmes formules, recomptes indépendants) ; un tour
  « -m local » sur la base réelle pourra épingler BW0917 (dette écrite).
- 8 fiches restent `reference_introuvable` (listées, avec ce qui a été tenté) ; 3 choix sans
  témoin (verrouillés dans la garde avec motif).
- Le badge de règle est branché au TIROIR DE TRACE et à la page robinet (admin) ; les surfaces
  CLIENT (fiche parcelle) lisent le registre via la base sync — brancher un badge client est un
  choix d'UI produit laissé à Vic (les données sont prêtes : `registre_chiffres.*_regle`).
- DPE outre-mer : question posée (REGLES-ECARTS) — mention « référentiel métropole » à trancher.

## Bilan des suites (méthode A/B sur base FRAÎCHE)

- La comparaison « avant/après » sur la base de test ACCUMULÉE s'est révélée non significative
  (la suite de main elle-même dépend de l'état de la base : 15 échecs sur base chaude, 27 sur
  base fraîche). Preuve rigoureuse faite en A/B : base labuse_test RECRÉÉE + schéma bootstrappé,
  suite jouée sur le point de base de la branche (worktree `80fe9fee`) PUIS sur `feat/circuit-4` :
  - main fraîche : **27 failed / 2 522 passed** ;
  - branche fraîche : **27 failed / 2 602 passed** (+80 tests du mandat) — **le MÊME ensemble
    d'échecs, zéro régression** (le 28ᵉ était `test_plu_destinations`, causé par un artefact de
    build LOCAL non tracké `src/labuse.egg-info/SOURCES.txt` — purgé, test vert ; il polluait déjà
    la baseline chaude du départ).
- LEÇON D'ISOLATION (payée puis corrigée au lot 6) : la première version des témoins créait des
  tables minimales RIVALES (parcel_renouvellement…) et faisait des DELETE globaux (pige) — 15
  faux échecs en aval. Corrigé : DDL RÉELLES importées de leurs modules (jamais de rivale),
  table scratch pour le segment renouvellement, corpus FUSIONNÉ (pas de delete) pour le témoin
  Radar, nettoyage systématique des seeds géométriques. Les témoins sont désormais sans legs.
- tsc + vitest circuit : verts. Rien n'est mergé.

## Ce qui reste à Vic, après

- Trancher `REGLES-ECARTS.md` (E2 SDP en tête — libellé ou coefficient, avec Stéphanie),
  confirmer/corriger `CHOIX-LABUSE.md` (49 lignes, dont les hypothèses de faisabilité).
- Décider du badge de règle côté client (les données sont en base).
- Merger 1 → 2 → 3 → P → 4 ; relancer `labuse registre sync` en prod (colonnes de règle).
