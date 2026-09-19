"""SOURCES-AUDIT-1 — Réinjectable : vanne (commande/dépôt) + dernière exécution réussie.
Lecture seule. Enrichit /tmp/sources_audit_bind.json → /tmp/sources_audit_vannes.json.
Règle du verdict :
  OUI  = une vanne fonctionnelle existe ET la dernière exécution a réussi (preuve).
  NON  = aucune vanne (hub), OU vanne pas encore fonctionnelle (a_faire/chantier),
         OU dernière exécution en échec.
Preuve « dernière exécution » : last_sync_at (posé par l'ingestion en cas de succès),
ingestion_runs.ok, sinon rempli>0 sans drapeau d'erreur (vanne one_shot déjà passée).
"""
from __future__ import annotations
import json

d = json.load(open("/tmp/sources_audit_bind.json"))

# slug -> commande CLI (vanne). '' quand ce n'est pas une commande (api directe, seed, code, hub, manuel).
VANNE = {
    "abf_merimee": "labuse ingest-abf", "ban": "labuse ingest-ban",
    "bd_ortho_irc": "labuse ortho-refresh/ortho-detect", "bruit_itt_cerema": "labuse ingest-bruit-route",
    "catnat_gaspar": "labuse ingest-catnat", "cosia": "labuse ingest-cosia",
    "deal_ppr": "labuse ingest-georisques (ppr)", "dgfip_parcelles_pm": "labuse ingest-personnes-morales/ingest-pm-millesimes",
    "dvf": "labuse refresh-dvf", "enp_complements_deal": "labuse ingest-deal-carmen",
    "frr_ex_zrr": "labuse ingest-qpv (frr/zfang)", "georisques_cavites": "labuse ingest-georisques",
    "georisques_ssp": "labuse ingest-georisques/ingest-sis-projets", "gpu_zonage_assainissement": "labuse ingest-gpu-infos",
    "insee_rp2022_egoul": "labuse ingest-rp-logement", "loyers_dhup": "",
    "osm_overpass": "labuse ingest-amenites", "peb_dgac": "labuse ingest-gpu-infos",
    "qpv_2024": "labuse ingest-qpv", "rnb": "labuse ingest (RNB)", "rtaa_dom": "",
    "spanc_epci": "", "taxe_amenagement": "labuse ingest-taxe-amenagement", "znieff_inpn": "labuse ingest-georisques",
    "anct_ort": "labuse ingest-ort", "ban_plus": "labuse ingest-ban-plus", "bd_topo": "labuse ingest-mvt (BD TOPO)",
    "cadastre_api_carto": "labuse ingest-island/ingest-real", "cinquante_pas_deal": "labuse ingest-cinquante-pas",
    "cout_construction_sdes": "labuse ingest-cout-construction", "deal_wms_wfs": "",
    "dgfip_rei": "labuse ingest-rei", "edf_hta": "labuse ingest (EDF HTA)", "erosion_cotiere_geolittoral": "labuse ingest-deal-carmen",
    "georisques_api": "labuse ingest-georisques", "georisques_icpe": "labuse ingest-georisques",
    "gpu_plu_api_carto": "labuse ingest-gpu-infos", "gtfs_pan": "labuse ingest (GTFS)", "insee_rp_iris": "labuse ingest-iris-rp",
    "loyers_oll": "labuse ingest-oll", "osm_transport": "labuse ingest-amenites", "plh_epci": "dépôt manuel (PLH)",
    "radar_pige": "labuse radar-depot-html/radar-cycle-*", "rnic_anah": "labuse ingest-rnic",
    "sirene_etablissements": "labuse ingest-sirene-etab", "sru_dhup": "labuse ingest (SRU)", "tcsp_osm": "labuse ingest-amenites",
    "zonage_abc_dhup": "labuse ingest-zonage-abc",
    "annuaire_service_public": "labuse ingest-annuaire-services/ingest-mairies", "bd_carto_ocs": "labuse ingest (BD CARTO)",
    "bodacc": "labuse ingest-bodacc", "cadastre_epoque": "labuse ingest (cadastre époque)", "communes_ign": "seed (référentiel embarqué)",
    "deal_bruit_cartes": "labuse ingest-bruit-cartes", "deal_zones_humides": "labuse ingest-deal-carmen",
    "dpe_ademe": "labuse ingest-dpe", "enaf_cerema": "labuse ingest (ENAF)", "filosofi_carreaux": "labuse ingest (Filosofi)",
    "georisques_azi_tri": "labuse ingest-azi-tri", "georisques_mvt": "labuse ingest-georisques",
    "gpu_prescriptions_ebc": "labuse ingest-gpu-infos", "inpi_rne": "labuse ingest-inpi-rne/ingest-inpi-gigogne",
    "insee_rp_logement": "labuse ingest-rp-logement", "npnru": "labuse ingest-qpv (anru)", "parc_national_inpn": "labuse ingest-georisques",
    "potentiel_foncier_ods": "labuse ingest (potentiel foncier)", "recherche_entreprises_dinum": "",
    "rpg_proxy_ign": "labuse ingest (RPG)", "sirene_recherche_entreprises": "", "sudocuh": "labuse ingest-sudocuh",
    "trafic_rn": "labuse ingest-trafic-rn",
    "arcep_fibre": "labuse ingest-arcep", "bd_ortho": "labuse ortho-tiles/ortho-refresh", "bpe_insee": "labuse ingest-amenites-affichage",
    "cartofriches": "labuse ingest-cartofriches", "contours_iris": "labuse ingest-iris-rp", "deal_dpf_dpe": "labuse ingest-deal-carmen",
    "dgfip_dfi": "labuse ingest-dfi", "dpu_perimetres": "labuse ingest-gpu-infos", "endiguement": "labuse ingest-endiguement",
    "forets_onf_bdtopo": "labuse ingest (forêts ONF)", "georisques_casias": "labuse ingest-georisques", "georisques_sis": "labuse ingest-sis-projets",
    "gpu_prescriptions_er": "labuse ingest-gpu-infos", "inpn_espaces_proteges": "labuse ingest-georisques",
    "lidar_hd_mnh": "labuse ingest (LiDAR dalles)", "ocsge": "labuse ingest (OCS GE)", "parkings_osm_aper": "labuse ingest-amenites",
    "pvgis": "labuse ingest (PVGIS)", "rge_alti": "labuse ortho-pente/ingest (RGE ALTI)", "rpls_sdes": "labuse ingest (RPLS)",
    "sitadel": "labuse ingest-permits", "sup_gpu": "labuse ingest-sup", "zfang": "labuse ingest-qpv (zfang)",
}
# notes RESERVOIR sans vanne fonctionnelle (chantier/a_faire/hub/retiré)
SANS_VANNE = {"deal_wms_wfs": "hub (aucune ingestion propre)"}

