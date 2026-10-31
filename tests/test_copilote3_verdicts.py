"""COPILOTE-3 — le Copilote n'affirme que ce qu'un OUTIL PORTE.

Registre : docs/audit-2026-11/nu-1/E/RAPPORT.md (NU-E-046 à 049).

NU-E-046 : la copropriété (et le propriétaire personne morale) sont désormais PORTÉS par l'outil de
           fiche, chacun avec sa vraie source ; la réponse OUI/NON est DÉTERMINISTE (aucun LLM).
NU-E-047 : le verrou anti-invention est étendu aux VERDICTS QUALITATIFS — toute affirmation oui/non
           de la prose doit correspondre à un champ présent dans le résultat d'outil, sinon REFUS.
NU-E-048 : chaque fait porte sa VRAIE source (PLU, PPR/DEAL, DGFiP, cadastre), jamais un verdict PLU
           estampillé « cadastre Etalab ».

La partie DÉTERMINISTE (verrou, détecteurs, sources, polarité) tourne SANS clé IA ni base : c'est le
« test automatisé qui échoue si une réponse affirme un fait absent du résultat d'outil ». Les témoins
qui lisent la base sont marqués `db` (skip propre si la parcelle témoin manque de la base de test).
"""
from __future__ import annotations

import pytest

from labuse.copilote_v2 import answering as A
from labuse.copilote_v2 import outils
from labuse.copilote_v2 import resume_fiche as RF
from labuse.copilote_v2.outils import ToolResult


# ───────────────────────── fabriques de ToolResult (sans base) ─────────────────────────
def _fiche_res(*, copro=None, pm=None, zone="UC"):
    """Un résultat `fiche_parcelle` de la même FORME que l'outil réel (data + faits sourcés)."""
    data = {"idu": "97404000AV0167", "commune": "L'Étang-Salé", "surface_m2": 139,
            "zone": zone, "etage0": True, "copro": copro, "proprietaire_personne_morale": pm}
    faits = [
        {"cle": "commune", "libelle": "commune", "valeur": data["commune"], "source": outils._SRC_CADASTRE},
        {"cle": "surface_m2", "libelle": "surface", "valeur": 139, "source": outils._SRC_CADASTRE},
        {"cle": "zone", "libelle": "zone PLU", "valeur": zone, "source": outils._SRC_PLU},
        {"cle": "copro", "libelle": "copropriété", "valeur": copro, "source": outils._SRC_RNIC},
        {"cle": "proprietaire_personne_morale", "libelle": "propriétaire (personne morale)",
         "valeur": pm, "source": outils._SRC_PM},
    ]
    return ToolResult("fiche_parcelle", valeur=139, data=data, faits=faits, source=outils._SRC_CADASTRE)


def _fiche_res_legacy():
    """La forme AVANT COPILOTE-3 : la fiche ne portait NI copro NI PM (NU-E-046). Toute affirmation
    oui/non de copropriété était alors une INVENTION — le verrou doit la refuser."""
    return ToolResult("fiche_parcelle", valeur=139,
                      data={"idu": "97404000AV0167", "commune": "L'Étang-Salé", "surface_m2": 139,
                            "zone": "UC", "etage0": True}, source="cadastre")


def _ppr_res(statut):
    return ToolResult("statut_ppr", valeur=("oui" if statut in ("rouge", "bleue") else "non"),
                      data={"idu": "x", "reponse": ("oui" if statut != "hors" else "non"),
                            "statut_ppr": statut},
                      source="DEAL Réunion — PPR / aléas")


# ───────────────────────── NU-E-047 : le verrou refuse toute affirmation NON portée ─────────────────────────
def test_verrou_refuse_verdict_copro_absent_du_resultat():
    """LE test du mandat : une réponse qui AFFIRME un fait absent du résultat d'outil échoue au verrou.
    Prose = l'hallucination observée (NU-E-046) ; résultat = la fiche LEGACY (sans champ copro)."""
    res = _fiche_res_legacy()
    assert A._verdicts_coherents("Non, cette parcelle n'est pas en copropriété.", res) is False
    assert A._verdicts_coherents("Oui, elle est en copropriété.", res) is False


def test_verrou_refuse_polarite_contraire_a_la_donnee():
    """Copropriété AVÉRÉE (copro=True) : la prose qui dit « pas en copropriété » contredit la donnée."""
    res = _fiche_res(copro=True)
    assert A._verdicts_coherents("Non, cette parcelle n'est pas en copropriété.", res) is False


def test_verrou_accepte_verdict_porte_et_coherent():
    assert A._verdicts_coherents("Oui, elle est en copropriété.", _fiche_res(copro=True)) is True
    assert A._verdicts_coherents("Non, elle n'est pas en copropriété.", _fiche_res(copro=False)) is True


def test_verrou_refus_honnete_nest_pas_une_affirmation():
    """« je n'ai pas cette donnée » près du topic = refus honnête → passe (ce n'est pas un verdict)."""
    res = _fiche_res(copro=None)
    assert A._verdicts_coherents("Je n'ai pas cette donnée de copropriété pour cette parcelle.", res) is True


