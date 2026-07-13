# M6 Phase 1 §1.9 — Fiabilité des Vues (fiches client)

Audit LECTURE SEULE du 13/07/2026 — branche `audit/grand-check`, base `labuse` (SELECT uniquement), app `http://127.0.0.1:8010`.

**Périmètre** : les 5 vues métiers actives de la galerie « Vues » (presets du moteur de segments Habitat, table `segment_presets`, moteur `src/labuse/segments/{registry,engine}.py`) + la vue **Foncier — Brûlantes & chaudes** (scoring v2, tuile `data-vue-fonciere` de `SegmentsPage.tsx`).

**Méthode** : définition exacte relue en base (`segment_presets.filtres` jsonb) et dans le registry ; compte servi recalculé en SQL **et** confronté à l'API produit (`POST /segments/query`, `GET /segments`, `GET /stats?source=q_v3_datagap`) ; couvertures mesurées par requête ; millésimes repris de l'audit fraîcheur M5.1 (`reports/m51-unification/FRAICHEUR.md`, vérifié en ligne les 12-13/07/2026).

## Cohérence servi / affiché (contrôle §3)

| Vue | Compteur UI (cache `segment_preset_counts`, 12/07 12:10) | Compte live (API + SQL, 13/07) | Écart |
|---|---:|---:|---|
| Pergolas & terrasses | 5 315 | 5 315 | aucun |
| Paysagistes | 3 992 | 3 992 | aucun |
| Piscinistes — construction | 5 541 | 5 541 | aucun |
| Parc piscines — entretien | 5 784 | 5 784 | aucun |
| PV résidentiel | 2 381 | 2 381 | aucun |
| Foncier (tuile) | 117 brûlantes · 960 chaudes (live `/stats`, cache 30 s) | 117 · 960 | aucun |

L'UI affiche le cache 24 h des compteurs ; il est aujourd'hui identique au calcul live. La tuile Foncier est SQL-exacte (pas de chiffre codé en dur). Filtres inactifs : **aucun** (toutes les sources requises sont présentes et non vides — disponibilité « complet » sur les 5 presets).

## Dénominateurs et couvertures mesurées (13/07/2026)

Parc total : **431 663 parcelles** ; servables par le moteur (`surface_m2 ≥ 2`, anti-slivers) : **430 813**.

| Source d'un filtre | Table | Couverture mesurée | Producteur / millésime |
|---|---|---|---|
| Jardin & emprise bâtie | `parcel_residuel_bati` | 292 056 parcelles avec bâti (67,7 %) — **les 139 607 restantes sont traitées « jardin = surface entière »** (LEFT JOIN + COALESCE) | BD TOPO IGN, éd. avril 2026 (juillet 2026 en diffusion) |
| Dernière mutation / type de bien | `dvf_mutations_parcelle` | 37 868 parcelles mutées 2021-2025 (8,8 % du parc) ; type de local renseigné : 18 179 | DGFiP DVF, publication 20/04/2026, couvre jusqu'au **31/12/2025** |
| Pente | `parcel_terrain` | 423 452 (98,1 %) | RGE ALTI 5 m — **produit gelé par l'IGN depuis 2024** (bascule MNT LiDAR HD au backlog) |
| Piscine / PV détectés | `parcel_equipements` | 11 558 lignes ; **8 299 piscines** ; **pv_detecte = 0 partout (détection PV = stub, jamais livrée)** | Détection LABUSE sur BD ORTHO IGN 2025 ; précision piscine 90,7 % (échantillon interne 300 vignettes, 11/07/2026) |
| Score solaire, facture, proprio-occupant, ombrages | `parcel_solar` | 431 663 (100 %) ; facture estimée : 266 056 (61,6 %) ; flag topo-ombrage : 264 ; flag ombrage végétal : 17 670 | PVGIS/SARAH3 (Commission européenne) + Filosofi 2021 + LiDAR HD ; calcul 11/07/2026 |
| ABF | `dryrun_cascade_results` (run `q_v3_datagap`) | 431 663 (100 %) ; 60 618 parcelles en périmètre ABF (14 %) | Mérimée/POP, sync 05/07/2026 ; abords ~500 m (proxy cercle) |
| Année de construction (vues inactives uniquement) | `dpe_records` | **914 DPE sur 277 parcelles (~0,06 %)** | ADEME, sync 12/07/2026 — gisement 974 complet, couverture structurellement minuscule |

