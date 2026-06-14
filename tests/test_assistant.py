"""3.A — Assistant IA : garde-fou anti-hallucination + dégradation propre sans clé.

Sans clé API on ne peut pas tester la réponse live, mais on verrouille l'essentiel : le prompt
ne transmet QUE des faits réels (liste blanche), et l'absence de clé donne un message clair sans
crash. La recette « explication fidèle sur 2 parcelles contrastées » s'exécute dès la clé posée.
"""
from __future__ import annotations

import pytest

from labuse.api.assistant import ENV_KEY, assistant_facts, explain_parcel, is_configured

FICHE = {
    "parcel": {"idu": "97415000AB0001", "commune": "Saint-Paul", "section": "AB", "numero": "1",
               "surface_m2": 1234.5, "centroid": {"lon": 55.27, "lat": -21.0}},
    "verdict": {"status": "opportunite", "opportunity_score": 78, "completeness_score": 64,
                "downgrade_reason": None},
    "faisabilite": {"zone": "U1c", "constructible": True, "verdict": "R+3 · ~12-18 logts",
                    "fourchette": {"niveaux": "R+3", "surface_plancher_m2": 900,
                                   "logements_au_sol": [12, 18], "hauteur_m": 12.0},
                    "volume3d": {"volume_m3": 7200},
                    "bilan": {"verdict": "charge foncière ~250 k€", "charge_fonciere": 250000,
                              "fiable": True}},
    "cascade": [
        {"layer_name": "zonage_plu_gpu", "result": "POSITIVE", "detail": "Zone U constructible", "source": "GPU"},
        {"layer_name": "pente", "result": "SOFT_FLAG", "detail": "Pente forte 32 %", "source": "RGE ALTI"},
        {"layer_name": "ravine", "result": "UNKNOWN", "detail": "non ingéré", "source": "BD TOPO"},
    ],
    "sources_responded": ["GPU", "RGE ALTI"],
    "sources_silent": ["BD TOPO"],
    "resume": {"titre": "Belle opportunité"},
}


def test_facts_liste_blanche_seulement_les_vrais_champs():
    f = assistant_facts(FICHE)
    assert set(f) == {"parcelle", "verdict", "faisabilite", "bilan_promoteur",
                      "contraintes_et_signaux", "completude", "resume_metier"}
    assert f["parcelle"]["surface_m2"] == 1234.5
    assert f["verdict"]["statut"] == "opportunite" and f["verdict"]["score_opportunite"] == 78
    assert f["faisabilite"]["hauteur_m"] == 12.0 and f["faisabilite"]["volume_enveloppe_m3"] == 7200
    assert f["bilan_promoteur"]["charge_fonciere"] == 250000
    # Le centroïde (donnée parasite) n'est PAS transmis au modèle.
    assert "centroid" not in str(f["parcelle"])


def test_facts_ne_garde_que_contraintes_et_signaux_pas_unknown():
    f = assistant_facts(FICHE)
    types = {c["type"] for c in f["contraintes_et_signaux"]}
    assert types == {"POSITIVE", "SOFT_FLAG"}            # UNKNOWN/PASS exclus
    assert all(c["motif"] for c in f["contraintes_et_signaux"])


def test_facts_donnee_absente_reste_nulle_jamais_inventee():
    f = assistant_facts({"parcel": {"idu": "X"}, "verdict": {}, "cascade": []})
    assert f["parcelle"]["surface_m2"] is None
    assert f["faisabilite"] is None and f["bilan_promoteur"] is None
    assert f["verdict"]["statut"] is None
    assert f["contraintes_et_signaux"] == []


def test_sans_cle_degrade_proprement(monkeypatch):
    monkeypatch.delenv(ENV_KEY, raising=False)
    out = explain_parcel(FICHE)
    assert out["available"] is False and out["reason"] == "no_key"
    assert ENV_KEY in out["message"]                    # message clair : nomme la variable d'env
    assert "facts" in out                               # les faits restent dispo (preview/debug)
    assert "explanation" not in out                     # rien d'inventé sans le modèle


def test_is_configured_reflet_de_lenv(monkeypatch):
    """1.B — l'UI sait si l'assistant est activable (bouton désactivé sinon)."""
    monkeypatch.delenv(ENV_KEY, raising=False)
    assert is_configured() is False
    monkeypatch.setenv(ENV_KEY, "sk-ant-test")
    assert is_configured() is True


@pytest.mark.db
def test_assistant_status_endpoint(engine, monkeypatch):
    from fastapi.testclient import TestClient

    from labuse.api.app import app
    monkeypatch.delenv(ENV_KEY, raising=False)
    with TestClient(app) as c:
        assert c.get("/assistant/status").json() == {"configured": False}
