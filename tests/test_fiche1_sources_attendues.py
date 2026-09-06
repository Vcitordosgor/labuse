"""FICHE-1 lot 7 — les données réglementaires qui ATTENDENT une source (SOURCES-1).

Emplacement réservé, EBC, DPU, PEB, zonage A/B/C : demandées par Vic mais leur source n'est pas
ingérée. Déclarées avec l'état « non calculée — source absente » et la source attendue nommée —
JAMAIS servies (aucun robinet) tant que le réservoir n'est pas là, pour que le trou soit visible
et se comble tout seul à l'ingestion.
"""
from __future__ import annotations

from labuse.registre import ROBINETS
from labuse.registre.donnees import DONNEES

ATTENDUES = ("er_emplacement_reserve", "ebc_classe", "dpu_perimetre", "peb_zone",
             "zonage_abc_logement")


def test_declarees_source_absente_et_nommee():
    for cid in ATTENDUES:
        d = DONNEES[cid]
        assert d.en_attente, cid
        # état « non calculée — source absente » + chantiers nommés (CIRCUIT-3 requis par le guard)
        assert "source absente" in d.en_attente, cid
        assert "CIRCUIT-3" in d.en_attente and "SOURCES-1" in d.en_attente, cid
        # la source attendue est nommée (domaine_source)
        assert d.domaine_source, cid


def test_jamais_servies_tant_que_source_absente():
    servies = {c for r in ROBINETS.values() for c in r.chiffres}
    assert not (set(ATTENDUES) & servies)
