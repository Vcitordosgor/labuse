# M6 Phase 1 §1.3b — ER / EBC / OAP & anomalie A1 approfondie (AUDIT LECTURE SEULE)

Date : 2026-07-13 · Branche : `audit/grand-check` · Base : `postgresql://openclaw@localhost:5432/labuse`
Livrables : ce fichier + `1-3b-a1-parcelles-affectees.csv` (29 933 lignes) + `a1_simulation.sql` (requête rejouable, SELECT pur).
Aucune écriture en base, aucune ingestion — l'unique appel réseau est un `resultType=hits` WFS GPU (comptage).

---

## BLOC A — ER / EBC / OAP

### A.1 Présents en base ? OUI

`spatial_layers` kind=`plu_gpu_prescription` : **17 765 lignes, 24/24 communes**, subtype = `typepsc` CNIG.
Ingestion : `src/labuse/ingestion/layers_ingest.py` → `ingest_gpu_prescriptions()` (API Carto GPU,
endpoints `prescription-surf/lin/pct`, requête par **bbox de commune** — cause des doublons, voir A.5).

| typepsc | classe (cascade_rules.yaml) | n | communes |
|---|---|---|---|
| 07 | élément bâti protégé (L151-19) | 5 048 | 23 |
| **05** | **emplacement réservé (ER)** | 3 865 | 24 |
| 02 | non mappé (fallback flag FAIBLE) | 3 673 | 20 |
| **01** | **espace boisé classé (EBC)** | 3 360 | 24 |
| 15 | non mappé | 736 | 20 |
| **18** | **OAP** | 167 | 15 |
| 16/17 | mixité sociale | 386 | 7/4 |
| 48 | eaux pluviales | 24 | 5 |
| autres (99, 24, 37, 22, 08, …) | non mappés | ~500 | — |

Vigilances contenu :
- **typepsc 02** (3 673 obj.) = essentiellement des périmètres PPR re-livrés par les communes dans leur PLU
  (redondant avec la couche `ppr` dédiée) **mais contient 11 « Emplacement réservé » mal codés en 02**
  (non traités comme ER par la cascade).
- **OAP** : seulement 167 objets / 15 communes — les OAP ne sont dématérialisées en prescription typepsc 18
  que dans une partie des PLU ; API Carto n'expose pas de classe OAP séparée. Couverture partielle par nature.
- Fraîcheur (spot-check WFS GPU `resultType=hits`, `partition=DU_<insee>`) : Trois-Bassins WFS 189 surf vs
  217 en base, Saint-Paul 414 vs 615, Saint-Benoît 283 vs 1 665 — l'excédent en base = objets des communes
  voisines capturés par la bbox (pas un déficit ; voir doublons A.5).

### A.2 Pris en compte par la cascade/scoring ? OUI

`src/labuse/cascade/layers/phase1.py` → `PrescriptionPluLayer` (name=`prescription_plu`), active dans
`config/cascade_rules.yaml` et **effective dans le run courant** (cascade_results du 04/07) :

| verdict | parcelles |
|---|---|
| HARD_EXCLUDE (ER ≥ 50 % — `er_hard_exclude_pct`, PLACEHOLDER à calibrer par Vic) | **5 077** (100 % motif ER) |
| SOFT_FLAG (ER < 50 % avec déduction pré-faisa · EBC flag FORT · bâti protégé MOYEN · non mappés FAIBLE) | 127 569 |
| PASS (mixité/OAP/eaux pluviales informatifs, ou aucune prescription) | 308 407 |

La pré-faisabilité (`faisabilite/db.py`) **déduit la surface ER** de l'emprise constructible
(`ST_Union`, filtré commune → robuste aux doublons). La surface **EBC n'est PAS déduite** (ER uniquement).

### A.3 Chiffrage de l'impact résiduel (exhaustif à l'île, pas une extrapolation)

Croisement en base (SELECT pur) : parcelles **non écartées** (statut ≠ ecartee, 22,6 k) × emprises ER/EBC
(couverture par `ST_Union`, donc dédoublonnée) :

