"""TESTS-1 lot 2 — les EXEMPLES TÉMOINS réels des 4 fiches de règle nouvelles (garde
circuit4_lot4 : un verdict « choix_assume » porte un témoin numérique vérifié à la main).
Chaque test seed des petites données aux valeurs choisies À LA MAIN et vérifie que le code
de PRODUCTION rend exactement l'arithmétique de la fiche."""
from __future__ import annotations

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.db

_WKT = "POLYGON((55.47 -20.93,55.471 -20.93,55.471 -20.931,55.47 -20.931,55.47 -20.93))"
_WKT2 = "POLYGON((55.48 -20.94,55.481 -20.94,55.481 -20.941,55.48 -20.941,55.48 -20.94))"


def _seed_parcelle(s, idu, wkt=_WKT, commune="Saint-Paul"):
    return s.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, centroid, bbox) VALUES "
        "(:i, :c, 'ZZ','1', ST_GeomFromText(:w,4326), ST_Transform(ST_GeomFromText(:w,4326),2975), 10000, "
        " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326))) RETURNING id"),
        {"i": idu, "w": wkt, "c": commune}).scalar()


def _seed_couche_batiment(s):
    # le_bien_block s'OMET (None) sans couche bâtiments (layer_available) : un témoin bâti minimal.
    if not s.execute(text("SELECT EXISTS(SELECT 1 FROM spatial_layers WHERE kind='batiment')")).scalar():
        s.execute(text(
            "INSERT INTO spatial_layers (kind, name, geom, geom_2975) VALUES ('batiment', 'témoin', "
            "ST_GeomFromText(:w,4326), ST_Transform(ST_GeomFromText(:w,4326),2975))"),
            {"w": "POLYGON((55.469 -20.929,55.4691 -20.929,55.4691 -20.9291,55.469 -20.9291,55.469 -20.929))"})


def test_zan_ocsge_commune_a_la_main(db_session):
    """Témoin fiche zan_evolution_commune : 12 000 + 8 000 m² artificialisés → 2,0 ha ;
    5 000 m² renaturés → 0,5 ha ; part = 100 × Σ artif ÷ Σ aire cadastrale (formule de la fiche)."""
    from labuse.ingestion.ocsge import ensure_tables
    from labuse.registre.moteurs.commune import zan_ocsge_commune
    s = db_session
    ensure_tables(s)
    _seed_parcelle(s, "97415000ZA0001")
    _seed_parcelle(s, "97415000ZA0002", _WKT2)
    s.execute(text(
        "INSERT INTO parcel_ocsge (idu, part_artif_pct, cs_dominant, us_dominant, artif_m2,"
        " evol_artif_m2, evol_renat_m2, millesime) VALUES"
        " ('97415000ZA0001', 40.0, 'CS1.1.1.1', 'US2', 4000, 12000, 5000, '2022'),"
        " ('97415000ZA0002', 10.0, 'CS2.2.1', 'US1.1', 1000, 8000, 0, '2022')"))
    d = zan_ocsge_commune(s, "Saint-Paul")["Saint-Paul"]
    assert d["artif_ha"] == 2.0 and d["renat_ha"] == 0.5          # (12000+8000)/10⁴ · 5000/10⁴
    aire = s.execute(text(
        "SELECT sum(ST_Area(geom_2975)) FROM parcels WHERE idu IN ('97415000ZA0001','97415000ZA0002')"
    )).scalar()
    assert d["part_artif_pct"] == round(100.0 * 5000 / float(aire), 1)   # Σ artif_m2 = 4000+1000
    assert "assiette cadastrale" in d["source"]


