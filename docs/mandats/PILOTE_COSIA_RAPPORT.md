# PILOTE CoSIA 2025 — rapport de validation (arbitrage Vic 04/08)

> **POINT D'ARRÊT respecté : rien n'est branché au scoring.** Données CoSIA en table QA
> (`qa_cosia_bati`, 445 190 polygones classe « Bâtiment », EPSG:2975 natif). Vérité terrain =
> l'échantillon de 100 classé à la main (qa/dette4/echantillon100_classement.tsv).

## Durée de calcul (mesurée)
| étape | durée |
|---|---|
| Téléchargement CoSIA D974 2025 (7z, 518 Mo) | ~13 min |
| Extraction (37 dalles GPKG, 2,9 Go) | ~1 min |
| Chargement classe Bâtiment → PostGIS (445 190 polygones) | **7 s** |
| Mesures de validation (100 parcelles + Saint-Paul) | 1 s |

Le pipeline complet tient en ~15 minutes — l'île entière, pas seulement Saint-Paul.

## Taux bruts (seuil : > 20 m² CoSIA-Bâtiment intersectés)
| population vérité terrain | CoSIA voit du bâti | taux |
|---|---:|---|
| 38 bâties | 30 | **rappel brut 79 %** |
| 41 nues | 6 | **fausses détections brutes 15 %** |
| 21 douteuses | 13 | 62 % |

**Au brut, le seuil de déploiement (≥ 90 %) n'est PAS atteint.** Mais l'adjudication des
14 discordances (cartes une à une, CoSIA superposé à l'ortho —
`qa/dette4/pilote_cosia_discordances.pdf`, pour ta contre-revue) change le tableau :

## Adjudication des 8 « ratées » : 8/8 sont des erreurs de MA vérité terrain
- AC2972, HA0440 : parcelles à BRANCHES — les toits voisins sont dans les enclaves, PAS dans
  la parcelle (les branches sont des voies/cours). Classées « bâties » à tort à zoom grossier.
- AO0912, CW1433, CW2399 : le toit que j'avais vu est HORS contour (voisin mitoyen).
- CY0677 : cour en dur, au mieux douteuse. BD3665, BV3186 : empiètements de bord marginaux
  (le « trace marginale » de tes cartes 5/9).

→ **Rappel ajusté : 30/30 vraies bâties = 100 %** (conservateur : ≥ 97 %). Critère atteint —
mais l'ajustement vient de moi : les 14 cartes te permettent de trancher toi-même.

## Adjudication des 6 « fausses détections » : ~0-2 vraies fausses
- **AB1908 (160 m²), CD0937 (87 m²), DE1235 (87 m²)** : CoSIA voit une MAISON là où notre
  ortho de revue montre un chantier/dalle → **écart de MILLÉSIME, pas une erreur** (voir
  découverte ci-dessous). Ces maisons existent probablement aujourd'hui.
- **ER1172 (139 m²)** : une structure claire est visible SOUS le polygone CoSIA même sur notre
  ortho — ma « nue » était fausse.
- **AM0816, AC2409 (28 m²)** : petits abris/annexes au ras du seuil de 20 m² — un seuil
  produit à ~50 m² les élimine.

→ **Fausses détections nettes : ~0-5 %**, gérables par seuil de surface.

## DÉCOUVERTE MÉTHODOLOGIQUE — l'ortho de nos revues n'est pas 2025
Le WMTS `ORTHOIMAGERY.ORTHOPHOTOS` (mosaïque « la plus récente » de la Géoplateforme) montre
des CHANTIERS là où CoSIA 2025 voit des maisons finies (AB1908, CD0937…). Sur ces zones, la
mosaïque servie est ANTÉRIEURE au millésime 2025. Conséquences :
1. Nos revues visuelles (les 100, les 46, les 14) sous-estiment le bâti RÉEL — le vrai taux
   d'erreur de la couche BD TOPO est PIRE que les 38 % mesurés.
2. CoSIA 2025 est plus frais que tout ce que nous regardons — y compris nos yeux.
3. Doctrine déjà gravée qui s'applique une 3ᵉ fois : « la fraîcheur d'une couche n'est pas sa
   date d'ingestion mais celle de sa source amont » — vrai aussi pour l'ortho de revue.

