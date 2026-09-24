# GABARIT-6 — Suites de GABARIT-AUDIT-1

Exécution des 4 points de GABARIT-AUDIT-1 (rapport dans `main`). Branche `fix/gabarit-6`
depuis `main` `2d3b7213`, worktree `~/Desktop/labuse-gabarit6`, ports 8395/5595. **Non mergé.**
Un commit par point. CDC Gabarit respecté : faits sourcés seulement, jamais logements / SDP / valeur.

Captures : `docs/audit-2026-09/gabarit-6/captures/` (script rejouable `capture.mjs`, node playwright).

| # | Commit | Objet |
|---|---|---|
| P1 | `85ba0f18` | En-tête fiche : hauteur réglementaire sourcée (faîtage), plus niveaux × 3 m |
| P2 | `838e5e7c` | Outil : surface à-cheval = cadastre entier + portion servie |
| P3 | `1803a313` | Outil : afficher la liste des règles non intégrées |
| P4 | `37ecbeae` | Outil : bâti existant sur la carte (BD TOPO 2D + LiDAR HD 3D) |

---

## P1 — La hauteur d'en-tête de la fiche (le point n°1)

**Avant.** L'en-tête « Urbanisme » affichait `fourchette.hauteur_m = niveaux × étage_m`
(`engine.py:649`), avec `niveaux` compté **sur l'égout** (`engine.py:472-473`) : ⌊6/3⌋·3 = « 6 m max »
sur BW0102, ⌊4,5/3⌋·3 = « 3 m max » sur BZ1065. Une **estimation d'étages présentée comme une règle**,
qui contredisait le règlement cité (9 / 7 m faîtage) et le tiroir §10 de la même fiche.

**Après.** L'en-tête lit la **hauteur réglementaire sourcée** par la **même fonction que le tiroir §10
et l'outil** : l'endpoint `/outils/gabarit/{idu}`, via la **même clé react-query** que `<GabaritLine>`
(`['gabarit', idu]`, cache partagé → zéro requête en plus). Faîtage = le « max » ; l'égout, quand la
règle le distingue, en **sous-ligne**. Hauteur en prospect (Saint-Denis Ud) → « Non chiffrée ». Zones
A/N → inchangé (« constructibilité très limitée »).

Le calcul « niveaux » reste dans la capacité (11 étapes), jamais dans l'en-tête sous « max ».

