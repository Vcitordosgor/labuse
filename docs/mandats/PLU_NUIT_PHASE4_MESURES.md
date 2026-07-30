# PLU-SÉRIE-NUIT — PHASE 4 : MESURES GROUPÉES (28/07/2026)

**Nature** : campagne de MESURE, rien d'autre — aucun re-run de scoring, aucun contact
avec le champion P, aucune correction (code, YAML, base : rien n'est modifié).
**Périmètre** : les 17 communes de la nuit + la consolidation Saint-Paul, sur base
harmonisée (doctrines a/b, arbitrages du matin, hypothèses bilan 2300-2800 mergées).
**Base** : run servi `q_v7_defisc`, base locale, API 8010 déjà en service (réutilisée
telle quelle, jamais redémarrée). Toutes les requêtes : SELECT uniquement.
**Artefacts vérifiables** : `reports/plu-phase4/` — un JSON par commune (échantillon
10 parcelles détaillé avant/après + stats 400), `populations.json` (pools par zone),
et les deux scripts de mesure (`mesure_ecart.py`, `populations.py`).

---

## 0 · Golden et tiers — AVANT et APRÈS la campagne : au bit près

| Contrôle | Avant toute mesure | Après toutes les mesures |
|---|---|---|
| `qa/golden_check.py` (API 8010 + DB) | **116/116 PASS, 0 FAIL** | **116/116 PASS, 0 FAIL** |
| Tiers `q_v7_defisc` | 120 / 1031 / 3587 / 72980 / 353945 | **identiques au bit près** |

Aucun tier n'a bougé. La campagne n'a rien écrit.

## 1 · Méthodologie (identique à la campagne Saint-Pierre/Saint-Paul/Saint-Denis)

Reprise à l'identique de `qa/plu_saint_pierre_validation_b.py` (celle qui a établi les
−33/−33/−53 %) : pool servi = `parcel_p_score_v2` run `q_v7_defisc`, `tier <> 'ecartee'`,
par commune ; `random.seed(42)`, 400 parcelles ; moteur complet `parcel_faisabilite`
(géométrie réelle insetée, clip U/AU, ER déduits, prospect, hypothèses YAML).
**Une différence assumée** : la passe « avant » (repli) est obtenue en substituant
`resolve_zone → _zone_generique` EN MÉMOIRE (équivalent exact « commune sans YAML »,
`plu_rules.py:178`) au lieu de déplacer le YAML sur disque — l'API tourne, et le YAML
Saint-Paul porte aussi les `Hypotheses` du moteur (le déplacer fausserait la mesure).
Échantillon 10 : zones triées par pool servi décroissant, 1 parcelle par zone (idu
minimal) en round-robin — déterministe, re-jouable, vérifiable à la main.

## 2 · Écart repli → calibré, 400 parcelles/commune

