"""ALGO-FIX-1 — recette de CONTRAT du moteur V2 par scénario (cœur pur).

Les 26 tests de contrat du §13.2 de la spécification
(`docs/audit-2026-11/algo-fix-1/LABUSE_DOSSIER_V2/01_SPECIFICATION_ALGORITHME.md`), adaptés au
dépôt : ils ciblent `labuse.scoring.scenarios_v2` (fonction PURE, aucune base, aucun SIG, aucun
modèle ML). Ils valident le contrat arithmétique, les statuts, le tri et les gardes de Signal —
PAS le SIG ni le modèle réel (ceux-ci sont couverts par les protections sur parcelles réelles,
`test_algofix1_protections.py`).

Les 10 cas fictifs reprennent `05_CAS_FICTIFS.json` du dossier, traduits aux champs du
`ScenarioRecord`. Aucune constante pédagogique n'entre en configuration de production.
"""
from __future__ import annotations

import math

import pytest

from labuse.scoring import scenarios_v2 as v2
from labuse.scoring import signal_mutation

pytestmark = pytest.mark.local


# ── fixtures fictives (miroir de 05_CAS_FICTIFS.json) ────────────────────────
def _niveau(p):
    return signal_mutation.signal_niveau(p) if p is not None else None


def _rec(**kw):
    kw.setdefault("signal_status", "AVAILABLE")
    kw.pop("signal_domain_verified", None)
    if kw.get("signal_status") == "AVAILABLE" and "signal_niveau" not in kw:
        kw["signal_niveau"] = _niveau(kw.get("signal_p"))
    # Forme CONNUE par défaut : un périmètre compact (≈ carré) si l'aire est donnée sans périmètre,
    # pour que la forme ne soit pas « inconnue » (D4) dans les cas fictifs — comme en données
    # réelles où ST_Area/ST_Perimeter existent toujours sur une géométrie valide.
    if kw.get("area_m2") and "perimeter_m" not in kw:
        kw["perimeter_m"] = 4.0 * math.sqrt(kw["area_m2"])
    return v2.ScenarioRecord(**kw)


FIXTURES = {
    "A": dict(id="DEMO-A", area_m2=450, capacity_rebuild_m2=180, existing_m2=180,
              residual_m2=0, signal_p=0.24, slope_deg=8, eligibility="allowed",
              eligibility_proof={"verified": True}, horizon="now", signal_status="AVAILABLE"),
    "B": dict(id="DEMO-B", area_m2=1400, capacity_rebuild_m2=1200, existing_m2=0,
              residual_m2=1200, signal_p=0.06, slope_deg=7, eligibility="allowed",
              horizon="now", signal_status="AVAILABLE"),
    "C": dict(id="DEMO-C", area_m2=2200, capacity_rebuild_m2=2400, existing_m2=1800,
              residual_m2=600, signal_p=0.14, slope_deg=12, eligibility="allowed",
              horizon="now", signal_status="AVAILABLE"),
    "D": dict(id="DEMO-D", area_m2=6000, capacity_rebuild_m2=None, existing_m2=0,
              signal_p=None, eligibility="incompatible",
              eligibility_proof={"verified": True, "rule": "Règle logement fictive, portion entière",
                                 "source": "Démo", "portion": "entière"},
              horizon="now", signal_status="OUT_OF_SCOPE", zone_main="N"),
    "E": dict(id="DEMO-E", area_m2=1800, capacity_rebuild_m2=None, existing_m2=900,
              height_status="missing", height_required=True, signal_p=0.035, slope_deg=None,
              eligibility="allowed", horizon="now", signal_status="AVAILABLE"),
    "F": dict(id="DEMO-F", area_m2=4200, capacity_rebuild_m2=2800, existing_m2=400,
              residual_m2=2400, signal_p=0.018, slope_deg=35, eligibility="allowed",
              horizon="now", signal_status="AVAILABLE"),
    "G": dict(id="DEMO-G", area_m2=8000, capacity_rebuild_m2=None, existing_m2=0,
              signal_p=0.08, horizon="deferred", future_capacity_m2=4200,
              eligibility="allowed", signal_status="AVAILABLE", zone_main="AU fermée"),
    "H": dict(id="DEMO-H", area_m2=1700, capacity_rebuild_m2=2500, existing_m2=3000,
              residual_m2=0, signal_p=0.12, slope_deg=9, eligibility="allowed",
              horizon="now", signal_status="AVAILABLE"),
    "I": dict(id="DEMO-I", area_m2=113832, capacity_rebuild_m2=None, existing_m2=None,
              signal_p=None, geometry_status="suspect", eligibility="allowed",
              horizon="now", signal_status="NOT_AVAILABLE"),
    "J": dict(id="DEMO-J", area_m2=20000, capacity_rebuild_m2=2100, existing_m2=100,
              residual_m2=2000, signal_p=0.025, slope_deg=14, eligibility="allowed",
              horizon="now", signal_status="AVAILABLE", zone_main="U",
              zone_parts=[{"zone": "U", "area_m2": 4000, "constructible": True},
                          {"zone": "N", "area_m2": 16000, "constructible": False}]),
}


