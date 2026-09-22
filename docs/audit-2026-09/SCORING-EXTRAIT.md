# SCORING-EXTRAIT — le calcul du score, tel qu'il tourne aujourd'hui

**Mandat** : lire le calcul, pas le présenter. Lecture seule stricte, rien exécuté (aucun run,
aucune bascule, aucune ingestion, aucun merge, aucune modification de code). Branche
`audit/scoring-extrait`, arbre propre à l'ouverture et à la clôture.

**Run servi** : `q_v11_m137` — point de vérité `config/served_run.txt` (via
`config/served_manifest.json`, `scoring_run: q_v11_m137`, promu le 2026-09-05), relu vivant à la
requête par `src/labuse/runs.py:current()`. Run précédent = `q_v12` (`config/run_precedent.txt`).

**Artefact modèle servi** : `reports/m36-foncier/artifacts-m36-scoring2026.joblib`
(`src/labuse/scoring/p_v2/__init__.py:19`), `model_version = m36-l2f-2026`
(`__init__.py:21`). Le sha256 réel de l'artefact
`00a58008143d5260b9aea192eb73b94bd11693cba6cc4f99fd622da3a4959b64` est **identique** à celui gelé
au manifeste `reports/m36-foncier/FREEZE-scoring2026.json` **et** à `p_score_v2_runs.model_sha256`
du run servi. Le modèle servi est donc bien celui gelé le 2026-07-12 — vérifié, pas déclaré.

> **Deux vocabulaires coexistent dans le code.** Le run servi `q_v11_m137` utilise
> `assign_tiers` (tiers par RANG : `brulante / chaude / a_creuser / reserve_fonciere / ecartee`
> + `declasse_*`). Le système en probabilité absolue (`assign_paliers`, seuils 0,20 / 0,10) n'est
> appliqué **qu'à la recette `q_v14`** (`scoring/p_v2/pipeline.py:487`), qui **n'est pas servie**.
> Tout ce document décrit le calcul du RUN SERVI. La divergence est traitée en Q4.

---

## Q1. Le chemin complet, bout en bout

Orchestrateur : `src/labuse/scoring/p_v2/pipeline.py:run_score_v2()` (ligne 275). CLI `labuse
score-v2`. Une parcelle traverse :

