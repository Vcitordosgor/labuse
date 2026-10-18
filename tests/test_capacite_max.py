"""FIX-PRIX-ET-OPPORTUNITES lot 3 — la capacité constructible est présentée comme un MAXIMUM
réglementaire, avec une mention mesurée (volet D : les permis réels en utilisent ~½ en médiane)."""
from __future__ import annotations

from pathlib import Path

from labuse import capacite_max

RACINE = Path(__file__).resolve().parents[1]


def _lire(rel: str) -> str:
    return (RACINE / rel).read_text()


def test_mention_cite_la_mesure_du_volet_d():
    assert capacite_max.RATIO_MEDIAN_SDP == 0.46
    assert capacite_max.RATIO_MEDIAN_LOGEMENTS == 0.40
    assert "0,46" in capacite_max.MENTION and "0,40" in capacite_max.MENTION
    assert "maximum" in capacite_max.MENTION.lower()
    assert "volet D" in capacite_max.MENTION
    assert "½" in capacite_max.MENTION_COURTE and "maximum" in capacite_max.MENTION_COURTE.lower()


def test_exports_portent_la_mention_capacite():
    for rel in ("src/labuse/exports/blocs/financier.py",
                "src/labuse/exports/blocs/comparatif.py",
                "src/labuse/exports/blocs/potentiel.py"):
        assert "capacite_max" in _lire(rel), rel
    # libellés « maximum » posés
    assert "Surface de plancher (maximum)" in _lire("src/labuse/exports/blocs/financier.py")
    assert "Logements (maximum)" in _lire("src/labuse/exports/blocs/financier.py")
    assert "Logements possibles (max.)" in _lire("src/labuse/exports/blocs/comparatif.py")


def test_fiche_et_gabarit_portent_la_mention():
    assert "capaciteMax" in _lire("frontend/src/components/fiche/constructibilite.tsx")
    assert "SDP max" in _lire("frontend/src/components/fiche/constructibilite.tsx")
    assert "capaciteMax" in _lire("frontend/src/components/outils/Gabarit.tsx")
    assert "capaciteMax" in _lire("frontend/src/components/compare/ComparePanel.tsx")


def test_copilote_porte_la_mention_sur_la_capacite():
    assert "capacite_max" in _lire("src/labuse/copilote_v2/resume_fiche.py")
