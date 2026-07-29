# RE-RUN COMPLET — MESURE (run de travail isolé, lecture seule)

> **Statut : MESURE TERMINÉE — POINT D'ARRÊT. AUCUNE BASCULE. `q_v7_defisc` intouché, non modifié
> d'un bit.** Mesuré le 29/07/2026, en mémoire, champion chargé depuis l'artifact (sha vérifié),
> jamais ré-entraîné. La bascule reste l'arbitrage de Vic.

---

## 1. Arène — le pouvoir prédictif se MAINTIENT (condition d'arrêt NON déclenchée)

Même champion (`model_sha256 = 00a58008…9b64`), deux états de features : SDP du repli générique
(ancien) vs SDP calibrée sur 21 communes (nouveau). RR@1158 hors copro, `paired_bootstrap_diff`
(bootstrap apparié, mêmes lignes, seed 974), walk-forward 5 folds :

| Année | RR ancien | RR calibré | ΔRR | IC95(Δ) | Verdict |
|---|---:|---:|---:|---|---|
| 2021 | 9,061 | 8,879 | −0,181 | [−0,70 ; +0,45] | ≈ (IC ∋ 0) |
| 2022 | 8,809 | 8,945 | +0,136 | [−0,54 ; +0,37] | ≈ |
| 2023 | 8,533 | 8,893 | +0,360 | [−0,36 ; +0,84] | ≈ |
| 2024 | 7,777 | 7,777 | 0,000 | [−0,58 ; +0,36] | ≈ |
| 2025 | 6,727 | 6,841 | +0,114 | [−0,28 ; +0,40] | ≈ |

**0 fold de dégradation significative** (tous les IC95 contiennent 0 ; 4/5 en légère hausse). Le
modèle **n'exploitait PAS le biais du repli** — sinon des features plus justes auraient dégradé le
RR. Reproduction fidèle : 2025 RR_old = 6,727 = walk-forward M3.6 (6,73). **Le pouvoir prédictif
tient avec des features calibrées → pas d'obstacle arène à la bascule.**

## 2. Matrice de transition — ce que la nuit du 27 a produit (intrinsèque vs relationnel)

| servi ↓ / re-run → | a_creuser | brûlante | chaude | déclassée B | déclassée A | réserve |
|---|---:|---:|---:|---:|---:|---:|
| **a_creuser** (72 980) | 63 060 | 5 | 90 | 6 151 | 2 924 | 750 |
| **brûlante** (120) | 0 | 109 | 9 | 1 | 1 | 0 |
| **chaude** (1 031) | 15 | 6 | 939 | 26 | 45 | 0 |
| **réserve** (3 587) | 913 | 0 | 0 | 0 | 251 | 2 423 |
| **écartée** (353 945) | — | — | — | — | — | (353 945 inchangées) |

**11 187 mouvements de tier** — dont 9 399 déclassements (tête-de-liste) et 1 788 re-classements P.

**Séparation intrinsèque / relationnel** (intrinsèque = déclassée OU SDP propre modifiée ;
relationnel = features inchangées, rang déplacé par le mouvement des autres) :
- **10 797 intrinsèques (96,5 %)** — de la VRAIE information nouvelle (calibrage).
- **390 relationnels (3,5 %)** — du simple re-classement de rang, rien de produit.
- Le relationnel se concentre là où on l'attend : **communes NON calibrées** — Saint-André **89**,
  Saint-Leu **82** (aucun YAML → elles ne bougent que par ricochet) — plus quelques déplacements de
  frontière dans les calibrées (Saint-Benoît 52, Le Tampon 50, Saint-Paul 49). **Ce que la
  calibration a réellement produit = les 10 797 intrinsèques, pas les 11 187 bruts.**

## 3. Les brûlantes qui sortent et qui entrent (nominatif, avec motif)

Effectif brûlante conservé (120 → 120). **11 sortent, 11 entrent.** Le SENS est respecté (SDP
baisse ⇒ P monte ⇒ entre ; SDP monte ⇒ P baisse ⇒ sort — WoE décroissant du champion).

**SORTENT (11)** :
| IDU | Commune | → | Motif |
|---|---|---|---|
| 97422000AD1237 | Le Tampon | déclassée A | **golden** — 2AUd zone fermée |
| 97407000AS1056 | Le Port | déclassée B | parcelle inconstructible |
| 97407000AS1075 | Le Port | chaude | SDP 79 → 55 (capacité corrigée ↓) |
| 97407000AS1160 | Le Port | chaude | SDP 64 → 46 |
| 97414000EL0117 | Saint-Louis | chaude | SDP 163 → **271** (↑ → P ↓, sort) |
| 97416000HP0798 | Saint-Pierre | chaude | SDP 86 → **147** (↑) |
| 97421000AV0815 | Salazie | chaude | SDP 199 → **266** (↑) |
| 97403000AR1423 | Entre-Deux | chaude | relationnel (non-ancre golden) |
| 97413000BM0899 | Saint-Leu | chaude | relationnel |
| 97413000CX2822 | Saint-Leu | chaude | relationnel |
| 97420000AR0927 | Sainte-Suzanne | chaude | relationnel |

**ENTRENT (11)** — majoritairement SDP corrigée à la baisse (→ P monte, sens WoE) :
97402000AH1350 (SDP 259→124), 97404000AI2379 (497→330), 97406000AP0427 (400→98), 97408000AM0989
(236→128), 97414000CH1893 (245→135), 97424000AM0894 (312→207), 97418000AT2300 (55→74),
97401000AR1345 (30→46) ; relationnel : 97411000AD0030, 97413000CX2555, 97415000AY1608.

---

## Ce que le re-run produirait à la bascule (synthèse, pour l'arbitrage Vic)
- **Tiers** : 9 399 déclassements (déjà câblés, visibles en fiche) + 1 788 re-classements P (96,5 %
  intrinsèques). Brûlantes 120 → 120 (11 in / 11 out). Chaudes ~1 031 → ~1 038.
- **Arène** : RR maintenu sur 5 folds, aucune dégradation → le modèle gagne en justesse sans perdre
  en pouvoir prédictif.
- **Sens** : monotone et correct (canal P : SDP ↓ ⇒ score ↑ ; canal socle capacité : SDP ↓ ⇒ socle ↓).
- **Golden** : les 12 ancres réalignées correspondent exactement (10 déclassées + AV0815/CD0926).

**LA BASCULE RESTE À VIC.** Rien n'est basculé ; `q_v7_defisc` sert toujours. Protocole de bascule
disponible (`scripts/a1_bascule_v7.py`) sur GO explicite après lecture de cette mesure.

*Artefacts (lecture seule) : `/tmp/arene_rr.py`, `/tmp/rerun_matrix.csv`, `parcel_residuel_rerun`,
`parcel_constructibilite`. Aucune écriture DB ; `q_v7_defisc` intouché.*
