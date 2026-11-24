# OUTIL-COMMUNES-FIX-1 — Compte rendu

Worktree `~/Desktop/labuse-communes-fix`, branche `fix/outil-communes-1` (depuis `origin/main`).
Base locale PostGIS `labuse` (lecture seule, peer auth `openclaw`), `dvf_mutations_parcelle` = 102 551 lignes.
Aucune prod, aucun merge main. Lecture seule tant que LOT 0 n'est pas arbitré.

> **Note de périmètre.** Le contre-audit `~/Desktop/audit-outils/03-COMMUNES-ASTRA.md` **n'existe pas**
> au démarrage (seuls `01-PLU-ASTRA.md` et `02-PERMIS-ASTRA.md` sont présents ; `03-COMMUNES.md`
> l'audit de l'outil, oui). La « liste fermée » censée être mon périmètre n'est donc pas disponible
> telle quelle : je travaille sur la paraphrase des LOTs 0→5 du mandat (qui encode cette liste). **À
> fournir avant les LOTs 1→5** pour verrouiller le périmètre exact. LOT 0 ci-dessous est lecture seule
> et pleinement spécifié par le mandat, je l'ai donc produit.

---

## LOT 0 — Où sert le prix du terrain nu (lecture seule, à arbitrer avant toute correction)

### 0.1 Le défaut, précisément

Toutes les médianes « terrain nu » **vivantes** partagent la MÊME erreur de requête. Elles lisent
`dvf_mutations_parcelle` (grain : une ligne par parcelle × nature de culture) avec un filtre bâti
appliqué **ligne par ligne** :

```sql
WHERE ... AND COALESCE(surface_reelle_bati, 0) = 0 AND surface_terrain > 0
...
tot AS (SELECT id_mutation, sum(terr_parc) AS terr_tot, max(valeur_fonciere) AS val ...)
-- €/m² = val / terr_tot
```

Deux conséquences, les deux relevées par le relecteur :

1. **Un acte mixte (bâti + nu) est compté comme une vente de terrain nu.** Le filtre
   `surface_reelle_bati = 0` écarte les *parcelles* bâties de l'acte, mais **garde l'acte** dès qu'il
   reste une parcelle nue. Un acte « maison sur parcelle A + jardin nu parcelle B » survit comme
   « terrain nu ».
