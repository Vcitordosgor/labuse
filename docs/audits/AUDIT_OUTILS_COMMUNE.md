# AUDIT — Les 6 outils « échelle commune », avant fusion

Audit PUR (aucune correction). Six outils : **Rareté du foncier**, **Vélocité admin**,
**Baromètre foncier**, **Marché**, **Comparateur de communes**, **Suivi de secteur** (Carnet).
Run servi de référence : `q_v10_m129` (`config/served_run.txt:1`, constante `Q_A_RUN_LABEL`).

Mesures DB exécutées le jour de l'audit sur la base réelle.

---

## 0. Verdict express (les 5 questions)

| Outil | 1. Branché / sert | 2. Scopé q_v10_m129 ? | 3. Vestiges matrice | 4. Couverture /24 | 5. Test « ne lève pas » |
|---|---|---|---|---|---|
| **Rareté** (`rarete.py`) | ✅ sert (ENAF + stock v2) | 🟡 stock oui, budget ZAN non | **Aucun** | **24/24** | ❌ (garde table-absente seule) |
| **Vélocité** (`modules.py:463`) | ✅ sert (délais permis) | ❌ non (SITADEL/SDES) | **Aucun** | **24/24** | ❌ |
| **Baromètre** (`moteurs.py:422`) | ✅ sert (DVF/Sitadel) | ❌ non (DVF public) | **Aucun** | **île** + top-8 communes | ❌ |
| **Marché** (`marche_commune.py`) | ✅ sert (9 lignes) | 🟡 ligne 7 oui, reste non | **Aucun** | **24/24** | ✅ happy-path (pas de garde anti-lève) |
| **Comparateur** (`comparateur.py`) | ✅ sert (6 axes + composite) | 🟡 stock oui, reste non | **Aucun** | **24/24** | 🟡 1 test DB (shape, pas anti-lève) |
| **Carnet** (`carnet.py`) | ✅ sert (stock + prix + signaux) | 🟡 stock oui, reste non | **Aucun** | secteur (all communes) | 🟡 2 tests DB (happy-path) |

**Constats transverses :**
- **Vestiges matrice : ZÉRO sur les 6.** Grep `q_score|a_score|matrice_statut|a_completude|completeness|opportunity_score` sur `rarete.py`, `modules.py:463-540`, `moteurs.py:340-420`, `marche_commune.py`, `comparateur.py`, `carnet.py` → aucune occurrence. Contrairement aux lots précédents (scoreur/duediligence/simulplu), **ce lot est propre**.
- **Couverture : 24/24 sur toutes les sources.** Mesuré : `commune_conso_enaf` 24 · `m10_permit_delais` (valide) 24 · `dvf_mutations` 24 · `sitadel_permits` 24. Aucun outil n'est troué par manque de données commune.
- **Scope run : partiel et cohérent.** Seul le **stock d'opportunités** (parcelles brûlante/chaude) est scopé sur `q_v10_m129` — les indicateurs de marché/admin/ZAN sont volontairement **run-independent** (DVF, SITADEL, ENAF, DHUP : données publiques, pas du scoring).
- **Tests : le trou.** **Aucun** des 6 n'a de test qui prouve « l'endpoint ne lève pas » (au sens M136/M137). Les tests existants vérifient des helpers (normalisation, horizon) ou un happy-path de forme ; `test_rarete.py` ne garde que le cas « table absente ». Si une requête casse (colonne renommée, jointure), rien ne l'attrape.

---

## 1. Détail par outil (fichier:ligne)

### 1.1 Rareté du foncier — `src/labuse/api/rarete.py`
- **Branché.** `_SQL` (`rarete.py:34-46`) lit **`commune_conso_enaf`** (`:39-45`, source principale) + **`parcels`/`parcel_p_score_v2`** (`:36-38`, CTE `stock`). Endpoint `/pipeline-rarete` (`:91-94`). Sert de vraies données ; garde table-absente → `[]` (`:66-67`).
- **Run.** Stock scopé `WHERE v.run_id = :run AND v.tier IN ('brulante','chaude')` (`:38`, `:69` passe `Q_A_RUN_LABEL`). Le budget ZAN vient d'`ENAF` (2011-2021 / 2021-2024, **non run-dépendant**, `:40-42`).
- **Vestiges.** Aucun.
- **Couverture.** 24/24 (`commune_conso_enaf` = 24, LEFT JOIN → jamais de commune omise, `:45`).
- **Test.** `tests/test_rarete.py` : `test_horizon_normal` (helper), `test_compute_vide_si_table_absente`. **Aucun test ne vérifie la forme du payload ni « ne lève pas ».**
- **Indicateurs servis (6)** `rarete.py:73-85` : `rythme_conso_ha_an`, `budget_zan_ha`, `reste_zan_ha`, `horizon_epuisement_ans`, `statut` (5 paliers), `stock_opportunites_ha`.

