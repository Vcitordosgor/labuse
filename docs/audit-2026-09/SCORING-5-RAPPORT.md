# SCORING-5 — Score LABUSE + Signal de mutation : rapport de conception

**Date : 21/09/2026 · Branche : `audit/scoring-5` · Mandat : audit + conception en LECTURE SEULE.**
Rien de servi n'a changé (`q_v11_m137` reste servi). Aucun code de production, aucun run, aucune ingestion, aucun entraînement.
Méthode : les rapports du §2 du mandat sont cités (chemin + section) et jamais redémontrés ; les seules mesures nouvelles sont des SELECT reproductibles (annexe A) sur la base `labuse` au 21/09/2026.

> **Décisions actées par Vic (21/09/2026 — SCORING-5-RETOUR)** — cadre gelé du présent rapport :
> architecture **GO** (Score LABUSE principal + Signal de mutation secondaire) · combinaison **V3 lexicographique** (V2 bonus écartée) · Signal = **recette q_v14**, grain annuel + re-score mensuel · plafond « sans bloc propriétaire personne physique » = **borne assumée**, pas un défaut · assemblage = **information seule en V1** · ordre : **`residuel-serve` recalculé post-calibrage → ablations → q_v15 → bascule** · **bandes et barèmes non fixés sur le papier — ils sortent des parcelles témoins** (`reports/scoring-5/TEMOINS.csv`).