**La fonction unique de hauteur.** `build_gabarit_input` (`builder.py:249,286-307`) lit le faîtage
`hf_m` (sinon l'égout `he_m`, cité comme tel) depuis `resolve_zone` → `regles_zone`
(`config/plu_destinations/*.yaml`, feuilles `statut: valide`). Payload enrichi :
`MaxHeight.basis` / `egoutMeters` (builder) → `GabaritResult.hauteurBase` / `hauteurEgoutM` (engine).
L'en-tête (`Fiche.tsx`), le tiroir §10 (`GabaritLine.tsx`) et l'outil (`Gabarit.tsx`) lisent le **même
payload** — en-tête = tiroir = outil par construction.

**Vérifié (moteur + app réelle) :**

| Parcelle | Zone | En-tête AVANT | En-tête APRÈS | Règlement cité |
|---|---|---|---|---|
| BW0102 | U6c | « 6 m max » | **9 m max · égout 6 m** | 9 m faîtage / 6 m égout — Art. 10.2 p.282 |
| BZ1065 | Uh | « 3 m max » | **7 m max · égout 4,5 m** | 7 m faîtage / 4,5 m égout — Art. Uh.10 p.73 |
| AK0069 | Ud | (—) | **Non chiffrée (prospect)** | prospect L ≥ H — Art. Ud.10 |

Captures : `p1-fiche-entete-BW0102.png` (« 9 m max · égout 6 m », corps « 9 m au faîtage · 6 m à
l'égout · Art. 10.2 »), `p1-fiche-entete-BZ1065.png` (« 7 m max · égout 4,5 m »).

---

## P2 — Libellé de la surface à-cheval (outil)

**Avant.** Sur une parcelle à cheval, l'outil affichait « Surface parcelle 7 465 m² » = la **portion**
de la zone constructible dominante, pas la parcelle (10 321 m² au cadastre = la valeur de la fiche).

**Après.** Quand `raccordement.zone.a_cheval` : **« Surface parcelle 10 321 m² · dont 7 465 m² en U6c
(72 %) »** — le cadastre entier d'abord (`raccordement.parcelle.surface_m2`, préservé avant le
découpage), la portion constructible en sous-ligne avec sa zone et son %. Mono-zone : une seule ligne,
inchangée. **Aucun calcul modifié** (zone d'implantation / plafond restent sur le morceau constructible).
Appliqué aussi au tiroir §10 (`GabaritLine`).

Capture : `p2-outil-BW0102-panneau.png` (« 10 321 m² · dont 7 465 m² en U6c (72 %) »).

---

## P3 — La liste des règles non intégrées (outil)

**Avant.** Le compte « N règles non intégrées » s'affichait ; la liste était déjà dans la charge utile
(`nonIntegratedRules`), non rendue.

**Après.** Sous le compte, une liste **repliable, ouverte par défaut si N ≥ 1** : nom · **pourquoi**
(souvent avec la citation PLU) · source (document — zone — article). Payload : `NonIntegratedRule.detail`
propagé depuis `ApplicableRule.detail` (engine). **Rien d'inventé** — exactement ce que le moteur renvoie.

Vérifié sur Ud (AK0069, capture `p3-outil-Ud-AK0069-panneau.png`) — 4 règles listées :
- **Hauteur réglementaire (prospect L ≥ H)** — « non chiffrée — En secteur Ud : … prospect L ≥ H … »
  — PLU — Saint-Denis — Ud ;
- **Stationnement** / **Espaces libres** — « Règle connue, non chiffrée » — PLU — Saint-Denis — Ud ;
- **PPR — analyse** — « Aucun risque PPR/aléa intersecté. » — PPR — zonage réglementaire.

---

## P4 — Le bâti existant sur la carte du gabarit (outil)

**Avant.** L'outil dessinait où l'on **peut** construire, jamais ce qui est **déjà là** (BZ1065 :
bâtiments invisibles).

**Après.** L'endpoint sert `batiExistantGeoJSON` (nouveau champ) : l'emprise **BD TOPO**
(`spatial_layers` kind=`batiment`) des bâtiments majoritairement sur la parcelle (≥ 50 % de leur
emprise, ou ≥ 20 m² intersectés — écarte les débords de voisins), chacun avec sa **hauteur mesurée**
(LiDAR HD faîtage `batiment_hauteur_lidar`, à défaut la hauteur BD TOPO). **Fait contextuel** : aucun
calcul réglementaire n'en dépend (CDC §3). Sur la carte : surimpression **2D** (emprise grise + contour)
+ extrusion **3D** à la hauteur mesurée, couche **distincte** de l'enveloppe réglementaire (vert).
Légende « Bâti existant (BD TOPO · LiDAR HD) ». Servi que le calcul soit complet ou incomplet.

**Vérifié (endpoint) :** BZ1065 → **3 emprises BD TOPO**, hauteur LiDAR faîtage **10,3 m** ; BW0102 /
AV0055 (nues) → **aucun bâti** (rien dessiné).

Captures : `p4-outil-BZ1065-carte-2d.png` — la zone d'implantation (vert), le retrait (ambre) et **deux
emprises de bâti (gris + contour)** à l'intérieur ; `p4-outil-BZ1065-panneau.png` — panneau complet ;
`p4-outil-BZ1065-carte-3d.png` — 3D active, légende « Bâti existant (BD TOPO · LiDAR HD) » +
« Enveloppe réglementaire … (hauteur sourcée 7 m) ».

> ⚠ **Limite de capture (pas de code) :** en Chromium **headless**, le relief 3D (terrain WebGL/DEM) ne
> rasterise pas les couches vectorielles du gabarit — le plan 3D ressort sombre. Le **plan 2D** montre
> nettement le bâti ; la **légende du plan 3D** confirme le branchement (couche bâti + extrusion à la
> hauteur sourcée) ; l'**endpoint** prouve la donnée (3 bâtiments, LiDAR 10,3 m). L'extrusion 3D
> (`fill-extrusion` à `hauteur_m`) est ajoutée par une couche dédiée `gabarit-bati-3d` (code + tsc verts).

---

## Vérification

| Contrôle | Résultat |
|---|---|
| `tsc -b` (frontend) | ✅ 0 erreur |
| `vite build` | ✅ built |
| `vitest run` | ✅ **182 / 182** (45 fichiers) |
| `pytest -k gabarit` | ✅ **84 passed**, 1 skipped |
| Portée : `git diff` de mes 4 commits | 8 fichiers (gabarit + fiche), **0 fichier hors périmètre** |

**Non-régression notée (hors périmètre) :** `tests/test_facturation.py::test_flash_fulfillment_reel`
échoue, mais c'est un **bug préexistant sur `main`** — `NameError: _cause_zone` à `app.py:5324`
(dead reference laissée par le lot FAISABILITE-clip, le garde « dominante A/N » ayant été retiré). Il
fait **500 la fiche `/parcels/{idu}`**. Fichier non touché par mes commits (vérifié : présent identique
au merge-base `2d3b7213`). Pour capturer l'en-tête P1 en app réelle, ce bug a été neutralisé **par une
correction temporaire d'1 ligne (`"cause": None`), RÉVERTÉE avant tout commit** (aucun de mes 4 commits
ne touche `app.py`). **Recommandation à Vic : corriger `_cause_zone` → `None` sur `main`** (1 ligne, la
fiche 500 en production sinon — déjà signalé dans FICHE-AUDIT-2).

## Hors mandat (non traité)
Unifier les deux moteurs de géométrie (zone d'implantation vs assiette clippée — dette notée) · ER/EBC/
SUP déduits · classification des limites · exports · merger.