| signal | touchées | ≥ 10 % | ≥ 50 % | ≥ 90 % | dont brûlante/chaude ≥ 50 % |
|---|---|---|---|---|---|
| ER (05) | 1 118 | 369 | **10** | 5 | **0** |
| EBC (01) | 18 | 7 | **5** | 3 | **0** |

- **Fausses opportunités mécaniques ≈ 15 parcelles à l'île entière** (10 ER + 5 EBC ≥ 50 %), toutes
  tiers `a_creuser`/`reserve_fonciere`. **Aucune brûlante, aucune chaude.** Les 13 chaudes touchées par un ER
  le sont à < 20 % de couverture (soft flag + déduction pré-faisa = traitement voulu).
- Exemples EBC : 97411000AS0195 (Saint-Denis, EBC 100 %, zone U, a_creuser) ; 97411000DR0787 (98,8 %, chaude
  de statut mais tier réserve foncière) ; 97416000CS1201 (96,3 %).
- Exemples ER : 97402000AH0570 (Bras-Panon, ER 100 %) ; 97412000BL0997 (Saint-Joseph, 99,6 %).

**Deux causes précises (code, pas données) :**
1. **Bug premier-arrivé du dédoublonnage `(typepsc, libellé)`** (`phase1.py` l. 334) : quand plusieurs ER
   partagent le libellé générique « Emplacement réservé », seul le PREMIER objet de la liste (ordre SQL
   arbitraire) est évalué. Si c'est un petit ER (< 50 %), l'ER couvrant ≥ 50 % est ignoré →
   97402000AH0570 (objet à 100 %) est SOFT_FLAG au lieu de HARD_EXCLUDE.
2. **Seuil ER testé PAR OBJET, jamais en cumul** : 2 ER de 30 % + 30 % (60 % cumulés) n'excluent pas.
   Et **l'EBC n'a aucun seuil d'exclusion** (flag FORT même à 100 % de couverture) ni de déduction d'emprise.

### A.4 Verdict intégrabilité Phase 2b

