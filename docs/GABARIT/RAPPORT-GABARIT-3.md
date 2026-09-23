# RAPPORT GABARIT-3 — Couverture : servir les enclaves et les emprises publiques

Branche `feat/gabarit-3` (depuis `feat/gabarit-2`, non mergée), worktree `~/Desktop/labuse-gabarit`,
ports API 8125 / Vite 5325. 8 commits (A→F + rapport), **aucun merge**, aucun `residuel-serve`.
Références : `A0-2-MESURE.md`, `A0-3-MESURE.md`.

## Verdict

**Seuil ≥ 90 % servies : NON ATTEINT. 0 faux : OUI. → STOP + rapport (comme prévu au lot E).**
La couverture globale est **47 % (80/170)**. Le blocage n'est **pas** les limites : **44 % des
parcelles (75/170) bloquent sur la complétude du PLU** (CES/hauteur non validées, zone non calibrée,
multi-zone) — **hors du périmètre de ce mandat**. Parmi les **95 parcelles qui atteignent l'étape
limites** (PLU complet, zone unique), **84 % servent** — c'est le plafond que le travail limites peut
atteindre, et il est quasi atteint, à 0 faux.

## 1. Les 28 bloquées d'A0-2 par cause (lot A)

| Cause | n | Levier |
|---|---|---|
| E1 enclave vraie | 14 | **débloqué** (lot B : séparatives seules) |
| P2 route à la marge | 6 | marge 3,5→4,0 (lot D) + emprise publique (lot C) ; reste bloqué si PLU incomplet |
| P1 emprise publique | 5 | **débloqué SI** citation « emprises publiques » + PLU complet (lot C) |
| P1 ravine / littoral | 2 | idem P1 + règle ravine `not_integrated` |
| E2 chemin privé cadastré | 1 | bloqué sauf citation « voies privées » |

## 2. Ce que chaque lot a débloqué

- **Lot B — enclaves E1** : une parcelle sans façade mais entourée de parcelles bâties est servie en
  **séparatives seules** (recul limites partout), recul voie déclaré « sans objet ». E2 (voisin chemin
  privé cadastré, `_has_chemin_neighbor`) reste bloquée « accès par voie privée non qualifiée » sauf
  citation. Recette : **CH0196 servie zone 69 m²** (bloquée en GABARIT-2).
- **Lot C — emprises publiques** : une arête ouverte (ni voisin ni route) devient une **voie** si la
  citation validée `retraits.voie` de la zone vise « voies **et emprises publiques** » (`_voie_citation_flags`
  via `regles_zone`), source dédiée « LABUSE — cadastre (non cadastré = domaine public) + citation PLU
  art. X ». Ravine/littoral longé → règle `not_integrated` « recul ravine non chiffré », calcul inchangé.
  **Aucune règle inventée** : tout vient du texte validé.
- **Lot D — route à la marge** : marge portée **3,5 → 4,0 m** (capte les frontages à ~5,6 m de l'axe,
  ex. AE0256), **audité 0 faux-voie** sur les 70 ET sur 100 parcelles. Surface de route BD TOPO absente
  de la base (→ GABARIT-4).

## 3. Mesure finale (lot E, 170 = 100 tirées + 70 d'A0-2, via le builder complet)

| | n | % |
|---|---|---|
| Servies | 80 | 47 % |
| Bloquées | 90 | 53 % |
| **FAUX servis** | **0** | audit voie/séparative largeur-aware + parcelle-voirie |

| Cause de blocage | n | Périmètre |
|---|---|---|
| PLU : CES (emprise) non validée | 51 | **hors GABARIT-3** |
| PLU : zone non calibrée | 10 | hors GABARIT-3 |
| PLU : hauteur non validée | 7 | hors GABARIT-3 |
| multi-zone | 7 | hors GABARIT-3 |
| enclave / voie privée (E2) | 8 | limites |
| limite non qualifiée (emprise non couverte) | 6 | limites |
| recul non validé | 1 | PLU |

**Atteignables (hors verrou PLU/multizone) = 95 → 80 servies = 84 %.**

## 4. Causes restantes chiffrées

1. **Validation PLU du CES (emprise au sol) : 51/170 (30 %)** — le blocage n°1, et de loin.
2. Zones non calibrées (10) et hauteur non validée (7).
3. Multi-zone (7) — découpage non fait (bloquant assumé GABARIT-1).
4. Limites : E2 chemin privé (8, dont la plupart bloquent aussi sur le PLU), emprise non couverte (6).

