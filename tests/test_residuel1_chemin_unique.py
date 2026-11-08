"""RESIDUEL-1 (décision Vic 08/11/2026) — UN SEUL chemin de calcul du résiduel.

Avant : le run de nuit (`compute_residuel_batch`) appelait `parcel_faisabilite(assiette_clippee=False)`
— la branche héritée SANS découpe de la zone rouge PPR — tandis que la fiche en ligne appelait le
même moteur en assiette CLIPPÉE. Deux chemins, deux verdicts : une parcelle en zone U partiellement
touchée par une zone rouge PPR était fermée « rédhibitoire » au run (SDP 0, exclue du tri « À
construire ») alors que la fiche la disait constructible sur sa partie hors rouge.

Ce fichier verrouille la réparation :
  1. le flag a disparu partout (moteur + CLI) — aucune variante non clippée ne peut réapparaître ;
  2. sur les quatre témoins (DH0076, AK0804, BZ1065, AB0133), le calcul « batch » (qui résout la
     faisabilité lui-même) et le calcul « fiche » (qui lui passe la faisabilité déjà calculée) rendent
     EXACTEMENT le même verdict, la même SDP et la même emprise — base réelle (`reel`) ;
  3. la réconciliation à la lecture posée par DOCS-1 (`verdict_ppr_partiel` / `_override_ppr_partiel`)
     ne change plus un verdict quand le résiduel est FRAIS : dès que la cause stockée est NULL
     (run clippé), le lecteur `potentiel_batir` sert le run tel quel, sans override PPR-partiel.
"""
from __future__ import annotations

import inspect
import os

import pytest
from sqlalchemy import text


# ── 1. Verrou de structure (sans base) — le flag a disparu, un seul chemin ───────────────────────
def test_aucune_variante_non_clippee_ne_subsiste():
    from labuse.faisabilite import db, residuel
    cli_mod = __import__("labuse.cli", fromlist=["compute_residuel_cmd"])
    surfaces = {
        "parcel_faisabilite": db.parcel_faisabilite,
        "compute_residuel": residuel.compute_residuel,
        "compute_residuel_batch": residuel.compute_residuel_batch,
        "compute-residuel (CLI)": cli_mod.compute_residuel_cmd,
    }
    for nom, fn in surfaces.items():
        assert "assiette_clippee" not in inspect.signature(fn).parameters, nom


# ── 2. Témoins — batch ≡ fiche (base réelle) ─────────────────────────────────────────────────────
# Les quatre parcelles du banc DOCS-1. DH0076 = zone U partiellement rouge PPR (le cas qui flippait) ;
# AK0804 = UB nue ; BZ1065 = Uh bâtie (PPR bleu) ; AB0133 = zone N (non constructible, garde-fou).
_TEMOINS = ["97415000DH0076", "97409000AK0804", "97411000BZ1065", "97421000AB0133"]


@pytest.fixture(scope="module")
def session_reelle():
    from sqlalchemy.orm import sessionmaker

    from labuse.db import make_engine
    url = os.environ.get("LABUSE_APP_DATABASE_URL")
    if not url:
        pytest.skip("LABUSE_APP_DATABASE_URL absent (base applicative non définie)")
    s = sessionmaker(bind=make_engine(url=url), future=True)()
    yield s
    s.close()


def _cle(d: dict) -> tuple:
    """La signature comparable d'un résiduel : (disponible, cause, SDP résiduelle, SDP écrite,
    emprise constructible). Ce que le run STOCKE et ce que la fiche MONTRE doivent coïncider."""
    return (d.get("disponible"), d.get("cause"), d.get("sdp_residuelle_m2"),
            d.get("sdp_ecrite"), d.get("emprise_constructible_m2"))