```
[0] SOURCES BRUTES (ingérées)                                    tables ingestion
      DVF (dvf_mutations_parcelle), Sitadel (sitadel_permits), BD TOPO bâti,
      Filosofi, GPU zonage/prescriptions, RGE ALTI (pente), OSM, cadastre…
        │
[1] FEATURE STORE as-of  ext_sql.build_ext_union / _mutations / _dataset  pipeline.py:127-139
      → table p_model_ext_dataset : 1 ligne par (parcelle × année), features au 01/01/Y,
        fenêtres DVF/Sitadel finissant au 31/12/Y-1. Le run servi lit annee = 2026.
      → build_permits AVANT le dataset + garde de fraîcheur check_permits_fraicheur()
        (pipeline.py:114) : échec BRUYANT si les permis en features retardent sur la source.
        │
[2] CHARGEMENT + DÉRIVATION           pipeline.py:307  +  p_model/features.py:derive()
      SELECT * FROM p_model_ext_dataset WHERE annee = 2026    → df (431 663 lignes)
      derive() : rotations shrinkées rot_nu/rot_bati (features.py:203-240), composite
      acces_equipements, dormance_droits. Merge copro (p_model_ext_copro).
        │
[3] GARDE NON-CONSTANCE                pipeline.py:314  +  features.py:check_non_constance()
      un signal constant sur tout le parc REFUSE le build (pv_candidat exempté, daté).
        │
[4] MODÈLE (recette m36 servie)        pipeline.py:296-299, 320-329
      verify_artifact() charge le joblib gelé, REFUSE tout mismatch sha256 (pipeline.py:82).
      recale_intercept sur la DERNIÈRE année labellisée (2025) — décalage additif du
        log-hazard, coefficients INTACTS (model.py:110).
      p = model.predict_proba(df)      → proba calibrée (isotonique), model.py:82
      contrib = model.contributions(df) → contribution ligne à ligne coef×WoE, par bloc Z/D
        │
[5] PONDÉRATION AU_SOUS_PLANCHER       pipeline.py:344  _pondere_au_sous_plancher()
      p ×= (1 − manque/seuil) pour les AU trop petites (reste servie, seul le rang bouge).
        │
[6] RANG + PERCENTILE hors copro       pipeline.py:346-364
      départage EXPLICITE : p desc → contrib_D desc → SDP résiduelle desc → surface desc →
      IDU alpha → tirage seedé 974. percentile = 100·(1 − (rang-1)/N_horscopro).
        │
[7] CASCADE / ÉTAGE 0 (RÈGLES)         pipeline.py:369-453   (détail Q5)
      ecartee_etage0  ← dryrun_parcel_evaluations du run SERVI (status 'exclue'), runs.current()
      declasse_cause  ← parcel_constructibilite   (zone fermée / non constructible)
      au_statut       ← parcel_au_statut          (AU fermée / statut inconnu)
      bati_revele     ← parcel_bati_revele        (bâti CoSIA révélé)
      bati_sature     ← parcel_filtre_bati        (bâti saturé, sans SDP résiduelle)
      event_age_mois  ← load_events() (BODACC daté, parcel_v_score.signals)
        │
[8] TIERS (MODÈLE × RÈGLES)            pipeline.py:456-480   +  statuts.py:assign_tiers()
      calibre_n_entree(cible=1150) → n_entree ; n_sortie = 1,4·n_entree
      assign_tiers → chaude (rang ≤ n_entree + hystérésis + plancher C, hors copro/écartée/déclassée)
      calibre_brulante (garde-fou effectif 30–120) → seuil de contrib_D
      assign_tiers (2e passe) → brulante ⊂ chaude filtrée sur contrib_D
        │
[9] ÉCRITURE VERSIONNÉE                pipeline.py:497-…    → parcel_p_score_v2
      colonnes servies : p_raw, mult_base (= p/taux_base), percentile, rang, contrib_z,
      contrib_d, top5_contributions, copro, TIER, event_date, model_version.
        │
[10] LECTURE API                        src/labuse/api/score_v2.py:/v2/score/{idu}
      SELECT … tier … FROM parcel_p_score_v2 WHERE run_id = runs.current() → renvoie `tier` brut.
        │
[11] TRADUCTION CLIENT                  src/labuse/scoring/p_v2/tiers_client.py:20-44
      CORRESPONDANCE_LEGACY : brulante→priorite, chaude→a_suivre, a_creuser/reserve/declasse_*→
      sans_signal, ecartee→ecartee.  Front frontend/src/lib/status.ts (PALIER_META) affiche le
      libellé + couleur. Test anti-dérive tests/test_m137_vocabulaire.py.
        │
[12] PALIER AFFICHÉ : Priorité / À suivre / Sans signal / Écartée.
```

Point de vérité du run à chaque étape : `runs.current()` (jamais une constante gelée en dur —
`LABUSE_ETAGE0_RUN` par défaut = `runs.current()`, pipeline.py:375).

---

## Q2. Les variables, une par une, avec leur poids réel

Le modèle est une **régression logistique régularisée** (L2, `C = 5,0`) sur des variables
**encodées en WoE** (weight-of-evidence par bin), plus 5 interactions et des indicatrices
d'année. Le « poids » d'une variable n'est donc **pas** son coefficient seul : c'est
`coef × WoE(bin)` = la contribution au log-hazard. J'ai chargé l'artefact gelé (lecture seule) et
extrait les coefficients réels ; l'importance effective = **écart-type pondéré par la population**
de la contribution `coef × WoE` sur le parc 2026 (combien la variable déplace réellement le score).

**Coefficients bruts extraits de l'artefact** (`m.coefs`, unité = log-hazard par unité de WoE) :