Note d'audit (code, sans impact chiffres) : la clé `optionnel: true` présente dans les jsonb de presets n'est **pas interprétée par le moteur** (`engine.compile_one` l'ignore) — un filtre « optionnel » est appliqué comme les autres dès que sa source existe. Les comptes ci-dessus l'intègrent.

---

## FICHE 1 — Pergolas & terrasses (`pergolas-terrasses`)

**Définition exacte** : jardin ≥ 150 m² ET dernière mutation ≤ 24 mois (ancrée sur le flux DVF, max 31/12/2025) ET pente moyenne ≤ 10° ET hors périmètre ABF. Tri : mutation la plus récente.

**Servi aujourd'hui : 5 315 parcelles** (UI identique).

**Ce qu'on garantit**
- Chaque parcelle a réellement été vendue dans les 24 derniers mois du flux DVF (acte notarié, source DGFiP — pas un scraping d'annonces).
- Jardin et pente calculés sur tout le parc (BD TOPO avril 2026, RGE ALTI) ; les parcelles en périmètre ABF (contraintes architecturales) sont écartées d'office.
- Le compteur affiché est le compte SQL exact, recalculable en un clic.

**Ce qu'on ne garantit pas**
- **1 886 des 5 315 parcelles (35,5 %) n'ont aucun bâti détecté** : du terrain nu récemment vendu, pas une maison avec jardin. Le filtre « jardin » vaut « surface non bâtie », donc une parcelle vierge passe toujours.
- Fraîcheur : DVF publie avec ~6 mois de retard — la vente la plus récente date du 31/12/2025 ; « moins de 24 mois » se compte depuis cette date, pas depuis aujourd'hui.
- Une mutation DVF n'est pas toujours un emménagement (ventes SCI, partages, VEFA).

**Chiffres clés** : 5 315 servies · 14 383 parcelles mutées ≤ 24 mois sur l'île · ABF exclut 60 618 parcelles du jeu. **Dernière MAJ données** : DVF 20/04/2026 (couvre 31/12/2025) ; BD TOPO avril 2026 ; Mérimée 05/07/2026.

**Angle mort principal** : ~1 lead sur 3 est un terrain nu (aucune maison où adosser une pergola) — ajouter `emprise_batie_m2 ≥ 20` (comme le preset élagage) le corrigerait.

---

## FICHE 2 — Paysagistes (`paysagistes`)

**Définition exacte** : jardin ≥ 300 m² ET dernière mutation ≤ 12 mois. Tri : jardin décroissant.

**Servi aujourd'hui : 3 992 parcelles** (UI identique).

**Ce qu'on garantit**
- Acquéreurs récents (≤ 12 mois de flux DVF) avec au moins 300 m² non bâtis — le cœur de cible « nouveau propriétaire, jardin à créer/reprendre ».
- Sources publiques officielles (DVF DGFiP, BD TOPO IGN), comptage exact.

**Ce qu'on ne garantit pas**
- **1 567 des 3 992 (39,3 %) sont sans aucun bâti** : terrain nu, client potentiel… ou chantier de construction à venir (peut être un bon lead paysagiste, mais ce n'est pas « une maison avec jardin »).
- Ni ABF ni pente ne sont filtrés ici (contrairement aux pergolas) ; aucune garantie que le « jardin » soit végétalisable (parking, cour, friche).
- Même limite de fraîcheur DVF que ci-dessus (ancrage 31/12/2025).

**Chiffres clés** : 3 992 servies · 7 719 parcelles mutées ≤ 12 mois sur l'île. **Dernière MAJ** : DVF 20/04/2026 ; BD TOPO avril 2026.

**Angle mort principal** : « jardin » = surface non bâtie cadastrale, jamais une qualification paysagère — et 39 % de terrains nus.

---

## FICHE 3 — Piscinistes — construction (`piscinistes-construction`)

**Définition exacte** : jardin ≥ 200 m² ET mutation ≤ 24 mois ET pente ≤ 10° ET **aucune piscine détectée**. Tri : jardin décroissant.

**Servi aujourd'hui : 5 541 parcelles** (UI identique).

**Ce qu'on garantit**
- Acquéreurs récents, terrain plat et assez grand pour un bassin, sans piscine détectée sur l'orthophoto IGN 2025.
- La détection piscine est mesurée : 90,7 % de précision sur un échantillon interne de 300 vignettes (cascade de juges du 11/07/2026) — mention affichée dans le produit et au pied des exports.

**Ce qu'on ne garantit pas**
- L'absence de piscine : le rappel de la détection n'est **pas mesuré** — piscines hors-sol, couvertes, sous canopée ou construites depuis la prise de vue 2025 échappent au filtre ; une partie des 5 541 possède donc déjà un bassin.
- **1 968 des 5 541 (35,5 %) sont sans bâti** : terrain nu (un pisciniste vend rarement avant la maison).
- La faisabilité réglementaire (PLU, servitudes) n'est pas vérifiée par cette vue.

**Chiffres clés** : 5 541 servies · 8 299 piscines détectées sur l'île (base d'exclusion) · précision détection 90,7 % (interne, non contractuelle). **Dernière MAJ** : ortho IGN 2025, détection 11-12/07/2026 ; DVF 20/04/2026.

**Angle mort principal** : « sans piscine » = « sans piscine *détectée* en 2025 » (rappel non mesuré) + 35 % de terrains nus.

---

## FICHE 4 — Parc piscines — entretien & rénovation (`parc-piscines-entretien`)

**Définition exacte** : piscine détectée ET emprise bâtie entre 40 et 400 m² (proxy « habitation individuelle », fix 497→5 784) ET jardin ≥ 100 m². Tri : jardin décroissant.

**Servi aujourd'hui : 5 784 parcelles** (UI identique).

**Ce qu'on garantit**
- Chaque lead porte une piscine détectée sur l'orthophoto IGN 2025 (précision mesurée 90,7 %) **et** un bâti de gabarit maison individuelle — les copropriétés, hôtels et gros équipements sont écartés par le seuil 400 m².
- Surface de bassin estimée disponible en export (statistique).

**Ce qu'on ne garantit pas**
- ~9 % des détections sont des faux positifs (bâches bleues, toits, bassins d'agrément) : la présence réelle se vérifie sur place.
- Le proxy emprise 40-400 m² écarte **2 080 piscines sur parcelles à gros bâti** (dont de vraies grandes villas), 170 sans bâti, 111 à bâti < 40 m², 154 à jardin < 100 m² — soit 2 515 piscines détectées non servies (8 299 → 5 784).
- Aucune information sur l'état ou l'âge du bassin (la vue cible le parc, pas le besoin).

**Chiffres clés** : 5 784 servies / 8 299 piscines détectées · précision 90,7 % (300 vignettes, 11/07/2026). **Dernière MAJ** : ortho IGN 2025 ; BD TOPO avril 2026.

**Angle mort principal** : le proxy « maison » (emprise 40-400 m²) sacrifie ~25 % du parc détecté, surtout les grandes propriétés — précisément des clients entretien à panier élevé.

---

## FICHE 5 — Photovoltaïque résidentiel (`pv-residentiel`)

**Définition exacte** : type de bien « Maison » (dernière mutation DVF) ET score solaire ≥ 60/100 ET pas de PV détecté ET facture électrique estimée ≥ 1 200 €/an ET pas d'ombrage topographique ET probabilité propriétaire-occupant ≥ 50 ET pas d'ombrage végétal du toit. Tri : score solaire décroissant.

**Servi aujourd'hui : 2 381 parcelles** (UI identique). Entonnoir mesuré : 13 090 maisons DVF → score ≥ 60 : 5 262 → facture ≥ 1 200 € : 3 320 → proprio-occupant ≥ 50 : 2 523 → hors ombrages topo/végétal : **2 381**.

**Ce qu'on garantit**
- Gisement solaire calculé sur 100 % du parc (PVGIS/SARAH3, Commission européenne) ; ombrage végétal du toit mesuré au LiDAR HD (17 670 toits sous canopée exclus) ; cirques/remparts exclus (264 parcelles).
- Facture et proprio-occupant sont explicitement étiquetés ESTIMATIONS statistiques (jamais une donnée réelle ni nominative) dans le produit et les exports.

**Ce qu'on ne garantit pas**
- **Le périmètre n'est pas « les maisons de l'île » mais « les maisons vendues depuis 2021 »** : le filtre « Maison » s'appuie sur la dernière mutation DVF → 13 090 parcelles éligibles au départ, sur ~292 000 parcelles bâties. Toute maison non vendue depuis 2021 est invisible pour cette vue.
- **Le filtre « pas de PV détecté » ne filtre rien aujourd'hui** : la détection PV ortho est restée à l'état de stub (`pv_detecte` = 0 partout, clôture Option B wave-ortho) — une partie des leads a déjà des panneaux. Le proxy `pv_existant` (registre national) existe dans `parcel_solar` mais n'est pas branché sur ce preset.
- Le score solaire ne rend pas le gradient côtier Ouest/Est (limite documentée SARAH3) ; la facture estimée manque sur 38 % du parc (les parcelles sans estimation sont exclues par le seuil).

**Chiffres clés** : 2 381 servies · score solaire couvert à 100 % · 2 523 candidats hors PV du registre EDF/OA (au registre : 736 APER dont 24 en échéance = cible repowering séparée). **Dernière MAJ** : parcel_solar 11/07/2026 ; DVF 20/04/2026 ; Filosofi 2021.

**Angle mort principal** : double — périmètre restreint aux maisons mutées depuis 2021 (~4,5 % du bâti), et « sans PV » non vérifié (détection stub).

---

## FICHE 6 — Foncier — Brûlantes & chaudes (vue cœur produit)

**Définition exacte** : parcelles du dernier run scoring v2 (`parcel_p_score_v2`, run `m36-l2f-2026-2026-07-12`, calculé le 12/07/2026 22:11) en tier `brulante` ou `chaude`, **hors étage 0** (statuts `exclue`/`faux_positif_probable` du run cascade servi `q_v3_datagap`), triées par rang. Tiers = modèle P (probabilité de mutation à 12 mois, logistique WoE calibrée) × plancher capacité C (SDP résiduelle > 0 OU ≥ 600 m² en zone U/AU), effectif chaude calibré ~1 150 avec hystérésis anti-churn ; brûlante = surcouche événement daté/top contribution.

**Servi aujourd'hui : 117 brûlantes + 960 chaudes = 1 077 opportunités** (brut : 119 + 1 032, moins 2 + 72 à l'étage 0). La tuile UI affiche exactement ces chiffres.

**Ce qu'on garantit**
- Un classement **backtesté** : sur le test 2025 (année jamais vue du modèle), le top-1158 contenait 40,8 % de parcelles effectivement mutées sous 12 mois (×23,5 vs le taux de base 1,7 %) ; le top-500 : 59 % (×34) — IC bootstrap dans `reports/m3-p-model/test-2025-resultats.csv`.
- Chaque signal est sourcé et daté dans la fiche parcelle (DVF, permis Sitadel, BODACC, PLU, propriétaires DGFiP 2024) ; les copropriétés sont hors classement ; le churn entre recalculs est contenu par hystérésis (< 15 % visé).
- Compteurs SQL-exacts, périmètre cohérent partout (liste, carte, stats — unification M5.1).

**Ce qu'on ne garantit pas**
- **Une probabilité n'est pas une promesse** : ~60 % du top ne mutera pas dans l'année ; le score dit « où prospecter d'abord », jamais « ce terrain se vendra ».
- Le propriétaire n'est pas identifié pour 783 des 1 077 opportunités (particuliers : DGFiP ne publie que les personnes morales, millésime 2024 — le 2025 est publié, à ingérer).
- Les signaux s'arrêtent au flux public : DVF au 31/12/2025, BODACC à ~8 jours, rien sur l'off-market (successions non publiées, intentions de vente) ; PLU de certaines communes à recalibrer (vigilances M5.1).

**Chiffres clés** : 117 🔥 + 960 chaudes (+ 3 607 réserve foncière, vitrine capacité — jamais vendue comme pipeline) · backtest top-500 : 59 % de mutations réelles sous 12 mois. **Dernière MAJ** : run v2 du 12/07/2026 ; DVF 20/04/2026 ; Sitadel 01/06/2026 ; BODACC 05/07/2026 ; PM DGFiP millésime 2024.

**Angle mort principal** : l'identité du propriétaire manque sur ~73 % des opportunités (particuliers), et le signal s'arrête aux flux publics (pas d'off-market) — le rendez-vous terrain reste l'étape de vérité.

---

## Synthèse transverse (à dire en rendez-vous)

1. **Tout chiffre affiché est recalculable** : aucun écart servi/affiché constaté sur les 6 vues (13/07/2026).
2. **Trois angles morts structurels partagés** : (a) « jardin » = surface non bâtie → 35-39 % de terrains nus dans les vues extérieur ; (b) fraîcheur DVF ~6 mois (ancrage 31/12/2025) ; (c) détections ortho = statistiques (piscine 90,7 % précision, rappel non mesuré ; PV non livré).
3. **Corrections à faible coût identifiées** (pour M6, hors périmètre de cet audit) : ajouter `emprise_batie_m2 ≥ 20` aux vues pergolas/paysagistes/piscinistes ; brancher `pv_existant` (proxy registre) sur la vue PV ; documenter dans l'admin que `optionnel` n'est pas interprété par le moteur.