def test_artif_decret_matrice_a_la_main():
    """Témoin fiche part_artificialisee_pct / usage_sol_dominant : la matrice de l'étape 1 du
    décret 2023-1096, cas choisis à la main (bâti toujours artif sauf l'exception serre US1.3 ;
    CS2.2 selon l'usage ; le naturel jamais)."""
    from labuse.ingestion.ocsge import artif_decret
    assert artif_decret("CS1.1.1.1", "US2") is True          # bâti × production secondaire
    assert artif_decret("CS1.1.2.1", "US1.3") is False       # serre agricole : l'exception écrite
    assert artif_decret("CS1.1.2.1", "US2") is True          # même couverture, autre usage → artif
    assert artif_decret("CS2.2.1", "US2") is True            # formation herbacée × usage productif
    assert artif_decret("CS2.2.1", "US1.1") is False         # herbacé agricole → non artificialisé
    assert artif_decret("CS2.2.1", "US4.1.1") is True        # réseau (préfixe US4)
    assert artif_decret("CS2.1.1.1", "US2") is False         # forêt : jamais artif à l'étape 1
    assert artif_decret(None, None) is False                 # l'inconnu ne s'invente pas artif


def test_ban_plus_comptes_a_la_main(db_session):
    """Témoin fiche ban_plus_adresses_bati : 3 liens, 2 adresses distinctes, 2 bâtiments
    distincts — comptés par le code de production (le_bien_block), zéro → None."""
    from labuse.bati import le_bien_block
    from labuse.ingestion import ban_plus
    s = db_session
    for stmt in [x for x in ban_plus.DDL.split(";") if x.strip()]:
        s.execute(text(stmt))
    idu = "97415000BA0001"
    _seed_parcelle(s, idu)
    _seed_couche_batiment(s)
    s.execute(text(
        "INSERT INTO ban_plus_liens (id_adr, id_bat, idu) VALUES"
        " ('ADR1','BAT1',:i), ('ADR1','BAT2',:i), ('ADR2','BAT1',:i)"), {"i": idu})
    bloc = le_bien_block(s, idu)
    ab = (bloc or {}).get("adresses_bati")
    assert ab and ab["liens"] == 3 and ab["adresses"] == 2 and ab["batiments"] == 2
    assert "BAN PLUS" in ab["source"]
    # zéro lien → None (« aucun lien publié » et « parcelle sans adresse » indistinguables)
    idu2 = "97415000BA0002"
    _seed_parcelle(s, idu2, _WKT2)
    bloc2 = le_bien_block(s, idu2)
    assert (bloc2 or {}).get("adresses_bati") is None


def test_rnb_actifs_ordre_recouvrement_a_la_main(db_session):
    """Témoin fiche rnb_batiments_liste : seuls les ACTIFS sortent, triés du plus grand
    recouvrement au plus petit, chacun avec son lien officiel."""
    from labuse.bati import le_bien_block
    from labuse.db import sql_statements
    from labuse.ingestion import rnb
    s = db_session
    for stmt in sql_statements(rnb.DDL):
        s.execute(text(stmt))
    idu = "97415000RN0001"
    _seed_parcelle(s, idu)
    _seed_couche_batiment(s)
    # b_grand couvre ~la moitié ouest, b_petit un petit coin, b_demoli (inactif) couvre tout
    moitie = "POLYGON((55.47 -20.93,55.4705 -20.93,55.4705 -20.931,55.47 -20.931,55.47 -20.93))"
    coin = "POLYGON((55.4709 -20.9309,55.471 -20.9309,55.471 -20.931,55.4709 -20.931,55.4709 -20.9309))"
    for rid, wkt, actif in (("RNBGRAND1", moitie, True), ("RNBPETIT1", coin, True), ("RNBDEMOLI1", _WKT, False)):
        s.execute(text(
            "INSERT INTO rnb_batiments (rnb_id, statut, is_active, insee, shape, shape_2975) VALUES"
            " (:r, :st, :a, '97415', ST_GeomFromText(:w,4326), ST_Transform(ST_GeomFromText(:w,4326),2975))"),
            {"r": rid, "st": "constructed" if actif else "demolished", "a": actif, "w": wkt})
    bloc = le_bien_block(s, idu)
    ids = [b["rnb_id"] for b in (bloc or {}).get("rnb", [])]
    assert ids == ["RNBGRAND1", "RNBPETIT1"]                 # l'inactif jamais, l'ordre = recouvrement
    assert (bloc["rnb"][0]["lien"] == "https://rnb.beta.gouv.fr/batiments/RNBGRAND1")