| # | Variable | Bloc | coef | Import. effective (σ log-hazard, pondérée) | Couverture / état de la source |
|---|---|---|---:|---:|---|
| 1 | `zone_plu` | Z | +0,514 | **0,218** | GPU, 5 bins (U/AUc/AUs/A/N/inconnu). Complet. |
| 2 | `canopee_pct` | D | +0,605 | **0,208** | LiDAR/ortho `parcel_vegetation`. Statique 2026. |
| 3 | `tenure_bin` | D | +0,819 | **0,174** | DVF, ancienneté dernière mutation (bins <1/1-2/2-3/3+/inconnu). Tronqué à 2021. |
| 4 | `permis_bin` | D | +1,001 | **0,167** | Sitadel 2013+, ancienneté dernier permis. |
| 5 | `rot_nu` | Z | +0,678 | **0,134** | DVF L2 nu, rotation secteur (36 mois), shrinkage. |
| 6 | `rot_bati` | Z | +0,478 | **0,126** | DVF L2 bâti, rotation secteur (36 mois). |
| 7 | `sdp_residuelle_m2` | D | +0,498 | 0,096 | `parcel_residuel`. |
| 8 | `nu_constructible` | D | +0,666 | 0,095 | BD TOPO ≤20 m² × zone U/AU. 15,5 % du parc. |
| 9 | `surface_m2` | D | +0,284 | 0,089 | Cadastre. Complet. |
| 10 | `piscine` | D | +0,787 | 0,086 | Détection ortho validée. 4,1 % du parc. |
| 11 | `filo_pct_pauv` | Z | +0,260 | 0,069 | Filosofi 200 m (2019). |
| 12 | `pct_bati_secteur` | Z | −0,329 | 0,061 | BD TOPO. |
| 13 | `filo_snv_pp` | Z | +0,216 | 0,056 | Filosofi 200 m (2019). |
| 14 | `dens_bati_secteur` | Z | −0,271 | 0,050 | BD TOPO. |
| 15 | `filo_dens_pop` | Z | −0,161 | 0,041 | Filosofi. **Retirée** (features.py:82), encore dans l'artefact. |
| 16 | `ndvi_moyen` | D | +0,114 | 0,038 | `parcel_vegetation`. |
| 17 | `sous_densite` | D | −0,187 | 0,029 | `parcel_residuel`. |
| 18 | `pente_moy_deg` | Z | −0,141 | 0,024 | RGE ALTI 5 m. |
| 19 | `window_coverage` | Z | +0,492 | 0,022 | mois DVF dispo/36. **Retirée** (features.py:103). Coef élevé mais quasi 2 valeurs. |
| 20 | `tendance_pm2_bati` | Z | +0,100 | 0,019 | DVF. |
| 21 | `med_pm2_bati_36m` | Z | −0,089 | 0,018 | DVF bâti. |
| 22 | `pv_candidat` | D | +0,337 | 0,018 | Candidats PV ortho. **0 validé sur 23 529** (mort exempté, features.py:163). |
| 23 | `dormance_droits` | D | −0,093 | 0,015 | `parcel_residuel.pct_potentiel`. **Retirée** (features.py:113). |
| 24 | `permis_24m_norm` | Z | +0,073 | 0,014 | Sitadel secteur 24 mois. **Retirée** (features.py:67). |
| 25 | `acces_equipements` | Z | +0,065 | 0,013 | OSM Σexp(−d/800 m). |
| 26 | `med_pm2_terrain_36m` | Z | −0,062 | 0,011 | DVF terrain. |
| 27 | `filo_pct_prop` | Z | +0,050 | 0,010 | Filosofi. |
| 28 | `qpv` | Z | −0,004 | **0,000** | Périmètres QPV. **Retirée** (features.py:86). Contribution nulle. |
| 29 | `friche` | D | +0,0004 | **0,000** | Cartofriches. **0,15 % du parc** (≈640 parcelles). Coef ≈ 0. Morte. |

**Interactions** (`m.inter_coefs`, pipeline.py via `_design`) :
`tenure_bin*permis_bin` −1,884 · `tenure_bin*surface_m2` −1,443 · `tenure_bin*rot_nu` −0,652 ·
`surface_m2*permis_bin` +0,418 · `ndvi_moyen*zone_plu` +0,464. Les deux plus fortes croisent
l'ancienneté de détention avec le dernier permis et la surface (un terrain fraîchement muté ou
récemment permis fait retomber le signal des autres blocs D).

**Indicatrices d'année** (`m.year_coefs`) : 2017 +0,249, 2018 +0,180, 2019 +0,227, 2020 +0,224,
2021 +0,367, 2022 +0,321, 2023 +0,144 (référence = 2024). **Intercept** −4,239 ;
`intercept_shift` de l'artefact = 0 (le recalage 2025 est appliqué au run, sur une copie).

