"""AUTONOMIE-1 — recette des POLITIQUES d'autonomie (pures, sans base ni réseau).

Couvre les scénarios de recette du mandat :
  · un run simulé qui échoue un contrôle n'est PAS promu (controler_run) ;
  · une injection de classe A avec un contrôle qui échoue revient en arrière (controler_injection) ;
  · la fenêtre/cadence du calcul de nuit ;
  · la classification A/B des sources (défaut B = prudence) ;
  · la fusion « retard/échec » d'un même job et le repérage des incidents > N jours.

Les scénarios DB (auto-close en base, mail) sont dans test_autonomie_1_db.py (marqués reel)."""
from datetime import datetime, timedelta, timezone

import pytest

from labuse import autonomie as A


# ───────────────────────────── classes de sources ─────────────────────────────

def test_classe_structurant_est_B():
    for nom in ["DEAL Réunion — PPR / aléas", "DVF / valeurs foncières",
                "Urbanisme PLU/GPU (API Carto)", "Cadastre (API Carto PCI)",
                "RGE ALTI (altimétrie)", "BD TOPO IGN",
                "DGFiP — parcelles des personnes morales"]:
        cl, _ = A.classe_source(nom)
        assert cl == "B", f"{nom} doit être structurant (B)"


def test_classe_reference_faible_risque_est_A():
    for nom in ["Contours IRIS (IGN/INSEE)", "SIRENE", "BPE INSEE",
                "SUP — assiettes GPU (API Carto)", "Zones exclues EnR sauf toiture (OFB/APER)",
                "Parc National de La Réunion (INPN)", "INSEE RP Logement 2023"]:
        cl, _ = A.classe_source(nom)
        assert cl == "A", f"{nom} doit être référence faible risque (A)"


def test_classe_defaut_inconnue_est_B_prudence():
    cl, raison = A.classe_source("Source totalement inconnue", categorie="risques")
    assert cl == "B"
    assert "défaut" in raison.lower()


def test_sources_par_classe_range_bien():
    srcs = [{"name": "DVF / valeurs foncières", "category": "marche"},
            {"name": "SIRENE", "category": "economie"},
            {"name": "DEAL Réunion — PPR / aléas", "category": "risques"}]
    out = A.sources_par_classe(srcs)
    assert {s["name"] for s in out["B"]} == {"DVF / valeurs foncières", "DEAL Réunion — PPR / aléas"}
    assert {s["name"] for s in out["A"]} == {"SIRENE"}


# ───────────────────────────── fenêtre / cadence du calcul de nuit ─────────────────────────────

def test_fenetre_nuit():
    assert A.fenetre_nuit(datetime(2026, 11, 3, 1, 0), 1, 5) is True
    assert A.fenetre_nuit(datetime(2026, 11, 3, 4, 59), 1, 5) is True
    assert A.fenetre_nuit(datetime(2026, 11, 3, 0, 30), 1, 5) is False
    assert A.fenetre_nuit(datetime(2026, 11, 3, 5, 0), 1, 5) is False


def test_fenetre_depassee():
    assert A.fenetre_depassee(datetime(2026, 11, 3, 5, 0), 5) is True
    assert A.fenetre_depassee(datetime(2026, 11, 3, 4, 59), 5) is False


def test_doit_calculer_declencheur_entree():
    maintenant = datetime(2026, 11, 3, 1, 0, tzinfo=timezone.utc)
    recent = maintenant - timedelta(days=1)
    doit, _ = A.doit_calculer(recent, declencheur_entree=True, cadence_min_jours=7, maintenant=maintenant)
    assert doit is True  # une entrée a changé → on calcule même récent


def test_doit_calculer_anti_churn():
    maintenant = datetime(2026, 11, 3, 1, 0, tzinfo=timezone.utc)
    recent = maintenant - timedelta(days=2)
    doit, raison = A.doit_calculer(recent, declencheur_entree=False, cadence_min_jours=7, maintenant=maintenant)
    assert doit is False and "recalcule pas" in raison


def test_doit_calculer_cadence_de_fond():
    maintenant = datetime(2026, 11, 3, 1, 0, tzinfo=timezone.utc)
    vieux = maintenant - timedelta(days=8)
    doit, _ = A.doit_calculer(vieux, declencheur_entree=False, cadence_min_jours=7, maintenant=maintenant)
    assert doit is True


def test_doit_calculer_jamais_promu():
    maintenant = datetime(2026, 11, 3, 1, 0, tzinfo=timezone.utc)
    doit, _ = A.doit_calculer(None, declencheur_entree=False, cadence_min_jours=7, maintenant=maintenant)
    assert doit is True


# ───────────────────────────── contrôles AVANT promotion (run de nuit) ─────────────────────────────

