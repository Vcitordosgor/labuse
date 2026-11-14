"""CAPACITE-1 LOT C — la règle unique « surface à retenir » et le garde-fou « un seul chiffre par parcelle »."""
import os

import pytest

from labuse.faisabilite.surface_retenue import (GRANDEUR_ESTIMATION, GRANDEUR_SCENARIO,
                                                surface_a_retenir)


@pytest.fixture(scope="module")
def session_reelle():
    from sqlalchemy import text
    from sqlalchemy.orm import sessionmaker

    from labuse.db import make_engine

    url = os.environ.get("LABUSE_APP_DATABASE_URL") or os.environ.get("LABUSE_DATABASE_URL")
    if not url:
        pytest.skip("base applicative absente")
    s = sessionmaker(bind=make_engine(url=url), future=True)()
    if s.execute(text("SELECT count(*) FROM parcels WHERE idu = '97416000HT0538'")).scalar() != 1:
        s.close()
        pytest.skip("parcelle témoin HT0538 absente")
    yield s
    s.close()


def test_sans_etude_estimation_rapide():
    r = surface_a_retenir(614, None)
    assert r["valeur_m2"] == 614 and r["source"] == GRANDEUR_ESTIMATION
    assert "estimation rapide" in r["phrase"] and "scénario" not in r["phrase"].lower()


def test_scenario_sans_stationnement_majorant_non_retenu():
    # HT0538 — le barème n'est pas ingéré : le scénario (888) est un MAJORANT, on retient 614.
    r = surface_a_retenir(614, {"sdp_m2": 887.5, "stationnement_applique": False})
    assert r["valeur_m2"] == 614 and r["source"] == GRANDEUR_ESTIMATION
    assert "888" in r["phrase"] and "non retenu tant que le stationnement" in r["phrase"]


def test_scenario_avec_stationnement_retenu():
    # Le Tampon AD0887 — barème appliqué (stationnement déduit) : on retient le scénario (795).
    r = surface_a_retenir(1047, {"sdp_m2": 795, "stationnement_applique": True})
    assert r["valeur_m2"] == 795 and r["source"] == GRANDEUR_SCENARIO
    assert "795 m²" in r["phrase"] and "1 047 m²" in r["phrase"] and "stationnement déduit" in r["phrase"]


def test_jamais_le_plus_grand_par_defaut():
    # Garde LABUSE : un scénario plus GRAND que l'estimation n'est pas retenu sans stationnement appliqué.
    r = surface_a_retenir(614, {"sdp_m2": 2000, "stationnement_applique": False})
    assert r["valeur_m2"] == 614


# ── Garde-fou : un seul « surface à retenir » par parcelle, tous documents (C6) ──────────────────
@pytest.mark.reel
def test_un_seul_surface_a_retenir_par_parcelle(session_reelle):
    """Le Dossier (estimation fiche + scénario PERSISTÉ) et l'Étude (scénario LIVE) doivent produire
    LA MÊME surface à retenir — sinon deux documents afficheraient deux chiffres (interdit)."""
    from labuse.implantation import revisions as _rev
    from labuse.implantation.service import etudier_payload
    from labuse.exports.etude_faisabilite import (scenario_retenu, scenario_etude_persiste,
                                                   _bareme_stationnement_absent)
    from labuse.faisabilite.surface_retenue import estimation_rapide_m2

    idu = "97416000HT0538"
    cfg = {"idus": [idu], "type_projet": "collectif", "objectif": "equilibre", "stationnement": "aerien"}
    payload = etudier_payload(session_reelle, cfg)
    _rev.enregistrer(session_reelle, payload)          # persiste (le Dossier le relira)

    # Étude (scénario LIVE) et Dossier (scénario PERSISTÉ) partent de la MÊME estimation rapide (live).
    est = estimation_rapide_m2(session_reelle, idu)
    retenu = scenario_retenu(payload)
    scn_e = {"sdp_m2": (retenu or {}).get("resume", {}).get("sdp_m2"),
             "stationnement_applique": not _bareme_stationnement_absent(payload)}
    sar_etude = surface_a_retenir(est, scn_e)
    sar_dossier = surface_a_retenir(est, scenario_etude_persiste(session_reelle, idu))

    assert sar_etude["valeur_m2"] == sar_dossier["valeur_m2"], (
        f"deux surfaces à retenir pour {idu} : Étude {sar_etude['valeur_m2']} vs Dossier {sar_dossier['valeur_m2']}")
    # HT0538 : stationnement non ingéré → on retient l'estimation rapide (614), jamais le scénario (888).
    assert sar_dossier["source"] == GRANDEUR_ESTIMATION