def test_verrou_copro_inconnue_bloque_toute_affirmation():
    """copro inconnu (None, pas de run) : aucune affirmation oui/non permise (NU-E-047)."""
    res = _fiche_res(copro=None)
    assert A._verdicts_coherents("Oui, elle est en copropriété.", res) is False
    assert A._verdicts_coherents("Non, elle n'est pas en copropriété.", res) is False


def test_verrou_ppr_porte_par_statut_ppr_pas_par_la_fiche():
    # la fiche factuelle NE porte PAS le PPR → un verdict PPR en sortant est une invention.
    assert A._verdicts_coherents("Elle est en zone rouge du PPR.", _fiche_res(copro=True)) is False
    # statut_ppr le porte → cohérent si la polarité suit la donnée.
    assert A._verdicts_coherents("Oui, en zone rouge du PPR.", _ppr_res("rouge")) is True
    assert A._verdicts_coherents("Non, hors PPR.", _ppr_res("rouge")) is False
    assert A._verdicts_coherents("Non, cette parcelle n'est pas en zone PPR.", _ppr_res("hors")) is True


def test_verrou_constructibilite_jamais_inventee_depuis_la_fiche():
    """NU-E-049 : la fiche factuelle ne porte pas de verdict de constructibilité → refus."""
    assert A._verdicts_coherents("Cette parcelle est constructible.", _fiche_res(copro=True)) is False
    assert A._verdicts_coherents("Cette parcelle est inconstructible.", _fiche_res(copro=True)) is False
    # destination_zone PORTE un verdict de zone → la constructibilité y est permise (pas une invention).
    dz = ToolResult("destination_zone", valeur="autorise",
                    data={"statut_effectif": "autorise", "phrase": "Le commerce est autorisé en zone UE."},
                    source="PLU")
    assert A._verdicts_coherents("Oui, c'est constructible pour ce commerce.", dz) is True


def test_verrou_proprietaire_morale_contre_la_donnee():
    res_pm = _fiche_res(copro=False, pm="SCI ALOE")
    res_sans = _fiche_res(copro=False, pm=None)
    assert A._verdicts_coherents("Elle appartient à une société (SCI ALOE).", res_pm) is True
    # PM absente (champ servi = None) : affirmer l'appartenance à une personne morale est faux.
    assert A._verdicts_coherents("Elle appartient à une société.", res_sans) is False


def test_verrou_nignore_pas_les_mots_courts_hors_contexte():
    """« ppr » ne doit pas se déclencher dans « approprié » (bornes de mot)."""
    res = _fiche_res(copro=True)
    # aucune mention PPR réelle → le verrou ne bloque pas sur « approprié »
    assert A._verdicts_coherents("Cette surface est appropriée à un petit collectif.", res) is True


def test_verrou_laisse_passer_le_comptage_filtre():
    """Un comptage « en copropriété » (compter_parcelles, filtre copro=avec) est cohérent, pas bloqué."""
    res = ToolResult("compter_parcelles", valeur=12,
                     data={"copro": "avec", "criteres": {"commune": "Saint-Denis"}}, source="facette")
    assert A._verdicts_coherents("12 parcelles en copropriété à Saint-Denis.", res) is True
    res2 = ToolResult("compter_parcelles", valeur=3, data={"copro": "sans"}, source="facette")
    assert A._verdicts_coherents("3 parcelles hors copropriété.", res2) is True
    # un comptage « détenues par une personne morale » (filtre personne_morale) reste cohérent
    res3 = ToolResult("compter_parcelles", valeur=8, data={"personne_morale": True}, source="facette")
    assert A._verdicts_coherents("8 parcelles détenues par une personne morale.", res3) is True


# ───────────────────────── détecteurs (déterministes) ─────────────────────────
def test_detecteur_copro():
    assert RF.est_question_copro("cette parcelle est-elle en copropriété ?")
    assert RF.est_question_copro("y a-t-il un syndic sur 97404000AV0167 ?")
    # une NOTION (pas un statut) n'est pas happée (voie explication)
    assert not RF.est_question_copro("c'est quoi une copropriété ?")
    assert not RF.est_question_copro("quelle est la surface de cette parcelle ?")


def test_detecteur_constructibilite():
    assert A._est_question_constructibilite("cette parcelle est-elle constructible ?")
    assert A._est_question_constructibilite("peut-on construire sur ce terrain ?")
    assert not A._est_question_constructibilite("c'est quoi la constructibilité ?")
    assert not A._est_question_constructibilite("quelle est la pente ?")


# ───────────────────────── NU-E-048 : sources par fait ─────────────────────────
def test_sources_par_fait_distinctes_et_vraies():
    res = _fiche_res(copro=True, pm="SCI X", zone="A")
    par_cle = {f["cle"]: f["source"] for f in res.faits}
    assert par_cle["zone"] == outils._SRC_PLU and "PLU" in par_cle["zone"]
    assert "cadastre" not in par_cle["zone"].lower()        # NU-E-048 : jamais « cadastre » sur la zone
    assert par_cle["copro"] == outils._SRC_RNIC
    assert "DGFiP" in par_cle["proprietaire_personne_morale"]
    assert par_cle["surface_m2"] == outils._SRC_CADASTRE


