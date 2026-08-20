"""Tests du résumé « business » de la fiche (Phase 2). Cœur pur, sans DB.

M34 (dette #14) : verrous mis à jour vers la NOUVELLE vérité — le statut du résumé est la
traduction du tier servi (brûlante/chaude/réserve/à creuser/déclassée/écartée), plus jamais
les statuts cascade legacy (opportunite/faux_positif_probable/exclue).

Verrouille : la synthèse par tier, le badge division, le motif du registre, le plafond
≤3 raisons/vigilances, et surtout l'ABSENCE de vocabulaire interdit.
"""
from labuse.api.resume import build_resume

FORBIDDEN = ("constructible", "rentable", "rentabilité", "garanti", "propriétaire trouvé", "bilan fiable")


def _no_forbidden(r):
    blob = " ".join([r["synthese"], r["prochaine_action"], *r["positifs"], *r["vigilance"]]).lower()
    for w in FORBIDDEN:
        assert w not in blob, f"vocabulaire interdit « {w} » dans : {blob!r}"


def _verdict(status, **kw):
    base = {"status": status, "label": None, "rang": None, "servable": status in
            ("brulante", "chaude", "reserve_fonciere", "a_creuser"),
            "badge_division_libelle": None, "motif": None, "exception_registre": False,
            "downgrade_reason": None}
    base.update(kw)
    return base


def test_resume_brulante():
    verdict = _verdict("brulante", rang=163)
    cascade = [
        {"layer_name": "zonage_plu_gpu", "result": "POSITIVE", "detail": "Zone PLU U", "severity": None},
        {"layer_name": "surface", "result": "POSITIVE", "detail": "Surface utile", "severity": None},
        {"layer_name": "sar", "result": "PASS", "detail": "vocation compatible détectée", "severity": None},
    ]
    fa = {"bilan": {"fiable": True, "fiabilite": "fiable"}}
    r = build_resume(verdict, cascade, fa, {"has_manual_contact": False})
    assert r["statut_label"] == "Priorité"   # M137 — chip court servi (le long ne vit qu'au « i »)
    assert 0 < len(r["positifs"]) <= 3
    assert "Propriétaire à identifier" in r["vigilance"]
    assert r["synthese"].startswith("Classée Priorité") and "rang 163" in r["synthese"]
    assert r["prochaine_action"]
    _no_forbidden(r)


def test_resume_brulante_badge_division():
    # Bâtie marginale divisible SERVIE (étage 3) : le badge nuance, ne déclasse jamais (CY0197).
    verdict = _verdict("brulante", rang=163,
                       badge_division_libelle="bâtie — emprise marginale (bâtie à ~29 %)")
    r = build_resume(verdict, [], None, {"has_manual_contact": False})
    assert r["statut_label"] == "Priorité"   # M137 — chip court servi
    assert "bâtie — emprise marginale" in r["synthese"]
    assert "déclass" not in r["synthese"].lower()   # jamais un déclassement silencieux
    _no_forbidden(r)


def test_resume_signal_nonfranc_en_vigilance_jamais_verdict():
    # L'ex-déclassement cascade (bâti partiel, accès…) reste une VIGILANCE informative.
    verdict = _verdict("chaude", rang=500,
                       downgrade_reason="bâti significatif : 22 % de la surface intersecte des bâtiments (BD TOPO) — occupation à vérifier")
    r = build_resume(verdict, [], None, {"has_manual_contact": False})
    assert r["statut_label"] == "À suivre"   # M137 — chip court servi
    assert any("bâti significatif" in v for v in r["vigilance"])
    assert r["synthese"].startswith("Classée À suivre")
    _no_forbidden(r)


def test_resume_declassee_bati_sature():
    verdict = _verdict("declasse_bati_sature",
                       motif="bâtie saturée — ratio 55 % (emprise 440 m²)")
    r = build_resume(verdict, [], None, {})
    assert r["statut_label"] == "Faible"   # M137 — chip court servi
    assert "déclassée" in r["synthese"].lower() and "saturée" in r["synthese"]
    _no_forbidden(r)


def test_resume_a_creuser_ppr():
    verdict = _verdict("a_creuser")
    cascade = [{"layer_name": "risques", "result": "SOFT_FLAG", "severity": "fort",
                "detail": "Périmètre PPR inondation — servitude approuvée"}]
    r = build_resume(verdict, cascade, None, {"has_manual_contact": False})
    assert r["statut_label"] == "Neutre"   # M137 — chip court servi
    assert any("PPR" in v for v in r["vigilance"])
    assert "à creuser" in r["synthese"].lower()
    _no_forbidden(r)


def test_resume_a_creuser_registre():
    # Exception du registre servi (ex. piscine) : son motif prime dans la synthèse.
    verdict = _verdict("a_creuser", motif="piscine centrale FLAIR 88 m² (PVA 2025)",
                       exception_registre=True)
    r = build_resume(verdict, [], None, {"has_manual_contact": False})
    assert "registre servi" in r["synthese"] and "piscine" in r["synthese"]
    _no_forbidden(r)


def test_resume_ecartee():
    verdict = _verdict("ecartee")
    cascade = [{"layer_name": "foret_publique", "result": "HARD_EXCLUDE", "severity": None,
                "detail": "Exclue : forêt domaniale (domaine public — terrain inacquérable)."}]
    r = build_resume(verdict, cascade, None, {})
    assert r["statut_label"] == "Écartée"   # M137 — chip court servi
    assert "écartée" in r["synthese"].lower() and "forêt domaniale" in r["synthese"]
    _no_forbidden(r)


def test_resume_non_evaluee():
    verdict = _verdict("non_evaluee", label="Non évaluée au run servi", servable=False)
    r = build_resume(verdict, [], None, {})
    assert r["statut_label"] == "Non évaluée au run servi"
    assert "non évaluée" in r["synthese"].lower()


def test_resume_plafond_trois():
    verdict = _verdict("brulante", rang=1)
    cascade = [
        {"layer_name": "zonage_plu_gpu", "result": "POSITIVE", "detail": "", "severity": None},
        {"layer_name": "surface", "result": "POSITIVE", "detail": "", "severity": None},
        {"layer_name": "acces", "result": "POSITIVE", "detail": "", "severity": None},
        {"layer_name": "risques", "result": "SOFT_FLAG", "severity": "fort", "detail": "PPR"},
        {"layer_name": "safer", "result": "SOFT_FLAG", "severity": "fort", "detail": "SAFER"},
        {"layer_name": "trait_de_cote", "result": "SOFT_FLAG", "severity": "fort", "detail": "littoral"},
    ]
    fa = {"bilan": {"fiable": True, "fiabilite": "fiable"}}
    r = build_resume(verdict, cascade, fa, {"has_manual_contact": False})
    assert len(r["positifs"]) <= 3 and len(r["vigilance"]) <= 3


def test_resume_prix_fragile_en_vigilance():
    verdict = _verdict("chaude")
    fa = {"bilan": {"fiable": True, "fiabilite": "fragile"}}
    r = build_resume(verdict, [], fa, {"has_manual_contact": False})
    assert any("fragile" in v.lower() for v in r["vigilance"])
    _no_forbidden(r)


def test_resume_contact_manuel_retire_vigilance_proprietaire():
    verdict = _verdict("brulante")
    r = build_resume(verdict, [], None, {"has_manual_contact": True})
    assert not any("Propriétaire à identifier" == v for v in r["vigilance"])
