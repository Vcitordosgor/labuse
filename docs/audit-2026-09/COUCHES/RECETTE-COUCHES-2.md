# RECETTE — COUCHES-2 (reliquat du travail 22 + ZFANG/FRR)
**Branche :** `fix/couches-2` (tirée de `fix/couches-1` — le reliquat s'appuie sur geom_simple livré là ;
rebasable sur main si Vic préfère l'indépendance) · **API** worktree :8020 · **Front** :5175 · CC ne merge pas.

> Captures WebGL non capturables par l'outil (plafond 5 s < repeinte relief 3D) → **render-proof**
> (queryRenderedFeatures / DOM / réseau) ; app laissée sur :5175 pour les pixels de Vic (points 1, 2, 4-carte).

---

## Point 1 — Seuils de zoom par couche

**Les seuils EXISTENT déjà** pour les couches qui en ont besoin (preuve fichier:ligne) — RIEN à re-déclarer :

| Couche | Seuil | Preuve |
|--------|-------|--------|
| Équipements OSM | minzoom 12 | `MapView.tsx:1429` |
| Équipements INSEE BPE | minzoom 12 | `MapView.tsx:1440` |
| Arrêts de transport | minzoom 11 | `MapView.tsx:1039` |
| Étiquettes de zone (parcelle + île) | minzoom 14 | `MapView.tsx:1181`, `:1227` |
| Tuiles vectorielles zonage / PPR | minzoom 8 (source) | `MapView.tsx:1188`, `:1190` |
| Parcelles île (MVT) | minzoom 9 (source) | `MapView.tsx:1205` |
| Ortho récente | minzoom 12 | `MapView.tsx:941` |

**Symptôme traité — décision Vic : garder la vue d'ensemble, corriger le bandeau.** L'aplat zonage par
FAMILLE à l'échelle île est la vitrine assumée de la couche (raison d'être documentée, gravée COUCHES-1).
Le défaut réel était le **bandeau qui mentait**. Correctif (`MapView.tsx:2254`, `data-carte-banner`) :

- Couche zonage éteinte (rien de peint) → `« Zoomez ou cliquez une commune pour voir ses parcelles »` (inchangé).
- Zonage qui peint déjà l'aperçu île (`zonageFill`) → `« Vue d'ensemble par zone PLU — zoomez ou cliquez une
  commune pour le détail parcelle »`.

**Preuve** (render-proof à z 9,18) : bandeau **avant** = « Zoomez… pour voir ses parcelles » ; **après**
allumage du zonage = « Vue d'ensemble par zone PLU — … pour le détail parcelle ». Plus de contradiction.

---

## Point 2 — État de chargement visible

Allumer une couche déclenche sa requête `['layer', …]` ; l'écran restait muet pendant l'attente (geom_simple
a raccourci, pas supprimé le geste). Correctif : `useIsFetching({ queryKey: ['layer'] })` alimente le bandeau
de chargement existant (`MapView.tsx:2233`, `data-carte-loading`), libellé prioritaire **parcelles > couche >
carte**. **Preuve** : au 1er allumage d'une couche (RPG, non caché), le libellé **« Chargement de la couche… »**
apparaît, puis « Chargement de la carte » (repeinte tuiles).

---

## Point 3 — Procédure de matérialisation geom_simple en prod

Écrite dans **`docs/audit-2026-09/COUCHES/DEPLOY-geom-simple.md`** (rien exécuté en prod) : contexte, nature
(UPDATE non destructif idempotent, colonne NULL, pas de migration), ORDRE, commande SQL (transaction +
lock_timeout, variante par couche), durée attendue (quelques s à ~2 min, poste lourd safer 38 460), 3
vérifications, rollback.

---

## Point 4 — ZFANG / FRR : carte ET attribut, une seule source

**Source unique = `territoire_fiscal_commune` / `territoire_fiscal.attributs_commune`.** Les trois usages en
dérivent, jamais trois calculs :
- **Carte** : polygones `spatial_layers` zfang/frr **construits depuis cette table** (`ingestion/dispositifs.py`).
- **Fiche commune** : `attributs_commune` (via `fiche_commune.zfang_frr`).
- **Filtre** : `EXISTS` sur `territoire_fiscal_commune` (jointure INSEE = `left(idu,5)`).

**Carte** — opacité TRÈS BASSE : `dispoFillOpacity` 0,16/0,18 → **0,10/0,12** ; empilement : ZFANG/FRR
descendus tout en bas de la pile vectorielle (`_bas` = communes-bounds/parcels-base). Off par défaut (déjà,
`useApp.ts`). **Preuve** : fill-opacity `ov-zfang`/`ov-frr` = 0,10 ; tous les calques structurels
(communes-bounds, parcels-base, ile-base, parcels-limites, ile-limites) **au-dessus** → cadastre et limites
de communes lisibles. Capture avant/après = Vic (WebGL).

**Fiche commune** — bloc « ZFANG / FRR (dispositifs fiscaux) », statut EXACT + source :
ligne **ZFANG** (Régime renforcé / standard) et ligne **FRR** (Classée en totalité / en partie / Hors
dispositif). Back : `fiche_commune.zfang_frr` + build/_FALLBACK + payload cache `_compute_commune_contexte`.
Front : type `ContexteCommune.zfang_frr` + LigneCarte `ContextePanel`. **Preuve** : Salazie → « ZFANG
renforcée » à l'écran ; back sert `zfang=renforce, frr=totalite`. ⚠ En prod le bloc apparaît après le job
nocturne `fiche-commune-cache` (comme tout ajout de bloc fiche commune) — cache reconstruit en recette.

**Filtre** — `/filtre?zfang=<renforce|standard>&frr=<totalite|partie|hors>` (CSV). Back : `_q_v2_where` +
`FiltreCriteres` (champ + `where()` + `cache_key()`). Front : `Filters.zfangRegime`/`frrClassement` +
`EMPTY_FILTERS` + `filterParams` + `ChipGroup` (section « ZFANG — zone franche » / « FRR — ruralités »).
**Preuve** (comptes sur run q_v11_m137, total 430 813) :

| Filtre | Parcelles |
|--------|-----------|
| aucun | 430 813 |
| `zfang=renforce` | 70 018 |
| `zfang=standard` | 360 795 |
| `frr=totalite` | 20 033 |
| `frr=hors` | 10 112 |

Réseau : le clic « Renforcée » envoie bien `/filtre?…&zfang=renforce` (200).

---

## Gates

tsc 0 · vitest 191/191 (44 fichiers) · pytest ciblé (geom/layer/map ; fiche_commune/contexte/filtre/
territoire/fiscal/dispositif) vert (skips = env). 4 commits, non mergés.
