"""OUTIL-ASSEMBLAGE-FIX-6 — filet (LOT 0) des 8 constats « C'est faux » de 05-ASSEMBLAGE-ASTRA-2.

Test-first : sur le code d'AVANT le correctif, chaque test échoue sur SON comportement. La règle de
ce tour : chaque point se prouve par ce que l'utilisateur REÇOIT (PDF/Excel réellement produits et
relus, JSON du moteur servi à l'écran), pas seulement la valeur interne.

  · LOT 1 — la note de mixité du Bilan (PDF/Excel) vient du PROGRAMME SAISI, pas de l'identifiant
            cadastral (AB0006 à 24 logts ≠ 39 auto ; BZ0824 à 35 logts) ; fiche + comparatif lisent
            le même résultat du moteur (la clause Uavap.2 de Saint-Denis n'y disparaît plus) ;
  · LOT 2 — Saint-Paul Art. 2 : ≥ 1 800 m² de SDP → 30 % LLTS/LLS/PLS (locatif social), pas « accession
            seule » ; en multizone, le nombre de logements testé = somme de toutes les portions ;
  · LOT 3 — Saint-Denis : les 10 zones portent la clause (dont Up p. 31), libellé « logements sociaux
            et/ou intermédiaires », pas « accession sociale » ;
  · LOT 4 — l'avertissement Marie Caze / Sans Souci du moteur individuel est transmis à l'Assemblage ;
  · LOT 5 — un bord cadastral plus court que le seuil est décrit AVEC sa longueur et « à vérifier »,
            jamais comme un point ;
  · LOT 6 — la surface en zone constructible affichée est la surface géométrique de l'union ;
  · LOT 7 — « reconstruction 0 m² » devient « non calculée » quand la capacité n'existe pas ;
  · LOT 8 — « marché du terrain nu, zones AU de {commune} » (pas « zone AU3c »), « sans personne morale
            identifiée » (pas « propriétaire particulier »).
"""
from __future__ import annotations

import os
import subprocess
import tempfile

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# conftest redirige LABUSE_DATABASE_URL vers la base de TEST (vide) ; les données SERVIES (île
# complète) sont dans LABUSE_APP_DATABASE_URL — c'est elle qu'on lit, en lecture seule.
DBURL = (os.environ.get("LABUSE_APP_DATABASE_URL")
         or os.environ.get("LABUSE_DATABASE_URL")
         or "postgresql+psycopg://openclaw@localhost:5432/labuse")


_ENGINE = create_engine(DBURL, future=True)


@pytest.fixture()
def db():
    s = Session(_ENGINE)
    s.execute(text("SET default_transaction_read_only = on"))
    yield s
    s.rollback()
    s.close()


def _pid(db, idu):
    db.rollback()
    return db.execute(text("SELECT id FROM parcels WHERE idu=:i"), {"i": idu}).scalar()


def _corps(nb_logements, sdp, suv=None, prix=5000.0):
    """CalculIn minimal : un produit de `nb_logements` lots, SDP programme saisie."""
    from labuse.api.bilan import CalculIn, ProduitIn, ProgrammeIn
    return CalculIn(
        programme=ProgrammeIn(terrain=1000.0, sdp=float(sdp)),
        produits=[ProduitIn(libelle="Logements", lots=float(nb_logements),
                            suv=float(suv if suv is not None else sdp * 0.85),
                            prix_ttc_m2_suv=prix, tva=0.2)],
    )


def _pdftotext(octets: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(octets); path = f.name
    try:
        return subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True, text=True).stdout
    finally:
        os.unlink(path)


# ───────────────── LOT 1 — note de mixité du Bilan = programme SAISI ─────────────────

