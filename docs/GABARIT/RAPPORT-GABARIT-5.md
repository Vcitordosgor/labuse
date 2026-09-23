# RAPPORT GABARIT-5 — Voies privées et exports

Branche `feat/gabarit-5` (depuis `feat/gabarit-4`, non mergée), worktree `~/Desktop/labuse-gabarit`,
ports API 8125 / Vite 5325. **Aucun merge, aucun `residuel-serve`.** Un commit par lot.
Références : `A0-5-MESURE.md`, `captures/gabarit-5/`.

## Verdict

- **Lot A (voies privées E2)** — couverture **135 → 143 / 170 (79 % → 84 %)**, **+8**, **0 faux**,
  **0 régression**. Le mécanisme « voie privée par citation PLU » est implanté et prouvé (tests), mais
  **inert sur la calibration actuelle** : aucune zone ne vise les voies privées avec un recul chiffré.
- **Lots B–D (exports)** — le tiroir §10 « Gabarit réglementaire » est désormais **déclaré** dans la
  fiche (V5d vert) et **mirroré** dans le Dossier / Flash + servi au **Pré-dossier PC** (page dédiée),
  plan 2D SVG compris. `registre.verifier() = 0`, `tsc -b` + `vite build` verts.

## Lot A — la règle vient du texte (comme GABARIT-3 lot C)

### Principe
Une **parcelle de voie privée cadastrée** (E2) dessert une enclave. Le recul applicable sur cette
façade n'est réglé que si le règlement de la zone **vise les voies privées**. GABARIT-5 :
1. **détecte** la parcelle de voie privée par trois critères obligatoires (aucun seul ne suffit) ;
2. **sert** l'arête en `road` **si** la citation `retraits.voie` de la (commune, zone) vise les voies
   privées → `source.provider = "LABUSE — parcelle de voie privée (cadastre) + citation PLU art. X"` ;
3. **sinon bloque** avec le motif honnête « desservie par une voie privée : le règlement ne précise pas
   le recul » (silence prouvé, jamais un recul inventé).

