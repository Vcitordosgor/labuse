# SCORING-1 — l'algorithme mis à nu (audit, lecture seule)

**Branche `audit/scoring-1`. Aucune ligne de code servi modifiée, aucun seuil ni palier touché.**
Toutes les mesures sont faites sur la base réelle (431 663 parcelles, run servi `q_v11_m137`),
avec un harnais qui **reproduit la production à l'identique** : la probabilité recalculée par ce
rapport coïncide avec `parcel_p_score_v2.p_raw` du run servi (écart médian 1,7·10⁻⁷ ; les 1 275
seules parcelles qui diffèrent sont exactement les `au_sous_plancher` dont la p subit la
pondération d'ouverture AU — comportement documenté). Scripts rejouables :
`scripts/audit/scoring/` ; sorties chiffrées : `reports/audit-scoring/`.

> Convention de lecture : chaque section commence par trois phrases simples, puis le détail. Aucun
> chiffre sans sa base.

---

## A — Le modèle, expliqué

**Ce qu'on a trouvé.** LA BUSE fait tourner *deux* systèmes de notation : un barème à points hérité
(« Score V », règles écrites à la main) et le vrai modèle servi, un modèle de **hasard en temps
discret** (« modèle P », `m36-l2f-2026`) qui estime la probabilité qu'une parcelle se vende dans
l'année. **Ce que ça veut dire.** Ce qui décide des paliers affichés aujourd'hui, c'est le modèle P
seul — le Score V n'est plus qu'une baseline de contrôle (il fait 0,51× la moyenne hors copro, il
ne prédit rien). **Ce qu'on peut en faire.** On peut décrire précisément ce que le produit promet
et où la chaîne peut écarter une parcelle, ce qui est le préalable à toute amélioration.

### A.1 — Ce qu'il prédit exactement

- **Cible** : « la parcelle connaît-elle une **mutation L2-F** dans les 12 mois ? » L2-F = vente
  foncière (mutation à titre onéreux, natures « Vente » et « Vente en l'état futur d'achèvement »),
  **hors ventes d'unités de copropriété** (un lot d'appartement isolé est exclu ; une vente en bloc
  d'immeuble est conservée). Défini en SQL, `ext_sql.py:224-236`, colonne `label`.
- **Ce n'est PAS** : le type de mutation (succession/donation ne sont pas la cible — seule la vente
  onéreuse compte), ni le prix, ni « le propriétaire veut vendre ». C'est un fait de marché observé.
- **Unité** : la **parcelle** (IDU), grain **parcelle × année**.
- **Fenêtre** : les features sont figées **as-of le 01/01 de l'année** (toutes les fenêtres se
  terminent strictement avant le 01/01/Y) ; le label regarde `[01/01/Y, 01/01/Y+1)`. Construction
  temporelle propre (voir B.4).
- **Taux de base réel** (hors copro, ce que le modèle doit battre) : **1,55 %** par an — soit à peu
  près **1 vente pour 65 parcelles**. En copropriété, le taux est de **29 %** : d'où l'exclusion des
  copros du classement produit (elles écraseraient tout).

### A.2 — Comment il est fait

- **Type** : régression logistique **L2** sur variables encodées en *Weight-of-Evidence* (WoE, un
  bin par tranche), sortie interprétée comme un **log-hasard additif par bloc** —
  `contribution(feature) = coef × WoE(bin)`. Calibration **isotonique** par-dessus.
  `scoring/p_model/model.py`.
- **Apprentissage / validation** : artefact gelé `artifacts-m36-scoring2026.joblib` (sha256 vérifié
  au lancement, refus si écart) — **entraîné 2017-2024** (n = 3 453 304 lignes parcelle-année),
  **calibration isotonique sur 2025**, 5 croisements retenus (`tenure×permis`, `tenure×surface`,
  `ndvi×zone`, `tenure×rot_nu`, `surface×permis`), effets-année 2017-2023 (2024 = référence), C = 5.
- **Walk-forward** : `reports/m36-foncier/walk-forward.csv` — 6 plis 2020→2025. Le pli honnête
  2025 (`artifacts-m36-fold2025.joblib`, entraîné SANS 2025) sert de témoin hors-échantillon dans
  tout ce rapport.
- ⚠ **Nuance de calibration importante** : l'isotonique servie a été **ajustée sur 2025**, et le
  pipeline **recale l'intercept à chaque run sur la dernière année labellisée** (2025 aujourd'hui).
  Il n'existe donc **aucune année 100 % vierge** pour juger la calibration du modèle *servi* : la
  calibration « servie » en C.1 est **in-sample** (optimiste), le témoin `fold2025` est le vrai
  hors-échantillon. Les deux sont donnés côte à côte.

### A.3 — Les trois runs et comment ils s'articulent

Trois identifiants circulent ; ils ne désignent pas la même chose :

```
  m36-l2f-2026            q_v11_m137                         m135-run2-ile
  (LE MODÈLE)             (LE RUN SERVI)                     (LE RÉSIDUEL)
  coefficients gelés  →   applique le modèle sur les     ←   SDP résiduelle par
  + isotonique 2025       features 2026, écrit dans           parcelle (droits PLU
  sha256 au manifeste     parcel_p_score_v2, dryrun_*,        non consommés)
                          score_snapshots (label unique).     run_seq=2, 1h47 de calcul
       │                        │                                   │
       │  model_version         │  run_id / run_label = point       │  alimente le
       └───────────────────────┤  de vérité config/served_run.txt  │  « plancher C » et
                                │  (relu à la requête, bascule       │  la « réserve foncière »
                                │   à chaud par golden promote)      │  (statuts.py)
                                ▼
                          PALIERS AFFICHÉS (tiers_client.py)
```

- **`m36-l2f-2026`** = l'**artefact** (le cerveau figé). Ne change qu'au ré-entraînement annuel.
- **`q_v11_m137`** = le **run servi** : une passe du modèle sur les données du moment. C'est le même
  label qui indexe `parcel_p_score_v2` (le score P + tier), `dryrun_parcel_evaluations` (l'étage 0
  cascade), `dryrun_cascade_results` (15,9 M lignes de règles). Point de vérité unique :
  `config/served_run.txt`, relu à chaque requête (`runs.current()`).
- **`m135-run2-ile`** = le run **résiduel** (`residuel_runs.run_seq=2`, servi, calculé en 6 399 s ≈
  1 h 47). Fournit `sdp_residuelle_m2` / `sous_densite` — à la fois **features D** du modèle ET
  entrée du **plancher de capacité** qui gate les paliers de tête.

### A.4 — La chaîne complète (ce qui entre, ce qui sort, ce qui écarte)