| Commune | Pool servi | n 2 passes | Q25 | **Médiane** | Q75 | min / max | SDP méd. avant→après | Perdent tout | Gagnent |
|---|---|---|---|---|---|---|---|---|---|
| Saint-Paul | 13155 | 366 | -33.4 % | **-33.0 %** | +0.0 % | -95.4 / +67.2 % | 339 → 262 m² | 5 | 0 |
| Saint-Joseph | 6265 | 324 | -53.9 % | **-46.1 %** | -42.0 % | -91.3 / +0.0 % | 342 → 182 m² | 21 | 0 |
| Saint-Benoît | 3676 | 358 | +0.0 % | **+0.0 %** | +0.0 % | +0.0 / +0.0 % | 316 → 312 m² | 9 | 0 |
| Saint-Louis | 3604 | 329 | -33.8 % | **-33.3 %** | +33.3 % | -64.1 / +72.7 % | 286 → 224 m² | 13 | 0 |
| La Possession | 3175 | 332 | -50.1 % | **-40.2 %** | -32.7 % | -96.6 / +7.5 % | 371 → 247 m² | 44 | 0 |
| Sainte-Marie | 2994 | 332 | -36.3 % | **+0.0 %** | +33.0 % | -87.0 / +100.0 % | 355 → 328 m² | 33 | 0 |
| L'Étang-Salé | 1554 | 364 | -33.3 % | **+0.0 %** | +33.3 % | -70.8 / +35.3 % | 328 → 329 m² | 18 | 0 |
| Petite-Île | 1354 | 301 | -62.5 % | **-37.7 %** | -33.3 % | -83.1 / +557.1 % | 333 → 167 m² | 10 | 0 |
| Le Port | 1333 | 308 | -6.8 % | **+0.0 %** | +26.8 % | -78.6 / +2354.8 % | 188 → 197 m² | 70 | 0 |
| Sainte-Suzanne | 1303 | 339 | -5.1 % | **+0.0 %** | +33.1 % | -43.1 / +42.9 % | 297 → 277 m² | 8 | 0 |
| Sainte-Rose | 1220 | 347 | -37.1 % | **-33.3 %** | +0.0 % | -76.1 / +0.0 % | 412 → 309 m² | 12 | 0 |
| Entre-Deux | 1175 | 380 | -33.3 % | **+0.0 %** | +0.0 % | -67.7 / +0.0 % | 334 → 292 m² | 0 | 0 |
| Les Avirons | 840 | 338 | -39.3 % | **-21.4 %** | +4.4 % | -63.2 / +1015.8 % | 319 → 218 m² | 13 | 23 |
| La Plaine-des-Palmistes | 828 | 335 | -72.0 % | **-51.3 %** | -44.5 % | -89.7 / -36.9 % | 514 → 233 m² | 26 | 0 |
| Cilaos | 820 | 382 | -45.6 % | **-34.5 %** | -33.3 % | -66.8 / +0.0 % | 378 → 236 m² | 1 | 0 |
| Les Trois-Bassins | 742 | 324 | -48.0 % | **-33.7 %** | -33.2 % | -81.6 / +32.9 % | 304 → 186 m² | 26 | 0 |
| Bras-Panon | 686 | 292 | -60.9 % | **-52.5 %** | -48.2 % | -94.3 / -40.8 % | 256 → 127 m² | 46 | 0 |
| Salazie | 490 | 360 | +32.5 % | **+33.3 %** | +33.4 % | -35.7 / +36.8 % | 447 → 540 m² | 1 | 0 |

