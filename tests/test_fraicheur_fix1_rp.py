"""FRAICHEUR-FIX-1 (point 4) — recensement RP : le contrôle de millésime compare l'édition RP
PUBLIÉE (année lue par la sonde page) au millésime RÉELLEMENT ingéré (`iris_rp.millesime`). RP2023
publié mais RP2022 servi → en retard ; une fois RP2023 ingéré → à jour. L'ingestion est paramétrée
par millésime (bascule RP2023 = un appel avec les URLs RP2023)."""
import inspect

import pytest
from sqlalchemy import text

from labuse import controle_millesime as cm
from labuse.ingestion import iris_rp

_NOM = "INSEE RP2022 — bases IRIS (logement, population)"


def _ensure_iris(s):
    # table minimale suffisante pour le contrôle (SELECT max(millesime)) — isolée du schéma complet.
    s.execute(text("CREATE TABLE IF NOT EXISTS iris_rp (iris varchar PRIMARY KEY, "
                   "insee varchar, millesime varchar(64) NOT NULL)"))
    s.execute(text("DELETE FROM iris_rp"))


@pytest.mark.db
def test_rp_en_retard_avant_puis_a_jour_apres(db_session):
    s = db_session
    _ensure_iris(s)
    # servi = RP2022, publié (sonde page) = 2023 → EN RETARD
    s.execute(text("INSERT INTO iris_rp (iris, insee, millesime) "
                   "VALUES ('974110000', '97411', 'RP2022, parution 16/10/2025')"))
    v = cm.verdict(s, {"name": _NOM, "dernier_vu": "2023", "source_horizon_at": None})
    assert v["etat"] == "en_retard" and v["publie"] == "2023" and v["ingere"] == "2022"

    # après ingestion RP2023 (millésime du jeu mis à jour) → À JOUR
    s.execute(text("UPDATE iris_rp SET millesime = 'RP2023, parution 2026'"))
    v2 = cm.verdict(s, {"name": _NOM, "dernier_vu": "2023", "source_horizon_at": None})
    assert v2["etat"] == "a_jour"


@pytest.mark.db
def test_rp_a_verifier_si_table_vide(db_session):
    s = db_session
    _ensure_iris(s)
    v = cm.verdict(s, {"name": _NOM, "dernier_vu": "2023", "source_horizon_at": None})
    assert v["etat"] == "a_verifier"   # publié connu, ingéré introuvable → pas prouvé à jour


def test_ingest_iris_rp_parametre_par_millesime():
    # la bascule RP2023 passe par un simple paramètre (URLs + millésime), pas une édition de code figée.
    sig = inspect.signature(iris_rp.ingest_iris_rp)
    assert "millesime" in sig.parameters
    assert "url_logement" in sig.parameters and "url_population" in sig.parameters
