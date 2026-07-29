# TÊTE DE LISTE NON CONSTRUCTIBLE — PHASE DE MESURE (lecture seule)

> **Statut : MESURE TERMINÉE — POINT D'ARRÊT. Rien appliqué, pas de re-run, champion intouché.**
> Mesuré le 29/07/2026. Source AUTORITAIRE = `parcel_faisabilite` (résout la zone FINE), jamais
> le subtype grossier de `parcel_zone_plu`.

> **POURQUOI CE DÉFAUT PASSE DEVANT TOUT (Vic, 29/07)** : c'est le SEUL de tous ceux trouvés qui
> soit visible en UN CLIC. Un promoteur ouvre la tête de liste, choisit une parcelle, découvre que
> le règlement y interdit toute construction. Les 2 234 du repli, le ×2 de la charge, les SDP
> surestimées — tout cela demandait une mesure pour être vu. Celui-ci se voit à l'œil nu, dès le
> premier usage.

---

## 1. Ampleur complète (431 663 servies ; 77 718 non-écartées évaluées au moteur)

**9 399 parcelles servies (non-écartées) sont NON CONSTRUCTIBLES** — 12,1 % du pool servi.

| Tier | Non constructible | Total tier | Part |
|---|---:|---:|---:|
| **brûlante** | 2 | 120 | 1,7 % |
| **chaude** | 71 | 1 031 | 6,9 % |
| **réserve foncière** | 251 | 3 587 | 7,0 % |
| **à creuser** | 9 075 | 72 980 | 12,4 % |
| **total** | **9 399** | 77 718 | 12,1 % |

+ 2 383 parcelles servies en communes NON outillées (`parcel_faisabilite` = None) : verdict
impossible sans YAML — à traiter avec le calibrage des communes dépubliées (Saint-André/Leu/Philippe).

## 2. DEUX causes, deux formulations (Vic tâche 3 — confirmée et généralisée)

Le défaut n'est pas homogène. Le verdict moteur sépare nettement :

| Cause | n | dont tiers de tête (brûl.+ch.+rés.) | Nature |
|---|---:|---:|---|
| **A — ZONE fermée au règlement** | **3 221** | 297 | AU*st « secteur de transition » (2 217) + « habitat interdit, vocation économique » (1 004). **Peut s'ouvrir** (2AU → modification PLU). |
| **B — PARCELLE inconstructible** | **6 177** | 26 | « terrain trop exigu compte tenu des reculs » (4 653) + « contrainte rédhibitoire malgré le zonage » (1 524). **Permanent** (physique). |
| autre (hauteur à_vérifier) | 1 | 1 | — |

**Les 2/3 du défaut sont des parcelles physiquement trop petites, pas des zones interdites.** Deux
messages produit distincts requis : « zone fermée à l'urbanisation » (A, peut évoluer) vs « parcelle
inconstructible en l'état — trop exiguë compte tenu des reculs » (B, définitif).

Les « 15 U » qui intriguaient (chaudes) sont élucidées : `parcel_zone_plu` les étiquette « U »
grossièrement, mais le moteur résout la zone FINE et y lit *« habitat interdit — vocation
économique »* (cause A). Ce ne sont pas des U ordinaires. → toujours passer par le verdict moteur.

Répartition cause A par commune × tier : table complète en base (`tdl_faisa`) — têtes : Saint-Pierre
(504 a_creuser, 10 ch., 53 rés.), Saint-Joseph (372/2/19), Le Tampon (289/5/15 + 1 brûlante),
Sainte-Marie (249/7/23), Saint-Paul (183/6/0), Le Port (144/5/32).

## 3. Exclure ou déclasser ? (Vic tâche 2 — les deux chiffres)

Effet mesuré en mémoire (lecture seule) : non-constructibles retirés du ranking (comme le ferait
l'étage 0), tiers ré-assignés sur les scores SERVIS (reproduction fidèle : 120/1031/3587).

| Option | Effet |
|---|---|
| **EXCLUSION** (sort du pool) | Pool servi **77 718 → 68 319** (−9 399). Les 9 399 DISPARAISSENT du produit — y compris les 3 221 zones fermées qui peuvent rouvrir. |
| **DÉCLASSEMENT** (tier dédié + motif) | **80 constructibles seulement changent de tier** (76 montent, 4 descendent) — très peu disruptif. Brûlante (120) et chaude (1 031) restent PLEINES, refaites par de vraies opportunités ; réserve foncière 3 587 → 3 336 (251 zone-fermées retirées). Les 9 399 restent VISIBLES avec motif. |

**L'effet de tri est quasi identique** (les non-constructibles quittent les tiers normaux dans les
deux cas) ; la seule différence est la VISIBILITÉ produit. Le déclassement coûte 80 mouvements de
tier et garde le foncier surveillable (radar M24 sur les 3 221 zones fermées). Inclination Vic :
déclassement — la mesure la confirme peu coûteuse.

