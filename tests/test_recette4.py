"""RECETTE-4 — gardes des branchements TFPB + zonage A/B/C (Lot 1, U1/U2).

Tests de fonctions PURES (aucune base) : la fraîcheur de la taxe foncière et la section
« Fiscalité locale » du Financier. Les rendus en base (fiche commune, fiche parcelle) ont été
constatés au navigateur (cf. docs/audit-2026-09/RECETTE-4.md)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone


# ── U1 — fraîcheur de la taxe foncière (fiche commune) ────────────────────────────────────────
def test_perime_donnee_recente_non_signalee():
    from labuse.api.fiche_commune import _perime
    recent = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    assert _perime(recent) is False


def test_perime_donnee_ancienne_signalee():
    from labuse.api.fiche_commune import _perime
    vieux = (datetime.now(timezone.utc) - timedelta(days=400)).isoformat()
    assert _perime(vieux) is True


def test_perime_date_absente_ou_illisible_jamais_de_fausse_alerte():
    from labuse.api.fiche_commune import _perime
    assert _perime(None) is False
    assert _perime("pas-une-date") is False