### 1.2 Vélocité admin — `src/labuse/api/modules.py:463-535`
- **Branché.** Lit **`m10_permit_delais`** (`:482`, `:495`, `:503`). Endpoint `/modules/velocite` (`:463`). Sert par-commune médiane/quartiles + tendance.
- **Run.** **Non scopé** — SITADEL/SDES-Dido, indépendant du scoring. Millésime servi = plage d'années d'autorisation (`:515-518`).
- **Vestiges.** Aucun.
- **Couverture.** 24/24 (`m10_permit_delais` valide = 24 communes ; `HAVING count(*) FILTER (WHERE valide) > 0` `:484` ne retire que les communes à 0 permis — aucune ici).
- **Test.** Pas de test direct de l'endpoint ; `test_comparateur.py` teste la normalisation « bas = mieux ». **Aucune garde anti-lève.**
- **Indicateurs (6+)** `modules.py:487-535` : `delai_median_mois`, `delai_p25_mois`, `delai_p75_mois`, `rang_delai`, `tendance` (accelere/ralentit/stable), `n_valide`/`n_mur`/`n_recent_exclu`.

### 1.3 Baromètre foncier — `src/labuse/api/moteurs.py:341-423`
- **Branché.** `_barometre_data` lit **`dvf_mutations`** (`:387` trimestres, `:394-400` top communes, `:407` écartées) + **`sitadel_permits`** (`:392`). Endpoint `/moteurs/barometre` (`:422`) + PDF (`:435`).
- **Run.** **Non scopé** — DVF public. Millésime = 8 derniers trimestres (`:381`, `:388`).
- **Vestiges.** Aucun.
- **Couverture.** Séries `dvf_trimestres`/`permis` = **île entière** (pas de GROUP BY commune). Seul `top_communes_prix` est par commune, avec **`HAVING count(*) >= 100` puis `LIMIT 8`** (`:399-400`). → voir §2.3.
- **Test.** `test_copilote_guidage.py:23` mappe le concept, ne teste pas l'endpoint. **Aucune garde anti-lève.**
- **Indicateurs (4)** `moteurs.py:413-418` : `dvf_trimestres[]` (médiane €/m² bâti + écartées), `permis_trimestres[]`, `top_communes_prix[]` (≤8), `ecartees{}` (VEFA/symboliques/hors-bande).

### 1.4 Marché (par commune) — `src/labuse/faisabilite/marche_commune.py`
- **Branché.** `build_marche_commune` (`:329`), appelé par `moteurs.py:427`. Lit **8 tables** : `dvf_mutations` (via `sector_price`, `:63`), `dvf_mutations_parcelle`+`parcel_zone_plu` (`:96-114`), `dvf_prix_sortie_neuf` (`:135-148`), `dvf_mutations` tendance/liquidité (`:158-211`), `sitadel_permits` (`:218-233`), `parcel_residuel`+`parcel_p_score_v2` (`:239-255`), `dpe_records` (`:261-276`), module loyers (`:279-292`).
- **Run.** **Ligne 7 (gisement) scopée** `s.run_id = :run` (`:243`) ; **lignes 1-6 et 9 run-independent** (marché historique).
- **Vestiges.** Aucun.
- **Couverture.** 24/24 — jamais de commune omise ; une donnée insuffisante rend une ligne `calculable=False` + `motif` (`:120-124`, `:173-179`), jamais masquée.
- **Test.** `tests/test_marche_commune.py` (5 tests DB) : `len(lignes)==9` (`:31`), tendance non calculable si n<seuil (`:49`), gisement run-servi (`:58`), market_signal jamais nu (`:69`), cellule < seuil non calculable (`:83`). Happy-path — **pas de garde « ne lève pas ».**
- **Indicateurs (9 lignes)** `marche_commune.py:329-342` : `prix_ancien_median`, `prix_terrain_nu_par_zone`, `prix_sortie_neuf`, `tendance_12m`, `liquidite`, `offre_engagee` (permis), `gisement_constructible` (SDP résiduelle), `pression_dpe`, `loyer_median` + `market_signal` composite.