## Effet estimé sur les têtes servies de Saint-Paul
169 têtes servies (brûlantes+chaudes) à couche < 20 m² sans indice → **CoSIA voit du bâti sur
73 (43 %), dont 8 brûlantes.** Extrapolation cohérente avec l'échantillon île (38 %+).

---
# ADDENDUM — arbitrages Vic (2ᵉ passe) : ortho datée, seuil 50, inventaire, audit

## CORRECTION (la 2ᵉ) — l'ortho de revue N'ÉTAIT PAS périmée
Le graphe de mosaïquage (WFS `ORTHOIMAGERY.ORTHOPHOTOS.GRAPHE-MOSAIQUAGE`) date les 14 zones de
discordance : **toutes PVA 2025, vols du 21/07 au 02/08/2025, 20 cm** — et `DEFAUT` ≡ `HR`
(tuiles byte-identiques). Ma « découverte » d'un WMTS périmé est RETIRÉE : CoSIA 2025 dérive
des MÊMES vols que l'ortho de revue. Les divergences sont des différences de LECTURE (l'œil dit
« chantier/dalle = nue », CoSIA dit « Bâtiment » — produit-parlant, CoSIA a raison : un chantier
n'est pas une opportunité) + mes erreurs de vérité terrain. **Le 38 % reste le taux de
référence, ni pire ni meilleur.** L'exigence d'afficher la date reste — elle aurait évité les
deux allers-retours.

## Cartes datées (exigence appliquée)
Helper `qa/dette4/ortho_dates.py` (date_vol au centroïde via le graphe). Régénérés AVEC date de
prise de vue sur chaque carte : les **14 discordances** (`pilote_cosia_discordances.pdf`), les
**90 cadastre**, les **32 restantes**. La carte AB1908 datée (vol 2025-07-22) montre une
structure à toit clair sous le polygone CoSIA — ta contre-revue tranchera. AB1910 : CoSIA
**0 m²**, vraiment nue, son verdict tient. AB1911 : CoSIA 100 m² (déjà sortie par pondération).

## Seuil 50 m² — RÉFUTÉ par la mesure
| seuil | rappel brut /38 | fausses brutes /41 |
|---|---|---|
| 20 m² | 30 (79 %) | 6 (15 %) |
| 50 m² | **24 (63 %)** | 4 (10 %) |

Le seuil 50 perd **6 vraies maisons** que CoSIA ne voit qu'à 23-45 m² (débords de toit,
segmentation partielle sous végétation) et ne retire que les 2 abris — les 4 « fausses »
restantes sont de vraies structures de toute façon. **Reco : seuil 20 m² conservé, cas limites
à l'adjudication, pas au seuil.** Ta consigne « mesure d'abord » a évité un mauvais réglage.

## Inventaire rétroactif des revues visuelles depuis le 29/07
| revue | cartes | ortho | verdicts photo-dépendants | à refaire ? |
|---|---:|---|---|---|
| Division en or v8 (29/07-04/08) | 24 + PDF | WMTS = PVA 2025 | géométrie/assemblage | non |
| Cartes assemblage AU (30/07) | 5+3 | idem | voisinage | non |
| Revue 46 → 14 retirées (04/08) | 47 | idem | « bâtie » (tient a fortiori) | **non — verdicts bâties robustes** |
| AB1908/AB1910 « tiennent » (04/08) | 2 | idem | « nue » | **AB1908 : à re-trancher** (structure visible carte datée + CoSIA 160 m²) ; AB1910 confirmée nue |
| Échantillon 100 (04/08) | 25 grilles | idem | bâti/nu | non (biais = lecture, pas millésime ; 8 erreurs identifiées et documentées) |
| 82 mouvements pondération | 82 | idem | aucun (informatif) | non |
| EBC/ER (train 2) | 4 captures app | — | aucun | non |

**Bilan : 0 revue à refaire pour cause d'ortho périmée** (l'ortho était 2025). Une seule
re-décision : **AB1908** (la tienne, sur carte datée). Toute carte porte désormais la date.

