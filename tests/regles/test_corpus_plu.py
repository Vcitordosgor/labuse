"""Témoin CIRCUIT-4 — corpus PLU : invariant somme des statuts, RNU prime (millésimes injectés,
corpus vide → non_ingere)."""
from __future__ import annotations

import pytest


@pytest.mark.db
def test_invariant_somme_statuts(engine):
    from labuse.registre.moteurs.commune import etat_corpus_plu
    from labuse.db import session_scope
    millesimes = {
        "97401": {"commune": "Les Avirons", "statut": "autre", "idurba": None},
        "97416": {"commune": "Saint-Philippe", "statut": "rnu"},
        "97423": {"commune": "X", "statut": "opposabilite_en_attente", "idurba": "PLU_X"},
    }
    with session_scope() as s:
        out = etat_corpus_plu(s, millesimes=millesimes)
    # invariant : somme des quatre statuts = n_communes (recompté indépendamment)
    assert (out["servables"] + out["n_revision"] + out["n_rnu"] + out["n_non_ingere"]
            == out["n_communes"] == 3)
    assert out["n_rnu"] == 1 and out["n_revision"] == 1


@pytest.mark.db
def test_rnu_prime(engine):
    from labuse.registre.moteurs.commune import etat_corpus_plu
    from labuse.db import session_scope
    with session_scope() as s:
        out = etat_corpus_plu(s, millesimes={"97416": {"commune": "Saint-Philippe", "statut": "rnu"}})
    c = out["communes"][0]
    assert c["statut"] == "rnu" and "RNU" in c["message"]
