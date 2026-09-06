"""CIRCUIT-P3 lot 3 — une seule source de vérité. Le Résumé et le Circuit lisent le MÊME état
(circuit_etats), calculé une seule fois côté serveur ; le front ne reclasse plus rien (`ko` posé
par le serveur, plus de koTank/koTap). Un test de cohérence globale, joué sur la base RÉELLE locale
(`pytest -m local`), exige que les deux lectures coïncident."""
from __future__ import annotations

import os

import pytest

from labuse import circuit_etats as E


@pytest.fixture
def client(engine):
    from fastapi.testclient import TestClient
    from labuse.api.app import app
    from labuse.api.dashboard import router
    if not any(getattr(r, "path", "") == "/admin/circuit" for r in app.routes):
        app.include_router(router)
    return TestClient(app)


# ── 3.1 — la source est unique : chaque élément porte son `ko` (posé par le serveur), et les
#         compteurs comptent CE `ko`. Le front n'a rien à reclasser. ────────────────────────────
@pytest.mark.db
def test_payload_porte_ko_source_unique(client, engine):
    from labuse.ingestion.seed_sources import appliquer_modes_cadences
    with engine.begin() as c:
        appliquer_modes_cadences(c)
    circ = client.get("/admin/circuit").json()
    # tout réservoir / robinet porte un `ko` booléen, cohérent avec ko_reservoir/ko_robinet
    for r in circ["reservoirs"]:
        assert r["ko"] is E.ko_reservoir(*r["etat"])
    for rb in circ["robinets"]:
        assert rb["ko"] is E.ko_robinet(*rb["etat"])
    # les compteurs de colonne SONT ces ko (aucun recompte parallèle)
    assert circ["compteurs"]["a_regarder"] == sum(1 for r in circ["reservoirs"] if r["ko"])
    assert circ["compteurs"]["robinets_a_regarder"] == sum(1 for rb in circ["robinets"] if rb["ko"])


def _coherence(circ: dict) -> list[str]:
    """Renvoie la liste des incohérences Résumé ↔ Circuit (vide = cohérent). Réutilisable pour
    prouver l'échec AVANT correctif et le succès APRÈS."""
    pbs = []
    # tolérant à un payload d'AVANT P3 (sans `ko`) : on retombe sur ko_robinet/ko_reservoir — ce qui
    # permet à ce test de prouver l'incohérence sur l'ancien code comme sur le nouveau.
    def _ko_rob(rb):
        return rb["ko"] if "ko" in rb else E.ko_robinet(*rb["etat"])

    def _ko_res(r):
        return r["ko"] if "ko" in r else E.ko_reservoir(*r["etat"])
    # ── robinets ──
    ko_rendu = {rb["id"] for rb in circ["robinets"] if _ko_rob(rb)}
    lignes = {li["titre"]: li for g in circ["resume"]["groupes"] for li in g["lignes"]}
    ids_resume_rob = set()
    for titre in ("fuites mesurées", "robinets servent de l'eau ancienne",
                  "affichages calculés hors moteur"):
        if titre in lignes:
            ids_resume_rob |= set(lignes[titre]["cible"]["ids"])
    # chaque robinet cité par le Résumé est « à regarder » dans le Circuit
    for rid in ids_resume_rob:
        if rid not in ko_rendu:
            pbs.append(f"Résumé cite le robinet {rid!r} que le Circuit dit OK")
    # chaque robinet « à regarder » (fuite/eau/hors-moteur) est cité par le Résumé
    for rid in ko_rendu:
        rb = next(x for x in circ["robinets"] if x["id"] == rid)
        if rb["etat"][1] not in ("choix à confirmer", "écart à la règle") and rid not in ids_resume_rob:
            pbs.append(f"Circuit dit le robinet {rid!r} à regarder ({rb['etat'][1]}) sans ligne au Résumé")
    # ── réservoirs ──
    ko_res = {r["id"] for r in circ["reservoirs"] if _ko_res(r)}
    ids_resume_res = set()
    for g in circ["resume"]["groupes"]:
        for li in g["lignes"]:
            if li["cible"]["type"] == "reservoir" and li["couleur"] in ("rouge", "ambre", "mauve"):
                ids_resume_res |= set(li["cible"]["ids"])
    if ko_res != ids_resume_res:
        pbs.append(f"réservoirs : Circuit {sorted(ko_res)} ≠ Résumé {sorted(ids_resume_res)}")
    return pbs


# ── 3.2 — cohérence globale sur la BASE RÉELLE locale (pytest -m local) ────────────────────────
@pytest.mark.local
def test_coherence_globale_base_reelle(monkeypatch):
    """Sur la vraie base `labuse` : le Journal rend ses lignes, et chaque lecture (Résumé, Circuit)
    dit la même chose. Ce test échouait avant les correctifs P3 (journal vide + robinets muets)."""
    from labuse import db
    app_url = os.environ.get("LABUSE_APP_DATABASE_URL")
    assert app_url, "LABUSE_APP_DATABASE_URL absent (base réelle inconnue)"
    real = db.make_engine(app_url)
    monkeypatch.setattr(db, "_engine", real)
    monkeypatch.setattr(db, "_Session", None)      # session_factory se rebâtit sur la vraie base

    from fastapi.testclient import TestClient
    from labuse.api.app import app
    from labuse.api.dashboard import router
    if not any(getattr(r, "path", "") == "/admin/circuit" for r in app.routes):
        app.include_router(router)
    client = TestClient(app)

    # le Journal rend ses lignes (la table réelle est pleine) — plus de « 0 passage »
    journal = client.get("/admin/circuit/journal?taille=50").json()
    assert journal["total"] > 0 and journal["entrees"], "journal vide sur une base pleine"

    # les deux lectures coïncident
    circ = client.get("/admin/circuit").json()
    pbs = _coherence(circ)
    assert not pbs, "incohérences Résumé ↔ Circuit :\n  - " + "\n  - ".join(pbs)