## 3bis. Remembrement (cause B — MESURE en information, Vic tâche 2 ; NE PAS traiter ici)

Les 4 653 « terrain trop exigu » sont les candidates naturelles au remembrement (une parcelle seule
inconstructible, deux ou trois contiguës ne le sont plus — le pendant inverse d'O12). Mesure de
contiguïté (ST_Touches, geom_2975) :
- **1 234 parcelles B contiguës à une autre B**, formant **475 groupes** (≥2).
- Tailles : 340 paires, 78 triples, 26 quadruples… jusqu'à un groupe de 18. **554 parcelles en
  groupes de 3+.** 1 366 contiguës à une inconstructible quelconque.

**Significatif** — segment qu'aucun concurrent ne sert. Graine de mandat « remembrement » (inverse
d'O12), à ouvrir séparément. Non traité ici.

## 4. Golden avant/après (Vic tâche 5) — 10 ancres à réaligner, motifs sourcés

10 ancres golden sont servies positives mais non constructibles au règlement calibré :

**Cause A (zone fermée)** — 4 :
- `97422000AD1237` Le Tampon 2AUd (**brûlante**) — secteur de transition AU*st.
- `97422000AX1253` Le Tampon 2AUe (**chaude**) — secteur de transition AU*st.
- `97407000AV0096` Le Port Ue (**réserve**) — habitat interdit / transition. (déjà tranchée mandat repli)
- `97401000AD0016` Les Avirons (a_creuser) — secteur de transition AU*st.

**Cause B (parcelle terrain)** — 6 :
- `97403000AR1424` Entre-Deux, `97406000AW1250` Plaine-Palmistes, `97407000BI0350` Le Port (chaude),
  `97413000CR0344` Saint-Leu, `97415000CW1056` Saint-Paul — « terrain trop exigu, reculs ».
- `97422000AS0911` Le Tampon Uc — « contrainte rédhibitoire malgré le zonage ».

Mise à jour du golden légitime (référence générée le 15/07, pré-calibration) — commit dédié, chaque
ancre datée + zone + article/page, distinct du correctif.

## 5. Discipline du correctif (Vic tâche 4) — le test AVANT le code

Détection du gel : **`calibree=True` croisé avec la famille de zonage, JAMAIS `constructible_neuf`
seul** (sinon 21 077 parcelles à `name` descriptif faussement exclues / 13 golden cassés — cf.
`REPLI_NON_OPTIMISTE_PHASE_A_MESURE.md`). **Le test qui vérifie qu'on n'exclut PAS ces 21 077
s'écrit AVANT le correctif, pas après.** Pour la cause B, s'appuyer sur le verdict moteur direct
(`parcel_faisabilite`), pas sur le zonage.

## 6. Un seul correctif pour deux mandats (Vic tâche 6 — gravé en tête des deux)

Le correctif d'étage 0 de CE mandat (honorer le verdict de faisabilité avant le scoring P) EST le
levier du repli non optimiste : le déclassement des gels passe par l'étage 0, jamais par le canal
résiduel (contre-levier prouvé, phase 1 re-run). **Un seul correctif, mesuré une fois, sert les
deux.** Le repli reprend sa population (cause A) portée par ce correctif. Note gravée en tête de
`MANDAT_TETE_DE_LISTE_NON_CONSTRUCTIBLE.md` ET `MANDAT_REPLI_NON_OPTIMISTE.md`.

---

## Ordre acté (Vic 29/07)
**(1) ce défaut tête-de-liste → (2) re-dérivation barème `residuel_socle` → (3) mesure canal cascade
(déclassement gels) → (4) re-run complet post-calibration.**

*Artefacts (lecture seule) : `tdl_faisa` (77 718 verdicts moteur), `/tmp/repli_nullcap.txt`,
`/tmp/tdl_declasse.csv`. Aucune table de production modifiée ; `q_v7_defisc` intouché.*
