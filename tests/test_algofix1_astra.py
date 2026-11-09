"""ALGO-FIX-1 (3ᵉ passe) — vérifications ciblées de l'avis d'Astra (§6).

Un test par vérification demandée. La plupart sont PURES (aucune base) ; les contrôles sur la
sélection réelle et le Signal persisté sont dans `test_algofix1_persist.py`.
"""
from __future__ import annotations

import math
import types

import pytest

from labuse.scoring import scenarios_v2 as v2
from labuse.scoring import scenarios_v2_build as build
from labuse.scoring import scenarios_v2_persist as persist
from labuse.scoring import score_labuse as sl

pytestmark = pytest.mark.local


# ── « entrée B→C à quantité constante impossible après seul retrait bâti » ───
def test_invariant_retrait_bati_ne_baisse_jamais():
    bareme, _ = sl.charger_bareme()
    cap, fa = bareme["capacite"], bareme["faisabilite"]
    plancher = float(fa.get("plancher", 0.4))
    for sdp in (40, 79, 150, 300, 700, 1500, 2500):
        for pente in (None, 5, 16, 20, 40):
            for emp in (0, 10, 40, 80, 160):
                for fait in (None, 12):
                    bc, _ = sl._bareme_capacite(sdp, None, cap)
                    f_p, _ = sl._f_pente(pente, fa)
                    f_ba = sl._f_bati(emp, fait, fa)
                    s_v1 = min(100, round(bc * max(plancher, f_p * 1.0 * 1.0 * f_ba)))
                    s_v2 = min(100, round(bc * max(plancher, f_p * 1.0 * 1.0)))
                    assert s_v2 >= s_v1                 # retirer le seul bâti ne baisse jamais le score


# ── « reconstruction sans C non estimée » (COMPUTE_PENDING, P1) ─────────────
def test_reconstruction_sans_c_est_calcul_a_completer():
    rec = v2.ScenarioRecord(id="X", cause_engine=None)
    keep_est = types.SimpleNamespace(status="ESTIMATED")
    keep_nm = types.SimpleNamespace(status="NO_MARGIN")
    keep_out = types.SimpleNamespace(status="OUTSIDE_OBJECTIVE")
    assert persist._rebuild_statut_sans_C(rec, keep_est) == "COMPUTE_PENDING"
    assert persist._rebuild_statut_sans_C(rec, keep_nm) == "COMPUTE_PENDING"   # saturé : C à chiffrer
    assert persist._rebuild_statut_sans_C(rec, keep_out) == "OUTSIDE_OBJECTIVE"
    rec_nulle = v2.ScenarioRecord(id="X", cause_engine="capacite_nulle")
    assert persist._rebuild_statut_sans_C(rec_nulle, keep_nm) == "NO_MARGIN"   # zéro réglementaire
    assert "Calcul à compléter" == v2.LABELS["COMPUTE_PENDING"]


# ── « nouvelle provenance live prioritaire sur l'ancien cache » (P2) ────────
def _sig(**kw):
    base = {"idu": "X", "bande": "B", "cause": None, "cascade_exclue": False,
            "cascade_motifs": [], "signal_p": None, "sdp_residuelle_m2": None}
    return {**base, **kw}


def _ent(**kw):
    base = {"id": 1, "idu": "X", "commune": "C", "residuel_present": True, "sdp": 500, "emp": 10,
            "cause": None, "capacite_estimee": False, "pente_moy_deg": 10, "aire": 1000,
            "perim": 130, "faitage_m": None, "au_classe": None, "acces": "POSITIVE"}
    return {**base, **kw}


def test_provenance_live_prioritaire_sur_cache():
    residuel = {"disponible": True, "sdp_max_m2": 900, "sdp_existante_m2": 100,
                "sdp_residuelle_m2": 800, "assiette_source": "gabarit", "capacite_differee": False}
    rec, _ = build.record_from_rows(_sig(), _ent(cause="terrain_exigu"), None,
                                    residuel=residuel, assiette_source="residuel_legacy")
    assert rec.provenance == "live"
    assert rec.assiette_source == "gabarit"             # live, PAS le cache 'residuel_legacy'
    assert rec.cause_engine is None                     # live constructible, pas le cache terrain_exigu
    assert rec.capacity_rebuild_m2 == 900 and rec.residual_m2 == 800


# ── « invalidité géométrique traitée quelle que soit la cause » (P4) ────────
def test_geometrie_invalide_avant_incompatibilite():
    r = v2.evaluate(v2.ScenarioRecord(
        id="G", area_m2=1000, perimeter_m=130, geometry_status="suspect",
        eligibility="incompatible", eligibility_proof={"verified": True}, horizon="now"),
        {"mode": "potential", "scenario": "keep"})
    assert r.status == "TO_VERIFY"
    assert r.cause_codes == ["GEOMETRIE_SUSPECTE"]      # géométrie traitée AVANT l'incompatibilité


