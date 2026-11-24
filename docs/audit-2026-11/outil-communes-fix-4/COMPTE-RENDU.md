# OUTIL-COMMUNES-FIX-4 — réponse au recontrôle externe (`03-COMMUNES-ASTRA-3.md`)

Périmètre = la liste fermée « C'est faux » du recontrôle (6 points), rien d'autre. Branche
`fix/outil-communes-1`, `origin/main` déjà fusionné (à jour). Base locale `labuse` (dev, openclaw) —
jamais écrite : les recalculs de cache sont des gestes de déploiement, mesurés ici en LECTURE SEULE.

Tout chiffre ci-dessous sort d'un script committé (`scripts/communes_fix4_*.py`) ou de pytest ; la
sortie brute est dans `docs/audit-2026-11/outil-communes-fix-4/LOT*.txt`.

---

## LOT 0 — le filet (commit séparé `729966ed8`)

`tests/test_communes_cas_externes.py` : un test par témoin du rapport, valeur précise. AVANT correction
(base `labuse`, `LOT0-pytest-rouge.txt` / `LOT0-detail-terrain-catnat.txt`) : **11 failed**. Extraits bruts :

```
2023-1315722 : assert {'terr_tot': 80.0, 'val': 20000.0} is None          → local présent à tort
comparables IZ0236 : [{surface 80, prix_m2 250, distance_m 0}]            → l'acte du sujet reparaît
2022-1639451 : assert {'terr_tot': 950.0, 'val': 60000.0} is None         → multi-communes présent
2021-1676912 : assert 1195 == 1895                                         → plus grande ligne, pas la somme
catnat Saint-Denis : RuntimeError (le bloc entier tombe)                   → faux zéro
_FALLBACK risques catnat_arretes : assert 0 is None
Sainte-Marie / Sainte-Suzanne : 'revision_plu' == 'cloturee'
```

APRÈS les LOTS 1-4 (`LOT0-vert.txt`) : **11 passed**.

---

## LOT 1 — terrain nu : une seule fonction, tous les lecteurs l'appellent

La qualification unique `ACTE_TERRAIN_NU_CTE` (`marche_dvf_commune.py`) applique désormais, sur l'ACTE
ENTIER (toutes lignes DVF, toutes communes) :

- **(a) local déclaré même sans surface → exclu** : `bool_or(type_local IS NOT NULL) = false`. L'ancien
  `sum(bati)=0` laissait passer un « Local industriel… » à surface bâtie NULL (témoin 2023-1315722).
- **(b) acte multi-communes → écarté partout** : `count(DISTINCT code_commune) = 1` (témoin 2022-1639451,
  Petite-Île + Saint-Joseph).
- **(c) surface = somme des subdivisions DISTINCTES** `(nature_culture, surface_terrain)`, jamais la plus
  grande ligne. Témoin 2021-1676912 / ET0142 = 1 195 (« sols ») + 700 (« terres ») = **1 895 m²**
  (contenance cadastrale confirmée) → **280 €/m²** au lieu de 1 195 m² / 444 €/m².
- **(d) l'acte du sujet jamais dans ses propres comparables** (`comparateur_terrain`, fiche parcelle +
  Estimer) : on exclut TOUTE mutation ayant touché la parcelle sujet, pas seulement sa ligne (le témoin
  revenait par la 2ᵉ parcelle de la mutation).

Les lecteurs que le rapport montrait HORS de cette fonction y passent désormais, et les **deux copies
inline** restantes de la règle ont été supprimées :

| Lecteur | Fichier | Statut |
|---|---|---|
| tableau / fiche commune / Comparer / Assemblage | `faisabilite/marche_commune.py::ligne2_terrain_zone` | embarque le CTE |
| repère commune (Radar, PDF) | `marche_dvf_commune.py::_median_terrain` | embarque le CTE |
| **fiche parcelle §Marché, Estimer** | `marche_service.py::comparateur_terrain` | CTE + exclusion acte sujet (d) |
| **Comparatif / fiche §8 (prix de section)** | `ingestion/dvf_marche.py::compute_medianes_secteur` | terrain recalculé via le CTE (2ᵉ INSERT) |
| **Étude de zone** | `zone.py::prix_par_type_zone` | embarque le CTE |
| **Radar île** | `pige/signaux.py` | embarque le CTE |
| série baromètre | `api/moteurs.py` | embarque le CTE |
| bloc « Marché de la commune » | `faisabilite/marche_commune.py::_median_terrain_commune` | **copie inline → CTE** |
| banc d'estimation | `pige/banc_estimer.py` | **copie inline → CTE** (ne dédouble plus un acte multi-communes par commune) |