def rec(letter, **patch):
    return _rec(**{**FIXTURES[letter], **patch})


def all_recs():
    return [_rec(**FIXTURES[k]) for k in FIXTURES]


def pot(r, scenario="keep", sort=None):
    opts = {"mode": "potential", "scenario": scenario}
    if sort:
        opts["sort"] = sort
    return v2.evaluate(r, opts)


def sale(r):
    return v2.evaluate(r, {"mode": "sale"})


def ids(rows):
    return [row.id for row in rows]


# ── 1. identité (spec §13.2.1-2, §2.1) ───────────────────────────────────────
def test_identifiants_conserves_tous_modes_scenarios():
    base = sorted(r.id for r in all_recs())
    for mode in ("sale", "potential"):
        for scenario in ("keep", "rebuild", "divide"):
            got = v2.order(all_recs(), {"mode": mode, "scenario": scenario})
            assert sorted(r.id for r in got) == base


def test_tous_les_statuts_dans_les_comptes():
    rows = v2.order(all_recs(), {"mode": "potential", "scenario": "keep"})
    eff = v2.effectifs(rows)
    assert eff["n"] == len(FIXTURES)
    assert sum(eff["par_statut"].values()) == len(FIXTURES)


# ── 3. bâti saturé visible en vente, sans marge en conservation ──────────────
def test_bati_sature_sans_marge_mais_signal_disponible():
    assert pot(rec("A")).status == "NO_MARGIN"
    assert pot(rec("A")).quantities["additional"] == 0
    assert sale(rec("A")).status == "SIGNAL_AVAILABLE"


# ── 4-6. Signal : bornes, politique, absence ≠ zéro ──────────────────────────
def test_seuils_signal_exacts_fonction_servie():
    # Les seuils sont la PROPRIÉTÉ de la fonction servie `signal_mutation.signal_niveau`
    # (source unique, inchangée — D6) ; le cœur V2 la relaie.
    for p, niveau in [(0.0, "faible"), (0.099999, "faible"), (0.1, "moyen"),
                      (0.199999, "moyen"), (0.2, "fort"), (1.0, "fort")]:
        assert signal_mutation.signal_niveau(p) == niveau
        assert sale(rec("A", signal_p=p, signal_niveau=_niveau(p))).signal["niveau"] == niveau


def test_probabilite_absente_distincte_de_zero():
    assert sale(rec("A", signal_p=None)).status == "SIGNAL_NOT_AVAILABLE"
    r0 = sale(rec("A", signal_p=0.0, signal_niveau=_niveau(0.0)))
    assert r0.status == "SIGNAL_AVAILABLE"
    assert r0.signal["p"] == 0.0


def test_probabilites_hors_bornes_refusees():
    for p in (-0.1, 1.1, float("nan"), float("inf")):
        r = sale(rec("A", signal_p=p))
        assert r.status == "SIGNAL_TO_VERIFY"
        assert r.signal["p"] is None