def test_adaptateur_geometrie_invalide_toute_cause():
    # Géométrie invalide (ST_IsValid false) + résiduel POSITIF + cause bénigne → suspect.
    geom = {"valide": False, "n_geom": 1, "aire": 1000, "perim": 130}
    rec, _ = build.record_from_rows(_sig(), _ent(cause=None), geom)
    assert rec.geometry_status == "suspect"


# ── « AU inconnue distincte d'AU fermée » (P4) ──────────────────────────────
def test_au_inconnu_distinct_de_au_ferme():
    rec_inc, _ = build.record_from_rows(_sig(), _ent(au_classe="declasse_au_statut_inconnu"), None)
    assert rec_inc.horizon == "unknown"                 # inconnu reste inconnu (pas « À différer »)
    rec_fer, _ = build.record_from_rows(_sig(), _ent(au_classe="declasse_au_fermee"), None)
    assert rec_fer.horizon == "deferred"
    assert v2.evaluate(rec_inc, {"mode": "potential", "scenario": "keep"}).status == "TO_VERIFY"
    assert v2.evaluate(rec_fer, {"mode": "potential", "scenario": "keep"}).status == "DEFERRED"


# ── « probabilité Signal invalide jamais disponible » (P6) ──────────────────
def test_signal_invalide_jamais_disponible():
    # Harmonisé avec le moteur pur (passe-4) : invalide → TO_VERIFY, JAMAIS AVAILABLE/en tête.
    for bad in (1.2, float("nan"), float("inf"), -0.1):
        st = persist._signal_persiste(bad, "fort", False)
        assert st["status"] == "TO_VERIFY" and st["p"] is None
        assert st["reason"] == "PROBABILITE_SERVIE_INVALIDE"
    ok = persist._signal_persiste(0.5, "moyen", False)
    assert ok["status"] == "AVAILABLE" and ok["p"] == 0.5
    assert persist._signal_persiste(None, None, True)["reason"] == "ECARTEE_ETAGE_0"


# ── « contrôle de précision des quantités aux paliers » (arrondi) ───────────
def test_arrondi_palier_non_franchi_silencieusement():
    # Le cœur calcule R = max(0, C − E) à partir des C/E qu'il reçoit (déjà arrondis par le moteur) ;
    # il ne RE-arrondit pas séparément. À la frontière 200 m² du barème : C=400, E=200 → R=200
    # (palier ≥ 200), et une variation de 1 m² d'un côté reste tracée, jamais masquée par un arrondi.
    r_juste = v2.evaluate(v2.ScenarioRecord(
        id="P", area_m2=1000, perimeter_m=130, capacity_rebuild_m2=400, existing_m2=200,
        residual_m2=None, slope_deg=5, eligibility="allowed", horizon="now"),
        {"mode": "potential", "scenario": "keep"})
    assert r_juste.quantities["additional"] == 200       # R = C − E exact, pas de double arrondi
    r_sous = v2.evaluate(v2.ScenarioRecord(
        id="P", area_m2=1000, perimeter_m=130, capacity_rebuild_m2=400, existing_m2=201,
        residual_m2=None, slope_deg=5, eligibility="allowed", horizon="now"),
        {"mode": "potential", "scenario": "keep"})
    assert r_sous.quantities["additional"] == 199        # 1 m² de moins → palier inférieur, visible
    assert r_juste.band != r_sous.band or r_juste.score != r_sous.score


# ══ Reproductions de la SECONDE revue d'Astra (passe-4) ══════════════════════

# [1] Legacy par scénario : aucune reconstruction estimée sur assiette non qualifiée, SATURÉE ou non.
def test_legacy_reconstruction_saturee_a_verifier():
    # R=0 (saturée), C>0, assiette non qualifiée : conservation = Aucun ajout (R=0 réel) ;
    # reconstruction = À vérifier (la capacité du scénario est C, pas R).
    rec = v2.ScenarioRecord(id="SAT", area_m2=300, perimeter_m=70, capacity_rebuild_m2=142,
                            existing_m2=169, residual_m2=0, slope_deg=10, eligibility="allowed",
                            horizon="now", assiette_qualifiee=False)
    keep = v2.evaluate(rec, {"mode": "potential", "scenario": "keep"})
    reb = v2.evaluate(rec, {"mode": "potential", "scenario": "rebuild"})
    assert keep.status == "NO_MARGIN"                   # R=0 : zéro réel du scénario conservation
    assert reb.status == "TO_VERIFY"
    assert reb.cause_codes == ["ASSIETTE_A_CONFIRMER"]  # C>0 sur legacy → à confirmer, même saturée
    assert reb.band is None and reb.band_provisional is not None


