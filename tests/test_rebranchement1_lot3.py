"""EXPORTS-REBRANCHEMENT-1 lot 3 — le Pré-dossier PC au circuit.

Trois verrous de non-contradiction entre pièces, joués sur la base réelle (témoin AN0347) :
  · surface et emprise bâtie des pièces = LA FICHE (mêmes robinets que l'écran/Dossier) ;
  · une seule exclusion « PPR zone rouge » servie (l'arbitrage du lot 0 couvre le pré-dossier
    via served_cascade_lines) ;
  · le zonage des pièces = zone_servie.zone_dominante (le même que le Dossier), sans liseré 0 %.
Skip propre si la base de test ne porte pas le témoin.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

IDU = "97410000AN0347"


@pytest.fixture()
def db_reelle():
    from labuse.db import session_scope
    with session_scope() as s:
        pid = s.execute(text("SELECT id FROM parcels WHERE idu = :i"), {"i": IDU}).scalar()
        if pid is None:
            pytest.skip("base sans le témoin AN0347 — vérifié sur la base réelle")
        yield s


def test_dims_du_pre_dossier_viennent_de_la_fiche(db_reelle):
    from labuse.api.pre_dossier import _terrain_dims
    fiche = {"surface_m2": 4501.4, "le_bien": {"emprise_batie_m2": 337}}
    dims = _terrain_dims(db_reelle, IDU, fiche)
    assert dims["surface_m2"] == 4501          # la fiche, pas un ST_Area recalculé
    assert dims["emprise_batie_m2"] == 337     # le_bien (BD TOPO), le robinet de l'écran
    # sans fiche : repli SQL historique, jamais un crash
    assert _terrain_dims(db_reelle, IDU)["surface_m2"] is not None


def test_une_seule_exclusion_rouge_servie(db_reelle):
    from labuse.api.served_cascade import served_cascade_lines
    lignes = served_cascade_lines(db_reelle, IDU)
    rouges = [l for l in lignes if l["result"] == "HARD_EXCLUDE"
              and "PPR zone rouge" in (l["detail"] or "")]
    assert len(rouges) <= 1, f"exclusions rouges servies en double : {[r['detail'] for r in rouges]}"


def test_zonage_du_pre_dossier_est_zone_servie(db_reelle):
    from labuse.faisabilite.zone_servie import zone_dominante
    from labuse.flash.data import _identite
    pid = db_reelle.execute(text("SELECT id FROM parcels WHERE idu = :i"), {"i": IDU}).scalar()
    zs = zone_dominante(db_reelle, pid)
    ident = _identite(db_reelle, IDU, {"spatial_layers", "parcels"})
    zones = ident.get("zones") or []
    assert zones, "le pré-dossier doit servir un zonage"
    # la première ligne du tableau EST la dominante de zone_servie — plus de « Nerl » d'un côté
    # et « N » de l'autre ; et aucun liseré arrondi à 0 % (seuil 2 %, dominante gardée).
    assert zones[0]["libelle"] == zs.zone
    assert all(z["pct"] >= 1 for z in zones[1:]), f"liseré < 1 % servi : {zones}"