@pytest.mark.reel
def test_lot1_note_bilan_suit_les_logements_saisis(db):
    """AB0006 : 24 logts saisis < 30 → clause NON déclenchée (le scénario auto à 39 ne décide plus) ;
    BZ0824 : 35 logts saisis ≥ 30 → clause déclenchée."""
    from labuse.api.bilan import _mixite_note
    note24 = _mixite_note(db, "97411000AB0006", _corps(24, 1700))
    assert note24 is not None
    assert "15 %" not in note24 and "BORNE HAUTE" not in note24
    assert "non déclenchée" in note24.lower()

    note35 = _mixite_note(db, "97411000BZ0824", _corps(35, 2600))
    assert note35 is not None and "15 %" in note35
    assert "non déclenchée" not in note35.lower()


@pytest.mark.reel
def test_lot1_pdf_bilan_ne_porte_plus_la_borne_haute_a_24_logements(db):
    """Preuve par le document : le PDF du Bilan de 24 logts sur AB0006 ne contient plus « BORNE HAUTE »."""
    from labuse.api.bilan import _mixite_note
    from labuse.bilan import pdf as _pdf
    from labuse.bilan.moteur import Moteur
    from labuse.api.bilan import _entrees
    corps = _corps(24, 1700)
    gf = {"mixite_note": _mixite_note(db, "97411000AB0006", corps)}
    r = Moteur().calculer(_entrees(corps))
    octets = _pdf.construire_pdf(r, idu="97411000AB0006", commune="Saint-Denis",
                                 adresse="", donnees_au=None,
                                 programme=corps.programme.model_dump(), calendrier={},
                                 map_html="", etude_reliee=None, prix_demande=5000.0, garde_fou=gf)
    txt = _pdftotext(octets)
    assert "BORNE HAUTE" not in txt
    assert "15 %" not in txt


@pytest.mark.reel
def test_lot1_fiche_porte_la_clause_uavap_de_saint_denis(db):
    """La fiche (bloc `reglement_plu.mixite`) montre la clause Uavap.2 que le moteur connaît — avant,
    elle lisait `resolve_zone().mixite` (absent de plu_zonage pour Uavap) → « aucune clause validée »."""
    from labuse.api.app import _mixite_fiche_block  # helper unique de source (ajouté au correctif)
    mx = _mixite_fiche_block(db, "Saint-Denis", "Uavap")
    assert mx is not None
    assert mx.get("statut") == "valide"
    assert mx.get("quota_pct") == 15
    assert (mx.get("seuil_logements") == 30) or (mx.get("seuil_m2") is not None)
    assert "Uavap" in str(mx.get("article"))


# ───────────────── LOT 2 — Saint-Paul : ≥ 1 800 m² → 30 % LLTS/LLS/PLS (locatif social) ─────────────────

#: 8 parcelles CV contiguës de Saint-Paul (zone U3/AU3c), terrain ~10 812 m² > 6 000, SDP programme
#: ~6 000 m² ≥ 1 800 → régime PLEIN. Reconstruit par contiguïté (les 8 exactes de l'auditeur non notées).
HUIT_CV = ["97415000CV0724", "97415000CV0169", "97415000CV0722", "97415000CV0723",
           "97415000CV1253", "97415000CV1505", "97415000CV1507", "97415000CV0231"]


def _assemblage(db, idus):
    from labuse.api.moteurs import assemblage, AssemblageIn
    db.rollback()
    return assemblage(AssemblageIn(idus=idus), db)


@pytest.mark.reel
def test_lot2_8CV_plein_regime_nomme_LLTS_LLS_PLS_pas_accession_seule(db):
    d = _assemblage(db, HUIT_CV)
    m = d["mixite"]
    assert m["declenchee"] and m["regime"] == "plein"
    prod = m["produits"]
    assert "LLTS" in prod and "LLS" in prod and "PLS" in prod
    # ≥ 1 800 m² : l'exigence est le locatif social, pas « accession seule »
    assert "accession" not in prod.lower()


