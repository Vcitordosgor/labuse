"""RETOURS-8 (R5) — la pige en onglets : les 4 chiffres de tête + la confiance/pourquoi de « À rattacher ».

Vérifie côté backend ce qui NOURRIT l'UI en onglets :
  · /admin/radar/check expose annonces_en_vie · a_rattacher · reverif_dues (les chiffres de tête) ;
  · /admin/radar/a-instruire expose, par proposition, la CONFIANCE (forte/faible), le POURQUOI (critères
    convergents) et la 1re candidate — de quoi proposer « Rattacher » en 1 clic (forte) vs « Instruire ».
"""
from __future__ import annotations

import types
import uuid

import pytest
from sqlalchemy import text

from labuse.db import session_scope
from labuse.pige import api as radar_api

pytestmark = pytest.mark.db

COMMUNE = "RadarR8Ville"


def _req():
    return types.SimpleNamespace(state=types.SimpleNamespace(compte_id=None))


@pytest.fixture
def seed_pistes(engine, monkeypatch):
    monkeypatch.setattr(radar_api, "exiger_admin", lambda req: None, raising=False)
    # la garde est importée dans les endpoints via `from ..api.auth import exiger_admin` → on patche là.
    from labuse.api import auth
    monkeypatch.setattr(auth, "exiger_admin", lambda req: None)
    idu_forte = f"97498{uuid.uuid4().hex[:4].upper()}0001"[:14].ljust(14, "0")
    with engine.begin() as c:
        # bien FORTE (confiance 0,9, adresse BAN exacte) — 1 candidate en piste.
        bf = c.execute(text(
            "INSERT INTO pige_biens (commune, type_bien, statut, rattachement_etat, rattachement_confiance, "
            " rattachement_pistes, rattachement_criteres, rattachement_humain, a_qualifier) "
            "VALUES (:c,'maison','active','piste',0.9, "
            " CAST(:p AS jsonb), CAST(:cr AS jsonb), false, false) RETURNING bien_id"),
            {"c": COMMUNE, "p": f'[{{"idu":"{idu_forte}"}}]',
             "cr": '[{"critere":"adresse BAN exacte","valeur":"12 rue X","converge":true}]'}).scalar()
        c.execute(text("INSERT INTO pige_faits (bien_id, prix, type_bien, valide_at) "
                       "VALUES (:b, 350000, 'maison', now())"), {"b": bf})
        # bien FAIBLE (confiance 0,78, surface seule) — en piste aussi.
        bfaible = c.execute(text(
            "INSERT INTO pige_biens (commune, type_bien, statut, rattachement_etat, rattachement_confiance, "
            " rattachement_pistes, rattachement_criteres, rattachement_humain, a_qualifier) "
            "VALUES (:c,'terrain','active','piste',0.78, '[]'::jsonb, '[]'::jsonb, false, false) RETURNING bien_id"),
            {"c": COMMUNE}).scalar()
        c.execute(text("INSERT INTO pige_faits (bien_id, prix, type_bien, valide_at) "
                       "VALUES (:b, 190000, 'terrain', now())"), {"b": bfaible})
    yield {"forte": bf, "faible": bfaible, "idu_forte": idu_forte}
    with engine.begin() as c:
        c.execute(text("DELETE FROM pige_faits WHERE bien_id IN (:a,:b)"), {"a": bf, "b": bfaible})
        c.execute(text("DELETE FROM pige_biens WHERE bien_id IN (:a,:b)"), {"a": bf, "b": bfaible})


def test_a_instruire_expose_confiance_et_pourquoi(seed_pistes):
    out = radar_api.radar_a_instruire(_req())
    par_id = {r["bien_id"]: r for r in out["file"]}
    forte = par_id[seed_pistes["forte"]]
    assert forte["confiance"] == "forte"                              # ≥ 0,85 → Rattacher 1 clic
    assert forte["premiere_piste"] and forte["premiere_piste"]["idu"] == seed_pistes["idu_forte"]
    assert forte["rattachement_criteres"]                            # le POURQUOI est présent
    faible = par_id[seed_pistes["faible"]]
    assert faible["confiance"] == "faible"                           # < 0,85 → Instruire (ortho)


def test_check_expose_les_chiffres_de_tete(seed_pistes):
    d = radar_api.radar_check(_req())
    assert "annonces_en_vie" in d and "a_rattacher" in d and "reverif_dues" in d
    assert d["a_rattacher"] >= 2                                     # nos deux biens en piste
    assert d["annonces_en_vie"] >= 2                                 # validés + actifs
