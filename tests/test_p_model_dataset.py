"""Cas synthétiques ANTI-LEAKAGE du dataset builder P (mandat M3, lot 1).

Chaque test matérialise un micro-monde (parcelles + DVF + Sitadel) dans la base de
test, exécute le builder complet, puis vérifie la frontière temporelle : ce qui date
de l'année Y appartient au LABEL de Y et ne doit JAMAIS apparaître dans les features
de Y ; ce qui est antérieur au 01/01/Y appartient aux features et jamais au label.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.scoring.p_model import sql as psql

pytestmark = pytest.mark.db

C = "97411"          # commune
SA = C + "000AB"     # secteur A
SB = C + "000AC"     # secteur B
P1, P2, P3, P4 = SA + "0001", SA + "0002", SA + "0003", SA + "0004"
P5 = SB + "0001"
P6 = SB + "0002"


def _seed(session):
    """Micro-monde : 6 parcelles, 2 secteurs, mutations 2021-2023, permis 2022-2023."""
    for idu in (P1, P2, P3, P4, P5, P6):
        session.execute(text("""
            INSERT INTO parcels (idu, commune, surface_m2, geom)
            VALUES (:i, 'Saint-Paul', 500,
                    ST_SetSRID(ST_GeomFromText('POLYGON((55.27 -21.01, 55.271 -21.01,
                    55.271 -21.009, 55.27 -21.009, 55.27 -21.01))'), 4326))"""),
            {"i": idu})

    rows = [
        # M1 : Vente 2023 sur P1, MULTI-LOTS (2 lignes, même mutation) → label 2023, dédup
        ("M1", "2023-06-15", "Vente", 200000, P1, 120, 500),
        ("M1", "2023-06-15", "Vente", 200000, P1, 80, 500),
        # M2 : Vente 2022 sur P2 → feature (rotation 2023), label 2022, PAS label 2023
        ("M2", "2022-05-01", "Vente", 150000, P2, 100, 500),
        # M3 : Échange 2023 sur P3 → HORS périmètre L2 (ni label ni rotation)
        ("M3", "2023-03-01", "Echange", 90000, P3, 0, 500),
        # M4 : Vente 2021 MULTI-PARCELLES (P1 + P2) → compte UNE fois dans la rotation
        ("M4", "2021-08-01", "Vente", 300000, P1, 0, 500),
        ("M4", "2021-08-01", "Vente", 300000, P2, 0, 600),
        # M5 : Vente terrain à bâtir 2023 sur P5 (nu) → label 2023 (périmètre L2)
        ("M5", "2023-04-10", "Vente terrain à bâtir", 80000, P5, 0, 700),
        # M6 : VEFA 2023 sur P6 → hors périmètre L2
        ("M6", "2023-09-01", "Vente en l'état futur d'achèvement", 250000, P6, 60, 0),
    ]
    for mid, d, nat, val, idu, sb, st_ in rows:
        session.execute(text("""
            INSERT INTO dvf_mutations_parcelle
                (id_mutation, date_mutation, nature_mutation, valeur_fonciere,
                 code_commune, id_parcelle, surface_reelle_bati, surface_terrain, millesime)
            VALUES (:m, :d, :n, :v, :c, :i, :sb, :st, :y)"""),
            {"m": mid, "d": d, "n": nat, "v": val, "c": C, "i": idu,
             "sb": sb, "st": st_, "y": int(d[:4])})

    permits = [
        # PC sur P1 autorisé 2022-06-01 → visible as-of 2023 ('<2a'), compte permis_24m 2023
        ("PC-1", "PC", "2022-06-01", P1),
        # PC sur P4 autorisé 2023-02-01 → INVISIBLE as-of 01/01/2023 (anti-leakage),
        # visible as-of 2024
        ("PC-2", "PC", "2023-02-01", P4),
    ]
    for pid, typ, d, idu in permits:
        session.execute(text("""
            INSERT INTO sitadel_permits (permit_id, type, date, idu_codes, commune, raw)
            VALUES (:p, :t, :d, :j, 'Saint-Paul', '{}')"""),
            {"p": pid, "t": typ, "d": d, "j": f'["{idu}"]'})
    session.flush()


@pytest.fixture
def dataset(db_session):
    _seed(db_session)
    psql.build_all(db_session, years=(2022, 2023, 2024))
    def row(idu, annee):
        r = db_session.execute(text(
            "SELECT * FROM p_model_dataset WHERE idu = :i AND annee = :a"),
            {"i": idu, "a": annee}).mappings().one()
        return r
    return row


