# COHERENCE-1 — notes de travail : comment le banc interroge chaque lecteur

Relevé (agent d'exploration, 28/09/2026) des routes, paramètres et tables que
`scripts/coherence/` utilise. Vérifié au fil du banc — toute divergence constatée
est corrigée ICI et dans le banc.

## Lecteurs HTTP (API 8605, aucune auth en dev pilote)

| Lecteur | Route | Paramètres utiles |
|---|---|---|
| Fiche parcelle | `GET /parcels/{idu}` | `?source=q_v11_m137` (défaut = run servi) ; `?trace=1` admin |
| Fiche commune | `GET /communes/{commune}/contexte` | cache `commune_contexte_cache` (job nuit) |
| Filtre (compte+liste) | `GET /filtre` | `source, commune, surface_min/max, sdp_min, flags, tiers, zonage, hors_copro, bande, signal, segment, idus=1, limit, offset` |
| Stats | `GET /stats` | mêmes filtres, ventilation `tiers` |
| Tuiles MVT | `GET /map/tiles/{z}/{x}/{y}.pbf` | attrs : `idu, commune, surface_m2, tier_v2, rang_v2, sdp_residuelle_m2, sous_densite, evenement, flags (CSV), zone_lib, zone_fam` |
| Dossier PDF | `GET /dossier/{idu}.pdf?carte=false` | compte requis (plan) — builder `src/labuse/exports/builder.py:construire` |
| Pré-dossier PC | `GET /pre-dossier/{idu}.zip` | compte plan Intégral |
| Copilote v2 | `POST /api/copilote-v2/ask` | `{message, contexte:{idu}}` — coût LLM réel (haiku routeur + sonnet) |
| Étude de zone | `GET /parcels/{idu}/zone?mode=pied&minutes=15` ; `POST /outils/etude-zone` | |
| Faisabilité | `POST /parcels/{idu}/scenario` | 2 scénarios terrain_libere / bati_garde |
| Taxe aménagement | `GET /outils/taxe-amenagement(/config|/prefill?idu=)` | |
| Radar stats | `GET /radar/stats` | commune, type |

## Tables/vues qui doublent les lecteurs (comparaisons île entière)

`parcels` (surface_m2, commune) · `parcel_zone_plu` (zone_fam/zone_lib, dominante) ·
`parcel_residuel` (sdp_residuelle_m2, sous_densite, cause, hauteur_source) ·
`parcel_flags` (run_label=q_v11_m137, layer_name) · `mvt_parcels` (miroir tuiles) ·
`score_labuse` (bande, signal_niveau, contributions, cause) ·
`commune_contexte_cache` (payload JSONB nuit) · `spatial_layers` (kind : ppr, georisque_alea,
plu_gpu_zone, mvt, ravine, cinquante_pas…) · `pm_proprietaires_millesimes` ·
`dfi_filiation` · `dvf_mutations` · `p_model_bati` · `p_model_ext_copro`.

## Pièges connus

- Front vite écoute en IPv6 seulement : `http://localhost:5805/socle/` (pas 127.0.0.1).
- Fiche commune : si `commune_contexte_cache` est vieux, la fiche sert le cache — le banc
  compare cache ET recalcul (déterminisme, cause « cache périmé »).
- `parcel_flags.parcel_id` = `parcels.id` (int), pas l'idu.
- Tuiles : LRU worker + `mvt_tile_cache` z9-11 pré-générées ; ETag fort.
- Copilote : quota/coût — le banc limite à 20 questions (lot F), jamais en boucle.
