"""PLU-MAJ-2 LOT 1 — le détecteur : un changement d'IDENTIFIANT, de DATE ou de STATUT
(annulation partielle comprise) ne passe plus. L'ancienne sonde lisait un COMPTE (totalFeatures) :
aveugle au remplacement 1→1 ET à une republication/annulation à identifiant constant. On signe
désormais le document publié par (idurba | horodatage GPU | statut) : la signature bouge → vu.

Les cas d'ancrage sont l'état RÉEL du Géoportail au 15/11/2026 (FRAICHEUR-PROD-2 §A.2) :
  · Saint-Denis   97411_PLU_20260805 (approuvé 05/08, publié 24/08) vs servi 20260423 — remplacement ;
  · La Possession 97408_PLU_20260625 (modif. n°2, publiée 21/10) vs servi 20251217 — remplacement ;
  · Le Port       97407_PLU_20241209 REPUBLIÉ le 18/11/2025 « partiellement annulé » — idurba constant.
"""
from datetime import date

import pytest
from sqlalchemy import text

from labuse import controle_plu as cp


def _c(idurba):
    return ({"idurba": idurba, "date": cp._date8(idurba), "ingere_le": None, "n": 1, "n_idurba": 1}
            if idurba else None)


def _gpu(idurba, ts=None):
    return {"idurba": idurba, "du_type": "PLU", "timestamp": ts}


# ─────────────────────────── la signature et ses briques (pur) ───────────────────────────

def test_ts_date():
    assert cp._ts_date("2025-11-18T06:36:20.630Z") == date(2025, 11, 18)
    assert cp._ts_date(None) is None
    assert cp._ts_date("illisible") is None


def test_signature_capte_les_trois_axes():
    """La signature bouge si l'IDENTIFIANT, la DATE (dans l'idurba) OU l'horodatage/statut change."""
    base = cp.signature_gpu(_gpu("97407_PLU_20241209", "2024-12-10T00:00:00Z"), "a_jour")
    # 1) identifiant/date différents
    assert cp.signature_gpu(_gpu("97407_PLU_20250101", "2024-12-10T00:00:00Z"), "a_jour") != base
    # 2) REPUBLICATION à identifiant constant (horodatage postérieur) → signature différente
    assert cp.signature_gpu(_gpu("97407_PLU_20241209", "2025-11-18T06:36:20.630Z"), "a_jour") != base
    # 3) STATUT différent à tout le reste constant
    assert cp.signature_gpu(_gpu("97407_PLU_20241209", "2024-12-10T00:00:00Z"), "annule_partiel") != base
    assert cp.signature_gpu(None, "a_jour") is None


def test_sonde_par_compte_aveugle_la_signature_voit():
    """Démonstration du trou corrigé : le COMPTE (1 document avant, 1 après) ne bouge pas sur une
    republication ; la SIGNATURE, elle, change."""
    avant = {"totalFeatures": 1}
    apres = {"totalFeatures": 1}
    assert avant["totalFeatures"] == apres["totalFeatures"]           # l'ancienne sonde : rien vu
    sig_avant = cp.signature_gpu(_gpu("97407_PLU_20241209", "2024-12-10T00:00:00Z"), "a_jour")
    sig_apres = cp.signature_gpu(_gpu("97407_PLU_20241209", "2025-11-18T06:36:20.630Z"), "annule_partiel")
    assert sig_avant != sig_apres                                     # la nouvelle sonde : vu


# ─────────────────────────── détection d'un remplacement (échoue sur l'état actuel) ───────────────────────────

def test_detecte_remplacement_saint_denis():
    """Saint-Denis servi au 23/04, le Géoportail sert le 05/08 → desync FORT (le zonage bouge)."""
    ing = {"zonage": _c("97411_PLU_20260423"), "prescriptions": _c("97411_PLU_20260423"),
           "informations": None}
    reg = {"idurba": "97411_PLU_20260423", "date": date(2026, 4, 23), "etat": "calibree"}
    e = cp.verdict_pur("97411", "Saint-Denis", "97411_PLU_20260805", "geoportail", ing, reg,
                       gpu=_gpu("97411_PLU_20260805", "2026-08-24T10:12:05Z"), statut="a_jour")
    assert e.etat == "desync" and e.niveau == "fort"
    assert "zonage" in e.couches_en_retard
    assert e.nouveau == "97411_PLU_20260805" and e.ancien == "97411_PLU_20260423"


def test_detecte_nouvelle_version_la_possession():
    """La Possession servie au 17/12/2025, le Géoportail sert la modif. n°2 du 25/06/2026 → desync FORT."""
    ing = {"zonage": _c("97408_PLU_20251217"), "prescriptions": _c("97408_PLU_20251217"),
           "informations": None}
    reg = {"idurba": "97408_PLU_20251217", "date": date(2025, 12, 17), "etat": "calibree"}
    e = cp.verdict_pur("97408", "La Possession", "97408_PLU_20260625", "geoportail", ing, reg,
                       gpu=_gpu("97408_PLU_20260625", "2026-10-21T05:09:02Z"), statut="a_jour")
    assert e.etat == "desync" and e.niveau == "fort"
    assert "zonage" in e.couches_en_retard
    assert e.nouveau == "97408_PLU_20260625"


