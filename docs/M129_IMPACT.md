# M129 — RAPPORT D'IMPACT AVANT BASCULE (STOP)

*Branche `feat/m129-grand-nettoyage`. Le run `q_v10_m129` est calculé À CÔTÉ, complet — RIEN n'a
basculé, le servi reste q_v9_m81 (golden 0 FAIL, garde-run verte). La bascule attend ton GO.*

## 1. VIVIER AVANT/APRÈS — la cible arbitrée est TENUE

| | q_v9_m81 (servi) | q_v10_m129 (à côté) |
|---|--:|--:|
| Évaluées | 431 663 | **431 663** ✓ (garde-run) |
| Étage 0 (« exclue », motif dit) | 340 752 (dont 262 531 `faux_positif_probable`) | **145 882** — `faux_positif_probable` **MORT** |
| **Vivier** | 90 911 | **285 781** (cible 285 770, écart −11 = bord du seuil pente strictement > 100 %) |
| Opportunités (statut cascade) | 8 285 | **18 382** |

**Motifs d'exclusion restants (français, chacun consultable)** : zonage A/N-éco 103 722 · PPR rouge
44 764 · micro-parcelle < 40 m² 18 902 · emprise linéaire 13 801 · forêt domaniale 6 890 · cœur du
Parc 6 137 · emprise routière 4 851 · pente > 45° 4 739 · équipement OSM 1 526 · eau 316 ·
prescriptions gelantes 15 · trait de côte 3. **Bâti et foncier public : absents** (libérés) ✓.

**Transitions q_v9 → q_v10** : 169 534 fp→a_creuser (le bâti libéré) · 83 857 fp→exclue (co-exclues,
le panier seul change) · 14 526 exclue→a_creuser (public 9 002 + ER + pente 45-31° + micro 40-100) ·
**10 810 nouvelles opportunités** · 740 opportunite→a_creuser **expliquées** : les zéros M125 entrent
au run (`residuel_socle` lit sdp=0 → « rien à construire » −25 sur des UNKNOWN d'avant — effet VOULU,
anticipé au doc M125) · 27 a_creuser→opportunite.

## 2. COMPOSITION DU NOUVEAU VIVIER (exigence Vic n°1)

Tiers v2 (score sha `00a58008…` INTOUCHÉ, recalé intercept seul — N_entrée 3 890, N_sortie 5 446) :

| Tier | nu | bâti |
|---|--:|--:|
| brûlante | 88 | 17 |
| chaude | 857 | 427 |
| a_creuser | 37 050 | 26 464 |
| réserve foncière | 2 342 | 5 079 |
| declasse_bati_sature (VISIBLE, motif) | 16 402 | **181 448** |
| autres declasse_* (visible, motif) | 10 511 | 5 096 |

**Ce qu'un client sans filtre voit en tête : top 100 = 78 nu / 22 bâti.** La masse bâtie libérée
(181 k) est VISIBLE mais rangée par le déclassement tier `bati_sature` (arbitrage 29/07 : visible
avec motif, hors tiers de tête) — la tête de liste reste dominée par le nu tant que les features
bâti (C_bati, gardé au chaud) ne sont pas promues. **Copros : 0 avec un rang foncier** ✓ (M36 tenu).

## 3. TENUE DES ÉCRANS SUR L'UNIVERS ×3 (exigence Vic n°2)

Chronos SQL des formes servies, mêmes requêtes sur les deux runs :

| Requête | q_v9 (90 911) | q_v10 (285 781) |
|---|--:|--:|
| Liste p.1 (tri rang, LIMIT 60) | 62 ms | **26 ms** |
| Compteur vivier | 403 ms | **167 ms** |
| Page profonde (OFFSET 5000) | 4 495 ms | **1 441 ms** |
| Facette sous-densité | 305 ms | **191 ms** |

**Rien ne plie** — v10 est même plus rapide (tables fraîchement écrites, stats PG propres ; à
re-mesurer après VACUUM de rétention). Deux points connus, PAS aggravés par le ×3 : (a) la
**pagination profonde par OFFSET** est lente sur les DEUX runs (~15 paginations en dur, dette
M122) ; (b) la **palette carte coupe à 20 000** avec toast — déjà le cas à 90 k, la glose doit
nommer le nouvel univers (P5). Compteurs : `/projets/compteur` (M120-B) lit le vivier figeable —
dira 285 781 après bascule.

## 4. GOLDEN — ce qui bougera à la bascule (rien avant)

Aujourd'hui : **0 FAIL** (le servi n'a pas bougé) + GARDE-RUN 431 663 ✓. À la bascule, bougeront
et seront à re-ancrer (chacun attendu, aucun n'est une régression) : les ancres portant `statut`
(fp→exclue/a_creuser), `tier` (declasse_bati_sature massif), les compteurs de vivier, l'entonnoir.
La liste exacte ancre par ancre sera produite par un golden-rejeu au geste de bascule (rejouable :
`LABUSE_SERVED_RUN=q_v10_m129 python qa/golden_check.py`).

## 5. PROJETS EXISTANTS (P6.3)

Le rejeu M120 (`_figer_shortlist` diff {ajoutees/sorties/tris_conserves}) couvrira mécaniquement
les entrées à la bascule. **Vérifié : le message de rejeu ne dit PAS ENCORE « entrée par refonte
cascade »** — libellé à ajouter (P5, une ligne dans le diff). Volume attendu : les cadrages sans
filtre nu/bâti verront des « +N » massifs (l'univers triple) — le rejeu reste sur TON geste par
projet, jamais muet.

## 6. DIVISION (P4 — NON ENTAMÉ, honnête)

Les 7 candidates restent stampées q_v8_calibre : le re-stamp SANS re-calcul mentirait (la garde
étage 0 a changé de définition). L'industrialisation (CoSIA + pente branchés, calcul sur le vivier,
badge revue, ligne unifiée, réconciliation des DEUX divisibilités — `parcel_filtre_bati` vs
`division_or_candidates`) = **session dédiée** (P4), config déjà posée (`seuils_geometrie.yaml`).

## 7. CE QUI RESTE AVANT LA BASCULE (découpage proposé)

M129 est un mandat multi-sessions — fait ici : **P1 complet · P2 complet · P3 inventaire**
(14 consommateurs matrice mappés, mort structurelle actée : q_v10 n'a NI matrice NI q_score).
Restent, chacun une demi-session au standard :
- **M129-B — P3-exécution** : les 14 migrations (CSV export, geojson/tuiles props, partners
  v1→opportunity_score, moteurs, 4 lectures front q_score, filtre score_min, verdict_servi
  tier-écartée) — chaque suppression avec preuve, golden re-ancré.
- **M129-C — P4 division industrialisée** (+ le « ~N lots » à définir, cf. audit division_or).
- **M129-D — P5 restitution** : gloses (« hors exclusions légales et physiques »), « probabilité
  de vente sous 1 an » partout, 3 facettes nouvelles (droits résiduels · propriétaire public ·
  Divisible), captures avant/après (P6.2).
**La bascule vient APRÈS M129-B minimum** (servir q_v10 avec les lectures matrice encore en place
afficherait des colonnes NULL).

---
**STOP. La bascule attend ton GO — et ton arbitrage sur le découpage B/C/D.**
