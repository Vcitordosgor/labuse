"""PLU-CALIBRAGE-1 lot 4 — V6a : aucune règle chiffrée VALIDÉE sans article + page + citation.
Preuve cassé → vert. Les `propose` sont libres (ils attendent la revue) ; seuls les `valide`
doivent porter leur source complète."""
from __future__ import annotations

import pytest

from labuse import circuit_verrous as CV
from labuse.plu import destinations as D

pytestmark = pytest.mark.verrous


def test_v6a_vert_sur_le_registre_reel():
    """Le registre réel passe : toute règle `valide` porte article + page_pdf + citation
    (les `propose` de l'agent ne sont pas concernés)."""
    r = CV.verrou_regles_citations()
    assert r.verdict == "ok", r.details[:10]


def test_v6a_prouve_casse_sur_une_regle_valide_sans_citation(monkeypatch):
    """Une feuille au statut `valide` sans citation (ni article, ni page) casse le verrou, et le
    détail NOMME la règle fautive — jamais une valeur validée sans preuve."""
    def _faux_iter():
        yield {"insee": "97411", "zone": "Ud", "chemin": "hauteur.faitage",
               "statut": "valide", "m": 15, "article": "", "page_pdf": None, "citation": ""}
        yield {"insee": "97411", "zone": "Ud", "chemin": "emprise_sol.ces",
               "statut": "propose", "pct": 60}  # propose incomplet : IGNORÉ par V6a
    monkeypatch.setattr(D, "iter_regles_calibrees", _faux_iter)
    r = CV.verrou_regles_citations()
    assert r.verdict == "casse"
    assert any("hauteur.faitage" in d for d in r.details)
    assert not any("emprise_sol.ces" in d for d in r.details)  # le propose n'est pas jugé


def test_v6a_valide_complet_passe(monkeypatch):
    """Une feuille `valide` avec article + page + citation passe."""
    def _faux_iter():
        yield {"insee": "97411", "zone": "Ud", "chemin": "hauteur.faitage", "statut": "valide",
               "m": 15, "article": "Ud 10", "page_pdf": 45, "citation": "« 15 m au faîtage »"}
    monkeypatch.setattr(D, "iter_regles_calibrees", _faux_iter)
    r = CV.verrou_regles_citations()
    assert r.verdict == "ok"