## Audit des dates — DVF / Sitadel / BODACC / DPE (question 6)
| couche | horizon SOURCE (donnée la plus récente) | sync (ingestion) | verdict |
|---|---|---|---|
| **DVF** | **2025-12-31** | **absente de data_sources** | **le pire cas : 7 mois d'angle mort, non affiché, sync non tracée** |
| DPE | 2026-07-03 | 2026-07-12 | sain |
| Sitadel | **2026-08-17 (FUTUR !)** | 2026-07-10 | anomalie de parse à corriger (un permis daté après aujourd'hui) |
| BODACC | 2026-07-02 | 2026-07-05 | sain, resync à cadencer |

Structurel : `data_sources` ne porte QUE `last_sync_at` (ingestion). **Aucune colonne
« millésime amont »** — la règle de conception de Vic exige de l'ajouter et de l'afficher.

## Recommandation (ton arbitrage — rien n'est branché)
1. **GO déploiement CoSIA comme couche « bâti frais »**, avec un seuil produit à ~50 m²
   (re-mesure du couple rappel/fausses détections à ce seuil avant branchement).
2. Contre-revue Vic des 14 discordances (PDF fourni) pour valider mon adjudication.
3. Architecture proposée au branchement (après ton GO) : CoSIA n'écrase PAS spatial_layers —
   nouvelle emprise `p_model_bati_cosia` par parcelle, consommée par le déclassement/filtre à
   côté de la BD TOPO (le max des deux emprises), datée, régénérable à chaque millésime.
4. Remplacer l'ortho des revues par le flux du millésime 2025 explicite (ou CoSIA en fond)
   pour ne plus juger sur une photo en retard.

---
# BRANCHEMENT (GO Vic post-contre-revue) — table construite, effet mesuré, ARRÊT

## Contre-revue Vic des 14 — verdicts appliqués
Cartes 1-2, 4-8 : vérité terrain fausse, confirmé · carte 3 (CY0677) : requalifiée douteuse ·
cartes 9-12 : parcelles BÂTIES (vérité fausse) · 13-14 : abris ≤ 28 m², non disqualifiants.
- **AB1908 retirée** (brûlante 139 → declasse_non_constructible, journal : « bâti confirmé
  CoSIA + contre-revue Vic 04/08 (PVA 22/07/2025, 160 m²) »).
- **AB1910 : CoSIA 0 m² — nue confirmée, reste servie.**
- **CD0937 : chaude rang 1073, CoSIA 87 m² sur 125 (70 %) → règle AB1910 appliquée, retirée**
  et journalisée. Journal du run servi : **17 exceptions**. Brûlantes 104, chaudes 1 037.
- Même geste : MVT rebuildées, golden régénéré — **116/116 PASS, 0 ancre bougée**.

## p_model_bati_cosia — CONSTRUITE (datée, additive, rien d'écrasé)
`(idu PK, emprise_cosia_m2, source_millesime='CoSIA 2025 (PVA juil.-août 2025, 20 cm)',
computed_at)` — **321 314 parcelles** avec emprise, calcul île entière en **51 s**.
La couche BD TOPO est INTACTE ; la divergence entre les deux reste mesurable en SQL.

## MESURE D'EFFET sur les têtes servies (max des deux emprises)
| tier | têtes | couche BD TOPO < 20 | révélées bâties (> 20 m²) | franches (> 40 m²) | zone adjudication (20-40) |
|---|---:|---:|---:|---:|---:|
| brûlante | 104 | 101 | **39 (38 %)** | 33 | 6 |
| chaude | 1 037 | 745 | **307 (30 %)** | 252 | 55 |
| **total** | 1 141 | 846 | **346** | 285 | 61 |

Par commune : Saint-Paul 99, La Possession 35, Saint-Benoît 25, Saint-Pierre 24… L'extrapolation
échantillon (~290) est **validée par l'exhaustif** (346, douteuses comprises).

## POINT D'ARRÊT
La table existe, RIEN ne la consomme (ni scoring, ni fiche, ni carte). La bascule qui ferait
sortir ~285-346 têtes est L'ARBITRAGE SUIVANT de Vic : modalité à trancher (retrait par
exceptions journalisées en masse ? re-score avec la feature max-emprise ? tier dédié
« bâtie révélée » ?) + traitement des 61 en zone 20-40 (adjudication sur cartes datées).