for o in d:
    slug = o["slug"]
    mode = o["mode"] or ""
    note = o["note"] or ""
    cmd = VANNE.get(slug, "?")
    o["vanne_cmd"] = cmd
    # preuve dernière exécution
    preuve = []
    if o["last_sync"]:
        preuve.append(f"last_sync {o['last_sync']}")
    if o["fraicheur"]:
        preuve.append(o["fraicheur"])
    if o["err"]:
        preuve.append(f"ERREUR {o['err']}")
    o["preuve_exec"] = " · ".join(preuve) or ("rempli>0" if o["rempli_total"] else "aucune")
    # verdict
    v = "oui"
    why = ""
    if slug in SANS_VANNE:
        v, why = "non", SANS_VANNE[slug]
    elif "a_faire" in note or "CHANTIER" in note:
        v, why = "non", "vanne pas fonctionnelle (a_faire/chantier)"
    elif mode == "en_direct":
        v, why = "oui", "API directe (re-requête à la volée)"
    elif mode == "seed":
        v, why = "oui", "seed embarqué (référentiel)"
    elif cmd == "":
        # pas de table / code / manuel sans dépôt
        if mode == "depot_manuel":
            v, why = "oui", "dépôt manuel"
        else:
            v, why = "n/a", "règles code / repli embarqué (rien à réinjecter)"
    else:
        if o["err"]:
            v, why = "non", "dernière exécution en échec"
        elif o["rempli_total"] and o["rempli_total"] > 0:
            v, why = "oui", "vanne présente, données en base"
        else:
            v, why = "non", "vanne présente mais base vide"
    o["reinjectable"] = v
    o["reinjectable_why"] = why

json.dump(d, open("/tmp/sources_audit_vannes.json", "w"), ensure_ascii=False, indent=1)
# résumé
from collections import Counter
print("verdicts réinjectable:", Counter(o["reinjectable"] for o in d))
print("\n=== sans vanne / non-réinjectable ===")
for o in d:
    if o["reinjectable"] in ("non",):
        print(f'  {o["slug"]:32} {o["reinjectable_why"]}  [{o["preuve_exec"]}]')
print("\n=== n/a (rien à réinjecter : code/repli) ===")
for o in d:
    if o["reinjectable"] == "n/a":
        print(f'  {o["slug"]:32} {o["reinjectable_why"]}')