### 1.5 Comparateur de communes — `src/labuse/api/comparateur.py`
- **Branché.** Requête unifiée (`:40-66`) : `parcels` (base `:41`), `parcel_p_score_v2` (stock `:42-45`), `m10_permit_delais` (vélocité `:46-48`), `sitadel_permits` (permis `:49-51`), `commune_contexte_sru` (`:52`), `commune_conso_enaf` (pression ZAN `:53`), `dvf_prix_sortie_neuf` (`:54`). Endpoint `/comparateur-communes` (`:133`).
- **Run.** **Stock scopé** `s.run_id = :run` (`:43-45`) ; 5 autres axes run-independent.
- **Vestiges.** Aucun.
- **Couverture.** 24/24 — base = `SELECT DISTINCT ... FROM parcels` (`:41`), LEFT JOIN → axe manquant = `null`, jamais dropé. Renormalisation du composite sur les axes présents (`:75-105`).
- **Test.** `tests/test_comparateur.py` : 6 tests de `_normalize` (directions, axe manquant, borne dégénérée) + `test_compute_24_communes_et_composite` (DB, shape). **Pas de garde anti-lève explicite.**
- **Indicateurs (6 + composite)** `comparateur.py:108-129` : `stock`, `velocite`, `permis`, `deficit_sru`, `pression_zan`, `prix_neuf`, `score_composite` (moyenne pondérée renormalisée).

### 1.6 Suivi de secteur (Carnet) — `src/labuse/api/carnet.py`
- **Branché.** `liste_secteurs` (`:58`) + `_carnet` (`:86`). Lit `parcel_p_score_v2` (stock `:67-75`, `:96-98`), + (gardés par `_has`) `dvf_secteur_medianes` (`:102-105`), `dvf_prix_sortie_neuf` (`:107-110`), `parcel_signals` (`:114-117`), `sitadel_permits` (`:121-126`), `commune_conso_enaf` (`:129-132`).
- **Run.** **Stock scopé** `s.run_id = :run` (`:97`) ; reste run-independent.
- **Vestiges.** Aucun.
- **Échelle = SECTEUR** (`left(idu,10)`), pas commune. `liste_secteurs` filtre `HAVING count(*) FILTER (WHERE tier IN ('brulante','chaude')) > 0` (`:73`) → ne liste que les secteurs à ≥1 opportunité (couvre toutes les communes ayant des opportunités).
- **Test.** `tests/test_carnet.py` : longueur secteur 422 (`:17`), labels, + 2 tests DB (stock, tri). Happy-path.
- **Indicateurs (6-8 blocs)** `carnet.py:134-143` : `stock`/`par_tier`, `prix.dvf` (par type_bien), `prix.sortie_neuf`, `signaux`, `permis_24_mois`, `zan`.

---

## 2. Les trois points de Vic — chiffrés

### 2.1 Rareté — quelle mesure exactement ? Dit-elle ce qu'elle prétend ?

**La mesure (formule, `rarete.py:34-62`) :**
- `rythme_conso_ha_an = conso_2021_2024_m2 / 3 / 10000` (`:40`) — ha/an **artificialisés** (ENAF Cerema).
- `budget_zan_ha = conso_2011_2021_m2 × 0,5` (`:41`) — budget ZAN = **50 % de la conso 2011-2021** (interprétation loi TRACE, CAVEAT `:31-32`).
- `reste_zan_ha = budget − conso_2021_2024` (`:42`) — **enveloppe ZAN restante**.
- `horizon_epuisement_ans = reste / rythme` (`:54-62`) — années avant épuisement de l'enveloppe.
- `stock_opportunites_ha` = Σ surface des parcelles brûlante/chaude (`:36-38`, scopé run).

**Verdict — le calcul dit une chose, le libellé en promet une autre.**
Le libellé registry (`registry.ts:97`) dit *« combien de **constructible** reste-t-il… horizon ZAN »*. Or `reste_zan_ha` **n'est pas du foncier constructible** : c'est un **budget réglementaire d'artificialisation** (estimé −50 %). Une commune peut être « budget dépassé » (`reste ≤ 0`, statut `:79`) **tout en ayant des parcelles constructibles** (son `stock_opportunites_ha` > 0). Les deux grandeurs sont servies côte à côte mais mesurent des choses différentes :
- `reste_zan_ha` / `horizon` = **droit à artificialiser** qui reste (Estimé, ENAF).
- `stock_opportunites_ha` = **le vrai proxy « constructible qui reste »** (parcelles promues, ha).

