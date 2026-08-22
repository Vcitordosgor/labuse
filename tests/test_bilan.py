"""Tests du bilan promoteur (PARTIE 1). Cœur pur, sans DB."""
from labuse.faisabilite.bilan import _comparables, compute_bilan, compute_calculette
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
    # 10 VEFA à 5000, 10 ancien à 3800 : médianes séparées + écart exploitable.
    c = _comparables(_kept(10, 10), min_n=8, fiabilite="fiable")
    assert c["n_vefa"] == 10 and c["n_ancien"] == 10
    assert c["mediane_vefa"] == 5000 and c["mediane_ancien"] == 3800
    assert c["ecart_vefa_ancien_pct"] == round(100 * (5000 / 3800 - 1)) and c["exploitable"] is True
    assert c["note"] is None and c["fiabilite_prix"] == "fiable"


def test_comparables_vefa_insuffisant_pas_de_faux_ecart():
    # 3 VEFA seulement → pas de médiane VEFA, pas d'écart, note explicite.
    c = _comparables(_kept(3, 20), min_n=8, fiabilite="fiable")
    assert c["mediane_vefa"] is None and c["ecart_vefa_ancien_pct"] is None and c["exploitable"] is False
    assert "vefa insuffisant" in c["note"].lower()
    assert c["mediane_ancien"] == 3800            # l'ancien reste affiché


def test_comparables_sans_vefa_affiche_seulement_ancien():
    c = _comparables(_kept(0, 15), min_n=8, fiabilite="fragile")
    assert c["n_vefa"] == 0 and c["mediane_vefa"] is None and c["exploitable"] is False
    assert "aucune vente vefa" in c["note"].lower()
    assert c["mediane_ancien"] == 3800 and c["fiabilite_prix"] == "fragile"


def test_charge_fonciere_a_rebours_formule():
    b = compute_bilan(1000, 1000, _prix(3000, 3000, 3000), H)
    # M128-3-§1 (2026-08) : la SDP coûtée = vendable ÷ coef_rendement (SOURCE UNIQUE, partagée avec
    # la faisabilité) — PLUS de « × coef_plancher_habitable » (1,15) en dur. Le coût porte sur le
    # plancher qui produit le vendable effectivement valorisé. CA = 3,0 M€ ; coef = 1 − marge −
    # frais annexes (frais financiers = 0 par défaut). Le « central » reste le chiffre VRAI.
    coef = 1 - H.marge_promoteur_pct - H.frais_annexes_pct
    sdp = 1000 / H.coef_rendement
    cout_central = sdp * (H.cout_construction_m2_bas + H.cout_construction_m2_haut) / 2
    attendu = 3_000_000 * coef - cout_central
    assert abs(b.charge_fonciere["central"] - attendu) < 5_000


def test_dvf_trop_maigre_ne_chiffre_pas():
    b = compute_bilan(4600, 4500,
                      {"fiable": False, "fiabilite": "insuffisant", "n": 3, "radius_m": 1500.0}, H)
    assert b.fiable is False
    assert b.fiabilite == "insuffisant"
    assert b.ca is None
    assert "insuffisant" in b.verdict.lower()


def test_charge_fonciere_negative_signalee():
    # M128-2-D2(a) (2026-08) : la borne basse est désormais AFFICHÉE RÉELLE (négative), plus
    # d'écrêtage muet à 0 (le « 0 » masquait une charge infaisable). L'avertissement « négative »
    # est toujours émis (l'information reste visible).
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
    # M128-A1 (2026-08) : un prix fragile est arrondi au k€ — PLUS aux 100 k€ (qui écrasaient une
    # charge ~40 k€ à « 0 € », bandeau contredisant le texte). Le k€ tue la fausse précision sans mentir.
    assert b.ca["central"] % 1_000 == 0
    assert "simulation indicative" in b.verdict.lower()
    assert any("fragile" in a.lower() for a in b.avertissements)


def test_hypotheses_et_bandeau():
    b = compute_bilan(3000, 3000, _prix(2500, 3200, 4000), H)
    txt = " ".join(b.hypotheses).lower()
    assert "coût de construction" in txt and "marge" in txt and "dvf" in txt
    assert "ne remplace pas un bilan promoteur" in b.bandeau


