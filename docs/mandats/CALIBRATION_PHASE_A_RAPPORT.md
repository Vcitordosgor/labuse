# RAPPORT — Mandat calibration estimées, PHASE A : prix de sortie neuf, du socle global à la résolution par commune

**Exécuté le 28/07/2026** (branche `mesure/calibration-phase-a-prix-neuf`, exécuteur Claude Code).
Mandat : `MANDAT_CALIBRATION_ESTIMEES.md` §2.1/§4.A. **LECTURE SEULE intégrale** : aucune
application, aucun re-run de scoring, aucun contact avec le champion P. Méthode et harnais
repris du mandat hypothèses bilan (`HYPOTHESES_BILAN_RAPPORT.md`, échantillons seedés `m26-hyp`).

**État de la base — ouverture ET clôture : golden 116/116 PASS, tiers du run servi
`q_v7_defisc` au bit près (120 / 1031 / 3587 / 72980 / 353945), les deux fois.**
La mesure est faite aux coûts DÉJÀ réalignés (YAML 2300-2800, mandat hypothèses mergé) :
les bascules ci-dessous s'ajoutent à celles du coût, elles ne les recouvrent pas.

## 0 · La phrase

Sur le périmètre où le socle 4900 est réellement servi, **95 % des parcelles déclarées
viables ne le sont plus au prix de sortie réellement observé localement** (1 717 / 1 813 sur
l'échantillon seedé) — l'ampleur est SUPÉRIEURE à celle du coût de construction (52 %) :
**requalification en mandat de même priorité demandée** (règle Vic, §2.1 du mandat).

## 1 · Couverture de `dvf_prix_sortie_neuf` (mesurée, table du 21/07/2026)

- **17 communes sur 24** ont une valeur commune (748 ventes neuves) ; **45 secteurs** ont une
  valeur secteur (416 ventes). Médiane île : **3 688 €/m² sur 765 ventes**.
- **Les 17 communes couvertes sont TOUTES sous le socle 4900** — aucune au-dessus :

| Commune | Prix neuf DVF | n ventes | Écart vs 4900 |
|---|---|---|---|
| Petite-Île | 1 980 | 9 | **−59,6 %** |
| La Plaine-des-Palmistes | 2 250 | 6 | −54,1 % |
| Le Port | 2 268 | 16 | −53,7 % |
| Saint-Benoît | 2 385 | 22 | −51,3 % |
| Sainte-Suzanne | 2 640 | 14 | −46,1 % |
| Saint-Joseph | 2 734 | 18 | −44,2 % |
| Sainte-Marie | 2 863 | 17 | −41,6 % |
| Saint-Louis | 3 073 | 37 | −37,3 % |
| L'Étang-Salé | 3 118 | 12 | −36,4 % |
| La Possession | 3 122 | 28 | −36,3 % |
| Les Trois-Bassins | 3 605 | 11 | −26,4 % |
| Le Tampon | 3 652 | 63 | −25,5 % |
| Saint-Pierre | 3 765 | 163 | −23,2 % |
| Saint-Leu | 3 994 | 82 | −18,5 % |
| Saint-Denis | 4 005 | 134 | −18,3 % |
| Entre-Deux | 4 186 | 17 | −14,6 % |
| **Saint-Paul** | **4 462** | 99 | **−8,9 %** |

- **Incohérence interne du socle** : 4900 est « sourcé Saint-Paul 2024 (~4 920) » — mais le
  neuf DVF de Saint-Paul mesure **4 462 (−8,9 %)**. Même la commune source ne supporte pas son
  propre socle. Les deux chiffres ne mesurent pas la même chose (observatoire/annonces vs
  ventes DVF ≤ 3 ans post-achèvement) : **quelle métrique fait foi est un arbitrage de phase B**,
  mais servir l'une (la plus haute) aux 23 communes de l'autre n'est défendable dans aucun des
  deux référentiels.
- **Résolution opérationnelle du parc non-écarté** (repli secteur → commune, comme score_e) :
  **66 090 / 77 718 parcelles (85,0 %)** résolues localement (8 840 au secteur, 57 250 à la
  commune) ; **11 628 (15,0 %) sans prix local**, concentrées sur 7 communes (§4), dont
  **10 brûlantes et 70 chaudes**.

## 2 · Écart de charge et bascules (échantillon seedé `m26-hyp`, 24 communes)

Réplique exacte du chemin cœur (`faisabilite/db.py:350-370` : `resolve_zone` → bassin →
`bilan_params.resolve` → `compute_bilan`), scénario A = servi tel quel (socle 4900 ou override
bassin), scénario B = prix local `dvf_prix_sortie_neuf` secteur→commune. Tirage stratifié
commune×tier (brûlantes exhaustives, 50/tier sinon) : **4 295 parcelles, 2 551 calculables**
sur les deux scénarios. Verdict « viable » = charge foncière médiane servie > 0.

**Périmètre socle strict (prix servi = 4900) : 2 378 calculables, 1 813 viables au socle →
1 717 basculent viable → non viable (95 %)**, 3 bascules inverses seulement (Trois-Bassins,
secteur DVF > 4900). Le sens attendu par le mandat est confirmé et quasi unilatéral.

Par commune (calc / viables socle → viables local / bascules V→NV) :

| Commune | calc | V socle → V local | V→NV |
|---|---|---|---|
| Saint-Benoît | 165 | 142 → 0 | 142 |
| Saint-Pierre | 179 | 157 → 4 | 153 |
| Le Tampon | 167 | 153 → 4 | 149 |
| Saint-Leu | 178 | 149 → 6 | 143 |
| L'Étang-Salé | 144 | 118 → 0 | 118 |
| La Possession | 158 | 117 → 0 | 117 |
| Sainte-Marie | 140 | 116 → 0 | 116 |
| Saint-Louis | 164 | 127 → 0 | 127 |
| Saint-Denis | 182 | 114 → 12 | 102 |
| Sainte-Suzanne | 121 | 99 → 0 | 99 |
| Le Port | 107 | 96 → 0 | 96 |
| Entre-Deux | 140 | 124 → 40 | 84 |
| Saint-Joseph | 155 | 81 → 0 | 81 |
| La Plaine-des-Palmistes | 131 | 73 → 0 | 73 |
| Petite-Île | 115 | 63 → 0 | 63 |
| Les Trois-Bassins | 107 | 67 → 24 | 46 (+3 NV→V) |
| Saint-Paul | 198 | 53 → 56 | 26 (+29 NV→V, artefact §2.1) |

**Treize communes tombent à ZÉRO viable au prix local** — aux coûts audités, le neuf local n'y
supporte plus d'opération de promotion sur l'échantillon. Comme le zéro dionysien du mandat
hypothèses : une information de MARCHÉ, servie aujourd'hui à l'envers par le socle.

### 2.1 · L'artefact Saint-Paul (à graver en préséance de phase B)

Les 29 NV→V de Saint-Paul ne sont PAS un effet du socle : ce sont des parcelles servies aux
**overrides de bassin des Hauts (3 400/3 500/3 900, sourcés quartier)** que le scénario B
écrase avec la médiane commune (4 462) — un repli MOINS local que la valeur servie. Préséance
à graver à l'application : **override sectoriel sourcé > DVF secteur > DVF commune** ; avec
elle, ces 29 ne bougent pas. Sur le périmètre des 5 bassins overridés : 173 calculables,
36 viables, 18 V→NV (bassins où l'override sourcé, déjà < 4900, reste > DVF local).

### 2.2 · Brûlantes (exhaustives) : 62 viables au socle → 47 basculent

**46 brûlantes au socle strict + 1 artefact bassin** (97415000EP1170, La Saline 6000 → commune
4 462, charge 0). Nominativement (commune · prix servi → local · charge socle → locale) :
97403000AM0815/AR1423/AR1511 (Entre-Deux), 97404000AW0199 (L'Étang-Salé), 97406000AI1016
(La Plaine-des-Palmistes), 97407000AH0233/AH1188/AS1075/AS1160/AY0575 (Le Port),
97408000AP1496/AT2026/BN3751 (La Possession), 97410000AS1425/CD0897/CD0907/CD0939/CD0943
(Saint-Benoît), 97411000AW1042/EL0656/EL0665/KA0296 (Saint-Denis), 97413000CM0749/CT0129/CX2191
(Saint-Leu), 97414000CH1740/EL0117/EL2067/EM1037/EN3984 (Saint-Louis), 97415000BW1480/BW1486
(Saint-Paul), 97416000ET1952/ET2141/ET2164/ET2166/ET2167/HP0798/HP0860 (Saint-Pierre),
97418000AT2317/AT2374/AT2379/AT2381/BH0995 (Sainte-Marie), 97422000BX1123/DM0647 (Le Tampon).
Détail à l'euro : `/tmp/mesure_prix_neuf_resultats.json`. Nota : 97410000AS1425 est une
**parcelle golden** (ancre) — le golden ne fige aucun champ de charge (§3), son PASS n'est pas
contredit.

Ratio charge socle/locale : médiane ×0,86 mais distribution violente (q1 ×0,25, q3 ×9,05,
négatifs fréquents) — le ratio est peu parlant ici car la plupart des charges locales passent
NÉGATIVES ; la métrique qui compte est la bascule de verdict.

## 3 · Question bloquante — les tiers servis bougent-ils ? NON, prouvé par les maillons

1. **Écrivain unique** de `parcel_p_score_v2` : `scoring/p_v2/pipeline.py:287` (`labuse
   score-v2`) — non exécuté (lecture seule intégrale ; re-run scoring interdit par le mandat).
2. **Aucune référence** à `bilan_params`, `dvf_prix_sortie_neuf`, `score_e`, `compute_bilan`,
   `prix_m2_neuf`, `sector_price` dans TOUTE la chaîne `scoring/` (grep récursif, 0 occurrence,
   `p_model` et `p_v2` inclus). Les seules features « prix » du modèle P
   (`med_pm2_terrain_36m`, `med_pm2_bati_36m`) sont des médianes de mutations DVF brutes
   (`p_model/ext_sql`), une autre table que `dvf_prix_sortie_neuf`.
3. **Run servi épinglé** : `Q_A_RUN_LABEL = "q_v7_defisc"` (`scoring/score_v_constants.py:46`) —
   l'application future (couche bilan/params) n'écrit pas dans les tables de scoring.
4. **`score_e` est en AVAL des tiers**, jamais en amont (`ingestion/score_e.py:91` : `WHERE
   s.run_id = :run AND s.tier <> 'ecartee'`) — un recalcul de score_e changerait les marges
   affichées, pas les tiers.
5. **Mesuré** : golden 116/116 PASS et tiers au bit près, en ouverture ET en clôture de phase A.

**Honnêteté de la preuve (même clause qu'au mandat hypothèses)** : la référence golden ne
couvre AUCUN champ bilan/charge. À l'application, les charges bougeront SANS faire bouger le
golden — le golden protège cascade/tiers/zonages/ancres, pas ce périmètre. La condition
d'arrêt de l'application reste : un tier qui bouge = arrêt.

**Risque résiduel déclaré** : si la phase C re-exécute `build_prix_neuf` (rebuild
`DROP TABLE`+`INSERT` de `dvf_prix_sortie_neuf`), le snapshot `score_e` servi (77 718 lignes du
21/07) ne bouge pas tout seul ; un `score-e` relancé ensuite changerait `marge_estimee` sur la
fiche — impact fiche, pas tiers. À mesurer au moment C, pas avant.

## 4 · Les 7 communes sans valeur locale — repli recommandé

Saint-André (5 340 non-écartées), Saint-Philippe (2 232), Sainte-Rose (1 220), Les Avirons
(840), Cilaos (820), Bras-Panon (686), Salazie (490) = **11 628 parcelles (15,0 %)**, dont
10 brûlantes / 70 chaudes. Ces 7 communes totalisent **17 ventes neuves à elles sept** (< 5
chacune, seuil `N_MIN`) : il n'y aura pas de valeur locale DVF à court terme. Sur l'échantillon,
**565 / 763 parcelles sans prix local sont servies « viables » aujourd'hui au prix
saint-paulois** (dont 8 brûlantes : 7 Saint-André + 1 Salazie) — le statu quo est la pire option.

**Recommandation : repli à la médiane île `dvf_prix_sortie_neuf` = 3 688 €/m² (765 ventes,
mesurée — pas inventée), niveau tracé `ile`, `is_placeholder=true`, étiquette imposée :
« Estimé — repli île, aucune vente neuve suffisante sur la commune ».**
Arguments : (a) c'est le même geste que le repli secteur→commune déjà tracé par score_e,
prolongé d'un cran, avec le niveau VISIBLE au bandeau ; (b) −25 % sous le socle actuel — le
sens non-optimiste est préservé pour les 7 communes (toutes rurales/est, vraisemblablement
sous la médiane île : le repli reste optimiste PAR RAPPORT à leur marché réel, d'où
l'étiquette placeholder qui maintient la pression de calibration) ; (c) l'alternative stricte
« pas d'override → prix DVF existant » retombe sur l'ancien dilué (~2 265) dont O0 a montré
qu'il écrase tout — trop pessimiste pour être une mesure, et silencieux au bandeau.
Alternative si Vic préfère la doctrine dure « on n'invente pas de prix » : **non estimable**
(pas de bilan chiffré sur ces 7 communes, comme score_e sait le faire) — défendable, mais
prive la fiche de tout ordre de grandeur là où le Copilote sert déjà des verdicts.
**Étiquette : décision Vic, formulation à verrouiller par test comme les précédentes.**

## 5 · Conclusion — requalification demandée (point d'arrêt Vic)

L'ampleur est **comparable et même supérieure à celle du coût de construction** : 95 % des
viables du périmètre socle basculent (coût : 52 %), le levier est le premier de l'équation
(±17,6 % de prix = ±102 % de charge — annexe), le motif est le même (une valeur d'un cas
particulier servie par défaut à tous, dans le sens généreux, troisième occurrence), et il
reste optimiste APRÈS la correction du coût : les deux couches se cumulent (sur 2 551
calculables, 146 restent viables aux prix locaux, 5,7 %). **En application de la règle du
mandat (§2.1), c'est un mandat de même priorité, pas une suite.** L'application (résolution
par commune, préséance override sourcé > DVF secteur > DVF commune > repli île étiqueté,
le 4900 ne survivant — au plus — que comme valeur Saint-Paul à réconcilier avec le 4 462 DVF)
attend l'arbitrage du point d'arrêt.

## Annexe — sensibilité des autres paramètres vivants (témoin CX1395, chemin cœur répliqué)

Charge de base au servi actuel : **−168 723 €** (le témoin résout sur le bassin Plateau
Caillou, override 3 500 — l'illustration du mandat §1, charge 237 k€, supposait le socle
4900 : la charge servie du témoin est en réalité DÉJÀ négative). Variations un paramètre à la
fois, en % de la charge de base :

| Param (valeur) | ±17,6 % | ±50 % |
|---|---|---|
| `prix_m2_neuf` (3500 ici) | **∓102 %** | ∓290 % |
| `honoraires_pct` (12) | ±16 % | ±46 % |
| `marge_cible_pct` (9) | ±12 % | ±34 % |
| `cout_vrd_base` (90) | ±7 % | ±20 % |
| `frais_financiers_pct` (3) | ±4 % | ±11 % |
| `majoration_vrd_assainissement_pct` (25) | ±1 % | ±4 % |
| `majoration_vrd_pente_pct` (30) | 0 % (pente < 15 % ici) | 0 % |
| `prix_m2_lls` (2900) | 0 % (hors mixité ici) | 0 % |

La hiérarchie analytique du §1 du mandat est confirmée par la mesure, au point près. Le
levier prix est hors catégorie ; viennent ensuite honoraires et marge (bloc « retour
promoteur » de la phase B), puis le bloc VRD (§2.2 du mandat, ordre de grandeur à confirmer
par devis — sa sensibilité en % est faible mais la crainte du mandat porte sur un facteur
2-3×, pas sur ±17,6 %).

## Artefacts

Scripts LECTURE SEULE : `/tmp/mesure_prix_neuf_phaseA.py` (mesure principale, seed `m26-hyp`),
`/tmp/annexe_sensibilite_params.py` (annexe). Résultats à l'euro :
`/tmp/mesure_prix_neuf_resultats.json` (4 295 lignes). Relevés d'état :
`/tmp/tiers_ouverture_calibration.txt`, golden 116/116 en ouverture et clôture (stdout).