def test_domaine_non_valide_sans_extrapolation():
    assert sale(rec("A", signal_status="TO_VERIFY")).status == "SIGNAL_TO_VERIFY"
    r = sale(rec("D", signal_p=0.9))          # hors domaine : aucune proba extrapolée
    assert r.status == "SIGNAL_OUT_OF_SCOPE"
    assert r.signal["p"] is None


def test_vente_ne_reapplique_pas_exclusions_logement():
    # Une prédiction servie ne change pas parce que le foncier est mauvais (D6).
    altere = rec("A", existing_m2=9000, capacity_rebuild_m2=None, slope_deg=None,
                 eligibility="incompatible", geometry_status="suspect",
                 signal_p=0.24, signal_niveau=_niveau(0.24))
    assert sale(altere).rank_value == sale(rec("A")).rank_value


# ── 7. aucune modification des variables historiques (relais fidèle) ─────────
def test_niveau_servi_relaye_sans_recalcul():
    # Le cœur ne recalcule pas le niveau : il relaie exactement ce que l'adaptateur a servi.
    r = sale(rec("A", signal_p=0.24, signal_niveau="fort"))
    assert r.signal["niveau"] == "fort"
    r2 = sale(rec("A", signal_p=0.24, signal_niveau="moyen"))   # relais tel quel (fictif)
    assert r2.signal["niveau"] == "moyen"


# ── 8-9. conservation / reconstruction cohérentes ───────────────────────────
def test_conservation_arithmetique_et_limite_insertion():
    r = pot(rec("C"))
    assert r.status == "ESTIMATED"
    assert r.quantities["additional"] == 600
    assert any("insertion" in m for m in r.vigilance)


def test_reconstruction_quantites_signees_coherentes():
    r = pot(rec("C"), "rebuild")
    assert r.status == "ESTIMATED"
    assert r.quantities["project_total"] == 2400
    assert r.quantities["existing"] == 1800
    assert r.quantities["net_signed"] == 600


# ── 10. C=2100,E=2099 puis 2100 : aucune bascule de formule ─────────────────
def test_reconstruction_2099_puis_2100_sans_bascule():
    a = pot(rec("C", capacity_rebuild_m2=2100, existing_m2=2099), "rebuild")
    b = pot(rec("C", capacity_rebuild_m2=2100, existing_m2=2100), "rebuild")
    assert a.status == b.status == "ESTIMATED"
    assert a.quantities["project_total"] == b.quantities["project_total"] == 2100
    assert a.quantities["net_signed"] == 1
    assert b.quantities["net_signed"] == 0


# ── 11. C=2500,E=3000 : gain net −500 visible ───────────────────────────────
def test_perte_sdp_moins_500_conservee():
    r = pot(rec("H"), "rebuild")
    assert r.status == "ESTIMATED"
    assert r.quantities["net_signed"] == -500
    assert r.quantities["project_total"] == 2500
    assert any("perte" in m for m in r.vigilance)


# ── 12. capacité absente jamais assimilée à zéro ────────────────────────────
def test_capacite_absente_distincte_de_zero():
    r = pot(rec("B", capacity_rebuild_m2=None, residual_m2=None))
    assert r.status == "TO_VERIFY"
    assert r.quantities["additional"] is None
    assert r.rank_value is None


# ── 13. inconnue non critique conservée et visible, sans bonus ni malus ─────
def test_pente_inconnue_sans_changement_arithmetique():
    a = pot(rec("F"))
    b = pot(rec("F", slope_deg=None))
    assert a.quantities["additional"] == 2400
    assert b.quantities["additional"] == 2400
    assert any("Pente non renseignée" in m for m in b.vigilance)


# ── 14. hauteur manquante bloque SDP mais pas le repérage division ──────────
def test_hauteur_manquante_bloque_sdp_pas_division():
    assert pot(rec("E")).status == "TO_VERIFY"
    d = pot(rec("E"), "divide")
    assert d.status == "PRESTUDY"
    assert d.quantities["project_total"] is None


