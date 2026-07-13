# §1.5 — AUDIT DU MENU OUTILS (M6 Phase 1, lecture seule)

Date : 13/07/2026 · App auditée : http://127.0.0.1:8010/socle/ (LABUSE_DEV_MODE) · Run v2 servi : `m36-l2f-2026-2026-07-12` · Run matrice : `q_v3_datagap`.
Méthode : inventaire Playwright du tiroir réel (`qa_1_5_outils.mjs` + `qa_1_5_outils_b.mjs`, captures sous `captures-1-5/`), exécution d'une requête type EN LECTURE par outil (aucun POST « compute » écrivant en base — matching add/run non exécutés, analysés statiquement), croisement SQL systématique, lecture du code `src/labuse/api/{modules,moteurs,partners,solaire,score_v2}.py`.

## LOT 0 — Inventaire du tiroir Outils (UI réelle) : **19 outils**

Tel qu'affiché (ordre du tiroir, ★ = phare) :

**Détecter le foncier (9)**
1. ★ Scoring v2 (P) — `scoring-v2` (M25)
2. ★ Faisabilité programme — `programme` (M22)
3. ★ Parkings APER — `parkings-aper` (M23)
4. Toitures tertiaires — `toitures-tertiaires` (M24)
5. ★ Division parcellaire — `division` (M01)
6. ★ Foncier fantôme — `fantome` (M07)
7. ★ Scan patrimoine — `patrimoine` (M02)
8. Mode bailleur — `bailleur` (M06)
9. Matching promoteurs — `matching` (M19)

**Analyser & simuler (8)**
10. ★ Assemblage — `assemblage` (M16)
11. Baromètre foncier — `barometre` (M18)
12. Radar permis — `permis` (M03)
13. Promesses mortes — `promesses` (M04)
14. Vélocité admin — `velocite` (M05)
15. Simulateur PLU — `simulplu` (M15)
16. Simulateur ZAN — `zan` (M17)
17. Remonter le temps — `temps` (M08)

**Passer à l'action (2)**
18. ★ Due diligence — `duediligence` (M10)
19. Courrier propriétaire — `courriers` (M09)

Le bouton **Mutabilité** (point spécifique n°3) n'est PAS dans le tiroir : c'est le toggle de mode carte de l'en-tête (Verdict / Mutabilité) — traité en section dédiée.

## Tableau des verdicts

