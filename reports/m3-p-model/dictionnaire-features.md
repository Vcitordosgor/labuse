# Dictionnaire de features — modèle P (M3, blocs Z + D)

Convention as-of : pour l'année d'observation Y, toute feature n'utilise que
des événements **strictement antérieurs au 01/01/Y** ; le label n'utilise que
les mutations L2 de [01/01/Y, 31/12/Y]. Fenêtres clampées au 01/01/2021
(millésimes DVF antérieurs retirés par la DGFiP) — la couverture réelle est
portée par `window_coverage`.

Interdits (absents par construction) : statut matrice, computed_at, score V
(baseline lot 5 uniquement), tout calcul daté de 2026 hors couches statiques
consignées ci-dessous. `owner_type` est une méta de ventilation d'évaluation,
jamais une feature.

| Feature | Bloc | Type | Monotonie | Source | Fenêtre | Disponibilité | Notes |
|---|---|---|---|---|---|---|---|
| `rot_nu` | Z | num | ↑ contrainte | DVF L2 dédupliqué (p_model_mut_l2) + stock parcelles | 36 mois glissants finissant au 31/12/Y-1 (clampés à 2021), annualisés | acte publié DVF, ~6 mois de latence DGFiP | rotation nu du secteur, shrinkage empirique vers le taux commune |
| `rot_bati` | Z | num | ↑ contrainte | DVF L2 dédupliqué + stock parcelles | 36 mois glissants finissant au 31/12/Y-1, annualisés | acte publié DVF, ~6 mois de latence DGFiP | rotation bâti du secteur, même shrinkage |
| `med_pm2_terrain_36m` | Z | num | libre | DVF L2 mutations nues (valeur / surface terrain de la mutation) | 36 mois finissant au 31/12/Y-1 | idem DVF |  |
| `med_pm2_bati_36m` | Z | num | libre | DVF L2 mutations bâties (valeur / surface bâtie de la mutation) | 36 mois finissant au 31/12/Y-1 | idem DVF |  |
| `tendance_pm2_bati` | Z | num | libre | DVF L2 : médiane €/m² bâti 12 derniers mois vs début de fenêtre | [Y-1] vs [Y-3, Y-1] | idem DVF |  |
| `permis_24m_norm` | Z | num | libre | Sitadel PC+PA autorisés (DATE_REELLE_AUTORISATION), rattachés au secteur via idu_codes, normalisés par le stock de parcelles | 24 mois finissant au 31/12/Y-1 | date d'autorisation connue immédiatement ; publication Dido mensuelle, latence 1-3 mois consignée |  |
| `dens_bati_secteur` | Z | num | libre | BD TOPO bâtiments × parcelles (emprise / surface du secteur) | statique | millésime unique en base (ingestion 2026) — fuite faible, consignée |  |
| `pct_bati_secteur` | Z | num | libre | BD TOPO : part de parcelles bâties du secteur | statique | millésime unique en base (ingestion 2026) — fuite faible, consignée |  |
| `filo_snv_pp` | Z | num | libre | Filosofi INSEE carreau 200 m : niveau de vie / individu | statique (millésime Filosofi 2019) | millésime unique en base (ingestion 2026) — fuite faible, consignée |  |
| `filo_pct_pauv` | Z | num | libre | Filosofi 200 m : part ménages pauvres | statique | millésime unique en base (ingestion 2026) — fuite faible, consignée |  |
| `filo_pct_prop` | Z | num | libre | Filosofi 200 m : part ménages propriétaires | statique | millésime unique en base (ingestion 2026) — fuite faible, consignée |  |
| `filo_dens_pop` | Z | num | libre | Filosofi 200 m : individus / km² | statique | millésime unique en base (ingestion 2026) — fuite faible, consignée |  |
| `qpv` | Z | bool | libre | périmètres QPV (spatial_layers kind=qpv), centroïde dans le polygone | statique | millésime unique en base (ingestion 2026) — fuite faible, consignée |  |
| `pente_moy_deg` | Z | num | libre | RGE ALTI 5 m (parcel_terrain.pente_moy_deg) | statique | millésime unique en base (ingestion 2026) — fuite faible, consignée |  |
| `acces_equipements` | Z | num | libre | OSM (parcel_amenites) : Σ exp(-dist/800 m) sur école, santé, commerce, TCSP — distance absente = contribution nulle | statique | millésime unique en base (ingestion 2026) — fuite faible, consignée |  |
| `zone_plu` | Z | cat | libre | GPU zonage agrégé U / AU (AUc,AUs) / A / N, centroïde dans la zone ; 'inconnu' explicite hors couverture | statique (PLU en vigueur à l'ingestion) | millésime unique en base (ingestion 2026) — fuite faible, consignée ; un reclassement PLU postérieur à Y peut refléter la dynamique — risque consigné, pas de zonage historisé disponible |  |
| `window_coverage` | Z | num | libre | mois DVF réellement disponibles dans la fenêtre 36 mois / 36 | par année d'observation | déterministe | dégradation des fenêtres 2022 (burn-in court) — lot 1.4 |
| `nu_constructible` | D | bool | libre | BD TOPO (emprise ≤ 20 m²) × zone PLU U/AU | statique | millésime unique en base (ingestion 2026) — fuite faible, consignée |  |
| `surface_m2` | D | num | libre | référentiel parcellaire (mvt_parcels/parcels) | statique | millésime unique en base (ingestion 2026) — fuite faible, consignée |  |
| `dormance_droits` | D | num | ↑ contrainte | parcel_residuel.pct_potentiel : part du potentiel de droits PLU non consommée (BD TOPO vs droits calibrés) | statique | millésime unique en base (ingestion 2026) — fuite faible, consignée ; NULL = hors périmètre de calcul → bin 'manquant' |  |
| `sous_densite` | D | bool | libre | parcel_residuel.sous_densite | statique | millésime unique en base (ingestion 2026) — fuite faible, consignée |  |
| `sdp_residuelle_m2` | D | num | libre | parcel_residuel.sdp_residuelle_m2 | statique | millésime unique en base (ingestion 2026) — fuite faible, consignée |  |
| `tenure_bin` | D | cat | libre | DVF toutes natures : dernière mutation avant le 01/01/Y → bins {<1, 1-2, 2-3, 3+, inconnu} — troncature 2021 assumée, le bin 'inconnu' (rien depuis 2021) est explicite et sa portée varie avec Y (consigné) | as-of 01/01/Y | idem DVF |  |
| `permis_bin` | D | cat | libre | Sitadel 2013+ : ancienneté du dernier permis SUR la parcelle (tous types) → bins {<2a, 2-5a, 5-10a, 10a+, jamais} ; « permis < 24 mois » attendu NÉGATIF (projet en cours) — signe libre | as-of 01/01/Y | date d'autorisation, latence 1-3 mois |  |
| `canopee_pct` | D | num | libre | LiDAR/ortho (parcel_vegetation.canopee_pct) | statique | millésime unique en base (ingestion 2026) — fuite faible, consignée |  |
| `ndvi_moyen` | D | num | libre | parcel_vegetation.ndvi_moyen | statique | millésime unique en base (ingestion 2026) — fuite faible, consignée |  |
| `friche` | D | bool | libre | Cartofriches (spatial_layers kind=friche) | statique | millésime unique en base (ingestion 2026) — fuite faible, consignée |  |
| `piscine` | D | bool | libre | détection ortho validée ou non-infirmée (type=piscine, hors faux_positif) — signe libre | statique | millésime unique en base (ingestion 2026) — fuite faible, consignée |  |
| `pv_candidat` | D | bool | libre | candidats photovoltaïque (ortho_detections type=pv) | statique | millésime unique en base (ingestion 2026) — fuite faible, consignée |  |
