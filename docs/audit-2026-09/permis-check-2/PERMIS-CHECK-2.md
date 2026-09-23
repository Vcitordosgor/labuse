# PERMIS-CHECK-2 — Outil Permis : 3 problèmes réels

Branche `fix/permis-check-2` (worktree `~/Desktop/labuse-permis2`, base = main `25598473` **+ merge de `fix/permis-check-1`** `eec69b73` — PERMIS-CHECK-1 n'était pas mergée dans main, or le pt 3 corrige sa normalisation). Ports 8205/5405.
Mandat d'exécution : comprendre la cause données à l'appui, corriger, prouver au navigateur.

| Point | État | Nature |
|---|---|---|
| 1 — la phrase annonce des permis mais aucun point n'apparaît | **FAIT** | back (géom servie) + front (carte pilotée par la parcelle) + preuve data BZ1065 |
| 2 — le zoom ne suit pas au changement de parcelle dans la barre | **FAIT** | front (lever la fiche stale avant le focus) + constat navigateur |
| 3 — « 1 bis » écrasé en « 1 » | **FAIT** | back (le libellé porte le rep) + constat navigateur |

Portes : `tsc -b` vert · `vite build` vert · vitest **178 pass / 3 échecs admin PRÉ-EXISTANTS** (Detail.test / Donnees.test — snapshots admin, sans lien) · recherche/adresses **9/9** (dont la régression pt 3 renforcée) · sous-ensemble pytest `module|permis|registre|lecture` = **7 échecs / 135 pass IDENTIQUE à la baseline HEAD** (prouvé par revert des 4 fichiers → même 7/135 ; les 7 = `circuit_provenance` base_reelle ×5 + `plu_destinations::module_unique` [offenders gabarit, jamais touchés] + `retours17_permis::test_w2` [chaîne absente de main comme de HEAD, pré-existant]). **0 échec nouveau.**

---

## Point 1 — la phrase annonce des permis, mais aucun point n'apparaît

### Diagnostic chiffré — BZ1065 (`97411000BZ1065`, Saint-Denis)

La phrase (« 11 permis ») et la carte venaient de **deux sources différentes** :

- **la phrase** compte `/modules/parcelle-permis` = permis autorisés **géolocalisés ≤ 200 m** (table `via_permits_geo`, source du signal viabilisation M-VIA), **tous états confondus, non fenêtré en temps** ;
- **la carte**, elle, ne peignait QUE la couche radar `/permis` filtrée par l'état actif (Récent/Dormant/…) et la fenêtre mois — et **jamais les permis propres à la parcelle** (`/modules/parcelle-permis` ne renvoyait aucune géométrie).

Décompte réel des 11 permis de BZ1065 (base `labuse`) :

| | valeur |
|---|---|
| permis ≤ 200 m (= la phrase) | **11** |
| dont **géolocalisés** (coordonnées présentes) | **11 / 11** |
| dont **littéralement SUR la parcelle** (`idu_codes @> BZ1065`) | **0 / 11** |
| dates | 2013 → 2023 (**les 11 ont > 24 mois** ; le plus récent = 2023-09-12) |
| états Sitadel (`raw.etat`) | 6× état 6 (achevé), 3× état 5, 2× état 2 |

**Verdict : cause (b), pas (a).** Les 11 sont bien géolocalisés — rien n'est « sans coordonnées ». Ils étaient **masqués par le filtre d'état** : le filtre « Récent » (≤ 24 mois) était actif, or les 11 datent tous de plus de 24 mois → la couche radar n'en peignait **aucun**. La phrase disait 11, la carte montrait 0. En prime, « sur cette parcelle » était faux : **0** des 11 sont sur la parcelle, les 11 sont dans le **voisinage ≤ 200 m**.

### Règle retenue et correction

Quand une parcelle est ciblée, **la carte montre EXACTEMENT les permis de la parcelle** (`/modules/parcelle-permis`, ≤ 200 m, géolocalisés), **indépendamment du filtre d'état** — la phrase « X permis » ⇒ **X points cliquables à l'écran**, toujours. Solution la plus simple et robuste : pas de bascule de filtre à faire, la carte suit la parcelle.

- **Back** (`modules.py::parcelle_permis`) : chaque item porte sa **géom 4326** (`ST_AsGeoJSON(s.geom)`, la même colonne que la carte radar) + compteurs `localises` / `non_localises`. La source ne renvoyant que du géolocalisé, `non_localises` = 0 en pratique (dit à part si jamais).
- **Front** (`ModulePanel.tsx`) : parcelle ciblée → la `featureCollection` de la carte = **les permis de la parcelle** (couleur = récence PROPRE du permis, récent ≤ 24 m vert / sinon gris, jamais le segment). Le compte affiché = les points **dessinables**. Libellé rendu honnête : **« à moins de 200 m de cette parcelle »** (voisinage, pas « sur »). 0 → « Aucun permis à moins de 200 m … sur les **240** derniers mois ».

### Preuve navigateur (filtre « Récent » ACTIF — le scénario du bug)

| | avant | après |
|---|---|---|
| phrase | « 11 permis sur cette parcelle » | « **11 permis à moins de 200 m de cette parcelle BZ 1065** — cliquez les points » |
| points sur la carte (`module-extra`) | **0** (radar filtré Récent, tous > 24 mois) | **11** (source parcelle, tous gris) |
| filtre Récent actif | oui | oui (`data-permis-seg="cours"` `aria-pressed=true`) |

`data-permis-parcelle-resultat` = 11, `module-extra._data` = **11 features `kind:permis`**. Capture : `captures/p1_bz1065_11pts_recent.png`.

---

## Point 2 — le zoom ne suit pas au changement de parcelle dans la barre

**Cause.** `MapView` calcule sa cible `cible = selectedIdu ?? focusIdu`. La barre de l'outil posait un `focusIdu` (via `focusParcelle`) mais **ne levait pas** une fiche restée ouverte (`selectedIdu`) : le `selectedIdu` d'une parcelle A cliquée **masquait** le `focusIdu` de la parcelle B cherchée → la carte restait sur A.

**Correction** (`ModulePanel.tsx`, `onSelect` + `onEnterRaw`) : `select(null)` **avant** `focusParcelle(c)`. La barre lève la sélection stale → `cible = null ?? focusIdu(B) = B` : **la barre recentre TOUJOURS**, fiche ouverte ou non.

### Constat navigateur

Parcelle A = `97411000BZ1065` (Saint-Denis), parcelle B = `97422000AV0674` (Le Tampon, ~40 km au sud).

| étape | centre carte |
|---|---|
| `select(A)` (fiche ouverte sur A) | 55.4295, −20.8852 (**A**) |
| recherche **B** dans la barre + Entrée | 55.5220, −21.2324 (**B**, exact) |

Mécanisme du bug confirmé à part : carte posée sur B, `select(A)` la **rappelle** sur A (55.4295, −20.8852) — `selectedIdu` gouverne bien le centre ; c'est cette sélection stale que le fix efface. Après : hash passe de `…&idu=BZ1065` à `…&m=permis` (fiche levée), carte sur B. Capture : `captures/p2_after_recentre_B_tampon.png`.

---

## Point 3 — « 1 bis » écrasé en « 1 »

**Cause EXACTE (pas celle attendue).** La **résolution** était déjà juste : `_sugg_adresse` renvoie le bon `idu` par ligne — « 1 bis Chemin de la Citerne » → **97411000BZ1288** (le 1 bis), « 1 » → **97411000BZ1287** (deux parcelles distinctes). C'est le **LIBELLÉ AFFICHÉ** qui perdait le rep : `label = numéro + voie` **sans le rep**. Donc « 1 bis » et « 1 » s'affichaient tous deux « 1 Chemin de la Citerne », **indistinguables**, et au clic le pick recopiait ce libellé rep-less dans la barre → l'utilisateur voyait son « 1 bis » **remplacé par « 1 »** (constat Vic). Pas un trou data, pas une normalisation trop agressive : un libellé qui laissait tomber le rep.

**Correction** (`recherche.py::_sugg_adresse`) : le libellé = `trim(concat_ws(' ', nullif(numero,''), nullif(rep,''), voie))` — **le rep est porté**, comme la fiche (`_ban_adresse`). « 1 bis » et « 1 » redeviennent distinguables ; le pick réécrit « 1 bis … » dans la barre.

### Preuve — 3 adresses de fiches avec rep (base réelle)

| adresse collée | parcelle attendue | résolue | libellé rendu |
|---|---|---|---|
| `1 bis Chemin de la Citerne, 97417 Saint-Denis` | 97411000BZ1288 | ✅ | « 1 bis Chemin de la Citerne » |
| `53 bis Rue du Cardinal, 97430 Le Tampon` | 97422000CS0802 | ✅ | « 53 bis Rue du Cardinal » |
| `41 bis Chemin Jacquemin, 97470 Saint-Benoît` | 97410000BV0696 | ✅ | « 41 bis Chemin Jacquemin » |

Le voisin **« 1 » sans rep (BZ1287) n'est JAMAIS renvoyé** pour la requête « 1 bis » (le rep discrimine : « 1 bis chemin… » n'est pas un sous-texte de « 1 chemin… »). Régression verrouillée : `tests/test_retours16_recherche.py::test_adresse_collee_depuis_fiche_retrouve_parcelle` (seed voisin « 1 » ZX0043 ajouté ; asserts : bonne parcelle, JAMAIS le voisin, libellé porte le rep, les deux distinguables).

### Constat navigateur

Frappe « 1 bis Chemin de la Citerne » → suggestions : **« 1 bis Chemin de la Citerne · 97417 Saint-Denis »** (rep visible) et « 11 bis Chemin de la Citerne · 97430 Le Tampon ». Clic sur la 1re → la barre affiche **« 1 bis Chemin de la Citerne »** (rep conservé) et la phrase cible **BZ 1288** (le 1 bis), carte sur Saint-Denis. Capture : `captures/p3_suggest_bis_kept.png`.

---

## Fichiers touchés

- `src/labuse/api/modules.py` — pt 1 (géom + `localises`/`non_localises` dans `/modules/parcelle-permis`).
- `frontend/src/components/outils/ModulePanel.tsx` — pt 1 (carte pilotée par la parcelle, phrase « ≤ 200 m » sur le compte dessinable) + pt 2 (`select(null)` avant `focusParcelle`).
- `src/labuse/api/recherche.py` — pt 3 (libellé `_sugg_adresse` porte le rep).
- `tests/test_retours16_recherche.py` — pt 3 (voisin « 1 » seedé, asserts renforcés).

## Hors mandat (non touché)

Audit complet de l'outil, ingestion Sitadel, scoring, autres outils, exports, merge.