**Absence de valeur** : chaque variable a un bin `manquant/inconnu` explicite (WoE propre, jamais
imputé, `woe.py`). Distance OSM absente → contribution nulle (features.py:215). NULL de
`pct_potentiel` → bin manquant (features.py:113). Un manquant a donc **son propre poids appris**,
il ne « vaut » pas zéro par défaut.

**Lecture** : le pouvoir prédictif tient sur 6 variables (zone_plu, canopée, ancienneté de
mutation, ancienneté de permis, rotations nu/bâti). Les 5 variables `retired` (permis_24m_norm,
filo_dens_pop, qpv, window_coverage, dormance_droits) sont **encore dans l'artefact servi** parce
que le gel M3.6 est antérieur à leur retrait — le retrait ne prendra effet qu'au prochain
ré-entraînement (features.py:29-32, 146-151). `qpv` et `friche` sont mortes (importance 0,000).

---

## Q3. La forme du modèle

**Nature exacte.** Modèle de **survie à temps discret, période = année** : un empilement de lignes
`parcelle × année` (person-period), estimé par une **régression logistique** unique (lien logit)
sur variables WoE. `n_train = 3 453 304` = 8 × 431 663 = les années **2017-2024** empilées
(`meta` de l'artefact, FREEZE `train: 2017-2024`). Le docstring parle de « log-hazard additif par
bloc » (`model.py:1`) : la sortie linéaire `margin()` (model.py:72) est le log-hazard de la
période, la sigmoïde/isotonique en fait la probabilité d'événement de l'année.

**Ce qu'il prédit précisément.** `label` = **mutation L2 dans l'année civile Y** — une vente de
type `Vente` **ou** `Vente terrain à bâtir` (DVF dédupliqué, `p_model_mut_l2`). Les autres natures
(VEFA, échange, adjudication, culture) ne sont **pas** L2. « Probabilité de vente sous 1 an »
signifie donc, techniquement : `P(la parcelle connaît ≥ 1 mutation L2 pendant l'année Y |
features figées au 01/01/Y)`, calibrée en fréquence observée.

**Fenêtre.** Convention as-of stricte : pour Y, les variables n'utilisent que des événements
**antérieurs au 01/01/Y** (fenêtres finissant au 31/12/Y-1, clampées à 2021) ; le label ne lit que
`[01/01/Y, 31/12/Y]` (features.py:9-12, 249-256). Le run servi score **Y = 2026**
(`params.annee_features = 2026`), année dont le label est **NULL** (non encore observable).

**Calibration.** Isotonique (`IsotonicRegression`, model.py:104) ajustée sur la **validation
2025**. À chaque run, seul l'**intercept** est recalé sur la dernière année labellisée (2025) —
décalage additif, coefficients et binning intacts (`recale_intercept`, model.py:110 ;
politique pipeline.py:8-14). Un ré-entraînement complet est une décision humaine annuelle.

**Entraîné quand, servi aujourd'hui ?** Gel **2026-07-12 19:54** (FREEZE `gel`). C = 5,0,
29 features, 5 interactions, indicatrices 2017-2023, seed 974. Run `q_v11_m137` calculé le
**2026-08-27**. Le sha256 de l'artefact chargé = sha256 gelé = `model_sha256` du run servi
(vérifié Q1) : **oui, le modèle servi est exactement l'artefact M3.6 gelé.**

**Réserve de validité (Q6).** Comme Y = 2026 n'a pas de label et que DVF s'arrête au 2025-12-31,
la prédiction servie **ne peut pas encore être confrontée à un résultat réalisé**. Toute mesure de
performance « 12 mois » porte sur 2025 — année qui est **à la fois dans les fenêtres de features
et la cible du recalage d'intercept** (contamination, cf. Q6).

---

## Q4. Les paliers

**Le run servi n'utilise PAS de seuil de probabilité.** Le palier vient de `assign_tiers`
(`scoring/p_v2/statuts.py:73`), qui classe par **rang** (donc par `p`, mais relatif), hystérésis et
capacité — pas par une valeur absolue de `p`. Traduction en libellé client :
`tiers_client.py:CORRESPONDANCE_LEGACY` (lignes 34-46).

Effectifs réels sur `q_v11_m137` (`parcel_p_score_v2`, 431 663 parcelles) :

| Palier affiché | Tier interne | Effectif | D'où vient le seuil |
|---|---|---:|---|
| **Priorité** | `brulante` | **111** | `calibre_brulante` : plus petit quantile de `contrib_D` (parmi les chaudes) ramenant l'effectif dans **[30, 120]** (statuts.py:154-177). |
| **À suivre** | `chaude` | 1 367 | rang ≤ `n_entree` + plancher C, hors copro/écartée/déclassée. `n_entree` = `calibre_n_entree(cible=1150)` (statuts.py:180). |
| **Sans signal** | `a_creuser` (136 841) + `reserve_fonciere` (8 789) + tous `declasse_*` (138 673) | **284 303** | résiduel du modèle + drapeau réserve + motifs de déclassement (règles). |
| **Écartée** | `ecartee` | 145 882 | cascade étage 0 dur (Q5). |

Détail des `declasse_*` (tous → « Sans signal », motif porté en fiche) : `declasse_bati_sature`
123 066 · `declasse_bati_revele` 5 475 · `declasse_zone_fermee` 2 809 · `declasse_au_statut_inconnu`
900 · `declasse_non_constructible` 6 178 · `declasse_au_fermee` 245.

**Pourquoi Priorité = 111.** Ce n'est **pas** un seuil de probabilité. C'est le tier `brulante`
(statuts.py:116-120) : une parcelle **déjà `chaude`** (donc dans le haut du rang) **ET**
`contrib_D ≥ brulante_seuil_d` **ET** (événement daté ≤ 12 mois **OU** `contrib_D ≥` top-décile).
`calibre_brulante` cherche mécaniquement le quantile de `contrib_D` qui pose l'effectif **dans
[30, 120]** ; sur `q_v11_m137`, `brulante_seuil_d = 1,694`, `brulante_top_decile_d = 1,592`
(`p_score_v2_runs.params`), ce qui **sélectionne 111 parcelles**. Le chiffre 111 est donc un
**produit de calibrage d'effectif sur `contrib_D`**, borné à 120 par construction — pas une
frontière de risque.

**Divergence documentée.**
- « **potentiel épuisé** » n'existe pas comme palier affiché. Le vocabulaire servi n'a **que
  quatre** paliers (`tiers_client.py:20-27`, front `status.ts`). Le bâti saturé
  (`declasse_bati_sature`, 123 066) est projeté sur **« Sans signal »** avec un **motif** de fiche
  (« bâti saturé »). C'est vraisemblablement ce que « potentiel épuisé » désigne côté humain.
- Les seuils en probabilité absolue **0,20 / 0,10** (`PaliersConfig`, statuts.py:218-238) et
  `assign_paliers` (statuts.py:248) ne s'appliquent **qu'à `q_v14`** (pipeline.py:487), run **non
  servi**. Sur le servi, ces seuils sont **inertes**.

---

## Q5. La cascade et les motifs — ce qui est règle, ce qui est modèle

La cascade (`src/labuse/cascade/`, `config/cascade_rules.yaml`) tourne en deux phases (Phase 1
géométrique sur toutes les parcelles, Phase 2 coûteuse sur les survivantes). Son verdict d'écart
dur est **lu** par le scoring depuis `dryrun_parcel_evaluations` du run servi (pipeline.py:369-379,
status `'exclue'`). Sur `q_v11_m137`, `dryrun_parcel_evaluations` : **145 882 exclue**,
17 671 opportunite, 268 110 a_creuser.

**1) Écartement DUR → « Écartée » (145 882).** Couches Phase 1 rendant `HARD_EXCLUDE`. Attribution
réelle par couche (`dryrun_cascade_results`, une parcelle peut cumuler plusieurs motifs, d'où un
total > 145 882) :

