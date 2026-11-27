"""OUTIL-ASSEMBLAGE-FIX-8 — filet (LOT 0) des constats « C'est faux » / « Ça pourrait être mieux »
de 05-ASSEMBLAGE-ASTRA-3. Test-first : sur le code d'AVANT le correctif, chacun échoue sur SON point.

  · LOT 1 — le Bilan compte des COMMERCES pour la mixité (24 logts + 8 commerces → 15 % à 32 lots) ;
            la note dit « part aidée non chiffrée » même quand le prix aidé EST saisi ; l'écran de
            saisie ne porte aucune mention de mixité.
  · LOT 2 — l'avertissement d'exclusion ZAC (Marie Caze / Sans Souci) et l'obligation se perdent entre
            supports ; la fiche dit « Aucune clause » pour Saint-Paul alors que le bilan cite 30 % ;
            Saint-Denis est qualifié d'« accession sociale » (faux) ; le dénominateur Saint-Paul manque.
  · LOT 4 — un bord cadastral COURT (type `bord_court`, `vide_m` = null) faisait planter l'écran.

Base servie en lecture seule (LABUSE_APP_DATABASE_URL).
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

DBURL = (os.environ.get("LABUSE_APP_DATABASE_URL")
         or os.environ.get("LABUSE_DATABASE_URL")
         or "postgresql+psycopg://openclaw@localhost:5432/labuse")
_ENGINE = create_engine(DBURL, future=True)

# Identifiants de l'audit (préfixes commune résolus en base).
AB0006_SD = "97411000AB0006"   # Saint-Denis, zone Uavap : 30 logts collectif → 15 % sociaux et/ou interm.
AH0022_SP = "97415000AH0022"   # Saint-Paul, zone U4a (livret 4) — exclusion ZAC Marie Caze / Sans Souci
CV1498_SP = "97415000CV1498"   # Saint-Paul, secteur SMS
DH0119_SP = "97415000DH0119"   # Saint-Paul, zone U2h (sans leaf)
CV1134, CV1381 = "97415000CV1134", "97415000CV1381"   # paire à bord court 0,34 m


@pytest.fixture()
def db():
    s = Session(_ENGINE)
    s.execute(text("SET default_transaction_read_only = on"))
    yield s
    s.rollback()
    s.close()


def _mk(prods, sdp=None):
    from labuse.api.bilan import CalculIn, ProduitIn, ProgrammeIn
    return CalculIn(produits=[ProduitIn(**p) for p in prods], programme=ProgrammeIn(sdp=sdp))


# ─────────────── LOT 1 — seuls les logements comptent, note véridique, écran ───────────────

@pytest.mark.reel
def test_lot1_commerces_ne_declenchent_pas_la_mixite(db):
    from labuse.api.bilan import _mixite_note
    # 24 logts + 8 commerces : 24 < 30 → clause NON déclenchée (les commerces ne comptent pas).
    note = _mixite_note(db, AB0006_SD, _mk([
        {"libelle": "Logements", "lots": 24, "suv": 1700, "prix_ttc_m2_suv": 4000},
        {"libelle": "Commerces", "lots": 8, "suv": 600, "prix_ttc_m2_suv": 2500}]))
    assert note is not None
    assert "non déclenchée" in note
    assert "15 %" not in note and "15%" not in note


@pytest.mark.reel
def test_lot1_35_logements_declenchent(db):
    from labuse.api.bilan import _mixite_note
    note = _mixite_note(db, AB0006_SD, _mk([{"libelle": "Logements", "lots": 35, "suv": 2500, "prix_ttc_m2_suv": 4000}]))
    assert note and "15 %" in note


@pytest.mark.reel
def test_lot1_part_aidee_chiffree_quand_prix_saisi(db):
    from labuse.api.bilan import _mixite_note, _mixite_structuree
    corps = _mk([
        {"libelle": "Logements libres", "lots": 29, "suv": 2000, "prix_ttc_m2_suv": 4000},
        {"libelle": "PLS", "lots": 6, "suv": 360, "prix_ttc_m2_suv": 2200}])
    note = _mixite_note(db, AB0006_SD, corps)
    # Le prix de la part aidée EST saisi → la note ne doit PLUS dire « non chiffrée ».
    assert note and "non chiffrée" not in note
    s = _mixite_structuree(db, AB0006_SD, corps)
    assert s and s["borne_haute"] is False


@pytest.mark.reel
def test_lot1_borne_haute_nomme_la_part_manquante(db):
    from labuse.api.bilan import _mixite_structuree
    s = _mixite_structuree(db, AB0006_SD, _mk([{"libelle": "Logements libres", "lots": 35, "suv": 2500, "prix_ttc_m2_suv": 4000}]))
    assert s and s["borne_haute"] is True
    assert s["charge_reserve"] and "logement" in s["charge_reserve"].lower()


@pytest.mark.reel
def test_lot1_ecran_de_saisie_porte_la_mixite(db):
    # L'écran appelle /bilan/{idu}/calcul ; la réponse doit porter res.mixite (note non vide).
    from labuse.api.bilan import calculer_bilan
    out = calculer_bilan(AB0006_SD, _mk([{"libelle": "Logements", "lots": 35, "suv": 2500, "prix_ttc_m2_suv": 4000}]), db)
    assert out.get("mixite") and out["mixite"]["note"]


# ─────────────── LOT 2 — source unique, avert, Saint-Denis sans « accession sociale », dénominateur ───────────────

def _pid(db, idu):
    db.rollback()
    return db.execute(text("SELECT id FROM parcels WHERE idu=:i"), {"i": idu}).scalar()


@pytest.mark.reel
def test_lot2_avert_zac_voyage_dans_la_note_bilan(db):
    from labuse.api.bilan import _mixite_note
    # AH0022 (U4a) déclenchée → la note du Bilan porte l'avert d'exclusion ZAC Marie Caze / Sans Souci.
    note = _mixite_note(db, AH0022_SP, _mk([{"libelle": "Logements", "lots": 40, "suv": 3000, "prix_ttc_m2_suv": 4500}]))
    assert note and "Marie Caze" in note and "Sans Souci" in note


@pytest.mark.reel
def test_lot2_saint_denis_jamais_accession_sociale(db):
    from labuse.faisabilite.bilan import compute_bilan_servi
    b, _ = compute_bilan_servi(db, _pid(db, AB0006_SD))
    joined = " ".join(getattr(b, "avertissements", None) or [])
    assert "accession sociale" not in joined
    # et la part visée est bien nommée
    assert "sociaux et/ou intermédiaires" in joined or "aidé" in joined.lower()


@pytest.mark.reel
def test_lot2_fiche_porte_la_clause_pour_saint_paul(db):
    from labuse.api.app import _mixite_fiche_block
    from labuse.faisabilite.zonage import resolve_zone  # noqa: F401  (import de cohérence)
    for idu, zone in ((AH0022_SP, "U4a"), (CV1498_SP, "AU3c"), (DH0119_SP, "U2h")):
        fb = _mixite_fiche_block(db, "Saint-Paul", zone)
        assert fb and fb.get("statut") == "valide" and fb.get("quota_pct") == 30.0, (idu, zone, fb)


@pytest.mark.reel
def test_lot2_denominateur_saint_paul_dans_la_note(db):
    from labuse.api.bilan import _mixite_note
    note = _mixite_note(db, CV1498_SP, _mk([{"libelle": "Logements", "lots": 35, "suv": 2500, "prix_ttc_m2_suv": 4500}]))
    assert note and "Dénominateur" in note and "arrondi supérieur" in note


# ─────────────── LOT 4 — le bord court est un lien `bord_court` (vide_m null) : l'écran doit le gérer ───────────────

@pytest.mark.reel
def test_lot4_bord_court_est_un_type_distinct_sans_vide(db):
    from labuse.assemblage import liens_assiette
    liens = liens_assiette(db, [_pid(db, CV1134), _pid(db, CV1381)])
    assert len(liens) == 1
    ln = liens[0]
    assert ln["type"] == "bord_court"
    assert ln["vide_m"] is None          # c'est CE null qui plantait le formatage de l'écran
    assert ln["longueur_bord_m"] and ln["longueur_bord_m"] > 0


# ─────────────── LOT 5 — motif « zone rouge » faux (DH0119 en PPR bleu) + comparatif ───────────────

@pytest.mark.reel
def test_lot5_dh0119_motif_pas_zone_rouge_sans_ppr_rouge(db):
    from labuse.faisabilite.potentiel_batir import potentiel_batir
    pb = potentiel_batir(db, DH0119_SP)
    motif = pb.get("motif") or ""
    # DH0119 est en PPR BLEU (B2) — aucune intersection avec une couche d'INTERDICTION (rouge).
    assert "zone rouge" not in motif.lower() or "hors zone rouge" in motif.lower()


@pytest.mark.reel
def test_lot5_vraie_zone_rouge_conserve_le_motif(db):
    # Non-régression : une parcelle réellement ≥ 95 % en PPR rouge garde « Zone rouge du PPR ».
    from labuse.faisabilite.potentiel_batir import potentiel_batir
    pb = potentiel_batir(db, "97410000AO0534")
    assert "Zone rouge du PPR" in (pb.get("motif") or "")


def test_lot5_comparatif_capacite_non_calculee():
    from labuse.exports.blocs.comparatif import rendu
    rows = [{"idu": "97415000DH0120", "constructible": False,
             "verdict_motif": "Zone non constructible — naturelle", "zone": "N", "surface_m2": 1000},
            {"idu": "97415000CV1504", "constructible": False,
             "cause_libelle": "Terrain trop exigu", "zone": "U", "surface_m2": 300}]
    html = rendu(rows)
    assert "capacité non calculée" in html
    assert html.count("capacité non calculée") >= 2


# ─────────────── LOT 6 — surfaces effectivement retranchées (brut + effectif) ───────────────

@pytest.mark.reel
def test_lot6_retranchement_effectif_a_cote_du_brut(db):
    from labuse.assemblage import aggregate_assiette
    from sqlalchemy import text as _t
    for idus, cle, brut, eff in (
        (["97415000DH0191", "97415000DH0098"], "ppr_rouge", 935, 41),
        (["97415000EP0971", "97415000EP0762"], "emplacement_reserve", 2386, 1827)):
        db.rollback()
        parcels = db.execute(_t("SELECT id, idu, round(COALESCE(contenance_m2, surface_m2)) AS surface_m2, "
                                "commune FROM parcels WHERE idu = ANY(:i)"), {"i": idus}).all()
        u = aggregate_assiette(db, parcels)
        rt = (u or {}).get("retranchements") or {}
        assert abs(rt.get(f"{cle}_m2", 0) - brut) <= 3, (idus, rt)
        assert abs(rt.get(f"{cle}_effectif_m2", 0) - eff) <= 5, (idus, rt)
        assert rt[f"{cle}_effectif_m2"] < rt[f"{cle}_m2"]
