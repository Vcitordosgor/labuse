"""Tests Score V (Vendabilité) — moteur pur, sans DB ni réseau.

Couvre le barème verrouillé (D1), la dédup radiation/cessation (D6), les plafonds
MAX/SOMME, le facteur fallback ×0.7 (§4.2), le typage propriétaire (§4.3) et les bandes (D2).
"""
from __future__ import annotations

from datetime import date, timedelta

from labuse.connectors.bodacc import parse_annonce_score_v
from labuse.connectors.recherche_entreprises import normalize_denomination
from labuse.scoring import score_v_constants as C
from labuse.scoring.score_v import (
    _retain,
    _signal,
    classify_owner,
    famille_a,
    famille_b,
    famille_c,
    resolve_owner,
)

TODAY = date(2026, 7, 10)
MATCH = {"type": "siren", "valeur": "123456789", "confiance": 1.0}


def _annonce(famille, nature, d, cedants="", registre=""):
    return {"famille": famille, "nature": nature.lower(), "date": d,
            "annonce_id": "A1", "url": None, "cedants": cedants, "registre": registre}


# ── Famille A : machine d'état BODACC ──────────────────────────────────────────

def test_lj_en_cours():
    sigs = famille_a("123456789", [
        _annonce("pcl", "Jugement prononçant la liquidation judiciaire", date(2025, 3, 1))], MATCH)
    assert [s["code"] for s in sigs] == ["BODACC_LJ"]
    assert sigs[0]["points"] == 35


def test_lj_cloturee_reste_signalee():
    sigs = famille_a("123456789", [
        _annonce("pcl", "Jugement prononçant la liquidation judiciaire", date(2020, 1, 1)),
        _annonce("pcl", "Jugement de clôture pour insuffisance d'actif", date(2022, 6, 1))], MATCH)
    assert [s["code"] for s in sigs] == ["BODACC_LJ_CLOT"]
    assert sigs[0]["points"] == 30


def test_rj_efface_par_plan():
    sigs = famille_a("123456789", [
        _annonce("pcl", "Jugement d'ouverture d'une procédure de redressement judiciaire",
                 date(2024, 1, 1)),
        _annonce("pcl", "Jugement arrêtant le plan de redressement", date(2025, 1, 1))], MATCH)
    assert not [s for s in sigs if s["code"] == "BODACC_RJ"]


def test_radiation_fenetre_36_mois():
    recente = famille_a("123456789", [
        _annonce("radiation", "Radiations", TODAY - timedelta(days=200))], MATCH)
    vieille = famille_a("123456789", [
        _annonce("radiation", "Radiations", TODAY - timedelta(days=36 * 31))], MATCH)
    assert [s["code"] for s in recente] == ["BODACC_RADIATION"]
    assert recente[0]["points"] == 0        # v1.3 : anti-signal — tracé, jamais compté
    assert vieille == []


def test_cession_fonds_cedant_seulement():
    # Le SIREN propriétaire est le CÉDANT → signal ; acheteur multi-parties → pas de signal.
    cedant = famille_a("123456789", [
        _annonce("vente_cession", "Ventes et cessions", TODAY - timedelta(days=100),
                 cedants='{"numeroIdentification": "123 456 789"}',
                 registre='["987686540","987 686 540","123456789","123 456 789"]')], MATCH)
    acheteur = famille_a("123456789", [
        _annonce("vente_cession", "Ventes et cessions", TODAY - timedelta(days=100),
                 cedants='{"numeroIdentification": "987 686 540"}',
                 registre='["987686540","987 686 540","123456789","123 456 789"]')], MATCH)
    assert [s["code"] for s in cedant] == ["BODACC_CESSION_FONDS"]
    assert acheteur == []


# ── Famille B + dédup D6 ───────────────────────────────────────────────────────

def _fiche(**kw):
    base = {"etat_administratif": "A", "nature_juridique": "5499", "activite_principale": "68.20B",
            "date_creation": "1990-01-01", "date_fermeture": None, "date_mise_a_jour_rne": None,
            "siege": {"departement": "974", "commune_insee": "97415", "adresse": "St-Paul",
                      "code_pays_etranger": None, "libelle_commune": "SAINT-PAUL"},
            "dirigeants": [], "denomination": "TEST"}
    base.update(kw)
    return base


