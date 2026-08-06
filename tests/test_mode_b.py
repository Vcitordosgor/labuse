"""M33 — MODE B (réhabilitation) : verrous du moteur `compute_mode_b`.

Verrouille : la population (2 tiers déclassés bâti, jamais une servie), le calcul (briques
mode A : coef CA, SHAB = SDP/1,15), l'héritage d'étiquette STRICT (jamais Sourcé — le
paramètre travaux est toujours Estimé), le bilan négatif DIT honnêtement (défaut vs saisi),
le clamp des bornes, la préséance prix secteur → commune étiquetée, l'ABSENT explicite.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.faisabilite.bilan import (
    MODE_B_TRAVAUX_M2_DEFAUT,
    MODE_B_TRAVAUX_M2_MAX,
    MODE_B_TRAVAUX_M2_MIN,
    compute_mode_b,
)
from labuse.scoring.score_v_constants import Q_A_RUN_LABEL

pytestmark = pytest.mark.db

_WKT = ("POLYGON((55.47 -20.90, 55.471 -20.90, 55.471 -20.901, "
        "55.47 -20.901, 55.47 -20.90))")


def _parcel(session, idu: str) -> int:
    return session.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, "
        "                     centroid, bbox) "
        "VALUES (:i, 'Testville', 'MB', '1', ST_GeomFromText(:w, 4326), "
        "        ST_Transform(ST_GeomFromText(:w, 4326), 2975), 900, "
        "        ST_Centroid(ST_GeomFromText(:w, 4326)), ST_Envelope(ST_GeomFromText(:w, 4326))) "
        "RETURNING id"), {"i": idu, "w": _WKT}).scalar()


def _seed(session):
    session.execute(text(
        "CREATE TABLE IF NOT EXISTS p_model_bati ("
        " idu varchar(14) PRIMARY KEY, emprise_bati_m2 double precision)"))
    session.execute(text(
        "CREATE TABLE IF NOT EXISTS dvf_secteur_medianes ("
        " secteur varchar(10) NOT NULL, type_bien varchar(16) NOT NULL,"
        " n_ventes integer NOT NULL, mediane_valeur integer, mediane_prix_m2 integer,"
        " fenetre text NOT NULL DEFAULT '2021-2025',"
        " computed_at timestamptz NOT NULL DEFAULT now(),"
        " PRIMARY KEY (secteur, type_bien))"))
    cas = [
        ("97499000MB0001", "declasse_bati_sature", 200.0),   # prix secteur → positif
        ("97499000MB0002", "declasse_bati_revele", 100.0),   # marché pauvre → négatif au défaut
        ("97499000MB0003", "chaude", 150.0),                 # SERVIE → hors population
        ("97499000MB0004", "declasse_bati_sature", 10.0),    # emprise < 20 → ABSENT
        ("97499100MB0005", "declasse_bati_sature", 120.0),   # pas de secteur → repli COMMUNE
    ]
    for idu, tier, emprise in cas:
        _parcel(session, idu)
        session.execute(text(
            "INSERT INTO parcel_p_score_v2 (run_id, parcelle_id, p_raw, mult_base, percentile, "
            "rang, contrib_z, contrib_d, copro, tier, model_version) "
            "VALUES (:r, :i, 0.5, 1.0, 50, 400000, 0, 0, false, :t, 'm33-test')"),
            {"r": Q_A_RUN_LABEL, "i": idu, "t": tier})
        session.execute(text(
            "INSERT INTO p_model_bati (idu, emprise_bati_m2) VALUES (:i, :e) "
            "ON CONFLICT (idu) DO UPDATE SET emprise_bati_m2 = :e"),
            {"i": idu, "e": emprise})
    session.execute(text(
        "INSERT INTO dvf_secteur_medianes (secteur, type_bien, n_ventes, mediane_prix_m2, fenetre) VALUES "
        "('97499000MB', 'maison', 8, 3000, '2021-2025'),"
        "('97499000MB', 'appartement', 4, 2600, '2021-2025'),"
        # MB0005 : secteur 97499100MB SANS ligne → repli commune 97499 (médiane des secteurs)
        "('97499200ZZ', 'maison', 5, 2400, '2021-2025') "
        "ON CONFLICT DO NOTHING"))
    session.flush()


def test_hors_population_jamais_servie(db_session):
    _seed(db_session)
    r = compute_mode_b(db_session, "97499000MB0003")
    assert r["disponible"] is False and "hors population" in r["motif"]


def test_calcul_briques_mode_a_et_etiquettes(db_session):
    _seed(db_session)
    r = compute_mode_b(db_session, "97499000MB0001")
    assert r["disponible"] is True and r["population_tier"] == "declasse_bati_sature"
    c = r["composantes"]
    # SHAB = emprise × niveaux(1, placeholder) / 1,15 — conventions mode A
    assert c["surface"]["shab_rehabilitable_m2"] == round(200 * 1.0 / 1.15)
    assert c["surface"]["niveaux_reels"] is False
    assert "Estimé" in c["surface"]["niveaux_etiquette"]
    assert c["surface"]["etiquette_emprise"] == "Sourcé"
    # prix : max(maison, appartement) du secteur, étiqueté Sourcé DVF
    assert c["prix_sortie"]["prix_m2"] == 3000 and c["prix_sortie"]["niveau"] == "secteur"
    # achat max = SHAB × prix × 0,79 − SHAB × 1500 (défaut)
    shab = 200 / 1.15
    attendu = round(shab * 3000 * 0.79 - shab * MODE_B_TRAVAUX_M2_DEFAUT)
    assert r["achat_max_eur"] == attendu and r["negatif"] is False
    # HÉRITAGE STRICT : jamais Sourcé (travaux toujours Estimé) — assumé au libellé
    assert r["etiquette"] == "Estimé"
    assert c["travaux"]["etiquette"] == "ESTIMÉ"
    assert "à ajuster selon l'état constaté" in c["travaux"]["libelle"]


def test_negatif_dit_honnetement_defaut_et_saisi(db_session):
    _seed(db_session)
    r = compute_mode_b(db_session, "97499000MB0002")   # prix 3000 secteur partagé… même secteur
    # MB0002 partage le secteur 97499000MB (prix 3000) → positif ; on force un travaux haut
    r = compute_mode_b(db_session, "97499000MB0002", travaux_m2=3000)
    assert r["negatif"] is True
    assert "3000 €/m² de travaux" in r["message_negatif"]      # message « saisi », pas « défaut »
    assert r["achat_max_eur"] <= 0                             # servi comme NÉGATIF, jamais actionnable


def test_clamp_bornes_travaux(db_session):
    _seed(db_session)
    r = compute_mode_b(db_session, "97499000MB0001", travaux_m2=99999)
    assert r["composantes"]["travaux"]["hypothese_m2"] == round(MODE_B_TRAVAUX_M2_MAX)
    r = compute_mode_b(db_session, "97499000MB0001", travaux_m2=1)
    assert r["composantes"]["travaux"]["hypothese_m2"] == round(MODE_B_TRAVAUX_M2_MIN)


def test_repli_commune_etiquete(db_session):
    _seed(db_session)
    r = compute_mode_b(db_session, "97499100MB0005")
    assert r["disponible"] is True
    assert r["composantes"]["prix_sortie"]["niveau"] == "commune"
    assert "repli" in r["composantes"]["prix_sortie"]["libelle"]


def test_absent_explicite_emprise(db_session):
    _seed(db_session)
    r = compute_mode_b(db_session, "97499000MB0004")
    assert r["disponible"] is False and "Absent" in r["motif"] and "inventé" in r["motif"]
