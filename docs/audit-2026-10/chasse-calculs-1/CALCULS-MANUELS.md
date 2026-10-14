# CHASSE-CALCULS-1 — CALCULS REFAITS À LA MAIN

Branche `audit/chasse-calculs-1`, worktree `~/Desktop/labuse-chasse-calculs`, base `labuse` locale **lecture seule**, run servi **q_v18** (scoring / `q_v18_sources` cascade / `run_seq 15` résiduel). Date 2026-10-14. Modèle Opus.

Règle : chaque chiffre affirmé par LABUSE est reconstitué **indépendamment** à partir du texte officiel (article cité), puis comparé à la sortie du produit. Le produit n'est appelé que pour **lire** la valeur servie — jamais importé pour recalculer.

---

## LOT A — TAXE D'AMÉNAGEMENT

### A1 — La règle officielle 2026 (reconstituée des textes)

| Élément | Valeur 2026 | Source (article / texte) |
|---|---|---|
| Valeur forfaitaire hors Île-de-France (= **La Réunion / DOM**) | **892 €/m²** | CGI art. **1635 quater H, 1°** ; arrêté du 22/12/2025 ; service-public A15416. **1ʳᵉ baisse de l'histoire** (930 €/m² en 2025, −2,4 %, indexation ICC). |
| Valeur forfaitaire Île-de-France (mémoire) | 1 011 €/m² | idem (non applicable au 974) |
| **Pas de valeur forfaitaire spécifique DOM** | — | La Réunion applique la valeur hors-IdF. Vérifié BOFiP BOI-IF-TU-10-30-20 : l'abattement s'applique aussi outre-mer (catégories LES/LLS), mais **aucune valeur forfaitaire DOM distincte**. |
| Abattement 50 % — 100 premiers m² **par logement** de résidence principale | 50 % / 100 m² | CGI art. **1635 quater I, I-2°** (« les cent premiers mètres carrés … **logement par logement** », BOFiP : non mutualisable entre logements d'un collectif) |
| Abattement 50 % — logements sociaux/aidés (PLUS/PLS/PSLA ; LES/LLS DOM) : sur **toute** la surface | 50 % | CGI art. **1635 quater I, I-1°** |
| Exonération de plein droit des petites surfaces < 5 m² | 0 € | CGI art. **1635 quater D, 10°** |
| Forfait piscine | 251 €/m² | CGI art. **1635 quater J** |
| Forfait panneaux PV au sol | 10 €/m² | CGI art. 1635 quater J |
| Forfait stationnement extérieur | 2 928 €/place (jusqu'à 5 857 € sur délibération) | CGI art. 1635 quater J |
| Forfait éolienne (mât > 12 m) | 3 000 €/mât | CGI art. 1635 quater J |
| Part départementale (plafond) | 2,5 % | CGI art. 1635 quater E ; La Réunion = 2,5 % |
| Redevance d'archéologie préventive (RAP) | 0,40 % de l'assiette TA | CGI art. 1635 quater F (gestion DGFiP depuis ord. 2022-883) |

**Constantes du produit** (`config/taxe_amenagement.yaml`, relevé 2026-08-28) = **toutes conformes** au tableau ci-dessus (vérification ligne à ligne). Seul errata documentaire, déjà consigné par l'équipe : les commentaires du YAML intervertissent les articles H et I — **les valeurs, elles, sont exactes**.

### A2 — Les 24 taux communaux servis (table `taxe_amenagement_taux`)

24/24 communes présentes, **toutes sourcées et datées** (`source = DGFiP — application DELTA`, `delib_date`, `maj_at = 2026-09-25`). Aucun taux sans source → **aucun écart A2**. Échantillon : Saint-Denis (97411) 3 %, Saint-Paul (97415) 5 %, Sainte-Rose (97419) **1 %**, Le Port (97407) 3 % (délib. 2025), Trois-Bassins (97423) 3 % (délib. 2024). Part départementale 974 = **2,5 % confirmée** par la même source DELTA (`part_departementale_confirmee_974: true`). Secteurs à taux majoré (`taxe_amenagement_secteur`) : **10 465 parcelles / 6 communes** servies (feature active, pas un placeholder vide).

### A3 — 10 cas recalculés À LA MAIN vs produit (`taxe_amenagement.calculer`)

VF = 892 €/m² · abattement 50 % · part dép 2,5 % · RAP 0,40 %. Reproductible : `banc_chasse_calculs.py` (ce dossier).

| # | Cas | Calcul manuel (règle) | Assiette manuelle | TOTAL manuel | TOTAL produit | Verdict |
|---|---|---|---|---|---|---|
| 1 | maison 120 m² **RP**, com 3 % | 20×892 + 100×892×0,5 | 62 440 | **3 434,20** | 3 434,20 | ✅ exact |
| 2 | maison 250 m², com 5 % | 250×892 | 223 000 | **16 725,00** | 16 725,00 | ✅ |
| 3 | **collectif 20 lgt = 1 400 m² RP**, com 3 % | 20 × (100 m² max → ici 70<100 ⇒ tout à −50 %) = 1 400×892×0,5 | **624 400** | **34 342,00** | **66 231,00** (assiette 1 204 200) | ❌ **écart : produit sur-taxe ~×2** |
| 4 | piscine 30 m² seule, com 5 % | 30×251 | 7 530 | **564,75** | 564,75 | ✅ |
| 5 | abri de jardin 15 m², com 3 % | 15×892 (pas d'exo de plein droit > 5 m²) | 13 380 | **735,90** | 735,90 | ✅ * |
| 6 | logement social 120 m² (aidé), com 5 % | 120×892×0,5 | 53 520 | **4 014,00** | 4 014,00 | ✅ |
| 7 | extension 40 m², com 3 % | 40×892 | 35 680 | **1 962,40** | 1 962,40 | ✅ |
| 8 | bureaux 300 m², com 3 % | 300×892 | 267 600 | **14 718,00** | 14 718,00 | ✅ |
| 9 | stationnement 10 places, com 5 % | 10×2 928 | 29 280 | **2 196,00** | 2 196,00 | ✅ |
| 10 | mixte 200 m² + piscine 40 + 4 places, com 5 % | 200×892 + 40×251 + 4×2 928 | 200 152 | **15 011,40** | 15 011,40 | ✅ |

RAP vérifiée au centime sur les 10 cas (0,40 % × assiette). **9/10 identiques au centime.**

\* Cas 5 : l'arithmétique par défaut est juste (un abri > 5 m² est taxable de plein droit). Mais l'outil **ne modélise pas** l'exonération **facultative** que la commune peut voter pour les abris de jardin ≤ 20 m² (CGI art. 1635 quater E) — voir écart **E-A2**.

**Cas 3 — le seul écart métier.** L'endpoint `/outils/taxe-amenagement` (`app.py:3047`) et `calculer()` (`taxe_amenagement.py:245-252`) n'ont **aucun paramètre `nb_logements`** : le plafond de 100 m² de l'abattement RP est appliqué **une seule fois au total saisi**, alors que le texte l'accorde **logement par logement**. Pour un collectif de 20 résidences principales, l'outil ne décote que 100 m² au lieu de 20×100 → **assiette 1 204 200 € au lieu de 624 400 €, total 66 231 € au lieu de 34 342 €**. Direction prudente (sur-estimation), mais faux vs la règle et non signalé.

### A4 — Ce que l'outil déclare NE PAS couvrir

Déclaré : estimation indicative (meta.note), taux communal jamais inventé (total `None` si absent), part départementale « confirmée ». **Non déclaré** (écart E-A2) : exonérations **facultatives** communales (abris de jardin ≤ 20 m², commerces < 400 m², etc.), stationnement extérieur **majoré sur délibération** (5 857 €/place — la constante existe dans le YAML mais `calculer()` sert toujours 2 928), et l'abattement **par logement** des collectifs (E-A1). Arrondi : l'outil sert au **centime** (ex. 3 434,20 €) alors que la TA légale s'arrondit à l'**euro inférieur** (CGI 1635 quater I, III) — écart E-A3, faible.

---

## LOT B / LOT C — cohérence « même donnée » (3 témoins, lecture en-process)

Fiche `/parcels/{idu}` vs outil Gabarit `/outils/gabarit/{idu}` vs base. **La surface de terrain servie = la contenance cadastrale partout** (règle CONTENANCE-1, **LIVE sur q_v18**) :

| témoin | DB `contenance_m2` | DB dessin `ST_Area` | fiche `surface_terrain_m2` (`surface_source`) | Gabarit `surfaceParcelleM2` | cohérent ? |
|---|---|---|---|---|---|
| 97409000AK0804 (PPR partiel) | 27 862 | 28 258 | 27 862 (`cadastre`) | 27 862 | ✅ |
| 97415000CW0658 (contenance ≠ dessin +5,9 %) | 25 633 | 27 156 | 25 633 (`cadastre`) | 25 633 | ✅ |
| 97411000AW0692 (U Saint-Denis) | 991 | 991 | 991 (`cadastre`) | 991 | ✅ |

La SDP servie (fiche § Potentiel, Dossier, Flash, Copilote) vient d'une **source unique** `potentiel_transformation.sdp_residuelle_m2`, elle-même tirée du **run gelé** `parcel_residuel` (run_seq 15). AK0804 : SDP résiduelle 34 223 m², zone d'implantation Gabarit 19 294 m², hauteur réglementaire 14 m (faîtage) — concepts distincts, base de surface commune (contenance). Voir écarts E-B1 (réactivité) et E-C1 (3D terrain plat).

---

## BANC DE RECALCUL INDÉPENDANT (existant, rejoué sur q_v18)

```
PYTHONPATH=src python -m scripts.coherence.recalcul.banc_calcul
```
Résultat 2026-10-14 : **494 comparaisons · 1 écart** (`mult_base` 0,86 vs 0,85, tolérance 0,01 abs → TOLERABLE). Modules : géométrie (surface/pente/% couche), résiduel/hauteur, médianes DVF, **taxe d'aménagement**, signal/bandes. → la couche de calcul servie (TA, géométrie, SDP résiduelle, score) **réconcilie servi ↔ recalcul indépendant**, 1 seul écart d'arrondi non bloquant.

---

---

## LOT B1 — 12 FAISABILITÉS RECALCULÉES À LA MAIN (passe 2, run q_v18 / run_seq 15)

Méthode : pour chaque parcelle, la chaîne officielle est rejouée à la main depuis le **règlement de zone** (article + page citées, tels que servis par l'outil `GET /modules/faisabilite/{idu}` dans `steps[].source`, miroir du YAML `config/plu_destinations/{insee}.yaml`), puis les trois lectures sont confrontées : **outil Faisabilité** (live), **fiche** `/parcels/{idu}` (`potentiel_transformation.sdp_residuelle_m2`, SERVIE depuis le run gelé) et **Gabarit** `/outils/gabarit/{idu}`. Harnais rejouable : `_harness.py B1`. Constantes du moteur (toutes exposées en `hypotheses`) : étage 3 m, occupation 0,45, rendement 0,80, logement 65–80 m², densité-filet 30 logts/ha/niveau, place 25 m².

**Chaîne** : `emprise_constructible = min(zone_implantation(reculs), CES×contenance, (1−pleine_terre%)×contenance)` → `emprise_bâtie = emprise_constructible × 0,45` → `SDP = emprise_bâtie × niveaux` → `shab = SDP × 0,80` → `logements = min(shab / logt_moyen, densité×ha×niveaux)`.

### Les 12 parcelles

| # | IDU · commune | zone | contenance (=surface servie) | règlement (CES · Hégout · recul voie/sep · article/page) | outil : emprise→SDP→niveaux→logts | hand-check chaîne | fiche SDP servie | Gabarit zone impl. |
|---|---|---|---|---|---|---|---|---|
| 1 | 97411000BK0101 St-Denis | Ud | 574 | 80 % · 12 m · 3/4 m · Art. Ud.9 p.43 / Ud.10 p.44 | 255→460→R+3→4-6 | 255×0,45=115 ✓ ; 115×4=460 ✓ | **460 =** outil | 262 (⚠ ≠ 255) |
| 2 | 97411000AB0318 St-Denis | Uavap (non calibré) | 270 | Art. 9 silence · R+2 générique | 105→142→R+2→1-2 | 105×0,45=47 ✓ ; 47×3=141≈142 ✓ | **0** (85-91 % bâti ⇒ résiduel saturé, OK) | incomplet |
| 3 | 97410000AB0212 St-Benoît | AUp1 | 40 930 | AU fermée — construction neuve non autorisée | — (verdict « non autorisée ») | n/a (0 cohérent) | **0** (cause `zone_non_constructible:AUp1`) ✓ | incomplet |
| 4 | 97415000BZ0007 St-Paul | Usdu (bizone 73 %/N) | 5 600 | Art. 7.2 p.132 · R+1 Art 10.2 p.134 · PT Art 13.1 p.143 ; ER/EBC −3 077 | 477→430→R+1→1-3 | 477×0,45=215 ✓ ; 215×2=430 ✓ | **0** (85 % bâti ⇒ résiduel saturé, OK) | incomplet (clip Usdu 4 037) |
| 5 | 97417000BN0002 St-Philippe | — (RNU) | 515 500 | RNU — pas de PLU opposable | **muet** (zone None) | n/a | **None** (cause `hors_plu`) | incomplet |
| 6 | 97409000AK0804 St-André | UB | 27 862 | silence CES (Art. 9) · R+3 Art. UB 10 p.29 · PT Art. UB 13.1 p.32 · recul 6/3 | 19 024→34 243→R+3→334-335 | 19 024×0,45=8 561 ✓ ; 8 561×4=34 244≈34 243 ✓ | **34 223** (⚠ ≠ 34 243 : −20, run gelé) | 19 294 (⚠ ≠ 19 024) |
| 7 | 97415000CW0658 St-Paul | AU3a (renvoi AU→U) | 25 633 | Art. 7.2 p.112 · R+4 Art 10.2 p.114 · PT Art 13.1 p.124 | 17 164→38 619→R+4→176-177 | 17 164×0,45=7 724 ✓ ; 7 724×5=38 620≈38 619 ✓ | **38 619 =** outil | incomplet |
| 8 | 97412000BV0419 St-Joseph | U2 | 2 983 | 80 % Art. U2 9.2 p.35 · R+2 Art. U2 10.2 p.35 · PT Art. U2 13.1 p.41 · 3/3 m | 2 305→3 112→R+2→26-27 | 2 983×0,80=2 386 (CES) ; min(2 305,2 386)=2 305 ✓ ; ×0,45=1 037 ✓ ; ×3=3 111≈3 112 ✓ | **3 095** (⚠ ≠ 3 112 : −17, run gelé) | 2 320 (⚠ ≠ 2 305) |
| 9 | 97419000AK0909 Ste-Rose | Ua | 2 737 | 70 % Art. UA 9 p.14 · R+2 Art. UA 10 p.15 · PT Art. UA 13 p.17 · 4/3 m | 1 916→2 586→R+2→17-18 | 2 737×0,70=1 916 (CES **lie**) ; ×0,45=862 ✓ ; ×3=2 586 ✓ | **2 586 =** outil | incomplet |
| 10 | 97409000AB0521 St-André | UB (GPU dépublié) | **NULL** (dessin 29 489) | Art. UB 7 p.27 · R+3 Art. UB 10 p.29 | 20 622→37 119→R+3→0 (rédhibitoire) | outil calcule sur le **dessin** ; fiche sert None | **None** (contenance absente) | incomplet |
| 11 | 97413000CA0243 St-Leu | AUE (GPU dépublié, non calibré) | 12 550 | Art. 7 non calibré · R+2 générique | 7 390→9 977→R+2→69-79 | 7 390×0,45=3 326 ✓ ; ×3=9 978≈9 977 ✓ | **9 977 =** outil | incomplet |
| 12 | 97416000DV0285 St-Pierre | Ue | **1** (dessin 117 505) | contenance absurde (acte=1 m²) | **muet** (« surface incertaine ») | n/a | **None** (cause `surface_incertaine`) ✓ | incomplet |

### Deux recalculs détaillés (preuve que la règle est appliquée, article cité)

**#9 Sainte-Rose 97419000AK0909, zone Ua** — règlement servi : CES 70 % (**Art. UA 9, p.14**), hauteur égout 9 m (**Art. UA 10, p.15**), reculs voie 4 m / séparatif 3 m (**Art. UA 7, p.13**).
- CES : 2 737 × 70 % = **1 916 m²** (= `emprise_sol_max` servi). Reculs → zone d'implantation 1 971 > 1 916, donc **le CES lie** : emprise constructible = 1 916 ✓.
- Niveaux : 9 ÷ 3 = **3 niveaux = R+2** ✓. Emprise bâtie : 1 916 × 0,45 = **862 m²** ✓. SDP : 862 × 3 = **2 586 m²** ✓ (exact). Logements : plafond densité 0,2737 ha × 30 × 3 = 24,6 → **25** ; shab 2 069 ÷ 80 = 25,9 ⇒ bornés à 25, retenus au sol 17-18 (stationnement). **Toute la chaîne tombe juste, fiche = outil = 2 586.**

**#8 Saint-Joseph 97412000BV0419, zone U2** — CES 80 % (**Art. U2 9.2, p.35**), hauteur égout 11 m (**Art. U2 10.2, p.35**), reculs 3/3.
- CES : 2 983 × 80 % = 2 386 m² ; zone implantation 2 305 < 2 386 ⇒ **les reculs lient**, emprise 2 305 ✓. Niveaux 11 ÷ 3 = 3 → R+2. Emprise bâtie 2 305 × 0,45 = 1 037 ✓. SDP 1 037 × 3 = 3 112 ✓. **Chaîne juste** ; seule la **fiche servie dit 3 095** (−17 m² vs 3 112 : décalage du run gelé, E-B1).

### Constats B1

- **Calcul JUSTE sur les parcelles constructibles** : sur BK0101, BV0419, AK0909, AK0804, CW0658, CA0243, chaque maillon (CES, hauteur→niveaux, occupation, SDP) se reconstitue à la main depuis le **règlement cité (article + page)**, et les hypothèses de modélisation sont toutes affichées. La contenance cadastrale est bien la surface d'assise partout (CONTENANCE-1 LIVE).
- **E-B1 (PÉRIMÉ, faible)** : la SDP **servie** (fiche, run gelé) retarde de ~0,05 % sur l'outil live — AK0804 34 223 vs 34 243, BV0419 3 095 vs 3 112. Confirme que la fiche sert un instantané de run, pas le calcul courant.
- **E-B2 (DIVERGENT, faible)** : le **Gabarit** et l'**outil Faisabilité** affichent une « zone d'implantation réglementaire » **différente** pour la même parcelle, bien que la faisabilité déclare utiliser « le moteur gabarit » : BK0101 **262 vs 255** (+2,7 %), AK0804 **19 294 vs 19 024** (+1,4 %), BV0419 **2 320 vs 2 305** (+0,6 %). Deux outils, même grandeur nommée, deux valeurs.
- **E-B3 (DIVERGENT / donnée, à instruire)** : deux moteurs cohabitent dans le run servi (`parcel_residuel.assiette_source` = **`gabarit`** 204 k parcelles vs **`residuel_legacy`** 53 925). Les parcelles où le gabarit échoue (status `incomplete`) basculent sur le legacy, qui sert des **intermédiaires impossibles** (`taux_emprise_pct` 607 et 233, `pct_potentiel` 640 — > 100 % n'a pas de sens) ; la SDP finale 0 reste défendable quand la parcelle est dense (BZ0007 85 % bâti, AB0318 91 %), mais les intermédiaires sont faux et la **source de calcul n'est pas la même pour tous les clients**.
- **Contenance absente (AB0521)** : la fiche sert `None` (honnête) mais l'outil calcule sur le **dessin** (29 489 m²) → incohérence de surface d'assise quand `contenance_m2 IS NULL`.
- **RNU Saint-Philippe (BN0002)** : l'outil est **muet** (zone None, `hors_plu`) — honnête, mais la méthode PAU (enveloppe urbanisée RNU) n'est pas servie dans l'outil.
- **Résiduel vs enveloppe (rappel)** : sur parcelles denses la fiche sert la SDP **résiduelle bâti-conservé** (0) quand l'outil montre l'**enveloppe table-rase** — c'est le design à deux scénarios (SDP-VERIF-1), pas un écart, mais l'écart de libellé peut dérouter.

---

## LOT C1 — 8 GABARITS : RECULS MESURÉS AU MÈTRE SUR LA GÉOMÉTRIE (run q_v18)

Méthode : pour chaque parcelle dont le Gabarit renvoie `status=ok`, la géométrie servie `zoneImplantationGeoJSON` (Z) est transformée en EPSG:2975 (mètres) et mesurée en PostGIS contre la parcelle P : **débordement** `aire(Z∖P)` (doit être ~0), **distance min Z→bord parcelle** (= recul le plus serré réellement appliqué), **distance Z→voirie**, **intersection Z∩PPR rouge** (`code_degre ~ '^R'`, doit être 0). Confronté aux reculs ANNONCÉS (`raccordement.plu`) et à la classification d'arêtes. Harnais rejouable : `_mesure_gabarit.py`.

| IDU · commune · zone | reculs annoncés (voie/sep) · arêtes voie/side/rear | Z (m²) | Z∖P (débord.) | **d(Z,bord) mesuré** vs recul serré | d(Z,voirie) | Z∩PPR rouge | hauteur servie |
|---|---|---|---|---|---|---|---|
| 97409000AK0804 St-André UB | 6 / 3 · 11/22/12 | 19 294 | **0,0** ✓ | **2,98 m** ≈ 3 (sep) ✓ | 0 * | **0,0** (rouge parcelle 3 362 m²/12 %) ✓ | 14 m faîtage ✓ |
| 97411000BK0101 St-Denis Ud | 3 / 4 · 0/0/1 (enclavée) | 262 | **0,0** ✓ | **3,99 m** ≈ 4 (sep, pas de voie) ✓ | 33,9 m | 0,0 ✓ | — |
| 97412000BV0419 St-Joseph U2 | 3 / 3 · 4/7/3 | 2 320 | **0,0** ✓ | **2,95 m** ≈ 3 ✓ | 0 * | 0,0 ✓ | 13 m faîtage ✓ |
| 97412000BV0039 St-Joseph U2 | 3 / 3 · 3/6/4 | 1 944 | **0,0** ✓ | **2,97 m** ≈ 3 ✓ | 0 * | 0,0 ✓ | 13 m faîtage |
| 97408000AP1344 La Possession UAM | **0 (alignement)** / 3 · 6/10/5 | 2 570 | **0,0** ✓ | **0,00 m** ≈ 0 (alignement) ✓✓ | 0 | 0,0 ✓ | 12 m égout |
| 97408000AN0062 La Possession UA | 3 / 3 · 2/4/3 | 2 455 | **0,0** ✓ | **2,95 m** ≈ 3 ✓ | 0 * | 0,0 ✓ | 16 m faîtage |
| 97409000AY0786 St-André (PPR 3 %) | 4 / 3 · 0/0/1 | 2 679 | **0,0** ✓ | **2,99 m** ≈ 3 (sep) ✓ | 7,6 m | **0,0** (rouge parcelle 145 m²/3 %) ✓ | 12 m faîtage ✓ |
| 97416000ES2238 St-Pierre | 3 / 3 · 0/0/1 | 110 | **0,0** ✓ | **3,00 m** ≈ 3 ✓ | 12,6 m | 0,0 ✓ | 12 m faîtage |

\* d(Z,voirie)=0 quand des arêtes « voie » existent : le recul est appliqué depuis la **limite cadastrale** de façade (classée « voie »), pas depuis le polygone de chaussée `voirie` (qui jouxte la limite) — la mesure pertinente est `d(Z,bord)`, qui tombe juste. Vérifié.

### Constats C1 — la GÉOMÉTRIE DU GABARIT EST JUSTE

- **Aucun débordement** : sur les 8, la zone d'implantation est **entièrement dans la parcelle** (Z∖P = 0,0 m²) — le gabarit ne dessine jamais hors du terrain.
- **Reculs exacts au centimètre** : `d(Z, bord parcelle)` = le recul le plus serré annoncé **à ±0,05 m** sur les 8 — y compris le cas **alignement** (La Possession UAM : recul voie 0 → Z touche la limite, mesuré 0,00 m) et les parcelles **enclavées** (BK0101, AY0786, ES2238 : aucune arête voie, recul séparatif appliqué).
- **PPR rouge correctement découpé** : sur les deux témoins PPR partiel, la zone **évite totalement le rouge** (Z∩rouge = 0,0 m²) alors que la parcelle en porte (AK0804 3 362 m²/12 %, AY0786 145 m²/3 %). La déduction PPR-INTERDICTION est géométriquement propre.
- **Hauteur = règlement** : la hauteur servie par le Gabarit = la hauteur **faîtage** du règlement de zone (AK0804 14 m, BV0419 13 m, AY0786 12 m…), ou l'**égout** là où seul l'égout est réglementé (La Possession 12 m).
- **E-C2 (MUET / couverture)** : le Gabarit renvoie `status=incomplete` pour une **large part** des parcelles (6 des 14 sondées ici, et la plupart des témoins B1 : AB0318, BZ0007, CW0658, AK0909, AB0521, CA0243, DV0285…) — « donnée réglementaire manquante » → **ni zone d'implantation ni plafond d'emprise servis**. Honnête (pas de chiffre inventé) mais trou de couverture important, à chiffrer au global.
- Rappel **E-C1** (ECARTS) : le volume 3D reste une extrusion à terrain plat ; la pente n'entre pas dans le volume.

---

## LOT D2 — 5 TÉMOINS × CHAQUE EXPORT, PDF EXTRAIT EN TEXTE, CONFRONTÉ À LA FICHE

Méthode : chaque export est généré **en-process** (aucune écriture), le PDF extrait au texte (`pdftotext`), et confronté aux chiffres **servis par la fiche à l'instant de la génération** (surface terrain, SDP, taux TA, commune). Harnais rejouable : `_exports_d2.py`. Témoins : AK0804 (St-André PPR), BV0419 (St-Joseph U2), CA0243 (St-Leu), ES2238 (St-Pierre), BZ1065 (St-Denis, prix connu).

| export | AK0804 | BV0419 | CA0243 | ES2238 | BZ1065 | lecture |
|---|---|---|---|---|---|---|
| **Dossier** | ✓ surf+SDP | ✓ surf+SDP | ✓ surf+SDP | ✓ surf+SDP | ✓ surf+SDP | surface (`27 862 m²`) **et** SDP servie présentes **à l'identique** dans le PDF ; millésime + sources + mention ; 0 None/null/nan réel |
| **Bilan** (financier) | 422 * | 422 * | 422 * | 422 * | ✓ surf | 422 `document_non_etablissable` tant qu'achat/revente non saisis (garde [[bilan-2]]) — attendu, pas un écart |
| **Apporteur** | ✓ surf | ✓ surf | ✓ surf | ✓ surf+SDP | ✓ surf | teaser court ; surface présente ; SDP non imprimée (doc volontairement bref) |
| **Gabarit** | ✓ | ✓ | **422** † | ✓ | ✓ | 422 quand gabarit `incomplete` (CA0243) — **propagation de E-C2** |
| **Comparatif** | — | — | — | — | — | 422 à 1 IDU (≥2 requises) ; **OK à 2 IDU** (200, surface + pied présents) |
| **Étude-zone** | ✓ | ✓ | ✓ | ✓ | ✓ | document de zone (agrégat), pas de surface parcelle — normal |
| **KMZ** | ✓ idu+commune | ✓ | ✓ | ✓ | ✓ | contour `ST_AsKML`, porte l'IDU et la commune |

\* Bilan : garde d'établissabilité (achat **ou** revente requis). † Gabarit : même donnée réglementaire manquante que le Gabarit outil.

### Constats D2 — « MÊME DONNÉE » TENU

- **Les chiffres de l'export = la fiche** : sur les 5 Dossiers, la surface servie (ex. `27 862 m²`) **et** la SDP résiduelle servie apparaissent **telles quelles** dans le PDF (le builder lit le payload fiche partagé). Aucune divergence export↔fiche trouvée sur les nombres confrontés.
- **Millésime = date de la donnée, pas de génération** : tous les PDF portent « Données LABUSE au **11/10/2026** » = `served_manifest.promoted_at` (run q_v18 promu le 11/10), **pas** la date de génération (14/10). Conforme à D4.
- **Sources par section** : chaque bloc liste ses sources **par nom** (« Sources : BD TOPO IGN · CoSIA · … ») **sans millésime par source** (doctrine PAGE-SOURCES-1). Donc la « date de la donnée » servie est **unique et globale** (le run), pas un millésime par source — choix produit assumé, à garder en tête pour D4.
- **Rendu propre** : 0 token `None`/`null`/`nan`/`undefined` isolé dans les PDF (le « nan » d'un premier passage était un sous-mot de « finance/gouvernance » — faux positif de l'outil, écarté).
- **Garde-fous légitimes** (pas des écarts) : Bilan 422 sans achat/revente ; Comparatif exige ≥ 2 parcelles ; Gabarit 422 quand le gabarit est `incomplete` (propagation **E-C2**).
- Caveat outillage : les cases « surface✗ » sur Gabarit/Étude-zone et « IDU absent » du Comparatif viennent du **format d'affichage** (ha, IDU découpé section/numéro, espace fine) — vérifié, la donnée est bien là ; pas d'écart.

---

## PÉRIMÈTRE RÉELLEMENT COUVERT CETTE PASSE

Couvert en profondeur : **Lot A** (règle, 24 taux, 10 cas manuels, A4), banc de recalcul indépendant (A + géométrie + résiduel + score), cohérence surface fiche=Gabarit=base sur 3 témoins (C2), cartographie code des 4 lots. **Non refait exhaustivement** (appuyé sur les audits antérieurs cités + le banc) : les 12 recalculs manuels parcelle-par-parcelle de faisabilité (B1), les 8 mesures de reculs au mètre du Gabarit (B/C1 — GABARIT-AUDIT-1 les a faits, 10 parcelles, 0 faux positif), l'extraction texte de 5 PDF × 14 exports (D2 — EXPORTS-AUDIT-2 : 930/942 chiffres ralliés, 0 divergence écran/PDF ; DOCS-FIX-1 : 4/4 écran=PDF). Voir RAPPORT.md § recommandations pour la suite.
