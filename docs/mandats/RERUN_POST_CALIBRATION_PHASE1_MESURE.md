# RE-RUN POST-CALIBRATION — PHASE 1, MESURE D'AMPLEUR (lecture seule)

> **Statut : MESURE TERMINÉE — POINT D'ARRÊT. Rien appliqué, pas de bascule, champion jamais
> ré-entraîné.** Mesuré le 29/07/2026. Isolation tenue : recalcul du résiduel dans une table
> ISOLÉE (`parcel_residuel_rerun`), re-score du champion **EN MÉMOIRE** (aucune écriture DB,
> aucun swap, aucun `run_score_v2`), `parcel_residuel` / `p_model_static` / `q_v7_defisc`
> intouchés. Champion chargé depuis l'artifact, sha vérifié.

---

## Résumé exécutif — le re-run ne fait PAS ce que le mandat supposait

Le critère de sens du mandat (« perdre du rang ⇔ SDP surestimée par le repli générique ») est
**INVERSÉ par le champion**, prouvé par le maillon. Ce n'est pas un bug du re-run : c'est que
la feature `sdp_residuelle_m2` est apprise à contribution **DÉCROISSANTE** (grande SDP → score
plus BAS). Conséquence dirimante : corriger une SDP surestimée fait **MONTER** le score, pas
descendre — **le canal résiduel/P ne peut pas déclasser les gels ; il les renforce.** Le
déclassement des parcelles en zone fermée ne peut venir que de la cascade (étage 0), jamais du
résiduel. → **Arrêt et rapport**, comme prévu au cadrage.

---

## 1. Recalcul du résiduel sur YAML courants (263 169 parcelles, table isolée)

| | parcelles |
|---|---:|
| SDP en BAISSE (capacité réduite : pleine terre ↑, hauteurs calibrées < repli) | **65 634** |
| SDP en HAUSSE (calibration densifie : hauteurs calibrées > repli prudent) | **24 150** |
| stable | 163 544 |
| devient NUL (interdit calibré → plus de résiduel) | 9 841 |

SDP résiduelle moyenne **395 → 302**. Mouvement **bidirectionnel** (contrairement à Saint-Paul,
monotone baisse) : la calibration restreint certaines communes et en densifie d'autres — exactement
le double effet attendu.

## 2. Barème `residuel_socle` — décalibré (préalable CONFIRMÉ, cf. §0bis du mandat)

Recalcul des 31 991 résiduels Saint-Paul : SDP moy 488 → 424 (**−13 %**), U3c −14 %, U6c −13 %,
**6 577 en baisse / 0 en hausse**, **1 633 SP (5,1 %) changent de palier de barème, toutes vers
le bas** (74 quittent le +30). Les bornes du barème (5000/2000/800/300/100), ajustées sur des
résiduels gonflés, sur-bornent désormais. **Re-dériver le barème sur verdicts SP recalculés AVANT
le re-run de l'île.**

## 3. Matrice de transition des tiers (canal résiduel, étage 0 tenu à l'état servi)

Champion ré-appliqué en mémoire au frame dont les 3 features résiduel sont remplacées par le
recalcul. **Validation** : reproduction du servi à corr(p_raw) = **0,99985** (max |Δ| = 1e-2),
sha champion `00a58008…9b64`. **2 011 parcelles changent de tier.**

| servi ↓ / rerun → | a_creuser | brûlante | chaude | écartée | réserve |
|---|---:|---:|---:|---:|---:|
| **a_creuser** (72 980) | 72 181 | 4 | 45 | 0 | 750 |
| **brûlante** (120) | 2 | 110 | 8 | 0 | 0 |
| **chaude** (1 031) | 32 | 6 | 993 | 0 | 0 |
| **écartée** (353 945) | 0 | 0 | 0 | 353 945 | 0 |
| **réserve** (3 587) | 1 164 | 0 | 0 | 0 | 2 423 |

10 brûlantes sortent (8 → chaude, 2 → a_creuser), 10 entrent (4 a_creuser, 6 chaude). 38 chaudes
bougent. 1 164 réserve → a_creuser (baisse) ; 750 a_creuser → réserve (hausse). Par commune : Le
Tampon 202 montent / 28 descendent, Saint-Pierre 53↑/267↓, Saint-Joseph 14↑/206↓ — la direction
est propre à la calibration de chaque commune.

