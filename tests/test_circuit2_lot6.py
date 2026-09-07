"""CIRCUIT-2 lot 6 (mis à jour EXPORTS-2 lot 8) — les exports sur le registre : le BUILDER UNIQUE
`src/labuse/exports/` reçoit des objets `Valeur` (origine portée : run, millésimes, couverture,
état), le prix du neuf des PDF est l'OBSERVÉ (jamais l'id VEFA à l'acte réservé au scoring —
arbitrage Q3), les millésimes des sources sont LUS de la fiche (data_sources), jamais en dur."""
from __future__ import annotations

from pathlib import Path

import pytest

from labuse.registre.valeur import Valeur, valeurs_pour

pytestmark = pytest.mark.db

RACINE = Path(__file__).resolve().parents[1]

#: EXPORTS-2 lot 8 — les anciennes chaînes (briques_pdf, banquier, argumentaire, pdf_zone,
#: pdf_projet) sont éteintes. Tous les documents client (Dossier · Résumé · Financier · Apporteur ·
#: Pré-dossier PC · Flash) sont désormais servis par le BUILDER UNIQUE `src/labuse/exports/`.
BUILDERS = sorted(str(p.relative_to(RACINE))
                  for p in (RACINE / "src/labuse/exports").rglob("*.py")
                  if "__pycache__" not in p.parts)


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
    """EXPORTS-2 lot 8 : la collecte du builder unique n'assemble QUE des objets `Valeur`
    tamponnés (`valeurs_pour`) — les blocs ne reçoivent ni calcul ni requête, seulement des
    Valeur. La mise en page (blocs/*.py) lit ces Valeur, jamais la base."""
    collecte = (RACINE / "src/labuse/exports/collecte.py").read_text()
    assert "valeurs_pour" in collecte, "la collecte doit tamponner via le registre"
    assert "dict[str, Valeur]" in collecte, "la collecte rend {id → Valeur}, rien d'autre"


def test_sources_des_pdf_millesime_depuis_la_fiche():
    """EXPORTS-2 lot 8 : le bloc « Sources et millésimes » LIT les millésimes des sources
    réellement servies (data_sources de la fiche) — jamais une année en dur dans le builder."""
    src = (RACINE / "src/labuse/exports/blocs/sources.py").read_text()
    assert "s['millesime']" in src or 's["millesime"]' in src, "le millésime vient de la source servie"
    # aucune année ortho gravée dans le bloc
    import re
    assert not re.search(r"\b(19|20)\d{2}\b", src), "aucun millésime en dur dans le bloc Sources"