def test_division_sans_lots_ni_certification():
    d = pot(rec("B", existing_m2=None, capacity_rebuild_m2=None, height_status="missing"), "divide")
    assert d.status == "PRESTUDY"
    assert "lots" not in d.details


# ── 15. bornes documentées : traversée zéro, invalides, absentes ────────────
_BC = {"min": 170, "max": 200, "documented": True, "source": "Hypothèse fictive C"}
_BE = {"min": 175, "max": 185, "documented": True, "source": "Hypothèse fictive E"}


def test_bornes_traversant_zero_a_verifier_en_conservation():
    r = pot(rec("A", capacity_rebuild_m2=180, existing_m2=180, residual_m2=0,
                capacity_bounds=_BC, existing_bounds=_BE))
    assert r.status == "TO_VERIFY"
    assert r.bounds["additional_interval"] == [0, 25]
    assert r.bounds["gain_interval"] == [-15, 25]


def test_bornes_traversant_zero_en_reconstruction_garde_capacite():
    r = pot(rec("A", capacity_rebuild_m2=180, existing_m2=180,
                capacity_bounds=_BC, existing_bounds=_BE), "rebuild")
    assert r.status == "ESTIMATED"
    assert r.quantities["project_total"] == 180
    assert r.bounds["gain_interval"] == [-15, 25]


def test_bornes_invalides_refusees():
    for bound in ({"min": 200, "max": 100, "source": "x", "documented": True},
                  {"min": 0, "max": 1000},                       # non documentée
                  {"min": 0, "max": 50, "source": "x", "documented": True},   # central hors bornes
                  {"min": -1, "max": 1300, "source": "x", "documented": True}):
        assert pot(rec("B", capacity_bounds=bound)).status == "TO_VERIFY"


def test_bornes_absentes_ou_une_seule_pas_d_enveloppe():
    assert pot(rec("B")).bounds is None
    r = pot(rec("B", capacity_bounds={"min": 1100, "max": 1300, "source": "C", "documented": True}))
    assert r.status == "ESTIMATED"
    assert r.bounds is None


# ── 16. grande et petite géométrie suspectes toutes deux à vérifier ─────────
def test_geometrie_suspecte_grande_et_petite():
    assert pot(rec("I")).status == "TO_VERIFY"
    assert pot(rec("I", area_m2=30)).status == "TO_VERIFY"


# ── 17. valeurs invalides interceptées (D8) ─────────────────────────────────
def test_valeurs_invalides_refusees():
    for champ in ("capacity_rebuild_m2", "existing_m2"):
        for val in (-1, float("nan"), float("inf")):
            assert pot(rec("B", **{champ: val}), "rebuild").status == "TO_VERIFY"


# ── 18. AU fermée : conditionnel, aucune capacité actuelle, aucun ×0,5 ──────
def test_au_fermee_differee_sans_demi():
    r = pot(rec("G"))
    assert r.status == "DEFERRED"
    assert r.quantities["conditional_future"] == 4200
    assert r.quantities["additional"] is None
    assert r.band is None                       # aucune bande sur le différé (D3)


def test_differe_capacite_future_absente_ou_invalide():
    for fut in (None, -1, float("nan")):
        r = pot(rec("G", future_capacity_m2=fut))
        assert r.status == "DEFERRED"
        assert r.quantities["conditional_future"] is None


def test_differe_ne_remplace_aucun_tri():
    a = rec("G", id="Z", future_capacity_m2=4200, existing_m2=10000)
    b = rec("G", id="A", future_capacity_m2=3000, existing_m2=0)
    for scenario, sort in (("keep", "capacity"), ("rebuild", "capacity"), ("rebuild", "gain")):
        rows = v2.order([a, b], {"mode": "potential", "scenario": scenario, "sort": sort})
        assert ids(rows) == ["A", "Z"]
        assert all(r.rank_value is None for r in rows)
    byarea = v2.order([a, b], {"mode": "potential", "scenario": "rebuild", "sort": "area"})
    assert byarea[0].rank_value == 8000