# ─────────────────────────── la vigilance de STATUT (annulation partielle) ───────────────────────────

def test_vigilance_statut_annulation_partielle_le_port():
    """Le Port : idurba et couches IDENTIQUES, mais le document est « annulé partiellement » et republié
    le 18/11/2025 → la commune reste `a_jour` (zonage résidentiel servi inchangé) MAIS porte une
    vigilance de statut, et la signature intègre l'horodatage + le statut."""
    ing = {"zonage": _c("97407_PLU_20241209"), "prescriptions": _c("97407_PLU_20241209"),
           "informations": None}
    reg = {"idurba": "97407_PLU_20241209", "date": date(2024, 12, 9), "etat": "calibree"}
    e = cp.verdict_pur("97407", "Le Port", "97407_PLU_20241209", "geoportail", ing, reg,
                       gpu=_gpu("97407_PLU_20241209", "2025-11-18T06:36:20.630Z"), statut="annule_partiel")
    assert e.etat == "a_jour" and e.couches_en_retard == []          # le zonage servi reste bon
    assert e.vigilance_statut is True
    assert e.statut_motif and "annulé" in e.statut_motif
    assert "annule_partiel" in (e.signature or "")
    assert "2025-11-18" in (e.gpu_timestamp or "")


def test_vigilance_republication_idurba_constant():
    """Une republication nette (horodatage > idurba + 45 j) à identifiant constant et sans retard de
    couche lève une vigilance « statut à vérifier », même sans statut curaté."""
    ing = {"zonage": _c("97410_PLU_20200206"), "prescriptions": _c("97410_PLU_20200206"),
           "informations": None}
    reg = {"idurba": "97410_PLU_20200206", "date": date(2020, 2, 6), "etat": "calibree"}
    e = cp.verdict_pur("97410", "Saint-Benoît", "97410_PLU_20200206", "geoportail", ing, reg,
                       gpu=_gpu("97410_PLU_20200206", "2024-03-01T00:00:00Z"), statut="a_jour")
    assert e.etat == "a_jour" and e.vigilance_statut is True
    assert e.statut_motif and "republié" in e.statut_motif


def test_pas_de_vigilance_quand_horodatage_proche():
    """Publication normale (horodatage proche de l'approbation) → aucune vigilance de statut."""
    ing = {"zonage": _c("97415_PLU_20251217"), "prescriptions": _c("97415_PLU_20251217"),
           "informations": None}
    reg = {"idurba": "97415_PLU_20251217", "date": date(2025, 12, 17), "etat": "calibree"}
    e = cp.verdict_pur("97415", "Saint-Paul", "97415_PLU_20251217", "geoportail", ing, reg,
                       gpu=_gpu("97415_PLU_20251217", "2025-12-20T00:00:00Z"), statut="a_jour")
    assert e.etat == "a_jour" and e.vigilance_statut is False and e.statut_motif is None


# ─────────────────────────── le PLU entre dans le contrôle de millésime (base) ───────────────────────────

@pytest.mark.db
def test_plu_entre_dans_controle_millesime(db_session):
    """Après une détection, les communes PLU en décalage et en vigilance de statut ressortent au
    contrôle de millésime — `en_retard` pour un remplacement, `a_verifier` pour une annulation
    partielle — au même titre que DVF/SITADEL."""
    from labuse import controle_millesime
    s = db_session
    cp.ensure_table(s)
    s.execute(text("DELETE FROM plu_veille_etat WHERE insee IN ('97408','97407')"))
    # un remplacement non suivi (La Possession) …
    s.execute(text(
        "INSERT INTO plu_veille_etat (insee, commune, etat, niveau, reference, ancien, nouveau, "
        " vigilance_statut, date_modif) VALUES ('97408','La Possession','desync','fort',"
        " '97408_PLU_20260625','97408_PLU_20251217','97408_PLU_20260625', false, '2026-06-25')"))
    # … et une annulation partielle (Le Port), couches à jour.
    s.execute(text(
        "INSERT INTO plu_veille_etat (insee, commune, etat, reference, vigilance_statut, statut_motif) "
        "VALUES ('97407','Le Port','a_jour','97407_PLU_20241209', true, "
        "'PLU partiellement annulé — zonage résidentiel servi inchangé.')"))

    lignes = cp.lignes_controle_millesime(s)
    par_nom = {ln["name"]: ln for ln in lignes}
    assert par_nom["PLU — La Possession"]["etat"] == "en_retard"
    assert par_nom["PLU — La Possession"]["millesime_publie"] == "97408_PLU_20260625"
    assert par_nom["PLU — La Possession"]["millesime_ingere"] == "97408_PLU_20251217"
    assert par_nom["PLU — Le Port"]["etat"] == "a_verifier"

    # et le contrôle de fraîcheur les compte parmi ses retards / à-vérifier.
    r = controle_millesime.rejouer_nuit(s)
    noms_retard = {e["name"] for e in r["retards"]}
    noms_verif = {e["name"] for e in r["a_verifier"]}
    assert "PLU — La Possession" in noms_retard
    assert "PLU — Le Port" in noms_verif
