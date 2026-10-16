# PLU-CALIBRAGE-10 — Distance entre constructions (ex-article 8) + ratio SHAB/SDP du moteur

Branche `feat/plu-calibrage-10` (depuis `main` `074cd6cd`) · worktree `~/Desktop/labuse-plu10` ·
ports réservés 8821 / 6021 (jamais démarrés). Aucun merge, aucun run résiduel, aucune migration,
rien en prod, aucune interface touchée.

Objet : brancher dans le moteur d'implantation (IMPLANTATION-1) la règle PLU d'implantation des
constructions **les unes par rapport aux autres sur une même propriété** (classiquement l'article 8),
et relever le ratio SHAB/SDP en sortant les coursives extérieures ouvertes de la surface de plancher.

Source de lecture (LOT A/B) : table `plu_reglement_extrait` (règlements PLU opposables servis par le
réservoir GPU, texte verbatim + article + page PDF), lue en **lecture seule**. Les citations des
feuilles calibrées en sont extraites telles quelles (aucune valeur fabriquée).

---

## LOT A — OÙ EST LA RÈGLE (lecture seule, 24 communes)

Méthode : recherche plein-texte dans `plu_reglement_extrait` des formulations canoniques de la règle
(« implantation des constructions **les unes par rapport aux autres** sur une même propriété / unité
foncière », « **entre deux constructions / bâtiments** », « non contiguës … distantes de … »), puis
lecture du verbatim article par article.

### Réconciliation avec FAISA-ETUDE-AUDIT-1 (« 3/23 »)

FAISA-ETUDE-AUDIT-1 annonçait la règle « trouvée » dans **3 communes seulement** (97410, 97412, 97422)
— mais ce comptage portait sur les YAML **déjà transcrits**, pas sur une lecture des règlements : un
`grep « entre construction/bâtiment »` dans la calibration existante. C'était donc un **plancher de
transcription**, pas l'état du PLU.

La lecture du corpus règlementaire corrige nettement ce chiffre : **la règle existe, chiffrée ou en
silence explicite, dans ~20 des 23 communes dotées d'un PLU** (quasiment toutes gardent l'article 8 /
l'article 5-ou-3 « implantation … les unes par rapport aux autres »). Les seuls vrais manques ne sont
pas des silences du règlement mais des **lacunes d'extraction** du corpus (4 communes). Écart avec
3/23 : **intégralement expliqué** — 3/23 = ce qui était déjà saisi, pas ce que disent les règlements.

### Tableau commune par commune

| INSEE | Commune | Statut | Où / quelles zones (verbatim résumé) |
|------|---------|--------|--------------------------------------|
| 97401 | Les Avirons | **Trouvée** | Art. 8. `U` : 6 m (constr. principales Ua/Uc/Ud), 3 m (dépendances), Ub 1,90 m ; `UE`/`AUEC`/`AUT` **fixe 3 m** ; `A`/`AUES`/`N` **silence** (« Sans objet »). |
| 97402 | Bras-Panon | **Trouvée** | Art. 8. `UA`/`UB`/`UC`/`UD` **fixe 6 m**, `UE` **fixe 8 m** ; `A`/`N`/`AUST` **silence** (« Non réglementée »/« Sans objet »). |
| 97403 | Entre-Deux | **Trouvée** | Art. 5 (PLU 2016). `U` réglée (U5.2) ; `AU` renvoi à la zone U indicée ; `A`/`N` **silence** (« Sans objet »). |
| 97404 | **L'Étang-Salé** | **Non lu (lacune corpus)** | Règlement à chapitres (2.x). L'extrait servi ne contient que la zone N + les titres : **l'article inter-bâtiments des zones U/AU n'est pas extrait**. Témoin UA → règle **non servie** (voir LOT C). |
| 97405 | Petite-Île | **Trouvée (partielle)** | Art. A.8 : habitations **8 m**, annexes 4 m, secteur Ac **5 m**. Zones U/AU non captées par l'extrait (à confirmer). |
| 97406 | La Plaine-des-Palmistes | **Trouvée** | Art. 8. `Ua`/`Ue` **fixe 3,50 m**, `Uc`/`Ur` **fixe 7 m**, `N` **fixe 10,50 m** ; `A` **silence**. |
| 97407 | Le Port | **Trouvée** | Art. 6 (PLU 2016). `Ua`/`Ub`/`Ud`/`Umi` **fixe 3 m**, `Ue` **fixe 5 m**, `Uc` (variante RHI) ; `A`/`N`/`Up` **silence** (« Non réglementé »), `Uoap` renvoi OAP. |
| 97408 | La Possession | **Trouvée** | Art. 8. `UA`/`UB`/`UEM`/`AUBM` **relative (H+h)/2, min 3 m** (secteur UAv **fixe 6 m**), `UE` **fixe 3 m** ; `A`/`N`/`AUST`/`UT` **silence** (« Sans objet »). |
| 97409 | **Saint-André** | **Non lu (lacune corpus)** | **Aucune ligne de règlement dans le corpus** (extraction absente pour 97409). Témoin UC → règle **non servie**. |
| 97410 | Saint-Benoît | **Non lu (lacune corpus)** | Extraction partielle (8 sections, PLU 2016 par sous-sections) sans article d'implantation inter-bâtiments capté. (FAISA l'annonçait « p.1430 » — introuvable dans le corpus actuel.) |
| 97411 | **Saint-Denis** | **Trouvée** | Art. `.8`. Quasi toutes zones **relative (H+h)/2, min 4 m** ; `Ua` **(H+h)/3, min 2 m** ; `Up` 4 m/5 m selon R+1+C = **forme hors schéma** ; `Uma` « desserte/incendie » (non chiffrée) ; `Uv`/`AUx` **silence**. Témoin **Ui** = (H+h)/2 min 4 m. |
| 97412 | Saint-Joseph | **Trouvée** | Art. 8. `U1`–`U6` **relative : moitié de la hauteur du plus haut bâtiment** ; `N` (Ntoh/Ntol/Nba **4 m**, Ntok **8 m**). |
| 97413 | Saint-Leu | **Non lu (lacune corpus)** | **Aucune ligne de règlement dans le corpus** (extraction absente pour 97413). |
| 97414 | Saint-Louis | **Trouvée** | Art. 8. `UA`–`UZ` **fixe 4 m** ; `A`/`N`/`AUST` **silence** (« Non réglementée »/« Sans objet »). |
| 97415 | Saint-Paul | **Trouvée** | Art. 8. Principal **fixe 3 m** (U2E/U3E/N/AU3ST/AU5E/AU5ST…), `AU6ST`/`N` (Ntol) **fixe 4 m** ; `AU4ST`/`AU5ST` listes par secteur (multi-valeurs). |
| 97416 | Saint-Pierre | **Silence prouvé** | Eco-PLU, art. 3 pt 3/ « les unes par rapport aux autres sur une même **parcelle** → **Non réglementée** » sur les zones U (Ua/Ud/Ue/Uf/Ug…). Règle **présente mais silence**. |
| 97417 | **Saint-Philippe** | **Sans objet — RNU** | Commune au Règlement National d'Urbanisme : pas de PLU, pas d'article 8. |
| 97418 | Sainte-Marie | **Trouvée** | Art. 6 (PLU 2016, « par rapport aux autres constructions »). `U`/`UE` **fixe 3 m** (+ clause lotissement/division), `A`/`N` **fixe 3 m**. |
| 97419 | Sainte-Rose | **Trouvée** | Art. 8. `UA`/`UB`/`UC`/`UD`/`AUTO` **conditionnelle : (H+h)/2, min 6 m avec baie / 3 m sans**, `UE` **fixe 3 m** ; `A` (sauf Ai), `N` (sauf Nec/Nrev) **silence**. |
| 97420 | Sainte-Suzanne | **Trouvée** | Art. 6 (PLU 2016). `U` **silence sous réserve de 6 m entre ouvertures de pièces principales** ; `UE` réglée ; `A`/`N` **silence** (« Sans objet »). |
| 97421 | Salazie | **Trouvée** | Art. 8. `U`/`UT` **conditionnelle : 3 m si une façade comporte des baies** (sinon non imposé), `AUE` **fixe 3 m** ; `A` (sauf Aba 3 m si baies), `N` **silence**. |
| 97422 | Le Tampon | **Trouvée — forme hors schéma** | Art. 8. `Ua`–`Ue`/`A`/`N` : **3 m, porté à 6 m si > 5 logements, hors coursives** → **seuil par nombre de logements**, forme non prévue au schéma → **STOP** (non calibrée en l'état, voir §LOT B). |
| 97423 | Les Trois-Bassins | **Trouvée** | Art. 8. `Ua`/`Ub`/`Uc` **relative D=H/2 (plus haut), min 4 m**, `Ue` **fixe 6 m**, `N` **D=H/2, min 8 m** ; `A` **silence** (« Non réglementé »). |
| 97424 | Cilaos | **Trouvée** | Art. 8. `Ua`/`Uc` **fixe 4 m** ; `A`/`N` **fixe 4 m** (règle générale 4 m). |

**Bilan LOT A :** règle **lisible** (chiffrée ou silence prouvé) dans **19 communes** ; **silence prouvé
d'ensemble** = Saint-Pierre (règle présente, « Non réglementée ») ; **non lu (lacune d'extraction,
≠ silence)** = L'Étang-Salé (U/AU), Saint-André, Saint-Benoît, Saint-Leu ; **sans objet** = Saint-Philippe (RNU).