def test_resume_fiche_sources_par_champ():
    assert RF._source_champ("zone_plu_famille").startswith("PLU")
    assert "DEAL" in RF._source_champ("aleas_parcelle_liste")
    assert "DGFiP" in RF._source_champ("type_proprietaire")


# ───────────────────────── base de test (lecture seule) — les 6 témoins ─────────────────────────
WITNESS = {
    "97404000AV0167": "copro=True (RNIC) · PPR rouge · zone UC — L'Étang-Salé (témoin NU-E-046)",
    "97410000AN0347": "zone N · PPR rouge · propriété communale — Saint-Benoît",
    "97401000AC0575": "zone A (agricole) — Les Avirons",
    "97417000AT1496": "RNU (pas de PLU) — Saint-Philippe (témoin NU-E-055)",
    "97411000AW0692": "zone Ud · PM = SCI ALOE — Saint-Denis",
    "97416000CD0448": "zone Us · hors PPR — Saint-Pierre",
}


@pytest.fixture(scope="module")
def db():
    from labuse.db import session_factory
    s = session_factory()()
    try:
        yield s
    finally:
        s.close()


def _skip_si_absent(db, idu):
    """Skip propre si le témoin manque de la base de test (la base `labuse_test` du hook est minimale ;
    les 6 témoins vivent dans la base de dev — cf. captures/copilote3/recette.py)."""
    if not outils.fiche_parcelle(db, idu=idu).ok:
        pytest.skip(f"témoin {idu} absent de cette base")


@pytest.mark.db
def test_fiche_parcelle_porte_copro_et_pm(db):
    """NU-E-046 — l'outil de fiche PORTE désormais copro + propriétaire PM, chacun sourcé."""
    r = outils.fiche_parcelle(db, idu="97404000AV0167")
    if not r.ok:
        pytest.skip("témoin AV0167 absent de cette base")
    assert "copro" in r.data and "proprietaire_personne_morale" in r.data
    assert r.data["copro"] is True                                  # copropriété avérée
    par_cle = {f["cle"]: f["source"] for f in r.faits}
    assert "PLU" in par_cle["zone"] and "cadastre" not in par_cle["zone"].lower()   # NU-E-048
    assert "RNIC" in par_cle["copro"]


@pytest.mark.db
def test_reponse_copro_oui_non_deterministe(db):
    """NU-E-046 — OUI sur AV0167 (copro avérée), NON sur un témoin non-copro, chacun sourcé RNIC."""
    oui = RF.reponse_copro(db, "97404000AV0167")
    if oui is None:
        pytest.skip("témoin AV0167 absent de cette base")
    assert oui["valeur"] is True and "copropriété" in oui["texte"].lower()
    assert "RNIC" in oui["source"]
    non = RF.reponse_copro(db, "97410000AN0347")
    assert non is not None and non["valeur"] is False
    assert non["texte"].lower().startswith("non")


@pytest.mark.db
def test_answer_copro_est_deterministe_et_source_rnic(db):
    """Bout en bout, SANS IA : la question copropriété est servie par la voie déterministe (RNIC),
    jamais par le formuler qui inventait (« pas en copropriété » sur une copro avérée, NU-E-046)."""
    rep = A.answer(db, "La parcelle 97404000AV0167 est-elle en copropriété ?")
    if "introuvable" in (rep.get("text") or "").lower():
        pytest.skip("témoin AV0167 absent de cette base")
    assert not rep.get("degraded")
    assert "copropriété" in rep["text"].lower()
    assert rep["text"].lower().startswith("oui")
    assert any("RNIC" in s for s in (rep.get("sources") or []))
    # NU-E-048 : jamais « cadastre » sur ce verdict de copropriété
    assert not any("cadastre" in s.lower() for s in (rep.get("sources") or []))


@pytest.mark.db
def test_answer_constructibilite_rnu_ne_tranche_pas(db):
    """NU-E-055 — commune au RNU (Saint-Philippe, pas de zonage PLU) : le Copilote ne tranche PAS la
    constructibilité et le DIT, au lieu d'inventer une zone « UA »."""
    _skip_si_absent(db, "97417000AT1496")
    rep = A.answer(db, "La parcelle 97417000AT1496 est-elle constructible ?")
    assert not rep.get("degraded")
    t = rep["text"].lower()
    assert "rnu" in t or "règlement national" in t or "ne tranche pas" in t


@pytest.mark.db
def test_answer_constructibilite_zone_a_non_autorisee(db):
    """Zone A : la construction nouvelle n'est en principe pas autorisée — dit depuis le PLU (sourcé)."""
    _skip_si_absent(db, "97401000AC0575")
    rep = A.answer(db, "Peut-on construire sur la parcelle 97401000AC0575 ?")
    assert "zone a" in rep["text"].lower()
    assert any("PLU" in s for s in (rep.get("sources") or []))
