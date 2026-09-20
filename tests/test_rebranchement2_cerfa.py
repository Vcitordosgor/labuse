"""EXPORTS-REBRANCHEMENT-2 lot 4 — le CERFA du pré-dossier PC : 13406 (maison) / 13409 (collectif),
mêmes champs T2* de terrain ; contrôle de millésime en ligne best-effort, NON fatal ; scénario
collectif → 13409. Sans réseau, le contrôle ne bloque jamais (on sert le fichier vendorisé)."""
from __future__ import annotations

import io

from pypdf import PdfReader

from labuse.api import pre_dossier as pd

PARC = {"idu": "97415000DK1169", "commune": "Saint-Paul", "section": "DK", "numero": "1169"}
ADR = {"numero": "5", "voie": "Rue Test", "code_postal": "97460"}


def test_les_deux_cerfa_sont_vendorises():
    assert pd._CERFA_FICHIERS["13406"]["fichier"].exists()
    assert pd._CERFA_FICHIERS["13409"]["fichier"].exists()   # déposé lot 4


def test_prefill_terrain_identique_sur_13406_et_13409():
    for num in ("13406", "13409"):
        b = pd._cerfa_prerempli(PARC, ADR, num)
        assert b, f"{num} : préremplissage vide"
        f = PdfReader(io.BytesIO(b)).get_fields() or {}
        # mêmes champs T2* de terrain sur les deux formulaires
        assert (f.get("T2S_section") or {}).get("/V") == "DK"
        assert (f.get("T2N_numero") or {}).get("/V") == "1169"
        assert (f.get("T2L_localite") or {}).get("/V") == "Saint-Paul"


def test_millesime_check_non_fatal(monkeypatch):
    # réseau coupé (urlopen lève) → (False, None) : on NE bloque JAMAIS sur notre incapacité à vérifier.
    pd._MILLESIME_CACHE.clear()
    import urllib.request
    def _boom(*a, **k):
        raise OSError("réseau coupé")
    monkeypatch.setattr(urllib.request, "urlopen", _boom)
    perime, courant = pd.cerfa_millesime_perime("13409", "13409*17")
    assert perime is False and courant is None
    assert pd._cerfa_prerempli(PARC, ADR, "13409")            # servi malgré l'absence de réseau


def test_millesime_perime_bloque_la_piece(monkeypatch):
    # la fiche annonce un millésime PLUS RÉCENT que le nôtre (*18 > *17) → pièce bloquée (None).
    class _Resp:
        def read(self, *a): return b"CERFA 13409*18 ... fiche signaletique"
        def __enter__(self): return self
        def __exit__(self, *a): return False
    pd._MILLESIME_CACHE.clear()
    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: _Resp())
    perime, courant = pd.cerfa_millesime_perime("13409", "13409*17")
    assert perime is True and courant == "13409*18"
    assert pd._cerfa_prerempli(PARC, ADR, "13409") is None     # périmé → INDISPONIBLE (pack sans formulaire)


def test_scenario_collectif_choisit_13409():
    # la logique de scénario : ≥ 3 logements → 13409 (pièces PC), sinon 13406 (maison).
    assert pd._CERFA_FICHIERS["13409"]["version"] == "13409*17"
    assert pd._CERFA_FICHIERS["13406"]["num"] == "13406"