| Couche | Parcelles HARD_EXCLUDE | Règle |
|---|---:|---|
| `zonage_plu_gpu` | 103 722 | zone A/N ≥ 90 % (agricole/naturelle) |
| `risques` | 44 764 | PPR rouge interdiction ≥ 50 % |
| `surface` | 18 902 | micro-parcelle < 40 m² |
| `emprise_lineaire` | 13 801 | délaissé de voirie (largeur < 8 m, allongement > 8×) |
| `foret_publique` | 6 890 | forêt domaniale |
| `parc_national` | 6 137 | cœur du parc |
| `emprise_routiere` | 4 851 | axe carrossable sans signal privé |
| `pente` | 4 739 | falaise (pente ≥ 100 %) |
| `osm_faux_positif` | 1 526 | cimetière/école ou couverture OSM ≥ 50 % |
| `eau` | 316 | hydrographie majoritaire |
| `prescription_plu` | 15 | ER ≥ 50 % / EBC ≥ 80 % |
| `trait_de_cote` | 3 | bande de recul courte |

**2) Déclassement → reste visible mais hors tête, projeté « Sans signal » + motif** (pipeline.py:
399-453, statuts.py:135-149) :
- `declasse_zone_fermee` / `declasse_non_constructible` ← `parcel_constructibilite` (verdict moteur
  faisabilité) ;