**Caveat — le tier est un rang GLOBAL** : des communes NON calibrées bougent aussi, purement par
re-classement relatif (Saint-André 85 changements / 0 feature modifiée, Saint-Leu 82). Une partie
des mouvements est relationnelle, pas intrinsèque.

## 4. Le SENS — inversé, prouvé par le maillon (le résultat bloquant)

**Coefficients du champion (log-hazard) :**
- `sdp_residuelle_m2` : coef **+0,498**, mais **WoE décroissant** : ≤10 → +0,074 ; (284,367] →
  −0,125 ; (493,719] → −0,29 ; >1341 → −0,30. Grande SDP résiduelle → contribution NÉGATIVE.
- `pct_potentiel` : **coef None — pas dans le modèle.**
- `sous_densite` : coef −0,186, effet marginal.

Donc la SEULE feature résiduel qui pèse, `sdp_residuelle_m2`, tire le score **vers le bas quand la
SDP est GRANDE**. Réduire une SDP surestimée (repli générique → calibré) fait **MONTER** le score.

- corr(Δp, ΔSDP) = **−0,48** (Spearman). corr(p_servi, sdp_servi) = −0,28.
- Descendants 99 % « SDP baissée » = **artefact de base** (73 % de tous les changements sont des
  baisses de SDP) — ne prouve PAS le sens causal.
- Contre-sens per-parcelle : 83 / 2 011 (4 %) — non massif ; mais le sens GLOBAL est inversé.

**Le critère de validation du mandat est inapplicable tel quel** : « perdre du rang ⇔ SDP
surestimée » est FAUX ici — le champion fait l'inverse. Il faut, soit reformuler le critère au
signe réel de la feature, soit acter que le canal résiduel n'est pas le bon levier.

## 5. Implication dirimante pour le repli non optimiste (golden brûlante)

La golden brûlante **97422000AD1237** (2AUd, SDP résiduelle 453). Sous le correctif gel, SDP →
0 :
- contribution p à SDP=453 : **−0,086** → contribution à SDP=0 : **+0,037**
- **Δ = +0,123 log-hazard : son score MONTE → elle devient PLUS brûlante, pas moins.**

**Le recalcul du résiduel ne déclasse PAS les parcelles en zone fermée — il les renforce.** Le
déclassement des gels/interdits ne peut venir que de l'**exclusion en étage 0 (cascade)**, jamais
du canal résiduel/P. Cela tranche la question des tiers laissée ouverte au mandat repli : la
migration `parcel_residuel` n'était pas le levier de déclassement — c'était même un contre-levier.

---

## Ce que je recommande de trancher (Vic)

1. **Sens inversé** → le critère « perte de rang ⇔ SDP surestimée » est abandonné ou reformulé au
   signe réel du champion (`sdp_residuelle_m2` décroissante). Décision produit : est-il voulu
   qu'une capacité résiduelle plus faible score plus haut ? (le modèle vise la sous-densité /
   le déjà-bâti, pas le greenfield — cohérent avec sa cible, mais à assumer explicitement.)
2. **Barème décalibré** → re-dérivation avant re-run (préalable confirmé §2).
3. **Déclassement des gels** → passe par la cascade (étage 0), pas par le résiduel. Le correctif
   gel du repli doit viser `_habitat_interdit`/`constructible_neuf` en étage 0, mesuré séparément.
4. **Le re-run complet** (recalcul résiduel + re-passe cascade + champion + arène) reste requis
   pour l'ampleur RÉELLE (canal cascade inclus) — cette phase 1 n'a mesuré que le canal résiduel,
   étage 0 tenu à l'état servi.

*Artefacts (isolés, lecture seule) : `parcel_residuel_rerun`, `repli_sp_residuel` (tables de
travail) ; `/tmp/repli_rerun_scores.csv`, `/tmp/repli_transition.csv`. Aucune table de production
modifiée ; `q_v7_defisc` intouché.*