**Écarts constatés au brief** (une ligne chacun — ils corrigent les acquis du §2 du mandat, le rapport cite partout les emplacements réels) :
1. `SOURCES-LABUSE-tableau.md` n'existe pas ; le tableau des sources réel est `docs/audit-2026-09/SOURCES/SOURCES-AUDIT.md` + `.csv` (121 sources, 63 colonnes). Il n'y a **pas de colonne littérale « déclenche un run ? »** — ce rôle est tenu par `viz_scoring` (18 sources) et `moteurs` (38 sources), confirmées par le code en §8.
2. Les « 10 `a_faire` » du brief ont en base le statut **`partenariat_requis`** (`SELECT status, count(*) FROM data_sources GROUP BY 1` → connecte 89 · partenariat_requis 14 · alias 6 · retiree 5 · hub 4 · manuel 2 · interne 1).
3. **`feat/paliers-1` est mergée dans main** (merge `b6aec2bd` dans l'historique) : `statuts.assign_paliers` v2 et `config/scoring_client.yaml → paliers` sont dans le worktree, branchés pour la seule recette q_v14 (`p_v2/pipeline.py:487-489`).
4. `SCHEMAS.csv` compte 1 004 lignes de champs / 87 sources distinctes (et non 841/93).

---

## 1. Verdict

**GO** sur « Score LABUSE principal + Signal de mutation secondaire », à trois conditions et une attention :

1. **Le résiduel doit être recalculé post-calibrage avant toute bascule** (décision Vic déjà prise, 21/09) : le Score LABUSE repose entièrement sur `zonage.py` calibré, or le résiduel servi (`m135-run2-ile`, run_seq 2) a été calculé les 22-23/08, AVANT le calibrage (annexe A.6).
2. **Le Signal repart de la recette q_v14** (AUC 0,626, précision Priorité 30,5 %, walk-forward > q_v12 sur 5 plis/6 — SCORING-4.md, « Résultat d'ensemble ») — pas d'une page blanche.
3. **Le plafond « sans bloc propriétaire personne physique » borne le Signal** : 81 % des parcelles sont en personne physique avec zéro donnée de cycle de vie (SCORING-RAPPORT §B.5), et aucun candidat n'a dépassé AUC ~0,63 sans lui (COMPTE-RENDU-SCORING-2, recommandation finale). Le produit se vend comme « intérêt foncier sûr + signal de mouvement modeste », jamais comme une prédiction forte.

Attention : la cascade actuelle exclut sur zonage A/N dès 90 % de recouvrement ; les 3 112 parcelles à 90-99 % (annexe A.2) ont une portion U exploitable et doivent passer en pénalité d'assiette (§5).

La contrainte d'exploitation (§12 du mandat) est **résolue par l'architecture** : le Score est déterministe et se calcule sans run ; le Signal coûte ~10 min/mois (scoring mesuré 226-505 s + features) ; la cascade — 95-97 % des ~5 h mesurées — ne se rejoue qu'en delta quand une couche change ; le VPS ne recalcule plus, il reçoit (`deploy/scripts/sync-run.sh`, existant). Détail complet en §8.

---

## 2. Score LABUSE V1 — la spec

**Question à laquelle il répond** : « à quel point cette parcelle mérite-t-elle d'être étudiée comme opportunité foncière ? » Intérêt foncier intrinsèque, orienté production de logement (le produit LABUSE). Ce n'est **pas** une probabilité de vente : aucune feature de marché n'entre dans le chiffre (le marché est information fiche et matière du Signal), aucune feature propriétaire n'y entre du tout.

**Identité** : `score_labuse` ∈ [0, 100] ou `non_calculable(motif)` · version `SL-1.x` + hash du barème (YAML dans `config/`, même mécanique que `config/scoring_client.yaml` et `config/plu_zonage.yaml`) · déterministe : fonction pure de caches par parcelle, aucun rang, aucun percentile, aucun quota — le contrat du §11 du mandat est satisfait par construction.

### 2.1 Méthode de calcul — trois temps et une information

```
score = clip( barème_capacité(SDP_résiduelle_sur_assiette) × coef_faisabilité , 0, 100 )
```

**Temps 1 — l'assiette exploitable (m²).** Surface de la parcelle moins les emprises sous contrainte **géométrique certaine** : portions A/N (le clipping existe déjà : `cascade/layers/phase1.py:312-324` clippe l'emprise en zone mixte), emplacements réservés, EBC, PPR rouge, PEB A/B, bande littorale, marchepied DPF. Principe gravé du §9 : une contrainte partielle **réduit l'assiette**, elle n'exclut jamais. Assiette nulle après contraintes certaines → c'est la cascade (classe A, §5) qui écarte, pas le Score.

**Temps 2 — la capacité (0-70 pts).** SDP résiduelle calculée par `faisabilite/zonage.py` **post-calibrage** sur l'assiette (colonnes de `parcel_residuel_runs` : `sdp_residuelle_m2`, `taux_emprise_pct`, `sous_densite`, `capacite_estimee`, `cause` — `faisabilite/residuel.py:80-149`). Barème par paliers **métier** en logements-équivalents, pas en points de fausse précision : ~80 m² SDP ≈ un logement produit vendable, ~400 m² ≈ petit collectif, ~2 000 m² ≈ opération. Les bornes exactes des paliers sont une décision Vic (§17 du mandat) ; la structure (paliers saturants, pas de linéarité infinie) est la proposition. Justification métier : la SDP résiduelle **est** ce que le client achète — c'est déjà la logique du `residuel_socle` de la cascade (`etage0_ext.py:162-190`), qui sort de la cascade et devient le cœur du Score. Zone AU fermée / au statut inconnu : capacité **différée** — barème plafonné (proposition : ≤ 50 % du barème ouvert), pas exclue ; renvois AU→U déjà portés par `zonage.py:205-213`.
Parcelle bâtie : la **capacité** reste nette du bâti (le résiduel croise BD TOPO + CoSIA révélé, `residuel.py:44-50, 110-117` ; le densifiable est capté par `sous_densite`) — mais le bâti n'est pas gratuit pour autant : il entre dans le **coefficient de faisabilité** (temps 3, correction Vic), jamais dans l'assiette. L'entérinement de PALIERS-1 tient toujours : « déjà bâtie » ne redevient jamais une exclusion ni un déclassement (déclassées gardées = tête ×2,4 à précision constante — PALIERS-1.md, Lot A).

**Temps 3 — le coefficient de faisabilité (0,4-1,0).** Produit de facteurs gradués, **plancher global 0,4** : une difficulté ne devient jamais une exclusion silencieuse (§9 du mandat).
- pente (RGE ALTI, 98,1 % couverte — SCORING-RAPPORT §B.1) : ≤15 % → 1,0 ; 15-30 % → intermédiaire ; >30 % → fort malus (seuils actuels de la couche `pente`, `phase1.py:860-907`, comme point de départ) ;
- forme (allongement/largeur — seuils existants `config/seuils_geometrie.yaml`, section `etage0_ext`) ;
- accès à la voie (BD TOPO, couche `acces` `phase1.py:1027-1050`) : voie ≤10 m → 1,0 ; non identifié → malus + libellé « accès à la voie non identifié » (pas un couperet : la donnée BD TOPO peut manquer) ;
- risques partiels non déjà déduits de l'assiette (PPR bleu, aléas moyens — gradations existantes `phase1.py:641-727`) ;
- servitudes fortes non géométriques (SUP t5/ac2/as1 — sévérités existantes `etage1.py:118-133`) ;
- **bâti existant (correction Vic, SCORING-5-RETOUR)** : un promoteur paie la démolition (coût ∝ volume ≈ emprise × hauteur), l'éviction ou le relogement éventuel, et le délai qui va avec — la capacité nette du bâti ne suffit donc pas. Facteur gradué par emprise bâtie (`taux_emprise_pct` du résiduel) et hauteur LiDAR (`batiment_hauteur_lidar`, 70,3 %) : nu → 1,0 · emprise ≤ 20 % de l'assiette → 0,9 (démolition légère) · 20-50 % → 0,8 · > 50 % ou ≥ R+2 → 0,65 (opération de démolition-reconstruction). Valeurs provisoires — **calées sur les témoins**, comme tous les crans ; hauteur manquante → cran par l'emprise seule, la couverture baisse.

**Temps 4 — le contexte : information seule en V1 (correction Vic, SCORING-5-RETOUR).** Le « ±8 plafonné » initialement proposé n'avait pas de justification métier défendable (pourquoi 8 et pas 5 ou 15 ?) — règle du mandat : aucun chiffre sans justification. Et le dynamisme de marché vit déjà dans le Signal (`rot_*`, `med_pm2_*`, voisinage) : l'additionner au Score serait un double compte. En V1, permis du secteur et rotation DVF s'affichent en **information fiche** (« secteur actif : 14 permis en 2 ans ») sans entrer dans le chiffre. Ré-examen possible en V1.1, sur témoins, si un cas montre qu'un contexte scoré sépare réellement mieux.

### 2.2 Axes instruits — retenus / écartés

- **5.1 Capacité réglementaire : RETENU, c'est le cœur** (temps 1+2). Données : `zonage.py` + 1 832 feuilles `valide`. ⚠ Nuance mesurée (RESIDUEL-1 lot 1, `SCORING-5-RETOUR.md` §2) : seul l'**overlay** est validées-only (`zonage.py:303-311`) ; la **base** des ZoneRules lit la valeur numérique de toute feuille (`_val`, `zonage.py:105-116`) et **95 feuilles `propose` numériques (hauteurs, CES, retraits, pleine terre, stationnement) branchent le calcul de SDP** — à trancher avant le run résiduel (valider ces 95 feuilles, ou acter le comportement). GPU, prescriptions, PPR, PEB, DPF, 50 pas, assainissement (zonage GPU 4/24 communes, 278 685 objets — source id 63). **Point de branchement Gabarit** : le futur moteur remplacera le couple (assiette × `zonage.py`) par sa sortie par parcelle, même contrat de sortie (SDP résiduelle sur assiette) — rien ne l'attend.
- **5.2 Capacité foncière : RETENU** (temps 2 + état). Emprise bâtie BD TOPO + CoSIA (couverture CoSIA : 1 947 019 lignes `parcel_cosia_couverture`, annexe A.5), hauteur LiDAR 303 452 parcelles (70,3 %), OCS GE : `parcel_ocsge` couvre **100 % des 431 663 parcelles** (annexe A.5) — utilisée comme **contrôle qualité** de l'emprise et information « artificialisé officiel », pas comme axe séparé (redondant avec l'emprise bâtie). **RNB vs BD TOPO** : le RNB (414 081 bâtiments actifs, 817 506 liens `rnb_rattachement_bdtopo`) n'apporte ni géométrie nouvelle ni hauteur ; son apport est la **clé stable inter-millésimes** et la fraîcheur en flux continu → croisement/contrôle, pas une feature. Nu/bâti : pour le Score affiché, l'état **courant** est le bon (l'as-of ne sert qu'au backtest du Signal — le Score n'est pas backtesté contre des ventes, §13 du mandat).
- **5.3 Faisabilité physique : RETENU** (temps 3). Le MNH LiDAR 50 cm (~5 406 parcelles, périmé) : rien n'est bâti dessus, conformément au mandat.
- **5.4 Assemblage : PAS ENCORE comme composante scorée.** Verdict motivé : le « même propriétaire » n'est observable que pour les personnes morales (millésimes DGFiP 2019-2024, 81 161 liens en 2024 — annexe A.5) ; un axe d'assemblage scoré avantagerait mécaniquement ~19 % du parc sans justification métier, sur une donnée périmée de 2 ans. En revanche : **DFI filiation est mûre comme information et comme candidate Signal** — 409 623 liens, 471 129 IDU, `date_validation` continue 1989→2025 (~6-16 k/an ; annexe A.4) : l'as-of est propre, ce que SCORING-4 (« En passant ») identifiait déjà comme meilleur candidat suivant. En V1 : affichage fiche (divisions récentes, voisines même PM, contiguïté) + point de branchement défini (axe A additif ≤10 pts, activé seulement après mesure sur témoins).
- **5.5 Contexte : INFORMATION seule en V1** (temps 4 — correction Vic). ZAC : **aucune table en base** (annexe A.7) → hors V1. ORT (19 communes) / PLH (5 EPCI) / ENAF (24 communes) : maille communale, information fiche, pas des composantes du score parcellaire.
- **5.6 Hors axes** : rien de mieux trouvé qui ne soit déjà couvert. Écartés explicitement du Score (corrélé ≠ intérêt foncier) : Filosofi, QPV, socio-démographie, NDVI/canopée (mortes — SCORING-RAPPORT §B.2), piscines, Cartofriches (0,15 % informatif), accessibilité OSM, prix locaux (information fiche), ZFANG, zonage ABC (fiscalité de l'acquéreur = information fiche, pas intérêt foncier).

### 2.3 Manquants, couverture, confiance — les trois volets

- **Entrées critiques** → `non_calculable`, dit tel quel : zone PLU non résolue. Effectif : causes M125 `zone_non_resolue` 12 566 + `hors_plu` 4 397 = **16 963 parcelles (3,9 %)** affichées « analyse non calculable : zone PLU non résolue » (ventilation K3 — COMPTE-RENDU-SCORING-2, lot K3).
- **Entrées non critiques absentes** (hauteur LiDAR, CoSIA, accès) → le score se calcule sur le reste, la **couverture** baisse. Absence de donnée ≠ mauvais score : un facteur manquant vaut 1,0 (neutre), jamais un malus.
- **Trois volets stockés séparément** : `score` (0-100 / non calculable + motif) · `couverture` (% de composantes calculées + liste FR des manquantes) · `qualite` (millésime et fraîcheur de chaque entrée : date d'approbation PLU, ortho 2025, dernière intégration DVF, millésime PM…). Jamais mélangés dans le chiffre.

### 2.4 Explicabilité

Chaque composante porte un libellé FR client (leçon PALIERS-1, Lot A0 : « état bâti/nu reconstruit à la date » est illisible) : « 480 m² de droits à construire restants », « 30 % de la parcelle en zone A, déduits », « pente forte (32 %) », « bâti existant sur 40 % de la parcelle — démolition à prévoir », « accès à la voie non identifié ». Le détail +/− est la décomposition littérale du calcul — pas un SHAP ; le contexte (« secteur actif : 14 permis en 2 ans ») s'affiche à part, hors calcul.

### 2.5 Validation sans label (§13 du mandat)

Pas de vérité terrain « bonne opportunité » : pas de label fabriqué. V1 valide par :
- **tests de monotonicité** (plus de SDP résiduelle à contraintes égales ⇒ score ≥ ; assiette réduite ⇒ score ≤) — automatisés (§10) ;
- **liste de parcelles témoins** évidentes (très bonnes / très mauvaises), à constituer avec Vic — geste du mandat suivant ;
- **benchmark externe** : potentiel foncier Région, comparaison et challenge uniquement — jamais une feature (déjà la doctrine : couche `potentiel_foncier_region` = POSITIVE informative, `phase2.py:119-137`) ;
- **à terme** : favoris/projets/CRM/retours terrain (sélecteur 7 états de SCORING-3 en spec ; `parcel_feedback` = 0 ligne aujourd'hui — SCORING-RAPPORT §F) : schéma prévu, rien codé ici. Seuil d'usage : ≥ 200-300 étiquettes, ≥ 30 par classe (SCORING-RAPPORT §F.4).

---

## 3. Signal de mutation V2

**Cible exacte** : P(vente foncière onéreuse L2-F dans les **12 mois suivant la date du score**), hors ventes d'unités de copropriété (cible large voulue par Vic — inchangée depuis le servi, `ext_sql.py:224-236`). À l'entraînement, grain parcelle × année avec features as-of 01/01/Y — ce qui **est** « 12 mois suivant la date du score » quand la date de score est le 01/01.

**Périodicité des snapshots — chiffrée, et tranchée.** Dataset actuel : 3 453 304 lignes parcelle-année 2017-2024 (SCORING-RAPPORT §A.2), cache `enrichi_2017_2026.pkl` 2,1 Go (SCORING-4, « Reproduction »).
- snapshots trimestriels : ×4 ≈ 13,8 M lignes, ~8,4 Go de cache, construction as-of des features à rejouer par date (le rebuild features complet tient en minutes par date — §8 —, soit de l'ordre d'heures cumulées par re-freeze) ;
- mensuels : ×12 ≈ 41,4 M lignes, ~25 Go — même logique.
**Recommandation : NE PAS multiplier les snapshots aujourd'hui.** Raison de fond, pas de coût : 18 des 29 features du servi sont à millésime unique (SCORING-RAPPORT §B.4) et DVF est publiée avec ~6 mois de latence (SCORING-RAPPORT §H.2) — un snapshot d'avril a le même DVF que celui de janvier ; seul Sitadel (mensuel) bougerait. Le gain d'information intra-annuel est quasi nul tant que les seules sources datées sont DVF et Sitadel. À re-chiffrer si des features datées à haute fréquence entrent (BODACC, DFI). En attendant : **grain annuel d'entraînement + re-score mensuel du modèle gelé** (mécanique existante — SCORING-RAPPORT §H.2 : ~220 parcelles bougent par mois, re-score après `ingest-sitadel`). La colonne 24 mois existe déjà (p_24m ; AUC 0,642 à horizon 24 m — NOTE-DE-VERSION-q_v14.md) et reste stockée.

**Dataset et hygiène** : banc K0 inchangé — entraîner ≤2023 · calibrer 2024 · tester 2025 (COMPTE-RENDU-SCORING-2, protocole) ; ventes groupées flaguées, ventes à clients LABUSE exclues ; la performance « 2025 » du servi n'est jamais une référence (isotonique servie calibrée sur 2025 — SCORING-RAPPORT §A.2).

**Features** : base = la recette q_v14, 35 features + 4 croisements (`qv12.py:59-136` + `qv14.py:67-103`), gains tous prouvés au K0 (SCORING-4). Gardées telles quelles, y compris `ventes_pm_secteur_36m` (garde-fou ECE PM non déclenché, s'améliore — SCORING-4, « Ce qui a été écarté »). Supprimées et non réintroduites : ndvi, canopée, accès équipements, friche (K2), les 5 `retired`, `dp_parcelle_36m`, `pc_caduc_asof`, tout le bloc D dirigeants (DONNEES-1, lots C-D). **DPE : hors** — 1 123 lignes / 20 communes / 0,26 % de couverture parcelle (annexe A.5), très en dessous de la règle des 5 %. **Radar : hors** (7 rattachées / 0 paire — SCORING-RAPPORT §E). Candidates à tester au banc dans le mandat suivant (§9) : `division_dfi_36m` (as-of daté propre, annexe A.4), `dernier_depot_comptes` BODACC (14 078 dépôts / 1 938 SIREN — segment PM seulement), re-mesure de `ventes_pm_secteur_36m` quand un millésime PM 2025+ existera. **Impact des millésimes PM arrêtés à 2024** : toute feature propriétaire PM est périmée de 2 ans au scoring 2026 → sous-estimation du geste (réserve déjà posée par DONNEES-1, lot C) ; à dire dans la note de version du Signal.

**Modèle** : hasard en temps discret L2-sur-WoE + **isotonique par segment** (bâti/nu/PM/copro) calibrée sur l'année de calibration — les fits séparés par segment sont réfutés (K4), le GBM est réfuté (K5) : ne le relancer que sur raison nouvelle.

**Protocole de calibration** : isotonique ajustée sur 2024 (année de calibration), jamais sur l'année de test ; en service, re-score mensuel sans recalage sauvage (recalage d'intercept = mécanique m36 ; pour la recette q_v14 l'isotonique est gelée par segment, application par ligne — `p_v2/pipeline.py:296-320`).

**Protocole de validation** : K0 + walk-forward 6 plis (2020→2025) ; métriques : ECE global et par segment (≤ 0,01 par segment), Brier, lift décile, précision@100/500/1000/2000 (médiane par commune), recall de tête, part des mutations captées, stabilité par commune / zonage / période / type de parcelle ; règle de verdict pré-enregistrée avant mesure (méthode DONNEES-1, lot G).

**Restitution client** : trois classes — **Signal fort (p ≥ 0,20) · moyen (0,10-0,20) · faible (< 0,10)** — ce sont les seuils absolus déjà décidés et mesurés (PALIERS-1 : précision 34,4 % ≥ 20 % sur 119 parcelles sans déclassements ; effectifs q_v14 : 114 / 631 / 280 658), avec l'anti-churn 0,18/0,09 existant (`config/scoring_client.yaml`). Le churn annuel ~79 % est une rotation as-of de fond, pas un défaut du modèle (PALIERS-1, Lot A) — assumé et dit. Badge « En vente » (Radar, 7 parcelles) : au-dessus, factuel, hors Signal.

---

## 4. Tableau des features

Couvertures : annexe A.5 sauf mention. Dénominateur parcelles = 431 663 (`parcels`). « as-of » = historique reconstructible pour le backtest.

### 4.1 Score LABUSE (déterministe — pas de backtest, le risque de fuite ne s'applique pas)

| Feature | Rôle | Source | Table | Couverture | Millésime / fraîcheur | Verdict |
|---|---|---|---|---|---|---|
| SDP résiduelle sur assiette | capacité (cœur) | PLU calibré | `parcel_residuel_runs` (run post-calibrage **à recalculer**) | 100 % avec cause M125 | calibrage 08/2026 | **GO sous condition** (recalcul décidé) |
| assiette exploitable (clips A/N, ER, EBC, PPR rouge, PEB, DPF, littoral) | capacité | GPU/DEAL | `spatial_layers`(+`_sub`) | zonage 99 % (SCORING-RAPPORT §B.1) | sync-gpu mensuel | GO |
| statut AU (ouverte/fermée/renvois) | capacité différée | GPU + `plu_zonage.yaml` | `parcel_au_statut` | 24/24 communes | calibrage | GO |
| pente | faisabilité | RGE ALTI 5 m | `parcel_terrain` | 98,1 % | quasi immuable | GO |
| forme (largeur/allongement) | faisabilité | cadastre | `parcels` (géométrie) | 100 % | vivant | GO |
| accès voie ≤10 m | faisabilité | BD TOPO | couche `acces` | île | édition 2026 | GO (manquant = neutre + mention) |
| emprise bâtie | occupation | BD TOPO + CoSIA | `p_model_bati`, `parcel_cosia_couverture` (1 947 019) | ~100 % | CoSIA 2025 (20 cm) | GO |
| hauteur bâti | saturation | LiDAR HD | `batiment_hauteur_lidar` | 303 452 = 70,3 % | 2023-2024 | GO (manquant → couverture) |
| OCS GE artificialisation | contrôle qualité | IGN OCS GE 2.0 | `parcel_ocsge` | **100 %** | 2017 + 2022 | GO (contrôle, pas axe) |
| RNB | clé stable bâti | RNB flux | `rnb_batiments` (414 081), `rnb_rattachement_bdtopo` (817 506) | — | flux continu | GO (croisement, pas feature) |
| DVF secteur (rotation, prix) | information fiche (hors calcul V1) | DVF | `dvf_secteur_medianes`, `p_model_ext_dvf` | 94-100 % | latence ~6 mois | GO (information) |
| Sitadel secteur 24 m | information fiche (hors calcul V1) | Sitadel | `sitadel_permits` (50 545) | île | mensuel, garde fraîcheur bloquante | GO (information) |
| emprise bâtie × hauteur (facteur bâti) | faisabilité | BD TOPO + CoSIA + LiDAR | `parcel_residuel_runs.taux_emprise_pct`, `batiment_hauteur_lidar` | ~100 % / 70,3 % | CoSIA 2025, LiDAR 2023-24 | GO (hauteur manquante → cran par l'emprise) |
| DFI filiation / contiguïté / voisines PM | information + branchement | DGFiP | `dfi_filiation` (409 623 liens) | 471 129 IDU | datée 1989→2025 | **ATTENTION** : info V1, axe scoré = plus tard |
| ZAC, OPAH, ZAE, ENS, ZPPA… | — | `partenariat_requis`, tables vides | — | 0 | — | **NO-GO** (« plus tard, si ingérées ») |
| Fichiers fonciers / DV3F / LOVAC | — | Cerema, convention non instruite | **aucune table** (annexe A.3) | 0 | — | **NO-GO** |

### 4.2 Signal (recette q_v14 conservée + candidates)

| Feature | Rôle | Table source | Couverture informative | as-of / fuite | Verdict |
|---|---|---|---|---|---|
| `tenure_bin_v2` (censoring K1c) | D | `p_model_ext_mut_all` (DVF 2014→) | 17,1 % informatif — plafond DGFiP, rien à gagner (DONNEES-1, lot B) | propre | GO |
| `permis_bin`, `pc_pm_sur_parcelle_pp_36m` | D | `sitadel_permits` (8 506 `petitioner_siret` — annexe A.5 ; 7 257 PC SIREN — DONNEES-1 lot C) | 8,8 % / rare mais ×4 la tête | propre (dates dépôt) | GO — meilleure variable connue |
| `rot_nu/rot_bati`, `med_pm2_*`, `tendance` | Z | `p_model_ext_dvf` | 88-100 % | propre (`< asof`) | GO |
| `nu_constructible_asof`, `pct_bati_secteur_asof` | D/Z | rejeu Sitadel+DVF | 100 % (rejeu corrige 33 % des flips — DONNEES-1, lot A) | as-of reconstruit | GO |
| `sdp_residuelle_v2`, `sous_densite`, `residuel_famille` | D | `parcel_residuel` (lecture K3 ~99 %) | ~99 % | quasi statique, `_STATIQUE` consigné | GO |
| voisinage spatio-temporel (11 features K4bis) | Z | construits as-of | île | test de fuite dédié VERT (K4bis) | GO |
| `anciennete_plu_annees` | Z | `sudocuh_procedures.approbation_opp` | 99 % | datée | GO — **sudocuh gardée** (statuer §6 du mandat : oui) |
| `ventes_pm_secteur_36m` | Z | `pm_proprietaires_millesimes` (2019-2024) | île | as-of propre mais **millésime figé 2024** | ATTENTION (re-mesurer au millésime 2025) |
| `filo_snv_pp`, `filo_pct_pauv`, `filo_pct_prop` | Z | `filosofi_carreaux_200m` | 89,3 % | 2021, statique | GO — re-challengées (ablation B, `SCORING-5-RETOUR.md` §4) : retrait = AUC −0,003, lift −0,034, gain nul |
| `zone_plu` (état courant) | Z | GPU | 99 % | **as-of irreconstructible** — biais documenté : 22,9 % des labels appris sous PLU postérieur, décroissant 51 %→7 % (DONNEES-1, lot A1) | GO avec biais assumé |
| `surface_m2`, `pente_moy_deg`, copro (RNIC) | D/Z | `parcels`, `parcel_terrain`, `rnic_coproprietes` | 98-100 % | immuable / vivant | GO |
| **candidate** `division_dfi_36m` | D | `dfi_filiation.date_validation` | ~6-16 k liens/an | as-of propre | à tester (protocole §9) |
| **candidate** `dernier_depot_comptes` | D (PM) | `bodacc_depots` (14 078 / 1 938 SIREN) | segment PM | daté | à tester (protocole §9) |
| DPE | — | `dpe_records` | **1 123 lignes / 20 communes / 0,26 %** | — | **NO-GO** (< 5 %) |
| Radar | — | 7 rattachées, 0 paire | — | — | **NO-GO** (acquis §2) |
| mortes retirées (ndvi, canopée, accès équip., friche, qpv, filo_dens_pop, window_coverage, permis_24m_norm, dormance_droits) | — | — | — | — | **restent dehors** (K2 : AUC 0,613→0,626) |

**Recherche d'entreprises (DINUM) — statut demandé par le mandat** : la recette Signal ne la consomme pas ; elle ne nourrit que `score_v.py` (âge dirigeant fallback, SCI dormante — `score_v.py:42,88-120`). Le Score V disparaît du produit (déjà décidé côté affichage ; PALIERS-1 Lot C le sort du vocabulaire). **Le nouveau moteur permet donc son retrait du scoring.** Réserve : les événements datés BODACC (bypass « brûlante ») passent par `parcel_v_score.signals` (`p_v2/pipeline.py:142-150`) — le Signal V2 doit lire BODACC directement avant de couper le tuyau ; usages hors scoring (courrier, annuaire) à vérifier hors mandat.

---

## 5. Cascade — reprise règle par règle

Classement : **A** hard exclude (certain) · **B** pénalité (assiette ou coefficient du Score) · **C** information · **D** supprimer/remplacer. Effectifs = parcelles distinctes HARD_EXCLUDE du run `q_v13_sources1` (la cascade dont hérite le nouveau moteur — 150 260 exclusions au total), requêtes annexe A.1-A.2-A.3. Les recouvrements entre règles interdisent d'additionner les lignes.

| Règle (code) | Condition actuelle | Effectif q_v13 | Classe | Justification |
|---|---|---|---|---|
| `zonage_plu_gpu` A/N **100 %** (`phase1.py:222`) | recouvrement total | **98 100** (A 69 505 + N 28 595) | **A** | assiette nulle certaine |
| `zonage_plu_gpu` A/N **90-99 %** | ≥90 % (`an_hard_exclude_pct`, non calibré) | **3 112** | **B** | une portion U exploitable subsiste — exigence explicite du mandat §5.1 ; assiette clippée |
| zone éco « habitat interdit » calibrée ≥90 % (`phase1.py:312-324`) | règlement cité | 2 445 | **A** (réserve) | interdit pour le produit logement ; réserve : destinations économiques hors produit actuel |
| `prescription_plu` EBC ≥80 % (`phase1.py:460-470`) | | 11 871 | **B** (A si 100 %) | inconstructible sur l'emprise EBC seulement → déduction d'assiette |
| `prescription_plu` ER ≥50 % (`phase1.py:443-454`) | | 5 125 | **B** (A si 100 %) | servitude d'acquisition réelle mais partielle → assiette |
| veto libellés (corridor, périmètre d'attente) (`phase1.py:429-437`) | | 15 | **B** | périmètre d'attente = gel temporaire |
| `risques` PPR rouge ≥50 % (`phase1.py:668-695`) | | **44 764** | **B** (A si 100 %) | principe partiel = assiette ; ventilation 100 %/partiel à mesurer à l'implémentation (requête spécifiée : parser `detail` sur le % de recouvrement, à ajouter au dry-run) |
| `peb` A/B ≥2 % (`phase1.py:508-560`) | seuil 2 % | 373 | **B gradué** (A si quasi-total) | L112-10 interdit l'habitat neuf **sur la zone** ; 2 % de recouvrement n'annule pas l'assiette |
| `dpf` marchepied ≤3,25 m (`phase1.py:770-797`) | | 10 335 | **A** | domaine public fluvial, servitude L2131-2 certaine |
| `safer` canne CSA ≥50 % en zone A (`phase1.py:592-638`) | | 6 612 | **D** (fusion) | redondante : la zone A est déjà traitée par l'assiette ; le RPG devient information (et candidate as-of — SCORING-4 « En passant ») |
| `ens` réserves naturelles / APB (`phase1.py:926-962`) | `hard_subtypes` | 1 100 | **A** | interdiction réglementaire intégrale |
| `eau` ≥50 % ou centroïde (`phase1.py:73-99`) | | 316 | **A** | plan d'eau |
| `parc_national` cœur (`phase1.py:102`) | | 6 137 | **A** | interdiction certaine (adhésion = C, déjà flag) |
| `foret_publique` domaniale (`phase1.py:131`) | | 6 890 | **A** | incompatible |
| `surface` <40 m² (`phase1.py:1053`) | | 18 902 | **A** | micro-parcelle, faux positif cadastral |
| `emprise_lineaire` (`etage0_ext.py:96`) | largeur <8 m, allongement >8× | 13 801 | **A** | délaissé linéaire |
| `emprise_routiere` (`etage0_ext.py:117`) | garde signaux privés déjà codée | 4 851 | **A** | emprise voirie certaine |
| `pente` >100 % (`phase1.py:860`) | | 4 739 | **A** | falaise (30-100 % = B coefficient) |
| `osm_faux_positif` (cimetière/école ≥30 %, équipement ≥50 %) (`phase1.py:992`) | | 1 526 | **A** | usage public certain ; vérifier le seuil 30 % à l'implémentation |
| `trait_de_cote` bande courte (`phase1.py:839`) | | 3 | **A** | recul réglementaire |
| `dpu` (`phase1.py:563`) | vigilance | 0 exclusion | **C** | déjà correct — jamais exclusion |
| `zone_humide` (`phase1.py:800`) | flag fort | 0 | **C** | inventaires partiels |
| `ravine` (`phase1.py:730`) | proximité ≤10 m | 0 | **B** (coefficient) | difficulté, pas interdiction |
| `ocs_ge` proxy BDCARTO (`phase1.py:965`) | flag faible | 0 | **D → remplacer** | le vrai OCS GE est ingéré (`parcel_ocsge`, 100 %) — le proxy meurt |
| `bati`, `foncier_public` (M129) | info ×0 | 0 | **C** | déjà convertis |
| `abf` (`phase1.py:910`) | UNKNOWN complétude | 0 | **C** | correct |
| `residuel_socle` (`etage0_ext.py:162`) | barème SDP −25…+30 | 0 | **B → cœur du Score** | sort de la cascade, devient le temps 2 du Score |
| étage 1 (`sup`, `sol_pollue`, `icpe`, `bruit`, `cinquante_pas`, `cavite`/`mvt`) | flags gradués | 0 | **B/C** | SUP fortes (t5/ac2/as1) → coefficient ; le reste information |
| phase 2 `dvf`/`sitadel` (POSITIVE) | | — | **D (déplacement)** | le « positif marché » appartient au Signal et à l'information fiche, plus à la cascade |
| phase 2 `potentiel_foncier_region` | | — | **C** | benchmark externe (§13), jamais feature |
| phase 2 `proprietaire` (Fichiers fonciers `manuel`) | quasi toujours UNKNOWN | — | **D** | aucune table — tuyau mort |
| étage 2 `age_dirigeant`, `bodacc` | info ×0 + bypass | — | **D (déplacement)** | événements → Signal, plus dans la cascade |
| déclassements (`pipeline.py:392-453`) : bâti saturé 122 198 · non constructible 6 171 · bâti révélé 5 333 · zone fermée 2 765 · AU 1 115 (SCORING-4) | gardes de tête | — | **B/C entériné** | PALIERS-1 en a déjà fait des motifs ; dans le nouveau moteur : bâti saturé = capacité nette + facteur bâti du coefficient (temps 3), zone/AU fermée = capacité différée, bâti révélé = qualité de donnée |

**Effet net attendu** : les règles reclassées B réintroduisent au plus ~3 112 (zonage 90-99 %) + 6 612 (safer) + parts partielles de PPR/ER/EBC/PEB dans l'univers scoré, avec pénalité d'assiette — borne haute ~70 k avant recouvrements, effectif net à mesurer à l'implémentation (requête : parcelles exclues UNIQUEMENT par des règles reclassées B). Principe gravé respecté : la mesure « déclassées gardées = tête ×2,4 à précision constante » (PALIERS-1) est le précédent, pas à redémontrer.

---

## 6. Combinaison Score × Signal — trois variantes, une recommandation

| Critère | V1 filtre/badge | V2 bonus plafonné | V3 lexicographique |
|---|---|---|---|
| Compréhensible | ✅ deux objets nets | ⚠ « pourquoi 62 et pas 58 ? » — le bonus remélange les deux natures | ✅ « les meilleures parcelles d'abord ; à qualité égale, celles qui bougent » |
| Robuste (cas gravés) | ✅ par construction | ⚠ dépend du plafond ; un bonus mal réglé fait remonter du Score bas | ✅ par construction : le Signal ne franchit jamais une frontière de bande |
| Utile commercialement | ⚠ l'ordre intra-score reste indéfini (paliers de barème ⇒ nombreux ex æquo) | ✅ liste totalement ordonnée | ✅ liste totalement ordonnée ET défendable |
| Défendable statistiquement | ✅ rien à défendre | ❌ le plafond serait arbitraire sans test dédié | ✅ le Signal n'est utilisé que là où il est bon : départager (tête ×10 mesurée — SCORING-RAPPORT §C.4) |
| Simple à maintenir | ✅ | ⚠ un paramètre de plus à versionner/justifier | ✅ zéro paramètre |

**Recommandation : V3** — le Score définit des **bandes de qualité foncière** (bornes = décision Vic, §17), le Signal ordonne à l'intérieur de chaque bande ; ties résiduels départagés par SDP puis IDU (déterminisme). V3 est exactement le « tri secondaire » de V1 rendu explicite et total ; V1 reste le comportement de repli si Vic préfère des bandes non ordonnées. Les deux cas gravés du mandat sont satisfaits par construction : Score haut + Signal faible reste dans sa bande haute ; Score bas + Signal fort reste dans sa bande basse.
**V2 rejetée par défaut** — pas sans mesure : si Vic veut l'instruire, le test départageant est spécifié pour le mandat suivant (pas exécuté) : au banc K0, construire les trois classements sur 2025 et comparer (a) ventes captées dans le top-N restreint aux bandes hautes, (b) nombre de violations des cas gravés, (c) churn mensuel du classement ; un bonus n'est retenu que s'il bat V3 sur (a) sans aucune violation en (b).

---

## 7. UI — vérification de compatibilité

**Compatible, aucun blocage majeur.**
- *Filtres globaux → « Analyser avec LABUSE » → une liste classée* : le Score est recalculable à la volée sur une sélection (fonction pure de caches par parcelle, §8) et le Signal est lu du run mensuel — même parcelle = même valeur quel que soit le filtre : le contrat §11 tient.
- *Filtre Signal fort/moyen/faible* : les trois classes sont déjà stockées par parcelle (paliers v2 en base pour q_v14 : 114/631/280 658 — annexe A.8).
- *Bandeau « LABUSE a analysé N parcelles : M ont plus de chances que les autres »* : N = sélection analysée, M = Signal fort + moyen dans la sélection — direct.
- *Doctrine d'affichage* (score uniquement fiche parcelle + Analyse, jamais dans les outils) : aucune contrainte moteur ; les 17 outils lisent le registre id (OUTILS-FIX-5), rien à changer côté moteur.
- *Invalidation « votre sélection a changé »* : naturelle — l'analyse est un instantané (sélection, version du Score, run du Signal) ; tout écart déclenche le bandeau.
Un seul point d'attention produit (pas un blocage) : avec des bandes + Signal, le vocabulaire client (Priorité / À suivre / Sans signal / Écartée) doit être re-proposé sur le **couple** — décision Vic (§17), maquettes hors mandat.

---

## 8. Recalcul — réponse complète au §12 (contrainte bloquante)

**8.1 Qui déclenche réellement quoi.** Confirmé par le code (builders `p_model/sql.py`, `ext_sql.py`, `qv14.py` ; couches `config/cascade_rules.yaml`) et le tableau des sources (`SOURCES-AUDIT.csv`) :
- **Signal** : DVF, Sitadel (garde de fraîcheur bloquante P1-6, `p_v2/pipeline.py:94-117`), BD TOPO/CoSIA (bâti), Filosofi, RGE ALTI, GPU (zone), résiduel, RNIC (copro), sudocuh, millésimes PM, BODACC (événements).
- **Cascade** : `spatial_layers` tous kinds câblés (43 couches) + caches déclassement.
- **Score déterministe** : résiduel post-calibrage + géométrie + couches clippées + pente + accès + emprise bâtie/hauteur.
- **Affichage seul** : 56 sources connectées sans moteur ; **DPE et SIRENE ne nourrissent ni feature ni couche cascade**.
- **Aucune ingestion ne déclenche de recalcul automatique** : le run est un geste manuel (`labuse flux-run`, `cli.py:643-716` ; aucun run dans le registre cron `jobs.py:287-380`) ; chaque run photographie ses millésimes (`snapshot_source_millesimes`, `pipeline.py:554-558`). Les ~95 sources hebdomadaires n'obligent donc à RIEN recalculer — c'est déjà vrai aujourd'hui ; le problème réel est le coût du geste quand on veut rafraîchir.

**8.2 Profil des ~5 h — mesuré, pas estimé** (annexe A.9) : cascade 24 communes = **3 h 26 (q_v12) à 4 h 13 (q_v13_sources1)** soit **95-97 % du run** ; scoring complet île entière (rebuild features compris) = **226 à 505 s** ; rebuild `spatial_layers_sub` = minutes ; résiduel = poste séparé (6 399 s, ne bouge que si bâti/PLU changent — SCORING-RAPPORT §H.3). À l'intérieur de la cascade, trois postes (code) : intersections spatiales par lots (`cascade/context.py:72-190`), boucle Python 43 couches × 431 663 parcelles (`engine.py:35-50`), et **écriture ORM ligne à ligne de 15,9-17,6 M lignes** `dryrun_cascade_results` (`cascade/pipeline.py:218-239`). Pistes chiffrables pour le mandat d'implémentation (non exécutées) : insertion bulk COPY ; ne persister que les lignes non-PASS (les PASS = ~2/3 du volume au store live, annexe A.9) ; delta par défaut.

**8.3 Recalcul incrémental : OUI, la structure le permet déjà.** `evaluate_parcels(parcel_ids)` accepte un ensemble arbitraire, le dry-run est idempotent par (run_label, parcel_id) et reprenable (`cascade/pipeline.py:56-64, 213-223` ; `flux-run --resume`). Preuve vivante : des parcelles du label servi ont été ré-évaluées entre le 27/08 et le 18/09 (min/max `created_at`, annexe A.9). Le delta cascade = parcelles intersectant les objets `spatial_layers` modifiés depuis le dernier calcul (jointure spatiale par kind/bbox) + parcelles aux caches déclassement changés. **Manque un journal des deltas d'ingestion** (quel objet de couche a changé quand) — c'est LA pièce à construire au mandat suivant ; en attendant, le delta se fait par kind ingéré (rejouer les seules communes/bbox touchées).

**8.4 Le Score LABUSE se recalcule à la volée : OUI par construction.** Fonction pure de caches par parcelle (résiduel, géométrie, clips, pente, accès, emprise bâtie/hauteur) — pas de rang, pas de percentile, pas d'état global. Matérialisation : nightly en delta (parcelles dont une entrée a bougé), et calcul à la demande pour l'Analyse d'une sélection. **Il n'y a plus de « run » pour le Score.**

**8.5 Features globales qui limitaient l'incrémental — levées.** Les pièces globales du servi étaient : rangs/percentiles île (`pipeline.py:346-366`), calibrage d'effectifs N_e 1150 (`:469-480`), quantiles de réserve. **`assign_paliers` v2 les supprime** (fonction pure de p, seuils absolus). Restent locales-mais-propagées : agrégats secteur (une mutation DVF change son secteur) et voisinage ≤400 m (`qv12.py:280-291`) — propagation bornée, et de toute façon le re-score complet coûte 8 min : l'incrémental fin du Signal est inutile, seul celui de la **cascade** compte.

**8.6 Local → VPS : le pont existe, un correctif à spécifier.** `deploy/scripts/sync-run.sh` : « le Mac CALCULE → le VPS SERT » — pg_dump ciblé de 10 tables de run, rsync + checksum, restore + ANALYZE, build-mvt distant, comptages local=VPS, golden avant service. Limite factuelle : il dumpe les tables **entières, tous labels confondus** (dont `dryrun_cascade_results`, 80 M lignes cumulées). Correctif à spécifier au mandat suivant : dump filtré par `run_label` (ou purge des labels morts avant dump). **Le double calcul disparaît.**

**8.7 Architecture de rafraîchissement recommandée** (récapitulatif) : Score = à la volée + delta nightly, sans run · Signal = re-score mensuel ~10 min après `ingest-sitadel`, semestriel au rythme DVF (SCORING-RAPPORT §H.2) · cascade = delta sur changement de couche, run complet réservé aux bascules majeures · résiduel = recalcul sur changement PLU/bâti seulement · re-freeze du modèle = annuel, humain, au banc K0 · VPS = transfert. La contrainte de Vic (« soit on trouve une solution, soit on arrête ») est levée point par point.

---

## 9. Protocole d'ablations — spécifié ici, EXÉCUTÉ par SCORING-5-RETOUR §4

> **Résultat (21/09, `SCORING-5-RETOUR.md` §4)** : A cité · B et C mesurés au banc K0 (reproduction contrôlée : réf q_v14 re-fitée = acquis). Verdict : **recette q_v14 complète pour q_v15** (au plus sans `piscine`/`pv_candidat`), filo gardées (retrait = perte petite mais cohérente pour gain nul) ; **C réfute « les statiques sont du lest »** (AUC 0,5995, churn 66,8 %) — le foncier statique est indispensable au Signal. Le protocole ci-dessous reste la référence de méthode.

Banc K0 (train ≤2023 · calib 2024 · test 2025) + walk-forward 6 plis, règle de verdict pré-enregistrée avant toute mesure (méthode DONNEES-1, lot G), métriques du §3.
- **A — servi m36-l2f** : baseline de contrôle (chiffres déjà connus, ne pas re-mesurer : AUC 0,613, Priorité 13,7 %).
- **B — Signal V2 = recette q_v14 re-freezée** avec hygiène 2026 (millésimes rafraîchis) : le candidat. Attendu ≈ connu (AUC 0,626, Priorité ~30 %) — l'ablation vérifie la reproduction, pas la découverte.
- **C — signaux dynamiques seuls** : DVF + Sitadel + voisinage as-of + événements, sans blocs statiques (zone, Filosofi, pente, résiduel). Question à trancher : quelle part de la discrimination vient du **mouvement** vs du **proxy foncier statique** ? Si C ≈ B, les statiques du Signal sont du lest (le foncier statique vit désormais dans le Score) ; si C ≪ B, on les garde.
- **D — si justifié** : B + `division_dfi_36m` + `dernier_depot_comptes` (PM), chaque variable SEULE puis combinées (méthode DONNEES-1). Justification d'entrée : as-of propres, gisements identifiés (SCORING-4 « En passant »).
Pour le **Score** (pas de label — §13) : banc de monotonicité + liste de témoins constituée avec Vic + confrontation au potentiel foncier Région (challenge externe) ; critère de réussite = zéro violation de monotonicité, témoins « très bonnes » dans les bandes hautes, désaccords avec la Région tous explicables par une donnée citée.

---

## 10. Tests automatisés à prévoir

1. **Déterminisme** : même entrée → même score, hash du barème dans la sortie ; refus de servir si version/hash absents.
2. **Monotonicité** : SDP↑ à contraintes égales ⇒ score ≥ ; assiette↓ ⇒ score ≤ ; emprise bâtie↑ ou hauteur↑ à capacité égale ⇒ score ≤.
3. **Manquants** : entrée critique absente → `non_calculable` + motif FR (jamais 0) ; entrée non critique absente → couverture baisse, composante neutre.
4. **Pénalité jamais exclusion** : ∀ parcelle avec assiette > 0 et zone résolue ⇒ score calculé > 0.
5. **Fuite temporelle** (Signal) : généraliser l'assert bloquant de K4bis (`k4bis_test_fuite.csv` : features reconstruites source-tronquée == livrées) à TOUTE feature nouvelle ; test de non-postériorité des dates max.
6. **Non-régression cascade** : effectifs par règle A figés en golden (annexe A.1) ; toute dérive > seuil = rouge ; aucune règle B ne produit de HARD_EXCLUDE.
7. **Stabilité/churn** : churn mensuel du Signal borné (garde >15 % de la tête → refus, mécanique `arene.decide_avis` existante — SCORING-RAPPORT §H.6) ; anti-churn 0,18/0,09 testé aux frontières.
8. **Versionnement** : changement de barème sans bump de version = échec de test ; note de version générée depuis les chiffres (jamais à la main — modèle NOTE-DE-VERSION-q_v14).
9. **Cas limites** : surface 40 m², assiette exactement 0, AU fermée, copro, `hors_plu`, parcelle 100 % ER.
10. **Garde-fou 974** : 24 communes présentes dans chaque sortie ; aucune commune à couverture silencieusement nulle ; totaux île = somme communes.

---

## 11. Risques et incertitudes

1. **Plafond « sans bloc propriétaire personne physique » — inscrit explicitement** : 81 % du parc sans donnée de cycle de vie (SCORING-RAPPORT §B.5) ; aucun candidat au-dessus d'AUC ~0,63 sans lui (COMPTE-RENDU-SCORING-2). Le Signal restera modeste tant que la convention Cerema (FF/DV3F/LOVAC, `partenariat_requis`, **0 table en base** — annexe A.3) n'existe pas. C'est le plafond connu du moteur, pas un défaut corrigeable par l'ingénierie.
2. **Le Score dépend à 100 % du résiduel post-calibrage** — qui n'existe pas encore (servi = pré-calibrage, annexe A.6). Tout le §2 se spécifie dessus ; si le recalcul révèle des causes M125 massives inattendues, les barèmes sont à re-proposer. Prérequis mesurés avant le run (RESIDUEL-1 lot 1, `SCORING-5-RETOUR.md` §2) : trancher les **95 feuilles `propose` numériques** qui branchent la base du calcul, et lancer dans un **process frais** (`_calibrage_overlay`/`_zonage_doc` en `lru_cache` à vie du process — `zonage.py:78,288`).
3. **Zone PLU as-of irreconstructible** (DONNEES-1, lot A2) : 22,9 % des labels 2017-2024 appris sous un PLU postérieur à la vente (51 %→7 % décroissant). Biais résiduel du backtest Signal : assumé et documenté, pas corrigeable.
4. **Millésimes PM arrêtés à 2024** : toute feature propriétaire PM périmée de 2 ans ; `ventes_pm_secteur_36m` gardée sous garde-fou mais à re-mesurer au premier millésime frais.
5. **Ventilations non mesurées** : PPR rouge 100 % vs partiel (le `detail` ne porte pas le %), ER/EBC à 100 % — nécessaires pour les frontières A/B exactes ; requêtes à ajouter au dry-run à l'implémentation.
6. **Churn annuel ~79 %** du Signal (PALIERS-1) : réalité as-of, à assumer commercialement (le Score, lui, est stable — c'est l'argument produit).
7. **SAR** : source `partenariat_requis` mais 2 453 objets déjà dans `spatial_layers` et un moteur `cascade` déclaré — la règle est informative (DÉCISION 2, `phase1.py:153-219`), mais clarifier la licence avant d'appuyer quoi que ce soit de nouveau dessus.
8. **Pas de vérité terrain pour le Score** : validation par monotonicité + témoins seulement ; le retour terrain (0 étiquette aujourd'hui, `parcel_feedback` vide) mettra 6-12 mois à exister — poser le geste maintenant (sélecteur 7 états SCORING-3), n'en rien attendre avant.
9. **Seuils et barèmes** : toutes les bornes chiffrées de ce rapport (paliers de capacité, plancher 0,4, crans du facteur bâti, bandes) sont des **structures proposées** — les valeurs sortent des parcelles témoins (décision Vic actée) puis restent des décisions Vic (§17), pas des chiffres à fausse précision.
10. **À abandonner** (déjà réfuté, ne pas y revenir sans fait nouveau) : fits séparés par segment (K4), GBM (K5), snapshots infra-annuels tant que DVF a 6 mois de latence, DPE (0,26 %), Radar comme feature, BDNB/MOBPRO (retirées), toute variable < 5 % de couverture.

---

## Annexe A — mesures nouvelles (SELECT, base `labuse`, 21/09/2026)

**A.1 Effectifs cascade par règle et par label** :
```sql
SELECT run_label, layer_name, count(DISTINCT parcel_id)
FROM dryrun_cascade_results
WHERE run_label IN ('q_v11_m137','q_v13_sources1') AND result='HARD_EXCLUDE'
GROUP BY 1,2 ORDER BY 1,3 DESC;
```
q_v13_sources1 : zonage_plu_gpu 103 657 · risques 44 764 · surface 18 902 · prescription_plu 17 010 · emprise_lineaire 13 801 · dpf 10 335 · foret_publique 6 890 · safer 6 612 · parc_national 6 137 · emprise_routiere 4 851 · pente 4 739 · osm_faux_positif 1 526 · ens 1 100 · peb 373 · eau 316 · trait_de_cote 3. (q_v11_m137 : mêmes valeurs hors durcissements SOURCES-1 : prescription 23, dpf 11, safer 1, ens 1, peb 2.)

**A.2 Ventilation zonage A/N (q_v13_sources1)** — `detail ~ 'recouvrement 100'` : Zone A 100 % : 69 505 · Zone N 100 % : 28 595 · Zone A 90-99 % : 1 494 · Zone N 90-99 % : 1 618 · zones éco « habitat interdit » : 2 445.

**A.3 Cerema/DV3F/LOVAC** : `SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename ~* 'lovac|dv3f|cerema|ff_|fichiers_fonciers'` → **0 ligne**.

**A.4 DFI** : `dfi_filiation` 409 623 liens · 471 129 IDU distincts (mère∪fille) · `date_validation` 1989→2025, par année récente : 2021 : 9 119 · 2022 : 7 518 · 2023 : 8 449 · 2024 : 8 357 · 2025 : 6 594.

**A.5 Couvertures** (counts unitaires) : `parcels` 431 663 · `batiment_hauteur_lidar` 303 452 (70,3 %) · `rnb_batiments` actifs 414 081 · `rnb_rattachement_bdtopo` 817 506 · `parcel_ocsge` 431 663 · `parcel_cosia_couverture` 1 947 019 · `dpe_records` 1 123 (20 communes, 1 109 avec `parcelle_idu`) · `dvf_mutations_histo` 110 477 (2014-2020, 45 089 parcelles) · `dvf_mutations` 29 566 (2021→08/2026) · `sitadel_permits` 50 545 (2004→07/2026, 8 506 avec `raw->>'petitioner_siret'`) · `pm_proprietaires_millesimes` 2019→2024 (81 161 liens en 2024) · `bodacc_depots` 14 078 (1 938 SIREN) · `territoire_fiscal_commune` 24.

**A.6 Résiduel servi** : `residuel_runs` → run_seq 2 « m135-run2-ile », `is_served`, 431 663 lignes, `computed_at` 22-23/08/2026, 6 399 s — antérieur au calibrage PLU.

**A.7 ZAC** : `SELECT tablename FROM pg_tables WHERE tablename ~ 'zac'` → aucune table ZAC. `commune_ort` 19 · `plh_epci` 5 · `commune_conso_enaf` 24.

**A.8 Paliers/tiers par run** (`SELECT run_id, tier, count(*) FROM parcel_p_score_v2 GROUP BY 1,2`) : q_v11_m137 : ecartee 145 882 · a_creuser 136 841 · declasse_bati_sature 123 066 · reserve_fonciere 8 789 · chaude 1 367 · brulante 111 (+ autres declasse_*) ; q_v14 : sans_signal 280 658 · ecartee 150 260 · a_suivre 631 · priorite 114.

**A.9 Durées** : `SELECT run_id, n_parcelles, duration_s FROM p_score_v2_runs` → q_v11_m137 226 s · q_v12 330 s · q_v13_sources1 277 s · q_v14 505 s (431 663 parcelles chacun). `SELECT run_label, max(created_at)-min(created_at) FROM dryrun_parcel_evaluations GROUP BY 1` → cascade q_v12 3 h 26 · q_v13_sources1 4 h 13 (q_v11_m137 : lignes étalées 27/08→18/09 = ré-évaluations sous label servi). Store live `cascade_results` : 9 206 291 lignes dont PASS 6 208 437 (~2/3).