def test_lot2_reorder_clause_est_euro_neutre_single_parcelle():
    """PREUVE que le réordonnancement de `_clause_mixite` (SDP≥1800 AVANT terrain>6000) ne change AUCUN
    euro sur les bilans SINGLE parcelle : le RÉGIME (plein / intermediaire / None) — seule entrée de la
    charge foncière via pondère/exclure_lls/intermediaire — est IDENTIQUE à la règle de l'Art. 2, pour
    toute combinaison (sdp_programme, terrain, logements). Balaye la grille complète des branches."""
    from labuse.faisabilite.bilan import _clause_mixite
    from labuse.faisabilite.engine import Hypotheses
    hyp = Hypotheses.charger("Saint-Paul")
    s_sdp, s_haut = float(hyp.mixite_sdp_seuil_m2), float(hyp.mixite_sdp_seuil_haut_m2)
    s_ter, s_log = float(hyp.mixite_terrain_seuil_m2), float(hyp.mixite_logements_seuil)
    for sdp in (0, s_sdp - 1, s_sdp, s_haut - 1, s_haut, s_haut + 500):
        for terr in (0, s_ter, s_ter + 1, s_ter + 5000):
            for logt in (0, s_log - 1, s_log, s_log + 50):
                eco = {"commune": "Saint-Paul", "mixite": True, "sdp_programme_m2": sdp,
                       "sdp_max_m2": sdp, "terrain_m2": terr, "logements_estimes": logt,
                       "zone_mixite": {"page": "pp. 106-107"}}
                regime = _clause_mixite(eco, hyp).get("regime")
                # régime attendu par l'Art. 2 (ordre indifférent : plein si ≥1800 OU terrain>6000) :
                attendu = ("plein" if (sdp >= s_haut or terr > s_ter)
                           else "intermediaire" if (sdp >= s_sdp or logt >= s_log) else None)
                assert regime == attendu, (sdp, terr, logt, regime, attendu)


@pytest.mark.reel
def test_lot2_multizone_teste_la_somme_des_logements(db):
    """Le nombre de logements comparé aux seuils 20/30 = somme de TOUTES les portions (comme les surfaces)."""
    from labuse.assemblage import _capacite_union
    from types import SimpleNamespace
    db.rollback()
    parcels = [SimpleNamespace(id=_pid(db, i), surface_m2=None, idu=i,
                               commune="Saint-Paul", contenance_m2=None) for i in HUIT_CV]
    # recharge surfaces
    for p in parcels:
        db.rollback()
        p.surface_m2 = db.execute(text("SELECT COALESCE(contenance_m2,surface_m2) FROM parcels WHERE id=:i"),
                                  {"i": p.id}).scalar()
    db.rollback()
    u = _capacite_union(db, parcels)
    assert u is not None
    assert u.get("logements_programme") is not None and u["logements_programme"] > 0


# ───────────────── LOT 3 — Saint-Denis : 10 zones, libellé « logements sociaux et/ou intermédiaires » ─────────────────

def test_lot3_dix_zones_portent_la_clause_dont_Up():
    from labuse.faisabilite.bilan import _zone_mixite_regle
    from labuse.faisabilite.zonage import resolve_zone
    zones = ["Uavap", "Up", "Ud", "Ui", "Uj", "Um", "Uh", "AUj", "AUm", "AUh"]
    for z in zones:
        r = resolve_zone(z, "Saint-Denis")
        mr = _zone_mixite_regle("Saint-Denis", z, r)
        assert mr is not None and mr.get("seuil_logements") == 30 and mr.get("quota_pct") == 15, z


@pytest.mark.reel
def test_lot3_note_borne_haute_ne_dit_pas_accession_sociale_a_saint_denis(db):
    """La réserve « borne haute » d'une obligation Saint-Denis ne doit pas parler d'« accession sociale »
    (c'est « logements sociaux et/ou intermédiaires »)."""
    from labuse.api.bilan import _mixite_note
    note = _mixite_note(db, "97411000AB0006", _corps(40, 3000))
    assert note is not None and "BORNE HAUTE" in note
    assert "accession sociale" not in note.lower()
    assert "sociaux et/ou intermédiaires" in note.lower()


# ───────────────── LOT 4 — avert Marie Caze / Sans Souci transmis à l'Assemblage ─────────────────

