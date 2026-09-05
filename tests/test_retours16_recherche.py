"""RETOURS-16 V5 — suggestion unifiée : un endpoint, six grammaires, un composant.

Gardes : l'aiguillage par forme (chiffres → SIREN, réf courte → cadastre multi-communes,
texte → adresse/commune/propriétaire/projet), le budget de 8 propositions, le zéro-résultat
parlant, l'isolement des projets par compte, et côté front : plus AUCUNE autocomplétion
maison (le composant partagé porte tout), Entrée ne devine jamais la 1re suggestion.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.db

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def client(engine):
    """Seed minimal : la MÊME réf courte dans DEUX communes, une adresse accentuée, une PM,
    un projet du compte local (compte_id NULL) — de quoi exercer chaque grammaire."""
    from fastapi.testclient import TestClient

    from labuse.api.app import app
    from labuse.api.recherche import ensure_index
    ensure_index(engine)
    with engine.begin() as c:
        c.execute(text("""
            INSERT INTO parcels (idu, commune, section, numero, surface_m2, geom, created_at, updated_at)
            VALUES ('97411000ZX0042', 'Saint-Denis', 'ZX', '42', 1234,
                    ST_SetSRID(ST_GeomFromText('POLYGON((55.45 -20.88,55.4501 -20.88,55.4501 -20.8801,55.45 -20.8801,55.45 -20.88))'), 4326), now(), now()),
                   ('97415000ZX0042', 'Saint-Paul', 'ZX', '42', 5678,
                    ST_SetSRID(ST_GeomFromText('POLYGON((55.27 -21.01,55.2701 -21.01,55.2701 -21.0101,55.27 -21.0101,55.27 -21.01))'), 4326), now(), now())
            ON CONFLICT (idu) DO NOTHING"""))
        c.execute(text("""
            INSERT INTO adresses (id_ban, numero, voie, commune, code_postal, idu, geom)
            VALUES ('r16-ban-1', '12', 'Rue de l''Étang Zoreil', 'Saint-Denis', '97400',
                    '97411000ZX0042', ST_SetSRID(ST_MakePoint(55.45, -20.88), 4326))
            ON CONFLICT DO NOTHING"""))
        c.execute(text("""
            INSERT INTO parcelle_personne_morale (idu, denomination, siren)
            VALUES ('97411000ZX0042', 'SCI ZOREIL FONCIER', '512345678')
            ON CONFLICT (idu) DO UPDATE SET denomination = EXCLUDED.denomination, siren = EXCLUDED.siren"""))
        c.execute(text("""
            INSERT INTO projets (nom, fiche, filtres, statut, created_at, updated_at)
            VALUES ('Zoreil lotissement', '{}', '{}', 'brouillon', now(), now())"""))
    try:
        yield TestClient(app)
    finally:
        with engine.begin() as c:
            c.execute(text("DELETE FROM projets WHERE nom = 'Zoreil lotissement'"))
            c.execute(text("DELETE FROM adresses WHERE id_ban = 'r16-ban-1'"))
            c.execute(text("DELETE FROM parcelle_personne_morale WHERE idu LIKE '974%ZX0042'"))
            c.execute(text("DELETE FROM parcels WHERE idu LIKE '974%ZX0042'"))


def _groupes(client, q: str) -> dict:
    r = client.get(f"/api/recherche/suggest?q={q}")
    assert r.status_code == 200, r.text[:300]
    d = r.json()
    assert d["total"] <= 8 and "ms" in d
    return {g["type"]: g["items"] for g in d["groupes"]}


def test_cadastre_ref_courte_toutes_les_communes(client):
    """« ZX 42 » existe dans deux communes → les DEUX apparaissent, avec commune et surface."""
    g = _groupes(client, "ZX%2042")
    labels = [i["label"] for i in g.get("cadastre", [])]
    assert any("Saint-Denis" in x for x in labels) and any("Saint-Paul" in x for x in labels), labels
    assert all(i.get("idu") and i.get("sub") for i in g["cadastre"])   # surface dite


def test_cadastre_idu_complet(client):
    g = _groupes(client, "97415000ZX0042")
    assert [i["idu"] for i in g.get("cadastre", [])] == ["97415000ZX0042"]


def test_siren_prefixe_et_aiguillage_chiffres(client):
    """Des chiffres purs essaient le SIREN d'abord (un « 512345 » matchait la regex IDU et ne
    proposait jamais la PM — mesuré au premier essai, corrigé)."""
    g = _groupes(client, "512345")
    assert [i["siren"] for i in g.get("siren", [])] == ["512345678"]


def test_proprietaire_a_la_frappe(client):
    g = _groupes(client, "zoreil%20fon")
    assert any(i["label"] == "SCI ZOREIL FONCIER" for i in g.get("proprietaire", []))


def test_commune_et_adresse_pliees(client):
    g = _groupes(client, "saint-pa")
    assert any(i["label"] == "Saint-Paul" for i in g.get("commune", []))
    # adresse accentuée retrouvée par sa forme pliée (etang sans accent, apostrophe droite)
    g2 = _groupes(client, "rue%20de%20l%27etang%20zoreil")
    assert any("Étang Zoreil" in i["label"] for i in g2.get("adresse", []))


def test_projet_du_compte(client):
    g = _groupes(client, "zoreil%20lot")
    assert any(i["label"] == "Zoreil lotissement" for i in g.get("projet", []))


def test_zero_resultat_parlant(client):
    r = client.get("/api/recherche/suggest?q=zzzzzzzz").json()
    assert r["total"] == 0 and "référence courte" in r["formats"]


def test_front_un_seul_composant_plus_d_autocompletion_maison():
    aa = (ROOT / "frontend/src/components/AddressAutocomplete.tsx").read_text(encoding="utf-8")
    assert "rechercheSuggest" in aa and "data-suggest-input" in aa and "data-suggest-item" in aa
    assert "banAutocomplete" not in aa                      # la barre ne parle qu'au suggest unifié
    assert "bg-mint text-mint-ink" in aa                    # survol : vert opaque, contenu inversé
    assert "pick(items[0])" not in aa                       # Entrée ne devine JAMAIS la 1re ligne
    assert "Aucune correspondance pour" in aa               # zéro-résultat parlant
    scan = (ROOT / "frontend/src/components/outils/ScanPatrimoine.tsx").read_text(encoding="utf-8")
    assert "data-scan-sug" not in scan and "AddressAutocomplete" in scan
    header = (ROOT / "frontend/src/components/header/Header.tsx").read_text(encoding="utf-8")
    assert "'adresse', 'cadastre', 'proprietaire', 'siren', 'commune', 'projet'" in header
    mp = (ROOT / "frontend/src/components/outils/ModulePanel.tsx").read_text(encoding="utf-8")
    assert "grammaires={['adresse', 'cadastre', 'commune']}" in mp
