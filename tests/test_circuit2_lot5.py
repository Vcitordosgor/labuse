"""CIRCUIT-2 lot 5 — page et traçage : le « i » d'une couche dit source/millésime/fabrication
(/map/couches-info), la fiche du bas reçoit type/table/fabrication par donnée, les pastilles
comptent les écarts de type classe et géométrie."""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.registre.couverture import COUCHE_PAR_CLE_FRONT
from labuse.registre.donnees import DONNEES

pytestmark = pytest.mark.db


def test_couche_par_cle_front_pointe_des_couches_declarees():
    for cle, cid in COUCHE_PAR_CLE_FRONT.items():
        assert cid in DONNEES, (cle, cid)
        assert DONNEES[cid].type == "couche", (cle, cid)


def test_couches_info_sert_source_et_fabrication(db_session):
    from fastapi.testclient import TestClient

    from labuse.api.app import app
    client = TestClient(app)
    d = client.get("/map/couches-info").json()
    assert set(d) == set(COUCHE_PAR_CLE_FRONT)
    for cle, meta in d.items():
        assert meta["source"], cle
        assert meta["fabrication"], cle
    # sobre, sans identifiant technique : la fabrication est en français
    assert d["parcelles"]["fabrication"] == "tuiles reconstruites à la bascule"
    assert d["zonage_parcelle"]["fabrication"] == "lue en direct de la base"


def test_admin_circuit_donnees_typees_et_pastilles(db_session):
    """Le payload de la page porte type/table/fabrication/domaine par donnée, le type des
    fuites et les compteurs par type (pastilles 5.3).

    LEÇON CIRCUIT-1 (« verrou 600 s ») : le DDL de `ensure()` + l'INSERT se posent sur une
    connexion AUTONOME (commit réel) — dans la transaction-savepoint du fixture, l'ALTER
    prendrait un verrou exclusif qui bloque la connexion propre de l'endpoint."""
    import labuse.sonde_circuit as sc
    from labuse.db import engine
    with engine().connect() as c:
        with c.begin():
            sc.ensure(c)
            sc._upsert_ecart(c, "zone_plu_famille", "LOT5-TEST", "fiche", "A", "couche", "U",
                             "table", type_donnee="classe")
    try:
        from fastapi.testclient import TestClient

        from labuse.api.app import app
        client = TestClient(app)
        d = client.get("/admin/circuit").json()
        ch = d["chiffres"]["zonage_plu_couche"]
        assert ch["type"] == "couche" and ch["table"] == "parcel_zone_plu"
        assert ch["fabrication"] == "requete"
        assert d["chiffres"]["zone_plu_famille"]["domaine"] == ["U", "AU", "A", "N"]
        assert d["compteurs"]["fuites_classe"] >= 1
        assert any(f.get("type") == "classe" for f in d["fuites"])
    finally:
        with engine().connect() as c:
            with c.begin():
                c.execute(text("DELETE FROM circuit_ecarts WHERE cle = 'LOT5-TEST'"))


def test_traçage_des_classes_pose():
    """La lettre de zone et le niveau d'aléa portent l'étiquette Trace (5.2) — vérifié au
    niveau source (le rendu identité éteint est verrouillé par le snapshot vitest de trace)."""
    from pathlib import Path
    racine = Path(__file__).resolve().parents[1]
    fiche = (racine / "frontend/src/components/fiche/Fiche.tsx").read_text()
    assert '<Trace id="zone_plu_famille">' in fiche
    risques = (racine / "frontend/src/components/fiche/risques.tsx").read_text()
    assert "alea_inondation_couche" in risques and "alea_mvt_couche" in risques
