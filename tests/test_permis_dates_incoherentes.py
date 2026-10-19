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


def test_dossier_ecart_plus_d_un_mois_dit_modificatif_ou_transfere():
    """DONNEES-7 — au-delà d'1 mois d'écart (dépôt bien après l'autorisation), le Dossier montre les
    deux dates telles quelles (jamais échangées) et qualifie : « souvent un permis modificatif ou
    transféré ». Toujours pas de « modifié, dernier dépôt le… » (pas de n° de modificatif au flux)."""
    permis = [{"type": "PC", "date_depot": "2018-10-15", "date_autorisation": "2017-08-25"}]  # ~14 mois
    out = _r_permis_liste(permis)
    # CHASSE-DOCS-FIX-1 (E-13) — dates servies au format FR (jamais ISO) ; l'ordre des LABELS reste
    # (déposé = date de dépôt, autorisé = date d'autorisation), jamais échangé même si dépôt > autorisation.
    assert "déposé 15/10/2018, autorisé 25/08/2017" in out
    assert "Dépôt enregistré après l'autorisation — souvent un permis modificatif ou transféré" in out
    assert "dates incohérentes chez le producteur" not in out


def test_dossier_ecart_sous_un_mois_reste_incoherence():
    """DONNEES-7 — sous 1 mois d'écart, on ne présume rien : « dates incohérentes chez le producteur »."""
    permis = [{"type": "PC", "date_depot": "2017-08-25", "date_autorisation": "2017-08-10"}]  # 15 jours
    out = _r_permis_liste(permis)
    assert "déposé 25/08/2017, autorisé 10/08/2017" in out            # format FR (E-13), non échangé
    assert "dates incohérentes chez le producteur" in out
    assert "modificatif" not in out


def test_dossier_permis_coherent_sans_mention():
    permis = [{"type": "PC", "date_depot": "2017-01-10", "date_autorisation": "2017-07-30"}]
    out = _r_permis_liste(permis)
    assert "déposé 10/01/2017, autorisé 30/07/2017" in out            # format FR (E-13)
    assert "incohérentes" not in out


def test_dossier_liste_vide_ou_dates_manquantes_ne_casse_pas():
    assert _r_permis_liste([]) == ""
    assert _r_permis_liste(None) == ""
    # une seule date : pas d'incohérence possible, pas de mention, pas d'échec.
    # E-13 — Sitadel ne publie que l'ANNÉE de dépôt (jour fabriqué « -01-01 ») → « en 2020 », jamais ISO.
    out = _r_permis_liste([{"type": "DP", "date_depot": "2020-01-01"}])
    assert "déposé en 2020" in out and "incohérentes" not in out
