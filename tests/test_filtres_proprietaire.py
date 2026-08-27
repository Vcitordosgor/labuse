"""K1 (rattrapage KelFoncier) — filtres propriétaire personne morale.

La donnée (DGFiP 2025 + INPI RNE) est déjà en base en prod. Ici (base de test vide) on SEME un
jeu minimal [KF-TEST] et on gèle : facettes = valeurs RÉELLES avec comptes + millésime, WHERE
construit les bons EXISTS, l'âge du dirigeant reste FERMÉ (drapeau RGPD désactivé par défaut).
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from labuse.db import session_scope

pytestmark = pytest.mark.db

COMMUNE = "KF-Test-Ville"
WKT = "POLYGON((55.45 -20.9,55.451 -20.9,55.451 -20.901,55.45 -20.901,55.45 -20.9))"


@pytest.fixture
def client(engine):
    from labuse.api.app import app
    return TestClient(app)


@pytest.fixture
def seed(engine):
    """2 parcelles PM [KF-TEST] : une SCI (siren enrichi APE 68.20B, 3 dirigeants) et une Commune."""
    sci_siren = "900000001"
    tag = uuid.uuid4().hex[:6]
    idu_sci = f"KFT{tag}SCI001"[:14].ljust(14, "0")
    idu_com = f"KFT{tag}COM001"[:14].ljust(14, "0")
    with session_scope() as s:
        for idu in (idu_sci, idu_com):
            s.execute(text(
                "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, centroid, bbox)"
                " VALUES (:i, :c, 'ZZ', '1', ST_GeomFromText(:w,4326), ST_Transform(ST_GeomFromText(:w,4326),2975),"
                " 800, ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326)))"),
                {"i": idu, "c": COMMUNE, "w": WKT})
        s.execute(text("INSERT INTO parcelle_personne_morale (idu, groupe, groupe_label, forme_juridique, denomination, siren, millesime, source)"
                       " VALUES (:i, 0, 'Personnes morales non remarquables', 'SCI', 'SCI KF-TEST OMEGA', :sir, '2025', 'DGFiP — parcelles des personnes morales')"),
                  {"i": idu_sci, "sir": sci_siren})
        s.execute(text("INSERT INTO parcelle_personne_morale (idu, groupe, groupe_label, forme_juridique, denomination, siren, millesime, source)"
                       " VALUES (:i, 4, 'Commune', 'COM', 'COMMUNE KF-TEST', '900000002', '2025', 'DGFiP — parcelles des personnes morales')"),
                  {"i": idu_com})
        s.execute(text("INSERT INTO owner_enrichment (siren, denomination, source, payload)"
                       " VALUES (:sir, 'SCI KF-TEST OMEGA', 'kf-test', CAST(:p AS jsonb))"),
                  {"sir": sci_siren, "p": '{"activite_principale": "68.20B"}'})
        for i in range(3):
            s.execute(text("INSERT INTO pm_dirigeants (siren, type_personne, nom, date_naissance, role_entreprise, diffusible)"
                           " VALUES (:sir, 'INDIVIDU', :nom, '1970-05', 'gerant', true)"),
                      {"sir": sci_siren, "nom": f"KFTEST_{i}"})
        s.commit()
    yield {"idu_sci": idu_sci, "idu_com": idu_com, "sci_siren": sci_siren}
    with session_scope() as s:
        s.execute(text("DELETE FROM pm_dirigeants WHERE siren IN ('900000001','900000002')"))
        s.execute(text("DELETE FROM owner_enrichment WHERE siren IN ('900000001','900000002')"))
        s.execute(text("DELETE FROM parcelle_personne_morale WHERE idu IN (:a,:b)"), {"a": idu_sci, "b": idu_com})
        s.execute(text("DELETE FROM parcels WHERE commune = :c"), {"c": COMMUNE})
        s.commit()


def test_facettes_valeurs_reelles_avec_millesime(client, seed):
    f = client.get(f"/proprietaires/facettes?commune={COMMUNE}").json()
    assert f["millesime"] == "2025" and "DGFiP" in f["source"]
    codes = {x["code"]: x for x in f["formes"]}
    assert "SCI" in codes and "COM" in codes
    assert codes["SCI"]["label"] == "Société civile immobilière" and codes["SCI"]["n"] == 1
    apes = {x["code"] for x in f["apes"]}
    assert "68.20B" in apes
    assert f["couverture"]["couvert"] is True and f["couverture"]["pm"] == 2
    assert f["age_dirigeant_actif"] is False           # drapeau RGPD fermé


def test_autocomplete_noms_reels(client, seed):
    r = client.get(f"/proprietaires/autocomplete?q=OMEGA&commune={COMMUNE}").json()["suggestions"]
    assert r and r[0]["denomination"] == "SCI KF-TEST OMEGA" and r[0]["siren"] == seed["sci_siren"]
    # q trop court → aucune suggestion inventée
    assert client.get("/proprietaires/autocomplete?q=O").json()["suggestions"] == []


def test_couverture_non_couvert_si_pas_de_pm(client):
    """Une commune sans PM répond couvert=False (dit « non couvert », pas un zéro muet)."""
    f = client.get("/proprietaires/facettes?commune=Commune-Inexistante-ZZ").json()
    assert f["couverture"]["couvert"] is False and f["couverture"]["pm"] == 0


def test_where_construit_les_filtres_pm():
    """Le fragment WHERE construit les bons EXISTS + paramètres (sans données de scoring)."""
    from labuse.api.app import _q_v2_where
    w, p = _q_v2_where("q_v11_m137", None, None, None, False, None,
                       pm_forme="SCI", pm_siren="900000001,900000002",
                       pm_ape="68.20B", pm_denom="OMEGA", pm_dirig_min=2)
    assert "parcelle_personne_morale" in w and "forme_juridique = ANY(:pm_forme)" in w
    assert p["pm_forme"] == ["SCI"] and p["pm_siren"] == ["900000001", "900000002"]
    assert "owner_enrichment" in w and p["pm_ape"] == ["68.20B"]           # APE via jointure SIREN
    assert "v_pm_propension_vendre" in w and p["pm_dirig_min"] == 2        # dirigeants via la vue
    assert p["pm_denom"] == "%OMEGA%"


def test_age_dirigeant_ferme_par_defaut():
    from labuse.config import get_settings
    assert get_settings().filtre_age_dirigeant is False
