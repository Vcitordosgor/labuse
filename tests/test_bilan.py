"""Tests du bilan promoteur (PARTIE 1). Cœur pur, sans DB."""
from labuse.faisabilite.bilan import compute_bilan
from labuse.faisabilite.engine import Hypotheses

H = Hypotheses()


def _prix(q1, med, q3, n=40, fiabilite="fiable", raisons=None):
    """Fixture d'un prix DVF fiabilisé (contrat de sector_price)."""
    return {
        "fiable": fiabilite != "insuffisant", "fiabilite": fiabilite,
        "fiabilite_raisons": raisons or [], "type_prix": "appartement",
        "n": n, "n_exclus": 0, "n_doublons": 0, "radius_m": 1500.0,
        "commune_fallback": False, "pct_appartement": 100,
        "periode": [2018, 2021], "q1": q1, "median": med, "q3": q3,
        "min": round(q1 * 0.9), "max": round(q3 * 1.1),
    }


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
    b = compute_bilan(4600, 4500,
                      {"fiable": False, "fiabilite": "insuffisant", "n": 3, "radius_m": 1500.0}, H)
    assert b.fiable is False
    assert b.fiabilite == "insuffisant"
    assert b.ca is None
    assert "insuffisant" in b.verdict.lower()


def test_charge_fonciere_negative_signalee():
    # prix bas + grande surface → CF basse négative
    b = compute_bilan(2000, 2000, _prix(1500, 1700, 1900), H)
    assert b.charge_fonciere["bas"] < 0
    assert any("négative" in a.lower() for a in b.avertissements)


def test_surface_vendable_nulle():
    b = compute_bilan(0, 1000, _prix(3000, 3000, 3000), H)
    assert b.fiable is False


def test_prix_fragile_arrondi_et_simulation_indicative():
    # un prix « fragile » est chiffré mais arrondi (pas de fausse précision) et signalé.
    b = compute_bilan(1000, 1000, _prix(2980, 3030, 3080, fiabilite="fragile",
                                        raisons=["ventes anciennes (2021)"]), H)
    assert b.fiable is True
    assert b.fiabilite == "fragile"
    # montants arrondis à la centaine de milliers d'euros
    assert b.ca["central"] % 100_000 == 0
    assert "simulation indicative" in b.verdict.lower()
    assert any("fragile" in a.lower() for a in b.avertissements)


def test_hypotheses_et_bandeau():
    b = compute_bilan(3000, 3000, _prix(2500, 3200, 4000), H)
    txt = " ".join(b.hypotheses).lower()
    assert "coût de construction" in txt and "marge" in txt and "dvf" in txt
    assert "ne remplace pas un bilan promoteur" in b.bandeau