| # | Outil | Fonctionne bout en bout | Données | Périmètre matrice ? | Verdict |
|---|---|---|---|---|---|
| 1 | Scoring v2 (P) | oui (onglets, sélection→fiche) | run 12/07, à jour | non (v2 natif) | **OK** — anomalie : 119 brûlantes affichées vs 117 doctrine (étage 0 non filtré) |
| 2 | Faisabilité programme | oui (300 candidates, critères affichés) | résiduel + PLU calibré | **OUI** (candidats) | **DÉGRADÉ** — 25/139 opportunités v2 invisibles ; compteur = cap 300 non signalé |
| 3 | Parkings APER | oui (liste, carte, tranches) | parkings_aper 11/07, frais | non (hors scoring) | **DÉGRADÉ** — compteur « 500 assujettis » vs 736 réels (cap LIMIT) ; CSV cappé idem |
| 4 | Toitures tertiaires | oui (liste triée potentiel) | MV sur bâti dupliqué | non | **DÉGRADÉ** — 74/300 lignes du top = doublons (bâti ×2 inter-communes) |
| 5 | Division parcellaire | oui (4 428 candidats, lot dessiné) | **figées 07/07**, bâti pollué | non (ignore même l'étage 0) | **DÉGRADÉ sérieux** — 48 % des candidats en exclusion dure (PPR rouge, public) + faux négatifs massifs (cf. section) |
| 6 | Foncier fantôme | oui (600 affichées, verrou/levier) | PM millésime 2024 (2025 publié) | oui (q_score ≥ 50) | **DÉGRADÉ** — compteur « 38 609 gelées » FAUX (réel : 6 263 ; le count omet le verrou INPI) |
| 7 | Scan patrimoine | oui (CBO → 1 833 parcelles, BODACC) | PM 2024 ; tier v2 affiché | non (tri rang v2) | **OK** — écart mineur 1 871 (suggestion) vs 1 833 (détail) : 38 idus hors cadastre courant |
| 8 | Mode bailleur | oui (2 062 QPV île · 500 affichées) | QPV génération 2024 (⚠ DOM 2025 à vérifier, M5.1) | **OUI** (statuts) | **DÉGRADÉ** — brûlantes v2 « écartées matrice » exclues ; 7-20 s sans vrai état de chargement |
| 9 | Matching promoteurs | UI oui (2 profils démo) ; run non testé (écrit) | event_log : 8 bascules, toutes démo | **OUI** (bascules matrice) | **DÉGRADÉ** — moteur branché sur « a_surveiller → chaude » (lexique disparu) ; zéro donnée réelle |
| 10 | Assemblage | oui (API : 2 contiguës, score 100, SDP 8 278) | résiduel + tier v2 | non | **OK** — clic-carte non automatisable headless (validé art antérieur qa_moteurs) |
| 11 | Baromètre foncier | JSON oui (8 trimestres) ; **PDF → HTTP 500** | DVF ventes → déc. 2025, à jour | non | **DÉGRADÉ + PDF CASSÉ** (cf. section) |
| 12 | Radar permis | oui (4 980 permis · carte) | Sitadel réel → 30/05/2026 | non | **DÉGRADÉ** — fenêtre ancrée sur l'outlier 17/08/2026 : bandeau faux + 610 permis perdus |
| 13 | Promesses mortes | oui (9 092 · 500 affichées) | Sitadel + cascade run | partiel (test « non bâti » via run) | **OK** — lenteur 3-6 s île |
| 14 | Vélocité admin | oui (24 communes, tris, CSV) | Sitadel | non | **OK** — limites honnêtes affichées (pas de dépôt→décision) |
| 15 | Simulateur PLU | oui (AUc : ratio 0,369, 400 parcelles) | cascade run + résiduel | **OUI** (bascule = statuts matrice) | **OK** (léger) — « bascules potentielles » raisonnent en statuts legacy |
| 16 | Simulateur ZAN | tableau communes oui ; **liste candidates VIDE** | OCS GE 24 communes (millésime non tracé) | **OUI** (statuts) | **DÉGRADÉ** — moitié de l'outil structurellement morte (cf. anomalies) |
| 17 | Remonter le temps | oui (split, poignée, 1950-1965) | orthos IGN WMTS | overlay parcelles = statuts legacy | **OK** |
| 18 | Due diligence | analyse oui (1/1 trouvée, flags/exclusions) | run + v2 | non (tier v2 affiché) | **DÉGRADÉ** — chaque lien « ⬇ PDF » → HTTP 500 (fpdf2) |
| 19 | Courrier propriétaire | oui (génération vérifiée, contenu correct) | parcels | non | **OK** — aucun envoi, 3 contextes |
| — | Mutabilité (en-tête) | oui (gradient + légende, 0 erreur) | parcel_residuel (162 947 SDP > 0) | non | **RETRAVAILLER** (cf. section) |

Zéro erreur console sur les 19 ouvertures + mode Mutabilité (2 passes complètes).

## Anomalies transverses (découvertes à cet audit)

- **T1 — fpdf2 absent de l'environnement qui sert l'app** (`miniforge3/envs/labusedb` : `ModuleNotFoundError: fpdf`, pourtant déclaré `fpdf2>=2.8` au pyproject). Conséquence : **TOUS les PDF sont HTTP 500** — baromètre PDF, PDF fiche (`/parcels/{idu}/export.pdf`), PDFs de la due diligence. Repro : `curl -s http://127.0.0.1:8010/moteurs/barometre.pdf` → 500. Réparation triviale (pip install fpdf2 dans l'env + restart) mais hors mandat lecture seule.
- **T2 — bâti dupliqué inter-communes (frère de l'anomalie A1 PLU, jamais consigné)** : `spatial_layers kind='batiment'` = 817 506 lignes pour **513 930 géométries distinctes** (247 825 géométries stockées ≥ 2 fois, 100 % inter-communes — ingestion par bbox communale qui déborde). Taux par commune : de 9 % (Saint-Philippe) à **100 % (La Plaine-des-Palmistes, Les Avirons)**. Pollue M01 (cf. section Division), M24 (doublons de toitures), et potentiellement toute mesure d'emprise bâtie.
- **T3 — compteurs plafonnés présentés comme des totaux** : M23 (« 500 parkings assujettis » vs 736 en base ; CSV exporté aussi tronqué à 500 sans mention), M24 (« 300 toitures » = LIMIT), M22 (« 300 parcelles candidates » = LIMIT sans total). À l'inverse M04/M06/M07 affichent « total · N affichées » — le pattern existe, il n'est pas appliqué partout.
- **T4 — `/v2/brulantes` et `/v2/liste` ne filtrent pas l'étage 0** : le module Scoring v2 affiche **119** brûlantes quand chips/compteurs/liste en affichent **117** (doctrine M5.1 « l'étage 0 prime »). Deux vérités dans la même UI.
- **T5 — compteur Fantôme faux ×6** : la requête de total (déclenchée dès que ≥ 600 lignes) omet les conditions de verrou INPI → « 38 609 parcelles gelées » au lieu de 6 263 réelles. La liste affichée, elle, est correcte.
- **T6 — fenêtre Sitadel ancrée sur l'outlier** : M03 ancre sa fenêtre sur `max(date)` = 17/08/2026 (l'outlier producteur consigné M5.1) au lieu du max réel 30/05/2026. Le bandeau affiche « Données jusqu'au 2026-08-17 » (faux) et la fenêtre 24 mois perd 610 permis en queue (30/05→17/08/2024). Le garde-fou `date <= now()` recommandé en M5.1 réglerait les deux.
- **T7 — liste ZAN structurellement vide** : M17 exige `weight_applied > 0` sur la couche `ocs_ge` du run, or au run servi `q_v3_datagap` cette couche n'applique QUE -5 (SOFT_FLAG malus, 431 663 lignes vérifiées). Zéro « ZAN-compatible » possible quel que soit le territoire — la moitié « détection » de l'outil est morte depuis le changement de convention de la cascade.

## Point sur les périmètres restés « matrice » (consigné M5.1 lot 3, à trancher ici)

L'affichage est unifié v2 (TierBadge : tier v2 principal, « (matrice : X) » secondaire) mais les REQUÊTES candidates de M06 bailleur, M17 ZAN, M22 programme (et la logique de bascule M15, les bascules M19) filtrent toujours sur `matrice_statut IN ('chaude','a_surveiller','a_creuser')`. Impact mesuré :

- **99 des 117 brûlantes v2 effectives** ont un statut matrice hors de cette liste (écartées matrice) → invisibles de ces périmètres, dont le rang 1 île `97423000AB1908` (brûlante v2, matrice `ecartee`).
- M22 avec le programme par défaut (8 unités, SDP ≥ 552 m²) : **25 des 139 opportunités v2 éligibles n'apparaissent jamais** (18 %).
- Conséquence produit : la promesse M5.1 (« un seul monde visible : le v2 ») est tenue en surface mais pas dans les gisements des outils — un promoteur qui passe par « Faisabilité programme » ou « Mode bailleur » travaille sur le monde d'avant.

Recommandation : basculer ces WHERE sur le tier v2 effectif (brûlante/chaude/à creuser hors étage 0), même famille de correctif que T4.

---

## 1. DIVISION PARCELLAIRE (M01) — comment il calcule, et pourquoi il n'est pas fiable aujourd'hui

**Algorithme** (`modules.py` L69-136 ; la spec officielle est absente du repo, les critères C1-C5 sont définis dans le code) :
1. **Pré-calcul par commune** (POST `/modules/division/compute`, résultats stockés dans `module_division` ; le GET ne fait que lire). Dernier calcul : **07/07/2026**, 4 433 candidats, 23 communes (Saint-Philippe absent — RNU, aucune zone U : légitime).
2. Filtres SQL : **C1** surface 600-5 000 m² · **C2** bâti 1-3 corps ET emprise bâtie 5-40 % (somme des intersections `spatial_layers kind='batiment'` / surface parcelle) · **C3** zone PLU dominante commençant par « U » (plus grande intersection) · **C4** lot libre : la parcelle est érodée d'un buffer de 3 m autour du bâti (`ST_Difference(parcelle, ST_Buffer(bati, 3))`), puis **plus grand cercle inscrit** (`ST_MaximumInscribedCircle`) dans l'espace restant → le « lot » est le carré inscrit dans ce cercle (côté r√2, aire 2r²) ; seuils r ≥ 6 m et aire ≥ 200 m² · **C5** accès voirie : la PARCELLE (pas le lot) à ≤ 5 m d'un segment `kind='voirie'`.
3. **Score** = 30·min(lot/500,1) + 25·(1−emprise) + 20·min(r/12,1) + 15·voirie + 10, plafonné à 100.

**Hypothèses/limites assumées par construction** (certaines affichées au bandeau UI, honnête) :
- Le lot carré axis-aligned inscrit dans le cercle est une approximation **conservatrice** : sous-estime les lots allongés (un fond de jardin de 12×40 m donne r≈6 → lot « 72 m² » refusé alors que 480 m² sont détachables).
- Recul de 3 m **uniquement autour du bâti** : aucun recul aux limites séparatives ni règle de prospect PLU — le lot dessiné peut coller la limite du voisin.
- Accès voirie mesuré depuis la parcelle entière : un lot enclavé au fond d'une parcelle dont la façade touche la rue « a un accès ».
- Aucune règle de division du PLU (taille minimale, bande de constructibilité), réseaux non regardés — assumé (« à instruire »).

**Pourquoi il n'est PAS fiable en l'état — sans détour, avec exemples** :
1. **Il propose de détacher des lots sur des parcelles inconstructibles** : il ignore totalement la cascade ET le scoring. **2 143 des 4 428 candidats score ≥ 70 (48 %) sont en étage 0 du run servi** (exclusion dure). Exemples reproduits : `97415000AS0899` score **92** → « Exclue : PPR zone rouge (inconstructible) » ; `97415000AH0513` score 75 → propriété **COMMUNE DE SAINT-PAUL** (non acquérable) + PPR rouge. Un client qui ouvre l'outil phare « Division » voit en tête des terrains où AUCUN lot à bâtir n'est possible.
2. **Ses entrées bâti sont polluées par T2 (bâti dupliqué)** : sur 150 candidats retenus échantillonnés, 30 % ont un `bati_count` faux et 29 % une emprise fausse de > 2 points. Pire, le filtre C2 exclut en masse des vrais candidats (emprise/nb de corps doublés) : à **Bras-Panon, 597 parcelles passent C2 avec le bâti dédupliqué contre 142 avec les données actuelles — 474 candidats réels perdus (77 %)**, cohérent avec les 21 candidats finaux dérisoires de la commune (91 % de bâti dupliqué). Le biais est systématique et inégal selon les communes (9 %-100 % de doublons) : les COMPARAISONS inter-communes n'ont pas de sens.
3. **Données figées** : `computed_at` = 07/07 pour les 24 communes ; tout re-calcul passe par un POST par commune que rien ne planifie (à re-lancer après correction de T2, PAS avant).

Verdict : **DÉGRADÉ sérieux** — la mécanique géométrique (MIC, score) est saine et le bandeau honnête, mais (a) croiser l'étage 0 est indispensable avant toute démo, (b) le pré-calcul doit être relancé après dédoublonnage du bâti. En l'état, l'outil sur-promet (candidats inconstructibles en tête) et sous-détecte (faux négatifs massifs à l'est).

