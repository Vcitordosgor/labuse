"""QV21-PROMO-1 — le contrôle d'écart de paliers compare des NOTIONS IDENTIQUES.

`tiers_client.canon_sql` projette tout tier STOCKÉ (ancien ou nouveau code) sur son palier canonique
AVANT de compter, exactement comme `code_palier`. On grave : (1) la dérivation depuis la source unique
`code_palier` ; (2) qu'un simple RENOMMAGE (reserve_fonciere → sans_signal, brulante → à suivre) ne
compte PLUS comme un changement de palier ; (3) qu'un VRAI changement (sans_signal ↔ écartée) compte
encore. La correction a fait tomber l'écart q_v21 mesuré de 35,5 % à 0,18 %.
"""
from __future__ import annotations

import sqlalchemy as sa

from labuse.scoring import tiers_client as TC


def test_canon_sql_derive_de_code_palier():
    """Pour CHAQUE code stocké connu, le CASE projette exactement comme `code_palier` (source unique)."""
    case = TC.canon_sql("tier")
    for code in {*TC.PALIERS_CLIENT, *TC.CORRESPONDANCE_LEGACY}:
        assert f"WHEN '{code}' THEN '{TC.code_palier(code)}'" in case


def _canon(engine, code):
    with engine.connect() as c:
        return c.execute(sa.text(f"SELECT {TC.canon_sql(':t')}").bindparams(t=code)).scalar()


def test_renommage_n_est_pas_un_changement():
    """Le cœur du mandat : d'anciens et de nouveaux codes qui DÉSIGNENT le même palier sont ÉGAUX
    après projection → plus de faux « écart de paliers » par vocabulaire."""
    eng = sa.create_engine("sqlite://")
    # réserve foncière (ancien) et « sans signal » (nouveau) = MÊME palier
    assert _canon(eng, "reserve_fonciere") == _canon(eng, "sans_signal") == "sans_signal"
    # à creuser / déclassements (anciens) → sans signal aussi
    assert _canon(eng, "a_creuser") == "sans_signal"
    assert _canon(eng, "declasse_non_constructible") == "sans_signal"
    # brûlante / chaude (anciens) et priorite / a_suivre (nouveaux) → « à suivre »
    #   (Priorité non servie, lot 2b : priorite se projette sur a_suivre)
    for c in ("brulante", "chaude", "priorite", "a_suivre"):
        assert _canon(eng, c) == "a_suivre", c
    # exclue (ancien) == ecartee (nouveau)
    assert _canon(eng, "exclue") == _canon(eng, "ecartee") == "ecartee"


def test_vrai_changement_reste_compte():
    """Un mouvement RÉEL de palier (sans signal ↔ écartée, à suivre ↔ sans signal) reste distinct."""
    eng = sa.create_engine("sqlite://")
    assert _canon(eng, "sans_signal") != _canon(eng, "ecartee")
    assert _canon(eng, "a_suivre") != _canon(eng, "sans_signal")


def test_code_inconnu_se_projette_sur_lui_meme():
    eng = sa.create_engine("sqlite://")
    assert _canon(eng, "zzz_inconnu") == "zzz_inconnu"