- `declasse_au_fermee` / `declasse_au_statut_inconnu` ← `parcel_au_statut` (ouverture des zones AU) ;
- `declasse_bati_revele` ← `parcel_bati_revele` (bâti CoSIA sur parcelle servie « nue ») ;
- `declasse_bati_sature` ← `parcel_filtre_bati` (« saturée » **et** sans SDP résiduelle > 0).
  Ordre de priorité du motif le plus spécifique (statuts.py:135-149).

**3) Événement daté (bypass).** BODACC (LJ/RJ/sauvegarde/cession de fonds) < 6 mois force l'entrée
en zone tampon ; < 12 mois participe à la qualification `brulante` (pipeline.py:79-80, EVENT_CODES ;
statuts.py:108-120).

**Règle vs modèle — la part de chaque.** Sur 431 663 parcelles servies :
- **Règles (déterministe)** : 145 882 écartées (33,8 %, cascade) + 138 673 déclassées (32,1 %,
  caches faisabilité/AU/bâti) = **65,9 % du parc dont le sort est décidé par une règle**, pas par
  le score. La réserve foncière (8 789, drapeau top-décile SDP ∧ P < médiane) est aussi une règle.
- **Modèle (statistique)** : la tête produit — `chaude` (1 367) + `brulante` (111) = **1 478
  parcelles (0,34 %)** — est sélectionnée par le **rang du score** `p` (puis, pour `brulante`, par
  `contrib_D`). Les 136 841 `a_creuser` sont le résiduel classé par le modèle mais sous le seuil
  d'entrée.

Autrement dit : **le modèle statistique ne « décide » que du sommet (~1 478 parcelles) ; les deux
tiers du parc sont filtrés par des règles déterministes**, et « Priorité » (111) est en plus
re-trié sur `contrib_D`, pas sur `p`.

---

## Q6. Ce qui tient et ce qui ne tient pas

### Rapport de risque par palier — 12 mois de DVF (mesuré ici)

Mesure : parmi les 431 663 parcelles scorées, part ayant ≥ 1 mutation L2 (`Vente` /
`Vente terrain à bâtir`) sur **2025-01-01 → 2025-12-31** (les 12 derniers mois disponibles),
rapportée au taux global. **Base globale = 1,735 %** (7 489 / 431 663).

| Palier | Effectif | Ventes L2 2025 | Taux | Rapport de risque |
|---|---:|---:|---:|---:|
| **À suivre** (`chaude`) | 1 367 | 412 | 30,1 % | **×17,4** |
| **Sans signal** | 284 303 | 5 401 | 1,90 % | ×1,09 |
| **Écartée** | 145 882 | 1 675 | 1,15 % | ×0,66 |
| **Priorité** (`brulante`) | **111** | **1** | 0,90 % | **×0,52** |

Détail par tier interne (mêmes données) : `chaude` ×17,4 · `declasse_bati_revele` ×1,97 ·
`declasse_au_statut_inconnu` ×1,92 · `declasse_non_constructible` ×1,53 · `declasse_bati_sature`
×1,22 · `a_creuser` ×0,99 · `declasse_zone_fermee` ×0,82 · `declasse_au_fermee` ×0,71 · `ecartee`
×0,66 · `brulante` ×0,52 · `reserve_fonciere` ×0,14.