### Preuve unique (`scripts/communes_fix4_terrain_preuve.py`, `LOT1-terrain-preuve.txt`)

```
actes terrain nu qualifiés : 10626
  dont avec un local déclaré   : 0   (attendu 0)
  dont multi-communes          : 0   (attendu 0)
```

Comme TOUS les lecteurs embarquent ce CTE, le « 0 » vaut dans chacun.

### Avant / après — médianes U et AU des 24 communes (effectifs)

Voir `LOT1-terrain-preuve.txt` (tableau complet). Lecture : les médianes U/AU bougent de **0 à 2 €/m²**
avec une baisse d'effectif de quelques actes (ceux retirés : local déclaré, multi-communes). Exemples :
Le Tampon U 209·623 → 208·619 ; Saint-Denis U 298·568 → 298·559 ; Les Trois-Bassins AU 161·81 → 169·80.
(Les valeurs absolues diffèrent du rapport externe : la base locale porte le millésime DVF jusqu'à 2026,
le rapport a contrôlé une base 2021-2025 ; c'est le DELTA de la règle qui est prouvé ici, sur la même base.)

### Chiffres de documents validés qui bougent — repère de secteur du Bilan

Le cache `dvf_secteur_medianes` (type_bien='terrain') est lu par la fiche §8 / le Comparatif ET par le
**Bilan mode B** (`faisabilite/bilan.py::_prix_terrain_local`). Son builder est corrigé (terrain via le
CTE) ; le recalcul du cache est un geste de DÉPLOIEMENT (comme toute ingestion DVF). Impact mesuré en
lecture seule (`scripts/communes_fix4_secteur_impact.py`, `LOT1-secteur-impact.txt`) :

```
secteurs en cache (ancien builder) : 791
secteurs dont (médiane ou n) bouge  : 110
→ dont PRIX servi au Bilan mode B (n≥3) qui bouge : 60
```

**Donc 60 secteurs verront leur repère terrain du Bilan bouger au prochain recalcul du cache** (liste des
25 plus gros écarts dans `LOT1-secteur-impact.txt`). Chaque écart retire un acte avec local déclaré ou
multi-communes (ex. secteur 97407000AT 346·3 → 228·2, 97418000AC 325·14 → 311·10). Le repère de secteur
avait été jugé « sain » en FIX-3 (bâti=0 global) ; FIX-4 y applique aussi les règles (a) et (b).

---

## LOT 2 — procédures PLU (`config/veille_plu.yaml`, `veille_plu.py`, `fiche_commune.py`)

- **Sainte-Marie (97418)** : PLU révisé APPROUVÉ le 26/11/2025, exécutoire le 14/01/2026 → `procedure:
  cloturee`, `stade: approuvée`, statut servi « à jour ». `état au 2026-01-14`.
- **Sainte-Suzanne (97420)** : pièce officielle du PLU portant la prescription (28/02/2018) ET
  l'approbation (29/09/2025) → `cloturee / approuvée`, « à jour ». `état au 2025-09-29`.
- **24 communes** : chaque état porte la DATE DE SA SOURCE (`etat_au`, servi + affiché « État au … »).
  Valeur = pièce la plus récente trouvée : approbation (SM/SS), opposable GPU (Étang-Salé 2025-09-17,
  La Plaine-des-Palmistes 2023-05-27, Saint-Denis 2026-04-23, Saint-Louis 2025-12-18, Saint-Paul
  2025-12-17), sinon squelette Sudocuh `2024-12-31` (nouveau `meta.source_squelette_date`). Aucun état
  ancien n'est présenté comme actuel : Saint-Denis reste « en révision » mais daté « état au 2026-04-23 ».

---

## LOT 3 — faux zéros (`api/fiche_commune.py`, `ContextePanel.tsx`)

**Cause trouvée** du zéro CatNat à Saint-Denis / Saint-Paul / La Plaine-des-Palmistes : le calcul
d'exposition (part de parcelles en PPR / mouvement de terrain) est un scan spatial `ST_Intersects`
lourd — **34 s pour le seul PPR de Saint-Denis** (mesuré, `\timing`), joué DEUX fois (PPR + mvt). Sur les
trois communes les plus lourdes il dépasse le `statement_timeout` de l'API (60 s) → tout le bloc
`risques` lève → repli `_FALLBACK` → `catnat_arretes = 0`. Les petites communes (Cilaos, Saint-Philippe)
passaient : d'où 0 à Saint-Denis mais 11/18 ailleurs.

**Réparé** : le nombre d'arrêtés CatNat (fait indexé sur l'insee) est calculé D'ABORD et INDÉPENDAMMENT ;
l'exposition PPR/mvt/Parc est ISOLÉE dans un bloc protégé — un timeout y donne `None` (indisponible) et
un rollback propre, jamais un faux 0. Preuve (`test_catnat_jamais_faux_zero_quand_exposition_echoue`,
exposition forcée en échec) : Saint-Denis **14**, Saint-Paul **17**, La Plaine-des-Palmistes **9**
arrêtés servis quand même ; ppr_pct = None (indisponible).

