"""ZONE-DONNÉES · LOT 1 — ingestion SIRENE établissements (géo INSEE × StockEtablissement, DuckDB).

On gèle : jointure sur SIRET ; 974 ACTIFS seuls ; masquage de diffusion (non-'O' → nom/adresse NULL,
NAF conservé) ; NAF normalisé sans point ; position = lon/lat GPS direct ; tranche/qualité/IRIS conservés.
Parquets de test créés localement (DuckDB), pas de réseau. Données purgées.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.db import session_scope
from labuse.ingestion import seed_sources
from labuse.ingestion.sirene_etablissements import build_sirene_etablissements, ensure_tables

pytestmark = pytest.mark.db


def _fixtures(tmp_path):
    import duckdb
    con = duckdb.connect()
    stock = tmp_path / "stock.parquet"
    geo = tmp_path / "geo.parquet"
    # 4 établissements : A diffusible 974 actif · B non-diffusible ('P') 974 actif · C fermé · D hors-974
    con.execute(f"""COPY (SELECT * FROM (VALUES
      ('90000000000011','10.71C','O','BOULANGE A','', '97415','01','12','RUE','DE LA GARE','A'),
      ('90000000000022','10.71C','P','MONSIEUR X','', '97415','NN','5','RUE','DES FLEURS','A'),
      ('90000000000033','10.71C','O','FERMEE','',      '97415','01','1','RUE','X','F'),
      ('90000000000044','10.71C','O','HORS 974','',    '75056','01','1','RUE','Y','A')
     ) AS t(siret, activitePrincipaleEtablissement, statutDiffusionEtablissement,
            denominationUsuelleEtablissement, enseigne1Etablissement, codeCommuneEtablissement,
            trancheEffectifsEtablissement, numeroVoieEtablissement, typeVoieEtablissement,
            libelleVoieEtablissement, etatAdministratifEtablissement)) TO '{stock}' (FORMAT parquet)""")
    con.execute(f"""COPY (SELECT * FROM (VALUES
      ('90000000000011', 55.2707, -21.0096, '11', '0101', '97415', 'HZ'),
      ('90000000000022', 55.2710, -21.0090, '11', '0101', '97415', 'HZ'),
      ('90000000000033', 55.2700, -21.0100, '11', '0101', '97415', 'HZ'),
      ('90000000000044', 2.3500,  48.8500,  '11', '0101', '75056', 'HZ')
     ) AS t(siret, x_longitude, y_latitude, qualite_xy, plg_iris, plg_code_commune, plg_qp24))
     TO '{geo}' (FORMAT parquet)""")
    return f"file://{geo}", f"file://{stock}"


def test_lot1_sirene_jointure_diffusion_position(tmp_path):
    geo_url, stock_url = _fixtures(tmp_path)
    with session_scope() as s:
        seed_sources.seed(s)
        ensure_tables(s)
        s.execute(text("DELETE FROM sirene_etablissements WHERE siret LIKE '9000000000%'"))
        r = build_sirene_etablissements(s, geo_url=geo_url, stock_url=stock_url)
        rows = {x["siret"]: dict(x) for x in s.execute(text(
            "SELECT siret, naf, denomination, adresse, diffusible, tranche_effectif, qualite_xy, iris, "
            " round(ST_X(geom)::numeric,4) lon, round(ST_Y(geom)::numeric,4) lat "
            "FROM sirene_etablissements WHERE siret LIKE '9000000000%'")).mappings()}
        s.execute(text("DELETE FROM sirene_etablissements WHERE siret LIKE '9000000000%'"))
    # 974 ACTIFS seuls : le fermé (F) et le hors-974 sont écartés
    assert set(rows) == {"90000000000011", "90000000000022"}
    a = rows["90000000000011"]
    assert a["naf"] == "1071C", "NAF normalisé sans point (10.71C → 1071C)"
    assert a["denomination"] == "BOULANGE A" and a["diffusible"] is True
    assert a["tranche_effectif"] == "01" and a["qualite_xy"] == "11"
    assert a["iris"] == "974150101", "IRIS = plg_code_commune + plg_iris"
    assert float(a["lon"]) == 55.2707 and float(a["lat"]) == -21.0096, "position = lon/lat GPS direct"
    # diffusion partielle ('P') : nom ET adresse NULL, NAF conservé
    b = rows["90000000000022"]
    assert b["diffusible"] is False
    assert b["denomination"] is None and b["adresse"] is None, "non diffusible : ni nom ni adresse"
    assert b["naf"] == "1071C", "le NAF reste (l'établissement compte dans la zone)"
    assert r["n"] == 2 and r["n_diffusion_partielle"] == 1


def test_lot2_emplois_zone_fourchette_et_sans_tranche():
    """LOT 2 — postes salariés = FOURCHETTE (somme des bornes de tranches), NN comptés à part."""
    from labuse import zone as Z
    _LON, _LAT = 55.65, -20.96
    zone = {"type": "Polygon", "coordinates": [[[_LON - 0.02, _LAT - 0.02], [_LON + 0.02, _LAT - 0.02],
            [_LON + 0.02, _LAT + 0.02], [_LON - 0.02, _LAT + 0.02], [_LON - 0.02, _LAT - 0.02]]]}
    with session_scope() as s:
        from labuse.ingestion.sirene_etablissements import ensure_tables as se_ens
        se_ens(s)
        s.execute(text("DELETE FROM sirene_etablissements WHERE siret LIKE '9100000000%'"))
        for siret, tr in [("91000000000011", "01"), ("91000000000022", "12"), ("91000000000033", "NN")]:
            s.execute(text(
                "INSERT INTO sirene_etablissements (siret, siren, naf, actif, diffusible, tranche_effectif, geom) "
                "VALUES (:s, :si, '4711D', true, true, :tr, ST_SetSRID(ST_MakePoint(:lon,:lat),4326))"),
                {"s": siret, "si": siret[:9], "tr": tr, "lon": _LON, "lat": _LAT})
        e = Z.emplois_zone(s, zone)
        s.execute(text("DELETE FROM sirene_etablissements WHERE siret LIKE '9100000000%'"))
    # 01 = 1–2, 12 = 20–49 → min 1+20=21, max 2+49=51 ; NN compté à part (1)
    assert e["postes_min"] == 21 and e["postes_max"] == 51
    assert e["n_sans_tranche"] == 1 and e["n_avec_tranche"] == 2
    assert e["libelle"] == "postes salariés déclarés dans la zone"


def test_lot3_filosofi_imputation_pilotee_par_i_est_200():
    """LOT 3 — le « valeur approchée sur N/M » est piloté par i_est_200 (2 imputés / 3 → majorité)."""
    from labuse import zone as Z
    _LON, _LAT = 55.65, -20.96
    zone = {"type": "Polygon", "coordinates": [[[_LON - 0.02, _LAT - 0.02], [_LON + 0.02, _LAT - 0.02],
            [_LON + 0.02, _LAT + 0.02], [_LON - 0.02, _LAT + 0.02], [_LON - 0.02, _LAT - 0.02]]]}
    with session_scope() as s:
        s.execute(text("ALTER TABLE filosofi_carreaux_200m ADD COLUMN IF NOT EXISTS i_est_200 varchar(1)"))
        for i, (iest, ind) in enumerate([("1", 100.0), ("1", 80.0), ("0", 60.0)]):
            s.execute(text(
                "INSERT INTO filosofi_carreaux_200m (geom, ind, men, men_pauv, men_prop, ind_snv, i_est_200) "
                "VALUES (ST_Transform(ST_SetSRID(ST_MakePoint(:lon,:lat),4326),2975), :ind, :men, 1, 5, :snv, :ie)"),
                {"lon": _LON + i * 0.0003, "lat": _LAT, "ind": ind, "men": ind / 2, "snv": ind * 20000, "ie": iest})
        pop = Z.population_zone(s, zone)
        s.execute(text("DELETE FROM filosofi_carreaux_200m WHERE men_prop = 5 AND ind IN (100,80,60)"))
    assert pop["revenu_impute_n"] == 2 and pop["revenu_carreaux_n"] == 3
    assert pop["revenu_majorite_imputee"] is True, "2/3 imputés → majorité, « valeur approchée »"


def test_lot8_zone_demain_logements_et_au():
    """LOT 8 — logements autorisés 36 mois (Sitadel raw.nb_lgt) + zones AU intersectantes, signal daté."""
    from labuse import zone as Z
    _LON, _LAT = 55.65, -20.96
    zone = {"type": "Polygon", "coordinates": [[[_LON - 0.02, _LAT - 0.02], [_LON + 0.02, _LAT - 0.02],
            [_LON + 0.02, _LAT + 0.02], [_LON - 0.02, _LAT + 0.02], [_LON - 0.02, _LAT - 0.02]]]}
    wkt_au = f"POLYGON(({_LON-0.001} {_LAT-0.001},{_LON+0.001} {_LAT-0.001},{_LON+0.001} {_LAT+0.001},{_LON-0.001} {_LAT+0.001},{_LON-0.001} {_LAT-0.001}))"
    with session_scope() as s:
        s.execute(text(
            "INSERT INTO sitadel_permits (permit_id, type, date, commune, geom, raw) VALUES "
            "('ZDTEST01','PC', now()-interval '6 months','Saint-André', "
            " ST_SetSRID(ST_MakePoint(:lon,:lat),4326), '{\"nb_lgt\": 12}'::jsonb)"),
            {"lon": _LON, "lat": _LAT})
        s.execute(text(
            "INSERT INTO spatial_layers (kind, subtype, name, geom) VALUES "
            "('plu_gpu_zone','AUc','AU test', ST_GeomFromText(:w,4326))"), {"w": wkt_au})
        d = Z.zone_demain(s, zone)
        s.execute(text("DELETE FROM sitadel_permits WHERE permit_id='ZDTEST01'"))
        s.execute(text("DELETE FROM spatial_layers WHERE name='AU test'"))
    assert d["logements_autorises_36m"] == 12 and d["permis_36m"] == 1
    assert d["au_zones_n"] == 1 and d["au_zones_ha"] >= 0


def test_lot7_contraintes_plu_tableau_zones():
    """LOT 7 — les zones PLU recouvertes (tableau ZONE / PART / DOCUMENT), part de surface."""
    from labuse import zone as Z
    _LON, _LAT = 55.65, -20.96
    zone = {"type": "Polygon", "coordinates": [[[_LON - 0.01, _LAT - 0.01], [_LON + 0.01, _LAT - 0.01],
            [_LON + 0.01, _LAT + 0.01], [_LON - 0.01, _LAT + 0.01], [_LON - 0.01, _LAT - 0.01]]]}
    # une zone PLU 'UA' qui couvre la moitié EST de la zone d'étude
    wkt = f"POLYGON(({_LON} {_LAT-0.01},{_LON+0.01} {_LAT-0.01},{_LON+0.01} {_LAT+0.01},{_LON} {_LAT+0.01},{_LON} {_LAT-0.01}))"
    with session_scope() as s:
        s.execute(text(
            "INSERT INTO spatial_layers (kind, subtype, name, commune, geom, attrs) VALUES "
            "('plu_gpu_zone','UA','PLU test','Saint-André', ST_GeomFromText(:w,4326), '{\"idurba\":\"97409_PLU\"}'::jsonb)"),
            {"w": wkt})
        c = Z.contraintes_plu(s, zone)
        s.execute(text("DELETE FROM spatial_layers WHERE name='PLU test'"))
    assert len(c["zones"]) == 1
    zz = c["zones"][0]
    assert zz["zone"] == "UA" and zz["document"] == "97409_PLU"
    assert 40 <= zz["part_pct"] <= 60, "la zone UA couvre ~50 % de l'emprise"
    assert "CDAC" in c["cdac_vigilance"]
