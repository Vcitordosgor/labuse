"""GABARIT-5 lot D — page « Enveloppe réglementaire » du pré-dossier PC.

Gabarit bloqué → la page N'EST PAS produite (None) ; gabarit servi → un PDF avec le plan et la
mention « pas un plan de masse ». Le builder est monkeypatché (aucune DB).
"""
from __future__ import annotations

import pytest

from labuse.gabarit.contract import GabaritInput
from labuse.gabarit.fixtures import demo_gabarit_input


def _patch(monkeypatch, build):
    import labuse.gabarit.builder as B
    monkeypatch.setattr(B, "build_gabarit_input", lambda db, idu: build)


def test_enveloppe_none_si_bloque(monkeypatch):
    from labuse.api import pre_dossier as PD
    from labuse.gabarit.builder import BuildResult
    _patch(monkeypatch, BuildResult(input=GabaritInput(), blocking=["limite non qualifiée"]))
    assert PD._enveloppe_reglementaire(None, "x") is None


def test_enveloppe_pdf_si_servi(monkeypatch):
    pytest.importorskip("weasyprint")
    from labuse.api import pre_dossier as PD
    from labuse.gabarit.builder import BuildResult
    _patch(monkeypatch, BuildResult(input=demo_gabarit_input(), blocking=[]))
    pdf = PD._enveloppe_reglementaire(None, "demo")
    assert pdf and pdf[:5] == b"%PDF-"