def test_cessation_et_bandes_age():
    sigs = famille_b("123456789", _fiche(etat_administratif="C"), 76, "SCI", MATCH, TODAY)
    codes = {s["code"] for s in sigs}
    assert "RNE_CESSATION" in codes and "RNE_DIRIGEANT_75" in codes
    assert famille_b("1", _fiche(), 71, "", MATCH, TODAY)[0]["code"] == "RNE_DIRIGEANT_70"
    assert famille_b("1", _fiche(), 65, "", MATCH, TODAY)[0]["code"] == "RNE_DIRIGEANT_65"
    assert famille_b("1", _fiche(), 64, "", MATCH, TODAY) == []


def test_sci_dormante():
    sigs = famille_b("1", _fiche(date_creation="2001-05-01"), None, "SCI", MATCH, TODAY)
    assert [s["code"] for s in sigs] == ["RNE_SCI_DORMANTE"]
    # Mise à jour RNE récente → pas dormante.
    sigs = famille_b("1", _fiche(date_creation="2001-05-01",
                                 date_mise_a_jour_rne="2025-06-01T00:00:00"),
                     None, "SCI", MATCH, TODAY)
    assert sigs == []


def test_v13_radiation_et_cessation_sont_des_anti_signaux():
    """v1.3 : la dédup D6 est SANS OBJET — radiation (A) et cessation (B) valent 0 toutes
    les deux ; les DEUX événements restent tracés (rien n'est supprimé de la traçabilité)."""
    a = famille_a("123456789", [
        _annonce("radiation", "Radiations", TODAY - timedelta(days=100))], MATCH)
    b = famille_b("123456789", _fiche(etat_administratif="C"), None, "", MATCH, TODAY)
    assert [s["code"] for s in a] == ["BODACC_RADIATION"] and a[0]["points"] == 0
    assert "RNE_CESSATION" in [s["code"] for s in b]
    assert all(s["points"] == 0 for s in b)


# ── Famille C ──────────────────────────────────────────────────────────────────

def test_grands_groupes_filtre_v11():
    """v1.1 : GE/ETI (catégorie INSEE) → familles B et C supprimées ; A/D/E restent."""
    from labuse.scoring.score_v_constants import GRANDS_GROUPES_CATEGORIES
    assert GRANDS_GROUPES_CATEGORIES == {"GE", "ETI"}
    from labuse.connectors.recherche_entreprises import parse_result
    rec = {"siren": "310895172", "nom_raison_sociale": "SHLMR", "categorie_entreprise": "GE",
           "etat_administratif": "A", "siege": {}, "dirigeants": []}
    assert parse_result(rec)["categorie_entreprise"] == "GE"


def test_geo_hors_ile_et_autre_commune():
    hors = famille_c("97415000AB0001", _fiche(siege={"departement": "75", "commune_insee": "75101",
                                                     "adresse": "Paris", "code_pays_etranger": None,
                                                     "libelle_commune": "PARIS"}), MATCH)
    autre = famille_c("97415000AB0001", _fiche(siege={"departement": "974", "commune_insee": "97411",
                                                      "adresse": "St-Denis", "code_pays_etranger": None,
                                                      "libelle_commune": "SAINT-DENIS"}), MATCH)
    meme = famille_c("97415000AB0001", _fiche(), MATCH)
    assert [s["code"] for s in hors] == ["GEO_HORS_ILE"]
    assert [s["code"] for s in autre] == ["GEO_AUTRE_COMMUNE"]
    assert meme == []


# ── Rétention : MAX / SOMME plafonnée / facteur fallback ──────────────────────

def test_retain_max_intra_famille():
    cands = [_signal("BODACC_LJ", source="x", match=MATCH),
             _signal("BODACC_RADIATION", source="x", match=MATCH)]
    retained, total = _retain(cands, None)
    assert [s["code"] for s in retained] == ["BODACC_LJ"] and total == 35


