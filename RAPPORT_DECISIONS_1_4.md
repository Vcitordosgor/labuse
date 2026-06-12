# RAPPORT GLOBAL — Décisions 1-4 exécutées · recettes · ⛔ STOP & VALIDATE

> Réponse à la DIRECTIVE post-1.A. Étape 0 : `ETAT_DES_LIEUX_DONE.md` (commit `c10c120`).
> Étape 1 : Décisions 1-3 livrées (commit `f81b35a`). Étape 2 : recette capacité ±15 % ci-dessous.
> **219 tests verts** (15 nouveaux), ruff clean, JS check OK, **démo 8/8 conforme**. 2026-06-12.

---

## 1. Recettes des Décisions 1-3 (3 000 parcelles ré-évaluées, avant → après)

### Statuts (net)
| Statut | Avant | Après | Mouvements |
|---|---:|---:|---|
| opportunité | 88 | **88** | aucune perte vitrine |
| à creuser | 768 | **777** | **+10 réadmises** (mixtes A/N), −1 (ER) |
| faux positif probable | 1 978 | 1 969 | |
| exclue | 166 | 166 | |

### D1 — A/N sensible au recouvrement (seuil 90 %, PLACEHOLDER)
- **292 HARD_EXCLUDE** au motif exact directive : `« Zone {libelle} PLU — inconstructible (recouvrement {pct} %) »`. Attendu Vic ~304 (23 A + 281 N **dominantes**) : les 12 dominantes-A/N sous 90 % basculent en **mixte** — c'est précisément l'effet recherché du seuil.
- **17 flags « Zonage mixte — constructibilité limitée à l'emprise U/AU »** (part A/N 5-90 % + part U/AU). **10 parcelles réadmises** `faux positif → à creuser` (ex. BV0206 : A 52 % + U 48 % — exclues à tort avant). Lisérés < 5 % (`an_mixte_min_pct`, PLACEHOLDER) ignorés : ~180 parcelles avec liséré géométrique GPU ne sont PAS flaggées (anti-bruit).
- **Clip géométrique fait** (option « si simple » retenue) : l'emprise insetée est intersectée avec l'union U/AU dans la pré-faisabilité, ligne de modulation explicite (« ~X m² retenus sur ~Y m² insetés »).
- **Recette BV0405** ✅ : `Zone A PLU — inconstructible (recouvrement 100 %)`, opp 0.

### D2 — Proxy SAR : zéro pouvoir d'exclusion
- **3 000 verdicts SAR = PASS** (0 HARD, 0 SOFT_FLAG). Donnée conservée, badge UI **« SAR (proxy indicatif) »**.
- **2 divergences ⚠** détectées (PLU U/AU ∩ proxy naturel/agricole), **dont 1 zone AU = BV1431** : `⚠ proxy SAR divergent du PLU — vigilance en cas de révision … zone AU : ouverture à l'urbanisation moins probable` — remontée en **vigilance** du résumé (cas AU) en plus de la table cascade. (2 seulement car le proxy ne couvre que les îlots « potentiel foncier » ; le reste est honnêtement « hors îlot »).
- **Recette BV1431** ✅ : plus aucun flag bloquant (opp 58 → **73**), warning affiché, statut inchangé `faux_positif_probable` (déclassement **pente 103 %**, comme le veut la démo).

### D3 — Prescriptions
- **3.a ER** : **10 HARD_EXCLUDE** (≥ 50 %, PLACEHOLDER) au format directive — ex. `Emplacement réservé 88 : Extension de la gare routière (100 %)` (6 parcelles), ER 68, ER 83 (×3). 9/10 étaient déjà faux positifs (autres signaux), 1 bascule. **81 SOFT_FLAG** < 50 % avec **déduction** : la surface ER ∩ emprise insetée est soustraite de l'emprise constructible, mention `« ER {num} : {libellé} — {m²} déduits »`.
  **Recette BV0912** ✅ : flag (9 %) + **« ER 81 … — 120 m² déduits »** + badge, capacité R+1 16-17 logts, **reste opportunité (67)**.
- **3.b Mixité sociale** : badge fiche + détection bilan. Le libellé GPU (« Clause logements aidés ») **ne chiffre pas le quota** → `pct_lls` et `prix_m2_lls` = **PLACEHOLDERS (0)** : CA non pondéré + avertissement explicite. **Champs éditables** dans le panneau bilan, **recalcul instantané** local (CA pondéré `[(1−p)×DVF + p×LLS]` + charge foncière). Dès que Vic calibre les params YAML, la pondération s'applique côté serveur.
- **3.c Eaux pluviales** : badge (libellé GPU avec niveau reglt) + `majoration_vrd_pluvial` (PLACEHOLDER 0) appliquée au coût de construction — **visible mais neutre** tant que non calibrée.

---