**Autres replis à 0 / vide corrigés** (se confondaient avec une vraie valeur) :
- `risques` : `catnat_arretes` 0 → **None**, `catnat_perils` → None, `parc_national` False → **None**.
- `permis` : `permis_12m` 0 → **None**, `point_mort` 0 → **None** (un « 0 permis » de repli ≠ une commune
  réellement sans permis).

Front : les lignes affichent **« indisponible »** sur `None` (PPR, mouvement de terrain, arrêtés CatNat,
Parc National), jamais « 0 » ni « — » qui se lisent comme une absence réelle. Types TS mis à jour
(`catnat_arretes: number | null`, etc.). `_FALLBACK["risques"].catnat_arretes is None` : testé.

---

## LOT 4 — baromètre : Cilaos répond (`api/moteurs.py`)

**Cause trouvée** du HTTP 500 : la requête de la série terrain joignait `acte_nu` à un `scope` filtré par
commune ; pour une commune le planner estimait `scope` à 1 ligne et choisissait une **boucle imbriquée
re-scannant `dvf_mutations_parcelle` 27 321 fois (54 M buffers)** → Cilaos **~200 s** → 500 sous le
statement_timeout. L'île (pas de filtre commune) passait en hash join (0,5 s). EXPLAIN brut :
`Execution Time: 192342 ms`.

**Réparé** : `scope AS MATERIALIZED` force l'évaluation unique (≈179 lignes) puis une jointure propre.
Mesuré : **192 000 ms → 177 ms** (EXPLAIN) ; **24/24 communes répondent, pire temps 0,42 s** ; Cilaos
sous `statement_timeout = 25 s` : test vert. Les chiffres du trimestre = base (permis Cilaos 2026T3 = 3,
comptage Sitadel direct identique).

---

## LOT 5 — dates (`ContextePanel.tsx`, `api/fiche_commune.py`, `taxe_amenagement.py`)

- **Carte ZAN** : une seule date de départ. Le libellé disait « base fin 2024 » quand l'hypothèse ET le
  calcul (`2024 + ans`) partent du 1ᵉʳ janvier 2024 (reste ZAN mesuré au terme de la série Cerema
  2021-2024). Libellé aligné sur « base 1ᵉʳ janvier 2024 » — sans toucher au chiffre servi.
- **Prix acté** : la période affiche désormais les DATES RÉELLES (« du JJ/MM/AAAA au JJ/MM/AAAA ») de la
  population exacte derrière la médiane (même filtre `_BAROMETRE_RETENUE` que `prix_ancien_communes`), à
  côté de la maille « DVF commune entière ». Plus de maille sans aucune date.
- **Taxe d'aménagement** : « Taux communal **au** JJ/MM/AAAA (délibération — référence datée, maintien non
  vérifié) » au lieu de « en vigueur **depuis** » (qui laissait entendre un maintien non établi).

---

## Vérifications finales

- `tests/test_communes_cas_externes.py` : **11 passed** (base `labuse`).
- Front `tsc -b` : OK. `vitest` : OK.
- Python unitaires (sans base) : OK. Cohérence (12 témoins, base locale) : OK.
- Aucune fusion dans `main`. Pousser sans `--no-verify`. API jamais lancée en service.
