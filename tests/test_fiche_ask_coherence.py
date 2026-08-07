"""M48 (F1) — verrou : le contexte IA porte le VERDICT SERVI, jamais le champ mort `statut`.

Régression attrapée par l'audit M48 : `fiche_ask` passait `statut_tier = f["statut"]` (matrice v1
éteinte M37) → l'IA annonçait « écartée » d'une brûlante. Ce test fige que le contexte lit
`verdict_servi` (parcel_p_score_v2.tier, point de vérité M34) même quand le champ mort dit autre chose.
"""
from __future__ import annotations

import labuse.api.fiche_ask as fa


class _DBraise:
    """DB factice : les blocs faisabilité/aménités (db.execute) doivent dégrader en ABSENT, pas casser."""
    def execute(self, *a, **k):
        raise RuntimeError("pas de DB en test unitaire")


def test_contexte_ia_porte_le_verdict_servi_pas_la_matrice_morte(monkeypatch):
    # fiche premium AVEC le piège : le champ mort statut = « ecartee »
    monkeypatch.setattr("labuse.api.app._q_v2_fiche",
                        lambda db, idu: {"idu": idu, "commune": "Sainte-Marie",
                                         "surface_m2": 500, "statut": "ecartee"})
    # verdict RÉELLEMENT servi (parcel_p_score_v2.tier traduit) = Brûlante rang 14
    monkeypatch.setattr("labuse.verdict_servi.verdict_servi",
                        lambda db, idu, run=None: {"label": "Brûlante", "tier": "brulante", "rang": 14})

    facts, _ = fa._ask_context(_DBraise(), "97418000AT2542")

    # le classement exposé à l'IA = le verdict SERVI, jamais le champ mort
    assert facts["statut_tier"].value == "Brûlante"
    assert facts["statut_tier"].value != "ecartee"
    assert facts["statut_tier"].provenance == "SOURCE"
    assert facts["rang_classement"].value == 14


def test_parcelle_non_evaluee_reste_absente(monkeypatch):
    # hors run servi → verdict_servi renvoie label None → Fact ABSENT (l'IA dit « non disponible »)
    monkeypatch.setattr("labuse.api.app._q_v2_fiche",
                        lambda db, idu: {"idu": idu, "commune": "X", "surface_m2": 300, "statut": "ecartee"})
    monkeypatch.setattr("labuse.verdict_servi.verdict_servi",
                        lambda db, idu, run=None: {"label": None, "tier": None, "rang": None})
    facts, _ = fa._ask_context(_DBraise(), "97499000ZZ0001")
    assert facts["statut_tier"].provenance == "ABSENT"
