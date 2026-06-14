# RAPPORT — Cercle 2 « Terrain & contraintes physiques » (LA BUSE v3)

> Ce que le terrain impose AVANT de chiffrer : pente, vue, eau, domaine maritime, assainissement.
> Rapports de dispo : `RAPPORT_DISPO_2B.md`, `RAPPORT_DISPO_2D.md`, `RAPPORT_DISPO_2E.md`.
> **270 tests verts**, ruff clean, baseline 3 000.

## 2.A — Pente & exposition ✅
- **Pente CALCULÉE et AFFICHÉE** (RGE ALTI, échantillonnage altimétrique dans l'emprise) ;
  au-delà du seuil → `SOFT_FLAG` « pente forte » — **driver de coût terrassement, jamais une
  exclusion**. Seuil `seuil_flag_pct` = 30 % (placeholder, défaut Vic, affiché « non calibré »).
- **Exposition** (orientation cardinale) : gradient altimétrique N-S / E-O sur 4 points autour du
  centroïde → azimut → N/NE/E/… ; « terrain plat » sous 3 %. Affichée sur la fiche.
- **Bilan** : `majoration_vrd_pente_pct` appliquée seulement si pente ≥ 15 % (placeholder). Recette ✅.

## 2.B — Vue mer ✅
- **Viewshed v1 (ligne de vue 1D)** faute de raster/GRASS dispo (limites documentées dans
  `RAPPORT_DISPO_2B.md`) : échantillonnage RGE ALTI du centroïde vers le trait de côte, test
  d'obstruction du profil → **oui / partielle / non**. Cas spécial **front de mer** (D < 120 m).
- **Bilan** : bonus `bonus_vue_mer_pct` sur le prix de vente neuf quand vue = « oui » (placeholder).
  Cache `parcel_vue_mer` (idempotent). Recette ✅.

## 2.C — Ravines (finition C1) ✅
- La couche `ravine` existait (C1) ; finition **2.C** : quand une **surface en eau** existe (ravine
  large), la distance de recul est mesurée **AU BORD** (berge), plus proche que l'axe — sinon à
  l'**axe** du thalweg, avec mention « recul réel à vérifier ». Jamais excluante seule (`SOFT_FLAG`).
- Buffer 10 m / `search_cap_m` 60 m (placeholders). Recette ✅ (test berge dédié).

## 2.D — Zone des 50 pas géométriques ⛔ STOP
- Domaine public maritime (bande 81,20 m) = inconstructible, mais **délimitation administrative**
  (régularisations/exclusions), pas un buffer du trait de côte. **Introuvable sur toute source
  joignable** ; PEIGEO (autoritaire) bloqué. Rapport + STOP, **sans bricoler** (`RAPPORT_DISPO_2D.md`).

## 2.E — Assainissement (collectif vs autonome) ⛔ STOP
- Zonage collectif/ANC = **compétence locale (TCO)**, acte réglementaire discret, non calculable.
  **Introuvable sur toute source joignable** (data.gouv = métropole only ; Géoplateforme = 0 couche ;
  Région ODS = rien) ; PEIGEO bloqué. Rapport + STOP, **sans bricoler** (`RAPPORT_DISPO_2E.md`).

## ⛔ STOP & VALIDATE — fin Cercle 2
**3 items livrés** (2.A, 2.B, 2.C) ; **2 items en attente d'une dépendance Vic** (2.D, 2.E) — tous
deux **débloqués par le même geste : whitelister PEIGEO** (`peigeo.re/geoserver`). Dès qu'il est
joignable, les deux loaders sont directs (couches surfaciques → verdict + attribut fiche) et leurs
recettes sont déjà écrites dans les rapports de dispo.

Sur ta validation — et indépendamment du whitelist PEIGEO, qui peut venir en parallèle —
j'enchaîne le **Cercle 3** (3.A assistant IA [décision clé API attendue] → 3.B photos historiques →
3.C alertes → 3.D 3D).