## 2. Étape 2 — recette capacité : 5 parcelles, manuel vs moteur (tolérance ±15 %)

Méthode : règles `plu_saint_paul.yaml` (sourcées Art./page) + hypothèses YAML déroulées **à la main** depuis les entrées brutes (surface cadastrale, emprise insetée mesurée par SQL indépendant, pente) et confrontées à la sortie du moteur.

| Parcelle | Zone (règles) | Entrées | **Manuel** | **Moteur** | Écart |
|---|---|---|---|---|---|
| BN1197 | U1b (hé 12 → R+3 ; 1 pl/logt ; PT à_vérifier) | 1 754 m², inset 1 158, pente 1 % | emprise 521 → SDP 2 084 → 20,8-25,7 logts → **plafond densité 21** → 20-22 | SDP 2 085, **20-22** | <1 % ✅ |
| BO0113 | U1c (hé 15 → R+4 ; 1 pl/logt) | 1 808 m², inset 1 305, pente 1 % | 587 → SDP 2 936 → 29,4-36,1 → densité 27,1 → 27-28 | SDP 2 936, **27-28** | <1 % ✅ |
| BV0912 | U6c (hé 6 → R+1 ; 2 pl ; PT 20 %) | 3 948 m², inset 2 960 **− ER 120**, pente 19 % | 2 840×0,45=1 278 → SDP 2 556 → 25,6-31,5 → densité 23,7 → ×0,7 = 16,6 | SDP 2 555, **16-17** | <1 % ✅ |
| BV1431 | AU6c → **renvoi U6c** | 2 274 m², **inset 367** (lanière), pente 103 % | 165 → SDP 330 → 3,3-4,1 → ×0,4 = 1,3-1,6 | SDP 331, **1-2** | <1 % ✅ |
| BV0405 | zone **A** | 1 991 m² | **0** (zone non constructible) | pas de carte capacité (zone hors YAML constructible) | cohérent ✅ |

Les écarts sont < 1 % (mêmes formules déroulées indépendamment) : la recette **valide le câblage** zone → règles sourcées → chiffres (renvoi AU→U compris) ; les hypothèses (occupation 45 %, rendement 80 %, densité 30 logts/ha/niveau…) restent des **paramètres éditables affichés**, pas des vérités.

### 🐛 La recette a payé : bug majeur détecté et corrigé
La résolution de zone de la faisabilité (`kind ILIKE '%plu%'`) attrapait les **prescriptions** ingérées en 1.B : quand une prescription plus petite que la zone contenait le centroïde, la « zone » devenait « Clause logements aidés » → **fiche capacité/bilan perdue sur 1 919 / 3 000 parcelles** (régression silencieuse 1.B, BV1431 incluse). Corrigé (`f81b35a`), fiches restaurées. *« Déjà implémenté » ≠ « validé »* — démonstration faite.

### Améliorations notées (non faites, hors scope)
- Carte capacité explicite « non constructible (zone A/N) » au lieu d'absence de carte (BV0405).
- Le recul voirie (souvent « à_vérifier ») n'est pas déduit géométriquement (façade rue non identifiable au cadastre) — déjà signalé en avertissement de fiche.

---

## 3. Synthèse Étape 0 (détail : `ETAT_DES_LIEUX_DONE.md`)

| Item DONE §7 | Existant | Manquant principal |
|---|---|---|
| Audit pull | IDU + re-éval à la demande ; connecteur cadastre à la volée **écrit mais non câblé** | BAN, polygone, orchestration hors-référentiel |
| Potentiel résiduel | bâti classé (6 classes) + capacité | le **croisement** « SDP résiduelle » affiché |
| Export | MD + HTML imprimable + GeoJSON | PDF natif, CSV |
| Pipeline / compar. / filtres | Kanban complet + prospection manuelle | comparateur, filtres sauvegardés |
| Couches Phase 3 | eau, littoral, SITADEL, pente, propriétaire (convention), voisinage | 50 pas officiels, exposition, flux DGFiP |
| Recette | 219 tests (statuts, seuils, API) | tests de chiffres → **comblé en partie par l'Étape 2** |

---

## ⛔ STOP & VALIDATE — aucune nouvelle couche entamée

Conformément à la Décision 4, je m'arrête ici. Pour re-prioriser la Phase 3, tu as :
1. l'état des lieux DONE §7 (tableau ci-dessus + fichier dédié),
2. les recettes 1-3 chiffrées (impacts, témoins, formats de motifs exacts),
3. la recette capacité ±15 % (5/5, + bug 1 919 fiches corrigé).

**PLACEHOLDERS en attente de calibrage Vic** : `an_hard_exclude_pct` (90), `an_mixte_min_pct` (5), `er_hard_exclude_pct` (50), `pct_lls` (0), `prix_m2_lls` (0), `majoration_vrd_pluvial` (0).
