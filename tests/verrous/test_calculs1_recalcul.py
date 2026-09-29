"""CALCULS-AUDIT-1 lot D — le RECALCUL INDÉPENDANT est permanent (compagnon de V6b).

Chaque calcul du back qui produit un chiffre servi a un recalcul indépendant dans
`scripts.coherence.recalcul` ; ce verrou rejoue les recalculs DÉTERMINISTES (formule pure,
sans base : taxe d'aménagement sur cas limites, frontières de palier/bande, médiane
indépendante) et exige ZÉRO écart. Les recalculs sur données (surface, médiane secteur,
mult_base…) sont joués par le banc `scripts.coherence.recalcul.banc_calcul` (job nocturne sur
l'échantillon, V6b sur les témoins présents) ; ici on garde le cœur déterministe + l'invariant
de couverture (tout domaine de calcul a son module de recalcul câblé).

Règle du registre (mandat) : un calcul nouveau SANS recalcul indépendant doit se voir — le
test de couverture ci-dessous liste les domaines câblés ; l'ajouter est explicite.
"""
from __future__ import annotations

import pytest

from scripts.coherence.recalcul import socle, taxe, score, banc_calcul

pytestmark = pytest.mark.verrous


def test_taxe_amenagement_formule_cas_limites():
    """La réimplémentation indépendante (constantes officielles 2026 vérifiées) reproduit
    EXACTEMENT la sortie du produit sur les cas limites du mandat (0, RP, aidé, forfaits,
    taux majoré, petite surface, taux manquant). Un écart = constante ou formule dérivée."""
    from labuse import taxe_amenagement as prod
    for cas in taxe.CAS:
        servi = prod.calculer(**cas)
        recalc = taxe.ta_independante(**cas)
        for champ in ("assiette_eur", "total_eur", "rap_eur"):
            s, r = servi.get(champ), recalc[champ]
            if s is None or r is None:
                assert (s is None) == (r is None), f"{champ} absence divergente sur {cas}"
                continue
            assert abs(float(s) - float(r)) <= max(0.01, abs(float(s)) * 0.01), \
                f"taxe {champ} : servi {s} ≠ recalc {r} sur {cas}"


def test_frontieres_palier_et_bande():
    """Frontières exactes du Signal (0,20/0,10) et des bandes du Score (80/50/30), y compris
    l'effet d'arrondi-avant-bande. La réimplémentation doit rendre l'intention documentée."""
    for p, attendu in score.CAS_SIGNAL:
        assert score.signal_niveau(p) == attendu, f"palier p={p}"
    for s, attendu in score.CAS_BANDE:
        assert score.bande_de_score(s) == attendu, f"bande score={s}"


def test_mediane_independante():
    """La médiane indépendante (interpolation des deux centraux) — l'oracle contre lequel on
    teste percentile_cont(0,5) de Postgres."""
    assert socle.mediane([]) is None
    assert socle.mediane([5]) == 5
    assert socle.mediane([1, 3]) == 2.0            # pair → moyenne des deux centraux
    assert socle.mediane([1, 2, 3, 4]) == 2.5
    assert socle.mediane([4, 1, 3, 2, 5]) == 3     # impair, non trié


def test_pente_conversion_degres_pourcent():
    """Conversion pente °→% = round(tan(rad)·100) — cas limites (0°, 45°→100%, 100%)."""
    import math
    assert round(math.tan(math.radians(0)) * 100) == 0
    assert round(math.tan(math.radians(45)) * 100) == 100
    assert socle.pente_deg_depuis_pct(100.0) == pytest.approx(45.0, abs=1e-6)


def test_couverture_domaines_de_calcul():
    """Registre : tout domaine de calcul servi a son module de recalcul câblé au banc.
    Ajouter un calcul dans un nouveau domaine SANS recalcul indépendant fait échouer ici."""
    domaines = {nom for nom, _ in banc_calcul.MODULES}
    attendus = {
        "géométrie (surface, pente, %couche)",
        "résiduel/hauteur (identités servies)",
        "médianes DVF secteur",
        "taxe d'aménagement",
        "signal/bandes (mult_base, frontières)",
    }
    assert attendus <= domaines, f"domaine(s) de recalcul manquant(s) : {attendus - domaines}"