2. **Le prix de l'acte ENTIER est attribué à la seule surface nue.** `max(valeur_fonciere)` =
   la valeur de **toute** la mutation (bâti compris, car DVF répète `valeur_fonciere` sur chaque
   ligne de l'acte) ; `sum(terr_parc)` ne somme que le terrain des parcelles **nues** gardées. Le
   ratio `val / terr_tot` applique donc le prix du bâti à des m² de terrain → médiane gonflée.

**Le bon calcul existe déjà dans le dépôt** (`ingestion/dvf_marche.py:compute_medianes_secteur`,
L.103-150) : il reconstitue l'acte entier, somme le bâti sur **toutes** les parcelles, puis ne
qualifie « terrain » que si `bati_m2 = 0 AND terrain_m2 > 0` — exactement le LOT 1. Le cache
`dvf_secteur_medianes` bâti ainsi est **sain**. Ce sont les fonctions **live** qui divergent. Le
LOT 1 consistera à aligner les fonctions live sur ce modèle déjà validé (un seul point de calcul).

### 0.2 Preuve chiffrée (base locale, Saint-Denis, grain commune)

Reproduction exacte de `_median_terrain` (défectueux) vs qualification acte-entier (corrigé),
mêmes bornes [50 ; 4 000], mêmes natures `('Vente','Vente terrain à bâtir')` :

| Variante | Médiane €/m² | n actes | Requête |
|---|---|---|---|
| **Défectueux** (filtre bâti par parcelle, prix acte entier) | **438** | 1 243 | §0.5 Q1 |
| **Corrigé** (acte entier, `sum(bati)=0`) | **295** | 633 | §0.5 Q2 |

→ **−33 % sur la médiane, 610 actes mixtes (49 %) retirés.** Direction et ordre de grandeur
identiques au cas du relecteur (Saint-Denis 482 → 275, qui est la variante **zone U** via
`ligne2_terrain_zone` / `parcel_zone_plu`, natures `'Vente'` seule — périmètre légèrement différent,
même mécanisme). Le chiffre exact 482/275 sera rejoué sur le point de calcul unique au LOT 1.

### 0.3 Inventaire des points de CALCUL (producteurs)

| # | Fonction (fichier:ligne) | Grain | Natures retenues | Défaut acte-mixte ? |
|---|---|---|---|---|
| P1 | `marche_dvf_commune.py:91` `_median_terrain` (via `mediane_commune('terrain')`) | commune | `Vente`+`VTB` | **OUI** |
| P2 | `faisabilite/marche_commune.py:100` `ligne2_terrain_zone` | commune × zone U/AU | `Vente` seule | **OUI** |
| P3 | `api/moteurs.py:944` série terrain nu trimestrielle (baromètre M18) | île/commune × trimestre | `Vente` seule | **OUI** |
| P4 | `marche_service.py:580` `comparateur_terrain` (secteur, rayon adaptatif) | secteur/parcelle | `Vente`+`VTB` | **OUI** |
| P5 | `pige/signaux.py:84` `_SQL_TERRAIN_ILE` (Radar « toute l'île ») | île zones U/AU | `Vente` seule | **OUI** |
| P6 | `pige/banc_estimer.py:105` pool terrain nu (backtest Estimer) | parcelle (géo) | `Vente`+`VTB` | **OUI** |
| P7 | `faisabilite/marche_commune.py:427` `_median_terrain_commune` | commune (12 m) | `Vente` (ILIKE) | **OUI — mais CODE MORT** (aucun appelant) |
| — | `ingestion/dvf_marche.py:103` `compute_medianes_secteur` → cache `dvf_secteur_medianes` | secteur | `Vente`+`VTB` | **NON (sain)** — modèle de référence |

**Inconsistance secondaire à acter** : la définition même du « terrain nu » diverge entre les
fonctions qui se déclarent pourtant « référentiel UNIQUE » — P2/P3/P5 excluent les
`Vente terrain à bâtir` (VTB), alors que P1/P4/P6 et le cache les incluent (arbitrage M101 B2). À
unifier dans le même point de calcul au LOT 1.

### 0.4 Inventaire des LECTEURS (consommateurs) et leur exposition

| Lecteur (écran / document) | Chemin de code | Point de calcul lu | Même défaut ? |
|---|---|---|---|
| **Tableau comparatif des 24** (`O6Comparateur`) | `api/comparateur.py:68` → `ligne2_terrain_zone` | P2 | **OUI** |
| **Fiche commune** (ContextePanel) | `api/app.py:2588` `ligne2_terrain_zone` ; `/moteurs/marche` → `build_marche_commune` (L.387) | P2 | **OUI** |
| **Évolution du marché** (baromètre M18) | `api/moteurs.py:944` série | P3 | **OUI** |
| **Marché des annonces (Radar)** | `pige/signaux.py` `_dvf_terrain` (commune → P2) / `_SQL_TERRAIN_ILE` (île → P5) | P2/P5 | **OUI** |
| **Fiche parcelle §Marché** | `marche_service.comparateur_terrain` (repère secteur) | P4 | **OUI** |
| **Fiche parcelle §Marché — comparaison Bilan** | `faisabilite/bilan.py:1144` `_prix_terrain_local` → cache `dvf_secteur_medianes` | cache sain | **NON** |
| **Estimer un bien** | `comparateur_terrain` (P4) + banc `banc_estimer` (P6) | P4/P6 | **OUI** |
| **Étude de zone / modules (valorisation zone)** | `api/modules.py:307,428` `ligne2_terrain_zone` ; `modules.py:2839` `prix_terrain_nu_zone`→P2 | P2 | **OUI** |
| **Étude de zone (« prix par type »)** | `zone.py:663` `prix_par_type_zone` — calcul INDÉPENDANT (polygone dessiné, `dvf_mutations`, 36 mois) | P8 (ajouté A-1) | **OUI (A-1)** — définition alignée sur le référentiel (acte sans bâti, Vente+VTB, borne [50,4000]) ; maille = polygone dessiné (documentée) |
| **Classement — charge foncière** | `api/scoreur.py:205` `prix_terrain_nu_zone`→P2 (valorisation affichée) ; la charge elle-même = `compute_bilan` (bilan à rebours) | P2 (affiché à côté) | charge = **NON** ; repère terrain-zone affiché = **OUI** |
| **Classement — Score LABUSE / composite** | `registre/moteurs/commune.py:18-25` INDICATEURS : stock/vélocité/permis/SRU/ZAN/**prix_neuf VEFA** | n'utilise PAS le terrain nu | **NON** |
| **Classement — Signal (`market_signal`)** | `faisabilite/marche_commune.py:349` : liquidité DVF bâti + offre Sitadel | n'utilise PAS le terrain nu | **NON** |
| **Dossier / « autres documents » (export comparatif)** | `exports/blocs/comparatif.py:123` `terrain_zone_eur_m2` ← `moteurs.py:324` / `modules.py:2841` (P2) | P2 | **OUI** |
| **Copilote / missions** | `copilote_v2/outils.py:454`, `missions_lourdes.py:74` → `build_marche_commune` (P2) | P2 | **OUI** |
| **Cascade / score_e (prix probable terrain)** | `cascade/context.py:535`, `ingestion/score_e.py:25` → cache `dvf_secteur_medianes` | cache sain | **NON** |

### 0.5 Requêtes rejouables

```sql
-- Q1 — DÉFECTUEUX (reproduit _median_terrain, grain commune) : filtre bâti par parcelle, prix acte entier
WITH parc AS (
  SELECT DISTINCT dm.id_mutation, dm.id_parcelle, dm.valeur_fonciere AS vf,
         max(COALESCE(dm.surface_terrain,0)) OVER (PARTITION BY dm.id_mutation, dm.id_parcelle) AS terr_p
  FROM dvf_mutations_parcelle dm JOIN parcels p ON p.idu = dm.id_parcelle
  WHERE lower(p.commune)=lower('Saint-Denis')
    AND dm.nature_mutation IN ('Vente','Vente terrain à bâtir')
    AND COALESCE(dm.surface_reelle_bati,0)=0 AND dm.surface_terrain>0),
tot AS (SELECT id_mutation, sum(terr_p) terr_tot, max(vf) vf FROM parc GROUP BY id_mutation)
SELECT round(percentile_cont(0.5) WITHIN GROUP (ORDER BY vf/NULLIF(terr_tot,0))
         FILTER (WHERE vf/NULLIF(terr_tot,0) BETWEEN 50 AND 4000))::int AS med,
       count(*) FILTER (WHERE vf/NULLIF(terr_tot,0) BETWEEN 50 AND 4000) AS n
FROM tot;   -- → 438 €/m², n=1243

-- Q2 — CORRIGÉ (acte entier : bâti sommé sur TOUTES les parcelles = 0) — modèle compute_medianes_secteur
WITH par AS (
  SELECT DISTINCT dm.id_mutation, dm.id_parcelle, dm.valeur_fonciere AS vf,
         max(COALESCE(dm.surface_terrain,0))     OVER (PARTITION BY dm.id_mutation, dm.id_parcelle) AS terr_p,
         max(COALESCE(dm.surface_reelle_bati,0)) OVER (PARTITION BY dm.id_mutation, dm.id_parcelle) AS bati_p
  FROM dvf_mutations_parcelle dm JOIN parcels p ON p.idu = dm.id_parcelle
  WHERE lower(p.commune)=lower('Saint-Denis')
    AND dm.nature_mutation IN ('Vente','Vente terrain à bâtir') AND dm.surface_terrain>0),
tot AS (SELECT id_mutation, sum(terr_p) terr_tot, max(vf) vf, sum(bati_p) bati_tot
        FROM par GROUP BY id_mutation)
SELECT round(percentile_cont(0.5) WITHIN GROUP (ORDER BY vf/NULLIF(terr_tot,0))
         FILTER (WHERE vf/NULLIF(terr_tot,0) BETWEEN 50 AND 4000))::int AS med,
       count(*) FILTER (WHERE vf/NULLIF(terr_tot,0) BETWEEN 50 AND 4000) AS n
FROM tot WHERE bati_tot = 0;   -- → 295 €/m², n=633
```

### 0.6 Conclusion LOT 0 (arbitrage demandé avant LOT 1)

- Le défaut touche **6 points de calcul live** (P1-P6) + **1 mort** (P7). Le **cache secteur**
  (`compute_medianes_secteur`) et ses lecteurs (Bilan, cascade, score_e) sont **déjà sains** et
  fournissent le **modèle de correction**.
- **Score LABUSE (composite)** et **Signal** ne lisent pas le terrain nu → non affectés. La **charge
  foncière** (bilan à rebours) non plus ; seul le **repère terrain-zone affiché à côté** d'elle est
  défectueux.
- **Questions d'arbitrage pour le LOT 1 :**
  1. Point de calcul unique : **étendre `mediane_commune`/`compute_medianes_secteur`** (acte entier)
     et y rebrancher P2 (zone), P3 (série), P4 (secteur), P5 (île), P6 (banc) ? Ou un nouveau module
     `terrain_nu_acte` partagé ?
  2. **VTB** : unifier sur `Vente`+`VTB` (arbitrage M101 B2 déjà en vigueur dans le cache) pour tous ?
  3. Supprimer le code mort P7 au passage ?

### 0.7 Arbitrage rendu (2026-11-23)

1. **Architecture** → **étendre l'existant** : rebrancher P1-P6 sur la logique acte-entier déjà
   validée (`compute_medianes_secteur` / `mediane_commune`), pas de nouveau module.
2. **VTB** → **`Vente` + `Vente terrain à bâtir` partout** (arbitrage M101 B2, comme le cache sain) ;
   P2/P3/P5 cessent d'exclure les VTB.
3. **Périmètre** → le contre-audit `03-COMMUNES-ASTRA.md` sera **fourni** ; **LOT 1 en attente** de ce
   fichier pour verrouiller la liste fermée.

---

## LOT 1 — Terrain nu qualifié sur l'acte entier (bloquant 1) ✅

### 1.1 Le correctif

**Un seul critère, appliqué aux 6 points de calcul live** : un acte n'est une vente de terrain nu que
si **son bâti TOTAL (sur toutes ses parcelles) est nul** — `GROUP BY mutation HAVING sum(bati_p) = 0` —
et sa **surface terrain est reconstituée sur l'acte entier**. Avant, le filtre `surface_reelle_bati = 0`
était posé **par parcelle**, puis `max(valeur_fonciere)` (prix de l'acte ENTIER) était rapporté à la
seule surface nue. Natures unifiées sur **`Vente` + `Vente terrain à bâtir`** (arbitrage M101 B2, comme
le cache secteur sain). C'est le modèle déjà validé de `compute_medianes_secteur` étendu aux chemins live.

| Point | Fichier:fonction | État |
|---|---|---|
| P1 | `marche_dvf_commune.py:_median_terrain` | corrigé |
| P2 | `faisabilite/marche_commune.py:ligne2_terrain_zone` (tableau 24 + fiche) | corrigé |
| P3 | `api/moteurs.py` série terrain nu trimestrielle (baromètre) | corrigé |
| P4 | `marche_service.py:comparateur_terrain` (fiche parcelle §Marché / Estimer) | corrigé |
| P5 | `pige/signaux.py:_SQL_TERRAIN_ILE` (Radar île) | corrigé |
| P6 | `pige/banc_estimer.py` (backtest Estimer) | corrigé |
| P7 | `faisabilite/marche_commune.py:_median_terrain_commune` (hors prod, test-only) | corrigé (cohérence) |

### 1.2 Cas-test : mutation 2021-1672641 (Saint-Denis)

Base locale, `dvf_mutations_parcelle` :

| id_parcelle | nature | valeur_fonciere | bâti m² | terrain m² |
|---|---|---|---|---|
| 97411000BZ0422 | Vente | 225 000 | — | 2 320 |
| 97411000BZ1224 | Vente | 225 000 | 87 | 356 |

Acte mixte (maison BZ1224 + jardin nu BZ0422). **Avant** : BZ0422 passait le filtre par parcelle →
225 000 € / 2 320 m² = 97 €/m² compté comme une vente de terrain nu. **Après** : `sum(bati) = 87 > 0`
→ l'acte entier est **écarté**. Couvert par `tests/test_terrain_nu_acte_entier.py`
(`test_mutation_mixte_reelle_ecartee_par_acte_entier` + un test d'injection d'acte mixte qui vérifie que
le compte et la médiane du terrain nu ne bougent pas).

### 1.3 Tableau du relecteur — avant / après (zone U servie, 5 témoins)

« Avant » = valeurs servies le 22/11 (relecteur, autoritatives). « Après » = valeurs produites par le
code corrigé (`ligne2_terrain_zone`, Vente+VTB, surface reconstituée) — vérifiées en appelant la fonction.

| Commune | Actes mixtes / retenus (relecteur) | Avant €/m² | Après €/m² | n après |
|---|---|---|---|---|
| Saint-Denis | 679 / 1 254 | 482 | **288** | 612 |
| Saint-Paul | 728 / 1 531 | 479 | **271** | 880 |
| Saint-Pierre | 646 / 1 388 | 422 | **301** | 784 |
| Le Tampon | 465 / 1 106 | 285 | **203** | 660 |
| Cilaos | 46 / 138 | 106 | **88** | 92 |

Cilaos tombe à l'euro sur le 88 du relecteur ; les autres sont légèrement au-dessus de son « après »
Vente-seule (275/251/202/303) car l'arbitrage **inclut les VTB** et **reconstitue la surface sur toutes
les zones** de l'acte. Direction et ordre de grandeur identiques, défaut supprimé.

### 1.4 Les 24 communes avec leurs effectifs (terrain nu zone U, après fix)

| Commune | n | Commune | n | Commune | n |
|---|---|---|---|---|---|
| Saint-Paul | 880 | Saint-André | 362 | Le Port | 182 |
| Saint-Pierre | 784 | Saint-Benoît | 386 | La Plaine-des-Palmistes | 174 |
| Saint-Denis | 612 | La Possession | 265 | Les Trois-Bassins | 122 |
| Le Tampon | 660 | Sainte-Marie | 423 | Cilaos | 92 |
| Saint-Joseph | 399 | Petite-Île | 287 | Entre-Deux | 76 |
| Saint-Louis | 415 | Sainte-Suzanne | 316 | Bras-Panon | 57 |
| Saint-Leu | 382 | L'Étang-Salé | 135 | Salazie | 87 |
| Les Avirons | 154 | Sainte-Rose | 50 | **Saint-Philippe** | **— (RNU, pas de zone U)** |

Toutes les médianes communales baissent après exclusion des actes mixtes (sweep 24 communes vérifié).

### 1.5 Écart sur trois bilans témoins

| Témoin | Lecteur | Avant | Après |
|---|---|---|---|
| Saint-Denis | tableau 24 / fiche commune (zone U) | 482 | **288** |
| Saint-Denis | médiane commune entière (`mediane_commune`, Radar « Ce bien » / PDF) | 438 | **293** (n=627) |
| Saint-Paul | tableau 24 / fiche (zone U) | 479 | **271** · commune entière **350** (n=916) |
| Cilaos | tableau 24 / fiche (zone U) | 106 | **88** · commune entière **96** (n=106) |
| Radar « toute l'île » (zones U/AU) | `_dvf_terrain(None)` | — | **240** (n=8 523) |

> **La charge foncière du Bilan de faisabilité (bilan à rebours) n'est PAS affectée** : elle ne lit pas
> la médiane terrain nu live, mais le cache secteur `dvf_secteur_medianes` (type_bien='terrain'), **déjà
> qualifié sur l'acte entier** (LOT 0). Le LOT 1 corrige donc le **repère de marché affiché**, pas le
> calcul de charge — qui était déjà juste. C'est l'écart demandé : nul sur la charge, −30 à −45 % sur le
> prix de terrain nu montré au promoteur.

### 1.6 Non-régression

- **Cohérence (12 témoins, base locale)** : `87 passed` (exit 0) — le changement en point unique garde
  fiche / outils / PDF / Docs / Copilote cohérents à l'euro/au m².
- **Rectification de l'audit (anticipe Mineur 9)** : le chemin terrain nu servi (`ligne2_terrain_zone`)
  n'appliquait **pas** la borne [50 ; 4 000] €/m² annoncée par l'audit de Claude (elle vit dans
  `_median_terrain`/`comparateur_terrain`, pas dans la zone servie) ; le relecteur a raison.

*Reste du LOT (si demandé) : capture écran du tableau/fiche après correctif (vérif finale 10).*

---

---

## LOT 2 — Signal SRU piloté par le statut (bloquant 2) ✅

**Défaut** : `app.py:_signaux_commune` émettait « SRU déficitaire » dès que `taux < objectif`, **sans
regarder le statut**. Cilaos (2,94 / 25) et Saint-Philippe (9,57 / 20) sont **exemptées** (donnée
`commune_contexte_sru.statut = 'exemptee'`) et portaient pourtant un signal rouge faux.

**Correctif** : extraction d'une fonction PURE `_sru_signal(sru)` qui suit le **statut officiel** et
**date** le signal :

| Commune | statut (donnée) | taux / obj | Signal avant | Signal après |
|---|---|---|---|---|
| Cilaos | exemptee | 2,94 / 25 | 🔴 SRU déficitaire | **(aucun)** |
| Saint-Philippe | exemptee | 9,57 / 20 | 🔴 SRU déficitaire | **(aucun)** |
| Saint-Paul | deficitaire | 18,33 / 25 | 🔴 SRU déficitaire | 🔴 SRU déficitaire (18,3 % / 25 %) · **SRU 2025** |
| Entre-Deux | carencee | 10,29 / 25 | 🔴 SRU déficitaire | 🔴 **SRU carencée** (10,3 % / 25 %) · SRU 2025 |
| Saint-Denis | conforme | 38,62 / 20 | (aucun) | (aucun) |

Taux, objectif, statut et année restent affichés **séparément** par la carte SRU de la fiche
(`SRU_META`, déjà dédiée). L'exemption n'est pas prolongée au-delà de sa période (on date, on ne
suppose pas 2026). Couvert par `tests/test_sru_signal.py` (5 tests, suite rapide, hors base).

## LOT 3 — Signal ZAN daté et nommé « scénario » (bloquant 3) ✅

**Défaut** : le signal court disait « ZAN épuisé dans 1,1 an » — un futur **relatif, sans date**,
trompeur lu en novembre 2026 (le calcul était juste au terme de la série, fin 2024), et présenté
comme une enveloppe alors que le budget = 50 % de la conso 2011-2021 est une **hypothèse** (scénario
−50 %), pas une enveloppe réglementaire opposable.

**Correctif** : fonction PURE `_zan_signal(h)` + constantes `ZAN_SERIE_FIN=2024` / `ZAN_SERIE_LABEL`
(série Cerema ENAF **ingérée** = conso 2009-2024, publiée 12/05/2025 — la plus récente disponible en
base ; à bumper à la prochaine ingestion). Le signal porte désormais le mot **scénario**, le terme
**solde simulé** (≠ enveloppe réglementaire) et une **année absolue** :

| Commune | horizon | Signal avant | Signal après |
|---|---|---|---|
| Saint-Denis | 1,1 an | ZAN épuisé dans 1,1 an | **ZAN — scénario −50 % : solde simulé épuisé vers 2025 (Cerema conso 2021-2024)** |
| Saint-Philippe | 0,8 an | ZAN épuisé dans 0,8 an | ZAN — scénario −50 % : solde simulé épuisé vers 2025 (Cerema conso 2021-2024) |
| Cilaos | 0 (dépassé) | enveloppe ZAN déjà dépassée | ZAN — scénario −50 % : solde simulé déjà dépassé (Cerema conso 2021-2024) |

La carte ZAN détaillée de la fiche distinguait déjà la projection de l'enveloppe (« Scénario au rythme
observé… Projection, pas une échéance réglementaire »). Couvert par `tests/test_zan_signal.py` (5 tests,
suite rapide, hors base).

## LOT 4 — Points à corriger 4-8 ✅

### 4.4 VEFA — surfaces répétées (chiffré) ✅

**Défaut** : `neuf_vefa_commune` sommait `surface_reelle_bati` groupé par mutation, sur des lignes
**répétées par nature_culture** → dénominateur gonflé, €/m² sous-estimé. Cas 2024-1190924 (Saint-Louis) :
les mêmes 130 m² sur AM0318 comptés deux fois → bâti **716 m² au lieu de 403** (×1,78).

**Correctif** : déduplication par (mutation, parcelle, type_local, surface) avant somme — **même
dédoublonnage que `ensure_dvf_views.lignes_dedup`** (un critère, un endroit).

**Effet global sur les médianes** (modeste — l'acte mixte multi-cultures est minoritaire, la médiane
est robuste ; n inchangé) :

| Commune | VEFA avant | VEFA après | Δ |
|---|---|---|---|
| Saint-Denis | 4 878 | 4 886 | +8 |
| Saint-Paul | 4 745 | 4 746 | +1 |
| Saint-Pierre | 4 931 | 4 952 | +21 |
| Le Tampon | 4 785 | 4 853 | +68 |

Le biais est supprimé à la source ; les têtes de médianes bougent peu (≤ 1,4 %), le chiffrage demandé
par le relecteur est donc : **effet unitaire fort sur les actes mixtes, effet agrégé faible (≤ 1,4 %)**.

### 4.5 Permis — trimestre incomplet, série par série ✅

**Défaut** : le drapeau « trimestre partiel » ne dépendait que du VOLUME (`_marque_partiel`, délai de
publication DVF). Sitadel s'arrêtant en août, 2026T3 (2 mois sur 3) est incomplet mais n'était PAS
marqué pour l'île et Saint-Denis (volume stable) — le relecteur l'a mesuré ; le drapeau d'une série
(DVF) servait pour l'autre.

**Correctif** : `_marque_partiel_couverture(serie, maj_date)` — un trimestre est partiel par COUVERTURE
si sa fin dépasse la dernière donnée de SA source. Appliqué à la série **permis** (borne Sitadel =
`max(date)` = 2026-08-31) ; DVF/terrain gardent leur heuristique de volume (inchangés).

| Série | Tête | Partiel avant | Partiel après |
|---|---|---|---|
| permis (île / St-Denis / Cilaos) | 2026T3 | **false** (île, St-Denis) | **true** (Sitadel s'arrête en août) |
| DVF / terrain | 2026T2 / 2025T4 | (heuristique volume) | inchangé |

Couvert par `tests/test_barometre_partiel.py` (4 tests, suite rapide).

### 4.7 « Acquisitions récentes » → « Changements de propriétaires (personnes morales) » ✅

Renommé (porte de l'outil Communes + section Étude de zone), avec la mention explicite : *changement de
propriétaire entre deux millésimes DGFiP — pas nécessairement un achat (ni sa date exacte)*. Le mot
« acquisition » ne sur-affirme plus ce que la source établit (`Communes.tsx`, `EtudeZone.tsx`).

### 4.4-bis — « VEFA déclarée » vs « neuf inféré sur la parcelle » ✅

Carte Prix de la fiche commune : les deux prix neuf sont désormais **nommés sans ambiguïté et portent
leur effectif** — « VEFA déclarée (prix à l'acte) · n 355 » et « Neuf inféré sur la parcelle · n 54 »,
avec une ligne de méthode : *rapprochement ventes ≤ 3 ans après l'achèvement d'un permis sur la parcelle
— méthode indicative, pas une preuve que le logement vendu appartient au bâtiment achevé*. Effectif VEFA
exposé par le payload (`comparable.neuf_n`, `fiche_commune.py` + `api.ts`). Vérifié en direct : Saint-Paul
VEFA n=326 · neuf inféré n=54.

### 4.6 — demandé / acté : deux médianes séparées, écart indicatif ✅

Bloc Activité de la fiche : les deux médianes sont montrées **séparément avec leur nature et effectif**
(« Prix demandé médian (annonces, Radar) · n … » et « Prix acté médian (ancien, DVF commune) »), et
l'écart est libellé **« (indicatif) »** avec la mention : *deux populations NON comparables (annonces
tous types / statuts mêlés / relevé continu vs ventes « ancien » DVF, fenêtre et composition
différentes) : écart INDICATIF, pas une marge de négociation*. (Changement additif côté front — le champ
`ecart_demande_acte_pct` est conservé pour les autres consommateurs, sans régression.)

### 4.8 — définitions ✅ (deux déjà en place)

- **tendance** : `ligne4_tendance` passe de `ILIKE '%vente%'` (VEFA incluse) à **`= 'Vente'` stricte** —
  elle mesure désormais LA MÊME population que l'« ancien » affiché à côté. Saint-Denis : +1,3 % (VEFA
  incluse) → **+1,8 %** (ancien strict).
- **dénominateur PPR** : `risques()` utilise le **parc VIVANT** (`compte_parcelles_commune`, exclut les
  disparues) — même base que le bandeau. Saint-Denis 72,2 % (dénom. 38 557) → **72,7 %** (dénom. 38 295).
- **procédure PLU** : déjà affichée **à côté** du statut « à jour » (carte Urbanisme, `procedure_sudocuh`).
- **zone du terrain** : la zone (U/AU) est portée par le « i » de la cellule (LOT 5) et par la fiche.
- **source du loyer** : l'étiquette porte déjà « OLL {année} (zone {z}) » vs « DHUP » (ligne9_loyer).
- **« ancien »** : l'infobulle du tableau dit déjà « commune entière, tous types bâti, ventes strictes,
  n ≥ 100, vue macro ≠ prix local de la fiche ».

## LOT 5 — mineur ✅

- **Tiret + effectif dans la cellule** (`blocB.tsx`) : chaque cellule prix du tableau porte un `title`
  (survol) qui DIT l'effectif et la raison du « — ». Vérifié à l'écran : « n = 880 ventes de terrain nu ·
  zone U » (Saint-Paul), « — : moins de 8 ventes VEFA (n = 5) » (Saint-Louis), « — : moins de 10 ventes de
  terrain nu » (Saint-Philippe, RNU).
- **Rectifications de l'audit de Claude** (§8 du contre-audit) : (a) le chemin terrain nu SERVI
  (`ligne2_terrain_zone`) n'applique PAS la borne [50, 4 000] annoncée (elle vit dans `_median_terrain` /
  `comparateur_terrain`) ; (b) l'« ancien » du tableau n'a ni filtre de type ni surface bâtie minimale ;
  (c) le filtre de cohortes mûres (délai d'instruction) n'est PAS appliqué à la médiane du tableau ;
  (d) la série d'évolution montre **neuf** trimestres, pas huit. (Documenté ici — l'audit `03-COMMUNES.md`
  est un livrable figé ; ces points le corrigent.)

## Vérification 10 — relecture sur l'app ✅

API `:7520` + front `:10320` (ports du mandat) lancés ; relu **à l'écran** sur **Saint-Denis, Cilaos et
Saint-Philippe** (chaque libellé corrigé du tableau et de la fiche), puis **arrêtés avant de rendre la
main**. Captures dans `~/Desktop/outil-communes-fix-1/` :

- `01-tableau-24-terrain-nu-corrige.png` — terrain nu corrigé sur les 24 communes (St-Denis 288, St-Paul
  271, Cilaos 88…) + effectifs/raison du tiret au survol des cellules (LOT 5 : « n = 880 … zone U »,
  « — : moins de 8 ventes VEFA (n = 5) », « — : moins de 10 ventes de terrain nu »).
- `02-fiche-cilaos-sru-exemptee-zan-scenario.png` — Cilaos (exemptée) : **aucun** signal « SRU
  déficitaire » ; ZAN « scénario −50 % : solde simulé déjà dépassé (Cerema conso 2021-2024) » ; SRU « 2,9 / 25 % ».
- `03-fiche-saint-denis-prix-vefa-declaree.png` — Saint-Denis (conforme) : « Prix ancien 2 493 · **VEFA
  déclarée** 4 886 €/m² », **tendance +1,8 %** (alignée), **38 295 parcelles** + **PPR 72,7 %** (parc
  vivant cohérent), ZAN scénario, **aucun** signal SRU (conforme).
- `04-fiche-saint-philippe-rnu-exemptee.png` — Saint-Philippe (exemptée, RNU) : **aucun** signal « SRU
  déficitaire » ; bandeau RNU ; « VEFA déclarée — » ; ZAN scénario.

Les trois communes exigées par la relecture sont relues à l'écran. (Note env. : le serveur API local est
tué par le bac à sable après ~1-2 min ; chaque fiche a été capturée dans sa fenêtre de vie, le reste des
chiffres étant confirmé par appels directs aux endpoints `:7520`.)

---

## Tests & non-régression (état à la clôture de cette passe)

| Gate | Résultat |
|---|---|
| Cohérence 12 témoins (base locale) | **87 passed** (exit 0) — surfaces cohérentes après LOT 1-4 |
| Suite Python « unitaires » (hors base) | **5005 passed** ; seuls échecs = environnement/concurrence (voir ci-dessous), aucun dû au diff |
| Front `tsc -b` | exit 0 |
| Front `vitest` | exit 0 |
| Tests ajoutés | `test_terrain_nu_acte_entier` (db), `test_sru_signal` (5), `test_zan_signal` (5), `test_barometre_partiel` (4) |

**Échecs environnement / concurrence (pré-existants, hors diff)** : (1) `test_boot_verrou_1` échouait sur
`host 'None'` faute de `.env` dans le worktree → **`.env` créé** (gitignoré, socket/TCP `openclaw` — rôle
`labuse:labuse` inexistant sur ce poste) → vert ; (2) `test_etude_fiable_1` (déterminisme) flaky — **passe
en isolement**, flottement dû aux autres sessions qui partagent la base locale (noté dans le mandat). Le
seul vrai accroc introduit — un garde de structure `test_chirurgical_fix_j` exigeant la syntaxe
`OVER (PARTITION BY …)` dans `_median_terrain_commune` — a été corrigé en conservant cette syntaxe (dédup
par couple) tout en ajoutant la qualification acte-entier.

## Reprises après relecture indépendante (RELECTURE-COMMUNES-1)

La relecture valide les 3 bloquants et la liste fermée (reproduits à la valeur près). Reprises :

### A-1 — `zone.py:prix_par_type_zone` rebranché sur le calcul unique ✅
Second lecteur du terrain nu (Étude de zone, « prix par type »), **absent de l'inventaire initial**,
sur un calcul indépendant. Aligné sur la DÉFINITION du référentiel : natures **Vente + VTB** (fini
`ILIKE 'vente%'` qui laissait entrer la VEFA), **acte sans bâti** (`surface_reelle_bati = 0`, plus
`< 20` — sur `dvf_mutations` à la maille mutation, c'est l'équivalent exact du `sum(bati)=0`), et
**borne [50 ; 4 000] €/m²** (jusque-là ABSENTE). La **maille** reste propre à l'Étude de zone (polygone
dessiné, fenêtre 36 mois cohérente avec maison/appartement) — **désormais documentée** dans l'inventaire
ci-dessus. Inventaire complété (ligne P8). *Note base locale : `dvf_mutations.geom` n'est pas peuplé
ici (0/31 171), donc ce chemin rend n=0 localement — vérifié au niveau code/définition, chiffrable en
prod où la géométrie est ingérée.*

### A-2 — `ligne2_terrain_zone` : vitesse restaurée, résultat identique ✅
Le double scan (`allparc` + `muz`) est remplacé par **un scan unique** avec `LEFT JOIN parcel_zone_plu`
portant l'appartenance de zone (`bool_or(zone_fam='U'/'AU')`) dans le même passage. **Mesuré Saint-Paul :
637 → 66 ms** (≈ 10×), **résultat identique à l'euro/à l'unité** (St-Denis U 288/612, St-Paul 271/880,
Cilaos 88/92 — inchangés).

### M3 — SRU : statut inattendu → « statut inconnu », jamais « déficitaire » ✅
`_sru_signal` suit le statut officiel ; un statut HORS référentiel (nouvelle valeur de millésime, NULL,
faute de frappe) ne disparaît plus en silence et n'est jamais interprété « déficitaire » : il affiche
**« SRU : statut inconnu « … » »** (ton orange) pour être relu. Couvert par deux tests ajoutés
(`test_sru_signal.py`). `deficitaire` fait foi même si `taux ≥ objectif` (plus de signal dû perdu).

### Mineurs consignés (limites connues, chiffrées)
- **M1** — fuite multi-communes : **7 actes** (sur 40 203) retenus « terrain nu » dans une commune alors
  que leur bâti réel est dans une AUTRE commune (`JOIN parcels p.commune = :c`). Négligeable sur les
  médianes ; non corrigé (coût disproportionné). `marche_commune.py`.
- **M2** — surface d'acte multi-zones : `terr_tot` inclut les parcelles hors U/AU (dilution par de
  l'hectare agricole) — **9 actes sur 612 à Saint-Denis (1,5 %)**, impact médiane négligeable. `marche_commune.py`.
- **M4** — dédup VEFA par valeur de surface : deux lots de surfaces proches (45/46 m²) comptés
  séparément (ambiguïté de la donnée source DVF, pas du correctif) — effet **≤ 1,4 %** sur la médiane.
  `ingestion/dvf_marche.py`.

## Comment rejouer

```bash
export LABUSE_DATABASE_URL="postgresql+psycopg://openclaw@localhost:5432/labuse"
PYTHONPATH=src .venv/bin/python -m pytest -m coherence tests/coherence_ecrans/ -q      # 87 passed
PYTHONPATH=src .venv/bin/python -m pytest tests/test_sru_signal.py tests/test_zan_signal.py \
    tests/test_barometre_partiel.py tests/test_terrain_nu_acte_entier.py -q
```