---

## LOT B — CALIBRAGE (schéma + zones)

### Schéma (une seule forme par feuille, le reste = STOP)

Nouvelle feuille `retraits.entre_constructions` dans `config/plu_destinations/974*.yaml`
(`src/labuse/plu/destinations.py` : rubrique `retraits` étendue). **Formes autorisées, et elles
seules :**

- `forme: fixe` + `min_m` — distance absolue en mètres ;
- `forme: relative` + `fraction_hauteur` + `base_hauteur` (`cumulee` = H+h, `plus_haut` = H) + `min_m`
  éventuel — fraction de la hauteur ;
- `forme: conditionnelle` + `avec_ouvertures_m` / `sans_ouvertures_m` (± `fraction_hauteur`) — deux
  valeurs selon que les façades portent ou non des ouvertures ;
- `forme: contiguite` + `contiguite_autorisee: true|false` ;
- `absent: true` → **silence prouvé** (servi « non réglementé »).

Toute autre forme (p. ex. seuil par **nombre de logements** — Le Tampon ; par **classe de hauteur
R+1+C** — Saint-Denis `Up`) = **STOP**, non servie, signalée ici. On ne devine pas.

Verrou inchangé (V6a) : une feuille n'est `validee` qu'avec `statut: valide` **et** citation
(article + page + verbatim). `propose` ou absente du YAML → non servie.