## 2. BAROMÈTRE FONCIER (M18) — filtres DVF, outliers, villa vs collectif

**Ce qu'il sert** (`moteurs.py` L193-283) : 3 tableaux île entière — mutations DVF par trimestre (8 derniers) avec médiane €/m² bâti, permis Sitadel par trimestre, top communes par médiane €/m² (≥ 100 mutations) — en JSON (panneau) et PDF (**cassé, cf. T1**).

**Sa source** : `dvf_mutations` = geo-DVF Etalab RE-AGRÉGÉ à l'ingestion (`layers_ingest.py::_geo_dvf_aggregate`) — c'est mieux que le DVF brut :
- 1 ligne = 1 mutation réelle (29 565 mutations 2021→déc. 2025, `mutation_id` unique vérifié) ;
- **multi-lots/multi-parcelles : traité** — surfaces des locaux résidentiels sommées par mutation, valeur = valeur de la mutation → le €/m² multi-lots n'est PAS surcompté ;
- mutations mixtes maison+appartement écartées ; seules les mutations avec local résidentiel, surface et géoloc sont conservées.

**Filtres réellement appliqués par le baromètre** : la MÉDIANE ne retient que `surface_bati > 0 AND valeur > 0 AND €/m² ∈ [100, 12 000]` — cette bande évacue de facto les ventes symboliques (16 ventes ≤ 1 € en base) et les ratios aberrants. Les COMPTES de mutations, eux, n'ont AUCUN filtre.

