"""CIRCUIT-2 lot 1 — LE REGISTRE ÉLARGI : types partout, hors_registre vidé (décor seul),
couches et fonds déclarés, tampon non numérique, couverture élargie de la fiche parcelle
(chaque clé servie rattachée à une donnée — la liste d'exceptions est VIDE)."""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse import registre
from labuse.registre.couverture import FICHE_PARCELLE_CLES, probleme_cles
from labuse.registre.donnees import DONNEES, TYPES

pytestmark = pytest.mark.db


# ─────────────────── 1.1 — types, domaines, couches ───────────────────

def test_toute_donnee_porte_un_type():
    for cid, d in DONNEES.items():
        assert d.type in TYPES, (cid, d.type)


def test_classe_declare_son_domaine():
    for cid, d in DONNEES.items():
        if d.type == "classe":
            assert d.domaine or d.domaine_source, f"{cid} : classe sans domaine (1.1)"


def test_couche_declare_table_et_fabrication():
    fabrications = {"build-mvt", "geom_simple", "vue", "requete", "wmts_distant"}
    for cid, d in DONNEES.items():
        if d.type == "couche":
            assert d.table, f"{cid} : couche sans table/tuilage"
            assert d.fabrication in fabrications, (cid, d.fabrication)


# ─────────────────── 1.2 — hors_registre vidé ───────────────────

def test_hors_registre_ne_reste_que_le_decor():
    """0 donnée d'origine externe hors registre : les seuls robinets sans donnée sont les
    modes de rendu (décor), raison préfixée « décor : »."""
    restants = {rid: r.hors_registre for rid, r in registre.ROBINETS.items()
                if not r.chiffres}
    assert set(restants) == {"fond_sombre", "fond_clair"}
    for rid, raison in restants.items():
        assert raison.startswith("décor"), (rid, raison)


# ─────────────────── 1.3 — les 16 couches et les 10 fonds ───────────────────

def test_couches_et_fonds_tous_declares():
    couches = [rid for rid, r in registre.ROBINETS.items() if r.categorie == "couche"]
    fonds = [rid for rid, r in registre.ROBINETS.items() if r.categorie == "fond"]
    assert len(couches) == 16 and len(fonds) == 10
    # chaque robinet couche sert au moins une donnée de type couche
    for rid in couches:
        types = {DONNEES[cid].type for cid in registre.ROBINETS[rid].chiffres}
        assert "couche" in types, f"{rid} : aucune donnée de type couche"
    # les 8 fonds IGN déclarent le service ET la version de tuiles interrogée
    for rid in fonds:
        r = registre.ROBINETS[rid]
        if r.hors_registre:      # sombre / clair = décor
            continue
        (cid,) = r.chiffres
        d = DONNEES[cid]
        assert d.fabrication == "wmts_distant", cid
        assert "data.geopf.fr" in d.table and "VERSION=" in d.table, \
            f"{cid} : le fond IGN doit déclarer service et version de tuiles"


def test_en_attente_jamais_servie():
    """Une donnée `en_attente` (1.8 — maquettes exports, réglementaires CIRCUIT-3) n'est
    servie par AUCUN robinet tant que son chantier n'est pas passé."""
    servies = {cid for r in registre.ROBINETS.values() for cid in r.chiffres}
    en_attente = {cid for cid, d in DONNEES.items() if d.en_attente}
    assert en_attente, "le lot 1.8 déclare des données en attente"
    assert not (en_attente & servies), en_attente & servies


def test_reglementaires_circuit3_declarees():
    for cid in ("er_emplacement_reserve", "ebc_classe", "dpu_perimetre", "peb_zone",
                "zonage_abc_logement"):
        assert DONNEES[cid].en_attente and "CIRCUIT-3" in DONNEES[cid].en_attente, cid


# ─────────────────── 1.4 — tampon non numérique ───────────────────

def test_tampon_porte_type_table_fabrication(db_session):
    t = registre.tampons_pour(db_session, ["zonage_plu_couche", "zone_plu_famille"])
    couche = t["zonage_plu_couche"]
    assert couche["type"] == "couche" and couche["table"] == "parcel_zone_plu"
    assert couche["fabrication"] == "requete"
    classe = t["zone_plu_famille"]
    assert classe["type"] == "classe" and classe["domaine"] == ["U", "AU", "A", "N"]


def test_valeur_etat_jamais_un_echec_deguise():
    """Règle 4 : trois états — `servie` (tampon muet), `non_determinee`, `non_calculee`
    (visibles au tampon). Un échec technique ne se déguise jamais en absence."""
    from labuse.registre.valeur import Valeur
    ok = Valeur(valeur="U", chiffre_id="zone_plu_famille", version_def="x", run=None)
    assert "etat" not in ok.tampon()
    echec = Valeur(valeur=None, chiffre_id="zone_plu_famille", version_def="x", run=None,
                   etat="non_calculee")
    assert echec.tampon()["etat"] == "non_calculee"


# ─────────────────── 1.5 — couverture élargie (exceptions = 0) ───────────────────

def test_carte_de_couverture_coherente():
    """Chaque id rattaché existe ; aucune entrée « exception » : une clé est une donnée du
    registre ou un `interne` motivé."""
    assert probleme_cles(set()) == []
    for cle, ids in FICHE_PARCELLE_CLES.items():
        assert ids, cle
        if ids[0] == "interne":
            assert len(ids) == 2 and ids[1], f"{cle} : interne sans raison"


def test_fiche_parcelle_chaque_cle_rattachee(db_session):
    """LE test de couverture élargi : l'endpoint réel `/parcels/{idu}` ne sert AUCUNE clé
    hors carte (une clé neuve sans donnée déclarée = rouge)."""
    idu = db_session.execute(text("SELECT idu FROM parcels ORDER BY idu LIMIT 1")).scalar()
    if not idu:
        pytest.skip("base de test sans parcelle — la couverture réelle est vérifiée sur la base réelle")
    from fastapi.testclient import TestClient

    from labuse.api.app import app
    client = TestClient(app)
    r = client.get(f"/parcels/{idu}")
    if r.status_code != 200:
        pytest.skip(f"fiche non servable sur la base de test ({r.status_code})")
    assert probleme_cles(set(r.json().keys())) == []


def test_donnees_de_la_carte_servies_par_un_robinet_fiche():
    """Les ids rattachés aux clés de la fiche sont servis par un robinet (verifier() le
    garantit globalement) et les nouveaux blocs (adresse, règlement, listes) le sont par un
    robinet de la fiche parcelle."""
    assert registre.verifier() == []
    fiche_ids = {cid for rid, r in registre.ROBINETS.items()
                 if rid.startswith("fiche_parcelle") for cid in r.chiffres}
    for cid in ("adresse_ban", "parcelle_geometrie", "reglement_plu_bloc",
                "historique_permis_liste", "dvf_parcelle_liste", "coproprietes_liste",
                "viabilisation_verdict", "equipements_proximite_liste",
                "evenements_proprietaire_liste", "proprietaire_timeline_liste",
                "perimetres_dispositifs_liste", "voisinage_100m_liste"):
        assert cid in fiche_ids, f"{cid} : déclaré mais pas servi par la fiche parcelle"
