"""NU5-FIX-1 — reproductions des trouvailles NU-5 Lots A & B (rouge avant, verte après).

Chaque test REJOUE une trouvaille du rapport et verrouille le correctif :
  · A-O1/O2 — le Gabarit dit « inconstructible » (jamais un volume, jamais « donnée manquante »)
    sur une parcelle dont la destination interdit de bâtir (via `potentiel_batir`, même robinet
    que la fiche).
  · A-O3 — « Estimer un bien » signale la non-constructibilité.
  · A-O4 — la taxe d'aménagement en calcul direct refuse surfaces absurdes et taux négatifs (422).
  · A-O5 — « Comparer » renvoie les IDU ignorés / en trop / doublons (plus de perte silencieuse).
  · A-O6 — l'Étude de zone refuse un rayon invalide (422) au lieu de le remplacer en silence.
  · B-F1 — LA garde unique « parcelle disparue » est câblée sur TOUTES les routes d'outil et de
    document qui prennent un IDU (test structurel : aucune route ne contourne la garde).
  · B-F2/B-F4 — l'avertissement juridique (ni conseil juridique, ni garantie de constructibilité)
    est servi en pied de CHAQUE document.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


# ───────────────────────── PUR (sans base) ─────────────────────────

def test_bf2_bf4_clause_juridique_sur_tous_les_pieds():
    """B-F2 / B-F4 — la clause juridique (certificat d'urbanisme + conseil juridique) figure dans le
    pied de CHAQUE document. DOCS-DA-1 (V11, arbitrage Vic / maquette) — le pied tient désormais sur UNE
    ligne, IDENTIQUE partout : « Document d'information · ne remplace ni un certificat d'urbanisme, ni
    une étude réglementaire, ni un conseil juridique » (la mention « garantie de constructibilité » a
    été retirée pour tenir sur une ligne ; la clause juridique essentielle reste)."""
    from labuse.exports.builder import _CLAUSE_JURIDIQUE, _FOOT
    assert "conseil juridique" in _CLAUSE_JURIDIQUE
    assert "certificat d'urbanisme" in _CLAUSE_JURIDIQUE
    for doc, pied in _FOOT.items():
        assert "conseil juridique" in pied, f"{doc} sans clause conseil juridique"
        assert "certificat d'urbanisme" in pied, f"{doc} sans clause certificat d'urbanisme"


def _fake_gabarit_ok():
    from labuse.gabarit.contract import GabaritResult
    return GabaritResult(status="ok", surfaceParcelleM2=1000.0, zoneImplantationM2=763.0,
                         plafondEmpriseM2=200.0, hauteurReglementaireM=18.0,
                         contourGeoJSON={"type": "Polygon", "coordinates": []})


def test_ao1_gabarit_inconstructible_quand_constructible_false(monkeypatch):
    """A-O1/O2 — `appliquer_verdict_constructibilite` convertit un Gabarit « ok » (763 m², R+5) en
    « inconstructible » + motif, SANS volume, quand potentiel_batir dit `constructible=False`."""
    import labuse.faisabilite.potentiel_batir as pb
    from labuse.gabarit.builder import appliquer_verdict_constructibilite
    monkeypatch.setattr(pb, "potentiel_batir", lambda db, idu: {
        "constructible": False, "rien_a_batir": True,
        "motif": "Habitat interdit dans cette zone", "libelle": "Rien à bâtir"})
    res = _fake_gabarit_ok()
    appliquer_verdict_constructibilite(None, "X", res)
    assert res.status == "inconstructible"
    assert res.message == "Habitat interdit dans cette zone"
    assert res.zoneImplantationM2 is None
    assert res.plafondEmpriseM2 is None
    assert res.hauteurReglementaireM is None


def test_ao1_gabarit_intact_quand_constructible(monkeypatch):
    """A-O1 — un Gabarit sur parcelle constructible n'est PAS touché (pas de régression)."""
    import labuse.faisabilite.potentiel_batir as pb
    from labuse.gabarit.builder import appliquer_verdict_constructibilite
    monkeypatch.setattr(pb, "potentiel_batir", lambda db, idu: {
        "constructible": True, "rien_a_batir": False, "motif": None})
    res = _fake_gabarit_ok()
    appliquer_verdict_constructibilite(None, "X", res)
    assert res.status == "ok"
    assert res.zoneImplantationM2 == 763.0


def test_ao1_gabarit_intact_quand_donnee_absente(monkeypatch):
    """A-O2 — donnée absente (constructible=None) → on NE transforme PAS un trou de donnée en
    interdiction : « incomplete » reste « incomplete »."""
    import labuse.faisabilite.potentiel_batir as pb
    from labuse.gabarit.builder import appliquer_verdict_constructibilite
    monkeypatch.setattr(pb, "potentiel_batir", lambda db, idu: {
        "constructible": None, "rien_a_batir": None, "motif": None})
    res = _fake_gabarit_ok()
    res.status = "incomplete"
    appliquer_verdict_constructibilite(None, "X", res)
    assert res.status == "incomplete"


def test_ao3_estimer_signale_non_constructibilite(monkeypatch):
    """A-O3 — `estimation_annonce` ajoute `constructibilite` + un avertissement quand la parcelle
    n'est pas constructible (prix = repère de marché, pas une valeur à bâtir)."""
    import labuse.pige.api as api
    monkeypatch.setattr(api, "_estimation_annonce_core",
                        lambda db, idu, fiche, surface_hab=None: {"median": 3289, "type_comparateur": "bati"})
    fiche = {"potentiel_a_batir": {"constructible": False, "rien_a_batir": True,
                                   "motif": "Zone non constructible (N)", "zone_lib": "N"}}
    res = api.estimation_annonce(None, "X", fiche)
    assert res["constructibilite"]["constructible"] is False
    assert "avertissement_constructibilite" in res
    assert "repère de marché" in res["avertissement_constructibilite"]


def test_df2_terrain_square_nest_pas_une_surface_habitable():
    """D-F2 — pour un TERRAIN, `square` (= surface du terrain) ne doit PLUS être recopié en
    surface_hab (c'est ce qui faisait flaguer 49/81 terrains « a_qualifier » hors médianes)."""
    from labuse.pige.html_next import aplatir
    rec = aplatir({"list_id": "1", "attributes": [
        {"key": "real_estate_type", "value": "3"},   # terrain
        {"key": "square", "value": "420"},
        {"key": "land_plot_surface", "value": "420"}]})
    assert rec["type"] == "terrain"
    assert rec["surface_hab"] is None
    assert rec["surface_terrain"] == 420


def test_df2_maison_square_reste_habitable():
    """D-F2 — pour une MAISON, `square` reste la surface habitable (pas de régression)."""
    from labuse.pige.html_next import aplatir
    rec = aplatir({"list_id": "2", "attributes": [
        {"key": "real_estate_type", "value": "1"},   # maison
        {"key": "square", "value": "120"},
        {"key": "land_plot_surface", "value": "800"}]})
    assert rec["type"] == "maison" and rec["surface_hab"] == 120 and rec["surface_terrain"] == 800


# ───────────────────────── AVEC base de test (client) ─────────────────────────
pytestmark_db = pytest.mark.db


@pytest.fixture
def client(engine):
    from labuse.api.app import app
    return TestClient(app)


@pytest.mark.db
def test_ao4_taxe_bornee(client):
    """A-O4 — surfaces absurdes et taux négatifs/hors-bornes refusés (422), valide accepté (200)."""
    assert client.get("/outils/taxe-amenagement?surface_taxable_m2=1000000000&taux_communal_pct=3").status_code == 422
    assert client.get("/outils/taxe-amenagement?surface_taxable_m2=100&taux_communal_pct=-5").status_code == 422
    assert client.get("/outils/taxe-amenagement?surface_taxable_m2=100&taux_communal_pct=9999").status_code == 422
    assert client.get("/outils/taxe-amenagement?surface_taxable_m2=100&taux_communal_pct=3").status_code == 200


@pytest.mark.db
def test_ao5_comparer_signale_ignores_tronques_doublons(client):
    """A-O5 — IDU introuvables (ignores), au-delà de 3 (tronques), doublons : tous RENVOYÉS."""
    r = client.get("/compare?idus=ZZZAAA00000000,ZZZBBB00000000")
    d = r.json()
    assert set(d["ignores"]) == {"ZZZAAA00000000", "ZZZBBB00000000"}
    r = client.get("/compare?idus=ZZZAAA00000000,ZZZAAA00000000")
    assert client.get("/compare?idus=ZZZAAA00000000,ZZZAAA00000000").json()["doublons"] == ["ZZZAAA00000000"]
    r = client.get("/compare?idus=A000000000000A,B000000000000B,C000000000000C,D000000000000D")
    assert r.json()["tronques"] == ["D000000000000D"]
    assert r.json()["limite"] == 3


@pytest.mark.db
def test_ao6_etude_zone_refuse_rayon_invalide(client):
    """A-O6 — rayon hors {0,5 ; 1 ; 2 ; 5} km refusé (422), pas remplacé en silence."""
    r = client.post("/outils/etude-zone", json={"lon": 55.5, "lat": -21.0, "rayon_km": 999})
    assert r.status_code == 422
    assert r.json()["detail"]["erreur"] == "rayon_invalide"


@pytest.mark.db
def test_bf1_garde_disparue_sur_toutes_les_routes(client, monkeypatch):
    """B-F1 (test structurel du mandat) — une parcelle disparue du cadastre est refusée AU MÊME
    ENDROIT par TOUS les outils et documents qui prennent un IDU. On force `info_disparue` à
    reconnaître une disparue : aucune route ne doit composer — celle qui le ferait ROUGIRAIT ici."""
    import labuse.cadastre_disparue as cd
    faux = {"idu": "X", "commune": "Saint-Denis", "disparue_le": "2026-09-01",
            "message": "Parcelle disparue du cadastre (version du 2026-09-01).", "remplacee_par": []}
    monkeypatch.setattr(cd, "info_disparue", lambda db, idu: dict(faux, idu=idu))
    IDU, IDU2 = "97416000EI1048", "97414000CT1094"
    # routes DOCUMENT qui REFUSENT (422 + erreur=parcelle_disparue). B-F1 : apporteur / etude-zone /
    # analyse-annonce composaient un document complet — elles refusent désormais ; gabarit / comparatif
    # / financier refusaient déjà.
    docs = [f"/apporteur/{IDU}.pdf", f"/financier/{IDU}.pdf", f"/gabarit/{IDU}.pdf",
            f"/etude-zone.pdf?idu={IDU}", f"/analyse-annonce/{IDU}.pdf",
            f"/comparatif.pdf?idus={IDU},{IDU2}"]
    for url in docs:
        r = client.get(url)
        assert r.status_code == 422, (url, r.status_code)
        assert (r.json().get("detail") or {}).get("erreur") == "parcelle_disparue", url
    # le Dossier NE compose PAS non plus : il rend un PDF d'UNE page portant le message (pré-existant,
    # CHASSE-DONNEES-FIX-1) — 200 mais jamais une fiche complète. On vérifie qu'il ne plante pas.
    assert client.get(f"/dossier/{IDU}.pdf").status_code == 200
    # outil Étude de zone (422)
    r = client.post("/outils/etude-zone", json={"idu": IDU})
    assert r.status_code == 422 and r.json()["detail"]["erreur"] == "parcelle_disparue"
    # outil Estimer (200 avec erreur=parcelle_disparue, median None)
    r = client.get(f"/radar/annonce/estimation/{IDU}")
    assert r.json().get("erreur") == "parcelle_disparue" and r.json().get("median") is None
    # outil Gabarit interactif (incomplete + message disparue, jamais un volume)
    r = client.get(f"/outils/gabarit/{IDU}")
    assert r.json()["status"] == "incomplete" and "disparue" in r.json()["message"].lower()
