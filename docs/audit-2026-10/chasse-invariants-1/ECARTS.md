# ECARTS — CHASSE-INVARIANTS-1

Une ligne par violation. Gravité : **FAUX-CLIENT** (l'utilisateur voit un chiffre faux) ·
**INCOHERENT** (deux lecteurs servis se contredisent) · **ROBUSTESSE** (plantage / affichage
sale / chiffre non signifiant, sans donnée fausse). Base servie : q_v18 / run_seq 15, 434 582
parcelles. Audit LECTURE SEULE — aucune correction appliquée.

## FAUX-CLIENT

| # | idu / périmètre | attendu | obtenu | cause | fichier:ligne | dom |
|---|---|---|---|---|---|---|
| E-01 | 61 599 parcelles (`taux_emprise_pct>100`, 9 735 >300 %). Pire : `97411000AY0015` = **19 569 %** (= parcel_id 331544) | taux d'occupation du gabarit borné à ~100 % | % bruts servis dans l'export **Comparatif** (« Taux d'occupation du gabarit : 19569 % ») + tuile gabarit + filtre emprise | `100*emprise_batie/emprise_max` sans `min(100,…)` à l'écriture du run ; l'export n'a pas le plafond de la fiche | `faisabilite/residuel.py:215-216` (écriture) · `exports/blocs/comparatif.py:77-79,97` + `api/app.py:8069` (export non plafonné) | **1 + 12** (trouvé 2× indépendamment) |
| E-02 | 1 380 parcelles (sur 2 901 zonables orphelines). Témoin `97401000AH0371` : fiche « Ud1 » + SDP 1 907 m² | toute parcelle intersectant une zone GPU a une ligne `parcel_zone_plu` (carte = fiche) | SDP positive servie mais **zone-less à la carte/filtres/liste** (table dérivée jamais reconstruite) | `parcel_zone_plu` bâtie une fois, reconstruite seulement si ABSENTE/VIDE, jamais si périmée | `api/tiles.py:148-155` (condition de rebuild trop faible) · `tiles.py:40-107` | 2 |
| E-03 | 224 parcelles ≥50 % PPR rouge (union) sans HARD_EXCLUDE, **dont 30 servies constructibles**. Pire `97401000AK0138` : **score B/60, 8 297 m² SDP, 65 % rouge** ; `97401000AM1179` 92 % rouge → D/55 m² | union(INTERDICTION) ≥50 % ⇒ HARD_EXCLUDE ⇒ rouge déduit ⇒ SDP sur la seule partie hors rouge | chaque polygone INTERDICTION évalué séparément (aucun n'atteint 50 %) ⇒ rouge jamais clippé ⇒ terrain majoritairement rouge servi bâtissable | la cascade n'`ST_Union` pas les polygones de même kind (coverage par polygone) | `cascade/context.py:340-366` · `cascade/layers/phase1.py:663-703,683` | 4 |
| E-04 | fenêtre DVF « 3 ans / 12 mois » du bloc Marché secteur + comparables (fiche/Flash/Dossier/PDF). Île : 12 030 ventes réelles vs 10 962 servies = **−1 068 (−8,9 %)**. `97411000AK0182` : 129 réelles → 121 servies | fenêtre ancrée sur `max(date_mutation)` (dernière vente = 2026-08-10) | fenêtre sur `CURRENT_DATE` (2026-10-14) → 65 j d'avance jettent les ventes du vieux bord | correction L7 non propagée aux lecteurs DVF génériques | `flash/data.py:489,515,602,625` · `marche_service.py:255` | 5 |
| E-05 | 5 fiches §Identité : âges **117** (`97411000BL0284`/`BL0392`, prouvé live), **114** (`97416000DW0432`), **0** (`97401000AI1157`), **13** (`97422000BX0880`), **4** (`97422000CS0612`) | âge dirigeant personne physique ∈ [18 ; 110], sinon pas de ligne « Dirigeant » | âges 0/4/13/114/117 servis bruts (aîné pris par `date_naissance ASC`, sans garde-fou de bornes) | `_pm_dirigeant` renvoie `int(age)` sans clamp ; dates INPI RNE erronées (1909/1911) ou futures (2026-11) | `api/app.py:5787-5800` (rendu `:5879`) | 6 |
| E-06 | `97416000DW0432` (SCI MAKBOULE) dans l'outil « Successions à venir » avec `dirigeant_age=114` | âge cohérent ≤110 pour justifier une « succession à venir » | 114 ans → `propension_band=tres_eleve` écrit dans la veille | `max(age)` non borné dans la vue + lecture sans clamp (clamp seulement dans le fallback) | vue `v_pm_propension_vendre` · `scoring/score_v.py:104-110` | 6 |

## INCOHERENT

| # | idu / périmètre | attendu | obtenu | cause | fichier:ligne | dom |
|---|---|---|---|---|---|---|
| E-07 | 9 792 parcelles vivantes, centroïde jusqu'à 236 m hors géométrie (`97414000CK0122`) | point « centre » garanti DANS la parcelle (`ST_PointOnSurface`) | `ST_Centroid` (barycentre) sort des géométries concaves | mauvais opérateur à l'ingestion | `ingestion/cadastre_ingest.py:42` | 1 |
| E-08 | 20 243 lignes `parcel_residuel_bati` : emprise bâtie > dessin (ex. `97406000AI0587` 18/6 m²) — **n'atteint PAS la fiche** | emprise bâtie clippée à la parcelle ⇒ ≤ surface | table amont non clippée (la fiche, elle, clippe via `bati.py`) | donnée d'ingestion non clippée | `parcel_residuel_bati` (ingestion) — lecteur servi sain `bati.py:119,147,234` | 1 |
| E-09 | 433 229 lignes (100 %) `surface_terrain_m2 IS NULL` sur q_v18 et son snapshot | surface du calcul écrite à chaque ligne (« Calcul du JJ/MM sur X m² ») | colonne vide → note de péremption générique, fonction « surface du calcul » muette | run figé AVANT peuplement de la colonne (code d'écriture présent, non rejoué) | run q_v18 obsolète · `residuel.py:243` (écriture) · `api/app.py:6336,6346` (lecteur) | 1 |
| E-10 | 607 parcelles bande A ET `cascade_exclue=true` (route/DPF/forêt publique) | une parcelle exclue dure ne remonte pas en tête de bande A sans marque | les 2 dimensions coexistent ; le tri ignore `cascade_exclue` | `bande` et `cascade_exclue` stockées sans fusion (bénin SI l'overlay d'exclusion est peint) | `scoring/score_labuse_combine.py:134,140-146` · `cascade_v2.py:52,90` | 3 |
| E-11 | 30 parcelles (sous-ensemble de E-03). `97401000AM1179` : fiche « rouge inconstructible 92 %, rédhibitoire » vs score D/9, SDP 55 m² | les 2 lecteurs du même PPR rouge s'accordent | fiche (union) dit rédhibitoire, score/SDP (cascade non-unionnée) servent constructible | même racine que E-03 | `api/servitudes.py` (union) vs `cascade/...` (non-union) | 4 |
| E-12 | fiche commune, 22/24 communes. Saint-Paul `surface_ha`=23 080 vs vivant 22 927 = **+153 ha fantômes (238 disparues)** ; Saint-André +120 ha | `surface_ha` sur le MÊME parc que `n_parcelles` (vivant) | `surface_ha` somme TOUTES les parcelles, disparues comprises | manque le `filtre_vivant_sql` sur la surface | `api/app.py:2161-2163` vs `registre/moteurs/commune.py:102-114` | 8 |
| E-13 | 1 148 parcelles, `taux_emprise_pct=40` exactement + `sous_densite=true` | si taux affiché = 40 et seuil = 40 %, `sous_densite` = false | flag calculé sur le taux NON arrondi (39,6 % réel), colonne stockée arrondie (40) → contradiction de bord | deux colonnes servies, l'une arrondie l'autre non | `faisabilite/residuel.py:217-218` vs `:234` | 12 |

## ROBUSTESSE

| # | idu / périmètre | attendu | obtenu | cause | fichier:ligne | dom |
|---|---|---|---|---|---|---|
| E-14 | `GET /map/tiles/{z}/{x}/{y}.pbf` et `/map/tiles/{kind}/{z}/{x}/{y}.pbf` avec x/y hors `[0,2^z)` ou négatif | 204 / tuile vide (comme pour z hors plage) | **HTTP 500** nu (`ST_TileEnvelope: Invalid tile x value`) | `z` validé, `x`/`y` jamais bornés avant `ST_TileEnvelope` | `api/tiles.py:820-840,625,546` · `api/couches_tuyau.py:731-754,646-647,606` | 11 |
| E-15 | `charge_supportable` jusqu'à 183,9 M€, `marge_estimee` −115 M€…+85 M€ sur très grandes parcelles (`97415000DK1169` 34,8 ha) | marge estimée lisible pour un promoteur | chiffres en dizaines de M€ (arithmétiquement justes, mais vides de sens métier) | bilan à rebours sans garde-fou de surface/SDP max | `ingestion/score_e.py:152-155` | 5 |

## Anomalies de SOURCE déjà neutralisées par le lecteur (traçabilité, non actives)

| # | périmètre | état | dom |
|---|---|---|---|
| N-01 | clôture BODACC en 2117 (`C201900709638`) | filtrée `<= now()`, retombe sur année de parution | 7 |
| N-02 | 7 754 permis dépôt > autorisation | note d'incohérence servie à l'écran/PDF, jamais réordonné | 7 |
| N-03 | 10 800 permis sans parcelle existante (idu_codes morts) | jamais servis par idu ; carte/voisinage géométrique seulement | 7 |
| N-04 | 1 mutation DVF datée 2026-08-10 sous source bornée 2025 | outlier d'ingestion (1/29 566), pas futur | 9 |
| N-05 | caches `commune_contexte`/`spatial_layers_sub` « périmés » | local non-warmé, auto-réparant, non servi faux | 9 |

## Lecture transversale
- **E-01 = E-03 racine « intermédiaire impossible non borné »** et **E-03/E-11 = racine « non-union des polygones »** : deux familles de racine unique touchant plusieurs lecteurs.
- **E-05 = E-06 racine unique** : âge dirigeant servi sans clamp de bornes (3 lecteurs : fiche, filtre 70+, veille succession).
- Domaines à chasse VIDE prouvée : **7** (permis/DPE/BODACC, 0 écart actif), **9** (dates/run, 0 FAUX-CLIENT), **10** (Copilote, 0 hallucination). La preuve tient au nombre de parcelles/lignes passées, pas à l'absence de recherche.