# ── 19. terrain nu en reconstruction, sans démolition fictive ───────────────
def test_sol_nu_aucune_demolition_inventee():
    r = pot(rec("B"), "rebuild")
    assert r.quantities["existing"] == 0
    assert any("aucune démolition" in m for m in r.vigilance)


# ── 20. incompatibilité : preuve vérifiée, pas simple étiquette de zone ─────
def test_incompatibilite_prouvee_pas_simple_zone():
    assert pot(rec("D")).status == "OUTSIDE_OBJECTIVE"
    assert pot(rec("D", eligibility_proof={"verified": False})).status == "TO_VERIFY"
    assert pot(rec("B", zone_main="N")).status == "ESTIMATED"     # zone N seule ≠ preuve


# ── 21. volumes >2000 toujours départageables dans un tri de volume ─────────
def test_absence_de_plafonnement_au_tri_de_volume():
    small = rec("B", id="SMALL", capacity_rebuild_m2=2100)
    big = rec("B", id="BIG", capacity_rebuild_m2=20000)
    rows = v2.order([small, big], {"mode": "potential", "scenario": "rebuild"})
    assert ids(rows) == ["BIG", "SMALL"]
    rows2 = v2.order([rec("H"), rec("C")], {"mode": "potential", "scenario": "rebuild", "sort": "gain"})
    assert ids(rows2) == ["DEMO-C", "DEMO-H"]


# ── 22. tris stables, valeurs nulles explicites ─────────────────────────────
def test_ordre_de_groupes_et_valeurs_nulles():
    rows = v2.order(all_recs(), {"mode": "potential", "scenario": "keep"})
    for i in range(1, len(rows)):
        assert v2.GROUP_ORDER.get(rows[i - 1].status, 9) <= v2.GROUP_ORDER.get(rows[i].status, 9)


def test_egalite_departagee_par_id():
    a = rec("B", id=" b ", capacity_rebuild_m2=1.0001, residual_m2=1.0001)
    b = rec("B", id="a", capacity_rebuild_m2=1.0001, residual_m2=1.0001)
    c = rec("B", id="c", capacity_rebuild_m2=1.0002, residual_m2=1.0002)
    assert ids(v2.order([a, b, c], {"mode": "potential", "scenario": "keep"})) == ["C", "A", "B"]


def test_petite_quantite_positive_pas_zero():
    assert v2.format_quantite(0.2) == "<1 m²"
    assert v2.format_quantite(None) != v2.format_quantite(0)


def test_ordre_stable_et_parametres_invalides():
    r1 = ids(v2.order(all_recs(), {"mode": "potential", "scenario": "keep"}))
    r2 = ids(v2.order(list(reversed(all_recs())), {"mode": "potential", "scenario": "keep"}))
    assert r1 == r2
    with pytest.raises(ValueError):
        v2.evaluate(rec("A"), {"mode": "autre"})
    with pytest.raises(TypeError):
        v2.order(None, {})
    with pytest.raises(ValueError):
        v2.order(all_recs(), {"mode": "potential", "sort": "signal"})
    with pytest.raises(ValueError):
        v2.order(all_recs(), {"mode": "potential", "scenario": "keep", "sort": "gain"})
    with pytest.raises(ValueError):
        v2.order(all_recs(), {"mode": "potential", "scenario": "divide", "sort": "capacity"})


# ── 25. zonage mixte : la portion productive est identifiable ────────────────
def test_zonage_mixte_portion_productive():
    r = pot(rec("J"))
    assert r.status == "ESTIMATED"
    assert r.quantities["additional"] == 2000
    # La portion productive est la U (4 000 m²), PAS la majoritaire N (16 000 m²).
    assert r.zone_portion == {"zone": "U", "area_m2": 4000}


