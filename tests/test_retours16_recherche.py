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
                    ST_SetSRID(ST_GeomFromText('POLYGON((55.27 -21.01,55.2701 -21.01,55.2701 -21.0101,55.27 -21.0101,55.27 -21.01))'), 4326), now(), now()),
                   ('97411000ZX0043', 'Saint-Denis', 'ZX', '43', 1234,
                    ST_SetSRID(ST_GeomFromText('POLYGON((55.45 -20.881,55.4501 -20.881,55.4501 -20.8811,55.45 -20.8811,55.45 -20.881))'), 4326), now(), now())
            ON CONFLICT (idu) DO NOTHING"""))
        c.execute(text("""
            INSERT INTO adresses (id_ban, numero, voie, commune, code_postal, idu, geom)
            VALUES ('r16-ban-1', '12', 'Rue de l''Étang Zoreil', 'Saint-Denis', '97400',
                    '97411000ZX0042', ST_SetSRID(ST_MakePoint(55.45, -20.88), 4326))
            ON CONFLICT DO NOTHING"""))
        # PERMIS-CHECK-1 P3 — adresse AVEC rep (bis) : le collage d'un libellé de fiche
        # « 1 bis Voie, CP Commune » doit retrouver la parcelle malgré le rep + le suffixe CP+commune.
        c.execute(text("""
            INSERT INTO adresses (id_ban, numero, rep, voie, commune, code_postal, idu, geom)
            VALUES ('r16-ban-2', '1', 'bis', 'Chemin de la Citerne Test', 'Saint-Denis', '97417',
                    '97411000ZX0042', ST_SetSRID(ST_MakePoint(55.45, -20.88), 4326))
            ON CONFLICT DO NOTHING"""))
        # PERMIS-CHECK-2 pt 3 — le VOISIN « 1 » (sans rep), parcelle DISTINCTE : « 1 bis » ne doit
        # PAS renvoyer cette parcelle, et le libellé doit AFFICHER le rep (sinon « 1 » et « 1 bis »
        # se ressemblent → confusion « 1 bis corrigé en 1 »).
        c.execute(text("""
            INSERT INTO adresses (id_ban, numero, voie, commune, code_postal, idu, geom)
            VALUES ('r16-ban-3', '1', 'Chemin de la Citerne Test', 'Saint-Denis', '97417',
                    '97411000ZX0043', ST_SetSRID(ST_MakePoint(55.45, -20.881), 4326))
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
            c.execute(text("DELETE FROM adresses WHERE id_ban IN ('r16-ban-1', 'r16-ban-2', 'r16-ban-3')"))
            c.execute(text("DELETE FROM parcelle_personne_morale WHERE idu LIKE '974%ZX0042'"))
            c.execute(text("DELETE FROM parcels WHERE idu LIKE '974%ZX004%'"))


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


def test_adresse_collee_depuis_fiche_retrouve_parcelle(client):
    """PERMIS-CHECK-1 P3 — une adresse RECOPIÉE depuis une fiche (« N rep Voie, CP Commune »)
    retrouve sa parcelle. Avant, le rep (bis/ter) et le suffixe CP+commune, absents de la colonne
    cherchée « numéro voie », faisaient échouer le collage → « Aucune correspondance »."""
    # collage EXACT du libellé de fiche (_fmt_ban : « {numero} {rep} {voie}, {cp} {commune} »)
    r = client.get("/api/recherche/suggest",
                   params={"q": "1 bis Chemin de la Citerne Test, 97417 Saint-Denis"})
    assert r.status_code == 200, r.text[:300]
    adr = {g["type"]: g["items"] for g in r.json()["groupes"]}.get("adresse", [])
    # PERMIS-CHECK-2 pt 3 — la BONNE parcelle (le « 1 bis » = ZX0042), JAMAIS le voisin « 1 » (ZX0043)
    bis = next((i for i in adr if i["idu"] == "97411000ZX0042"), None)
    assert bis is not None, adr
    assert not any(i["idu"] == "97411000ZX0043" for i in adr), adr   # le rep discrimine : pas le « 1 »
    # le libellé PORTE le rep (sinon « 1 » et « 1 bis » se ressemblent → « 1 bis corrigé en 1 »)
    assert bis["label"] == "1 bis Chemin de la Citerne Test", bis
    # le suffixe CP+commune ne suffit PAS seul à casser la recherche : la voie partielle marche toujours
    r2 = client.get("/api/recherche/suggest", params={"q": "chemin de la citerne test"})
    adr2 = {g["type"]: g["items"] for g in r2.json()["groupes"]}.get("adresse", [])
    assert any(i["idu"] == "97411000ZX0042" for i in adr2), adr2
    # les DEUX (« 1 » et « 1 bis ») apparaissent et sont DISTINGUABLES par leur libellé
    labels2 = {i["label"] for i in adr2}
    assert {"1 Chemin de la Citerne Test", "1 bis Chemin de la Citerne Test"} <= labels2, labels2


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
    assert "'adresse', 'cadastre', 'proprietaire', 'siren'" in header
    mp = (ROOT / "frontend/src/components/outils/ModulePanel.tsx").read_text(encoding="utf-8")
    assert "grammaires={['adresse', 'cadastre', 'commune']}" in mp
