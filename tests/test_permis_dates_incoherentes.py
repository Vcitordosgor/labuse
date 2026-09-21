"""DONNEES-6 — permis SDES/Dido dont l'autorisation précède le dépôt (~15 %, incohérence du
producteur). GARDES : (a) un tel permis est EXCLU de tout calcul de délai (valide=False) ;
(b) à l'affichage on NE RÉORDONNE JAMAIS les dates — on montre les deux telles quelles et on
LE DIT (« dates incohérentes chez le producteur »), sans jamais échouer en absence.
"""
from __future__ import annotations

from datetime import date

from labuse.exports.miroir import _r_permis_liste
from labuse.ingestion.permit_delais_m10 import _months


def test_delai_negatif_est_invalide_exclu_du_calcul():
    """L'invariant qui exclut les inversés de tout calcul de délai : autorisation < dépôt →
    délai < 0 → valide=False (la même règle que build_delais : `valide = delai >= 0`)."""
    dep, aut = date(2018, 10, 15), date(2017, 8, 25)   # l'exemple AM0112
    delai = _months(dep, aut)
    assert delai is not None and delai < 0, "autorisation avant dépôt = délai négatif"
    assert not (delai >= 0), "un délai négatif ne passe jamais le filtre `valide` des médianes"
    # un permis normal reste positif
    assert _months(date(2017, 1, 1), date(2017, 7, 1)) >= 0


def test_dossier_dit_l_incoherence_sans_reordonner():
    """Le Dossier montre les DEUX dates telles que le producteur les donne (dépôt puis
    autorisation, jamais échangées) et signale l'incohérence — pas de « modifié » (le flux
    open data ne porte pas le n° de modificatif)."""
    permis = [{"type": "PC", "date_depot": "2018-10-15", "date_autorisation": "2017-08-25"}]
    out = _r_permis_liste(permis)
    assert "déposé 2018-10-15, autorisé 2017-08-25" in out       # ordre des LABELS conservé
    assert "dates incohérentes chez le producteur" in out
    assert "modifié" not in out


def test_dossier_permis_coherent_sans_mention():
    permis = [{"type": "PC", "date_depot": "2017-01-10", "date_autorisation": "2017-07-30"}]
    out = _r_permis_liste(permis)
    assert "déposé 2017-01-10, autorisé 2017-07-30" in out
    assert "incohérentes" not in out


def test_dossier_liste_vide_ou_dates_manquantes_ne_casse_pas():
    assert _r_permis_liste([]) == ""
    assert _r_permis_liste(None) == ""
    # une seule date : pas d'incohérence possible, pas de mention, pas d'échec
    out = _r_permis_liste([{"type": "DP", "date_depot": "2020-01-01"}])
    assert "déposé 2020-01-01" in out and "incohérentes" not in out
