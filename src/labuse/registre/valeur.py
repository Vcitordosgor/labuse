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
}


@dataclass(frozen=True)
class Valeur:
    valeur: Any
    chiffre_id: str
    version_def: str
    run: str | None                       # run servi si portée run, sinon None
    reservoirs: dict = field(default_factory=dict)   # {reservoir_id: millésime servi}
    calcule_le: str = ""

    def tampon(self) -> dict:
        return {"chiffre_id": self.chiffre_id, "version_def": self.version_def,
                "run": self.run, "reservoirs": self.reservoirs, "calcule_le": self.calcule_le}


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
    return {cid: Valeur(valeur=None, chiffre_id=cid, version_def=c.version_def,
                        run=(run_courant if c.portee == "run" else None),
                        reservoirs={r: mill.get(r) for r in c.reservoirs},
                        calcule_le=quand).tampon() | {
                            "libelle": c.libelle, "unite": c.unite, "definition": c.definition,
                            "moteur": c.moteur, "portee": c.portee}
            for cid, c in voulus}
