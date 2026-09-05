# CONCEPTS CANONIQUES — un concept, une source (CIRCUIT-2 lot 3)

*05/09/2026 — pour chaque concept que l'utilisateur lit, ce qui existe au registre, la source
CANONIQUE proposée (règle de défaut : celle que la fiche parcelle sert déjà par le moteur), et
ce que deviennent les autres : `derivee` (calculée de la canonique), `nommee_a_part` (seconde
source légitime, RENOMMÉE à l'écran avec son origine), `retiree` (rien n'est retiré sans Vic —
aucune ligne ne l'est ici). Vic corrige un choix depuis la page ou par un mot ; rien ne l'attend.*

En tête (3.0) : `zone_servie` (zone d'UNE parcelle — ZONE-1) et `potentiel` (au sol / en
hauteur / table rase — EXPORTS-1) sont AU REGISTRE depuis le 0-bis, distincts de
`zonage_commune` (parts d'une commune). Confirmé, testé (`test_potentiel_et_zone_servie_au_registre`).

| concept | ce qui existe (registre) | canonique | les autres |
|---|---|---|---|
| **Zonage PLU (parcelle)** | `zone_plu_famille` (moteur zone_servie) · `zonage_plu_couche` (couche calée cadastre) · `gpu_brut_couche` (aplats bruts) · `reglement_plu_bloc` | **zone_servie** (dominante par surface, a_cheval dit) — fiche, couche, PDF, Copilote | GPU brut = `nommee_a_part` (déjà « Limites officielles PLU (GPU brut) » — le document opposable, hors cadastre) |
| **Zonage (commune)** | `part_zone_U/AU/A/N_pct`, `parcelles_par_zone_n` (moteur zonage_commune) | **zonage_commune** (parts de SURFACE — décision Vic 2.1) | le compte de parcelles du filtre = `nommee_a_part` (« parcelles en zone … », jamais une part) |
| **Règles de la zone** | `reglement_plu_bloc`, `statut_plu`, `destination_statut`, `n_extraits_plu`, `n_communes_rnu` | **plu_destinations** (corpus calibré + registre RNU) | — (une seule chaîne) |
| **Aléas & PPR** | `alea_inondation_couche`/`alea_mvt_couche` (cartographie d'aléas DEAL, NIVEAUX) · couche « Risques PPR » + `ppr_pct` + cascade (zonage réglementaire) | deux CONCEPTS distincts, pas un doublon : l'EXPOSITION (aléa, niveau) et la RÈGLE (PPR) | déjà `nommee_a_part` à l'écran (« Aléa … » vs « Risques PPR ») ; domaine des niveaux verrouillé (RETOURS-13, sonde 4.2) |
| **Littoral / 50 pas** | `cinquante_pas_couche` + couche cascade | **cinquante_pas_deal** (une source) | — |
| **Dispositifs (QPV/ANRU/ZFANG/FRR/TVA)** | `perimetres_dispositifs_liste` (fiche) · `dispositifs_couche` (carte) · `qpv_n` (commune) | **spatial_layers** (mêmes kinds partout) ; TVA primo = `derivee` (buffer 500 m des QPV, dit « Estimé ») | — |
| **Permis** | `n_permis_proximite` (500 m·24 mois) · `permis_12m_n`/`permis_5a_n` (commune) · `depots_secteur_n` (section·36 mois) · `historique_permis_liste` (parcelle) · `point_mort_n` | **marche_service.permits** (profils nommés, paramètres TRANSMIS — 0-bis) ; UN réservoir sitadel | chaque fenêtre/rayon est DANS le libellé (0-bis) — cinq lectures, cinq noms, une source |
| **Logements engagés** | offre Sitadel (détail couche VEFA : collectifs autorisés 24 mois) | **sitadel** | — |
| **Prix — secteur / commune / neuf / affiché vs acté** | `prix_terrain_secteur_eur_m2`+`prix_sortie_bati_eur_m2` (parcelle-secteur) · `prix_ancien_median_eur_m2`+`prix_terrain_zone_eur_m2` (commune) · `prix_neuf_vefa_acte_eur_m2` (scoring) / `prix_neuf_observe_eur_m2` (bilan/exports) · `prix_demande_median_eur_m2`+`ecart_demande_acte_pct` (Radar, affiché vs acté) | **marche_service** (point d'appel unique) — le grain et l'usage sont DANS le libellé | MESURÉ sur les 4 témoins (3.3) : secteur 3811/2308/3103/3118 ≠ ancien commune 4278/3041/3015/2469 ≠ VEFA acte 4742/—/4916/4998 — trois définitions réelles, AUCUNE fusion ; la scission du neuf (0-bis) a soldé le seul vrai doublon |
| **SDP & résiduel** | `sdp_residuelle_m2`, `classe_residuel`, `densifier_couche`, `n_densifiables` | **potentiel** (au sol, garde de lecture zone dominante ZONE-1) | la couche lit le MÊME run servi (`parcel_renouvellement`/`parcel_residuel`) |
| **Constructibilité (scénarios)** | `potentiel_verdict`, `surface_vendable_m2`, `surface_plancher_m2`, `marge_surelevation_m`, `capacite_logements`, `charge_fonciere_eur`, postes `bilan_*` | **potentiel** + **bilan_promoteur** (moteur commun EXPORTS-1) | — |
| **Division / copropriété** | `divisible_classe` (division parcellaire, run) · `coproprietes_liste` (RNIC) | deux concepts, deux noms (division d'or ≠ copropriété immatriculée) | — |
| **DPE** | cascade `dpe_passoire` + rattachement Radar | **dpe_ademe** (une source) | — |
| **Propriétaire & dirigeants** | `type_proprietaire`, `n_parcelles_pm`, `proprietaire_timeline_liste`, `acquisitions_pm_n` (fichier PM) · `evenements_proprietaire_liste` (BODACC/SIRENE) | **proprietaire_historique** (fichier PM, une assiette) ; événements = BODACC, autre concept | — |
| **Transport & TCSP** | `transport_couche` (GTFS 7 réseaux + Papang OSM) · `distance_arret_m` (fiche — GTFS/OSM, concordance DITE) · `tcsp_couche` + fiche TCSP (GTFS route BAO, une seule source) · « bus » du détail scoring (OSM, interne au modèle) | **GTFS** (lignes, arrêts, axe BAOBAB) — fiche et couche lisent le même | Papang = OSM `nommee_a_part` (dit dans le « i ») ; distance « bus » du détail de score = interne modèle (Estimé), jamais libellée « Transport public » |
| **Équipements** | `equip_osm_couche` (OSM) · `bpe_couche` (INSEE BPE) · `equipements_proximite_liste` (fiche « À proximité » — BPE) | **BPE** pour la ligne « À proximité » de la fiche (RETOURS-7 Z5, source dite dans le payload) ; **OSM** pour les amenités du MODÈLE (scoring) | jamais fusionnées, chaque couche porte sa source ; **corrigé ce lot** : le « i » de la couche OSM prétendait encore alimenter les distances de la fiche (périmé depuis Z5) — les deux « i » disent désormais qui nourrit quoi |
| **Population** | `habitants_n` (commune, INSEE RP/Filosofi) · `population_zone` (zone, carreaux 200 m) | deux grains, deux noms (commune vs zone atteignable) | — |
| **Réseaux / assainissement** | `viabilisation_verdict` (faisceau) · `part_logements_egout_pct` (EGOUL, taux statistique) · zonage d'assainissement (GPU, cascade) | trois lectures nommées : faisceau (accès/réseaux), TAUX (INSEE), RÈGLE (zonage) | — |
| **Solaire & toiture** | `prod_spec_kwh_kwc`, `azimut_bati_deg` | **solaire** (PVGIS gelé, millésime porté en base) | — |
| **Occupation du sol** | CoSIA (modèle, bâti révélé) · OCS « BD CARTO V5 » (couche cascade, « grain grossier » dit) | **cosia** pour le calcul | OCS = `nommee_a_part` (libellé porte déjà « grain grossier ») |
| **Friches** | cascade `friche` (Cartofriches) | **cartofriches** | — |
| **QPV** | voir Dispositifs | — | — |

## Doublons de définition (3.3) — mesurés, verdict

- Le SEUL doublon de définition réel (`prix_neuf_vefa_eur_m2` : acte vs observé sous un même id)
  a été soldé par SCISSION au 0-bis — la mesure sur les 4 témoins ci-dessus le confirme (4 742
  vs prix observé du bilan, chaînes distinctes, sonde `verifier_scission_neuf`).
- Aucun autre couple d'ids ne rend la même valeur à l'arrondi près sur les témoins (prix
  secteur/commune/VEFA tous distincts ; grains population distincts par construction ;
  `prix_demande_saisi_eur` ≠ `prix_demande_eur` : saisie client vs fait d'annonce, dit dans les
  deux définitions). **0 fusion, 0 libellé partagé** (`test` : aucun libellé en double au registre).

## Ce qui a été appliqué tout de suite (règle de défaut, autonomie)

1. `frontend/src/lib/layers.ts` — le « i » de la couche « Équipements (OSM) » ne prétend plus
   alimenter les distances de la fiche (c'est la BPE depuis RETOURS-7 Z5) ; le « i » de la
   couche BPE dit qu'elle nourrit la ligne « À proximité » de la fiche. Rien de supprimé.
2. Aucun autre renommage nécessaire : les secondes sources légitimes étaient déjà nommées avec
   leur origine (BPE vs OSM, GPU brut vs zonage par parcelle, aléa vs PPR, ancien vs VEFA).