| Étape | Entre | Sort | Peut écarter |
|---|---|---|---|
| **Feature store** (`p_model_ext_dataset`) | DVF, Sitadel, BD TOPO, Filosofi, RGE ALTI, OSM, GPU, résiduel, ortho | 29 features as-of × parcelle × année | — (une feature absente → bin « manquant/inconnu », jamais un rejet) |
| **Cascade / étage 0** (`dryrun_parcel_evaluations`) | règles de constructibilité, emprise, zone | statut `exclue`/`faux_positif_probable` | **écartée dure** : 145 882 parcelles (33,8 %) sortent du produit |
| **Scoring** (`predict_proba`) | features + intercept recalé | `p_raw`, contributions Z/D, top-5 lisible | — |
| **Policy / paliers** (`statuts.assign_tiers`) | rang hors copro, plancher C, événements datés, hystérésis, déclassements | tier interne | **déclassement** (bâti saturé, zone fermée, AU fermée, non constructible) sort des paliers de tête (visible, motivé) |
| **Présentation** (`tiers_client.py`) | tier interne | chip court (Priorité/À suivre/Long terme/Neutre/Faible/Écartée) | — |

Deux « portes » réduisent l'univers avant même le score : **l'étage 0** (33,8 % écartées) et le
**déclassement bâti/zone** (au total 138 673 parcelles en « Faible », dont 123 066 « bâti saturé »).
Il ne reste que **~137 000 parcelles « Neutre » + ~10 000 en tête** réellement classées par la
probabilité (voir D.2).

---

## B — Les données entrelacées : la carte des variables

**Ce qu'on a trouvé.** Le modèle voit la parcelle et son secteur (marché, densité, prix, végétation,
zone) et l'état de dormance de la parcelle (ancienneté de mutation, permis, capacité résiduelle) —
mais **rien du propriétaire**. Les variables qui pèsent le plus sont aussi les **plus mal couvertes**.
**Ce que ça veut dire.** Le gisement n'est pas « ajouter des variables » : c'est **compléter et
approfondir celles qui comptent déjà**, et retirer une dizaine de features mortes. **Ce qu'on peut en
faire.** Trois leviers nets ressortent (voir G).

### B.1 — Table des variables (couverture mesurée sur l'année scorée 2026, n = 431 663)

`% non-null` = renseignée ; `% informatif` = non-null ET non-défaut (bool vrai / cat hors
« inconnu/jamais »). Source : `reports/audit-scoring/b1_coverage.csv`.

| Feature | Bloc | Type | Source amont | % non-null | % informatif | Statut |
|---|---|---|---|---|---|---|
| `rot_nu` | Z | num | DVF L2 + stock secteur | 100 | 100 | actif |
| `rot_bati` | Z | num | DVF L2 + stock secteur | 100 | 100 | actif |
| `med_pm2_terrain_36m` | Z | num | DVF nu | 94,3 | 94,3 | actif |
| `med_pm2_bati_36m` | Z | num | DVF bâti | 96,1 | 96,1 | actif |
| `tendance_pm2_bati` | Z | num | DVF bâti (12m vs 36m) | 88,2 | 88,2 | actif |
| `permis_24m_norm` | Z | num | Sitadel secteur | 100 | 100 | **retirée** (futurs fits) |
| `dens_bati_secteur` | Z | num | BD TOPO | 100 | 100 | actif |
| `pct_bati_secteur` | Z | num | BD TOPO | 100 | 100 | actif |
| `filo_snv_pp` | Z | num | Filosofi 200 m | 89,3 | 89,3 | actif |
| `filo_pct_pauv` | Z | num | Filosofi 200 m | 89,3 | 89,3 | actif |
| `filo_pct_prop` | Z | num | Filosofi 200 m | 89,3 | 89,3 | actif |
| `filo_dens_pop` | Z | num | Filosofi 200 m | 89,3 | 89,3 | **retirée** |
| `qpv` | Z | bool | périmètres QPV | 100 | **9,6** | **retirée** |
| `pente_moy_deg` | Z | num | RGE ALTI 5 m | 98,1 | 98,1 | actif |
| `acces_equipements` | Z | num | OSM (école/santé/commerce/TCSP) | 100 | 100 | actif |
| `zone_plu` | Z | cat | GPU (U/AU/A/N) | 100 | 99,0 | actif |
| `window_coverage` | Z | num | déterministe | 100 | 100 | **retirée** |
| `nu_constructible` | D | bool | BD TOPO × zone | 100 | **15,5** | actif |
| `surface_m2` | D | num | référentiel parcellaire | 100 | 100 | actif |
| `dormance_droits` | D | num | résiduel `pct_potentiel` | **58,7** | 58,7 | **retirée** |
| `sous_densite` | D | bool | résiduel | **58,7** | 15,7 | actif |
| `sdp_residuelle_m2` | D | num | résiduel | **58,7** | 58,7 | actif |
| `tenure_bin` | D | cat | DVF (dernière mutation as-of) | 100 | **17,1** | actif |
| `permis_bin` | D | cat | Sitadel sur la parcelle | 100 | **8,8** | actif |
| `canopee_pct` | D | num | LiDAR/ortho | 98,7 | 98,7 | actif |
| `ndvi_moyen` | D | num | végétation | 98,7 | 98,7 | actif |
| `friche` | D | bool | Cartofriches | 100 | **0,15** | actif |
| `piscine` | D | bool | détection ortho | 100 | **4,1** | actif |
| `pv_candidat` | D | bool | candidats PV ortho | 100 | **4,6** | actif (**mort exempté**) |

**Ce que la couverture raconte.** Les features de secteur/marché (Z) sont bien couvertes (88-100 %).
Les features qui font vraiment travailler le modèle au grain parcelle sont creuses :
- `tenure_bin` **informative à 17,1 %** seulement — les 83 % restants tombent dans le bin « inconnu »
  (« aucune mutation DVF depuis 2021 »), car **la DGFiP a retiré les millésimes DVF < 2021** de la
  distribution (fenêtre glissante 5 ans). La détention longue est donc **tronquée**, pas mesurée.
- `sdp_residuelle_m2` / `sous_densite` / `dormance_droits` couverts à **58,7 %** : le run résiduel
  m135 ne couvre pas tout le parc.
- `friche` 0,15 %, `piscine` 4,1 %, `pv_candidat` 4,6 %, `nu_constructible` informatif 15,5 %,
  `permis_bin` 8,8 % : signaux rares.

### B.2 — Importance mesurée (permutation, hors-échantillon `fold2025` sur 2025, hors copro)

Baseline : AUC = **0,613**, AP = 0,027, RR@1158 = **6,84** (n = 428 239, 6 487 ventes).
`Δauc` = chute d'AUC quand on permute la variable (3 tirages). Source : `b2_importance.csv`.