@pytest.mark.reel
@pytest.mark.parametrize("idu", _TEMOINS)
def test_batch_egale_fiche_sur_les_temoins(session_reelle, idu):
    from labuse.faisabilite.db import parcel_faisabilite
    from labuse.faisabilite.residuel import compute_residuel
    s = session_reelle
    pid = s.execute(text("SELECT id FROM parcels WHERE idu = :i"), {"i": idu}).scalar()
    if pid is None:
        pytest.skip(f"témoin {idu} absent de la base")
    # Chemin « batch » : compute_residuel résout lui-même parcel_faisabilite (comme le run de nuit).
    batch = compute_residuel(s, pid)
    # Chemin « fiche » : on lui passe la faisabilité déjà calculée (comme fiche_payload en ligne).
    fiche = compute_residuel(s, pid, faisa=parcel_faisabilite(s, pid))
    assert _cle(batch) == _cle(fiche), f"{idu} : batch {_cle(batch)} ≠ fiche {_cle(fiche)}"


@pytest.mark.reel
def test_dh0076_constructible_hors_rouge_au_run(session_reelle):
    """Le cas qui flippait : DH0076 (zone U, 2 % rouge PPR) n'est PLUS fermé « rédhibitoire » par le
    calcul frais — il reçoit la capacité de sa partie hors rouge (cause NULL, SDP > 0)."""
    from labuse.faisabilite.residuel import compute_residuel
    s = session_reelle
    pid = s.execute(text("SELECT id FROM parcels WHERE idu = '97415000DH0076'")).scalar()
    if pid is None:
        pytest.skip("témoin DH0076 absent de la base")
    r = compute_residuel(s, pid)
    assert r.get("disponible") is True and r.get("cause") is None
    assert (r.get("sdp_residuelle_m2") or 0) > 0


# ── 3. La réconciliation DOCS-1 ne change plus un verdict frais ───────────────────────────────────
def test_reconciliation_ppr_partiel_no_op_sur_run_frais(monkeypatch):
    """Garde-fou, pas moteur : quand le run est FRAIS (cause NULL), `potentiel_batir` sert le run tel
    quel et n'appelle JAMAIS la correction PPR-partiel. On le prouve en rendant `verdict_ppr_partiel`
    explosif : s'il était appelé sur une parcelle à cause NULL, le test tomberait."""
    from labuse.faisabilite import potentiel_batir as pb

    def _bombe(*a, **k):  # ne doit jamais être atteint pour un run frais
        raise AssertionError("verdict_ppr_partiel appelé alors que le run est frais (cause NULL)")

    monkeypatch.setattr("labuse.faisabilite.db.verdict_ppr_partiel", _bombe)

    # Run FRAIS : la parcelle en zone U porte une SDP résiduelle et AUCUNE cause → constructible net.
    info = pb._assemble(sdp_raw=26258, cause=None, constr_label=None, au_classe=None,
                        zone_fam="U", zone_lib="Uh")
    assert info["constructible"] is True and info["rien_a_batir"] is False
    assert "ppr_partiel" not in info                      # pas d'override : le run frais se suffit
    assert info["sdp_restante_m2"] == 26258


def test_reconciliation_ppr_partiel_arme_quand_run_perime(monkeypatch):
    """Symétrie : tant qu'un run PÉRIMÉ ferme la parcelle (cause = 'redhibitoire'), la correction DOCS-1
    reste disponible (elle rattrape l'incohérence à la lecture). C'est le filet, pas la règle — une
    fois le run recalculé (test ci-dessus), il ne se déclenche plus."""
    from labuse.faisabilite import potentiel_batir as pb
    appels = {"n": 0}

    def _verdict(db, pid):
        appels["n"] += 1
        return {"pct_rouge": 2, "pct_hors_rouge": 98, "hors_rouge_m2": 17000}

    monkeypatch.setattr("labuse.faisabilite.db.verdict_ppr_partiel", _verdict)

    class _FakeDB:
        def execute(self, *a, **k):
            class _R:
                def mappings(self_inner):
                    return self_inner
                def all(self_inner):
                    return [{"idu": "X", "pid": 1, "sdp_raw": 0, "resid_cause": "redhibitoire",
                             "constr_label": None, "au_classe": None,
                             "zone_fam": "U", "zone_lib": "Uh"}]
            return _R()

    out = pb.potentiel_batir_batch(_FakeDB(), ["X"])["X"]
    assert appels["n"] == 1                               # run périmé → la correction est consultée
    assert out.get("ppr_partiel") and out["constructible"] is True