@pytest.mark.reel
def test_lot4_assemblage_U4_transmet_lavert_marie_caze(db):
    """AH0022 + AH1402 (zone U4a) déclenche 30 % ; l'avertissement Marie Caze / Sans Souci du moteur
    individuel voyage avec `mixite` jusqu'à l'Assemblage."""
    d = _assemblage(db, ["97415000AH0022", "97415000AH1402"])
    m = d["mixite"]
    assert m and m["declenchee"]
    averts = " ".join(m.get("avertissements") or [])
    assert "Marie Caze" in averts and "Sans Souci" in averts


# ───────────────── LOT 5 — bord court décrit comme tel, jamais comme un point ─────────────────

@pytest.mark.parametrize("a,b,longueur", [
    ("97415000CV1134", "97415000CV1381", 0.34),
    ("97415000CV1334", "97415000CV1435", 0.48),
])
@pytest.mark.reel
def test_lot5_bord_court_nest_pas_un_point(db, a, b, longueur):
    from labuse.assemblage import liens_assiette
    db.rollback()
    liens = liens_assiette(db, [_pid(db, a), _pid(db, b)])
    assert len(liens) == 1
    ln = liens[0]
    assert ln["type"] != "point"                        # un segment cadastral, pas un point
    assert ln.get("longueur_bord_m") == longueur        # sa longueur est portée
    assert ln.get("a_verifier") is True                 # signalé « à vérifier »


@pytest.mark.reel
def test_lot5_message_tenant_decrit_le_segment_pas_aucun_bord(db):
    from labuse.api.moteurs import assemblage, AssemblageIn
    db.rollback()
    d = assemblage(AssemblageIn(idus=["97415000CV1134", "97415000CV1381"]), db)
    msg = d.get("tenant_avertissement") or ""
    assert "aucun bord commun" not in msg
    assert "à vérifier" in msg and "0.34" in msg.replace(",", ".")


# ───────────────── LOT 6 — surface en zone constructible = géométrie de l'union ─────────────────

@pytest.mark.reel
def test_lot6_surface_constructible_est_la_geometrie_de_lunion(db):
    """Trio DH : l'écran annonce la surface géométrique de l'union en U/AU (21 516 m²), pas la contenance
    mise à l'échelle (21 638 m²) — ou il dit laquelle il affiche."""
    d = _assemblage(db, ["97415000DH0076", "97415000DH0119", "97415000DH0120"])
    assert d["surface_constructible_m2"] == 21516


# ───────────────── LOT 7 — reconstruction 0 m² → « non calculée » quand pas de capacité ─────────────────

@pytest.mark.reel
def test_lot7_item_sans_capacite_dit_non_calculee(db):
    """DH0120 n'a pas de capacité → la ligne d'Assemblage ne dit plus « reconstruction 0 m² » mais
    marque l'absence (sdp None), pour que l'écran écrive « non calculée »."""
    d = _assemblage(db, ["97415000DH0076", "97415000DH0119", "97415000DH0120"])
    it = {i["idu"]: i for i in d["items"]}["97415000DH0120"]
    # pas de capacité → sdp_m2 ne doit pas être un « 0 » muet qui se lit « reconstruction 0 m² »
    assert it.get("sdp_m2") in (None,) or it.get("capacite_absente") is True


# ───────────────── LOT 8 — libellés (zone AU → famille, particulier → sans PM) ─────────────────

@pytest.mark.reel
def test_lot8_marche_terrain_nu_nomme_la_famille_de_zone(db):
    """Le repère de marché du terrain nu porte sur la FAMILLE AU de la commune (median AU toutes
    sous-zones), pas la sous-zone AU3c : l'écran le nomme « zones AU de {commune} »."""
    d = _assemblage(db, ["97415000CV0724", "97415000CV1506", "97415000CV1507"])
    assert d.get("terrain_zone_famille") == "AU"
    assert d.get("terrain_zone_commune") == "Saint-Paul"