**Lecture franche.**
- **Tout le pouvoir prédictif vit dans « À suivre »** (×17,4, 412 ventes sur 1 367). C'est le seul
  palier qui sépare vraiment. L'ordre de grandeur recoupe le « À suivre ×13,3 » cité par le
  mandat (RECETTE-10) ; l'écart tient à la fenêtre/au run mesuré et n'est pas reproductible ici
  faute du rapport RECETTE-10 sur cette branche.
- **« Priorité » n'est pas prouvé** : 111 parcelles, **1 seule vente** → ×0,52, intervalle de
  confiance énorme (1 événement). Le sous-tri `brulante` (sur `contrib_D` = dormance parcellaire +
  événement) **retire de « À suivre » 111 parcelles qui vendent moins que la moyenne de « À
  suivre »**. Le filtre qui définit Priorité **dégrade** le signal au lieu de le concentrer, sur
  cet échantillon. « ×3,18 filtre réaliste » du mandat : non reproductible sans la définition
  exacte du filtre RECETTE-10 — non établi ici.
- **Contamination à noter** : 2025 est **dans** les fenêtres de features (rot_nu/rot_bati 36 mois
  finissant au 31/12/2025) **et** la cible du recalage d'intercept. Un secteur qui vend beaucoup en
  2025 a une rotation haute → `p` haut → `chaude`, et re-vend en 2025 (la cible). Le ×17,4 est donc
  **optimiste**. La vraie cible (2026) n'a pas de DVF : **le run servi n'est pas encore validable
  hors échantillon.**

### Variables : ce qui porte, ce qui ne sert à rien, ce qui est mal nourri

| Verdict | Variables | Fondement |
|---|---|---|
| **Portent le pouvoir prédictif** | `zone_plu` (0,218), `canopee_pct` (0,208), `tenure_bin` (0,174), `permis_bin` (0,167), `rot_nu` (0,134), `rot_bati` (0,126) + interactions `tenure×permis` (−1,884) et `tenure×surface` (−1,443) | importance effective (σ log-hazard pondérée), Q2 |
| **Ne servent à rien (mortes)** | `qpv` (0,000 ; coef −0,004), `friche` (0,000 ; coef +0,0004) | contribution nulle sur le parc |
| **Presque nulles / instables** | `pv_candidat`, `permis_24m_norm`, `dormance_droits`, `filo_pct_prop`, `med_pm2_terrain_36m`, `acces_equipements` | importance < 0,02 ; 4 sont `retired` |
| **Source incomplète / périmée** | `friche` : **0,15 % du parc** (≈640 parcelles) → ne peut rien prédire (le cas « source à 17 enregistrements » du mandat) · `pv_candidat` : **0 validé sur 23 529** candidats (validation NULL, features.py:163) · `filo_*` : millésime Filosofi **2019** · features `_STATIQUE` (canopée, NDVI, pente, densité, zone) : millésime unique 2026, non historisées → léger risque de fuite consigné (features.py:38, 96-98) · rotations : DVF avec ~6 mois de latence DGFiP |

`window_coverage` mérite un mot : coef élevé (+0,492) mais importance 0,022 (quasi 2 valeurs sur le
parc, feature `retired`) — un gros coefficient sur une variable presque constante ne déplace
presque rien.

---

## Tableau récapitulatif — variable · source · poids · couverture · verdict

Poids = coefficient brut (log-hazard/WoE). Importance = σ log-hazard pondérée (déplacement réel).
Ordre d'importance décroissante.