| Rang | Feature | Bloc | Δ AUC | Δ RR@1158 | Couverture info. |
|---|---|---|---|---|---|
| 1 | `tenure_bin` | D | **0,0224** | 3,23 | 17,1 % |
| 2 | `zone_plu` | Z | **0,0207** | 0,57 | 99,0 % |
| 3 | `permis_bin` | D | 0,0122 | **4,87** | 8,8 % |
| 4 | `surface_m2` | D | 0,0087 | 2,47 | 100 % |
| 5 | `nu_constructible` | D | 0,0085 | 0,95 | 15,5 % |
| 6 | `rot_nu` | Z | 0,0055 | 0,68 | 100 % |
| 7 | `rot_bati` | Z | 0,0033 | 0,48 | 100 % |
| 8 | `sdp_residuelle_m2` | D | 0,0022 | 0,25 | 58,7 % |
| 9 | `sous_densite` | D | 0,0014 | 0,29 | 58,7 % |
| 10 | `tendance_pm2_bati` | Z | 0,0007 | −0,10 | 88,2 % |

**Les 10 qui comptent** : ci-dessus. Trois d'entre elles (`tenure_bin`, `permis_bin`,
`nu_constructible`) sont **importantes ET mal couvertes** → **c'est le gisement**.

**Celles qui ne comptent PAS** (Δauc ≤ 0, candidates au retrait — au-delà des déjà « retirées ») :
`friche` (0,000), `dens_bati_secteur` (−0,00002), `med_pm2_bati_36m` (−0,0001),
`acces_equipements` (−0,0006), `canopee_pct` (−0,0008), **`ndvi_moyen` (−0,0047 : la permuter
*améliore* l'AUC hors-échantillon)**, `piscine` (≈0), `pv_candidat` (mort). Les features déjà
marquées `retired` (`permis_24m_norm`, `filo_dens_pop`, `qpv`, `window_coverage`, `dormance_droits`)
confirment leur inutilité (Δauc ≤ 0,0007).

### B.3 — Dépendances (Spearman sur 2025, `b3_correl.csv`) — qui dit la même chose

| Paire | ρ | Lecture |
|---|---|---|
| `filo_snv_pp` ~ `filo_pct_pauv` | −0,88 | même dimension « richesse du carreau » |
| `dormance_droits` ~ `sdp_residuelle_m2` | −0,87 | **dérivent du même résiduel** (redondance mécanique) |
| `canopee_pct` ~ `ndvi_moyen` | +0,80 | même dimension « végétation » |
| `dens_bati_secteur` ~ `pct_bati_secteur` | +0,76 | même dimension « densité bâtie du secteur » |
| `dens_bati_secteur` ~ `acces_equipements` | +0,67 | densité ≈ accès équipements |
| `surface_m2` ~ `sdp_residuelle_m2` | +0,52 | parcelle grande → plus de résiduel |

Schéma « qui dérive de quoi » : `dormance_droits` et `sdp_residuelle_m2` sortent du **même run
résiduel m135** ; `canopee_pct`/`ndvi_moyen` de la **même couche végétation** ; les trois `filo_*`
du **même carreau Filosofi**. Garder les deux membres d'une paire à ρ > 0,8 n'apporte rien au modèle
et fragilise l'interprétation des contributions.

### B.4 — Fuites : test explicite

**Résultat : pas de fuite temporelle détectée.** La construction as-of est propre (vérifiée dans
`ext_sql.py`) :
- Features DVF : `date_mutation ≥ w36_start AND < asof` (strictement avant le 01/01/Y).
- Features permis : `date_autorisation < asof`.
- Label : `date_mutation ≥ asof AND < 01/01/Y+1` (fenêtre **postérieure** disjointe).
- Il n'y a **aucune** feature « permis déposé par l'acheteur » ni « DVF de la mutation-cible » : le
  permis compté est celui *antérieur* au 01/01/Y, et la mutation-cible est *exclue* des features par
  la borne stricte. La garde de fraîcheur `check_permits_fraicheur` refuse même un run si les
  features permis sont en retard sur la source (empêche de scorer sur des permis périmés).
- Interdits par construction (contrôlés dans le code) : statut matrice, `computed_at`, score V (ce
  dernier n'entre jamais comme feature — seulement baseline de contrôle).

Point d'attention (pas une fuite, une **quasi-staticité**) : 18 des 29 features sont d'un
« millésime unique » d'ingestion 2026 (BD TOPO, Filosofi 2019, RGE, OSM, GPU, résiduel, ortho). Pour
les années d'entraînement 2017-2024, ces features ne varient pas dans le temps — elles décrivent
l'état 2026 projeté en arrière. C'est **assumé et consigné** dans le registre (`_STATIQUE`), mais ça
signifie que le modèle apprend surtout de **DVF + Sitadel** (les seules vraiment datées) ; le reste
est du contexte figé. C'est cohérent avec B.2 (tenure/permis/zone en tête).

### B.5 — Ce qui manque (variables prédictives connues en France, absentes)

Le modèle servi est **Z (zone) + D (dormance parcelle)**. Le **bloc O (propriétaire) n'existe pas** :
`owner_type` est une méta de ventilation, **jamais une feature**. Or **81 % des parcelles (349 597)
sont détenues par des personnes physiques** — pour lesquelles LA BUSE n'a **aucune** donnée de cycle
de vie. Bilan variable par variable :

| Variable manquante | En base ? | Sous convention ? | Nulle part ? |
|---|---|---|---|
| **Âge du propriétaire** | non (PP) ; RNE dirigeant pour les 8 % PM seulement | **fichiers fonciers (MAJIC) / DV3F** | — |
| **Décès / succession** | partiel : `parcel_veille_succession` (7 129) mais **PM uniquement** (dirigeant ≥ 70 / SCI dormante) | fichiers fonciers (date naissance propriétaire) | PP : nulle part |
| **Indivision** | non | **fichiers fonciers** (droit/type de propriété) | — |
| **Propriétaire non résident** | partiel : `GEO_HORS_ILE` dans le Score V (siège PM), pas dans P | fichiers fonciers (adresse propriétaire) | PP : nulle part |
| **Vacance du logement** | non | **LOVAC** (convention dédiée) | — |
| **Durée de détention** | **partiel** : `tenure_bin` mais **tronqué à 2021** (DGFiP) | DVF+ / DV3F historique profond, fichiers fonciers | — |
| **Divorce** | non | non (pas de source ouverte) | oui |

**La conclusion de B en une phrase** : le modèle prédit une vente **sans jamais regarder le vendeur**,
alors que le cycle de vie du propriétaire (âge, succession, indivision, non-résidence) est le premier
prédicteur de vente foncière en France — et il est accessible **sous convention** (fichiers fonciers /
LOVAC / DV3F) pour les 81 % de parcelles aujourd'hui aveugles.

---

## C — La calibration réelle : est-ce que « 1/5 » vaut 1/5 ?

**Ce qu'on a trouvé.** Quand le modèle dit « 1,6 % », il se vend 1,6 % — la calibration est
excellente (écart moyen ~0,1 point). Mais il **sépare peu** : le décile le plus « chaud » ne vend
que **2,1× la moyenne** (3,1 % contre 1,5 %). **Ce que ça veut dire.** Les *probabilités* sont
honnêtes, mais le pouvoir de tri est modeste sur le tout-venant — la valeur est concentrée dans la
toute petite tête (Priorité / À suivre), qui, elle, tient sa promesse. **Ce qu'on peut en faire.**
Afficher le relatif (« ×N ») à côté de la fraction, et concentrer les efforts d'amélioration sur la
séparation (features propriétaire), pas sur la calibration (déjà bonne).

### C.1 — Calibration par décile (2025 hors copro, taux base 1,51 %)

Source : `c1_calibration_*.csv`. **Témoin hors-échantillon `fold2025`** (modèle n'ayant jamais vu
2025) :

| Décile | n | p prédite moy. | taux observé | écart | lift |
|---|---|---|---|---|---|
| 1 (froid) | 42 824 | 0,88 % | 0,72 % | +0,16 | 0,47× |
| 2 | 42 824 | 1,00 % | 0,94 % | +0,06 | 0,62× |
| 3 | 42 824 | 1,09 % | 1,03 % | +0,05 | 0,68× |
| 4 | 42 824 | 1,17 % | 1,31 % | −0,14 | 0,86× |
| 5 | 42 824 | 1,27 % | 1,32 % | −0,04 | 0,87× |
| 6 | 42 823 | 1,33 % | 1,47 % | −0,14 | 0,97× |
| 7 | 42 824 | 1,38 % | 1,55 % | −0,17 | 1,02× |
| 8 | 42 824 | 1,63 % | 1,73 % | −0,11 | 1,14× |
| 9 | 42 824 | 1,87 % | 1,98 % | −0,11 | 1,31× |
| 10 (chaud) | 42 824 | 2,80 % | **3,10 %** | −0,30 | **2,04×** |

**ECE hors-échantillon = 0,0013** (excellent). Version « servie » (isotonique in-sample sur 2025) :
ECE = 0,0009, même forme, décile 10 = 3,16 % (lift 2,08×). **AUC = 0,61** dans les deux cas. Le
message tient dans les deux colonnes : **calibré, peu discriminant sur le corps de la distribution**.

### C.2 — Par commune (24 communes, `c2_commune.csv`)

Lift du décile supérieur, taux observé, effectifs. Extrait (triées par taille) :

| Commune INSEE | n | ventes | taux base | taux top 10 % | lift top 10 |
|---|---|---|---|---|---|
| 97415 (Saint-Paul) | 50 593 | 880 | 1,74 % | 3,31 % | 1,90× |
| 97422 (Saint-Louis) | 42 523 | 726 | 1,71 % | 2,96 % | 1,73× |
| 97416 (Saint-André) | 42 045 | 636 | 1,51 % | 3,60 % | 2,38× |
| 97411 (Saint-Denis) | 36 981 | 590 | 1,60 % | 2,24 % | 1,40× |
| 97408 (Le Tampon-ex) | 13 148 | 288 | 2,19 % | 5,70 % | **2,60×** |
| … | … | … | … | … | … |
| 97419 (petite) | 6 284 | 51 | 0,81 % | 0,79 % | **0,97×** (aucun signal) |

**Lecture honnête** : lift entre **0,97× et 2,60×** selon la commune ; la plupart entre 1,4 et 2,5×.
Les grosses communes (effectif > 30 000, ventes > 500) donnent un signal fiable ; les plus petites
(97419, 97402, 97420 : ventes < 120) sont **statistiquement fragiles** — un lift y vaut peu.

### C.3 — Par type (terrain nu / bâti × zone, `c3_bytype.csv`)

| Type | Zone | n | ventes | taux base | AUC | lift top 10 |
|---|---|---|---|---|---|---|
| bâti | U | 241 763 | 3 607 | 1,49 % | 0,567 | 1,60× |
| terrain nu | U | 61 730 | 1 462 | 2,37 % | 0,567 | 1,87× |
| terrain nu | A | 43 725 | 415 | 0,95 % | **0,508** | 1,40× |
| bâti | A | 30 080 | 228 | 0,76 % | **0,513** | 1,14× |
| terrain nu | N | 24 355 | 174 | 0,71 % | 0,667 | 2,98× |
| bâti | N | 11 699 | 109 | 0,93 % | 0,578 | 1,54× |
| terrain nu | AU | 5 000 | 304 | **6,08 %** | 0,641 | 1,52× |

**Bon en U et N, aveugle en A.** En zone **agricole (A)**, l'AUC tombe à **0,51 (le hasard)** pour le
nu comme pour le bâti : le modèle **ne sait pas trier** ce qui se vend en zone A. C'est cohérent — en
A, les leviers (constructibilité, permis, capacité) sont plats ; ce qui déclenche une vente agricole
(succession, cessation d'exploitation) relève du **propriétaire**, que le modèle ne voit pas (B.5).
La zone AU nu a le taux de base le plus haut (6,08 %) : le foncier ouvert à l'urbanisation tourne.

### C.4 — Par palier affiché : le libellé tient-il sa promesse ?

**Oui, la tête tient.** Backtest honnête : on reconstruit les paliers avec la probabilité **as-of
2025** (features au 01/01/2025) et les gates statiques servis, puis on mesure les ventes **réelles
2025**. Source : `c4_paliers_backtest.csv`, taux base hors copro 1,54 %.

| Palier affiché | n | ventes | **taux de vente réel 2025** | p médiane | lift |
|---|---|---|---|---|---|
| **Priorité** (« à contacter en priorité ») | 75 | 12 | **16,0 %** | 0,204 (≈ **1/5**) | **10,4×** |
| **À suivre** (« à suivre de près ») | 670 | 63 | **9,4 %** | 0,091 (≈ **1/11**) | **6,1×** |
| Neutre (« sans signal particulier ») | 137 884 | 2 455 | 1,78 % | 0,015 | 1,15× |
| Faible (« peu de potentiel ») | 138 673 | 2 397 | 1,73 % | 0,016 | 1,12× |
| Long terme (« réserve foncière ») | 8 479 | 99 | 1,17 % | 0,011 | 0,76× |
| Écartée | 145 882 | 1 633 | 1,12 % | 0,010 | 0,73× |

**Verdicts palier par palier :**
- **Priorité** : la promesse « 1/5 » est **tenue** — p médiane 0,204 et **16 % de ventes réelles**
  (sur 75 parcelles, à prendre avec l'incertitude d'un petit effectif). 10× la moyenne.
- **À suivre** : « 1/10 à 1/5 » **tenu** — 9,4 % réels, 6× la moyenne.
- **Faible ≈ Neutre pour la VENTE (1,12× vs 1,15×)** : ⚠ subtilité à connaître. « Faible / peu de
  potentiel » ne veut **pas** dire « ne se vendra pas » — ces parcelles (bâti saturé, non
  constructible) **se vendent au taux de base**. Le libellé parle de **potentiel de projet**, pas de
  probabilité de vente. Honnête (le motif est en fiche), mais un client pourrait le lire de travers.
- **Réserve foncière / Écartée** : vendent **moins** que la moyenne (0,76× / 0,73×) — cohérent avec
  leur définition (P sous la médiane / exclue).

Sur le **run servi 2026** (sans label encore), les mêmes paliers portent : Priorité **×7,1 vs
moyenne** (p médiane 0,111), À suivre **×5,1** (p médiane 0,079). Les multiplicateurs affichés
(`mult_base`) sont donc **honnêtes**.

### C.5 — Stabilité q_v10 → q_v11 (`hd_stability_matrix.csv`)

**Ultra-stable : 220 parcelles sur 431 663 changent de palier (0,05 %).** Matrice : Neutre↔Long
terme (51+2), À suivre→Neutre (124), Priorité/À suivre→réattributions fines (43). Aucune bascule de
masse. C'est **attendu** (même modèle gelé, hystérésis anti-churn, seules DVF/Sitadel rafraîchies +
recalage d'intercept) — et c'est aussi la raison pour laquelle un **re-score mensuel bouge très peu**
(voir H.2).

---

## D — Les paliers : logique et alternatives

**Ce qu'on a trouvé.** Les seuils ne sont pas des probabilités absolues : ce sont des **rangs**
calibrés mécaniquement pour remplir des effectifs cibles (~1 150 en tête), avec un plancher de
capacité et une hystérésis. **Ce que ça veut dire.** Les paliers sont une **politique de tri**, pas
une échelle de probabilité — deux runs peuvent avoir la même « Priorité » avec des p différentes.
**Ce qu'on peut en faire.** On peut simuler une échelle en **probabilité absolue** (≥ 1/5 / 1/10) et
voir ce qu'elle donnerait, sans rien changer.

### D.1 — Comment les seuils sont fixés aujourd'hui (`statuts.py`, `pipeline.py`)

- **chaude (À suivre)** : `rang hors copro ≤ n_entree` **ET** plancher C, avec `n_entree` **calibré
  pour ~1 150 éligibles** (`calibre_n_entree`, cible=1150 ; run servi : n_entree = 2 358 en rang
  brut). Ce n'est **pas** un seuil de probabilité — c'est un quantile de rang.
- **brûlante (Priorité)** : chaude **ET** contribution D ≥ seuil, seuil **calibré mécaniquement**
  pour tomber dans le garde-fou **[30, 120]** brûlantes (`calibre_brulante`), avec bypass si
  événement daté < 12 mois. Run servi : 111 brûlantes.
- **plancher C** : SDP résiduelle > 0 **OU** (surface ≥ 600 m² en U/AU, ou dans la PAU au RNU).
- **réserve foncière (Long terme)** : SDP dans le **top décile** des SDP > 0 **ET** p < médiane.
- **hystérésis** : une parcelle déjà chaude le reste tant que `rang ≤ 1,4 × n_entree` (anti-churn).
- **déclassements** (Faible) : caches `parcel_constructibilite`, `parcel_au_statut`,
  `parcel_bati_revele`, `parcel_filtre_bati` — priment sur les paliers normaux, sortent de la tête.

### D.2 — Ce que chaque palier contient (run servi q_v11_m137, `d2_composition_paliers.csv`)

| Palier | effectif île | p médiane | % terrain nu | % bâti |
|---|---|---|---|---|
| Priorité (brûlante) | 111 | 0,111 | 51 % (57) | 49 % (54) |
| À suivre (chaude) | 1 367 | 0,079 | ~21 % | ~79 % |
| Long terme (réserve) | 8 789 | 0,011 | ~15 % | ~85 % |
| Neutre (à creuser) | 136 841 | 0,014 | ~26 % | ~74 % |
| Faible (déclassé ×6) | 138 673 | 0,016 | ~4 % | ~96 % |
| Écartée | 145 882 | 0,010 | ~64 % | ~36 % |

(Répartition nu/bâti par palier sur le backtest 2025 dans `d2_composition_paliers.csv`.) La
« Faible » est massivement bâtie (bâti saturé) ; l'« Écartée » massivement nue (étage 0 : emprises,
non-bâtissable dur).

### D.3 — Simuler l'alternative : trois niveaux en probabilité absolue + deux états

Politique **mesurée, non appliquée** : **Priorité ≥ 1/5** · **À suivre 1/10-1/5** · **Sans signal
< 1/10**, plus l'état **En vente** (annonce Radar rattachée, au-dessus) et **Écartée** (cascade).
Sur le run servi 2026 (p_raw hors copro, 428 239 parcelles + 145 882 écartées) :

Effectifs **mesurés** sur `p_raw` servi (hors copro, hors écartée), île entière et Saint-Paul :

| Niveau (probabilité absolue) | seuil p | **effectif île mesuré** | **Saint-Paul (97415)** |
|---|---|---|---|
| **Priorité** (p ≥ 0,20) | ≥ 1/5 | **101** | **22** |
| **À suivre** (0,10 ≤ p < 0,20) | 1/10-1/5 | **234** | **30** |
| **Sans signal** (p < 0,10) hors écartée | | 282 298 | 33 391 |
| **En vente** (état, Radar rattaché) | fait | **7** (île entière) | à ventiler |
| **Écartée** (cascade étage 0) | fait | 145 882 | 17 219 |

Comparaison à l'affichage **actuel de Saint-Paul** (Priorité 21 / À suivre 264 / Long terme 1 251 /
Neutre 21 774 / Faible 10 600 / Écartée 17 219 — chiffres relevés en base ; l'énoncé du mandat
donnait 17 095). Deux enseignements **mesurés** :

- **Priorité serait quasi inchangée** : 101 (île) / 22 (Saint-Paul) vs 111 / 21 aujourd'hui — le
  seuil 1/5 ≈ le calibrage brûlante actuel. La promesse serait **lisible littéralement** (« 1/5 »
  veut dire 1/5).
- **À suivre RÉTRÉCIRAIT fortement** : 234 (île) / 30 (Saint-Paul) contre **1 367 / 264** aujourd'hui.
  Le palier « chaude » actuel est **calibré par rang** (~1 150 cible), il ratisse donc des parcelles
  à p ≈ 0,04-0,10 qu'un seuil strict 1/10 exclurait. **Choix de politique** : afficher moins mais
  plus vrai (absolu), ou plus large mais « meilleurs 1 150 » (rang). À trancher par Vic — les deux
  sont défendables, ce ne sont pas les mêmes clients servis.
- « Long terme » et « Neutre » **collapsent dans « Sans signal »**, et « Faible » **sort de l'échelle
  de probabilité** (état de constructibilité). **Coût** : la vitrine « réserve foncière » (capacité)
  doit être ré-exposée comme **état/onglet séparé**, pas comme palier.

> Note de méthode : effectifs lus directement sur la distribution de `p_raw` servie
> (`SELECT count FILTER(WHERE p_raw>=…)`). Aucun palier réel n'a été modifié.

### D.4 — Le relatif (lift à afficher à côté de la fraction)

| Palier | lift réel (backtest 2025) | `mult_base` servi (2026) |
|---|---|---|
| Priorité | **10,4×** | 7,1× |
| À suivre | 6,1× | 5,1× |
| Neutre | 1,15× | 0,93× |
| Faible | 1,12× | 1,00× |
| Long terme | 0,76× | 0,70× |
| Écartée | 0,73× | 0,67× |

**Recommandation** : afficher le **×N** à côté de la fraction pour Priorité/À suivre uniquement (là
où il est spectaculaire et vrai : ×6 à ×10). Pour Neutre/Faible, le ×1 ne dit rien d'utile — ne pas
l'afficher (ou dire « au niveau de la moyenne »).

---

## E — Le Radar dans l'algorithme (préparer l'injection)

**Ce qu'on a trouvé.** Le Radar a **5 jours de collecte** : 109 biens, **7 rattachés à une
parcelle**, **0 paire annonce→vente**, 0 historique de prix. **Ce que ça veut dire.** Il est bien
trop tôt pour en apprendre quoi que ce soit — le **goulot est le rattachement** (7/109 = 6,4 %), pas
la collecte. **Ce qu'on peut en faire.** Brancher tout de suite le seul usage honnête (l'**état
« En vente »**), et préparer le schéma des deux autres usages pour le jour où les seuils seront
atteints — mais ne rien apprendre avant.

