"""EXPORTS-2 lot 7 — Pré-dossier PC (corrections sur le pack CERFA/PCMI existant).

Vérifs déterministes (sans base) : le CERFA suit le scénario (P1), la notice/fiche gagnent le
contenu attendu (P3), le plan de masse montre DEUX bâtiments et ne fuit plus l'EPSG (P4), les
lignes ne se coupent plus sur deux pages (P6). Le bug pré-existant round(double precision) qui
empêchait la notice est corrigé (zone.py).
"""
from __future__ import annotations

from pathlib import Path

from labuse.api import pre_dossier as pd

SRC = (Path(__file__).resolve().parents[1] / "src" / "labuse" / "api" / "pre_dossier.py").read_text()
ZONE = (Path(__file__).resolve().parents[1] / "src" / "labuse" / "zone.py").read_text()


# ── P1 — le CERFA et le LISEZMOI suivent le scénario ────────────────────────────────────────

def test_lisezmoi_maison_individuelle():
    lz = pd._lisezmoi("IDU1", "Saint-Paul", True, True,
                      {"type": "maison individuelle", "cerfa": "13406", "collectif": False})
    assert "maison individuelle" in lz.splitlines()[0]
    assert "13409" not in lz


def test_lisezmoi_collectif_renvoie_au_13409():
    lz = pd._lisezmoi("IDU1", "Saint-Paul", True, True,
                      {"type": "collectif", "cerfa": "13409", "collectif": True, "logements": 8})
    assert "collectif" in lz.splitlines()[0]
    assert "13409" in lz and "PC1 à PC8" in lz
    assert "NE VAUT QUE pour une maison individuelle" in lz     # le 13406 fourni est annoncé


# ── P3 — la notice/fiche gagnent le contenu (le code le produit) ─────────────────────────────

def test_pcmi4_reprend_les_servitudes_et_sources():
    # les libellés + sources publiques nommées sont dans le code de la notice
    assert "Risque naturel (PPR)" in SRC and "DEAL Réunion" in SRC
    assert "Bruit" in SRC and "Cerema" in SRC
    assert "architecte des Bâtiments de" in SRC and "Mérimée" in SRC
    assert "Adresse du terrain" in SRC and "Base Adresse Nationale" in SRC


def test_regles_gagnent_destinations_ta_redevance():
    assert "Destinations autorisées" in SRC
    assert "Taxe d'aménagement" in SRC and "Redevance d'archéologie préventive" in SRC
    assert "L524-7" in SRC       # redevance : article du Code du patrimoine (libellé sur 2 lignes source)


# ── P4 — deux bâtiments, EPSG retiré des légendes ───────────────────────────────────────────

def test_pcmi2_deux_batiments_et_sans_epsg():
    assert "ST_Collect" in SRC and "ST_CollectionExtract" in SRC   # bâtiments distincts (pas ST_Union)
    assert "ST_Union(ST_Intersection" not in SRC                   # l'union est retirée
    assert "contour cadastral 2975" not in SRC                     # plus d'EPSG en légende


# ── P6 — les lignes ne se coupent plus sur deux pages ────────────────────────────────────────

def test_page_css_keep_together():
    assert "page-break-inside: avoid" in SRC     # tr
    assert "page-break-after: avoid" in SRC      # titres (keep-with-next)


# ── bug racine corrigé (sinon la notice/fiche crashent) ─────────────────────────────────────

def test_iris_round_numeric_corrige():
    # round(double precision, int) n'existe pas en Postgres → cast ::numeric
    assert "::numeric, 1)  AS vacance_pct" in ZONE
    assert "round(100.0 * sum(i.logvac) / NULLIF(sum(i.log), 0), 1)" not in ZONE