def test_tenure_conditionnelle_v13():
    """v1.1 : la tenure ne qualifie QUE combinée — v1.3 : et seulement par un signal à
    POINTS > 0 (un anti-signal tracé à 0 ne la réveille plus : bande morte 25-49, Phase 0)."""
    from labuse.scoring.score_v import _tenure_qualifiee
    assert not _tenure_qualifiee([])
    assert not _tenure_qualifiee([_signal("NU_PM_HORS_IMMO", source="x", match=MATCH)])
    assert _tenure_qualifiee([_signal("FRICHE", source="x", match=MATCH)])
    assert _tenure_qualifiee([_signal("DPE_F", source="x", match=MATCH)])
    assert _tenure_qualifiee([_signal("BODACC_CESSION_FONDS", source="x", match=MATCH)])
    # v1.3 : dirigeant âgé / cessation / radiation (0 pt) ne qualifient PLUS la tenure
    assert not _tenure_qualifiee([_signal("RNE_DIRIGEANT_65", source="x", match=MATCH)])
    assert not _tenure_qualifiee([_signal("RNE_CESSATION", source="x", match=MATCH)])
    assert not _tenure_qualifiee([_signal("BODACC_RADIATION", source="x", match=MATCH)])


def test_retain_somme_plafonnee_famille_d():
    cands = [_signal("FRICHE", source="x", match=MATCH),           # 18
             _signal("DVF_TENURE_OBS5", source="x", match=MATCH),  # 8
             _signal("NU_PM_HORS_IMMO", source="x", match=MATCH)]  # 5 → 18+8=26 → plafonné 25
    retained, total = _retain(cands, None)
    assert total == 25
    assert sum(s["points"] for s in retained) == 25


def test_retain_facteur_fallback_abc_seulement():
    cands = [_signal("BODACC_LJ", source="x", match=MATCH),   # A : 35 → 24
             _signal("FRICHE", source="x", match=MATCH)]      # D : intact
    retained, total = _retain(cands, C.FALLBACK_AFFECTED_FAMILIES)
    by = {s["code"]: s["points"] for s in retained}
    assert by["BODACC_LJ"] == round(35 * 0.7) == 24
    assert by["FRICHE"] == 18 and total == 24 + 18


# ── Matching & typage ─────────────────────────────────────────────────────────

def test_normalize_denomination():
    assert normalize_denomination("S.C.I. Les Flämboyants") == "LES FLAMBOYANTS"
    assert normalize_denomination("SARL  BOIS & FER") == "BOIS FER"


def test_resolve_owner_priorites():
    direct = resolve_owner({"siren": "123456789", "denomination": "X"}, {})
    assert direct == {"siren": "123456789", "confiance": 1.0, "candidats": None}
    fb = resolve_owner({"siren": None, "denomination": "SCI AZUR"},
                       {"AZUR": {"status": "found", "siren": "987654321", "candidats": None}})
    assert fb["confiance"] == C.CONF_DENOMINATION
    amb = resolve_owner({"siren": None, "denomination": "SCI AZUR"},
                        {"AZUR": {"status": "ambiguous", "siren": None,
                                  "candidats": [{"siren": "1"}, {"siren": "2"}]}})
    assert amb["siren"] is None and amb["candidats"]


def test_classify_owner():
    lk = {"groupe": None, "denomination": "SCI DU PORT", "forme": "SCI"}
    assert classify_owner({**lk, "groupe": 4}, None, None) == "public"
    assert classify_owner({**lk, "groupe": 5}, None, None) == "bailleur"
    assert classify_owner({**lk, "groupe": 7}, None, None) == "copro"
    assert classify_owner(lk, "310895172", None) == "bailleur"          # SIREN liste SHLMR
    assert classify_owner({**lk, "denomination": "REUNION HABITAT"}, None, None) == "bailleur"
    assert classify_owner(lk, "1", _fiche(nature_juridique="7210")) == "public"
    assert classify_owner(lk, "1", _fiche()) == "pm"


# ── Connecteur BODACC élargi ──────────────────────────────────────────────────

def test_parse_annonce_score_v_familles():
    rec = {"id": "B1", "familleavis": "radiation", "familleavis_lib": "Radiations",
           "registre": ["951517713", "951 517 713"], "dateparution": "2026-01-10",
           "jugement": None, "url_complete": "https://bodacc.fr/x"}
    p = parse_annonce_score_v(rec)
    assert p["famille"] == "radiation" and p["sirens"] == ["951517713"]
    assert p["nature"] == "Radiations" and p["date_annonce"] == date(2026, 1, 10)
    assert parse_annonce_score_v({**rec, "familleavis": "creation"}) is None
