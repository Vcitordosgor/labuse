"""RETOURS-10 (T2.3) — TEST DE GARDE de performance des endpoints admin.

Exécute chaque endpoint admin sur la base COURANTE et échoue au-dessus du seuil (2 s). Le test n'a de
sens que sur une base de taille RÉALISTE : il se SKIP quand `parcel_p_score_v2` est petite (base de test
vide en CI) — la garde vit alors sur la vraie base de Vic (`pytest tests/test_admin_perf_retours10.py`
avec `LABUSE_DATABASE_URL` pointant sur la base réelle).

On mesure le temps CHAUD (2ᵉ appel, caches peuplés) : c'est l'expérience réelle en production (les caches
accueil/écarts/tuiles se peuplent au 1ᵉ affichage). C'est ce temps chaud que le bug d'origine cassait
(Circuit à 56 s, /accueil/chiffres à ~3,6 s même « chaud » car la sonde bustait le cache)."""
from __future__ import annotations

import time

import pytest
from sqlalchemy import text

from labuse.db import session_scope

pytestmark = pytest.mark.db

SEUIL_S = 2.0
TAILLE_REALISTE = 1_000_000  # en-deçà, la base n'est pas représentative → skip


def _base_realiste(db) -> bool:
    try:
        n = db.execute(text("SELECT reltuples::bigint FROM pg_class WHERE relname = 'parcel_p_score_v2'")).scalar()
        return bool(n and n >= TAILLE_REALISTE)
    except Exception:  # noqa: BLE001
        return False


def _cases(db):
    import labuse.api.auth as auth
    auth.exiger_admin = lambda request=None: None
    from labuse.api import courrier, dashboard, ops
    from labuse.api import app as appmod
    from labuse.pige import api as pige_api
    return [
        ("Pilotage", lambda: dashboard.admin_pilotage(request=None)),
        ("Comptes (licences)", lambda: dashboard.admin_licences(request=None)),
        ("IA", lambda: dashboard.admin_ia(request=None)),
        ("Données · Catalogue", lambda: dashboard.admin_sources(request=None)),
        ("Données · Circuit (flux)", lambda: dashboard.admin_flux(request=None)),
        ("Données · Circuit (flux/runs)", lambda: dashboard.admin_flux_runs(request=None)),
        ("Produit", lambda: dashboard.admin_produit(request=None, jours=30)),
        ("Signalements", lambda: dashboard.admin_signalements(request=None)),
        ("Courrier", lambda: courrier.courrier_admin_demandes(request=None, statut=None, db=db)),
        ("Radar (check)", lambda: pige_api.radar_check(request=None)),
        ("Contacts", lambda: ops.admin_contacts(request=None)),
        ("Sources client (liste)", lambda: appmod.list_sources(db=db)),
        ("Sources client (couverture)", lambda: appmod.sources_couverture(db=db)),
        ("Accueil client (chiffres)", lambda: appmod.accueil_chiffres(db=db)),
    ]


def test_endpoints_admin_sous_le_seuil():
    with session_scope() as db:
        if not _base_realiste(db):
            pytest.skip("base non réaliste (parcel_p_score_v2 < 1 M) — garde active sur la base réelle de Vic")
        lents = []
        for nom, fn in _cases(db):
            try:
                fn()  # chauffe les caches (accueil, écarts de runs, tuiles) comme un 1ᵉ affichage
                t = time.perf_counter()
                fn()
                dt = time.perf_counter() - t
            except Exception as e:  # noqa: BLE001 — un endpoint qui casse est un échec de garde, pas un skip
                lents.append(f"{nom} : ERREUR {type(e).__name__}: {e}")
                continue
            if dt > SEUIL_S:
                lents.append(f"{nom} : {dt:.2f}s > {SEUIL_S}s")
        assert not lents, "endpoints admin au-dessus du seuil :\n  " + "\n  ".join(lents)
