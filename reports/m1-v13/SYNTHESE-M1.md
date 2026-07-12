# SYNTHÈSE M1 — Hotfix V v1.3 « correction des signes » · 12/07/2026

**Branche `hotfix/v-v1.3-signes` — aucun merge (validation Vic, merge --no-ff par lui).**
Fondement : Phase 0 (`reports/phase0-validite/SYNTHESE-PHASE0.md`). Périmètre tenu : diff
limité à barème V + brûlante + tag + snapshots ; **Q, A, matrice, étage 0 : zéro diff** ;
q_v3_datagap intact (checksum identique, cf. `snapshots.md`).

## 1. Barème avant / après (signes uniquement — aucune magnitude re-tunée)

| Code | Famille | v1.2 | v1.3 | Motif |
|---|---|---|---|---|
| BODACC_LJ | A | 35 | 35 | non tranché Phase 0 — TODO v2 |
| BODACC_LJ_CLOT | A | 30 | 30 | idem |
| BODACC_RJ | A | 30 | 30 | idem |
| BODACC_SAUVEGARDE | A | 20 | 20 | idem |
| **BODACC_RADIATION** | A | 25 | **0** | anti-signal (≈0,35× base) — événement tracé « détecté, non compté — anti-signal Phase 0 (v1.3) » |
| **BODACC_CESSION_FONDS** | A | 10 | **10 (conservé)** | signal le plus fort observé (72 % de vente) |
| **RNE_CESSATION** | B | 25 | **0** | anti-signal — trace conservée à 0 |
| **RNE_DIRIGEANT_75/70/65** | B | 22/18/12 | **0** | sortie de V → tag veille_succession |
| **RNE_SCI_DORMANTE** | B | 8 | **0** | sortie de V → tag veille_succession |
| GEO_HORS_ILE / AUTRE_COMMUNE | C | 15 / 4 | 15 / 4 | inchangés (mandat) |
| FRICHE / TENURE_OBS5 / NU_PM | D | 18 / 8 / 5 | 18 / 8 / 5 | inchangés ; **tenure qualifiée par signaux à points > 0 uniquement** (un anti-signal à 0 ne la réveille plus — c'était la bande morte 25-49) |
| DPE_G_MULTI / G / F | E | 15/12/8 | 15/12/8 | inchangés |
| Match nom ×0,7 · dédup D6 | — | — | ×0,7 inchangé · D6 retirée (sans objet à 0/0, les deux événements restent tracés) | |

## 2. Effectifs v1.2 → v1.3 (431 663 parcelles recalculées)

| Bande | v1.2 | v1.3 |
|---|---|---|
| V = 0 | 363 710 | 369 684 |
| V 1-7 | 1 986 | 2 638 |
| V 8-24 | 8 976 | 9 760 |
| V 25-49 (la bande morte) | 8 880 | **1 629** |
| V ≥ 50 | 169 | 10 |
| veille_succession (nouveau, hors V) | — | **7 092** |

Veille succession (lot 2) : 7 092 parcelles PM à SIREN confirmé — **7 085 dirigeant ≥ 70 ans ·
7 SCI dormante seule · 0 les deux** (`veille-succession.csv`, horizon affiché « 3-7 ans »,
jamais compté dans V, jamais brûlante).

## 3. Brûlante v1.3 : seuil 17 (mécanique, garde-fou [30-120])

L'ancien seuil 34 est caduc (échelle changée : 29 brûlantes seulement, au cœur de l'ex-bande
morte). Scan complet dans le rapport de calcul ; extrait :

| seuil | effectif brûlantes | dont ≥ 1 événement daté |
|---|---|---|
| 15 | 124 (> garde-fou) | 94 |
| **17 (retenu)** | **120** | **94 (78 %)** |
| 18 | 113 | 94 |
| 22 (+5) | 39 | 26 |
| 12 (−5) | 212 (hors garde-fou) | 102 |

**Seuil 17 = plus petit V dans le garde-fou**, et il maximise les porteuses d'événement daté
(94 — toutes les suivantes en perdent). Sensibilité : ±5 fait sortir du garde-fou vers le
bas (212) ou tomber à 39 vers le haut — le plateau 17-18 est stable (120→113).

**Delta vs les 79 v1.2** (`delta-brulantes.csv`, motif par parcelle) : **32 gardées ·
47 sorties · 88 entrées** (= 120). Les 47 sorties perdent leurs points de famille B
(dirigeant/SCI/cessation → 0) ; les 88 entrées passent le seuil recalibré sur l'échelle
v1.3 — 94/120 portent un événement daté (cession de fonds en tête), contre une minorité
dans le jeu v1.2. Liste complète pour validation visuelle : `brulantes-v13.csv`
(id, commune, V, composition, date du dernier événement).

## 4. Snapshots gelés (lot 4)

`v1.2-2026-07-10` (id 1, seuil 34, 79 brûlantes, gelé AVANT recalcul) et `v1.3-2026-07-12`
(id 2, seuil 17, 120 brûlantes + veille). q_v3_datagap **intact** :
`f568e45046c3e85892f0876e8096ca13` avant = après. Protocole d'arbitrage forward :
`snapshots.md`.

## 5. Tests (lot 5)

- Nouveaux (`test_score_v13.py`, 8) : cessation → 0 tracée · famille B totalement hors V ·
  cession de fonds strictement identique v1.2 · radiation ne déplace plus la cession ·
  SCI dormante 0 pt + tag · dirigeant 70 taggé / 69 non · PP/public/bailleur jamais taggés ·
  match nom jamais taggé.
- Adaptés (v1.3 documenté dans chaque docstring) : radiation tracée à 0 · dédup D6 → contrat
  anti-signaux · tenure qualifiée par points > 0 (dirigeant/cessation/radiation ne qualifient plus).
- Suites : score_v (18) + score_v13 (8) + ux_v1 + ai + segments = **50 verts, 1 skip
  documenté, 1 échec `test_evaluate_avec_ia_stocke_ai_payload` = pyproj DataDirError (dette
  d'environnement PROJ préexistante et consignée, indépendante de ce diff)**.
- Perf d'ingestion : aucune ingestion touchée ; le run complet Score V garde le même
  pipeline COPY (431 663 parcelles recalculées en un run).

## À valider par Vic
1. La liste des 120 brûlantes v1.3 (`brulantes-v13.csv`) — validation visuelle.
2. Le seuil 17 (mécanique ; alternatives 18 ou 23 documentées par le scan).
3. Merge `--no-ff`, puis **redémarrer `labuse api`** (le seuil 17 est une constante serveur ;
   la base porte déjà les scores v1.3 — d'ici merge+restart, le front affiche v1.3 avec
   l'ancien seuil 34, soit 29 brûlantes temporairement).