**Intégrable en Phase 2b SANS ingestion nouvelle.** Les données sont déjà en base (24/24 communes) et déjà
branchées sur la cascade. Reste à faire (petit, code + re-run) :
- corriger le dédoublonnage premier-arrivé (garder l'objet de couverture MAX par (typepsc, libellé)) ;
- décider seuil cumulé ER et seuil/déduction EBC (calibrage Vic, placeholders assumés dans le yaml) ;
- mapper typepsc 02/15 (au moins re-router les 11 ER mal codés en 02) ;
- dédoublonner à l'ingestion (cf. A.5) — même chantier que la réparation A1, PAS un mandat d'ingestion dédié.

### A.5 Bonus — les prescriptions ont le même mal qu'A1, en pire

Doublons md5(geom) dans `plu_gpu_prescription` : **5 394 groupes (5 391 inter-communes), 7 284 lignes
excédentaires sur 17 765 (41 %)** — ingestion par bbox de commune. Impact verdict quasi nul aujourd'hui
(le seuil ER est par-objet et le dédoublonnage (tp,lib) avale les copies identiques ; la pré-faisa fait
`ST_Union` filtré commune), mais toute évolution vers un seuil CUMULÉ devra dédoublonner d'abord.

---

## BLOC B — Anomalie A1 approfondie (doublons `plu_gpu_zone`)

### B.1 Reproduction

`md5(ST_AsBinary(geom))`, kind=`plu_gpu_zone` (6 306 lignes) : **441 groupes dupliqués — 100 %
inter-communes — 458 lignes excédentaires, max 3 copies** (ex. triplets La Possession + Saint-Denis +
Saint-Paul). Reproduit à l'identique de l'audit M5.1.

Profil : 311 groupes A/N (324 lignes excéd.) + 130 U/AU (134). Paires dominantes : La Possession+Saint-Paul
(138), Trois-Bassins+Saint-Paul (136), Saint-Denis+Salazie (42), Saint-Denis+Sainte-Marie (39).
Cause mécanique : `ingest` par bbox commune + cascade `prime()` (context.py) qui intersecte TOUTES les
géométries du kind sans filtre commune → la somme des couvertures compte chaque copie.

### B.2 Impact chiffré (simulation dédoublonnée LECTURE SEULE, sémantique cascade reproduite)

Méthode : parcelles intersectant une ligne excédentaire (surface > 0) ; pour chacune, couvertures
recalculées brutes vs `DISTINCT ON (parcelle, md5(geom))` ; classement U-AU/A-N et verdicts rejoués avec
les seuils du yaml (`an_hard_exclude_pct` = **90 %**, `an_mixte_min_pct` = 5 %). Requête : `a1_simulation.sql`.

| indicateur | valeur |
|---|---|
| parcelles affectées (intersectent un doublon) | **29 933** (23 communes) |
| recouvrement zonage sommé > 100 % | **28 142** |
| recouvrement gonflé (brut > dédoublonné) | 28 133 |
| **verdict zonage qui change après dédoublonnage** | **1 557** |
| — HARD_EXCLUDE → POSITIVE_mixte | 1 377 |
| — HARD_EXCLUDE → SOFT_FLAG_partiel | 9 |
| — POSITIVE_mixte → POSITIVE (flag mixte infondé) | 171 |
| **HARD_EXCLUDE zonage potentiellement infondés (≥ 90 % ne tient plus)** | **1 386** |
| zone majoritaire qui change | **967** (N→U 466, N→A 452, N→AUc 18, …) |

Répartition des 1 386 HE infondés : Sainte-Marie 402, La Possession 286, Trois-Bassins 218, Saint-Paul 217,
Salazie 123, Cilaos 99, Saint-Denis 20, Saint-Joseph 18, Le Port 3. **Toutes actuellement écartées.**

**Combien changeraient réellement de statut ?** Croisement avec `cascade_results` : 1 358 des 1 386 ont
AUSSI un HARD_EXCLUDE d'une autre couche (risques/PPR 1 308, déclassement 892, forêt publique 59, parc
national 30, prescription ER 5) → resteraient écartées (comme le témoin AB1341, PPR rouge). **28 parcelles
ont le zonage pour SEULE couche excluante** = candidates à réintégration après dédoublonnage + re-run :
12 La Possession, 7 Trois-Bassins, 3 Saint-Paul, 2 Saint-Joseph, 2 Salazie, 1 Le Port (26 445 m²),
1 Sainte-Marie (liste complète dans le CSV, colonne `hard_exclude_infonde`).

Inversement : **aucun cas U→exclusion** ; les 14 changements de zone majoritaire sur des parcelles NON
écartées (13 a_creuser + 1 réserve foncière) sont des erreurs d'AFFICHAGE fiche (« Zone N x % » gonflé),
sans effet statut. Témoin 97423000AB1341 reproduit exactement : an 94,9 % → 47,5 %, zone majoritaire
N → AUc, HARD_EXCLUDE → POSITIVE_mixte (mais reste écartée : PPR rouge).

### B.3 Livrable

`1-3b-a1-parcelles-affectees.csv` — 29 933 lignes : idu, commune, statut/tier/rang/étage0 (mvt), n zones et
couvertures totales/A-N/U-AU brutes vs dédoublonnées (%), zone majoritaire avant/après, verdict zonage
avant/après, drapeaux `hard_exclude_infonde` / `zone_majoritaire_change` / `verdict_change` (tris en tête).

### Recommandation (Phase 2b)

Une seule réparation racine pour A1 + prescriptions + parc_national (A2) : **dédoublonner à l'ingestion**
(clé md5(geom) par kind, ou filtre commune GPU au lieu de bbox) OU **filtrer commune dans `prime()`**
(attention : certaines couches île — PPR, SAR — sont légitimement multi-communes ; le dédoublonnage md5
par kind est le plus sûr), puis re-run cascade + build-mvt. L'enjeu statut réel est faible (28 parcelles),
l'enjeu CRÉDIBILITÉ est fort : 967 fiches affichent une zone majoritaire fausse et 28 142 parcelles ont un
recouvrement sommé > 100 % exposable en démo.