def test_legacy_conservation_positive_a_verifier():
    rec = v2.ScenarioRecord(id="L", area_m2=1000, perimeter_m=130, capacity_rebuild_m2=800,
                            existing_m2=100, residual_m2=700, slope_deg=8, eligibility="allowed",
                            horizon="now", assiette_qualifiee=False)
    assert v2.evaluate(rec, {"mode": "potential", "scenario": "keep"}).cause_codes == ["ASSIETTE_A_CONFIRMER"]
    assert v2.evaluate(rec, {"mode": "potential", "scenario": "rebuild"}).cause_codes == ["ASSIETTE_A_CONFIRMER"]
    # Qualifiée (gabarit) : estimée.
    rec.assiette_qualifiee = True
    assert v2.evaluate(rec, {"mode": "potential", "scenario": "keep"}).status == "ESTIMATED"


# [1b] Contrôle AU uniforme : lu des motifs (chemin rapide comme enrichi), absence de classe ≠ preuve.
def test_au_uniforme_depuis_motifs():
    motifs_au = [{"layer": "zonage_plu_gpu", "result": "POSITIVE",
                  "detail": "Zone PLU « AUm » (à urbaniser — constructible sur ~40 %)."}]
    rec_au, _ = build.record_from_rows(_sig(cascade_motifs=motifs_au),
                                       _ent(au_classe=None, sdp=500), None)   # chemin RAPIDE (cache)
    assert rec_au.horizon == "unknown"                  # portion AU, régime non établi
    motifs_u = [{"layer": "zonage_plu_gpu", "result": "POSITIVE",
                 "detail": "Zone PLU « Uh » (urbaine — constructible sur ~90 %)."}]
    rec_u, _ = build.record_from_rows(_sig(cascade_motifs=motifs_u), _ent(au_classe=None, sdp=500), None)
    assert rec_u.horizon == "now"


# [2] Bande provisoire = quantité du SCÉNARIO (C en reconstruction), pas R.
def test_bande_provisoire_reconstruction_utilise_C():
    rec = v2.ScenarioRecord(id="B", area_m2=2200, perimeter_m=190, capacity_rebuild_m2=2100,
                            existing_m2=2100, residual_m2=0, slope_deg=9, eligibility="allowed",
                            horizon="unknown")           # À vérifier (horizon inconnu)
    reb = v2.evaluate(rec, {"mode": "potential", "scenario": "rebuild"})
    assert reb.status == "TO_VERIFY"
    assert reb.band_provisional not in (None, "0")      # bande sur C=2100 (pas « 0 » sur R=0)


# [2] Précision complète : R issu de C/E précis, arrondi seulement à l'affichage.
def test_precision_complete_pas_de_double_arrondi():
    # C=384,4 E=184,6 → R=199,8 (< 200 → palier 35), PAS 200 (palier 55). Précision gardée.
    rec = v2.ScenarioRecord(id="P", area_m2=1000, perimeter_m=130, capacity_rebuild_m2=384.4,
                            existing_m2=184.6, residual_m2=None, slope_deg=5, eligibility="allowed",
                            horizon="now")
    r = v2.evaluate(rec, {"mode": "potential", "scenario": "keep"})
    assert abs(r.quantities["additional"] - 199.8) < 1e-6   # R précis, pas 200
    assert r.details["score_brut"] <= 40                    # palier < 200 (35 pts), pas 55


# [2] Valeurs invalides en branche provisoire : jamais exposées, résultat sérialisable.
def test_quantites_invalides_non_exposees():
    import json
    for mauvaise in (float("inf"), float("nan"), -5.0, "texte"):
        rec = v2.ScenarioRecord(id="X", area_m2=1000, perimeter_m=130, capacity_rebuild_m2=mauvaise,
                                existing_m2=100, residual_m2=None, slope_deg=5, eligibility="allowed",
                                horizon="unknown")      # passe par provisoire()
        r = v2.evaluate(rec, {"mode": "potential", "scenario": "rebuild"})
        assert r.quantities["project_total"] in (None,)  # C invalide non exposé
        json.dumps(r.quantities)                         # sérialisable (pas d'inf/nan)


# [4] Échec du calcul live : état PAR PARCELLE, jamais silencieux.
def test_enrich_state_par_parcelle():
    rec, _ = build.record_from_rows(_sig(), _ent(), None, enrich_state="failed")
    assert rec.enrich_state == "failed"
    rec2, _ = build.record_from_rows(_sig(), _ent(), None)
    assert rec2.enrich_state == "not_requested"
