"""CIRCUIT-2 lot 6 — les exports sur le registre : les builders PDF reçoivent des objets
`Valeur` (origine portée : run, millésimes, couverture, état), le prix du neuf des PDF est
l'OBSERVÉ (jamais l'id VEFA à l'acte réservé au scoring — arbitrage Q3), les cartes des PDF
lisent leur millésime de data_sources (jamais en dur)."""
from __future__ import annotations

from pathlib import Path

import pytest

from labuse.registre.valeur import Valeur, valeurs_pour

pytestmark = pytest.mark.db

RACINE = Path(__file__).resolve().parents[1]

#: tous les builders d'exports client (Dossier, banquier/Financier, argumentaire, Flash,
#: pré-dossier PC, étude de zone, premium)
BUILDERS = ["src/labuse/api/briques_pdf.py", "src/labuse/api/pdf_premium.py",
            "src/labuse/api/argumentaire.py", "src/labuse/api/pre_dossier.py",
            "src/labuse/api/pdf_zone.py", "src/labuse/flash/data.py",
            "src/labuse/flash/report.py", "src/labuse/api/banquier.py"]


def test_valeurs_pour_construit_des_valeurs_tamponnees(db_session):
    v = valeurs_pour(db_session,
                     {"prix_neuf_observe_eur_m2": 4730, "ventes_100m_n": 3},
                     couvertures={"ventes_100m_n": {"n": 3, "non_couvert": False}})
    assert set(v) == {"prix_neuf_observe_eur_m2", "ventes_100m_n"}
    neuf = v["prix_neuf_observe_eur_m2"]
    assert isinstance(neuf, Valeur) and neuf.valeur == 4730
    assert "dvf" in neuf.reservoirs, "le tampon porte les réservoirs (millésimes)"
    assert v["ventes_100m_n"].tampon()["couverture"] == {"n": 3, "non_couvert": False}


def test_valeurs_pour_jamais_une_valeur_inventee(db_session):
    """Un id non fourni ne reçoit RIEN (pas de Valeur creuse) ; un id inconnu est ignoré."""
    v = valeurs_pour(db_session, {"id_inconnu_xyz": 1})
    assert v == {}


def test_prix_neuf_des_pdf_jamais_l_acte():
    """Arbitrage Q3 (verrou code) : aucun builder d'export ne lit `neuf_vefa_commune` (l'acte,
    réservé au scoring) — le neuf des PDF vient de resolve_prix_sortie_servi (l'observé)."""
    for b in BUILDERS:
        src = (RACINE / b).read_text()
        assert "neuf_vefa_commune" not in src, f"{b} lit le VEFA à l'acte (réservé au scoring)"


def test_collectes_attachent_les_valeurs_registre():
    """Les deux collectes financières (briques Dossier/banquier + fiche premium) attachent
    `_valeurs_registre` (objets Valeur) — la mise en page reste inchangée."""
    briques = (RACINE / "src/labuse/api/briques_pdf.py").read_text()
    assert "_valeurs_registre" in briques and "valeurs_pour" in briques
    app = (RACINE / "src/labuse/api/app.py").read_text()
    assert app.count("_valeurs_registre") >= 2


def test_cartes_des_pdf_millesime_depuis_data_sources():
    """M73-F + lot 6 : le millésime ortho des cartes PDF est LU de data_sources (source
    unique), jamais une année en dur dans le builder."""
    app = (RACINE / "src/labuse/api/app.py").read_text()
    assert "SELECT source_millesime FROM data_sources WHERE name = 'BD ORTHO 20 cm (IGN)'" in app