Le CAVEAT interne est honnête (`:31-32` : « épuisement de l'enveloppe ENAF ≠ interdiction de bâtir »), mais **le libellé de l'outil sur-promet** (« constructible » pour un budget ZAN). À la fusion : dire « **horizon d'enveloppe ZAN** » et distinguer clairement du **stock de parcelles**.

### 2.2 Vélocité — source, plausibilité, et la distribution (tranche vs médiane)

**Source du délai** (`ingestion/permit_delais_m10.py:80-84`) :
`delai_mois = (aut.année − dép.année)×12 + (aut.mois − dép.mois)` — **différence de MOIS** entre `date_depot` et `date_autorisation` (SITADEL/SDES-Dido). Granularité **au mois** (« le dépôt n'est daté qu'au mois — jours non fiables », `:78`). ~15 % des lignes ont dépôt > autorisation (saisie) → **exclues** (`valide=false`).

**Distribution mesurée** (`m10_permit_delais` valide, n = 42 603) :

| min | p25 | médiane | p75 | p90 | max | moyenne |
|---|---|---|---|---|---|---|
| 0 | **6** | **9** | **12** | 14 | 114 | 8,9 |

Aberrants : 0 négatif (exclus en amont), 562 à **0 mois** (dépôt+autorisation même mois), 31 > 36 mois. **Pas de bug de signe/unité** — l'unité est bien le mois.

**Plausibilité :** médiane 9 mois pour dépôt→autorisation = **plausible** (instruction + pièces manquantes + prorogations + accord tacite). Le « douteux » vient de la **granularité au mois** (un délai réel de 5 jours à cheval sur 2 mois compte 1 mois ; un même-mois = 0) et des 562 zéros — pas d'une erreur grossière.

**Tranche vs médiane — OUI, plus honnête.** Par commune, l'**IQR est de ~6 mois partout** et les médianes se tiennent toutes entre **8 et 9** :

| commune (échantillon) | p25 | médiane | p75 |
|---|---|---|---|
| Saint-Pierre, Sainte-Suzanne, Petite-Île, Le Port… | 5-6 | **8** | 11-12 |
| Saint-Paul, Saint-Louis, Saint-Joseph | 6 | **9** | 12 |

Deux enseignements : (a) **les communes ne se distinguent quasiment pas sur la médiane** (8 vs 9) → un classement par médiane est du bruit ; (b) **chaque commune a une dispersion large** (moitié des permis entre ~6 et ~12 mois). Servir **« 6 à 12 mois »** (l'intervalle p25-p75, que l'outil **calcule déjà** — `modules.py:479-481` `delai_p25_mois`/`delai_p75_mois` — mais affiche en second) serait **plus honnête que la médiane 9**. La donnée pour la tranche existe ; c'est un choix de restitution.

### 2.3 Baromètre — pourquoi « 9 communes » ? Ni trou, ni robustesse : un `LIMIT`.

Mesuré : **les 24 communes ont ≥ 100 ventes strictes** (min **Salazie 106**, Cilaos 125, Sainte-Rose 122, Trois-Bassins 136). Donc le `HAVING count(*) >= 100` (`moteurs.py:399`) **ne retire aucune commune**.

La limitation est un **plafond d'affichage** : `top_communes` = `ORDER BY median_eur_m2 DESC LIMIT 8` (`moteurs.py:400`) → **top-8 par prix**, pas 9, et **pas un seuil de robustesse ni un trou de donnée**. Les autres séries (`dvf_trimestres`, `permis_trimestres`) sont **île entière**, pas par commune (`:387`, `:392`).

**Réponse chiffrée :** la donnée couvre **24/24** ; le baromètre par-commune est **arbitrairement tronqué à 8** (les 8 communes les plus chères). Rien n'empêche de servir les 24.

---

## 3. Structure pour la fusion — indicateurs × échelle, recouvrements

### 3.1 Les 6 ne sont PAS à la même échelle

| Échelle | Outils |
|---|---|
| **Commune** (choix commune → indicateurs) | Rareté · Vélocité · **Marché** · Comparateur |
| **Île** (vue d'ensemble, pas par commune) | **Baromètre** (+ un top-8 communes) |
| **Secteur** (`left(idu,10)`, plus fin que commune) | **Carnet** |

→ 4 outils sont commune-scale et fusionnent naturellement « par commune ». **Baromètre (île) et Carnet (secteur) ne sont pas sur le même axe** : le premier est une vue marché globale, le second un drill-down infra-commune.

### 3.2 Total ≈ 16 indicateurs distincts, tirés de ~11 tables partagées

Concepts distincts servis (dédupliqués), et **combien d'outils les recomputent** :

| # | Indicateur | Table source | Outils qui le servent |
|---|---|---|---|
| 1 | **Stock opportunités** (brûlante/chaude, ha/nb) | `parcel_p_score_v2` (run) | **Rareté · Comparateur · Carnet** (×3) |
| 2 | **Vélocité** (délai permis) | `m10_permit_delais` | **Vélocité · Comparateur** (×2) |
| 3 | **Permis Sitadel** (volume) | `sitadel_permits` | **Marché · Baromètre · Comparateur · Carnet** (×4) |
| 4 | **Prix ancien DVF** (médiane €/m²) | `dvf_mutations` / `dvf_secteur_medianes` | **Marché · Baromètre · Carnet** (×3) |
| 5 | **Prix sortie neuf** | `dvf_prix_sortie_neuf` | **Marché · Comparateur · Carnet** (×3) |
| 6 | **Conso/budget/horizon ZAN** | `commune_conso_enaf` | **Rareté · Comparateur · Carnet** (×3) |
| 7 | Prix terrain nu par zone | `dvf_mutations_parcelle` | Marché |
| 8 | Tendance 12 m | `dvf_mutations` | Marché |
| 9 | Liquidité (mutations/trim) | `dvf_mutations` | Marché |
| 10 | Gisement constructible (SDP résiduelle) | `parcel_residuel` | Marché |
| 11 | Pression DPE | `dpe_records` | Marché |
| 12 | Loyer médian | module loyers | Marché |
| 13 | Déficit SRU | `commune_contexte_sru` | Comparateur |
| 14 | Signaux (piscine…) | `parcel_signals` | Carnet |
| 15 | Composite (dérivé) | — | Comparateur |
| 16 | Écartées/qualité DVF | `dvf_mutations` | Baromètre |

**Recouvrement fort : 6 indicateurs sur 16 sont recalculés dans 2 à 4 outils** (stock ×3, vélocité ×2, permis ×4, prix ancien ×3, prix neuf ×3, ZAN ×3).

### 3.3 Le recouvrement structurant : le Comparateur EST déjà la vue « par commune » agrégée

**5 des 6 axes du Comparateur** (`stock`, `velocite`, `permis`, `pression_zan`, `prix_neuf`) sont exactement des indicateurs déjà produits par **Rareté / Vélocité / Marché**, mais **tabulés sur les 24 communes** au lieu d'une seule. Autrement dit :
- **« par outil »** ≈ ce qu'est déjà le **Comparateur** (toutes les communes, 6 indicateurs clés, classées).
- **« par commune »** ≈ le **drill-down** (Marché 9 lignes + Rareté ZAN + Vélocité délais sur UNE commune).

Ce ne sont pas deux organisations concurrentes mais **deux profondeurs de la même donnée** : une table (toutes communes, peu d'indicateurs) et une fiche (une commune, tous les indicateurs).

### 3.4 Ce que chaque organisation coûte (pour trancher)

- **« par commune »** (choix commune → tous ses indicateurs) : unifie naturellement Rareté+Vélocité+Marché en une fiche commune. **Baromètre (île) n'y entre pas** (c'est la vue « toute l'île » par défaut) ; **Carnet (secteur) devient un cran de zoom sous la commune**. Le Comparateur reste l'**écran d'entrée** (table classée → on clique une commune → sa fiche).
- **« par outil »** (choix outil → commune) : garde 6 entrées de menu pour ~16 indicateurs dont 6 dupliqués ; l'utilisateur qui veut « tout sur Saint-Paul » ouvre 4 outils. Le Comparateur y fait doublon avec les 3 autres commune-scale.

**Fait à retenir pour la décision (pas une reco imposée) :** une fusion « par commune » avec le Comparateur en table d'entrée **absorbe 4 des 6 outils sans perte** (Rareté, Vélocité, Marché, Comparateur), **dédoublonne les 6 indicateurs recalculés**, et laisse **Baromètre** (échelle île) et **Carnet** (échelle secteur) comme deux objets d'échelle différente à traiter à part (vue d'ensemble / zoom secteur).

---

## Annexe — commandes de mesure
- Couverture 24/24 : `count(DISTINCT commune)` sur `commune_conso_enaf`, `m10_permit_delais(valide)`, `dvf_mutations`, `sitadel_permits` → **24** chacun.
- Baromètre : `HAVING count>=100` par commune sur ventes strictes (`_BAROMETRE_RETENUE`) → **24 communes ≥ 100** (min Salazie 106) ; le « 8/9 » = `LIMIT 8`.
- Vélocité : percentiles de `delai_mois` (valide) → p25 6 / médiane 9 / p75 12 ; IQR ~6 mois par commune, médianes 8-9.
- Vestiges : grep `q_score|a_score|matrice_statut|a_completude|completeness|opportunity_score` sur les 6 fichiers → **0**.
