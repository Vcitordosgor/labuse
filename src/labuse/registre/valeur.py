"""CIRCUIT-1 lot 1.4 — LE TAMPON : toute valeur servie par le registre porte sa provenance.

`Valeur` = {valeur, chiffre_id, version_def, run, reservoirs:{id: millésime}, calcule_le}.
Les endpoints JSON servent `.valeur` seule par défaut et le tampon complet avec `?trace=1`
(admin seulement) ; les builders PDF et mails reçoivent l'objet et n'utilisent que `.valeur`.

`tampons_pour(db, chiffre_ids)` construit les tampons d'un lot de chiffres en UNE lecture des
millésimes (`data_sources.source_millesime`) + le run du manifeste/pointeur courant pour les
chiffres à portée `run` — c'est le chemin de `?trace=1` sans réécrire les producteurs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text

from .chiffres import CHIFFRES

#: data_sources.name par id de réservoir (reservoirs.csv) — motif ILIKE, jamais un id numérique
#: (les ids data_sources peuvent différer entre bases ; le nom est la clé stable du seed).
_RESERVOIR_NAME_ILIKE: dict[str, str] = {
    "cadastre_api_carto": "Cadastre (API Carto%", "cadastre_etalab_bulk": "Cadastre Etalab%",
    "gpu_plu_api_carto": "Urbanisme PLU/GPU%", "georisques_api": "Géorisques",
    "dvf": "DVF / valeurs%", "rge_alti": "RGE ALTI (altimétrie)%", "bd_topo": "BD TOPO IGN%",
    "ban": "Base Adresse Nationale%", "osm_overpass": "OpenStreetMap / Overpass%",
    "bpe_insee": "BPE INSEE%", "sitadel": "SITADEL%", "abf_merimee": "ABF / Monuments%",
    "erosion_cotiere_geolittoral": "Cerema / GéoLittoral%", "bodacc": "BODACC%",
    "deal_ppr": "DEAL Réunion — PPR%", "inpi_rne": "INPI RNE%",
    "georisques_ssp": "Géorisques — sites et sols%", "georisques_cavites": "Géorisques — cavités%",
    "georisques_icpe": "Géorisques — ICPE%", "cartofriches": "Cartofriches%",
    "georisques_mvt": "Géorisques — mouvements%", "dpe_ademe": "DPE ADEME%",
    "qpv_2024": "QPV 2024%", "sru_dhup": "Inventaire SRU%", "npnru": "NPNRU%",
    "insee_rp_logement": "INSEE RP Logement%", "plh_epci": "PLH des 5 EPCI%",
    "sup_gpu": "SUP — assiettes GPU%", "bruit_itt_cerema": "Classement sonore ITT%",
    "cinquante_pas_deal": "50 pas géométriques%", "pvgis": "PVGIS%",
    "filosofi_carreaux": "Filosofi INSEE%", "bd_ortho": "BD ORTHO 20 cm%",
    "sudocuh": "Sudocuh%", "gpu_zonage_assainissement": "GPU — zonages d'assainissement",
    "contours_iris": "Contours IRIS%", "insee_rp2022_egoul": "INSEE RP2022%",
    "office_eau_chroniques": "Office de l'eau%", "bd_ortho_irc": "BD ORTHO IRC%",
    "lidar_hd_mnh": "LiDAR HD — MNH%", "dgfip_parcelles_pm": "DGFiP — parcelles des personnes%",
    "zfang": "ZFANG%", "frr_ex_zrr": "FRR ex-ZRR%", "gtfs_pan": "Transport public — GTFS%",
    "osm_transport": "OSM — transport%", "znieff_inpn": "ZNIEFF (INPN/MNHN)%",
    "cosia": "CoSIA%", "radar_pige": "Radar (pige%", "sirene_etablissements": "SIRENE établissements%",
    "mobpro": "MOBPRO%", "trafic_rn": "Trafic RN%", "bdnb": "BDNB%",
    "edf_hta": "EDF Réunion — lignes moyenne%", "tcsp_osm": "TCSP — voies bus%",
    "annuaire_service_public": "Annuaire de l'administration%",
    "rnic_anah": "RNIC — copropriétés%",
    "parc_national_inpn": "Parc National de La Réunion%",
    # SOURCES-1 lot 1 — droit des sols
    "gpu_prescriptions_er": "GPU — emplacements réservés%",
    "gpu_prescriptions_ebc": "GPU — espaces boisés%",
    "dpu_perimetres": "GPU — droit de préemption%",
    "peb_dgac": "PEB — plans d'exposition%",
    "zonage_abc_dhup": "Zonage ABC des communes%",
    "zppa_culture": "ZPPA — zones de présomption%",
    # SOURCES-1 lot 3 — sols et bruit
    "georisques_sis": "Géorisques — secteurs d'information%",
    "georisques_casias": "Géorisques — CASIAS%",
    "deal_bruit_cartes": "DEAL — cartes de bruit%",
    # SOURCES-1 lot 2 — nature et eau
    "deal_dpf_dpe": "Ravines — domaine public fluvial%",
    "deal_zones_humides": "Zones humides — inventaires DEAL%",
    "enp_complements_deal": "Espaces protégés complémentaires%",
    "georisques_azi_tri": "AZI / TRI — inondation%",
    "rpg_proxy_ign": "RPG — déclarations agricoles%",
    "inpn_espaces_proteges": "INPN / patrinat%",
}


@dataclass(frozen=True)
class Valeur:
    valeur: Any
    chiffre_id: str
    version_def: str
    run: str | None                       # run servi si portée run, sinon None
    reservoirs: dict = field(default_factory=dict)   # {reservoir_id: millésime servi}
    calcule_le: str = ""
    #: 0-bis (garde de couverture EXPORTS-1 5.5, devenue règle du registre) : tout COMPTEUR
    #: (unité « nombre ») porte {n servi, non_couvert} — la sonde refuse un compteur sans.
    couverture: dict | None = None
    #: 0-bis (portée `projet`) : ISO du moment de saisie client — « saisi par le client le … ».
    saisi_le: str | None = None
    #: lot 1.4 (règle 4 du mandat) : `servie` · `non_determinee` (la source ne dit pas) ·
    #: `non_calculee` (la chaîne a échoué) — un échec technique ne se déguise JAMAIS en absence.
    etat: str = "servie"

    def tampon(self) -> dict:
        t = {"chiffre_id": self.chiffre_id, "version_def": self.version_def,
             "run": self.run, "reservoirs": self.reservoirs, "calcule_le": self.calcule_le}
        if self.etat != "servie":
            t["etat"] = self.etat
        if self.couverture is not None:
            t["couverture"] = self.couverture
        if self.saisi_le is not None:
            t["saisi_par_le_client_le"] = self.saisi_le
        return t


def probleme_couverture(v: Valeur) -> str | None:
    """Règle 0-bis : une Valeur de type COMPTEUR (unité « nombre » au registre) doit porter sa
    couverture ({n, non_couvert}). Rend le problème (str) ou None — la sonde refuse dessus."""
    c = CHIFFRES.get(v.chiffre_id)
    if c is not None and c.unite == "nombre" and v.couverture is None:
        return f"compteur {v.chiffre_id} sans couverture (règle 0-bis, garde EXPORTS-1 5.5)"
    return None


def _millesimes(db, reservoir_ids: set[str]) -> dict[str, str | None]:
    """Millésimes servis des réservoirs demandés, lus de data_sources (une requête)."""
    out: dict[str, str | None] = {}
    motifs = {rid: _RESERVOIR_NAME_ILIKE[rid] for rid in reservoir_ids if rid in _RESERVOIR_NAME_ILIKE}
    for rid, motif in motifs.items():
        try:
            out[rid] = db.execute(text(
                "SELECT source_millesime FROM data_sources WHERE name ILIKE :m LIMIT 1"),
                {"m": motif}).scalar()
        except Exception:  # noqa: BLE001 — base de test partielle : tampon sans millésime, jamais un 500
            out[rid] = None
    return out


def valeurs_pour(db, valeurs: dict[str, Any],
                 couvertures: dict[str, dict] | None = None,
                 etats: dict[str, str] | None = None) -> dict[str, "Valeur"]:
    """CIRCUIT-2 lot 6 — L'API REGISTRE DES EXPORTS : les builders PDF reçoivent des objets
    `Valeur` (valeur + tampon complet : run, réservoirs/millésimes, couverture, état) pour les
    données qu'ils servent — la mise en page continue de lire `.valeur`, l'origine est portée.

    `valeurs` : {donnee_id: valeur brute déjà calculée par le moteur} — seuls les ids fournis
    reçoivent une Valeur (jamais une valeur inventée). `couvertures` : {id: {n, non_couvert}}
    pour les compteurs (règle 0-bis). `etats` : {id: non_determinee|non_calculee} quand la
    chaîne l'a dit."""
    from .. import runs
    voulus = [(cid, CHIFFRES[cid]) for cid in valeurs if cid in CHIFFRES]
    mill = _millesimes(db, {r for _, c in voulus for r in c.reservoirs})
    run_courant: str | None = None
    if any(c.portee == "run" for _, c in voulus):
        try:
            run_courant = runs.current()
        except Exception:  # noqa: BLE001
            run_courant = None
    quand = datetime.now(tz=timezone.utc).isoformat()
    return {cid: Valeur(valeur=valeurs[cid], chiffre_id=cid, version_def=c.version_def,
                        run=(run_courant if c.portee == "run" else None),
                        reservoirs={r: mill.get(r) for r in c.reservoirs},
                        calcule_le=quand,
                        couverture=(couvertures or {}).get(cid),
                        etat=(etats or {}).get(cid, "servie"))
            for cid, c in voulus}


