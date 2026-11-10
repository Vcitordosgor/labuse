"""PLU-VEILLE-FIX-1 — un nouveau PLU est vu, appliqué en entier, et le client prévenu.

Les tests PURS (hors base) couvrent le cœur : la détection par IDENTIFIANT (idurba), couche par
couche, qui voit le remplacement 1→1 (ce que `totalFeatures` ratait), et l'overlay client qui passe
les parcelles « À vérifier ». Le test db vérifie le passage de nuit complet (instantané Données,
incident exploitation, item John)."""
import json
from datetime import date

import pytest
from sqlalchemy import text

from labuse import controle_plu as cp
from labuse.scoring import scenarios_v2 as v2
from labuse.scoring import scenarios_v2_persist as persist


def _c(idurba):
    return ({"idurba": idurba, "date": cp._date8(idurba), "ingere_le": None, "n": 1, "n_idurba": 1}
            if idurba else None)


# ─────────────────────────── détection (pur) ───────────────────────────

def test_date8():
    assert cp._date8("97411_PLU_20260805") == date(2026, 8, 5)
    assert cp._date8("97409_20190228") == date(2019, 2, 28)
    assert cp._date8(None) is None
    assert cp._date8("sans date") is None


def test_verdict_desync_sur_prescription_perimee():
    """Le cas Saint-Denis : zonage 05/08 servi, prescriptions restées au 23/04 → décalage vu."""
    ing = {"zonage": _c("97411_PLU_20260805"), "prescriptions": _c("97411_PLU_20260423"),
           "informations": _c("97411_PLU_20260805")}
    reg = {"idurba": "97411_PLU_20260805", "date": date(2026, 8, 5), "etat": "calibree"}
    e = cp.verdict_pur("97411", "Saint-Denis", "97411_PLU_20260805", "geoportail", ing, reg)
    assert e.etat == "desync"
    assert e.niveau == "prescriptions"                      # décalage proportionnel (prescriptions seules)
    assert "prescriptions" in e.couches_en_retard
    assert "zonage" not in e.couches_en_retard
    assert e.reference == "97411_PLU_20260805"
    assert e.ancien == "97411_PLU_20260423"
    assert e.gestes  # une liste de gestes concrets


def test_verdict_remplacement_1_1_detecte():
    """Le point du mandat : même NOMBRE de documents (1), mais IDENTIFIANT différent → détecté."""
    ing = {"zonage": _c("97411_PLU_20260423"), "prescriptions": _c("97411_PLU_20260423"),
           "informations": None}
    reg = {"idurba": "97411_PLU_20260423", "date": date(2026, 4, 23), "etat": "calibree"}
    e = cp.verdict_pur("97411", "Saint-Denis", "97411_PLU_20260805", "geoportail", ing, reg)
    assert e.etat == "desync"
    assert e.niveau == "fort"                               # le zonage bouge → toute la commune
    assert "zonage" in e.couches_en_retard and "prescriptions" in e.couches_en_retard
    assert e.nouveau == "97411_PLU_20260805"


def test_verdict_a_jour_quand_tout_aligne():
    ing = {"zonage": _c("97415_PLU_20251217"), "prescriptions": _c("97415_PLU_20251217"),
           "informations": _c("97415_PLU_20251217")}
    reg = {"idurba": "97415_PLU_20251217", "date": date(2025, 12, 17), "etat": "calibree"}
    e = cp.verdict_pur("97415", "Saint-Paul", "97415_PLU_20251217", "geoportail", ing, reg)
    assert e.etat == "a_jour" and e.couches_en_retard == []


def test_verdict_absence_de_couche_nest_pas_un_retard():
    """Commune legacy : zonage présent, aucune prescription publiée → PAS desync (absence ≠ retard)."""
    ing = {"zonage": _c("97409_20190228"), "prescriptions": None, "informations": None}
    reg = {"idurba": "97409_20190228", "date": date(2019, 2, 28), "etat": "calibree"}
    e = cp.verdict_pur("97409", "Saint-André", "97409_20190228", "geoportail", ing, reg)
    assert e.etat == "a_jour"


def test_verdict_drapeau_recalibrage_tient_le_desync():
    """Couches alignées MAIS drapeau « règles à recalibrer » posé → le client reste prévenu."""
    ing = {"zonage": _c("97411_PLU_20260805"), "prescriptions": _c("97411_PLU_20260805"),
           "informations": _c("97411_PLU_20260805")}
    reg = {"idurba": "97411_PLU_20260805", "date": date(2026, 8, 5), "etat": "calibree"}
    e = cp.verdict_pur("97411", "Saint-Denis", "97411_PLU_20260805", "geoportail", ing, reg,
                       demande_fn=lambda ref: True)
    assert e.etat == "desync" and "regles" in e.couches_en_retard
    assert e.couches["regles"]["demande_recalibrage"] is True


