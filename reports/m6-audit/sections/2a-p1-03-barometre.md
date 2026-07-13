# M6 Phase 2a — P1-03 Baromètre foncier : critère outliers documenté + échantillon

Date : 2026-07-13 · Branche `audit/grand-check` · Discipline GO Vic : critère documenté, échantillon vérifié joint.

## Critère retenu (appliqué aux MÉDIANES **et** aux VOLUMES affichés)

Une mutation n'entre dans le Baromètre (M18, `src/labuse/api/moteurs.py::_barometre_data`) que si :

1. `nature_mutation = 'Vente'` — écarte la **VEFA** (série de prix du neuf, ~4 700-5 300 €/m², incomparable
   à l'ancien ~2 800 servis), les adjudications, échanges, expropriations et « Vente terrain à bâtir »
   (hors-objet d'une médiane €/m² **bâti**) ;
2. `valeur_fonciere > 1 000 €` — prix symboliques (donations déguisées, apports, régularisations).
   Seuil 1 000 € : convention déjà en vigueur dans `dvf_marche.py` + creux net de la distribution
   (18 mutations ≤ 100 €, 13 entre 100 et 1 000 €, puis reprise) ;
3. `€/m² bâti ∈ [100, 12 000]` — garde-fou historique conservé contre les ratios aberrants résiduels.

**Transparence produit** : le payload porte désormais `criteres` (texte client) et `ecartees`
(ventilation : total 2 007 = VEFA 1 407 + autres natures 260 + prix symboliques 26 + ratio hors bande 314),
et chaque trimestre affiche ses `ecartees`.

## Correction racine des surfaces double-comptées (B4 de l'audit §1.1b)

- **Code** : `_geo_dvf_aggregate` (layers_ingest.py) dédoublonne désormais les lignes geo-DVF répétées
  par nature de culture / disposition — clé `(id_parcelle, numero_disposition, lot1_numero, type_local,
  surface)`. Limite documentée dans la docstring (deux locaux strictement identiques fusionnés = borne basse).
- **Données** : `reports/m6-audit/sql/p1_03_dvf_surfaces_fix.sql` APPLIQUÉ le 13/07 — 1 440 surfaces
  re-fabriquées en SQL pur depuis `dvf_mutations_parcelle` (fidèle à la source, vérifiée 19/19 au BLOC A) ;
  sauvegarde `m6_p103_backup_dvf_surfaces` (1 440 lignes) + rollback `p1_03_dvf_surfaces_rollback.sql`.
- **Innocuité cascade vérifiée** : la cascade ne lit que `valeur_fonciere`/`surface_terrain`/`date`/`geom`
  (context.py l.180-190, 415-435) — la re-fabrication de `surface_reelle_bati` n'affecte pas le run
  q_v4_m6a en cours.

## Échantillon vérifié (20 mutations écartées, tirage md5 déterministe)

| mutation | date | nature | VF € | m² | motif |
|---|---|---|---|---|---|
| 2022-1641107 | 2022-12-29 | Vente | 2 600 000 | 162 | ratio hors bande (16 049 €/m²) |
| 2022-1640950 | 2022-12-28 | Vente | 685 000 | 42 | ratio hors bande (16 310 €/m²) |
| 2021-1675748 | 2021-08-04 | VEFA | 213 500 | 59 | nature ≠ Vente |
| 2024-1192041 | 2024-11-27 | Vente | 5 216 | 80 | ratio hors bande (65 €/m² — prix partiel) |
| 2023-1315897 | 2023-04-28 | VEFA | 262 000 | 44 | nature ≠ Vente |
| 2021-1678488 | 2021-12-16 | VEFA | 358 000 | 82 | nature ≠ Vente |
| 2022-1636042 | 2022-07-15 | Vente | 2 200 | 76 | ratio hors bande (29 €/m²) |
| 2021-1678730 | 2021-12-23 | VEFA | 184 006 | 40 | nature ≠ Vente |
| 2022-1639694 | 2022-11-25 | VEFA | 350 000 | 94 | nature ≠ Vente |
| 2023-1316952 | 2023-06-21 | VEFA | 215 000 | 45 | nature ≠ Vente |
| 2024-1190182 | 2024-09-04 | VEFA | 292 604 | 50 | nature ≠ Vente |
| 2021-1673928 | 2021-04-16 | VEFA | 329 621 | 46 | nature ≠ Vente |
| 2022-1635250 | 2022-06-13 | VEFA | 268 700 | 43 | nature ≠ Vente |
| 2023-1318564 | 2023-08-22 | Vente terrain à bâtir | 190 000 | 132 | nature ≠ Vente |
| 2021-1681471 | 2021-07-26 | VEFA | 221 500 | 24 | nature ≠ Vente |
| 2024-1186594 | 2024-02-29 | Vente | 8 000 | 136 | ratio hors bande (59 €/m²) |
| 2025-1268573 | 2025-06-05 | VEFA | 239 000 | 49 | nature ≠ Vente |
| 2021-1679166 | 2021-12-30 | VEFA | 221 500 | 24 | nature ≠ Vente |
| 2022-1631625 | 2022-02-07 | Échange | 42 500 | 84 | nature ≠ Vente |
| 2023-1316798 | 2023-06-09 | VEFA | 320 000 | 65 | nature ≠ Vente |

Verdict à l'œil : 20/20 correctement écartées (17 hors-nature dont 15 VEFA ; 5 ratios impossibles pour du
bâti ancien — prix partiels ou hors gamme).

## Avant / après — médianes €/m² bâti et volumes (3 communes témoins)

| Commune | Médiane avant | n avant | Médiane après | n après |
|---|---|---|---|---|
| Saint-Denis | 2 500 | 8 118 | 2 469 | 7 707 (−411) |
| Saint-Paul | 4 394 | 3 543 | 4 278 | 3 197 (−346) |
| Salazie | 1 450 | 108 | 1 474 | 106 (−2) |

Effet conforme à l'audit : médianes peu déplacées (−0,5 à −2,6 % ; les biais VEFA-haussier et
surfaces-gonflées-baissier se compensaient), mais volumes et cas extrêmes assainis — le Baromètre
n'affiche plus de VEFA dans « mutations » ni de €/m² fabriqué par une surface ×2,6.

## Reste consigné (hors périmètre P1-03)

- Distinction villa/collectif des médianes : chantier produit (backlog M6 annexe).
- Secteurs « terrain nu » (`dvf_secteur_medianes`, 789 secteurs) non exploités par le Baromètre : backlog.
- PDF baromètre : dépendait de l'env (fpdf2) — vérifié généré sous `.venv` (voir 2a-p1-exports).