def _mesures_run_ok():
    return dict(manifeste_present=True, run_complet=True, comptes_parcelles=433229,
                comptes_precedent=433229, coherence_ecarts=0, coherence_erreurs=0,
                copro_actionnables=0, rouge_actionnables=0, paliers_change=746, paliers_total=433229)


def test_run_ok_est_promu():
    v = A.controler_run(_mesures_run_ok(), palier_delta_max_pct=3.0)
    assert v.ok is True, v.resume()
    assert v.details["palier_delta_pct"] < 1.0


def test_run_copro_actionnable_refuse():
    m = _mesures_run_ok(); m["copro_actionnables"] = 5
    v = A.controler_run(m, palier_delta_max_pct=3.0)
    assert v.ok is False and any("copropriété" in e for e in v.echecs)


def test_run_rouge_actionnable_refuse():
    m = _mesures_run_ok(); m["rouge_actionnables"] = 1
    v = A.controler_run(m, palier_delta_max_pct=3.0)
    assert v.ok is False and any("zone rouge" in e for e in v.echecs)


def test_run_coherence_ecart_refuse():
    m = _mesures_run_ok(); m["coherence_ecarts"] = 2
    v = A.controler_run(m, palier_delta_max_pct=3.0)
    assert v.ok is False and any("cohérence" in e for e in v.echecs)


def test_run_comptes_divergents_refuse():
    m = _mesures_run_ok(); m["comptes_parcelles"] = 400000
    v = A.controler_run(m, palier_delta_max_pct=3.0)
    assert v.ok is False and any("compte" in e for e in v.echecs)


def test_run_derive_paliers_refuse():
    m = _mesures_run_ok(); m["paliers_change"] = 50000  # ~11.5% > 3%
    v = A.controler_run(m, palier_delta_max_pct=3.0)
    assert v.ok is False and any("paliers" in e for e in v.echecs)


def test_run_mesure_manquante_refuse():
    m = _mesures_run_ok(); m["manifeste_present"] = False
    v = A.controler_run(m, palier_delta_max_pct=3.0)
    assert v.ok is False


# ───────────────────────────── contrôles d'injection classe A (rollback si échec) ──────────────────

def _mesures_inj_ok():
    return dict(comptes_apres=330, comptes_avant=330, geometries_invalides=0,
                communes_974=24, a_geometrie=True)


def test_injection_ok():
    v = A.controler_injection(_mesures_inj_ok(), delta_max_pct=15.0, couverture_974_min=20)
    assert v.ok is True, v.resume()


def test_injection_geometrie_invalide_rollback():
    m = _mesures_inj_ok(); m["geometries_invalides"] = 3
    v = A.controler_injection(m, delta_max_pct=15.0, couverture_974_min=20)
    assert v.ok is False and any("géométrie" in e for e in v.echecs)


def test_injection_couverture_insuffisante_rollback():
    m = _mesures_inj_ok(); m["communes_974"] = 10
    v = A.controler_injection(m, delta_max_pct=15.0, couverture_974_min=20)
    assert v.ok is False and any("couverture" in e for e in v.echecs)


def test_injection_ecart_version_rollback():
    m = _mesures_inj_ok(); m["comptes_apres"] = 660  # +100% vs 330
    v = A.controler_injection(m, delta_max_pct=15.0, couverture_974_min=20)
    assert v.ok is False and any("écart" in e for e in v.echecs)


def test_injection_vide_rollback():
    m = _mesures_inj_ok(); m["comptes_apres"] = 0
    v = A.controler_injection(m, delta_max_pct=15.0, couverture_974_min=20)
    assert v.ok is False


def test_injection_sans_geometrie_saute_controles_geo():
    m = dict(comptes_apres=1000, comptes_avant=1000, a_geometrie=False)
    v = A.controler_injection(m, delta_max_pct=15.0, couverture_974_min=20)
    assert v.ok is True


# ───────────────────────────── incidents vivants : fusion & ancienneté ─────────────────────────────

def test_fusion_retard_echec_un_seul_par_job():
    incidents = [
        {"cle": "job-echec:backup-postgres", "sujet": "Job en échec : backup-postgres",
         "ouvert_at": "2026-10-30T13:30:00+00:00", "rappels": 3},
        {"cle": "job-retard:backup-postgres", "sujet": "Job en retard : backup-postgres",
         "ouvert_at": "2026-10-31T02:00:00+00:00", "rappels": 2},
        {"cle": "copie-externe-ancienne", "sujet": "Copie externe ancienne",
         "ouvert_at": "2026-10-30T16:45:00+00:00", "rappels": 3},
    ]
    out = A.fusionner_retard_echec(incidents)
    jobs = [i for i in out if i["cle"].startswith("job-")]
    assert len(jobs) == 1
    j = jobs[0]
    assert set(j["cles_fusionnees"]) == {"job-echec:backup-postgres", "job-retard:backup-postgres"}
    assert j["ouvert_at"] == "2026-10-30T13:30:00+00:00"   # la plus ancienne
    assert j["rappels"] == 3
    assert "échec" in j["sujet"]                            # l'échec prime sur le retard
    assert any(i["cle"] == "copie-externe-ancienne" for i in out)  # non-job intact


