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

## PÉRIMÈTRE RÉELLEMENT COUVERT CETTE PASSE

Couvert en profondeur : **Lot A** (règle, 24 taux, 10 cas manuels, A4), banc de recalcul indépendant (A + géométrie + résiduel + score), cohérence surface fiche=Gabarit=base sur 3 témoins (C2), cartographie code des 4 lots. **Non refait exhaustivement** (appuyé sur les audits antérieurs cités + le banc) : les 12 recalculs manuels parcelle-par-parcelle de faisabilité (B1), les 8 mesures de reculs au mètre du Gabarit (B/C1 — GABARIT-AUDIT-1 les a faits, 10 parcelles, 0 faux positif), l'extraction texte de 5 PDF × 14 exports (D2 — EXPORTS-AUDIT-2 : 930/942 chiffres ralliés, 0 divergence écran/PDF ; DOCS-FIX-1 : 4/4 écran=PDF). Voir RAPPORT.md § recommandations pour la suite.