### Les trois critères (`limites.is_private_road_parcel`, pur, testé)
Une parcelle voisine collée (≤ 0,5 m) est une voie privée ssi :
1. **sans bâti** (aucun bâtiment BD TOPO ne l'intersecte) ;
2. **allongée ET étroite** — enveloppe orientée (`ST_OrientedEnvelope`) L/l ≥ 5 **et** largeur ≤ 6 m
   (un chemin d'accès, pas un lot allongé) ;
3. **raccordée au réseau BD TOPO à une extrémité sans le traverser** — à ≤ 6 m d'un tronçon carrossable
   (l'axe BD TOPO est au centre de chaussée : le débouché d'un chemin est à ~ demi-chaussée + accotement)
   mais aucun axe ne la parcourt sur > 3 m (sinon c'est une parcelle-voirie, déjà traitée).

### Tableau commune × citation « voies privées » (`captures/gabarit-5/citations-voie.csv`)
318 feuilles `retraits.voie` calibrées, 23 communes. Combien de zones dont la citation **validée** vise
« voies et emprises **publiques** » (ep) et « voies **privées** » (vp) :

| Commune | zones | ep | vp | Commune | zones | ep | vp |
|---|---|---|---|---|---|---|---|
| Les Avirons | 19 | 0 | 0 | Saint-Denis | 10 | 2 | 0 |
| Bras-Panon | 14 | 0 | 0 | Saint-Joseph | 24 | 1 | 0 |
| L'Entre-Deux | 5 | 0 | 0 | Saint-Leu | 7 | 2 | 0 |
| L'Étang-Salé | 12 | 0 | 0 | Saint-Louis | 17 | 0 | 0 |
| Petite-Île | 15 | 0 | 0 | **Saint-Paul** | 31 | **25** | 0 |
| La Plaine-des-Palmistes | 9 | 0 | 0 | Saint-Pierre | 26 | 0 | 0 |
| Le Port | 13 | 3 | 0 | Sainte-Marie | 19 | 0 | 0 |
| La Possession | 22 | 0 | 0 | Sainte-Rose | 9 | 0 | 0 |
| Saint-André | 7 | 2 | 0 | Sainte-Suzanne | 12 | 0 | 0 |
| Saint-Benoît | 5 | 0 | 0 | Salazie | 10 | 0 | 0 |
| Le Tampon | 15 | 0 | 0 | Les Trois-Bassins | 9 | 0 | 0 |
| Cilaos | 8 | 0 | 0 | Les Avirons… | | | |

**`vp` = 0 partout.** La seule citation « voies publiques **ou privées** » (Saint-Benoît Ua/Ub) est
`statut: propose` (non validée) **et** dit « l'implantation n'est pas réglementée » (aucun recul
chiffré). Le garde validées-only (GABARIT-3) l'écarte. → **Le mécanisme voie privée est inert sur la
calibration servie** — parallèle exact du mécanisme « emprises publiques » (GABARIT-3 : `ep` présent
mais jamais cumulé à un PLU complet). Il servira dès qu'une calibration gravera un recul de voie privée
validé.

### Mesure des 32 (12 E2 + 20 lotissement) — 0 faux
Audit des arêtes servies « road » (BD TOPO **et** voie privée) : chacune doit longer une route
carrossable / une parcelle-voirie / une parcelle de voie privée réellement détectée.

- **12 E2** (ex-« enclave / voie privée » de GABARIT-4) : **4 bloquées** (voie privée détectée, citation
  absente → motif honnête) · **8 servies E1** (voisin élancé non qualifiant → vraie enclave) ·
  **0 servie par citation** · **0 faux**.
- **20 lotissement** (une par commune, `_lotissement_sample`, voisin de voie privée détecté) :
  **6 servies · 3 bloquées E2** (voie privée, citation absente) · 11 bloquées pour un autre motif PLU
  (zone non calibrée, limite non qualifiée…) · **0 faux**.

Captures ortho par parcelle : `captures/gabarit-5/a5-voiepriv-<idu>.png` (contour, voirie BD TOPO,
parcelle de voie privée détectée en orange, arêtes classées, verdict servi/bloqué).

### Anti-régression : le width-cap
Sans plafond de largeur, la détection prenait des **lots allongés** pour des voies privées :
`97411000CH0196` — la parcelle de la recette E1 de GABARIT-3 — bordée de deux parcelles de 631 / 789 m²
(~10 m de large) était bloquée à tort. Le plafond largeur ≤ 6 m sépare les chemins (3–4 m) des lots
(≥ 10 m) → **CH0196 reste servie**, 0 régression sur les 170.

## Lots B–D — le gabarit déclaré, mirroré, servi aux exports

### Lot B — déclaré dans la fiche (V5d)
Le tiroir §10 (codé au rendu, `GabaritLine.tsx`) devient une **surface déclarée**
(`declarations/fiche/sections_restantes.yaml` → `fiche_parcelle_gabarit`, section Potentiel) : zone
d'implantation, plafond d'emprise, hauteur (citée du §4), couverture, motif de blocage, et le **plan 2D**
comme figure. 3 données ajoutées au registre (`gabarit_hauteur_m`, `gabarit_motif_blocage`,
`gabarit_plan_2d`, servies par `outil_gabarit`), un extracteur par ligne (`robinet_fiche.py`, lit la
base comme `n_permis_proximite`, mémoïsé par session), nouveau format `figure`. La surface parcelle
n'est **pas doublée** ; la hauteur PLU reste au §4, le tiroir la **cite**. Toutes les lignes sont
`masquer_si_absent` → parcelle bloquée : **le motif seul s'imprime**. `registre.verifier() = 0`, V5d vert
(69 données maille parcelle déclarées, 70 lignes du Dossier miroir toutes déclarées).

### Lot C — Dossier / Flash §10 (miroir)
Par construction du miroir, les lignes apparaissent en §10. Le **plan 2D SVG** est généré serveur
(`gabarit/plan_svg.py`, miroir exact du mini-plan React : mêmes couleurs, même projection) et rendu par
WeasyPrint (`_r_gabarit_plan`, bloc pleine largeur, légende « Zone d'implantation réglementaire —
schéma, pas un plan de masse »). Vérifié sur témoins : `97411000IE0153` (394 / 483 / 13 m, couverture
4/4) · `97422000AY0953` **« Non réglementé »** · `97411000BE0476` **« Non chiffrée »** · `97407000AM1059`
bloquée → **motif seul, aucun chiffre**. `recette_exports1.py` étendu (`verifier_gabarit_temoins`) :
§10 PDF = tiroir `/outils/gabarit/{idu}` (écran = Dossier).

### Lot D — Pré-dossier PC
Nouvelle pièce `{idu}-labuse-enveloppe-reglementaire.pdf` : **« Enveloppe réglementaire selon les règles
intégrées »** — le même SVG (agrandi) + les 4 chiffres + règles appliquées / non intégrées + sources.
Titre + phrase disent que c'est une **aide à la lecture, pas un plan de masse**. Gabarit **bloqué → la
page n'est pas produite** et le LISEZMOI ne la cite pas (vérifié : IE0153 la produit + la cite, AM1059
ne la produit pas). Apporteur / Financier : **rien** (hors mandat).

## Fichiers

- Moteur : `src/labuse/gabarit/limites.py` (détection + classification), `builder.py` (branchement,
  flag `private_road`, sources voie privée), `plan_svg.py` (SVG serveur, **nouveau**).
- Exports : `src/labuse/exports/robinet_fiche.py` (extracteurs gabarit), `miroir.py` (rendeur figure),
  `src/labuse/api/pre_dossier.py` (page enveloppe).
- Registre / déclarations : `registre/donnees.py`, `robinets.py`, `declarations.py` (format `figure`),
  `declarations/fiche/sections_restantes.yaml`.
- Tests : `tests/gabarit/test_limites.py`, `test_builder.py`, `test_plan_svg.py`,
  `test_declaration_fiche.py`, `test_enveloppe_predossier.py`.
- Scripts / recette : `scripts/gabarit_a0_5_mesure.py`, `gabarit_a0_5_captures.py`,
  `scripts/recette_exports1.py` (étendu). Sorties : `docs/GABARIT/captures/gabarit-5/`.

## Commandes et résultats

- `pytest tests/gabarit/` → **69 passés**.
- `registre.verifier()` → **0** ; `declarations.verifier()` → 0 violation (16 orphelins `couche_*`
  pré-existants) ; verrou **V5d vert**.
- `tsc -b` → 0 ; `vite build` → OK.
- `scripts/gabarit_a0_5_mesure.py` → 170 : **143 servies (84 %), 0 faux, 0 régression** ; 12 E2 (4 bloc /
  8 E1) ; 20 lotissement (0 faux).
- Dossier / Flash / Pré-dossier générés sur les 4 témoins (PDF ouverts, `pdftotext` = tiroir écran).

## Arbitrages de CC

1. **Trois critères + un 4e garde-fou (largeur ≤ 6 m).** Le mandat pose 3 critères ; la largeur est un
   raffinement **nécessaire** pour ne pas prendre un lot allongé pour un chemin (sinon régression
   CH0196). Mesuré : chemins réels 3–4 m, faux positifs 10–11 m → seuil 6 m net.
2. **Seuil de raccordement 6 m** (et non « touche à 0 m »). La BD TOPO donne l'**axe** ; le débouché d'un
   chemin est à ~ demi-chaussée + accotement (mesuré 5,3 m sur AM1058). Aligné sur la portée-façade de la
   classification voie (demi-chaussée 2 m + marge 4 m). Sans cela, tous les débouchés réels sont manqués.
3. **Portée aux enclaves seules.** La reclassification voie-privée n'agit que sur les parcelles **sans
   façade publique** (comme l'ancien `_has_chemin_neighbor`) → une parcelle desservie qui borde un chemin
   privé garde ce côté en **séparative** : aucune régression sur le desservi.
4. **Bloc E2 même sans citation.** Détecter une voie privée + citation absente **bloque** (motif honnête)
   plutôt que servir une E1 trompeuse « recul voie sans objet » — fidèle au silence sourcé du CDC.
5. **Mécanisme inert assumé et dit.** Comme GABARIT-3 pour les emprises publiques : le code est prouvé
   par les tests unitaires, la calibration ne l'active pas encore. On le documente, on ne triche pas.
6. **`figure` : nouveau format déclaratif + SVG serveur.** Plutôt qu'une image rasterisée, un SVG (miroir
   exact du React) rendu par WeasyPrint — vectoriel, léger, écran = PDF.

## Hors mandat (inchangé)

Zones non calibrées (10), limites hors emprise publique (9), recul non validé (3), hauteur non validée
hors prospect (1) ; calcul de H depuis le prospect ; surface de route BD TOPO ; Apporteur / Financier ;
merge ; `residuel-serve` ; suite pytest complète (Vic).