### E.1 — Inventaire de ce que le Radar produit par parcelle (base réelle, `pige_biens`)

| Champ | Disponible | Quantité aujourd'hui |
|---|---|---|
| annonce active (depuis quand) | oui (`date_premiere_saisie`) | 104 actives + 5 « en vente longue » |
| prix demandé | oui (`pige_faits.prix`) | 109 biens |
| écart au référentiel | calculable (`vendue_ecart_prix` pour les vendues) | 0 (aucune vendue) |
| **baisse de prix** | table `pige_prix_historique` | **0 ligne** — aucun historique encore |
| retrait | oui (`retiree_le`) | 0 |
| **vendue (paire DVF)** | oui (`vendue_le/valeur/delai_j`) | **0 paire** |
| **rattaché à une parcelle** | `idu` + `rattachement_etat` | **7 rattachés** (conf. « source » 0,79), 13 pistes, 89 non rattachés |

Collecte démarrée le **2026-08-29** (les `first_publication_date` remontent à 2025-04 = annonces
anciennes republiées). `radar_releves` (l'agrégat quotidien) est **vide** — le job `radar-releves`
(cron 13 h) n'a pas encore de série.

### E.2 — Trois natures à ne pas confondre

1. **Un fait — « en vente »** → un **état affiché au-dessus des paliers**, jamais une variable. C'est
   le seul usage **honnête aujourd'hui** (7 parcelles). Il ne s'apprend pas, il s'affiche.
2. **Une variable — « en vente depuis 24 mois sans se vendre », « baisse de prix »** → entrerait dans
   le hasard (bloc D), avec sa couverture. **Impossible aujourd'hui** : 0 historique de prix, 5
   « en vente longue » seulement. Exigerait des mois de série.
3. **Une cible — paires annonce → vente DVF** → un **modèle à part** qui apprend le **délai** et
   l'**écart demandé/acté**. **Impossible aujourd'hui** : 0 paire.

### E.3 — Seuils d'honnêteté et date estimée

Règle : **jamais un effet appris sur < 30 observations.**
- **État « en vente »** : ✅ **déjà utilisable** (fait, pas d'apprentissage) — 7 parcelles.
- **Variable « baisse / vente longue »** : besoin de **≥ 30 parcelles rattachées avec historique**.
  Aujourd'hui 7 rattachées, 0 historique. Le **goulot est le rattachement** : à 6,4 % de taux de
  rattachement, il faut **~470 biens** pour 30 rattachées ; OU améliorer le rattachement (13 pistes
  en attente + adresse exacte). **Estimation : impossible à dater sur 5 jours de données** (la série
  quotidienne `radar_releves` est vide). Il faut **1 mois de collecte** pour poser un débit fiable —
  ce qui est exactement le plan de Vic. À dire tel quel : *« on redonnera une date quand la série
  aura un mois ».*
- **Cible « paires »** : besoin de **≥ 30 paires annonce→DVF**. À un taux de vente de ~1,5 %/an sur
  les rattachées, 30 paires « naturelles » prendraient **des années** — sauf si le matcher
  annonce→DVF **rattrape les ventes passées** (une annonce 2025 dont la mutation est déjà dans DVF).
  C'est la voie réaliste, à instruire au moment venu. **Le rattachement reste le goulot.**

### E.4 — Le schéma prêt à mandater (au seuil atteint)

- **Table** : `pige_biens` (déjà là : `idu`, `rattachement_*`, `vendue_le/valeur/delai_j/ecart_prix`).
- **Colonnes à alimenter** : `pige_prix_historique` (série de prix pour la baisse — vide),
  `radar_releves` (débit quotidien — vide).
- **Job** : `radar-cycle` (2 h 30) + `radar-releves` (13 h) existent déjà.
- **Injection** : (1) **état** = jointure `pige_biens.rattachement_etat='rattachee'` → badge
  au-dessus du palier, **hors du modèle** ; (2) **variable** = feature D `en_vente_longue_mois` /
  `baisse_prix_pct` **au prochain ré-entraînement seulement**, quand couverture ≥ 30 ; (3) **cible** =
  table dédiée `radar_paires` + modèle délai/écart séparé. **Ne jamais mélanger les trois.**

---

## F — Le retour terrain (préparer la capture)

**Ce qu'on a trouvé.** Le vocabulaire de suivi existe déjà (`crm_columns` : 8 étapes de Repérée à
« À abandonner »), mais **presque personne ne l'a rempli** (176 fiches, ~1 compte actif, toutes en
début de tunnel ; 0 courrier réellement envoyé ; 0 feedback). **Ce que ça veut dire.** L'ossature
est là ; il manque **la donnée** et **le geste « un clic »** qui capture le résultat d'un contact.
**Ce qu'on peut en faire.** Enrichir le vocabulaire existant de quelques statuts de *sortie*
(refus / pas maintenant / vendu à nous / vendu à un autre), poser le clic sur la fiche, et attendre
d'avoir des centaines d'étiquettes avant d'en faire un modèle.