**Constat structurant** : **0 zone** ne cumule aujourd'hui la citation « emprises publiques » ET un PLU
complet (CES + hauteur validés). Le mécanisme du lot C est donc **correct et unit-testé mais inerte sur
données réelles** tant que le CES/la hauteur de ces zones ne sont pas validés. Le levier des ~44 %
restants est un mandat **PLU-calibrage** (valider CES + hauteur par citation), pas la classification des
limites. Recommandé aussi : ingérer la **surface de route BD TOPO** (tranche P2 sans marge) et le
**découpage multi-zone**.

## 5. Fichiers

Modifiés : `src/labuse/gabarit/limites.py` (flag `emprises_publiques`, `Edge.source_kind`, marge 4,0,
`summarize_edges`), `src/labuse/gabarit/builder.py` (E1/E2, citations `_voie_citation_flags`,
emprise-publique, ravine `_touche_ravine`, `regles_zone`). Créés : `scripts/gabarit_a0_3_mesure.py`,
`docs/GABARIT/A0-3-MESURE.md`, `docs/GABARIT/RAPPORT-GABARIT-3.md`, `docs/GABARIT/captures/gabarit-3/`.
Tests : `tests/gabarit/test_limites.py` + `test_builder.py` (48 verts).

## 6. Commandes et résultats

| Contrôle | Commande | Résultat |
|---|---|---|
| Classement 28 | diagnostic géométrique | 14 E1 · 6 P2 · 7 P1 · 1 E2 |
| Marge 4,0 auditée | audit faux-voie 70 + 100 | **0 faux** |
| Mesure finale | `gabarit_a0_3_mesure.py` | 80/170 servies (47 %), **0 faux** |
| Tests | `pytest tests/gabarit/` | **48 passés** |
| Registre | `registre.verifier()` | **0** |
| Types front | `tsc -b` | 0 erreur |
| Lint | `ruff check` | All checks passed |
| Recette | Playwright 8125/5325 | §7 |

## 7. Recette navigateur (`captures/gabarit-3/`)

- **recette-01** — `97411000CH0196` : **enclave E1 désormais SERVIE** (zone 69 m², séparatives seules,
  emprise 30 %, hauteur 7 m ; bloquée en GABARIT-2). Le win principal du mandat.
- **recette-02** — `97411000HP0606` : P1 en zone ne couvrant pas les emprises publiques → « Calcul
  incomplet — donnée réglementaire manquante » + motif « arête sans voie ni voisin cadastré (ravine,
  littoral ou domaine public non routier) ».
- **recette-03** — `97411000HD0281` : **inchangée** (2 387/1 200/1 194/10 m) ; `97411000IE0153`
  inchangée (805/394/483/13 m) — la marge 3,5→4,0 n'a rien régressé.
- **P1 servie par « emprises publiques » + ravine** : non montrable sur données réelles (0 zone
  EP-couverte a un PLU complet) ; mécanisme **unit-testé** (`test_P1_emprise_publique_servie_par_citation`,
  `test_emprise_publique_arete_ouverte`).

## 8. Arbitrages CC

1. **Marge 3,5 → 4,0 m** (lot D) : justifiée par les frontages en léger retrait (~5,6 m), auditée 0 faux
   sur 70 + 100. Pas d'élargissement au-delà (DL0527 à 8–12 m reste bloquée honnêtement).
2. **Source de la limite emprise publique** = « cadastre (non cadastré = domaine public) + citation PLU
   art. X » ; le recul (valeur PLU) est dans le détail. Cohérent avec le validateur.
3. **E2 par heuristique** (voisin élancé, sans bâti, hors BD TOPO) : conservateur (bloque le doute).
4. **STOP au lot E** : seuil ≥ 90 % structurellement hors d'atteinte (mur PLU) ; l'outil sert déjà tout
   ce qui est soluble côté limites (84 % des PLU-complets), à 0 faux. Ne rien forcer au-delà.

## 9. Limite connue

Le recul voie « sans objet » d'une enclave E1 est déclaré dans `applicableRules` mais n'apparaît pas
dans « Règles appliquées » du panneau (le moteur n'y émet que les règles portant une géométrie servie).
Cosmétique ; l'enclave est servie correctement. À surfacer en GABARIT-4 si souhaité.

## Hors mandat

Exports (Flash, Dossier) · règle non chiffrable = `not_integrated` · merge · `residuel-serve` ·
suite pytest complète (Vic) · **calibrage PLU du CES/hauteur (le vrai levier des 44 % restants)** ·
surface de route BD TOPO · découpage multi-zone.
