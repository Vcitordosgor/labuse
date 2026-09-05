"""CIRCUIT-1 lot 2 — les rebranchements : chaque fuite corrigée reçoit LE test qui l'aurait
attrapée.

  · 2.1 — la part de zonage est la part de SURFACE partout (moteur unique
    registre/moteurs/zonage.py) ; le compte de parcelles reste un NOMBRE de filtre
    (« parcelles en zone … »), jamais une part. Témoin réel (fuites_mesurees.csv 05/09) :
    Saint-Paul A 35,8 % / N 47,2 % en surface là où les parts de parcelles disaient 17,8 / 6,8.
  · 2.2 — score_e lit le NEUF LIVE (neuf_vefa_commune), plus jamais le précalcul divergent.
  · 2.3 — division d'or : aucune ligne d'un run mort servie ; « non recalculée pour ce run ».
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from labuse.registre.moteurs import zonage as mz

pytestmark = pytest.mark.db

_WKT_GRAND = "POLYGON((55.30 -21.0,55.309 -21.0,55.309 -21.009,55.30 -21.009,55.30 -21.0))"
_WKT_PETIT = "POLYGON((55.32 -21.0,55.3209 -21.0,55.3209 -21.0009,55.32 -21.0009,55.32 -21.0))"


def _parcelle(s, idu, commune, surface, wkt):
    return s.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, centroid, bbox) VALUES "
        "(:i,:c,'ZZ','1', ST_GeomFromText(:w,4326), ST_Transform(ST_GeomFromText(:w,4326),2975), :su, "
        " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326))) RETURNING id"),
        {"i": idu, "c": commune, "w": wkt, "su": surface}).scalar()


def test_21_part_zonage_est_la_surface_pas_le_compte(db_session):
    """LE test qui aurait attrapé la fuite du 05/09 : 3 petites parcelles U (300 m²) contre
    1 grande N (90 000 m²) — en COMPTE U domine (75 %), en SURFACE N domine. La part servie
    est celle de la SURFACE."""
    s = db_session
    com = f"TestZonage-{uuid.uuid4().hex[:6]}"
    for i in range(3):
        idu = f"97497000AA000{i}"
        _parcelle(s, idu, com, 100, _WKT_PETIT)
        s.execute(text("INSERT INTO parcel_zone_plu (idu, zone_fam, zone_filtre) VALUES (:i,'U','U')"),
                  {"i": idu})
    idu_n = "97497000AN0001"
    _parcelle(s, idu_n, com, 90000, _WKT_GRAND)
    s.execute(text("INSERT INTO parcel_zone_plu (idu, zone_fam, zone_filtre) VALUES (:i,'N','N')"),
              {"i": idu_n})

    parts = mz.parts_zonage_surface(s, com)
    assert parts["base"] == "surface"
    assert parts["familles"]["N"]["pct"] > 99.0, "la surface domine (90 000 vs 300 m²)"
    assert parts["familles"]["U"]["pct"] < 1.0
    # le COMPTE, lui, dit l'inverse — c'est un NOMBRE de filtre, jamais une part
    assert parts["familles"]["U"]["n"] == 3 and parts["familles"]["N"]["n"] == 1
    somme = sum(parts["familles"][f]["pct"] for f in ("U", "AU", "A", "N"))
    assert abs(somme - 100.0) < 0.3, "les parts de surface somment à 100 %"


def test_21_fiche_commune_sert_le_moteur(db_session):
    """`_foncier_commune` (fiche commune, carte « Zonage ») demande au moteur — même objet."""
    from labuse.api.app import _foncier_commune
    s = db_session
    com = f"TestZonage-{uuid.uuid4().hex[:6]}"
    idu = "97496000AB0001"
    _parcelle(s, idu, com, 5000, _WKT_GRAND)
    s.execute(text("INSERT INTO parcel_zone_plu (idu, zone_fam, zone_filtre) VALUES (:i,'A','A')"),
              {"i": idu})
    d = _foncier_commune(s, com)
    assert d["repartition_zonage"] == mz.parts_zonage_surface(s, com)
    assert d["repartition_zonage"]["base"] == "surface"


def test_21_filtre_zones_est_un_compte_sans_part(db_session):
    """/zonage/zones (sélecteur de filtres) sert des COMPTES par zone — aucune clé « part »/pct."""
    d = mz.parcelles_par_zone(db_session, None)
    assert set(d) == {"portee", "communes", "familles"}
    for fam in d["familles"]:
        assert set(fam) == {"fam", "n", "zones"}, "un nombre, jamais une part"


def test_22_score_e_ne_lit_plus_le_precalcul():
    """Garde 2.2 : le SQL de score_e ne lit plus dvf_prix_sortie_neuf (précalcul divergent —
    4 730 vs 5 003 €/m² à Saint-Paul, RETOURS-11F) ; le neuf est passé en paramètre LIVE."""
    from labuse.ingestion import score_e
    assert "dvf_prix_sortie_neuf" not in score_e._SELECT_RAW
    assert ":neuf_live" in score_e._SELECT_RAW, "le neuf vient du moteur live, en paramètre"


def test_23_division_run_mort_jamais_servie(db_session):
    """LE test 2.3 : un candidat q_v10_m129 (run mort) n'est JAMAIS servi — la fiche dit
    « divisibilité non recalculée pour ce run »."""
    from labuse.api.app import _division_fiche
    s = db_session
    idu = "97495000AC0001"
    _parcelle(s, idu, "TestDiv", 800, _WKT_PETIT)
    s.execute(text(
        "INSERT INTO division_or_candidates (idu, run_label, residuel_m2, type_division) "
        "VALUES (:i, 'q_v10_m129', 400, 'libre')"), {"i": idu})
    d = _division_fiche(s, idu, 800.0)
    assert d is not None and d.get("non_recalcule") is True
    assert d["lot_m2"] is None, "jamais la valeur du run mort"
    assert "non recalculée pour ce run" in d["ligne"]


def test_23_division_run_courant_servie(db_session, monkeypatch):
    """Un candidat DU run servi est rendu normalement (le scope ne casse pas le cas nominal)."""
    from labuse import runs
    from labuse.api.app import _division_fiche
    monkeypatch.setenv("LABUSE_SERVED_RUN", "q_test_circuit1")
    s = db_session
    idu = "97495000AD0002"
    _parcelle(s, idu, "TestDiv", 800, _WKT_PETIT)
    s.execute(text(
        "INSERT INTO division_or_candidates (idu, run_label, residuel_m2, type_division) "
        "VALUES (:i, 'q_test_circuit1', 400, 'libre')"), {"i": idu})
    d = _division_fiche(s, idu, 800.0)
    assert d is not None and not d.get("non_recalcule")
    assert d["lot_m2"] == 400


# ───────────────────────── 2.6 — garde Copilote voie B (adversarial) ─────────────────────────

def test_26_garde_generale_10_pieges_0_chiffre_invente():
    """10 sorties PIÈGES (ce qu'un modèle pourrait produire) → après la garde, AUCUN chiffre
    précis à unité de donnée ne survit hors fourchette ; les fourchettes 4bis survivent."""
    from labuse.copilote_v2.answering import garde_generale_sans_chiffre, _CHIFFRE_DATA, _FOURCHETTE
    pieges = [
        "Le prix médian à Saint-Paul est de 5003 €/m².",
        "Cette commune compte 51129 parcelles.",
        "Le taux LLS de Saint-Denis est 23,4 %.",
        "Un terrain en zone U vaut 250 €/m² à La Réunion.",
        "La SDP résiduelle moyenne est 1200 m².",
        "Il y a 431663 parcelles dans la base.",
        "Le déficit SRU est de 5,4 points, soit 890 logements.",
        "Le marché a progressé : 4500 € du m² au Port.",
        "La charge foncière type est 180 €.",
        "Saint-Pierre a autorisé 320 logements l'an dernier.",
    ]
    for p in pieges:
        garde, n = garde_generale_sans_chiffre(p)
        assert n >= 1, f"piège non attrapé : {p}"
        restes = [m.group(0) for m in _CHIFFRE_DATA.finditer(garde)
                  if not _FOURCHETTE.search(garde)]
        assert not restes, f"chiffre survivant : {restes} dans {garde!r}"
        assert "outils du Copilote" in garde, "le renvoi aux outils remplace le chiffre"
    # les FOURCHETTES honnêtes (règle 4bis) survivent
    ok = "Une étude de sol coûte en général entre 1 500 et 3 000 €, selon le terrain."
    garde, n = garde_generale_sans_chiffre(ok)
    assert n == 0 and garde == ok
    ok2 = "Comptez de l'ordre de 800 € pour un bornage simple."
    garde2, n2 = garde_generale_sans_chiffre(ok2)
    assert n2 == 0 and garde2 == ok2
