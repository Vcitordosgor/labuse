"""Tests du générateur de rapport Flash (Lot 1) — sections conditionnelles + idempotence.

Base de test quasi VIDE (conftest) = le cas « parcelle pauvre » du mandat : le rapport
doit se générer proprement, sans section vide et sans erreur, même quand seules les
tables du schéma existent. La parcelle « riche » est couverte par la QA manuelle sur la
base réelle (critère : validation visuelle Vic).
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.db

IDU = "97405000XX0001"


@pytest.fixture
def parcelle_seedee(db_session):
    """Une parcelle minimale (géométrie réelle Petite-Île, attributs synthétiques)."""
    db_session.execute(text(
        """INSERT INTO parcels (idu, commune, section, numero, surface_m2, geom, geom_2975)
           VALUES (:idu, 'Petite-Île', 'XX', '0001', 815,
                   ST_GeomFromText('POLYGON((55.5646 -21.3524, 55.5650 -21.3524,
                                             55.5650 -21.3520, 55.5646 -21.3520,
                                             55.5646 -21.3524))', 4326),
                   ST_Transform(ST_GeomFromText('POLYGON((55.5646 -21.3524, 55.5650 -21.3524,
                                             55.5650 -21.3520, 55.5646 -21.3520,
                                             55.5646 -21.3524))', 4326), 2975))"""),
        {"idu": IDU})
    return IDU


def test_collect_parcelle_inconnue(db_session):
    from labuse.flash.data import collect_report_data

    with pytest.raises(ValueError):
        collect_report_data(db_session, "97499000ZZ9999")


def test_collect_parcelle_pauvre_sections_omises(db_session, parcelle_seedee):
    """Base sans DVF/Sitadel/risques : chaque section manquante est None ou marquée
    vide — jamais une exception (résilience mandat §Lot1.3)."""
    from labuse.flash.data import collect_report_data

    data = collect_report_data(db_session, parcelle_seedee)
    assert data["parcelle"]["commune"] == "Petite-Île"
    assert data["parcelle"]["surface_m2"] == 815
    # Sections sans donnée : None (omises) ou explicitement « rien » — pas de section vide.
    for cle in ("constructibilite", "terrain"):
        assert data[cle] is None, f"{cle} devrait être omise sur base vide"
    assert data["sources"], "la page Sources doit toujours exister"


def test_generation_pdf_parcelle_pauvre(db_session, parcelle_seedee, tmp_path, monkeypatch):
    """Le PDF d'une parcelle pauvre se génère proprement (< 30 s, sans réseau)."""
    from labuse.flash import generate_flash_report

    monkeypatch.setenv("LABUSE_FLASH_STORAGE_DIR", str(tmp_path))
    from labuse import config
    config.get_settings.cache_clear()
    try:
        pdf = generate_flash_report(parcelle_seedee, order_ref="FL-TEST-1",
                                    db=db_session, with_map=False)
        assert pdf.exists()
        assert pdf.read_bytes()[:5] == b"%PDF-"

        # Idempotence : même (order_ref, idu, version) → fichier réutilisé tel quel.
        mtime = pdf.stat().st_mtime_ns
        pdf2 = generate_flash_report(parcelle_seedee, order_ref="FL-TEST-1",
                                     db=db_session, with_map=False)
        assert pdf2 == pdf and pdf.stat().st_mtime_ns == mtime
    finally:
        config.get_settings.cache_clear()


def test_watermark_exemple(db_session, parcelle_seedee, tmp_path, monkeypatch):
    """Le rapport démo porte le watermark (Lot 3) — le HTML le contient sur chaque page."""
    from labuse.flash.report import render_report_html

    monkeypatch.setenv("LABUSE_FLASH_STORAGE_DIR", str(tmp_path))
    from labuse import config
    config.get_settings.cache_clear()
    try:
        html = render_report_html(db_session, parcelle_seedee, order_ref="FL-DEMO",
                                  watermark="EXEMPLE", with_map=False)
        assert 'class="watermark"' in html and "EXEMPLE" in html
        assert "FL-DEMO" in html
    finally:
        config.get_settings.cache_clear()
