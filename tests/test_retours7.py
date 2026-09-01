"""RETOURS-7 — tests des fonctions pures introduites/corrigées par le mandat.

Z7  : registre du modèle PAR USAGE (ai_models.SURFACES / model_for / surfaces_table).
Z12.3 : la SDP résiduelle n'est plus « donnée non disponible » (alignement sur la vigilance).
Z12.2 : libellé de version LISIBLE unique dérivé du run courant.
"""
from __future__ import annotations

import datetime as _dt

from labuse import ai_models
from labuse.scoring.p_v2.libelles_client import phrase_client


# ── Z7 — le modèle par usage ─────────────────────────────────────────────────────────────────────
def test_surfaces_table_couvre_chaque_kind_avec_un_modele_actif():
    table = ai_models.surfaces_table()
    assert len(table) == len(ai_models.SURFACES)
    for row in table:
        assert row["kind"] in ai_models.SURFACES
        assert row["label"]
        # le modèle servi est TOUJOURS un modèle actif (jamais un retiré, jamais un littéral inconnu)
        assert row["model"] in ai_models.ACTIVE_MODELS


def test_model_for_defaut_registre():
    # défauts gravés au registre : routage/factuel sur Haiku, raisonnement sur Sonnet
    assert ai_models.model_for("copilote-route") == ai_models.MODEL_FACTUAL
    assert ai_models.model_for("copilote-select") == ai_models.MODEL_REASONING
    assert ai_models.model_for("vision_pige") == ai_models.MODEL_VISION
    # kind inconnu → défaut agent, jamais une exception
    assert ai_models.model_for("kind-inexistant") == ai_models.DEFAULT_AGENT_MODEL


def test_model_for_override_par_surface(monkeypatch):
    monkeypatch.setenv("LABUSE_IA_MODELE_SYNTHESE", ai_models.MODEL_FACTUAL)
    assert ai_models.model_for("synthese") == ai_models.MODEL_FACTUAL
    # les autres surfaces ne bougent pas
    assert ai_models.model_for("copilote-select") == ai_models.MODEL_REASONING


def test_model_for_override_retire_leve(monkeypatch):
    monkeypatch.setenv("LABUSE_IA_MODELE_SEARCH", "claude-3-5-haiku-20241022")  # retiré
    import pytest
    with pytest.raises(ValueError):
        ai_models.model_for("search")


# ── Z12.3 — SDP résiduelle : plus jamais « donnée non disponible » ───────────────────────────────
def test_sdp_residuelle_manquant_nest_pas_donnee_non_disponible():
    # bin « manquant » = parcelle contrainte (SDP résiduelle 0, cause posée) : la vigilance dit
    # « 0 m² — rien à construire » (juste). Le « pourquoi » ne doit plus la contredire.
    for bin_ in ("manquant", "inconnu", ""):
        p = phrase_client("sdp_residuelle_m2", bin_, "SDP résiduelle")
        assert "non disponible" not in p.lower()
        assert "résiduelle" in p.lower()


def test_autres_features_gardent_donnee_non_disponible():
    # la correction est CIBLÉE sur la SDP résiduelle — les autres features numériques inchangées.
    assert "donnée non disponible" in phrase_client("permis_24m_norm", "manquant", "Permis")


def test_sdp_residuelle_valeur_numerique_inchangee():
    # une tranche numérique réelle garde son libellé par seuils (aucune régression).
    p = phrase_client("sdp_residuelle_m2", "(493, 719]", "SDP résiduelle")
    assert "non retenue" not in p


# ── Z12.2 — un seul libellé de version lisible, dérivé du run courant ─────────────────────────────
def test_libelle_version_servie_est_une_date_lisible():
    from labuse.api.score_v2 import libelle_version_servie
    lab = libelle_version_servie({"computed_at": _dt.datetime(2026, 8, 25, 10, 0, 0)})
    assert lab == "Analyse LABUSE arrêtée au 25/08/2026"
    # aucun identifiant technique (m36-l2f / q_v / run) ne fuit dans le libellé client
    for tech in ("m36", "q_v", "run "):
        assert tech not in lab


def test_libelle_version_servie_repli_sans_date():
    from labuse.api.score_v2 import libelle_version_servie
    assert libelle_version_servie({"computed_at": None}) == "Analyse LABUSE — version courante"
