"""M22-C — ARGUMENTAIRE DE NÉGOCIATION : garde-fous de doctrine (sans réseau ni DB).

Décisions Vic testées :
 · le raisonnement passe par la charge foncière supportable — le mot « décote »
   n'apparaît JAMAIS appliqué au prix affiché ;
 · les points de vigilance sont qualitatifs : AUCUN montant en euros dans la section ;
 · non chiffrable → dit tel quel, jamais un chiffre fabriqué ;
 · ton montrable au vendeur : formulation neutre (« pour tout acquéreur »).
"""
from __future__ import annotations

from types import SimpleNamespace as NS

from labuse.api import argumentaire as ag


def _out(calculable=True, prix_demande=True):
    fais = NS(zone="AU", zone_resolue="AU2c", steps=[], hypotheses=[],
              avertissements=[], modulation=["Pente 18% → surcoût, capacité réduite (~×0,7)."],
              fourchette={"shab_vendable_m2": 2135}, bandeau="Pré-faisabilité indicative.")
    calc = {"calculable": False, "raison": "capacité non résolue"}
    if calculable:
        calc = {"calculable": True, "mode": "achat_max",
                "prix_achat_max": {"bas": 2800000, "central": 3217723, "haut": 4700000,
                                   "par_m2_terrain": 459},
                "steps": [{"label": "Chiffre d'affaires potentiel", "formule": "surf × prix",
                           "valeur": "~11,8 M€", "source": "dérivé", "prov": "derive"}],
                "avertissements": []}
        if prix_demande:
            calc["ecart_negociation"] = {"prix_demande_eur": 4000000, "prix_achat_max_eur": 3217723,
                                         "demande_moins_max_eur": 782277, "demande_moins_max_pct": 20,
                                         "sens": "surcout"}
    return {
        "parcelle": {"idu": "97415000ET1659", "commune": "Saint-Paul", "section": "ET",
                     "numero": "1659", "surface_m2": 7013, "geojson": "{}"},
        "rapport": {"risques": {"couches": [{"label": "Aléa inondation", "detail": "moyen"}]},
                    "patrimoine": {"couches": [], "abf": []},
                    "sources": [{"section": "marche", "source": "DVF", "millesime": "2026"}]},
        "faisabilite": fais, "prix_dvf": {"median": 5547, "n": 14, "fiabilite": "fiable"},
        "calc": calc, "hyp_saisies": {"cout_m2": 2500.0, "marge_pct": 21.0},
        "viab": {"score": 62, "band": "probable", "libelle": "Viabilisation probable",
                 "cout_raccordement": {"niveau": "Raccordement PROBABLE au coût standard.",
                                       "assainissement": "Zonage assainissement non disponible.",
                                       "disclaimer": "Estimation qualitative."}},
    }


def test_jamais_le_mot_decote():
    out = _out()
    doc = "".join([ag._synthese(out), ag._reductions(out), ag._bilan_rebours(out),
                   ag._vigilance(out), ag._sources(out)])
    assert "décote" not in doc.lower() and "decote" not in doc.lower()


def test_reductions_presentees_en_capacite_jamais_en_prix():
    html = ag._reductions(_out())
    assert "capacité" in html.lower() and "Pente 18%" in html
    assert "prix affiché" in html            # la doctrine est ÉNONCÉE dans le document


def test_vigilance_sans_aucun_euro():
    html = ag._vigilance(_out())
    assert "€" not in html                   # doctrine : jamais d'euros en vigilance
    assert "62/100" in html and "tout acquéreur" in html.lower()


def test_synthese_ecart_en_clair_ton_factuel():
    html = ag._synthese(_out())
    assert "3,22 M€" in html and "+20 %" in html
    assert "contre-proposition" in html
    # jamais dénigrant : pas de vocabulaire à charge
    for mot in ("surévalué", "irréaliste", "abusif"):
        assert mot not in html.lower()


def test_synthese_sans_prix_demande():
    html = ag._synthese(_out(prix_demande=False))
    assert "charge foncière supportable" in html and "Prix demandé" not in html


def test_non_chiffrable_honnete():
    import html as _h
    out = _out(calculable=False)
    assert "n'est pas chiffrable" in _h.unescape(ag._synthese(out))
    assert "aucun chiffre" in _h.unescape(ag._bilan_rebours(out)).lower()
