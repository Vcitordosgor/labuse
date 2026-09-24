# TAXE-FIX-1 — captures avant / après

Captures **déterministes** (fonction `calculer()` main vs fix), **endpoint LIVE** (API sur :8445),
**pipeline DELTA LIVE** (secteurs, transaction annulée), et **écran** (`apres-0*.png`).

---

## 1. Avant / après — la fonction `calculer()` (main vs fix)

| Scénario | AVANT (main) | APRÈS (fix) |
|---|---|---|
| Signature : param `surface_exoneree_m2` | **absent** (rejette l'appel) | présent |
| Résultat : clé `rap_eur` | **absente** | présente |
| Hangar agricole 400 m² (zone A, CO0322) | **26 760 €** (aucune exonération possible → taxé plein pot) | **0 €** (exonéré de plein droit, CGI 1635 quater D 3°) |
| 300 m² PLAI | **10 035 €** (seulement abattement 50 %) | **0 €** (exonéré ; l'abattement 50 % reste pour le PLUS/PLS) |
| CO0322 400 m² RP | 23 415 € **(sans RAP)** | 23 415 € **+ RAP 1 248,80 €** |
| Programme mixte 3 PLAI (180 m²) + 7 (420 m²) | non exprimable en un calcul | assiette 374 640, total 28 098 €, RAP 1 498,56 € (les 180 PLAI exonérés) |
| Secteur à taux majoré (parcelle @10 %) | taux général seulement | part communale au **taux du secteur** |

---

## 2. Endpoint LIVE (API :8445, dev DB) — `GET /outils/taxe-amenagement…`

```
CONFIG                : valeur_forfaitaire hors_idf=892 ; part_departementale_confirmee_974=true
PREFILL CO0322        : {commune: Saint-Paul, insee: 97415, zone_plu: A, sdp_gabarit_m2: null,
                         taux_communal_pct: 5.0, taux_communal_source: public, secteur_majore: false}
CALC hangar agricole  : surface_exoneree_m2=400&motif_exoneration=agricole&idu=97415000CO0322
   → assiette 0,0 ; part_communale 0,0 ; total 0,0 ; rap 0,0
   → ligne : « Surface exonérée — Locaux agricoles | 400 m² × 892 €/m² — exonérée de plein droit
              (CGI art. 1635 quater D, 3°) »
CALC CO0322 400 RP    : surface_taxable_m2=400&residence_principale=true&idu=97415000CO0322
   → assiette 312 200 ; part_com 15 610 ; part_dep 7 805 ; total 23 415 ; rap_pct 0,4 ; rap 1 248,80
CALC mixte 3 PLAI     : surface_taxable_m2=420&surface_exoneree_m2=180&motif_exoneration=plai
   → assiette 374 640 ; total 28 098 ; rap 1 498,56
```

## 3. Pipeline DELTA LIVE — secteurs à taux majoré (transaction ANNULÉE)

```
DELTA Saint-Paul secteurs (lignes brutes) = 649
ingéré (rollback) : secteurs=649, hors_bornes_99=0, communes=['97415']
  97415000CT2268 : 10.0%  secteur_majore=True
  97415000DK1053 : 10.0%  secteur_majore=True
  97415000CO0322 :  5.0%  secteur_majore=False   ← CO0322 n'est PAS en secteur → taux général
→ transaction ANNULÉE (rien de persistant en base partagée)
```

Agrégat DELTA 974 (grain parcelle, taux ≤ 20 %) — 6 communes ont des secteurs majorés :
Saint-Paul 10 % (649 parcelles), Saint-Leu 14 % (9 398), Trois-Bassins 20 % (268),
Les Avirons 10 % (189), Entre-Deux 8,5 % (121), Le Port 5 % (1 011). Les lignes sentinelles
à 99 % sont écartées par les bornes `[0 ; 20]`.

## 4. Écran (fix) — `apres-0*.png`

- `apres-01-CO0322-saisie-zoneA.png` — CO0322 (Saint-Paul, zone A), « Gabarit non calculable en
  zone A », champ **Surface taxable** avec l'aide « garages et annexes INCLUS (CGI 1635 quater H) — ≠ SDP ».
- `apres-02-agricole-exonere-0.png` — case **Locaux agricoles** cochée → ligne « Surface exonérée —
  Locaux agricoles … CGI 1635 quater D, 3° » → **Total estimé 0 €**.
- `apres-03-nature-du-projet.png` — le bloc **Nature du projet** (agricole / PLAI / reconstruction).
- `apres-04-surface-taxable-aide.png` — l'aide du champ + bouton « Partir de la SDP du projet (à
  compléter : garages, annexes) ».
- `apres-05-taxe-RAP-resultat.png` — CO0322 400 m² RP → **Total 23 415 €** + ligne **Redevance
  d'archéologie préventive (0,4 %) = 1 249 €** (art. L524-7). Taux départemental « 2,5 % — confirmé ».