def tampons_pour(db, chiffre_ids: list[str]) -> dict[str, dict]:
    """Le tampon de chaque chiffre demandé (pour `?trace=1`). Une lecture des millésimes,
    le run courant seulement si au moins un chiffre est à portée `run`."""
    from .. import runs
    voulus = [(cid, CHIFFRES[cid]) for cid in chiffre_ids if cid in CHIFFRES]
    tous_res: set[str] = set()
    for _, c in voulus:
        tous_res |= set(c.reservoirs)
    mill = _millesimes(db, tous_res)
    run_courant: str | None = None
    if any(c.portee == "run" for _, c in voulus):
        try:
            run_courant = runs.current()
        except Exception:  # noqa: BLE001
            run_courant = None
    quand = datetime.now(tz=timezone.utc).isoformat()
    # portée `projet` (0-bis) : pas de réservoir, pas de run — le tampon dit « saisi par le
    # client » (le moment réel de saisie est posé par le producteur quand il construit la Valeur).
    return {cid: Valeur(valeur=None, chiffre_id=cid, version_def=c.version_def,
                        run=(run_courant if c.portee == "run" else None),
                        reservoirs={r: mill.get(r) for r in c.reservoirs},
                        calcule_le=quand,
                        saisi_le=("(à la saisie)" if c.portee == "projet" else None)).tampon() | {
                            "libelle": c.libelle, "unite": c.unite, "definition": c.definition,
                            "moteur": c.moteur, "portee": c.portee, "type": c.type}
                        # lot 1.4 — tampon non numérique : la table (classe/géométrie), la
                        # fabrication (couche) et le domaine voyagent avec la trace
                        | ({"table": c.table} if c.table else {})
                        | ({"fabrication": c.fabrication} if c.fabrication else {})
                        | ({"domaine": list(c.domaine)} if c.domaine else {})
            for cid, c in voulus}
