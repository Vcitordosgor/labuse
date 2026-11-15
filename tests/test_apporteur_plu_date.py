"""CHIRURGICAL-FIX-1 (LOT F, E7) — la date d'approbation du PLU imprimée par l'Apporteur est celle de
la FICHE (document opposable servi, `plu_fraicheur.horizon`), jamais l'approbation d'ORIGINE Sudocuh
(qui précède une révision et affichait une date périmée divergente de la fiche)."""
from labuse.exports.blocs.apporteur import _coup_d_oeil
from labuse.registre.valeur import Valeur


def _v(x):
    return Valeur(valeur=x, chiffre_id="t", version_def="t", run=None)


def _valeurs(statut_plu):
    return {
        "surface_parcelle_m2": _v(1703),
        "zone_plu_famille": _v("U"),
        "reglement_plu_bloc": _v({"zones": [{"zone": "Ud", "libelle": "urbaine"}]}),
        "statut_plu": _v(statut_plu),
    }


def test_apporteur_prend_la_date_opposable_de_la_fiche_pas_sudocuh():
    # Fiche = document opposable 2023-08-11 (97422_PLU_20230811) ; Sudocuh = approbation d'origine 2018.
    statut = {"horizon": "2023-08-11", "approbation_sudocuh": "2018-12-08",
              "libelle": "PLU approuvé le 2023-08-11"}
    html = _coup_d_oeil(_valeurs(statut), ctx={})
    assert "PLU approuvé le 11/08/2023" in html      # la date de la FICHE
    assert "08/12/2018" not in html                  # jamais l'approbation d'origine Sudocuh périmée


def test_apporteur_repli_sudocuh_si_pas_d_horizon():
    # Sans date opposable servie, on retombe sur Sudocuh (repli ultime) — comportement conservé.
    statut = {"approbation_sudocuh": "2019-06-26", "libelle": "PLU"}
    html = _coup_d_oeil(_valeurs(statut), ctx={})
    assert "PLU approuvé le 26/06/2019" in html