| Variable | Bloc | Source | Poids (coef) | Importance | Couverture réelle | Verdict |
|---|---|---|---:|---:|---|---|
| `zone_plu` | Z | GPU zonage (centroïde) | +0,514 | 0,218 | complète (U/AU/A/N/inconnu) | **porteur #1** |
| `canopee_pct` | D | LiDAR/ortho `parcel_vegetation` | +0,605 | 0,208 | statique 2026 | **porteur** |
| `tenure_bin` | D | DVF ancienneté mutation | +0,819 | 0,174 | tronqué 2021 | **porteur** |
| `permis_bin` | D | Sitadel 2013+ | +1,001 | 0,167 | latence 1-3 mois | **porteur** |
| `rot_nu` | Z | DVF L2 nu (36 m) | +0,678 | 0,134 | latence DGFiP ~6 m | **porteur** |
| `rot_bati` | Z | DVF L2 bâti (36 m) | +0,478 | 0,126 | latence DGFiP ~6 m | **porteur** |
| `sdp_residuelle_m2` | D | `parcel_residuel` | +0,498 | 0,096 | dépend du moteur droits | utile |
| `nu_constructible` | D | BD TOPO × U/AU | +0,666 | 0,095 | 15,5 % du parc | utile |
| `surface_m2` | D | cadastre | +0,284 | 0,089 | complète | utile |
| `piscine` | D | détection ortho validée | +0,787 | 0,086 | 4,1 % du parc | utile |
| `filo_pct_pauv` | Z | Filosofi 200 m | +0,260 | 0,069 | millésime **2019** | utile (périmé) |
| `pct_bati_secteur` | Z | BD TOPO | −0,329 | 0,061 | statique | utile |
| `filo_snv_pp` | Z | Filosofi 200 m | +0,216 | 0,056 | millésime **2019** | utile (périmé) |
| `dens_bati_secteur` | Z | BD TOPO | −0,271 | 0,050 | statique | utile |
| `filo_dens_pop` | Z | Filosofi | −0,161 | 0,041 | 2019 · **retirée** | faible, sort au ré-entraînement |
| `ndvi_moyen` | D | `parcel_vegetation` | +0,114 | 0,038 | statique 2026 | faible |
| `sous_densite` | D | `parcel_residuel` | −0,187 | 0,029 | — | faible |
| `pente_moy_deg` | Z | RGE ALTI 5 m | −0,141 | 0,024 | statique | faible |
| `window_coverage` | Z | déterministe DVF | +0,492 | 0,022 | quasi constante · **retirée** | inerte |
| `tendance_pm2_bati` | Z | DVF | +0,100 | 0,019 | — | faible |
| `med_pm2_bati_36m` | Z | DVF bâti | −0,089 | 0,018 | — | faible |
| `pv_candidat` | D | ortho PV | +0,337 | 0,018 | **0 validé / 23 529** | quasi mort (exempté) |
| `dormance_droits` | D | `parcel_residuel.pct_potentiel` | −0,093 | 0,015 | NULL fréquent · **retirée** | faible |
| `permis_24m_norm` | Z | Sitadel secteur 24 m | +0,073 | 0,014 | **retirée** | faible |
| `acces_equipements` | Z | OSM Σexp(−d/800) | +0,065 | 0,013 | distance absente = 0 | faible |
| `med_pm2_terrain_36m` | Z | DVF terrain | −0,062 | 0,011 | — | faible |
| `filo_pct_prop` | Z | Filosofi | +0,050 | 0,010 | 2019 | faible |
| `qpv` | Z | périmètres QPV | −0,004 | **0,000** | 9,6 % du parc · **retirée** | **mort** |
| `friche` | D | Cartofriches | +0,0004 | **0,000** | **0,15 % du parc** | **mort (source vide)** |

Interactions : `tenure_bin*permis_bin` −1,884 · `tenure_bin*surface_m2` −1,443 · `tenure_bin*rot_nu`
−0,652 · `surface_m2*permis_bin` +0,418 · `ndvi_moyen*zone_plu` +0,464.

---

### Chiffres-clés à retenir

- Run servi **`q_v11_m137`**, artefact **m36-l2f-2026** gelé 2026-07-12 (sha256 vérifié = servi).
- Régression logistique WoE (survie à temps discret annuelle), train **2017-2024**, iso **2025**,
  C = 5,0, 29 features dont **5 retirées encore présentes**, 2 mortes (`qpv`, `friche`).
- Paliers servis = **tiers par rang** (`assign_tiers`), pas la probabilité absolue. **Priorité =
  111** = tier `brulante`, effectif calibré dans [30,120] sur `contrib_D` (seuil 1,694).
- Règles = 65,9 % du parc (écartées 145 882 + déclassées 138 673) ; modèle = tête 1 478 (0,34 %).
- Risque 12 mois (2025, base 1,735 %) : **À suivre ×17,4**, Sans signal ×1,09, Écartée ×0,66,
  **Priorité ×0,52 (1 vente / 111 — non prouvé)**. Mesure **contaminée** (2025 ∈ fenêtres +
  cible de recalage) ; 2026 non observable → **run servi non validable hors échantillon**.