# ── D4 complet — forme et accès inconnus suivent la règle de la pente ───────
def test_d4_pente_inconnue_bascule_bande():
    # R=633, pente inconnue : neutre→bande A/B, défavorable (0,6)→bande inférieure ⇒ sensible.
    r = pot(rec("B", capacity_rebuild_m2=1200, existing_m2=0, residual_m2=633, slope_deg=None))
    assert r.status == "TO_VERIFY"
    assert r.cause_codes == ["BANDE_SENSIBLE_INCONNUE"]
    assert r.band is None and r.band_provisional is not None


def test_d4_forme_inconnue_bascule_bande():
    # Même parcelle mais SANS périmètre (forme inconnue), pente connue plate : la forme inconnue
    # (pire = lame 0,8) peut faire basculer la bande ⇒ À vérifier, bande provisoire conservée.
    base = dict(id="DEMO-FORME", area_m2=1400, perimeter_m=None, capacity_rebuild_m2=1200,
                existing_m2=0, residual_m2=720, slope_deg=16, eligibility="allowed",
                horizon="now", signal_status="AVAILABLE", signal_p=0.05)
    r = v2.evaluate(v2.ScenarioRecord(**base), {"mode": "potential", "scenario": "keep"})
    if r.band_provisional is not None:               # bascule effective → À vérifier
        assert r.status == "TO_VERIFY"
        assert r.cause_codes == ["BANDE_SENSIBLE_INCONNUE"]
    # Avec périmètre (forme connue), plus de sensibilité de forme.
    base2 = {**base, "perimeter_m": 4.0 * math.sqrt(1400)}
    r2 = v2.evaluate(v2.ScenarioRecord(**base2), {"mode": "potential", "scenario": "keep"})
    assert r2.status == "ESTIMATED"


def test_d4_acces_inconnu_vs_non_identifie():
    # R=300 (55 pts), pente plate (coef 1) : bande neutre 55→B ; accès défavorable 0,85→47→C.
    # « non identifié » (PASS) est un fait MESURÉ (access_known=True) : jamais de sensibilité d'accès.
    r_pass = pot(rec("B", capacity_rebuild_m2=300, existing_m2=0, residual_m2=300,
                     slope_deg=5, access="PASS"))
    assert r_pass.status == "ESTIMATED"              # PASS = malus connu (0,85), pas une inconnue
    assert r_pass.band == "C"
    # « inconnu » (aucun verdict, access_known=False) suit la règle : la bande bascule B↔C ⇒ À vérifier.
    r_unk = v2.evaluate(v2.ScenarioRecord(
        id="DEMO-ACC", area_m2=1400, perimeter_m=4.0 * math.sqrt(1400), capacity_rebuild_m2=300,
        existing_m2=0, residual_m2=300, slope_deg=5, access=None, access_known=False,
        eligibility="allowed", horizon="now"), {"mode": "potential", "scenario": "keep"})
    assert r_unk.status == "TO_VERIFY"
    assert r_unk.band is None and r_unk.band_provisional == "B"


def test_calcul_assiette_douteux_a_verifier():
    # Assiette de repli non découpée (residuel_legacy + contrainte rédhibitoire) → À vérifier.
    r = v2.evaluate(v2.ScenarioRecord(
        id="DEMO-LEGACY", area_m2=199431, perimeter_m=4.0 * math.sqrt(199431),
        capacity_rebuild_m2=12976, existing_m2=1608, residual_m2=11368, slope_deg=40,
        eligibility="allowed", horizon="now", calc_reliable=False,
        calc_doubt_reason="Assiette de repli non découpée au gabarit — capacité à confirmer."),
        {"mode": "potential", "scenario": "keep"})
    assert r.status == "TO_VERIFY"
    assert r.cause_codes == ["CALCUL_ASSIETTE_DOUTEUX"]
    assert any("repli" in m for m in r.vigilance)


# ── 26. versions : une réponse porte sa version d'analyse ───────────────────
def test_version_d_analyse_presente():
    assert pot(rec("B")).analysis_version == v2.VERSION
