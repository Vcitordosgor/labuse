"""SOURCES-AUDIT-1 — verdicts 'Lue' consolidés des 4 agents de traçage (robinet nommé).
Merge bind+vannes+lue → /tmp/sources_audit_full.json. Lecture seule.
verdict: oui / non / na (na = pas de table à lire, règles code).
"""
import json

# slug -> (verdict, "robinet nommé — écran")
LUE = {
 # fam0
 "abf_merimee": ("oui", "couche `abf` couches_tuyau:couche_tuile → carte ; cascade rule abf → onglet Risques fiche"),
 "ban": ("oui", "app.py:_ban_adresse (adresses/adresse_parcelles) → fiche parcelle ; pré-dossier PDF"),
 "bd_ortho_irc": ("oui", "ortho_detections→parcel_equipements→ortho.py:equipements→badges fiche ; parcel_vegetation→PDF (vegetation_zonal_acc interne)"),
 "bruit_itt_cerema": ("oui", "couche `bruit_route`→carte ; cascade rule bruit_route → onglet Risques fiche"),
 "catnat_gaspar": ("oui", "fiche_commune.py:risques (catnat_arretes) → fiche commune + outil risques"),
 "cosia": ("oui", "couche `piscine_cosia`→carte + bloc fiscal ; p_model_bati_cosia→parcel_bati_revele→'Le bien' (qa_cosia_bati/parcel_cosia_couverture=interne ; batiment_cosia non servi)"),
 "deal_ppr": ("oui", "couche `ppr`→carte ; cascade risques (ppr) → onglet Risques fiche (verdict/exclusion)"),
 "dgfip_parcelles_pm": ("oui", "app.py:_q_v2_fiche (parcelle_personne_morale) + proprietaire_historique (pm_proprietaires_millesimes) → bloc propriétaire fiche"),
 "dvf": ("oui", "moteurs.py baromètre/prix (dvf_mutations*, dvf_prix_sortie_neuf)→Baromètre/fiche marché ; couche vefa_neuf→carte+cascade Marché (dvf_secteur_medianes/dvf_mutation_detail=interne)"),
 "enp_complements_deal": ("oui", "couche `ens` (via kind enp) → carte ; cascade ens → onglet Risques fiche"),
 "frr_ex_zrr": ("oui", "couche `frr`→carte + territoire_fiscal→bloc fiscal fiche ; territoire_fiscal_commune→fiche commune"),
 "georisques_cavites": ("oui", "couche `cavite`→carte ; cascade cavite → onglet Risques fiche"),
 "georisques_ssp": ("oui", "couche `sol_pollue` (kinds sis/casias)→carte ; cascade sol_pollue → onglet Risques fiche"),
 "gpu_zonage_assainissement": ("oui", "parcel_anc→anc_service:statut_anc→ViabilisationBlock fiche ; couche zonage_assainissement→outil Servitudes invisibles"),
 "insee_rp2022_egoul": ("oui", "anc_maille_taux→anc_service:statut_anc (taux secteur)→bloc assainissement fiche (rp_logement_commune=métadonnée)"),
 "loyers_dhup": ("oui", "loyers.py:fiche_block (JSON embarqué)→export md/html /parcels/{idu}/export SEULEMENT (pas la fiche React live)"),
 "osm_overpass": ("oui", "couche `amenite`→carte + score amenites cascade→onglet Marché ; osm_faux_positif→motif exclusion cascade fiche"),
 "peb_dgac": ("oui", "couche `peb`→carte ; cascade peb → onglet Risques fiche"),
 "qpv_2024": ("oui", "couche `qpv`→carte ; _territoire_fiscal_block (kind qpv + tva_primo)→fiche (TVA réduite/QPV)"),
 "rnb": ("oui", "rnb_batiments→bati.py:le_bien_block→bloc 'Le bien' fiche (rnb_rattachement_bdtopo=builder)"),
 "rtaa_dom": ("na", "aucune table — règles RTAA DOM portées par le code (constructibilité) ; rien à lire en base"),
 "spanc_epci": ("oui", "saisie collectif/non-collectif → parcel_anc.zone_anc → anc_service:statut_anc → bloc assainissement fiche"),
 "taxe_amenagement": ("oui", "taxe_amenagement.py:taux_communal_public (taxe_amenagement_taux)→_taxe_amenagement_block fiche + outil Financier (câblé ; table seed vide)"),
 "znieff_inpn": ("oui", "couche `znieff`→carte ; cascade znieff → onglet Risques fiche"),
 # fam1
 "anct_ort": ("oui", "fiche_commune.py:ort (commune_ort)→fiche commune 'ACV/PVD/ORT' ; filtres/sources acv→Denormandie"),
 "ban_plus": ("oui", "bati.py:le_bien_block (ban_plus_liens WHERE idu)→fiche parcelle 'Le bien'"),
 "bd_topo": ("oui", "couches_tuyau sert batiment/cimetiere/construction_*/zone_activite/bassin_versant/axe_structurant/ligne_ht→carte ; ravine→cascade phase1→Risques (voirie/water non servis)"),
 "cadastre_api_carto": ("oui", "couche `limites_parcelles`→carte ; parcels lue par toute fiche /parcels/{idu} (socle du produit)"),
 "cinquante_pas_deal": ("oui", "couche `cinquante_pas`→carte"),
 "cout_construction_sdes": ("oui", "faisabilite/engine.py (cout_construction_ref)→outil Faisabilité + bilan Financier"),
 "deal_wms_wfs": ("oui", "hub sans table propre — data servie via proxys couches qpv_2024/npnru (eux-mêmes Lus)→carte"),
 "dgfip_rei": ("oui", "fiche_commune.py:fiscalite (commune_rei)→fiche commune 'Taxe foncière (REI)'"),
 "edf_hta": ("oui", "couche `ligne_mt`→carte ; cascade fiche_couches2 ligne_mt 50m→onglet Risques fiche"),
 "erosion_cotiere_geolittoral": ("oui", "couche `trait_de_cote`→carte ; cascade"),
 "georisques_api": ("oui", "couche via virtuels alea_inondation/alea_mvt (kind georisque_alea)→carte"),
 "georisques_icpe": ("oui", "couche `icpe`→carte ; cascade→onglet Risques fiche"),
 "gpu_plu_api_carto": ("oui", "couches plu_gpu_zone/prescription→carte ; app.py:_reglement_plu_block (plu_reglement_extrait)→'Règlement d'urbanisme' fiche"),
 "gtfs_pan": ("oui", "couches transport_arret/transport_ligne/pole_echange→carte ; cascade transport_ligne 400m→Réseaux fiche"),
 "insee_rp_iris": ("oui", "zone.py (iris_rp, P22_*)→Étude de zone ; fiche 'Autour'/quartiers"),
 "loyers_oll": ("oui", "regle loyer_median_eur_m2 (oll_loyers/oll_zonage)→fiche commune 'Loyers'"),
 "osm_transport": ("oui", "couches `telepherique`+`pole_echange`→carte"),
 "plh_epci": ("oui", "fiche_commune.py:plh (plh_epci WHERE epci)→fiche commune 'PLH'"),
 "radar_pige": ("oui", "pige/client.py:lister/detail (pige_biens/annonces/faits/prix_historique)→Radar ; releves.py (radar_releves)→Marché (pige_captures/interets_agence=interne)"),
 "rnic_anah": ("oui", "app.py (rnic_coproprietes WHERE parcelle_idu)→bloc 'Division (copropriétés)' fiche"),
 "sirene_etablissements": ("oui", "zone.py:etude_de_zone (sirene_etablissements)→outil Étude de zone (concurrents/emplois) ; fiche 'Autour' + PDF Flash"),
 "sru_dhup": ("oui", "fiche_commune/flash (commune_contexte_sru)→fiche commune 'SRU' + comparateur + projets"),
 "tcsp_osm": ("oui", "couche virtuelle `tcsp` (tcsp_zone+tcsp_troncon+tcsp_station)→carte"),
 "zonage_abc_dhup": ("oui", "fiche_commune.py:zonage_abc (commune_zonage_abc)→fiche commune 'Zonage A/B/C'"),
 # fam2
 "annuaire_service_public": ("oui", "mairies→app.py bloc K2 mairie_de→fiche commune (coordonnées) + outil pack PLU (annuaire_services=admin Contacts seul)"),
 "bd_carto_ocs": ("oui", "couche `artificialisation`→carte ; ocs_ge→cascade phase1 OcsGeLayer→onglet Règles fiche (ZAN)"),
 "bodacc": ("oui", "projets.py:_signaux_parcelles (bodacc_procedures)→Projets/carte ; events.py→notifications ; app.py (bodacc_annonces_owner)→bloc propriétaire (bodacc_sondages=scoring interne)"),
 "cadastre_epoque": ("non", "SEUL lecteur ingestion/cadastre_historique.py:rattacher_par_geometrie = FABRICANT (corrige sitadel_permits.geom) ; aucun endpoint ne SELECT la table ; la fiche affiche une prose statique sans donnée"),
 "communes_ign": ("oui", "couche `limites_communes` via mvt_communes→carte (Repères)"),
 "deal_bruit_cartes": ("oui", "couche `bruit_carte`→carte ; onglet Risques fiche (cascade)"),
 "deal_zones_humides": ("oui", "couche `zone_humide`→carte (tuyau)"),
 "dpe_ademe": ("oui", "app.py:_dpe_connu_block (dpe_records)→payload dpe_connu→fiche 'DPE du bâtiment' leBien.tsx (robinet câblé ; table quasi-vide 16 l.)"),
 "enaf_cerema": ("oui", "rarete.py:compute_rarete (commune_conso_enaf)→'Enveloppe ZAN' ContextePanel ; carnet secteur"),
 "filosofi_carreaux": ("oui", "fiche_commune.py:population (filosofi_carreaux_200m)→ContextePanel ; marche_secteur→MarcheSecteurBlock fiche (p_model_filo=build scoring)"),
 "georisques_azi_tri": ("oui", "couche `tri_zone`→carte ; azi_tri.py:azi_tri_commune (azi_communes)→ContextePanel Risques fiche commune"),
 "georisques_mvt": ("oui", "cascade etage1:MvtLayer (kind mvt, cascade_rules spatial_kind:mvt)→onglet Risques fiche (couche map alea_mvt lit un AUTRE kind georisque_alea)"),
 "gpu_prescriptions_ebc": ("oui", "couche virtuelle `ebc`→plu_gpu_prescription(subtype 01)→carte (et `er` subtype 05)"),
 "inpi_rne": ("oui", "veille_promoteurs.py + modules.py (pm_dirigeants)→outil Scan patrimoine/Veille promoteurs (pm_dirigeant_gigogne→v_pm_propension→score_v indirect)"),
 "insee_rp_logement": ("oui", "app.py:_compute_commune_contexte (commune_insee_logement)→ContextePanel 'Population & logement' fiche commune (tenure)"),
 "npnru": ("oui", "couche `anru`→carte ; _compute_commune_contexte (anru_quartiers)→ContextePanel 'Quartiers prioritaires' fiche commune"),
 "parc_national_inpn": ("oui", "couche `parc_national`→carte (tuyau)"),
 "potentiel_foncier_ods": ("oui", "cascade phase2 (potentiel_foncier_region)→onglet Marché fiche (bonus potentiel_foncier_region ; pas de couche map servie)"),
 "recherche_entreprises_dinum": ("oui", "score_v_fetch:fetch_owner_enrichment (connector live, JOB)→owner_enrichment/owner_denom_lookup→score_v→parcel_v_score→ScoreV2Block fiche (build-then-surface)"),
 "rpg_proxy_ign": ("oui", "couche `safer` (RPG/SAFER)→carte 'Foncier agricole déclaré'"),
 "sirene_recherche_entreprises": ("oui", "connector live confirme la PM propriétaire ; affichage APE via table jumelle sirene_etablissements (proprietaire_facettes/_pm_identite)→carte d'identité PM fiche + concurrents EtudeZone"),
 "sudocuh": ("non", "SEUL lecteur scoring/p_v2/qv14.py:226 (sudocuh_procedures)→feature anciennete_plu présente UNIQUEMENT dans le run candidat q_v14 ; run servi = q_v11_m137 → 0 contribution ; aucune surface client"),
 "trafic_rn": ("oui", "zone.py:trafic_zone→POST /outils/etude-zone→outil EtudeZone 'Trafic routes nationales' (véh./j)"),
 # fam3
 "arcep_fibre": ("oui", "zone.py (arcep_immeubles, immeubles FttH)→outil Étude de zone / fiche"),
 "bd_ortho": ("oui", "ortho.py:equipements + fiche_commune (n_piscines) (parcel_equipements)→fiche Réseaux + outil Piscines (ortho_tiles=build, ortho_detections=QC ML)"),
 "bpe_insee": ("oui", "couche `amenite_bpe`→carte ; app.py:_PROX_EQUIP→proximités fiche"),
 "cartofriches": ("oui", "couche `friche`→carte ; cascade etage1 FricheLayer→fiche parcelle"),
 "contours_iris": ("oui", "anc_service.statut_anc (JOIN kind=iris_insee)→Viabilisation fiche + PDF ; zone.py→étude de zone (couche iris_insee non servie sur carte, lue en jointure)"),
 "deal_dpf_dpe": ("oui", "couche `dpf`→carte ; cascade phase1 DpfLayer→fiche parcelle"),
 "dgfip_dfi": ("oui", "moteurs.py:_filiation_parcelle (dfi_filiation)→fiche parcelle Filiation"),
 "dpu_perimetres": ("oui", "couche `dpu`→carte ; cascade phase1 DpuLayer→fiche parcelle"),
 "endiguement": ("oui", "couche `endiguement`→carte ; cascade fiche_couches2→onglet Risques fiche"),
 "forets_onf_bdtopo": ("oui", "couche `foret_publique`→carte ; cascade phase1→fiche parcelle"),
 "georisques_casias": ("oui", "couche front `casias` (kind sol_pollue subtype casias)→carte ; cascade Risques→fiche"),
 "georisques_sis": ("oui", "couche front `sis` (kind sol_pollue subtype sis)→carte ; cascade Risques→fiche"),
 "gpu_prescriptions_er": ("oui", "couches front `er`+`ebc` (kind plu_gpu_prescription subtypes 05/01)→carte"),
 "inpn_espaces_proteges": ("oui", "couche front `enp` (kind ens)→carte"),
 "lidar_hd_mnh": ("oui", "solaire_toiture.py (toiture_lidar)→fiche solaire ; batiment_hauteur_lidar→bâti 3D + faisabilite constructibilité (lidar_dalle_grille=état batch)"),
 "ocsge": ("oui", "bati.py:le_bien_block (parcel_ocsge, % artificialisé)→'Le bien' fiche ; couche `artificialisation`→carte"),
 "parkings_osm_aper": ("oui", "faisabilite/viabilisation_build:aper_note (parkings_aper)→note APER tiroir Urbanisme fiche + PDF"),
 "pvgis": ("oui", "modules.py:prospection_solaire (parcel_solar)→outil Prospection solaire + fiche soleil (solar_grid=intermédiaire)"),
 "rge_alti": ("oui", "parcel_terrain (rgealti_pente_5m)→fiche Terrain (pente) ; couche `pente`→carte + cascade PenteLayer (couche altitude non lue ; MNT rgealti_mnt_5m via enrichment)"),
 "rpls_sdes": ("oui", "app.py:_q_v2_fiche (rpls_commune)→fiche 'Marché' (parc social) + PDF"),
 "sitadel": ("oui", "app.py:permits_geojson→couche Permis SITADEL ; modules.py→outil Permis ; moteurs.py/events→fiche 'Autour' + baromètre commune"),
 "sup_gpu": ("oui", "couche `sup` (table tuyau_sup)→carte ; /map/couche-detail/sup→détail au clic"),
 "zfang": ("oui", "couche `zfang`→carte ; territoire_fiscal (territoire_fiscal_commune)→fiche 'Dispositifs territoriaux' + fiche commune + PDF"),
}

d = json.load(open("/tmp/sources_audit_vannes.json"))
missing = []
for o in d:
    v = LUE.get(o["slug"])
    if not v:
        missing.append(o["slug"]); o["lue"], o["lue_robinet"] = "?", ""
    else:
        o["lue"], o["lue_robinet"] = v
# corriger communes_ign réinjectable (seed re-jouable, pas 'base vide')
for o in d:
    if o["slug"] == "communes_ign":
        o["reinjectable"], o["reinjectable_why"] = "oui", "seed embarqué (référentiel re-jouable, tuiles mvt_communes)"

json.dump(d, open("/tmp/sources_audit_full.json", "w"), ensure_ascii=False, indent=1)
from collections import Counter
print("LUE:", Counter(o["lue"] for o in d))
print("manquants:", missing)
print("\n=== Lue=non / na ===")
for o in d:
    if o["lue"] in ("non", "na", "?"):
        print(f'  {o["lue"]:3} {o["slug"]:28} {o["lue_robinet"][:90]}')
print(f"\ntotal sources: {len(d)}")