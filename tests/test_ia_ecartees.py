"""M49 (Lot B) — l'IA doit TOUT montrer : le contexte porte le motif exact d'écartement/
déclassement/registre + vigilances + segment Renouvellement + mode B. Verrous par cas (le
constat M49 : l'IA refusait sur une bâti-saturé, disait « non disponible » sur une zone fermée,
ignorait le registre et le segment Renouvellement)."""
from __future__ import annotations

import labuse.api.fiche_ask as fa


class _DBraise:
    """DB factice : les blocs faisabilité/aménités (db.execute) dégradent en ABSENT, pas en erreur."""
    def execute(self, *a, **k):
        raise RuntimeError("pas de DB en test unitaire")


def _ctx(monkeypatch, fiche, verdict):
    monkeypatch.setattr("labuse.api.app._q_v2_fiche", lambda db, idu: fiche)
    monkeypatch.setattr("labuse.verdict_servi.verdict_servi", lambda db, idu, run=None: verdict)
    facts, _ = fa._ask_context(_DBraise(), "TEST")
    return facts


_BASE_FICHE = {"idu": "97400000ZZ0001", "commune": "X", "surface_m2": 500, "lines": []}


def test_bati_sature_motif_present(monkeypatch):
    facts = _ctx(monkeypatch, _BASE_FICHE,
                 {"label": "Déclassée — bâti saturé", "tier": "declasse_bati_sature", "rang": 1,
                  "motif": "bâtie 15-40 %, bâti d'année absente, non divisible", "exception_registre": False})
    assert "non divisible" in facts["motif_classement"].value        # avant M49 : l'IA REFUSAIT
    assert facts["motif_classement"].provenance == "SOURCE"


def test_zone_fermee_motif_structurel(monkeypatch):
    facts = _ctx(monkeypatch, _BASE_FICHE,
                 {"label": "Déclassée — fermée à l'urbanisation", "tier": "declasse_zone_fermee",
                  "rang": 1, "motif": None, "exception_registre": False})
    assert "fermée à l'urbanisation" in facts["motif_classement"].value   # avant : « non disponible »


def test_registre_motif_et_flag(monkeypatch):
    facts = _ctx(monkeypatch, _BASE_FICHE,
                 {"label": "À creuser", "tier": "a_creuser", "rang": 4132,
                  "motif": "Piscine centrale détectée sur imagerie 2025 — usage à vérifier.",
                  "exception_registre": True})
    assert "Piscine" in facts["motif_classement"].value
    assert facts["classement_registre"].provenance == "SOURCE"


def test_segment_renouvellement_expose(monkeypatch):
    fiche = {**_BASE_FICHE, "renouvellement": {"libelle": "Parcelle occupée — potentiel de "
             "renouvellement urbain", "rang_segment": 1, "total_segment": 67258, "renouv_score": 85}}
    facts = _ctx(monkeypatch, fiche,
                 {"label": "Écartée", "tier": "ecartee", "rang": 6916, "motif": None, "exception_registre": False})
    assert "renouvellement" in facts["segment_renouvellement"].value.lower()


def test_mode_b_expose_quand_disponible(monkeypatch):
    fiche = {**_BASE_FICHE, "mode_b": {"disponible": True, "population_tier": "declasse_bati_sature",
             "sortie_locative": {"loyer": {"mensuel_eur": 592}}}}
    facts = _ctx(monkeypatch, fiche,
                 {"label": "Déclassée — bâti saturé", "tier": "declasse_bati_sature", "rang": 1,
                  "motif": "x", "exception_registre": False})
    assert "592" in facts["mode_b_rehabilitation"].value
    assert facts["mode_b_rehabilitation"].provenance == "ESTIME"


def test_vigilances_soft_hors_rgpd(monkeypatch):
    fiche = {**_BASE_FICHE, "lines": [
        {"layer": "risques", "result": "SOFT_FLAG", "detail": "PPR aléa moyen inondation"},
        {"layer": "age_dirigeant", "result": "SOFT_FLAG", "detail": "gérant 82 ans"},   # RGPD → exclu
        {"layer": "bati", "result": "HARD_EXCLUDE", "detail": "déjà bâtie"},             # pas une vigilance soft
    ]}
    facts = _ctx(monkeypatch, fiche,
                 {"label": "À creuser", "tier": "a_creuser", "rang": 1, "motif": None, "exception_registre": False})
    v = facts["vigilances"].value
    assert any("PPR" in x for x in v)
    assert not any("gérant" in x for x in v)          # garde RGPD (M45)
    assert not any("déjà bâtie" in x for x in v)      # HARD_EXCLUDE ≠ vigilance soft
