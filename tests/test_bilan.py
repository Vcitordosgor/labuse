"""Tests du bilan promoteur (PARTIE 1). Cœur pur, sans DB."""
from labuse.faisabilite.bilan import compute_bilan
from labuse.faisabilite.engine import Hypotheses

H = Hypotheses()


def _prix(q1, med, q3, n=40):
    return {"fiable": True, "n": n, "radius_m": 1500.0, "q1": q1, "median": med, "q3": q3}


def test_bilan_chiffre_et_fourchettes():
    b = compute_bilan(4600, 4500, _prix(2200, 3000, 4300), H)
    assert b.fiable
    assert b.ca["bas"] < b.ca["central"] < b.ca["haut"]
    # CA = surface × prix
    assert b.ca["central"] == round(4600 * 3000)
    assert b.charge_fonciere["bas"] <= b.charge_fonciere["haut"]
    assert any("chiffre d'affaires" in s.label.lower() for s in b.steps)
    assert any("charge foncière" in s.label.lower() for s in b.steps)


def test_charge_fonciere_a_rebours_formule():
    b = compute_bilan(1000, 1000, _prix(3000, 3000, 3000), H)
    # CA=3,0 M€ ; coef=1-0.18-0.12=0.70 ; coût central=1000*2000=2,0 M€
    # CF central = 3.0M*0.70 - 2.0M = 100 k€
    assert abs(b.charge_fonciere["central"] - 100_000) < 5_000


def test_dvf_trop_maigre_ne_chiffre_pas():
    b = compute_bilan(4600, 4500, {"fiable": False, "n": 3, "radius_m": 1500.0}, H)
    assert b.fiable is False
    assert "non fiable" in b.verdict.lower() and b.ca is None
    assert any("ventes comparables" in a.lower() for a in b.avertissements)


def test_charge_fonciere_negative_signalee():
    # prix bas + grande surface → CF basse négative
    b = compute_bilan(2000, 2000, _prix(1500, 1700, 1900), H)
    assert b.charge_fonciere["bas"] < 0
    assert any("négative" in a.lower() for a in b.avertissements)


def test_surface_vendable_nulle():
    b = compute_bilan(0, 1000, _prix(3000, 3000, 3000), H)
    assert b.fiable is False


def test_hypotheses_et_bandeau():
    b = compute_bilan(3000, 3000, _prix(2500, 3200, 4000), H)
    txt = " ".join(b.hypotheses).lower()
    assert "coût de construction" in txt and "marge" in txt and "dvf" in txt
    assert "ne remplace pas un bilan promoteur" in b.bandeau
