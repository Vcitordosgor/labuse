"""PLU-CALIBRAGE-9 — la clause de mixité sociale (seuil → quota de logements aidés) est LUE du
règlement de zone calibré et branchée : la capacité sort la RÈGLE « X % du programme en
logements aidés » (Sourcé — jamais un nombre de logements dérivé, ROUGES-RESTANTS item 9),
« non imposé » (sous le seuil) ou « sans objet » (zone sans clause) ; le registre sert
`mixite_seuil_m2` / `mixite_quota_pct` au même robinet que l'écran (plus en_attente)."""
from __future__ import annotations

from labuse.faisabilite.engine import estimate_capacity
from labuse.faisabilite.zonage import resolve_zone


def _step(fa):
    return next(s for s in fa.steps if s.label == "Logements sociaux imposés (LLS)")


# ───────────────────────── Témoin : L'Étang-Salé UA (PLU du 17/09/2025) ─────────────────────────

def test_temoin_etang_sale_ua_seuil_m2_lu():
    """Le témoin du mandat : L'Étang-Salé UA, « > 1 000 m² SDP → 20 % aidé » LU du règlement
    (article UA 1.3 (1), p.17) — seuil en m² de SDP, quota 20 %, clause validée et sourcée."""
    zr = resolve_zone("UA", "L'Étang-Salé")
    assert zr and isinstance(zr.mixite, dict)
    assert zr.mixite["statut"] == "valide"
    assert zr.mixite["seuil_m2"] == 1000
    assert zr.mixite["quota_pct"] == 20
    assert zr.mixite["seuil_logements"] is None       # seuil en m², PAS en logements
    assert "1 000 m²" in zr.mixite["citation"] and "20%" in zr.mixite["citation"]
    assert "UA 1.3" in (zr.mixite["article"] or "")


def test_temoin_capacite_sort_la_regle_de_mixite():
    """ROUGES-RESTANTS item 9 (décision Vic, fix/rouges-restants) — au-delà de 1 000 m² de SDP, la
    capacité sort la RÈGLE « 20 % du programme en logements aidés » (Sourcé) : quota % et seuil
    déclencheur, JAMAIS un nombre de logements dérivé (plus de « sur ~a-b logts » ni « ~x-y
    logements aidés imposés »)."""
    zr = resolve_zone("UA", "L'Étang-Salé")
    fa = estimate_capacity(zr, 2000.0, emprise_geo=(1400.0, 4.0))
    st = _step(fa)
    assert st.prov == "sourcee"
    assert st.valeur == "20 % du programme en logements aidés"
    assert "UA 1.3" in st.source
    # le quota est bien 20 % (LU du règlement, pas une constante nationale) et le seuil est dit
    assert "20 %" in st.formule and "1000 m²" in st.formule and "seuil atteint" in st.formule
    # jamais une fourchette de logements dérivée dans la ligne mixité
    assert "logts" not in st.valeur and "sur ~" not in st.formule


def test_sous_le_seuil_non_impose():
    """Programme dont la SDP reste sous 1 000 m² → la clause existe mais « non imposé » (jamais 0 muet)."""
    zr = resolve_zone("UA", "L'Étang-Salé")
    fa = estimate_capacity(zr, 120.0, emprise_geo=(80.0, 3.0))
    st = _step(fa)
    assert st.valeur == "non imposé"
    assert st.prov == "sourcee"          # on SAIT qu'il n'est pas imposé (sourcé), ce n'est pas une absence


def test_zone_sans_clause_sans_objet():
    """Zone sans clause de mixité validée (Saint-Paul U1c) → « sans objet » (jamais « non renseigné »)."""
    zr = resolve_zone("U1c", "Saint-Paul")
    fa = estimate_capacity(zr, 2000.0, emprise_geo=(1200.0, 3.0))
    st = _step(fa)
    assert st.valeur == "sans objet"
    assert st.prov == "absent"


def test_seuil_logements_toujours_pris_en_charge():
    """Rétro-compat : Saint-Denis Uh porte un seuil en LOGEMENTS (30) + 15 % — toujours lu et sourcé."""
    zr = resolve_zone("Uh", "Saint-Denis")
    assert zr.mixite["seuil_logements"] == 30 and zr.mixite["quota_pct"] == 15
    fa = estimate_capacity(zr, 8000.0, emprise_geo=(5000.0, 3.0))
    st = _step(fa)
    assert st.prov == "sourcee" and "Uh.2" in st.source


# ───────────────────────── Registre : robinet fiche + en_attente levée ─────────────────────────

def test_robinet_sert_seuil_et_quota_depuis_la_fiche():
    """Les deux chiffres du registre sont servis du MÊME payload que l'écran (reglement_plu.mixite),
    uniquement si la clause est validée."""
    from labuse.exports.robinet_fiche import _c_mixite_seuil, _c_mixite_quota
    f_valide = {"reglement_plu": {"mixite": {"seuil_m2": 1000, "quota_pct": 20, "statut": "valide"}}}
    assert _c_mixite_seuil(None, "x", f_valide) == 1000
    assert _c_mixite_quota(None, "x", f_valide) == 20
    # clause non validée (propose) → rien servi
    f_propose = {"reglement_plu": {"mixite": {"seuil_m2": 1000, "quota_pct": 20, "statut": "propose"}}}
    assert _c_mixite_seuil(None, "x", f_propose) is None
    assert _c_mixite_quota(None, "x", f_propose) is None
    # seuil en logements (pas de m²) → seuil_m2 absent, quota servi
    f_log = {"reglement_plu": {"mixite": {"seuil_logements": 30, "quota_pct": 15, "statut": "valide"}}}
    assert _c_mixite_seuil(None, "x", f_log) is None
    assert _c_mixite_quota(None, "x", f_log) == 15


def test_en_attente_levee_et_servie():
    """`mixite_seuil_m2` / `mixite_quota_pct` ne sont plus en_attente et figurent dans un robinet."""
    from labuse.registre.donnees import DONNEES
    from labuse.registre.robinets import ROBINETS
    servies = {cid for r in ROBINETS.values() for cid in r.chiffres}
    for cid in ("mixite_seuil_m2", "mixite_quota_pct"):
        assert DONNEES[cid].en_attente is None, cid
        assert cid in servies, cid