def test_verdict_regles_a_relire():
    ing = {"zonage": _c("97411_PLU_20260805"), "prescriptions": _c("97411_PLU_20260805"),
           "informations": None}
    reg = {"idurba": "97411_PLU_20260423", "date": date(2026, 4, 23), "etat": "a_relire"}
    e = cp.verdict_pur("97411", "Saint-Denis", "97411_PLU_20260805", "geoportail", ing, reg)
    assert e.etat == "desync" and "regles" in e.couches_en_retard


# ─────────────────────────── signal client (moteur, pur) ───────────────────────────

_BASE = dict(id="X", area_m2=800, perimeter_m=120, capacity_rebuild_m2=1200, existing_m2=200,
             residual_m2=1000, zone_main="U", slope_deg=5, access="POSITIVE", access_known=True)


def test_evaluate_passe_a_verifier_quand_recalibrage():
    r = v2.evaluate(v2.ScenarioRecord(**_BASE, plu_recalibrage=True, plu_modifie_le="05/08/2026"),
                    {"mode": "potential", "scenario": "keep"})
    assert r.status == "TO_VERIFY"
    assert "PLU_MODIFIE_RECALIBRAGE" in r.cause_codes
    assert r.band is None and r.band_provisional == "A"      # bande calculée conservée en provisoire
    assert any("règles en cours de mise à jour" in v for v in r.vigilance)


def test_evaluate_sans_drapeau_reste_estime():
    r = v2.evaluate(v2.ScenarioRecord(**_BASE), {"mode": "potential", "scenario": "keep"})
    assert r.status == "ESTIMATED" and r.band == "A"


def test_evaluate_prospection_signal_non_touche():
    r = v2.evaluate(v2.ScenarioRecord(**_BASE, plu_recalibrage=True),
                    {"mode": "sale", "scenario": "keep", "sort": "signal"})
    assert r.status.startswith("SIGNAL_")                    # le Signal ne dépend pas du PLU


def test_evaluate_ne_touche_pas_les_statuts_durs():
    """« Hors de ce projet » / « À différer » / « Préétude » ne dépendent pas des chiffres du PLU."""
    kw = dict(id="Y", area_m2=500, perimeter_m=100, eligibility="incompatible",
              eligibility_proof={"rule": "zone N", "source": "PLU", "portion": 1.0, "date": "2026"},
              zone_main="N", slope_deg=5, access="POSITIVE", access_known=True)
    base = v2.evaluate(v2.ScenarioRecord(**kw), {"mode": "potential", "scenario": "keep"})
    flag = v2.evaluate(v2.ScenarioRecord(**kw, plu_recalibrage=True, plu_modifie_le="05/08/2026"),
                       {"mode": "potential", "scenario": "keep"})
    if base.status in ("OUTSIDE_OBJECTIVE", "DEFERRED", "PRESTUDY"):
        assert flag.status == base.status                    # statut dur inchangé
    else:
        assert flag.status == "TO_VERIFY"                    # statut chiffré → À vérifier


def test_augmenter_plu_idempotent():
    msg = "Prescriptions du PLU mises à jour le 05/08/2026 — intégration en cours."
    c, v = persist._augmenter_plu(["AUTRE"], ["note"], "PLU_PRESCRIPTIONS_MAJ", msg)
    assert "PLU_PRESCRIPTIONS_MAJ" in c
    assert any("Prescriptions du PLU mises à jour" in x for x in v)
    c2, v2_ = persist._augmenter_plu(c, v, "PLU_PRESCRIPTIONS_MAJ", msg)
    assert c2.count("PLU_PRESCRIPTIONS_MAJ") == 1
    assert sum(msg in x for x in v2_) == 1


# ─────────────────────────── passage de nuit (base) ───────────────────────────

pytestmark_db = pytest.mark.db


@pytest.mark.db
def test_plu_veille_nuit_signale_desync(db_session, monkeypatch):
    """Le passage complet : détection du décalage, instantané Données, incident exploitation, John."""
    from labuse import jobs_impl
    from labuse.jobs import JobContext
    s = db_session
    # plateau propre pour Saint-Denis, puis un décalage franc (zonage neuf, prescriptions anciennes).
    s.execute(text("DELETE FROM spatial_layers WHERE commune='Saint-Denis' "
                   "AND kind IN ('plu_gpu_zone','plu_gpu_prescription','dpu')"))

    def _ins(kind, idurba):
        s.execute(text(
            "INSERT INTO spatial_layers (kind, name, geom, attrs, commune) VALUES "
            "(:k, 'x', ST_SetSRID(ST_MakePoint(55.45,-20.88),4326), CAST(:a AS jsonb), 'Saint-Denis')"),
            {"k": kind, "a": json.dumps({"idurba": idurba})})
    _ins("plu_gpu_zone", "97411_PLU_20260805")
    _ins("plu_gpu_prescription", "97411_PLU_20260423")      # ancien document — remplacement non suivi

    # pas de réseau en test : publié = catalogue (référence 97411_PLU_20260805).
    monkeypatch.setattr(cp, "fetch_gpu_ile", lambda *a, **k: {})

    ctx = JobContext(db=s, dry_run=True)
    jobs_impl.plu_veille_nuit(ctx)

    snap = s.execute(text("SELECT etat, couches_en_retard, nouveau FROM plu_veille_etat "
                          "WHERE insee='97411'")).mappings().first()
    assert snap and snap["etat"] == "desync"
    assert "prescriptions" in snap["couches_en_retard"]
    assert snap["nouveau"] == "97411_PLU_20260805"

    assert s.execute(text("SELECT 1 FROM ops_incidents WHERE cle='plu-modifie:97411' "
                          "AND resolu_at IS NULL")).scalar() == 1
    assert s.execute(text("SELECT 1 FROM john_veille WHERE axe='reglementaire' "
                          "AND source LIKE '%DU_97411%'")).scalar() == 1
    assert ctx.compteurs["desync"] >= 1
    assert "Saint-Denis" in ctx.compteurs["communes_desync"]