# ── CALCULETTE DE CHARGE FONCIÈRE (mandat bilan-calculette) — arithmétique isolée ──────────

def test_calculette_arithmetique_independante():
    """Vérifie L'ARITHMÉTIQUE en isolation : entrées connues → charge foncière attendue.
    shab 6344 m², terrain 9723 m², prix médian 5310 €/m², coût 2500 €/m² SDP, marge+frais 21 %.
    CA médian = 6344×5310 ; coef = 1−0,21 ; M128-3-§1 : SDP = vendable ÷ coef_rendement (plus de
    ×1,15) ; construction = SDP×2500 ; CF médiane = CA×coef − construction (VRD nulle hors secteur)."""
    prix = _prix(5310, 5310, 5310, n=14)
    res = compute_calculette(6344, 9723, prix, cout_construction_m2=2500, marge_frais_pct=21)
    assert res["calculable"] is True
    ca = 6344 * 5310
    coef = 1 - 21 / 100
    construction = 6344 / H.coef_rendement * 2500   # M128-3 : SDP = vendable ÷ rendement
    attendu = ca * coef - construction
    assert res["ca"]["central"] == round(ca)
    assert abs(res["charge_fonciere"]["central"] - attendu) < 2          # arrondi à l'euro
    assert res["charge_fonciere"]["par_m2_terrain"] == round(attendu / 9723)


def test_calculette_hypotheses_utilisateur_pilotent():
    """Les saisies du promoteur CHANGENT le résultat (jamais figées) : coût ↑ → charge ↓."""
    prix = _prix(5000, 5000, 5000)
    bas_cout = compute_calculette(2000, 2000, prix, cout_construction_m2=2000, marge_frais_pct=20)
    haut_cout = compute_calculette(2000, 2000, prix, cout_construction_m2=3500, marge_frais_pct=20)
    assert haut_cout["charge_fonciere"]["central"] < bas_cout["charge_fonciere"]["central"]
    # marge ↑ → charge ↓
    plus_marge = compute_calculette(2000, 2000, prix, cout_construction_m2=2000, marge_frais_pct=35)
    assert plus_marge["charge_fonciere"]["central"] < bas_cout["charge_fonciere"]["central"]


def test_calculette_verdict_achat():
    """Prix demandé → verdict supportable / trop cher (charge foncière médiane vs prix)."""
    prix = _prix(5310, 5310, 5310, n=14)
    res = compute_calculette(6344, 9723, prix, 2500, 21, prix_demande_eur=3_000_000)
    assert res["achat"]["supportable"] is True and res["achat"]["ecart_eur"] > 0
    cher = compute_calculette(6344, 9723, prix, 2500, 21, prix_demande_eur=20_000_000)
    assert cher["achat"]["supportable"] is False and cher["achat"]["ecart_eur"] < 0


def test_calculette_cas_limite_prix_insuffisant():
    """Prix DVF insuffisant → PAS de faux chiffre (calculable=false), prix secteur au mieux."""
    prix = {"fiable": False, "fiabilite": "insuffisant", "n": 3, "median": None, "radius_m": 1500.0}
    res = compute_calculette(4600, 4500, prix, 2500, 21)
    assert res["calculable"] is False and res.get("charge_fonciere") is None
    assert "marche" in res


def test_calculette_fiabilite_heritee():
    """Le résultat HÉRITE de la fiabilité du prix (prix fragile → résultat fragile)."""
    prix = _prix(2980, 3030, 3080, fiabilite="fragile", raisons=["ventes anciennes (2021)"])
    res = compute_calculette(1000, 1000, prix, 2500, 21)
    assert res["fiabilite"] == "fragile"


# ── M22-A · MODE INVERSE — prix d'achat max admissible ─────────────────────────────────────

def test_achat_max_identite_arithmetique_forward_inverse():
    """COHÉRENCE forward/inverse : mêmes hypothèses → mêmes totaux. Le prix d'achat max EST la
    charge foncière supportable (identité, pas un second moteur) — bas/central/haut/€ par m²."""
    prix = _prix(5310, 5310, 5310, n=14)
    fwd = compute_calculette(6344, 9723, prix, 2500, 21)
    inv = compute_calculette(6344, 9723, prix, 2500, 21, mode="achat_max")
    assert inv["mode"] == "achat_max"
    assert inv["prix_achat_max"] == fwd["charge_fonciere"]
    # le mode inverse n'altère RIEN du sens forward (non-régression fiche M19/M20)
    assert inv["charge_fonciere"] == fwd["charge_fonciere"] and inv["ca"] == fwd["ca"]