**Est-il pollué ? Démonstration par requêtes (2025)** :
- **Ventes 1 € / hors bande** : exclues de la médiane (bande 100-12 000), mais comptées dans « mutations » (ex. 2025T1 : 15 lignes hors bande sur 1 052). Impact : marginal.
- **Multi-parcelles** : non — traité à l'ingestion (ci-dessus).
- **VEFA** : INCLUSE dans les médianes ET les comptes (1 407 mutations VEFA en base). La médiane VEFA vaut **4 734-5 347 €/m² contre 2 826 servis** (2025T3) — mais le flux VEFA s'est effondré (2-4/trimestre en 2025) : l'impact actuel sur la médiane servie est ≤ 2 €/m² (2 826 vs 2 826 ventes seules). Le risque est PROSPECTIF : à la prochaine vague de livraisons, la « médiane du marché » se déformera sans que rien ne le signale. Les natures non-Vente (160 adjudications, 66 échanges, 3 expropriations) sont également comptées.
- **Villa vs collectif : NON distingué — c'est le vrai défaut.** La base porte `type_local` (15 574 Maison / 13 991 Appartement) mais le baromètre fond tout : 2025T3 maison 2 764 €/m² vs appartement 2 865 €/m². Surtout, le « top communes » compare des mix incomparables : Saint-Paul « 4 351 €/m² » avec **51 % d'appartements** contre Salazie « 1 304 €/m² » 100 % maisons — le classement mesure autant la part du collectif que le niveau de prix. Et le tableau « prix par commune » agrège **toute la fenêtre 2021-2025** sans découpe temporelle.
- **Angle mort structurel : il n'y a AUCUN terrain nu** dans `dvf_mutations` (l'agrégation ne garde que les mutations avec local résidentiel). Un « baromètre FONCIER » qui ne montre que du bâti résidentiel… alors que la base contient déjà `dvf_secteur_medianes` type `terrain` : **789 secteurs, 9 581 ventes de terrains** avec médiane €/m², jamais montrées nulle part. Plein potentiel clairement inexploité.

