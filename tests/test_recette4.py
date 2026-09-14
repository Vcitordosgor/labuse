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


# ── U1/U2 — la section « Fiscalité locale et régime applicable » du Financier ──────────────────
def test_fiscalite_locale_dit_le_taux_et_la_zone_sources():
    from labuse.exports.blocs.financier import _fiscalite_locale
    tfpb = {"tfpb_commune_pct": 41.77, "tfpb_epci_pct": 0.0, "teom_pct": 16.0,
            "millesime": "REI 2025 (impositions primitives)"}
    zonage = {"zone": "A", "millesime": "arrêté du 23/06/2026"}
    html = _fiscalite_locale(tfpb, zonage, {"duree_portage_saisi_mois": {"valeur": 29}})
    assert "Fiscalité locale et régime applicable" in html
    # TESTS-1 lot 2 (B) — RECETTE-9 T4 (61f420aa) : la clé dit « Zone … », la valeur porte le SEUL
    # code (« A ») — plus de « zone A » redondant. Le contrat reste : taux ET zone servis, sourcés.
    assert "41,77 %" in html
    assert "Zone d&#x27;investissement (A/B/C)" in html and "<td>A</td>" in html   # apostrophe échappée
    # la taxe foncière de portage est DITE, jamais devinée : on exige la valeur locative cadastrale.
    assert "valeur locative cadastrale" in html
    assert "invente pas de valeur locative" in html   # l'apostrophe est échappée par note()
    assert "REI 2025" in html                     # source + millésime servis
    # aucune balise HTML crue échappée ne fuit dans les notes (note() échappe son texte).
    assert "&lt;strong&gt;" not in html


def test_fiscalite_locale_rien_sans_source():
    """Doctrine : sans donnée sourcée, aucune section (jamais un taux ou une zone inventés)."""
    from labuse.exports.blocs.financier import _fiscalite_locale
    assert _fiscalite_locale(None, None, {}) == ""