### Zones calibrées (verbatim, statut `valide`) — 13 feuilles, toutes les formes + silence

| Commune | Zone | Forme | Valeur servie | Art. / p. |
|---------|------|-------|---------------|-----------|
| Saint-Denis | Ui *(témoin)* | relative (cumulée) | 0,5·(H+h), min 4 m | Ui.8 / p.55 |
| Saint-Denis | Ua | relative (cumulée) | (H+h)/3, min 2 m | Ua.8 / p.79 |
| Bras-Panon | Ua | fixe | 6 m | UA 8 / p.18 |
| Bras-Panon | Ue | fixe | 8 m | UE 8 / p.70 |
| Bras-Panon | A | **silence** | non réglementé | A8 / p.91 |
| Cilaos | Ua | fixe | 4 m | Ua 8 / p.24 |
| Cilaos | Uc | fixe | 4 m | Uc 8 / p.48 |
| La Plaine-des-Palmistes | Ua | fixe | 3,50 m | Ua 8 / p.17 |
| La Plaine-des-Palmistes | Uc | fixe | 7 m | Uc 8 / p.41 |
| Sainte-Rose | Ua | **conditionnelle** | (H+h)/2, min 6 m (baie) / 3 m (sans) | UA 8 / p.14 |
| Le Port | Ua | fixe | 3 m | Ua 6 / p.25 |
| Les Trois-Bassins | Ua | relative (plus haut) | 0,5·H, min 4 m | Ua 8 / p.16 |
| Les Avirons | AUec | fixe | 3 m | AUEC 8 / p.31 |

