# Audit — plafond voirie 5 000 (avant vague 2)

> **Audit lecture seule** (diagnostic d'origine, conservé tel quel ci-dessous). Aucun import, aucune
> écriture base, aucune cascade au moment de l'audit. Diagnostic au **2026-06-20**.
>
> **🔧 MISE À JOUR 2026-06-20 — correctif CODE appliqué (données NON modifiées).** La pagination voirie
> est désormais implémentée et testée (cf. **§10 Correction appliquée**). **Aucune base n'a été touchée :
> aucun re-fetch, aucune cascade, aucun verdict modifié.** La voirie reste plafonnée à 5 000 en base
> (preuve : `voirie=5000` partout) tant que le re-fetch ciblé n'est pas lancé — voir
> **`docs/VOIRIE_REFETCH_RUNBOOK.md`** (procédure prête, NON exécutée).

## 1. Cause exacte

**Le plafond 5 000 n'est PAS dans notre code — c'est le plafond serveur du WFS IGN Géoplateforme**,
atteint parce que l'ingestion voirie fait **une seule requête non paginée**.

- `layers_ingest.ingest_bdtopo()` (utilisé pour **voirie** et `water`, ligne 369) fait **un seul**
  `wfs.fetch_layer(... max_features=8000)` → **pas de pagination**.
- `connectors/wfs.py:fetch_layer()` envoie `count=max_features` (8000) dans **un seul GetFeature WFS 2.0**.
- Le serveur **Géoplateforme WFS plafonne une réponse à 5 000 entités** (limite serveur `CountDefault`,
  comportement WFS standard) → il ignore `count=8000` et renvoie **au plus 5 000**.
- À l'inverse, **`ingest_batiments()` (ligne 413) et `ingest_ravines()` (ligne 384) PAGINENT**
  (boucle `start_index` + `sort_by="cleabs"`, par pages de 5 000/1 000) → elles récupèrent **tout**
  (bâti La Possession = 42 217, bien au-delà de 5 000). **La voirie ne pagine pas → elle est tronquée.**

> En clair : **augmenter `max_features` ne sert à rien** (le serveur cape à 5 000). Seule **la pagination**
> (déjà utilisée pour le bâti) récupère l'intégralité.

## 2. Qui est plafonné ?

`SELECT count(*) FROM spatial_layers WHERE kind='voirie' GROUP BY commune` :

- **15 / 18 communes présentes = exactement 5 000 → PLAFONNÉES** : Saint-Paul, La Possession,
  L'Étang-Salé (les 3 **gold**), **+ Saint-Pierre, Le Tampon, Saint-Denis, Saint-Leu, Saint-Louis**
  (les 5 grosses de la **vague 2**), + Saint-André, Saint-Joseph, Saint-Benoît, Les Avirons, Entre-Deux,
  Petite-Île, Bras-Panon.
- **3 communes < 5 000 = réelles (non tronquées)** : Le Port (4 897), La Plaine-des-Palmistes (3 178),
  Saint-Philippe (2 590). Ce sont les seules dont la voirie est **complète** (elles ont < 5 000 tronçons).

➡️ **Toutes les communes denses/grandes sont tronquées.** Plus la commune est grande, plus la troncature
est forte (le vrai nombre de tronçons croît, mais on en garde toujours 5 000).

## 3. 5 000 est-il suffisant ?

**Non pour les communes moyennes/grandes.** Le vrai nombre de tronçons de route d'une commune dense
(Saint-Paul 51 129 parcelles, Saint-Denis, Le Tampon) dépasse largement 5 000 — vraisemblablement
**10 000–20 000+**. On en garde 5 000, soit potentiellement **50–75 % de tronçons manquants**, et
**sans tri spatial** (ordre serveur par identifiant) → les 5 000 conservés laissent des **trous
géographiques**.

## 4. Impact métier (accès / enclavement / distance voirie)

La cascade calcule la **distance à la voirie la plus proche** (proxy d'accès). Si le tronçon le plus
proche a été **tronqué**, la distance est **surestimée** → la parcelle est faussement classée
**« accès non identifié »** (`scoring/declassement.py`, `ACCES_MAX_M = 6 m`) → **déclassée en « à creuser »**.

Mesuré sur les communes gold (dernière évaluation, motif « accès » SEUL, sans autre déclasseur) :

| Commune | Parcelles | « à creuser » | motif accès (total) | **« à creuser » accès SEUL** |
|---|--:|--:|--:|--:|
| Saint-Paul | 51 129 | 19 172 | 40 238 | **6 922** |
| La Possession | 13 338 | 4 141 | 8 158 | **1 081** |
| L'Étang-Salé | 9 070 | 2 696 | 3 239 | **401** |

**Lecture prudente** : le seuil 6 m est strict (beaucoup de parcelles sont légitimement à > 6 m d'un axe,
même avec une voirie complète). Donc tous ces « accès seul » ne sont pas des faux — mais **le plafond ne
peut qu'AGGRAVER** (jamais améliorer) : il **ajoute** des faux enclavements là où le tronçon proche manque.
Le « accès seul » est donc une **borne haute** des faux négatifs imputables au plafond :
**jusqu'à ~6 900 parcelles Saint-Paul, ~1 080 La Possession, ~400 L'Étang-Salé** potentiellement
**retenues à tort en « à creuser »** (donc des **opportunités sous-comptées**).

## 5. Risque pour les futures grosses communes (vague 2)

**Élevé et structurel.** Saint-Pierre, Le Tampon, Saint-Denis, Saint-Leu, Saint-Louis sont **toutes
déjà plafonnées à 5 000** et sont **plus grandes/denses** que les communes test → **troncature
proportionnellement pire** → **plus de faux « accès non identifié »** → **opportunités sous-comptées**
sur exactement les communes à **plus forte valeur promoteur**. Les traiter avec le plafond actuel
produirait des verdicts gold « techniquement verts » mais **biaisés sur l'accès**.

## 6. Options de correction (évaluées)

| # | Option | Verdict |
|---|---|---|
| 1 | **Augmenter le plafond** (`max_features`) | ❌ Inutile — le serveur cape à 5 000 quoi qu'on demande. |
| 2 | **Vraie pagination voirie** (`start_index` + `sort_by="cleabs"`, comme le bâti) | ✅ **RECOMMANDÉ** — pattern déjà éprouvé (bâti, ravines), `wfs.py` le supporte déjà, récupère tout, marche pour petites ET grandes communes. |
| 3 | **Tuile/bbox par commune** (sous-découper l'emprise) | ⚠ Marche mais plus complexe que la pagination ; utile seulement si une page > 5 000 même paginée (pas le cas). |
| 4 | **Re-fetch ciblé voirie + re-cascade** (communes déjà gold) | ✅ **complément opérationnel** — pour récupérer Saint-Paul / La Possession / L'Étang-Salé une fois le code corrigé (ré-ingère SEULEMENT la voirie + relance la cascade). Décision séparée (re-traitement). |
| 5 | **Plafond petites communes, pas grandes** | ❌ Inutile — la pagination (option 2) gère déjà les deux (1 page pour les petites, N pages pour les grandes). |

## 7. Correction proposée (au moment de l'audit) — **APPLIQUÉE depuis, cf. §10**

Rendre la voirie **paginée**, comme le bâti :
- soit ajouter la **pagination dans `ingest_bdtopo`** (boucle `start_index` + `sort_by` jusqu'à
  `len(feats) < page_size`), ce qui corrige **voirie ET water** d'un coup ;
- soit donner à la voirie sa **propre fonction paginée** `ingest_voirie()` (calquée sur `ingest_batiments`).
- `sort_by="cleabs"` (tri stable BD TOPO) est **obligatoire** pour paginer sans doublon ni trou.
- Garder un **garde-fou de boucle** (page_size 5 000, arrêt quand page incomplète, plafond dur de
  sécurité ex. 50 000 pour éviter une boucle infinie).

## 8. Tests nécessaires

- **Unitaire (mock WFS)** : un connecteur factice qui renvoie 2 pages (5 000 + 1 200) → `ingest_voirie`
  doit retourner **6 200** (preuve de pagination), pas 5 000.
- **Arrêt** : page incomplète (< page_size) → la boucle s'arrête (pas d'appel superflu).
- **Petite commune** : source < 5 000 → 1 seule page, count correct (régression).
- **Garde-fou** : plafond dur respecté (pas de boucle infinie si le serveur renvoie toujours plein).
- **Pas de doublon** : `sort_by` stable → 0 doublon (kind, géométrie) après pagination.

## 9. Faut-il corriger avant Saint-Pierre / Le Tampon / Saint-Leu / Saint-Louis ?

**OUI.** Trois raisons :
1. Ce sont les communes **les plus grandes** → **les plus tronquées** → **le plus de faux « accès »** →
   opportunités sous-comptées sur le **cœur de cible promoteur**.
2. Les traiter d'abord puis corriger = **les re-traiter** (re-couches voirie + re-cascade) → double travail.
3. Le correctif est **petit, bien cerné et déjà éprouvé** (pagination du bâti) → faible risque, fort gain.

**Ordre recommandé** : (a) corriger la pagination voirie + tests, (b) re-fetch voirie + re-cascade des
**3 communes gold** (option 4) pour les remettre au standard sur l'accès, (c) **ensuite** lancer la vague 2.

---

## Synthèse pour décision

| Question | Réponse |
|---|---|
| **Cause exacte** | Voirie = 1 requête WFS non paginée ; le serveur Géoplateforme cape à 5 000/réponse. |
| **Impact communes gold** | Voirie tronquée à 5 000 → faux « accès non identifié » → jusqu'à ~6 900 / 1 080 / 400 parcelles (Saint-Paul / La Possession / L'Étang-Salé) retenues à tort en « à creuser ». |
| **Impact grosses communes** | Pire (plus grandes = plus tronquées) ; toutes déjà plafonnées. |
| **Recommandation** | **Option 2 — paginer la voirie** (comme le bâti) + re-fetch ciblé des gold (option 4). |
| **Correction** | Pagination `start_index`/`sort_by="cleabs"` dans `ingest_bdtopo` (ou `ingest_voirie` dédiée). |
| **Tests** | Pagination (2 pages → somme), arrêt, petite commune, garde-fou, 0 doublon. |
| **Avant vague 2 ?** | **OUI** — corriger + re-fetch des gold, puis lancer les grosses communes. |

*Audit lecture seule. Le correctif et le re-fetch sont à valider séparément.*

---

## 10. Correction appliquée — CODE uniquement (2026-06-20)

> **Périmètre de ce chantier : code + tests + doc.** Aucun import, aucun re-fetch, aucune cascade,
> aucune écriture base, aucun verdict modifié, aucune commune traitée, aucun merge `main`, aucun déploiement.
> La base reste à l'identique (18 communes / 377 194 parcelles ; `voirie=5000` partout — non re-fetchée).

### 10.1 Ce qui a changé (1 fonction)

`src/labuse/ingestion/layers_ingest.py` › **`ingest_bdtopo()`** — la requête WFS unique est remplacée par
une **boucle de pagination** :

```text
start = 0
boucle :
    fetch_layer(typename, bbox, max_features=page_size=5000, start_index=start, sort_by="cleabs")
    insérer les features de la page
    si len(page) < page_size  →  STOP (dernière page, incomplète ou vide)
    start += page_size
    si start >= max_total (=60 000)  →  STOP + WARNING (garde-fou anti-boucle)
journaliser : nombre de pages + total d'objets
```

- **Choix de périmètre** : on pagine **`ingest_bdtopo`**, qui sert **à la fois la voirie ET le `water`**
  (même chemin, même bug). C'est le correctif **minimal et complet** : il couvre les deux couches
  concernées par le plafond sans élargir à d'autres fonctions. `ingest_batiments` et `ingest_ravines`
  **paginaient déjà** (inchangées) — la voirie s'aligne désormais sur le **même pattern éprouvé**.
- **Tri stable obligatoire** : `sort_by="cleabs"` (identifiant stable BD TOPO) → fenêtres `start_index`
  **disjointes**, donc **zéro doublon ni trou** entre pages.
- **Garde-fou anti-boucle** : `max_total=60 000`. Si un serveur pathologique renvoyait toujours une page
  pleine, la boucle s'arrête au plafond et **journalise un WARNING** plutôt que de boucler à l'infini.
- **Journalisation** : INFO en fin d'ingestion (`N objet(s) en P page(s)` par commune) → on **voit** si une
  commune dépasse 5 000 (preuve de dé-plafonnement) et le WARNING signale toute troncature résiduelle.

### 10.2 Pourquoi la pagination (et pas un simple `max_features` plus grand)

Le plafond **n'est pas dans notre code** : c'est la limite **serveur** du WFS Géoplateforme
(`CountDefault`, comportement WFS 2.0 standard). Le serveur **ignore tout `count`/`max_features`
au-delà de son plafond** et renvoie **au plus 5 000** entités par réponse `GetFeature`.

➡️ **`max_features=8000` (valeur d'avant) était donc inopérant** : on demandait 8 000, le serveur en
rendait 5 000, et l'ingestion n'allait **jamais chercher la suite**. Seule la **pagination**
(`startIndex` qui avance page après page) franchit le plafond, exactement comme le bâti récupère
> 40 000 bâtiments par commune. Augmenter encore `max_features` (10 000, 50 000…) ne changerait **rien**.

### 10.3 Stratégie de test (mock WFS — zéro réseau, zéro base)

`tests/test_voirie_pagination.py` — `WfsConnector` et `_insert_layer` sont **mockés** (aucun appel
réseau, aucune écriture base). **9 tests verts** :

| Test | Vérifie |
|---|---|
| `test_une_page_sous_5000` | petite commune (3 000) → 1 page, 1 appel (régression non-pagination inutile). |
| `test_deux_pages_5000_plus_1200` | **6 200** récupérés (> plafond) → **preuve de pagination** ; `start_index` = [0, 5000]. |
| `test_multiple_exact_de_5000` | 10 000 pile → 2 pages pleines + 1 page vide → stop propre (3 appels). |
| `test_arret_sur_page_vide_directe` | page vide d'emblée → 1 appel, stop. |
| `test_tri_stable_cleabs_sur_chaque_page` | `sort_by="cleabs"` sur **chaque** requête. |
| `test_pas_de_doublon_fenetres_non_chevauchantes` | `start_index` strictement croissants → **0 doublon** inséré. |
| `test_garde_fou_anti_boucle` | serveur « toujours plein » → s'arrête à `max_total`, pas de boucle infinie. |
| `test_regression_batiment_pagine` | **bâti** (déjà paginé) **inchangé** (6 200, tri stable). |
| `test_regression_ravines_paginees` | **ravines** (déjà paginées, filtre `nature='Ravine'`) **inchangées** (2 300, 3 pages). |

Full pytest : **441 passed**. `ruff check src tests` : **All checks passed**.

### 10.4 Re-fetch — PRÉVU, NON exécuté

Le code corrigé **ne change rien en base** tant qu'on ne ré-ingère pas la voirie. Le re-fetch ciblé des
**3 communes gold** (Saint-Paul, La Possession, L'Étang-Salé) + re-cascade est décrit pas à pas dans
**`docs/VOIRIE_REFETCH_RUNBOOK.md`** (backup pré, re-fetch voirie seule, re-cascade, post-checks,
décision gold maintenu / NO-GO, rollback). **À lancer séparément, sur validation explicite.**

**Impact attendu après re-fetch** (et seulement à ce moment-là) : la distance-à-la-voirie redevient
exacte → **moins de faux « accès non identifié »** → des parcelles aujourd'hui retenues à tort en
« à creuser » (jusqu'à ~6 900 Saint-Paul / ~1 080 La Possession / ~400 L'Étang-Salé, **bornes hautes**
du §4) repassent en **opportunités**. Le sens est **monotone** : le re-fetch ne peut qu'**ajouter** des
tronçons → les distances ne peuvent que **diminuer** → aucun verdict ne se dégrade du fait du correctif.
