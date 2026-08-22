# Améliorer la PAU de Saint-Philippe (RNU) avec CoSIA — Phase 1 : MESURE (STOP)

Commune : Saint-Philippe (97417), RNU, **4 162 parcelles** sans zonage.
PAU actuelle estimée par clustering DBSCAN sur les bâtiments **BD TOPO** (`rnu.py:131-186`,
ortho ~2023). CoSIA (PVA juil.-août 2025, 20 cm) voit du bâti que BD TOPO manque
(audit division_or : 16 142 parcelles au bâti révélé sur l'île).

Toutes les valeurs sont mesurées en SQL (algo `build_pau` reproduit à l'identique — baseline
retrouvé exactement : 35 noyaux / 3 482 bâtiments / 268 ha / 2 373 parcelles).

---

## Q1 — Bâti révélé par CoSIA à Saint-Philippe : **140 parcelles**

`parcel_bati_revele` (CoSIA emprise > BD TOPO emprise) :

| bande | n | emprise CoSIA moyenne |
|-------|--:|----------------------:|
| regle (significatif) | 72 | 112 m² |
| adjudication (petit/limite) | 68 | 28 m² |
| **total St-Philippe** | **140** | — |

Sur les 16 142 de l'île, **140** sont à Saint-Philippe. C'est peu — mais le recalcul PAU
n'utilise pas que ces 140 : il rejoue le clustering sur **toute** la couche de footprints CoSIA
(3 955 emprises à St-Philippe, dont **1 565 vraiment nouvelles** sans recouvrement BD TOPO +
2 390 doublons des bâtiments déjà vus). Source CoSIA = `qa_cosia_bati` (polygones), recoupée à
0,5 % près avec `p_model_bati_cosia` (aires 524 381 m² vs 521 918 m²) → fidèle.

---

## Q2 — Recalcul PAU avec BD TOPO + CoSIA : avant / après

**Méthode honnête = DÉDUPLIQUÉE** : BD TOPO ∪ (CoSIA sans recouvrement BD TOPO). Sinon la
simple union compte 2 fois les 2 390 bâtiments vus par les deux sources, ce qui gonfle la
densité locale et fait franchir le seuil de 10 à des hameaux qui ne le méritent pas.

| | noyaux | bâtiments clusterisés | PAU (ha) | parcelles dans PAU | dont ≥ 600 m² (plancher) |
|---|--:|--:|--:|--:|--:|
| **Baseline (BD TOPO seul)** | 35 | 3 482 | 268 | **2 373** | **947** |
| Union naïve (avec doublons) | 63 | 7 472 | 410 | 2 838 | 1 289 |
| **Enrichi DÉDUPLIQUÉ (honnête)** | **47** | 5 027 | 349 | **2 655** | **1 145** |

**Chiffre exact (dédupliqué, mêmes params médian) :**
- Noyaux : 35 → **47** (+12)
- Parcelles dans la PAU : 2 373 → **2 655** → **+282 entrent, 0 sortent**
  (0 sortant est garanti : on n'ajoute que des points, l'enveloppe ne peut que croître —
  vérifié explicitement, entrants 282 / sortants 0.)
- Parcelles au plancher de tier (PAU ∧ surface ≥ 600 m²) : 947 → **1 145** → **+198**.

> La version union-naïve annoncerait +465 / 63 noyaux : c'est SURESTIMÉ (double comptage).
> Le gain réel, honnête, est **+282 parcelles dans la PAU** et **+198 au plancher de tier**.

---

## Q3 — Les paramètres (eps 50 m, min 10 bât., buffer 40 m) : calibrés ou posés ?

**Posés par JUGEMENT prudent, PAS calibrés sur une vérité terrain.** Il n'existe aucune PAU
officielle de Saint-Philippe à laquelle ajuster les paramètres (la délimitation des PAU relève
de l'appréciation du service instructeur — c'est pourquoi la PAU reste étiquetée « Estimé »).
`docs/mandats/RNU_RAPPORT.md` documente 3 jeux dessinés à la main ; le **médian** a été retenu
et validé (Vic 26/07/2026) parce que « ≥ 10 constructions et ~50 m de continuité collent aux
hameaux réunionnais » — un choix raisonné, pas un fit statistique.

### Sensibilité (mesurée sur la source DÉDUPLIQUÉE honnête)

| jeu | eps/min/buf | noyaux | PAU (ha) | parc. PAU | parc. ≥ 600 |
|-----|-------------|-------:|---------:|----------:|------------:|
| strict | 40 / 15 / 30 | 40 | 137 | 1 667 | 507 |
| **médian** | **50 / 10 / 40** | **47** | **349** | **2 655** | **1 145** |
| large | 75 / 8 / 50 | 44 | 534 | 2 977 | 1 413 |

Variation FINE d'eps (min 10 / buf 40, source enrichie) : eps 45 → 60 donne 2 780 → 2 878
parcelles, soit **± 2 %** — peu sensible près du médian.

**Conclusion sensibilité :** le réglage fin d'`eps` change peu (± 2 %). Le VRAI levier est le
**choix de jeu** (couple minpoints + buffer) : strict → large va de 1 667 à 2 977 parcelles
(± 25 % autour du médian). Donc « une variation les change-t-elle beaucoup ? » — oui, mais
c'est l'arbitrage strict/médian/large qui compte, pas un micro-réglage. Le médian enrichi
(2 655) reste cohérent avec la doctrine actuelle (médian BD TOPO = 2 373).

---

## STOP — Le gain vaut-il le geste ?

**Ce n'est PAS « quelques dizaines » de parcelles.** À jeu constant (médian), passer BD TOPO
→ BD TOPO + CoSIA (source 2025, dédupliquée) donne :
- **+282 parcelles dans la PAU** (2 373 → 2 655, +12 %),
- **+198 parcelles au plancher de tier** (947 → 1 145, **+21 %**) — ce sont celles qui comptent
  vraiment, car le plancher conditionne l'éligibilité-capacité au tiering.

Et ce gain est **directionnellement une amélioration de qualité**, pas juste du volume : CoSIA
2025 est plus fraîche et plus complète que l'ortho ~2023 de BD TOPO ; 1 565 footprints
réellement nouveaux densifient 12 noyaux supplémentaires (hameaux sous-échantillonnés par
BD TOPO qui franchissent le seuil de 10). La PAU reste **Estimé** (avertissement inchangé).

**Décision Vic attendue** avant Phase 2. Points à trancher :
1. Faire le geste ? (gain +198 au plancher = matériel, à mon sens oui.)
2. Quel jeu de paramètres ? (recommandation : **rester au médian** — le changement de source
   ne doit pas se cumuler à un élargissement de jeu, sinon on ne sait plus d'où vient le gain.)

### Prérequis technique Phase 2 (à noter, pas encore fait)
`build_pau` (`rnu.py:149-158`) ne lit aujourd'hui QUE `spatial_layers kind='batiment'` (BD TOPO).
Pour Phase 2 il faudra lui donner la source CoSIA. `qa_cosia_bati` porte le préfixe `qa_`
(artefact de contrôle) — à vérifier avant de le câbler en dur : soit ingérer les footprints
CoSIA comme source bâtiment canonique, soit brancher `build_pau` sur la couche CoSIA officielle.
La mesure ci-dessus l'utilise comme proxy fidèle (recoupé à 0,5 %), ce qui est valide pour
CHIFFRER ; le câblage de production devra pointer la source canonique.

---

## Récap chiffres (à jeu médian, source dédupliquée honnête)

| # | mesure | avant | après | Δ |
|---|--------|------:|------:|--:|
| Q1 | parcelles bâti révélé St-Philippe | — | 140 | — |
| — | footprints CoSIA nouveaux (clustering) | — | 1 565 | — |
| Q2 | noyaux PAU | 35 | 47 | +12 |
| Q2 | parcelles dans PAU | 2 373 | 2 655 | **+282** (0 sortant) |
| Q2 | parcelles au plancher (≥ 600 m²) | 947 | 1 145 | **+198** |
| Q3 | sensibilité eps (près médian) | — | — | ± 2 % |
| Q3 | sensibilité jeu (strict↔large) | — | — | ± 25 % |
