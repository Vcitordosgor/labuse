# RAPPORT GABARIT-4 — Silence sourcé, renvois, multi-zones

Branche `feat/gabarit-4` (depuis `feat/gabarit-3`, non mergée), worktree `~/Desktop/labuse-gabarit`,
ports API 8125 / Vite 5325. 7 commits (A→F + rapport), **aucun merge**, aucun `residuel-serve`.
Références : `A0-4-MESURE.md`, ventilation du 22/09.

## Verdict

**Seuil ≥ 75 % servies ET 0 faux : ATTEINT.** Couverture **135 / 170 (79 %)**, **0 faux**.
Progression : GABARIT-3 **47 %** → GABARIT-4 **79 %** (**+55 parcelles servies**).

## Principe ajouté au CDC

**Un silence prouvé du règlement est une donnée sourcée** (comme un zéro explicite, CDC §3) : il se
sert (« non réglementé »), il ne bloque pas, il ne laisse jamais croire qu'on peut construire partout.

## Mesure 170 — avant / après

| | GABARIT-3 | **GABARIT-4** |
|---|---|---|
| Servies | 80 (47 %) | **135 (79 %)** |
| FAUX servis | 0 | **0** |
| Servies / atteignables | 84 % | **85 %** |

Causes de blocage restantes (35) : enclave/voie privée E2 (12), zone non calibrée (10), limite non
qualifiée hors emprise publique (9), recul non validé (3), hauteur non validée hors prospect (1).

## Ce que chaque lot a débloqué

- **A — CES `absent` (~48 parcelles)** : le cas dominant. Quand le règlement ne fixe pas de CES
  (`_feuille_absente` via `regles_zone` : 124 zones sur ~334 n'en fixent aucun), le plafond est servi
  **« Non réglementé »** (`maxFootprint.status='absent'`, `plafondEmpriseM2=null`, jamais 0 ni 100 %),
  la zone d'implantation est calculée normalement, couverture « ✓ Emprise vérifiée — sans plafond ».
  `absent` n'est accepté que si `zonage.py`/le YAML le rend explicite (jamais par défaut).
- **B — renvoi / silence total** : le renvoi AU→U (déjà résolu par `zonage.py`, `via_renvoi`) est
  surfacé ; une zone sans aucune règle d'implantation (Le Port Uv : destinations réglées, forme bâtie
  non réglée) est bloquée avec un motif clair « zone <X> sans règles d'implantation propres » au lieu
  du trompeur « CES non validée ».
- **C — hauteur en prospect (Saint-Denis Ud)** : quand `hauteur.faitage` est validée mais non chiffrée
  (prospect L ≥ H, `_feuille_forme_hors_schema`), `maxHeight.status='not_integrated'`, `meters=null` :
  le **2D est servi** (reculs, exclusions, zone, plafond), hauteur « Non chiffrée » listée en règles
  non intégrées, **3D indisponible**. Aucun calcul de H depuis L.
- **D — multi-zones (6/7)** : parcelle à cheval découpée par `plu_gpu_zone` (`_multizone_split`,
  morceaux ≥ 5 %, bandes < 5 % signalées). Une zone A/N = **non constructible (0 valide, exclue), pas
  un blocage** ; une seule zone constructible → le gabarit est calculé sur ce morceau (la coupure
  interne devient une séparative via `sub_geom_wkt` + `extra_neighbors_wkt`). ≥ 2 zones constructibles
  distinctes → différé (GABARIT-5).

## Contrat / moteur (fichiers)

`contract.py` : `MaxFootprint.status` ('absent'), `MaxHeight.status` ('not_integrated'),
`GabaritResult.plafondEmpriseStatus`/`hauteurStatus`. `validate.py` : accepte les silences sourcés ;
une hauteur non intégrée n'est pas « utilisée ». `engine.py` : plafond null si absent, hauteur null si
prospect (3D coupée), couvertures nuancées. `builder.py` : `_feuille_absente`/`_feuille_forme_hors_schema`,
renvoi, `_multizone_split`, classification du morceau constructible. `limites.py` : override de
géométrie + voisins de coupure, gestion MultiPolygon. Front : `Gabarit.tsx` + `GabaritLine.tsx`
(« Non réglementé » / « Non chiffrée », 3D indispo) + `api.ts`.

## Commandes et résultats

| Contrôle | Commande | Résultat |
|---|---|---|
| Mesure 170 | `gabarit_a0_3_mesure.py` | **135 servies (79 %), 0 faux** |
| Tests | `pytest tests/gabarit/` | **53 passés** |
| Registre | `registre.verifier()` | **0** |
| Types / build front | `tsc -b` · `vite build` | verts |
| Lint | `ruff check` | All checks passed |
| Recette | Playwright 8125/5325 | §ci-dessous |

## Recette (`captures/gabarit-4/`)

- **recette-01** `97422000AY0953` (Le Tampon Uc) : plafond **« Non réglementé »** + « pas de règle
  d'emprise au sol » ; couverture « ✓ Emprise vérifiée — sans plafond ».
- **recette-02** `97411000BE0476` (Saint-Denis Ud) : hauteur **« Non chiffrée »** (prospect L ≥ H) ;
  2D servie (zone 609, plafond 899) ; « 3D indisponible — hauteur non chiffrée ».
- **recette-03** `97411000CD1318` : multi-zone Uh + N **servie** (516 m² parcelle, zone 165 ; partie N
  exclue, non constructible).
- **recette-04** : tiroir fiche §10 rend **« Non réglementé »**.
- `97407000AL0484` (Le Port Uv) : bloc **« zone sans règles d'implantation propres »** (silence total).
- `97411000IE0153` (805/394/483/13) et `97411000HD0281` **inchangées** — aucune régression.

## Arbitrages CC

1. **Silence CES = donnée sourcée** → servi « non réglementé » (extension CDC §3 actée par le mandat).
   50/51 des ex-blocages « CES » étaient un silence, pas une donnée manquante.
2. **Zone A/N d'une parcelle à cheval = non constructible (0), pas un blocage** (raffinement du « un
   morceau bloque, tout bloque » : un morceau non constructible est un 0 valide). C'est ce qui sert les
   7 parcelles U+N (toutes les multi-zones de l'échantillon sont U+naturel, aucune U+U).
3. **Marge route conservée à 4,0 m** (GABARIT-3), 0 faux maintenu.
4. **≥ 2 zones constructibles** (découpage multi-CES) : différé GABARIT-5 (0 cas dans l'échantillon).

## Limites connues

- `97402000AB0268` : morceau constructible dégénéré (MultiPolygon fin) → reste « incomplet » (motif
  technique). 1 parcelle.
- « Recul voie sans objet » d'une enclave n'apparaît pas dans « Règles appliquées » (moteur : seules
  les règles à géométrie servie y figurent) — cosmétique.

## Hors mandat / restant

Calcul de H depuis le prospect · conversion R+n · calibrage des 10 zones non résolues · découpage
multi-CES (≥ 2 zones constructibles) · surface de route BD TOPO (P2 / limites non qualifiées) · E2
(voies privées) · exports · merge · `residuel-serve` · suite pytest complète (Vic).
