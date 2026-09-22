"""SCORING-6 lot E — combinaison V3 lexicographique (tests PURS de l'ordre, sans base)."""
from labuse.scoring.score_labuse_combine import (BANDE_RANG, LigneScoreLabuse,
                                                 ordonner)


def _l(idu, bande, signal_p=None, sdp=0):
    return LigneScoreLabuse(
        run_label="t", parcel_id=hash(idu) % 10_000, idu=idu, commune="X",
        score=None, bande=bande, non_calculable=(bande == "NC"), cause=None,
        couverture_pct=100, couverture_manquantes=[], confiance_niveau="haute",
        confiance_notes=[], contributions=[], score_version="labuse_v1+x",
        signal_p=signal_p, signal_niveau=None, signal_version=None,
        cascade_exclue=False, cascade_motifs=[], sdp_residuelle_m2=sdp)


def test_bande_domine_le_signal():
    # V3 : une parcelle A à Signal NUL passe AVANT une parcelle D à Signal FORT.
    a = _l("A0", "A", signal_p=0.0)
    d = _l("D9", "D", signal_p=0.9)
    assert [x.idu for x in ordonner([d, a])] == ["A0", "D9"]


def test_signal_departage_dans_la_bande():
    haut = _l("B_haut", "B", signal_p=0.30)
    bas = _l("B_bas", "B", signal_p=0.05)
    assert [x.idu for x in ordonner([bas, haut])] == ["B_haut", "B_bas"]


def test_nc_en_dernier():
    ordre = [x.bande for x in ordonner([_l("n", "NC"), _l("d", "D"), _l("a", "A")])]
    assert ordre == ["A", "D", "NC"]


def test_ties_departages_par_sdp_puis_idu():
    # même bande, même signal → SDP décroissante, puis IDU croissant (déterminisme).
    g = _l("zzz", "B", signal_p=0.1, sdp=2000)
    p = _l("aaa", "B", signal_p=0.1, sdp=500)
    e1 = _l("mmm", "B", signal_p=0.1, sdp=500)
    ordre = [x.idu for x in ordonner([e1, p, g])]
    assert ordre == ["zzz", "aaa", "mmm"]   # sdp 2000 d'abord, puis idu aaa < mmm


def test_signal_absent_ne_remonte_pas():
    # Signal None (non couvert) traité comme le plus bas dans la bande.
    avec = _l("avec", "B", signal_p=0.15)
    sans = _l("sans", "B", signal_p=None)
    assert [x.idu for x in ordonner([sans, avec])] == ["avec", "sans"]


def test_bande_rang_ordonne():
    assert BANDE_RANG["A"] < BANDE_RANG["B"] < BANDE_RANG["C"] < BANDE_RANG["D"] < BANDE_RANG["NC"]


def test_ordre_total_deterministe():
    lignes = [_l("A1", "A", 0.1), _l("A2", "A", 0.3), _l("C1", "C", 0.9),
              _l("B1", "B", 0.0), _l("NC1", "NC"), _l("D1", "D", 0.5)]
    idus = [x.idu for x in ordonner(lignes)]
    assert idus == ["A2", "A1", "B1", "C1", "D1", "NC1"]
    # rejouer = même ordre (aucun aléa, aucun percentile).
    assert idus == [x.idu for x in ordonner(list(reversed(lignes)))]