Verdict : **DÉGRADÉ** — honnête sur les outliers unitaires (bande + agrégation par mutation), cassé côté PDF (T1), mais médiane mono-indicateur (mélange maison/appart/VEFA/natures), top communes non comparable, et le marché du terrain — le cœur du métier LABUSE — absent alors que la donnée existe en base.

## 3. MUTABILITÉ (toggle d'en-tête) — à quoi il sert, verdict

**Ce que c'est** : le second mode du toggle Verdict/Mutabilité (Header L277). En mode Mutabilité, le remplissage des parcelles passe des couleurs de tier v2 à un **gradient continu sur `sdp_residuelle_m2`** (0 → 5 000+ m², MapView `MUTABILITE_COLOR`), légende dédiée « MUTABILITÉ / SDP résiduelle ». Données : `parcel_residuel` (162 947 parcelles avec SDP > 0), propriété présente dans les tuiles.

**Fonctionne-t-il ?** Oui — vérifié Playwright île et commune (Saint-Paul) : bascule instantanée, gradient rendu, légende commutée, retour Verdict propre, zéro erreur console/réseau (captures `mode_mutabilite*.png`).

**Le problème n'est pas technique, il est sémantique** :
- Ce mode colore la **capacité constructible restante** (SDP résiduelle), PAS une « mutabilité ». Or depuis M5, « probabilité de mutation à 12 mois » est PRÉCISÉMENT ce que vend le scoring v2 (P) — et la doctrine produit (Réserve foncière) martèle que **capacité ≠ probabilité de muter** (« C fort, P faible… peu de chances de muter »). Le bouton d'en-tête contredit frontalement ce lexique : il appelle « Mutabilité » ce que le reste de l'app appelle « capacité ».
- Trace d'un legacy : `/map/bati` (app.py L1430) se déclare « pour le mode carte mutabilité » mais n'est appelé par AUCUN code front — endpoint mort, docstring périmée.

**Verdict tranché : RETRAVAILLER (a minima : renommer) — ne pas supprimer.**
- SUPPRIMER serait une perte : la vue « où reste-t-il du gisement constructible » est complémentaire du verdict et fonctionne parfaitement ; c'est la seule lecture continue de la carte.
- GARDER tel quel entretient une collision de vocabulaire avec l'argument de vente n°1 (le P v2) — inacceptable en démo client (« pourquoi cette parcelle très “mutable” est-elle en réserve foncière ? »).
- Le retravail est minime : renommer le bouton « **Capacité (SDP)** » (la légende dit déjà « SDP résiduelle » — seul le mot du toggle ment), purger `/map/bati` ou sa docstring. Option ambitieuse pour plus tard : un vrai mode « Mutabilité » = gradient du percentile P v2.

---

## Annexes

- Scripts rejouables : `reports/m6-audit/qa_1_5_outils.mjs` (passe complète 19 outils) et `qa_1_5_outils_b.mjs` (inventaire + reprises). Lancement : `cd frontend && node ../reports/m6-audit/qa_1_5_outils.mjs`.
- Captures : `reports/m6-audit/captures-1-5/` (lot0_tiroir, outil_<key>, mode_mutabilite, mode_mutabilite_commune).
- Chiffres SQL-exacts recalculables : toutes les requêtes de ce rapport sont en SELECT sur `postgresql://openclaw@localhost:5432/labuse`.
- Nota bene lenteurs : les modules île entière (bailleur ~7-20 s, ZAN ~13 s, promesses ~3-6 s) répondent sans cache ; sous charge concurrente les panneaux restent sur « — » sans indicateur de chargement franc — état vide/chargement à prévoir (rejoint A3/M6 1.6).