Le silence prouvé est servi « non réglementé » (feuille `absent: true`, Bras-Panon `A`). La forme
`contiguite` n'a pas d'occurrence propre dans les règlements lus (les zones admettant la mitoyenneté
le disent au titre des **limites séparatives**, pas de l'inter-bâtiments) ; elle est donc couverte par
les tests unitaires de forme, pas par une feuille.

**Périmètre assumé :** la calibration livrée est **verbatim et vérifiée** (chargée par le vrai lecteur
`regles.charger`, 13/13 `validee`). Elle couvre le témoin, **chacune des 4 formes servables + le
silence**, et plusieurs communes. L'inventaire LOT A ci-dessus donne, zone par zone, le reste du
gisement (même patron de transcription) ; les 4 communes « non lu » et les 2 formes « hors schéma »
(Le Tampon, Saint-Denis `Up`) sont bloquées **à la source**, pas par le moteur.

---

## LOT C — BRANCHEMENT DANS LE MOTEUR

`src/labuse/implantation/` :

- **Mesure** : `controles._distance_min_batiments` prend la plus petite distance **bord à bord** entre
  deux emprises bâties (géométrie monde EPSG:2975).
- **Contrôle 4 états** (`controles.controles_reglementaires`, contrôle « Distance entre constructions ») :
  - un seul bâtiment → **Non applicable** ;
  - règle **fixe/relative chiffrable** → distance requise calculée (hauteur = niveaux × hauteur d'étage ;
    `cumulee` → 2·h, `plus_haut` → h ; plancher `min_m` prioritaire) → **Réussi / Échoué** ;
  - règle **conditionnelle** → le moteur applique la valeur **AVEC ouvertures** (la plus stricte) →
    Réussi si tenue, mention « cas le plus strict retenu (façades avec ouvertures) » ;
  - **silence prouvé** → **Non applicable** + distance de **convention nommée**
    `retrait_inter_barre_m = 6 m` (`config/implantation_conventions.yaml`, étiquetée **Estimé**),
    dite dans la mesure (« convention 6 m (Estimé) ») ;
  - règle **non servie / hors schéma** → **Non effectué**.
- **Statut d'étude** (`controles.statut_etude`) : plusieurs bâtiments ne forcent **plus** « à compléter »
  — l'étude reste exploitable si le contrôle de distance est Réussi ou Non applicable ; elle n'est
  forcée « à compléter » que si le contrôle est **Non effectué** (règle non servie). Un contrôle
  **Échoué** reste bloquant (candidat écarté par le moteur).
- La feuille `entre_constructions` est **exclue** du détecteur de prospect (`regles._detect_prospect`) :
  sa forme relative (L ≥ (H+h)/2 entre deux bâtiments) est désormais **chiffrée** par le contrôle dédié,
  et ne retombe donc plus dans le fourre-tout « hauteur non chiffrable ».
- Le moteur **peut désormais proposer plusieurs bâtiments** et garde la meilleure implantation qui
  passe tous les contrôles (classement inchangé : exploitable d'abord, puis capacité) ; une forme
  `deux_barres` dont la distance est servie et tenue devient **exploitable** au lieu de toujours
  « à compléter ».

### Témoins rejoués — plans + json avant/après (`avant/`, `apres/`)

| Témoin | Zone | Sélection moteur (avant → après) | Distance (contrôle) |
|--------|------|----------------------------------|---------------------|
| L'Étang-Salé | UA | barre R+3, 28 logts, *exploitable* → **inchangé** | 1 bâtiment → **Non applicable** (règle non lue en multi) |
| Saint-André | UC | barre R+2, 24 logts, *à compléter* (PPR bleue) → **inchangé** | 1 bâtiment → **Non applicable** |
| Saint-Denis | Ui | barre R+5, 12 logts, *à compléter* (prospect Ui.7) → **inchangé** | 1 bâtiment → **Non applicable** |

La sélection reste mono-barre : une seule barre offre plus de logements qu'une implantation en deux
barres (à longueur donnée, le jeu inter-barres coûte des logements), donc elle gagne au classement
— comportement correct (« la meilleure implantation qui passe »).

**Démonstration multi-bâtiments (deux_barres forcé, `apres/plan-*-deux-barres.png`)** — pour prouver que
le contrôle mesuré fonctionne sur la géométrie réelle :

| Témoin | deux_barres | Distance mesurée | Règle servie | Verdict |
|--------|-------------|------------------|--------------|---------|
| **Saint-Denis Ui** | R+2, 6 logts, 2 bât. | **9,2 m** | 0,5·(H+h) = 9,0 m, min 4 (Ui.8 p.55) | **Réussi** ✓ |
| L'Étang-Salé UA | R+3, 2 bât. | 10,7 m | non lue | Non effectué (honnête) |
| Saint-André UC | R+2, 2 bât. | 10,2 m | non lue | Non effectué (honnête) |

Saint-Denis en deux barres **tient** la distance inter-bâtiments servie (9,2 ≥ 9,0 m) : le contrôle
passe Réussi, citation à l'appui. L'étude reste « à compléter » — mais pour l'**autre** raison déjà
connue (prospect de limite séparative Ui.7 « L ≥ h/2 », hauteur non chiffrable), plus du tout à cause
de la distance inter-bâtiments. C'est exactement l'effet voulu : **la distance ne bloque plus quand la
règle est servie**.

---

## LOT D — RATIO SHAB / SDP

### Coursive extérieure ouverte → hors SDP

La **surface de plancher** est la somme des surfaces **closes et couvertes** (code de l'urbanisme,
**art. R111-22** : « … somme des surfaces de plancher de chaque niveau **clos et couvert** … »). La
coursive de desserte du moteur est une **circulation extérieure ouverte** (non close) : elle
n'entre donc **pas** dans la SDP. Elle reste mesurée (transparence) et demeure dans l'emprise au sol.

`capacite.calculer` : `SDP = modules + noyaux` (coursive retirée) ; `coursive_m2` exposée à part ;
ratio SHAB/SDP et distribution par niveau recalculés sur la SDP sans coursive. Le contrôle géométrique
« surfaces tableau = surfaces mesurées » a été aligné (coursive hors SDP).

### Noyaux — surface par niveau et par bâtiment

Nouveaux champs `noyau_m2` (total) et `noyaux_par_batiment` (`m2_par_niveau`, `niveaux`, `m2_total`),
et `noyau_m2`/`coursive_m2` par niveau dans `distribution_niveaux`.

**Revue de la convention de noyau :** un noyau mesure **3,5 m × 11,6 m ≈ 40,6 m² par niveau et par
bâtiment** (largeur `largeur_noyau_m = 3,5 m` × profondeur habitable `profondeur_m − coursive =
13 − 1,4 = 11,6 m`). C'est **au-dessus des valeurs usuelles** d'un noyau escalier + ascenseur
(~15–25 m² d'emprise par niveau) : dans le modèle « barre », le noyau occupe **toute la profondeur**
de la barre, alors qu'un noyau réel n'en occupe qu'une partie (le reste étant palier/local ou un
module). La SHAB/SDP monterait encore si le noyau était modélisé moins profond ; cela suppose un
**découpage en profondeur de la bande bâtie** (hors périmètre de ce lot — l'invariant « Σ surfaces =
assiette » et le pavage des modules en dépendent). **Signalé, non modifié** (pas de cible à atteindre).

### Tableau avant / après du ratio (par terrain)

| Terrain | SDP avant | SDP après | Coursive (hors SDP) | SHAB | Noyau/niveau · total | **Ratio avant → après** |
|---------|-----------|-----------|---------------------|------|----------------------|-------------------------|
| L'Étang-Salé UA (R+3, 28 logts) | 2 201,9 | 1 964,8 | 237,1 | 1 312,0 | 81,2 (2 noyaux) · 324,8 | **0,596 → 0,668** |
| Saint-André UC (R+2, 24 logts) | 1 870,0 | 1 668,6 | 201,4 | 1 140,0 | 81,2 (2 noyaux) · 243,6 | **0,610 → 0,683** |
| Saint-Denis Ui (R+5, 12 logts) | 1 046,3 | 933,6 | 112,7 | 552,0 | 40,6 (1 noyau) · 243,6 | **0,528 → 0,591** |

**Lecture :** la sortie de la coursive ouverte est **le** moteur du ratio (+7 à +12 pts). L'Étang-Salé
passe de 0,596 à **0,668**, proche du ~0,70 de l'architecte sans qu'on vise ce chiffre. Le reliquat
d'écart tient au noyau « pleine profondeur » (ci-dessus) : l'expliquer suffit, le mandat ne demande pas
de cible. La SHAB est **inchangée** (seule la SDP, dénominateur, baisse) : aucune donnée de capacité
servie n'est gonflée.

Effet de bord contrôlé : la SDP baissant, un seuil de mixité en m² pourrait basculer. Pour L'Étang-Salé
UA (seuil 1 000 m²), SDP = 1 964,8 m² > 1 000 → mixité toujours applicable : **pas de bascule** sur les
témoins.

---

## Tests

- `tests/test_implantation_distance.py` (**pur, CI**) — 15 tests : les 4 formes (fixe Réussi/Échoué,
  relative cumulée/plus-haut, plancher min prioritaire, conditionnelle « avec ouvertures », contiguïté),
  silence → Non applicable + convention, non servi / hors schéma → Non effectué, et la bascule de statut
  (plusieurs bâtiments non bloquants si la règle est servie ; bloquants si non servie).
- `tests/test_implantation1.py` (**reel**, 3 témoins) — mis à jour : SDP sans coursive
  (`test_surfaces_tableau_egalent_mesures`), nouveaux `test_coursive_hors_sdp`,
  `test_noyau_surface_exposee`, contrôle de distance réécrit (`test_distance_entre_constructions`).
- Résultats : **15 passed** (pur) · **82 passed** (reel, base locale) · **304 passed** sur
  `destinations/plu/calibrage/regles/revue`. ⚠ 2 échecs `tests/test_simulplu.py` **PRÉ-EXISTANTS**
  (documentés par BILAN-2, sans lien avec ce lot — `test_simulplu.py` ne touche ni l'implantation ni le
  schéma `retraits`).

## SONDAGE-10

`SONDAGE-10.md` : 10 règles de distance tirées du corpus (valeur + citation verbatim + page),
couvrant fixe / relative / conditionnelle / silence / forme hors schéma.

## Livrable

`docs/audit-2026-10/plu-calibrage-10/` : ce `RAPPORT.md`, `SONDAGE-10.md`, `avant/` et `apres/`
(scenario-*.json + plan-*.png des 3 témoins ; `apres/*-deux-barres.*` = démonstration multi-bâtiments).

Commits par lot, **aucun merge**.