def test_achat_max_derivation_ligne_a_ligne():
    """La dérivation est tracée ligne à ligne (prix de sortie → CA → marge & frais →
    construction → prix d'achat max), chaque terme avec sa provenance."""
    prix = _prix(5310, 5310, 5310, n=14)
    res = compute_calculette(6344, 9723, prix, 2500, 21, mode="achat_max")
    labels = [st["label"] for st in res["steps"]]
    assert labels[-1] == "Prix d'achat maximal admissible"
    txt = " ".join(labels).lower()
    assert "prix de vente" in txt and "chiffre d'affaires" in txt and "coût de construction" in txt
    assert all(st.get("prov") in ("sourcee", "estimee", "derive") for st in res["steps"])
    # pas de step en mode forward (réponse historique inchangée)
    assert "steps" not in compute_calculette(6344, 9723, prix, 2500, 21)


def test_achat_max_ecart_negociation_sens_demande_moins_max():
    """L'écart de négociation est demandé − max (+ = surcoût, − = marge) — LE chiffre
    de la contre-offre, jamais ambigu (le champ porte son sens)."""
    prix = _prix(5310, 5310, 5310, n=14)
    cher = compute_calculette(6344, 9723, prix, 2500, 21,
                              prix_demande_eur=20_000_000, mode="achat_max")
    e = cher["ecart_negociation"]
    assert e["sens"] == "surcout" and e["demande_moins_max_eur"] > 0
    assert e["demande_moins_max_eur"] == 20_000_000 - e["prix_achat_max_eur"]
    ok = compute_calculette(6344, 9723, prix, 2500, 21,
                            prix_demande_eur=3_000_000, mode="achat_max")
    assert ok["ecart_negociation"]["sens"] == "marge"
    assert ok["ecart_negociation"]["demande_moins_max_eur"] < 0


def test_achat_max_prix_insuffisant_pas_de_faux_chiffre():
    """Prix DVF insuffisant → PAS de prix d'achat max fabriqué (doctrine inchangée en inverse)."""
    prix = {"fiable": False, "fiabilite": "insuffisant", "n": 3, "median": None, "radius_m": 1500.0}
    res = compute_calculette(4600, 4500, prix, 2500, 21, mode="achat_max")
    assert res["calculable"] is False and res.get("prix_achat_max") is None


# ── M22-F C1 · UNE SEULE SOURCE D'HYPOTHÈSES (cohérence inter-documents) ───────────────────

def test_c1_banquier_et_calculette_memes_totaux():
    """Le bilan du Dossier banquier (compute_bilan + bilan_params_defaut) et la calculette
    (défauts) DOIVENT porter les mêmes totaux intermédiaires : CA, charge foncière, €/m²."""
    from labuse.faisabilite.bilan import (bilan_params_defaut, CALCULETTE_COUT_DEFAUT_M2,
                                          CALCULETTE_MARGE_FRAIS_DEFAUT_PCT)
    prix = _prix(5310, 5310, 5310, n=14)
    banquier = compute_bilan(6344, 9723, prix, H, bilan_params=bilan_params_defaut())
    calculette = compute_calculette(6344, 9723, prix,
                                    CALCULETTE_COUT_DEFAUT_M2, CALCULETTE_MARGE_FRAIS_DEFAUT_PCT)
    assert banquier.ca == calculette["ca"]
    assert banquier.charge_fonciere == calculette["charge_fonciere"]


def test_c1_encadre_hypotheses_identique_en_forme():
    """L'encadré « Hypothèses de calcul » est LA MÊME brique dans tous les documents —
    à hypothèses égales, HTML strictement identique."""
    from labuse.api.briques_pdf import hypotheses_encadre
    assert hypotheses_encadre(2500, 21) == hypotheses_encadre(2500.0, 21.0)
    html = hypotheses_encadre(2500, 21)
    assert "Hypothèses de calcul" in html and "2500" in html and "21" in html
