"""Tests du bilan promoteur (PARTIE 1). Cœur pur, sans DB."""
from labuse.faisabilite.bilan import _comparables, compute_bilan
from labuse.faisabilite.engine import Hypotheses

H = Hypotheses()


def _kept(n_vefa, n_ancien, prix_vefa=5000.0, prix_ancien=3800.0):
    return ([{"prix": prix_vefa, "vefa": True}] * n_vefa
            + [{"prix": prix_ancien, "vefa": False}] * n_ancien)


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
    # vocabulaire : même un prix fiable donne une SIMULATION indicative (bilon ≠ fiable)
    assert "simulation indicative" in b.verdict.lower()
    assert "prix de sortie fiable" in b.verdict.lower()


def test_comparables_neuf_vs_ancien_exploitable():
    # 10 VEFA à 5000, 10 ancien à 3800 : médianes séparées + écart +32 %.
    c = _comparables(_kept(10, 10), min_n=8)
    assert c["n_vefa"] == 10 and c["n_ancien"] == 10
    assert c["median_vefa"] == 5000 and c["median_ancien"] == 3800
    assert c["ecart_pct"] == round(100 * (5000 / 3800 - 1)) and c["ecart_exploitable"] is True
    assert c["note"] is None


def test_comparables_vefa_insuffisant_pas_de_faux_ecart():
    # 3 VEFA seulement → pas de médiane VEFA, pas d'écart, note explicite.
    c = _comparables(_kept(3, 20), min_n=8)
    assert c["median_vefa"] is None and c["ecart_pct"] is None and c["ecart_exploitable"] is False
    assert "vefa insuffisant" in c["note"].lower()
    assert c["median_ancien"] == 3800            # l'ancien reste affiché


def test_comparables_sans_vefa_affiche_seulement_ancien():
    c = _comparables(_kept(0, 15), min_n=8)
    assert c["n_vefa"] == 0 and c["median_vefa"] is None and c["ecart_exploitable"] is False
    assert "aucune vente vefa" in c["note"].lower()
    assert c["median_ancien"] == 3800


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
