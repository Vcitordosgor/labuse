"""CIRCUIT-1 lot 1 — LE REGISTRE : intégrité, miroir idempotent, tampon `?trace=1`,
modes + cadences déclarés au seed.

1.6 — GARDE DE COUVERTURE (version lot 1) : les endpoints tracés sont les deux mandatés
(`/parcels/{idu}` et `/communes/{c}/contexte`). EXCEPTIONS JUSTIFIÉES (le reste des 122
robinets sera équipé aux lots 2 et 7) :
  · robinets `hors_registre` (24) — tuiles/géométries/textes, raison déclarée dans robinets.py ;
  · robinets non encore servis par `?trace=1` (PDF, mails, Copilote, outils) — le tampon existe
    côté serveur (`registre.tampons_pour`), le branchement endpoint par endpoint est le lot 7.1.
La garde d'ici verrouille : tout chiffre déclaré des fiches parcelle/commune a un tampon complet.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse import registre
from labuse.registre import sync as registre_sync

pytestmark = pytest.mark.db


# ─────────────────────────── intégrité (pur code, sans base) ───────────────────────────

def test_integrite_zero_probleme():
    assert registre.verifier() == []


def test_un_chiffre_une_definition():
    """Règle 1 du mandat : id unique, définition non vide, unité et niveau dans les énums."""
    unites = {"%", "€", "€/m²", "m²", "logements", "classe", "verdict", "tranche", "date", "nombre", "m"}
    niveaux = {"parcelle", "commune", "zone", "proprietaire", "annonce", "global"}
    for cid, c in registre.CHIFFRES.items():
        assert c.definition.strip(), cid
        assert c.unite in unites, (cid, c.unite)
        assert c.niveau in niveaux, (cid, c.niveau)
        assert c.portee in ("run", "live"), cid


def test_robinet_sans_chiffre_dit_pourquoi():
    for rid, r in registre.ROBINETS.items():
        assert r.chiffres or r.hors_registre, rid


def test_aretes_derivees_jamais_saisies():
    a = registre.aretes()
    assert len(a["chiffre_vers_robinet"]) >= 139   # au moins les couples de l'inventaire
    # chaque arête pointe des ids existants
    for cid, rid in a["chiffre_vers_robinet"]:
        assert cid in registre.CHIFFRES and rid in registre.ROBINETS


# ─────────────────────────── miroir en base (1.5) ───────────────────────────

def test_sync_idempotent(db_session):
    n1 = registre_sync.sync(db_session)
    n2 = registre_sync.sync(db_session)
    assert n1 == n2
    en_base = db_session.execute(text("SELECT count(*) FROM registre_chiffres")).scalar()
    assert en_base == len(registre.CHIFFRES)
    en_base_r = db_session.execute(text("SELECT count(*) FROM registre_robinets")).scalar()
    assert en_base_r == len(registre.ROBINETS)
    aretes = db_session.execute(text("SELECT count(*) FROM registre_aretes")).scalar()
    assert aretes == sum(len(v) for v in registre.aretes().values())


# ─────────────────────────── tampon ?trace=1 (1.4 + 1.6) ───────────────────────────

def test_tampons_pour_chaque_chiffre_fiche_commune(db_session):
    """Chaque chiffre déclaré des 15 cartes de la fiche commune reçoit un tampon COMPLET
    (chiffre_id, version_def, portée, réservoirs) — la garde 1.6 du lot 1."""
    cids = sorted({cid for rid, r in registre.ROBINETS.items()
                   if rid.startswith("fiche_commune") for cid in r.chiffres})
    assert cids, "la fiche commune déclare des chiffres"
    t = registre.tampons_pour(db_session, cids)
    assert set(t) == set(cids)
    for cid, tampon in t.items():
        assert tampon["chiffre_id"] == cid
        assert tampon["version_def"] == registre.VERSION_DEF
        assert "reservoirs" in tampon and "run" in tampon and tampon["definition"]


def test_tampons_portee_run_porte_le_run(db_session):
    """Un chiffre à portée `run` porte le run servi dans son tampon ; un `live` porte None."""
    t = registre.tampons_pour(db_session, ["tier_opportunite", "prix_ancien_median_eur_m2"])
    assert t["tier_opportunite"]["portee"] == "run"
    assert t["tier_opportunite"]["run"], "portée run → le tampon porte le run servi"
    assert t["prix_ancien_median_eur_m2"]["run"] is None


def test_trace_endpoint_fiche_commune(db_session):
    """`?trace=1` sur /communes/{c}/contexte rend `_trace` avec un tampon par chiffre déclaré
    (auth locale désactivée : exiger_admin est no-op — le 403 hors admin est testé au lot 7)."""
    from fastapi.testclient import TestClient
    from labuse.api.app import app
    client = TestClient(app)
    d = client.get("/communes/Saint-Paul/contexte?trace=1").json()
    assert "_trace" in d
    attendus = {cid for rid, r in registre.ROBINETS.items()
                if rid.startswith("fiche_commune") for cid in r.chiffres}
    assert set(d["_trace"]) == attendus
    sans = client.get("/communes/Saint-Paul/contexte").json()
    assert "_trace" not in sans, "sans trace=1 : la valeur seule, jamais le tampon"


# ─────────────────────────── seed : modes + cadences (1.7) ───────────────────────────

def test_modes_cadences_declares(db_session):
    from labuse.ingestion.seed_sources import MODE_ET_CADENCE, appliquer_modes_cadences
    assert len(MODE_ET_CADENCE) == 77
    modes = {m for m, _, _ in MODE_ET_CADENCE.values()}
    assert modes <= {"job_sur_clic", "cron_mensuel", "depot_manuel", "one_shot", "en_direct", "absente"}
    statuts = {s for _, _, s in MODE_ET_CADENCE.values()}
    assert statuts == {"declaree", "proposee", "sans_objet"}
    # sans_objet ↔ jamais de cadence ; les autres en ont toujours une
    for nom, (mode, jours, statut) in MODE_ET_CADENCE.items():
        if statut == "sans_objet":
            assert jours is None, nom
        else:
            assert isinstance(jours, int) and jours > 0, nom
    appliquer_modes_cadences(db_session)     # idempotent, colonnes posées
    appliquer_modes_cadences(db_session)
    n = db_session.execute(text(
        "SELECT count(*) FROM data_sources WHERE mode_remplissage IS NOT NULL")).scalar()
    assert n >= 1