(« n 2 passes » = parcelles constructibles aux deux passes, base des quartiles — même
définition que la campagne de référence. « Perdent tout » = constructibles au repli,
capacité nulle au calibré ; « Gagnent » = l'inverse.)

### Verdict

- **Le −33 % est CONFIRMÉ** : médiane des 18 médianes = **−33,2 %**. Saint-Paul re-mesuré
  à −33,0 % — la campagne re-trouve exactement le chiffre historique, le harnais est
  validé par construction. 12 communes sur 18 à médiane ≤ −21 % ; 5 dépassent −40 %
  (Bras-Panon −52,5, PdP −51,3, Saint-Joseph −46,1, La Possession −40,2 — gamme du
  Saint-Denis historique à −53).
- **356 parcelles sur 6 111 perdent toute constructibilité** au calibré (gels exacts,
  habitat-interdit, hauteurs réelles) ; **23 en gagnent** — toutes aux Avirons, cf. §3.2.

## 3 · Anomalies et signaux (aucune n'est une curiosité)

1. **SALAZIE : +33,3 % — LE REPLI Y ÉTAIT PESSIMISTE.** Seule commune à médiane
   positive, et ce n'est pas un artefact : UA/UB/UT/AUb/AUt/AUe sont gravées
   **hé = 12 m** (Art. U 10.2, p.13 « 12 mètres à l'égout du toit ou au sommet de
   l'acrotère » ; Art. UT 10.2, p.22 ; Art. AUe 10.2, p.34), contre 9 m génériques →
   4 niveaux au lieu de 3, +33 % de SDP, reculs identiques au défaut (3 m). C'est le
   **premier contre-exemple mesuré** au « le repli ne se trompe que dans un sens »
   (établi sur 1 200 parcelles de 3 communes) : sur 18 communes, le biais du repli est
   massivement optimiste, mais PAS uniformément. Le mandat « Repli non optimiste » doit
   le savoir : un repli durci uniformément sous-estimerait Salazie encore plus.
2. **LES AVIRONS : les 23 seuls « gagnants » de la campagne** (0 sur 1 200
   historiquement). Cause vérifiée sur pièces : parcelles minuscules (117-206 m²)
   vidées par le recul séparatif générique de 3 m (« trop exigu »), mais le règlement
   calibré fixe le retrait à **1,9 m** (Art. U 7.2, p.11) → le contour inseté survit.
   SDP gagnées dérisoires : 8 à 34 m² (0-1 logement). Réel, sourcé, sans enjeu produit.
3. **Six médianes à 0,0 % — trois causes distinctes, aucune n'est un bug** :
   - *Quantification des niveaux* (Entre-Deux, L'Étang-Salé, Sainte-Suzanne, en partie
     Sainte-Marie/Le Port) : la zone dominante calibrée a hé ∈ [9 ; 11] m → même nombre
     de niveaux que le générique 9 m (÷3 m). L'écart réel est dans les quartiles
     (ex. Sainte-Marie Q25 −36,3 / Q75 +33,0 : les hauteurs vraies 15-27 m d'un côté,
     les reculs doctrine b de l'autre).
   - *Saint-Benoît : delta structurellement nul, et ce n'est PAS rassurant* — après la
     refonte `f55416a` (hauteurs par secteurs graphiques), le YAML n'a plus AUCUNE zone
     habitat-admis calibrée en hauteur : les deux passes servent le générique presque
     partout (min = max = 0). La mesure d'écart y est SANS OBJET tant que le mandat
     « règlement graphique » n'existe pas ; seuls les 9 perdants (habitat-interdit
     st-liste) témoignent du calibrage.
   - *Le Port* : moitié du pool en Ua hé 9 = générique (delta 0), l'autre en Ub/Uc/Ud
     13-21 m → Q75 +26,8 et l'outlier ci-dessous.
4. **Queues extrêmes positives vérifiées** : Le Port `97407000AO0803` **+2 355 %**
   (31 → 761 m² : Ud hé réel R+6, Art. Ud 8, p.68, emprise réelle 302 m² là où le
   repli 3 m vidait presque le contour) ; Avirons +1 016 % et Petite-Île +557 %, même
   mécanique (recul réel < 3 m et/ou hauteur réelle > 9 m sur petite parcelle). Le
   repli se trompe AUSSI vers le bas sur les petites parcelles denses — dans les deux
   cas c'est le calibré qui a raison.

## 4 · Échantillons 10 parcelles avant/après (vérifiables à la main)

Un tableau détaillé par commune est livré dans `reports/plu-phase4/<slug>.json`
(clé `echantillon10`) : pour chaque parcelle — idu, surface, zone de la couche, et pour
chaque passe : SDP, hauteur retenue, emprise constructible, emprise bâtie, verdict,
**article invoqué** (source de l'étape « niveaux »). Exemple (Bras-Panon) :

| Parcelle | Zone | AVANT (repli) | APRÈS (calibré) | Article invoqué |
|---|---|---|---|---|
| 97402000AH0040 (357 m²) | Ub | SDP 183 m², h 9 m, empr. 136 m² | SDP 70 m², h 6 m, empr. 78 m² | Art. UB 10.2, p.29 |
| 97402000AH0007 (187 m²) | Uba | SDP 47 m², h 9 m, empr. 35 m² | SDP 5 m², h 6 m, empr. 5 m² | Art. UB 10.2, p.29 |
| 97402000AB0131 (392 m²) | Uc | SDP 225 m², h 9 m, empr. 167 m² | SDP 99 m², h 6 m, empr. 110 m² | Art. UC 10.2, p.43 |

## 5 · Pools servis réels des populations en attente (mandat « Repli non optimiste »)

Comptes par zone : jointure `parcel_p_score_v2` (servi) × `parcels` ×
`spatial_layers kind='plu_gpu_zone'` via `ST_PointOnSurface(geom_2975)` — détail
zone par zone dans `reports/plu-phase4/populations.json`.

### 5.1 · Les 15 zones de dette de calibrage — 878 parcelles servies, dont 553 en générique

Les 15 = zones à hé ET hf non chiffrés dans les 21 YAML. Elles se décomposent (les
« 11 zones sans hauteur » du mandat en sont le sous-ensemble qui retombe réellement
en générique) :

| Classe | Zones | Pool servi |
|---|---|---|
| **11 « sans hauteur » → repli générique 9 m servi AUJOURD'HUI** (cœur du mandat) | La Possession UAv 50, AUAv 16, AUBm 124 · Saint-Denis Uavap **302**, AUx 44, Uat 4, Upi 2, Udo 0, Uma 0, Upr 0 · Saint-Pierre AUdma 11 | **553** |
| 3 prospect (hauteur calculée PAR PARCELLE — pas une dette moteur) | Saint-Denis Ud 295, Udp 27, Uu 3 | 325 |
| 1 en mode strict (non calculable, jamais servie) | Saint-Paul U1lec — libellé ABSENT de la couche (le zonage sert « U1l ») | 0 |

### 5.2 · Les 92 libellés gelés (population e) — 1 229 parcelles servies, capacité 0 exacte

Total vérifié : exactement 92 entrées `zones_au_st` sur les 21 YAML. Pool servi
cumulé **1 229**. Têtes : Saint-Pierre Us 139, Le Port Ue 97, Saint-Paul AU3st 97,
Saint-Benoît Ue 94, Saint-Paul AU1st 79, Le Tampon 2AUc 78, La Possession AUst 60.
**16 libellés à pool servi nul** (zone présente dans la couche, aucune parcelle servie
dedans — vérifié polygone par polygone) ; **2 anomalies de graphie Saint-Paul** :
« AU1e st » (YAML) vs « AU1est » (couche — rattrapée par la regex `AU\w*st` de
`resolve_zone`, gel effectif, pool 8 avec U1l) et « AU4st » absente de la couche.

### 5.3 · Les 14 zones habitat-interdit gelées — 238 parcelles servies

Petite-Île UF 3, UFcim 1, AUF 2 · Le Port Ue 97, Up 5, Uppp 1, Uv 26, 1AUe 3, 1AUv 0 ·
Saint-Benoît Ue 94, Up 3, Ut 0, AUe3 1, AUp1 2. **Total 238** — pour ces parcelles la
capacité 0 est déjà exacte (st-liste), c'est l'étiquette « secteur de transition » qui
ment (friction F2, exigence v2). À signaler en marge de la classe : Les Avirons Ub5
(non aedificandi, pool 1) et AUes (éco stricte gelée, pool 7) partagent la mécanique
sans être comptés dans les 14.

### 5.4 · Les 89 emprises implicites — 17 797 parcelles servies, mais 76/89 zones bornées par la pleine terre

Définition retrouvée qui tombe exactement sur 89 : zones calibrées à
`emprise_sol_pct: null` sur le périmètre **17 communes de la nuit + Saint-Paul**
(tous statuts confondus). Pool servi cumulé **17 797** — mais la mesure qui compte :

- **76 zones sur 89 ont un % pleine terre/perméable gravé** (doctrine a) → l'emprise y
  est DÉJÀ indirectement bornée (cap `1 − pleine_terre` dans le moteur) : 17 560 parcelles.
- **13 zones seulement sans AUCUNE borne d'emprise** (ni %, ni pleine terre) :
  **237 parcelles servies** — le vrai reliquat « emprise bornée par les seuls reculs ».

Têtes de pool (toutes bornées par la pleine terre) : Saint-Paul U3c 2 730, U6c 2 642,
U2c 1 445, U5b 1 046 · La Possession UB 1 372 · Entre-Deux Ub 714.

### 5.5 · Population d — cascade vs habitat-interdit calibré : 1 005 parcelles servies (mesure ajoutée sur demande Vic, clôture de phase 4)

Parcelles classées POSITIVES par la cascade (`tier <> 'ecartee'`) dont la zone porte
`habitat: interdit` dans une entrée `zones:` d'un YAML calibré (87 zones sur les
21 communes — hors les 14 gelées du §5.3, comptées à part). Détail zone par zone dans
`reports/plu-phase4/population_d.json`.

| Commune | brûlante | chaude | réserve | à creuser | TOTAL |
|---|---|---|---|---|---|
| Saint-Pierre | 0 | 9 | 30 | 253 | **292** |
| Sainte-Marie | 0 | 7 | 23 | 206 | **236** |
| Le Tampon | 0 | 1 | 10 | 87 | 98 |
| Saint-Louis | 0 | 1 | 22 | 49 | 72 |
| Saint-Joseph | 0 | 2 | 10 | 51 | 63 |
| L'Étang-Salé | 0 | 0 | 5 | 53 | 58 |
| Le Port | 0 | 1 | 4 | 40 | 45 |
| Bras-Panon | 0 | 0 | 0 | 40 | 40 |
| La Possession | 0 | 1 | 6 | 20 | 27 |
| Sainte-Suzanne | 0 | 0 | 0 | 25 | 25 |
| Les Avirons | 0 | 0 | 4 | 15 | 19 |
| Petite-Île | 0 | 0 | 0 | 12 | 12 |
| La Plaine-des-Palmistes | 0 | 0 | 0 | 11 | 11 |
| Les Trois-Bassins | 0 | 2 | 0 | 1 | 3 |
| Salazie | 0 | 0 | 1 | 2 | 3 |
| Saint-Paul | 0 | 0 | 0 | 1 | 1 |
| **TOTAL** | **0** | **24** | **115** | **866** | **1 005** |

Têtes de zone : Sainte-Marie UEm 139 · Saint-Pierre Uazi 134, Uazc 53, Uaza 52 ·
L'Étang-Salé UE 41 · Le Tampon UCtom 37. **Aucune brûlante** ; 24 chaudes concernées.
Pour toutes ces parcelles le moteur de faisabilité rend déjà capacité 0 exacte
(`engine.py:157`) — c'est la CASCADE qui les classe positives sans lire le règlement.

### 5.6 · Sous-ensemble U/AU des 3 communes résiduelles — ce que le calibrage n'a PAS résorbé

| Commune | Pool servi | dont U/AU (servi en GÉNÉRIQUE) | Détail têtes |
|---|---|---|---|
| Saint-André | 5 340 | **5 290** | UC 3078, UB 1661, UD 159, UA 128… |
| Saint-Leu | 6 016 | **5 927** (+25 parcelles sans polygone zone) | UC 2351, UD 2111, UB 514, UCA 360… |
| Saint-Philippe | 2 232 | **0 zone PLU en couche** (RNU — aucun polygone `plu_gpu_zone`) | — |

**11 217 parcelles servies restent en estimation générique U/AU** sur Saint-André et
Saint-Leu (dépubliés GPU — dossiers d'appel prêts), plus 2 232 à Saint-Philippe sans
zonage du tout. C'est, en creux, la mesure de ce que les 21 calibrages ont résorbé :
hors ces 3 communes, le U/AU servi de l'île est calibré ou gelé-exact.

## 6 · Poids réel du mandat « Repli non optimiste » (re-priorisé par Vic, 28/07/2026)

| Population | Pool servi mesuré | Priorité |
|---|---|---|
| **e** — 92 gelés classés positifs par la cascade | **1 229** | **1 — d'abord** (la plus lourde, la seule à toucher le scoring servi avec d) |
| **d** — cascade vs habitat-interdit calibré | **1 005** (0 brûlante, 24 chaudes) | mesurée en clôture — à arbitrer (même mécanique que e) |
| **b** — 11 zones sans hauteur, générique optimiste servi | **553** (Uavap 302) | 2 — ensuite |
| **a** — 14 habitat-interdit gelées (capacité déjà exacte, étiquette fausse) | 238 | 3 — en dernier |
| **c** — emprises implicites | ~~17 797~~ → **237** (76/89 zones bornées par la pleine terre gravée — produit dérivé, non recherché, de la passe d'harmonisation doctrine a) | 3 — DÉCLASSÉE en note |

Total mesurable ≈ 2 250 parcelles (a+b+c+e) + 1 005 (d). Nettement moins que redouté.
Mise à jour gravée dans le mandat lui-même (`PLU_SAINT_PIERRE_RAPPORT.md` §6bis).

Doctrine (leçon 24 du mandat-cadre, gravée ce jour) : **le repli générique n'est pas
systématiquement optimiste, il est ARBITRAIRE** — optimiste dans 17 communes sur 18
parce que 9 m est sous la plupart des plafonds réunionnais, mais rien ne le garantit
(Salazie hé 12 sourcé : −33 % de sous-estimation ; queues positives +2 355 %).
L'argument du calibrage est l'exactitude, pas la correction d'un biais unidirectionnel :
on ne vend pas « on corrige une surestimation », on vend « on lit le règlement ».

## 7 · Dette de calibrage prioritaire : Saint-Benoît

**Commune de 21 671 parcelles. Dette « muette en capacité » REQUALIFIÉE (arbitrage Vic
30/07, mandat V8-VERIF B'.3) : la dette réelle vaut 2 743 parcelles — les zones U/AU sans
capacité résiduelle. Les 6 928 autres muettes sont en A/N (agricole/naturel) = absence
RÉELLE et légitime, pas une dette. Ne plus écrire « 21 671 muettes ».** Historique : depuis
la refonte hauteurs-par-secteurs-graphiques (`f55416a`), les zones habitat-admis manquaient
de hauteur exploitable. Son déblocage ne passe pas par
une re-extraction mais par le **schéma v2 (hauteur par calque graphique)** — mandat
« règlement graphique » à ouvrir. À traiter comme dette de calibrage n°1 des
21 communes gravées.

---

**Exécution** : 28/07/2026, session unique, base jamais écrite, API jamais redémarrée,
champion P jamais consulté. Golden et tiers vérifiés au bit près en ouverture ET en
clôture (§0). Scripts et JSON de mesure versionnés sous `reports/plu-phase4/`.