def test_label_l2_dans_annee(dataset):
    assert dataset(P1, 2023)["label"] == 1          # Vente 2023
    assert dataset(P5, 2023)["label"] == 1          # Vente terrain à bâtir 2023
    assert dataset(P2, 2022)["label"] == 1          # Vente 2022


def test_label_exclut_hors_l2_et_hors_annee(dataset):
    assert dataset(P3, 2023)["label"] == 0          # Échange : hors L2
    assert dataset(P6, 2023)["label"] == 0          # VEFA : hors L2
    assert dataset(P2, 2023)["label"] == 0          # Vente 2022 ≠ label 2023
    assert dataset(P1, 2022)["label"] == 0          # Vente 2023 ≠ label 2022


def test_label_null_apres_dernier_millesime(dataset):
    # dernier millésime DVF synthétique = 2023 → 2024 : PAS de label observable
    assert dataset(P1, 2024)["label"] is None


def test_rotation_stricte_avant_asof_et_dedup(dataset):
    # secteur A, Y=2023, fenêtre [2021-01-01, 2023-01-01) :
    #  M4 (2021, multi-parcelles → UNE fois) + M2 (2022) = 2 mutations ;
    #  M1 (2023) est STRICTEMENT exclue des features 2023 (elle est le label).
    r = dataset(P1, 2023)
    assert r["n_mut_nu_36m"] + r["n_mut_bati_36m"] == 2
    # M4 : aucune ligne bâtie → nu ; M2 : 100 m² bâtis → bâti
    assert r["n_mut_nu_36m"] == 1 and r["n_mut_bati_36m"] == 1


def test_rotation_fenetre_glissante_2024(dataset):
    # Y=2024, fenêtre [2021, 2024) : M4 + M2 + M1 + M5(secteur B exclu du secteur A) = 3
    r = dataset(P1, 2024)
    assert r["n_mut_nu_36m"] + r["n_mut_bati_36m"] == 3


def test_window_coverage_clampee(dataset):
    # Y=2022 : 12 mois disponibles / 36 ; Y=2024 : 36/36
    assert abs(float(dataset(P1, 2022)["window_coverage"]) - 12 / 36) < 0.02
    assert float(dataset(P1, 2024)["window_coverage"]) > 0.98


def test_tenure_bins_asof(dataset):
    assert dataset(P2, 2023)["tenure_bin"] == "<1"       # M2 mai 2022, as-of 01/01/2023
    assert dataset(P2, 2024)["tenure_bin"] == "1-2"      # même mutation, un an plus tard
    assert dataset(P4, 2023)["tenure_bin"] == "inconnu"  # jamais vu depuis 2021
    # la mutation de l'année Y ne nourrit PAS la tenure de Y
    assert dataset(P1, 2023)["tenure_bin"] == "1-2"      # M4 2021, pas M1 2023


def test_permis_asof_anti_leakage(dataset):
    assert dataset(P4, 2023)["permis_bin"] == "jamais"   # PC-2 (fév. 2023) invisible au 01/01/2023
    assert dataset(P4, 2024)["permis_bin"] == "<2a"      # visible au 01/01/2024
    assert dataset(P1, 2023)["permis_bin"] == "<2a"      # PC-1 (juin 2022) visible


def test_permis_secteur_24m(dataset):
    # secteur A, Y=2023, fenêtre [2021, 2023) clampée : PC-1 seul (PC-2 est de 2023)
    r = dataset(P1, 2023)
    assert float(r["permis_24m_norm"]) == pytest.approx(1 / 4)  # 1 permis / 4 parcelles
    # Y=2024, fenêtre [2022, 2024) : PC-1 (2022-06) + PC-2 (2023-02) = 2
    assert float(dataset(P1, 2024)["permis_24m_norm"]) == pytest.approx(2 / 4)


def test_aucun_na_silencieux_sur_bins(dataset):
    for idu in (P1, P2, P3, P4, P5, P6):
        r = dataset(idu, 2023)
        assert r["tenure_bin"] in {"<1", "1-2", "2-3", "3+", "inconnu"}
        assert r["permis_bin"] in {"<2a", "2-5a", "5-10a", "10a+", "jamais"}
        assert r["zone_plu"] is not None


def test_frame_complet_une_ligne_par_parcelle_annee(dataset, db_session):
    n = db_session.execute(text("SELECT count(*) FROM p_model_dataset")).scalar()
    assert n == 6 * 3  # 6 parcelles × 3 années demandées