### F.1 — Ce qui existe déjà (base réelle)

| Surface | Table | Contenu réel | Exploitable comme étiquette ? |
|---|---|---|---|
| CRM Kanban | `pipeline_entries` (176) | statuts : `contact_a_preparer` 117, `reperee` 58, `proprietaire_a_identifier` 1 ; 30 archivées ; **1 seul compte actif** | partiellement : que du **haut de tunnel**, jamais un résultat de vente |
| Colonnes CRM | `crm_columns` | **8 étapes** : Repérée · Propriétaire à identifier · Contact à préparer · Contacté · Relance prévue · En discussion · Opportunité chaude · **À abandonner** | **oui** — l'ossature du vocabulaire est déjà là |
| Courrier | `courrier_envois` (3) | statut **`simule` ×3** (aucun envoi réel) | non (pas de « répondu / sans réponse » réel) |
| Signalements | `signalements` (19) | `type_erreur` : **erreurs de donnée**, pas volonté de vendre | non (autre usage) |
| Feedback fiche | `parcel_feedback` (**0**) | verdict/commentaire — **jamais utilisé** | non |

### F.2 — Le vocabulaire minimal proposé (un clic, jamais un formulaire)

Le vocabulaire du mandat recouvre `crm_columns` à ~70 %. Proposition : **garder les 8 étapes** et
ajouter **4 statuts de sortie** (aujourd'hui absents), posés **en un clic sur la fiche** (bouton
d'état, pas de formulaire) :

```
  contacté · pas de réponse · refus ferme · pas maintenant ·
  ouvert à discuter · en négociation · vendu à nous · vendu à un autre
```

Correspondance : `contacte`, (nouveau `sans_reponse`), (nouveau `refus_ferme`), (nouveau
`pas_maintenant`), `en_discussion`, `chaud`→`en_negociation`, (nouveaux `vendu_nous` /
`vendu_autre`). **Où le poser** : sur la **fiche parcelle** (bloc CRM déjà présent) et dans le
**Kanban** (glisser = changer d'état). Aucun nouvel écran.

### F.3 — Confidentialité

Ces étiquettes **appartiennent au compte qui les pose** (`pipeline_entries.compte_id`, déjà
cloisonné — cf. audits CRM/cloison antérieurs). Elles **ne peuvent nourrir un modèle commun
qu'agrégées et anonymisées** : un « refus ferme » chez un agent ne doit jamais être lisible par un
autre. Implication concrète : un futur modèle « volonté de vendre » devra apprendre sur des
**comptages agrégés par zone/segment**, jamais sur l'étiquette nominative d'un compte — sinon on
fuit du renseignement commercial entre concurrents.

### F.4 — Seuil d'utilité

Un modèle « volonté de vendre » (distinct de « va se vendre ») a besoin d'un **signal binaire
équilibré** : au bas mot **quelques centaines d'issues tranchées** (refus vs ouvert vs vendu), soit
**≥ 200-300 étiquettes de sortie** avant d'espérer mieux que le hasard, et **≥ 30 par classe** pour
un effet. Aujourd'hui : **0 étiquette de sortie**. Le préalable est donc **le geste de capture**, pas
le modèle — poser le clic, laisser les comptes remplir 6-12 mois, mesurer, puis mandater.

---

## H — Recalcul mensuel : cadrer le CRON avant de le poser

**Ce qu'on a trouvé.** Le re-score existe en commande (`labuse score-v2`) et un juge de bascule
existe (`arene`, lecture seule, avec budget de churn et garde de calibration) — mais **aucun CRON ne
les enchaîne** : le re-score mensuel est **manuel**. **Ce que ça veut dire.** La position « calcul
auto, mise en service manuelle » est déjà **à moitié outillée** ; il manque le chaînage et la note de
version. **Ce qu'on peut en faire.** Poser un CRON qui produit un **run candidat + un avis d'arène +
une note de version**, et laisser Vic basculer à la main — sans jamais rien mettre en service tout
seul.

### H.1 — Re-scorer ≠ ré-entraîner (ce que le pipeline fait des deux)

- **Re-scorer** (mensuel, sûr) : même artefact gelé (sha256 vérifié), features rafraîchies
  (DVF/Sitadel), **recalage du seul intercept** sur la dernière année labellisée. **C'est ce que
  `labuse score-v2` fait.** Ne touche ni coefficients ni binning ni calibration isotonique.
- **Ré-entraîner** (rare, suivi) : re-binning + coefficients + calibration → **décision humaine
  annuelle**, nouveau walk-forward, nouveau manifeste de gel. Le pipeline **refuse** de le faire
  automatiquement (documenté dans `pipeline.py`).

### H.2 — Ce qui bouge d'un mois à l'autre (mesuré q_v10 → q_v11)

**Très peu : 220 parcelles / 431 663 changent de palier (0,05 %)** — cf. C.5. Détail des causes :
- Le modèle est **gelé** → aucun mouvement ne vient des coefficients.
- Seuls bougent : **DVF/Sitadel rafraîchis** (tenure/permis/rotation) + **recalage d'intercept** +
  re-calibrage mécanique de `n_entree`/seuil brûlante. Ces effets sont amortis par **l'hystérésis**.
- **Conséquence pour la cadence** : puisque ~100 % des mouvements viennent de **DVF + Sitadel**, la
  cadence doit se caler sur **leur** fraîcheur — DVF (semestriel DGFiP, ~6 mois de latence) et
  Sitadel (mensuel, cron le 10). Re-scorer plus souvent que l'arrivée de DVF ne bouge presque rien.
  **Un re-score juste après `ingest-sitadel` (mensuel) est le bon rythme ; un re-score « lourd »
  (avec DVF frais) n'a de sens qu'au rythme semestriel de DVF.**

### H.3 — Coût et durée

- **Scoring pur** (`run_score_v2`) : **~226 s** (run servi), 431 663 parcelles. Négligeable.
- **Rebuild features** (DVF union + dataset + permis) : inclus, quelques minutes.
- **Résiduel (m135)** : **6 399 s ≈ 1 h 47** — c'est **le** poste lourd, mais il ne bouge que si le
  bâti/PLU change (rare). Il **ne doit pas** tourner chaque mois.
- **Total mensuel réaliste** (score + features, sans résiduel) : **< 10 min** — tourne de nuit sans
  gêner la prod. Un **run incrémental** est déjà de fait le cas (résiduel exclu). Le « ~3 h » évoqué
  dans le mandat = résiduel + cascade complète, à réserver aux ré-entraînements/bascules majeures.

### H.4 — La cadence proposée

```
  1er du mois (nuit)                    ce qui existe / manque
  ──────────────────────────────────────────────────────────────────
  1. ingest-sitadel (cron 10)   ........ EXISTE (cron.d-labuse)
  2. labuse score-v2 (candidat) ........ EXISTE en CLI — MANQUE le cron
     → run_id = candidat-AAAA-MM, sans bascule
  3. labuse arene --challenger  ........ EXISTE (lecture seule) : RR@1158 +
     candidat --champion servi           IC95 bootstrap, ECE delta, churn top-1158,
                                          boussole golden — AVIS promouvoir/rejeter
  4. NOTE DE VERSION générée    ........ MANQUE — à écrire :
     « run octobre : DVF 2026-S1, 312 annonces,     (composer depuis le retour
       N montent / M descendent, causes »            de run_score_v2 + arene)
  5. notification admin         ........ EXISTE (cloche/digest) — à câbler sur (4)
  6. Vic bascule ou refuse      ........ EXISTE : golden promote (geste manuel)
```

**Recommandation** : ajouter **un seul cron** (le 1er, la nuit) qui lance `score-v2` en run
**candidat** puis `arene`, écrit la **note de version** et **notifie** — **jamais `promote`**. La
bascule reste le clic de Vic (`golden promote <run>`), après lecture de l'écart.

### H.5 — Ce que voit le client

La **date d'analyse** change à chaque bascule (déjà géré : « Analyse LA BUSE arrêtée au JJ/MM »).
**Proposition** : puisque 0,05 % des parcelles bougent, ne **pas** noyer le client de « ça a
changé » ; mais sur **ses parcelles suivies** (CRM/veille), afficher un liseré « palier modifié au
JJ/MM » **uniquement** pour les rares qui changent — c'est peu coûteux (220 parcelles île entière) et
ça inspire confiance (« ils recalculent vraiment »).

### H.6 — Garde-fous (X proposé)

L'arène **calcule déjà** les deux gardes : **churn top-1158** (budget par défaut 0,25) et **ECE non
dégradée de plus de 0,01**, avec un avis **« rejeté »** si l'un saute. **Proposition de X** : un run
candidat est **refusé par défaut et signalé** si **> 15 % du top des paliers (Priorité+À suivre)
change** (cohérent avec la cible anti-churn < 15 % de `statuts.py`) **OU** si l'ECE hors-échantillon
se dégrade de **> 0,01** **OU** si une violation de la **boussole golden** apparaît. Ces trois
existent dans `arene.decide_avis` — il suffit de **brancher le refus par défaut sur son avis** et de
ne notifier « prêt à basculer » que sur un avis favorable.

---

## G — Verdict et plan

### G.1 — En cinq lignes

1. Le modèle est **honnête et bien calibré** (« 1,6 % » se vend 1,6 % ; ECE ≈ 0,001 hors-échantillon)
   et sa **tête tient sa promesse** : Priorité = **16 % de ventes réelles / ×10 la moyenne**, À
   suivre **×6**.
2. Mais il **sépare peu sur le tout-venant** : décile supérieur **×2 seulement** (3,1 % vs 1,5 %),
   **AUC 0,61**.
3. Il est **aveugle en zone agricole** (AUC 0,51) et, plus profondément, **aveugle au propriétaire**
   (81 % des parcelles en personne physique, 0 donnée de cycle de vie).
4. Ses variables les plus fortes (`tenure_bin`, `permis_bin`, `nu_constructible`) sont ses **plus mal
   couvertes** (17 %, 9 %, 16 %) — le gisement est là, pas dans de nouvelles features.
5. La mécanique de bascule (arène, gardes de churn/calibration, hystérésis) est **saine et prudente**
   — il manque surtout le **chaînage mensuel** et la **note de version**.

### G.2 — Les trois investissements qui rapportent le plus (classés gain / effort)

| # | Investissement | Ce qu'il faut | Gain attendu | À mesurer avant/après |
|---|---|---|---|---|
| **1** | **Bloc propriétaire (O)** : âge, indivision, non-résidence, succession pour les **81 % de PP** | **convention DGFiP fichiers fonciers (MAJIC/DV3F) ou LOVAC** ; ré-entraînement | **Élevé** — c'est LE prédicteur français absent ; devrait relever l'AUC surtout en zone A (aujourd'hui 0,51) | AUC/RR@1158 par walk-forward, ventilé par zone et owner_type, avant/après |
| **2** | **Compléter le résiduel (SDP) de 58,7 % → ~100 %** | interne : étendre `m135` à tout le parc (coût 1 h 47 → à paralléliser) | **Moyen** — `sdp`/`sous_densite`/`nu_constructible` sont dans le top-5 ; complète plancher C + réserve foncière | couverture `sdp_residuelle_m2`, Δauc de `sdp`/`sous_densite`, effectif « réserve foncière » |
| **3** | **Nettoyage + profondeur DVF** : retirer les features mortes (`ndvi`, `canopee`, `acces_equipements`, `friche`, `dens_bati`) et **approfondir l'historique DVF** (tenure) sous convention | interne (retrait, faible effort) + convention pour l'historique < 2021 | **Moyen, effort faible** — réduit le sur-ajustement (ndvi Δauc **négatif**), rend `tenure_bin` (top-1) pleinement informative | Δauc hors-échantillon avant/après retrait ; % informatif de `tenure_bin` |

**Ordre de priorité opérationnel** : #3 (nettoyage) tout de suite (gratuit, réduit le bruit) ; #2
en interne (dette technique du résiduel) ; #1 dès qu'une convention est signée (le vrai saut de
performance, mais dépend d'un tiers).

### G.3 — Ce qu'il ne faut PAS faire

- **Ne pas toucher aux seuils sans recalibrer** — la calibration est un actif rare (ECE 0,001) ;
  bricoler `n_entree`/brûlante à la main le casserait.
- **Ne pas ajouter de variables à < 5 % de couverture** (`friche` 0,15 %, `piscine` 4 %) : elles
  n'apportent rien et gonflent le risque de sur-ajustement.
- **Ne pas injecter le Radar comme variable avant 30 rattachées** (7 aujourd'hui) — l'état « en
  vente » oui, la variable non.
- **Ne pas sur-ajuster** en re-entraînant sur 2025 puis en jugeant sur 2025 (le piège actuel de la
  calibration in-sample) : toujours un pli **hors-échantillon** (`fold`).
- **Ne pas basculer automatiquement** : garder `promote` manuel, l'arène en conseil.

### G.4 — Mandats suivants proposés (Vic tranche)

1. **SCORING-2 — Nettoyage & re-freeze** : retirer les ~5 features mortes, re-walk-forward,
   re-freeze l'artefact, vérifier 0 régression de calibration. Effort faible, gain de robustesse.
2. **RÉSIDUEL-COMPLET** : étendre le run m135 à 100 % du parc (parallélisation), mesurer le gain sur
   plancher C et les features D. Interne, dette technique.
3. **CONVENTION-PROPRIÉTAIRE** : instruire l'accès fichiers fonciers/LOVAC, prototyper le bloc O sur
   un échantillon, mesurer l'AUC en zone A avant d'engager. Dépend d'un tiers, plus haut gain.
4. **CRON-MENSUEL** : câbler le chaînage H.4 (candidat → arène → note de version → notif), sans
   `promote`. Effort faible, ferme la boucle d'exploitation.

---

*Scripts : `scripts/audit/scoring/{_common,measure}.py` (rejouables, lecture seule).
Sorties chiffrées : `reports/audit-scoring/*.csv`. Harnais validé contre la production
(écart médian 1,7·10⁻⁷ sur 431 663 parcelles).*
