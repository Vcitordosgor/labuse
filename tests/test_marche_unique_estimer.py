"""CHASSE-FIX-1 (B-3 / CH-B-M3 / MARCHE-UNIQUE) — l'Estimer et la carte Marché de la fiche lisent
EXACTEMENT la même médiane €/m², au même point de calcul (`reference_locale`). Avant le correctif,
l'Estimer (`comparateur_bien`) calculait sa propre médiane (échantillon + fenêtre distincts) → un
bien affichait « maison 4 747 €/m² » à l'Estimer et « maison 4 265 €/m² » sur sa fiche. Désormais, un
seul chiffre pour le même bien.

DB réelle (skip si la base de test ne porte pas assez de ventes DVF bâties)."""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.db import session_scope

pytestmark = pytest.mark.db


# Témoins du rapport Lot B (Saint-Paul) qui PORTENT une médiane maison bâtie — garantissent que le
# test EXERCE le correctif (sinon les 12 premiers idus par ordre alpha n'ont pas de médiane par type).
_TEMOINS = ("97415000ER0783", "97415000ER0918", "97415000DT0487", "97415000BO0587")


def _parcelles(db, n=12):
    vus = [r[0] for r in db.execute(text(
        "SELECT idu FROM parcels WHERE idu = ANY(:w)"), {"w": list(_TEMOINS)}).all()]
    extra = [r[0] for r in db.execute(text(
        "SELECT idu FROM parcels WHERE commune IN "
        "('Saint-Denis','Saint-Pierre','Le Tampon','Saint-Paul','Saint-Louis') "
        "ORDER BY idu LIMIT :n"), {"n": n}).all()]
    return vus + [i for i in extra if i not in vus]


def test_estimer_et_fiche_servent_la_meme_mediane_maison_appartement():
    from labuse.api.mon_secteur import medianes_par_type
    from labuse.marche_service import comparateur_bien
    with session_scope() as db:
        idus = _parcelles(db)
        if not idus:
            pytest.skip("base de test sans parcelles témoins")
        vus = 0
        for idu in idus:
            fiche = medianes_par_type(db, idu)   # la carte Marché de la fiche (reference_locale)
            for typ in ("maison", "appartement"):
                fiche_med = (fiche.get(typ) or {}).get("eur_m2")
                if fiche_med is None:
                    continue
                # l'Estimer lit comparateur_bien → médiane reprise de reference_locale : MÊME chiffre.
                cb = comparateur_bien(db, idu, type_bien=typ)
                assert cb is not None and cb.get("median") is not None, f"{idu} {typ}"
                assert cb["median"] == round(float(fiche_med)), (
                    f"{idu} {typ} : Estimer {cb['median']} ≠ carte Marché fiche {round(float(fiche_med))}")
                assert cb["radius_m"] == (fiche.get(typ) or {}).get("rayon_m")
                vus += 1
        if vus == 0:
            pytest.skip("aucune parcelle témoin avec une médiane bâti par type dans la base de test")


def test_mediane_servie_independante_de_la_surface_du_sujet():
    """La médiane de tête ne dépend plus de la surface du sujet (un seul €/m² quelle que soit la
    surface saisie) : la pondération ESTIMER-PRECISION-1 n'ordonne plus que les comparables affichés."""
    from labuse.marche_service import comparateur_bien
    with session_scope() as db:
        idus = _parcelles(db)
        if not idus:
            pytest.skip("base de test sans parcelles témoins")
        for idu in idus:
            for typ in ("maison", "appartement"):
                a = comparateur_bien(db, idu, type_bien=typ, surface_sujet=None)
                b = comparateur_bien(db, idu, type_bien=typ, surface_sujet=250.0, terrain_sujet=800.0)
                if not a or a.get("median") is None:
                    continue
                assert a["median"] == b["median"], f"{idu} {typ} : médiane dépend de la surface sujet"
                return
        pytest.skip("aucune parcelle témoin avec médiane bâti")