def test_niveau_proportionnel():
    """Décision Vic : la gravité dépend de la couche en décalage."""
    assert cp.niveau_decalage(["zonage"]) == "fort"
    assert cp.niveau_decalage(["regles"]) == "fort"
    assert cp.niveau_decalage(["prescriptions"]) == "prescriptions"
    assert cp.niveau_decalage(["prescriptions", "informations"]) == "prescriptions"
    assert cp.niveau_decalage(["informations"]) == "informations"
    assert cp.niveau_decalage([]) is None
    assert cp.avec_a_verifier("fort") and cp.avec_a_verifier("prescriptions")
    assert not cp.avec_a_verifier("informations")              # DPU seul = bandeau seul
    assert "règles en cours" in cp.bandeau_client("fort", "05/08/2026")
    assert cp.bandeau_client("prescriptions", "05/08/2026").startswith("Prescriptions du PLU mises à jour")
    assert "préemption" in cp.bandeau_client("informations", "05/08/2026")


@pytest.mark.db
def test_appliquer_recalibrage_pose_restaure_et_proportionnel(db_session):
    """L'overlay persisté : poser « À vérifier » puis restaurer rend EXACTEMENT le statut d'avant ;
    et avec `idus` (niveau prescriptions) SEULES les parcelles visées basculent."""
    s = db_session
    persist.ensure_table(s)
    run = "test-plu-overlay"
    s.execute(text("DELETE FROM parcel_scenario_v2_runs WHERE run_label=:r"), {"r": run})
    for idu, st in [("A", "ESTIMATED"), ("B", "OUTSIDE_OBJECTIVE"), ("C", "COMPUTE_PENDING"),
                    ("D", "ESTIMATED")]:
        s.execute(text("INSERT INTO parcel_scenario_v2_runs (run_label, parcel_id, idu, commune, "
                       "scenario, status) VALUES (:run, :pid, :idu, 'Testville', 'keep', :st)"),
                  {"run": run, "pid": ord(idu), "idu": idu, "st": st})
    # fort (idus=None) : toutes les sensibles basculent (A, C, D ; pas B=OUTSIDE)
    n = persist.appliquer_recalibrage(s, run_label=run, commune="Testville", actif=True,
                                      message="PLU modifié le 05/08/2026 — règles en cours de mise à jour.",
                                      cause="PLU_MODIFIE_RECALIBRAGE")
    assert n == 3
    persist.appliquer_recalibrage(s, run_label=run, commune="Testville", actif=False)
    # prescriptions (idus=[A]) : SEULE A bascule ; C et D gardent leur bande
    n = persist.appliquer_recalibrage(s, run_label=run, commune="Testville", actif=True,
                                      message="Prescriptions du PLU mises à jour le 28/04/2026 — intégration en cours.",
                                      cause="PLU_PRESCRIPTIONS_MAJ", idus=["A"])
    assert n == 1
    stt = dict(s.execute(text("SELECT idu, status FROM parcel_scenario_v2_runs WHERE run_label=:r"),
                         {"r": run}).all())
    assert stt == {"A": "TO_VERIFY", "B": "OUTSIDE_OBJECTIVE", "C": "COMPUTE_PENDING", "D": "ESTIMATED"}
    # le bandeau/la cause PROPORTIONNELS sont stockés (injectés à la lecture par _augmenter_plu)
    bandeau, cause = s.execute(text("SELECT plu_bandeau, plu_cause FROM parcel_scenario_v2_runs "
                                    "WHERE run_label=:r AND idu='A'"), {"r": run}).first()
    assert cause == "PLU_PRESCRIPTIONS_MAJ" and "Prescriptions du PLU mises à jour" in bandeau
    c2, v2_ = persist._augmenter_plu([], [], cause, bandeau)          # la lecture injecte proprement
    assert "PLU_PRESCRIPTIONS_MAJ" in c2 and any("Prescriptions du PLU" in x for x in v2_)
    persist.appliquer_recalibrage(s, run_label=run, commune="Testville", actif=False)
    stt2 = dict(s.execute(text("SELECT idu, status FROM parcel_scenario_v2_runs WHERE run_label=:r"),
                          {"r": run}).all())
    assert stt2 == {"A": "ESTIMATED", "B": "OUTSIDE_OBJECTIVE", "C": "COMPUTE_PENDING", "D": "ESTIMATED"}