def test_incidents_anciens_seuil_3j():
    maintenant = datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc)
    incidents = [
        {"cle": "a", "ouvert_at": "2026-10-28T03:45:00+00:00"},  # ~5,3 j  → remonte
        {"cle": "b", "ouvert_at": "2026-11-02T13:15:00+00:00"},  # 0 j     → non
        {"cle": "c", "ouvert_at": "2026-10-30T13:30:00+00:00"},  # ~2,9 j  → non (< 3 j)
        {"cle": "d", "ouvert_at": "2026-10-29T00:00:00+00:00"},  # ~4,5 j  → remonte
    ]
    vieux = A.incidents_anciens(incidents, seuil_jours=3, maintenant=maintenant)
    cles = {i["cle"] for i in vieux}
    assert cles == {"a", "d"}, cles
    assert all("age_jours" in i for i in vieux)


# ───────────── recette : run simulé qui échoue un contrôle → PAS promu + mail ─────────────

def test_run_simule_echoue_controle_non_promu_et_mail():
    """Recette du mandat : un run candidat dont un contrôle échoue n'est PAS promu et déclenche le mail."""
    m = _mesures_run_ok(); m["copro_actionnables"] = 7     # un contrôle casse
    appels = {"promu": 0, "mail": 0}
    def _promouvoir():
        appels["promu"] += 1
    def _alerter(verdict, **kw):
        appels["mail"] += 1
        assert verdict.ok is False
    out = A.promouvoir_si_ok(m, palier_delta_max_pct=3.0, promouvoir=_promouvoir, alerter=_alerter)
    assert out["promu"] is False
    assert appels["promu"] == 0       # JAMAIS promu
    assert appels["mail"] == 1        # mail parti


def test_run_simule_ok_est_promu_sans_mail():
    appels = {"promu": 0, "mail": 0}
    out = A.promouvoir_si_ok(_mesures_run_ok(), palier_delta_max_pct=3.0,
                             promouvoir=lambda: appels.__setitem__("promu", appels["promu"] + 1),
                             alerter=lambda v, **k: appels.__setitem__("mail", appels["mail"] + 1))
    assert out["promu"] is True and appels["promu"] == 1 and appels["mail"] == 0


def test_promotion_qui_leve_nest_pas_un_run_promu():
    def _promouvoir():
        raise RuntimeError("bascule cassée")
    mails = []
    out = A.promouvoir_si_ok(_mesures_run_ok(), palier_delta_max_pct=3.0,
                             promouvoir=_promouvoir, alerter=lambda v, **k: mails.append(k))
    assert out["promu"] is False and "erreur_promotion" in out and len(mails) == 1


# ───────────── recette : injection classe A qui échoue un contrôle → ROLLBACK ─────────────

def test_injection_classe_a_echoue_revient_en_arriere():
    """Recette du mandat : une injection de classe A avec un contrôle qui échoue revient en arrière."""
    etat = {"valide": False, "annule": False}
    def _mesurer():
        return dict(comptes_apres=2000, comptes_avant=330, geometries_invalides=0,
                    communes_974=24, a_geometrie=True)   # +500 % → écart-version casse
    out = A.injecter_avec_rollback(
        injecter=lambda: None, mesurer=_mesurer,
        valider_ok=lambda: etat.__setitem__("valide", True),
        annuler=lambda: etat.__setitem__("annule", True),
        delta_max_pct=15.0, couverture_974_min=20)
    assert out["injecte"] is False
    assert etat["annule"] is True and etat["valide"] is False   # ROLLBACK, jamais commit


def test_injection_classe_a_ok_est_validee():
    etat = {"valide": False, "annule": False}
    out = A.injecter_avec_rollback(
        injecter=lambda: None,
        mesurer=lambda: dict(comptes_apres=331, comptes_avant=330, geometries_invalides=0,
                             communes_974=24, a_geometrie=True),
        valider_ok=lambda: etat.__setitem__("valide", True),
        annuler=lambda: etat.__setitem__("annule", True),
        delta_max_pct=15.0, couverture_974_min=20)
    assert out["injecte"] is True and etat["valide"] is True and etat["annule"] is False


def test_injection_qui_leve_est_annulee():
    etat = {"annule": False}
    def _injecter():
        raise RuntimeError("source injoignable")
    out = A.injecter_avec_rollback(
        injecter=_injecter, mesurer=lambda: {},
        valider_ok=lambda: None, annuler=lambda: etat.__setitem__("annule", True),
        delta_max_pct=15.0, couverture_974_min=20)
    assert out["injecte"] is False and etat["annule"] is True and "erreur" in out


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
