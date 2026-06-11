"""Tests du résumé « business » de la fiche (Phase 2). Cœur pur, sans DB.

Verrouille : la synthèse par statut, le plafond ≤3 raisons/vigilances, et surtout
l'ABSENCE de vocabulaire interdit (constructible/rentable/garanti/propriétaire trouvé).
"""
from labuse.api.resume import build_resume

FORBIDDEN = ("constructible", "rentable", "rentabilité", "garanti", "propriétaire trouvé", "bilan fiable")


def _no_forbidden(r):
    blob = " ".join([r["synthese"], r["prochaine_action"], *r["positifs"], *r["vigilance"]]).lower()
    for w in FORBIDDEN:
        assert w not in blob, f"vocabulaire interdit « {w} » dans : {blob!r}"


def test_resume_opportunite():
    verdict = {"status": "opportunite", "downgrade_reason": None}
    cascade = [
        {"layer_name": "zonage_plu_gpu", "result": "POSITIVE", "detail": "Zone PLU U", "severity": None},
        {"layer_name": "surface", "result": "POSITIVE", "detail": "Surface utile", "severity": None},
        {"layer_name": "sar", "result": "PASS", "detail": "vocation compatible détectée", "severity": None},
    ]
    fa = {"bilan": {"fiable": True, "fiabilite": "fiable"}}
    r = build_resume(verdict, cascade, fa, {"has_manual_contact": False})
    assert r["statut_label"] == "Opportunité vérifiée"
    assert 0 < len(r["positifs"]) <= 3
    assert "Propriétaire à identifier" in r["vigilance"]
    assert r["synthese"].startswith("Ressort comme opportunité")
    assert r["prochaine_action"]
    _no_forbidden(r)


def test_resume_faux_positif_parking():
    verdict = {"status": "faux_positif_probable", "downgrade_reason": "parking sur 82 % de la parcelle (OSM)"}
    r = build_resume(verdict, [], None, {})
    assert r["statut_label"] == "Faux positif probable"
    assert "parking" in r["synthese"] and "déclassée" in r["synthese"].lower()
    assert "parking sur 82 % de la parcelle (OSM)" in r["vigilance"]
    _no_forbidden(r)


def test_resume_a_creuser_ppr():
    verdict = {"status": "a_creuser", "downgrade_reason": None}
    cascade = [{"layer_name": "risques", "result": "SOFT_FLAG", "severity": "fort",
                "detail": "Périmètre PPR inondation — servitude approuvée"}]
    r = build_resume(verdict, cascade, None, {"has_manual_contact": False})
    assert r["statut_label"] == "À creuser"
    assert any("PPR" in v for v in r["vigilance"])
    assert "à creuser" in r["synthese"].lower()
    _no_forbidden(r)


def test_resume_exclue():
    verdict = {"status": "exclue", "downgrade_reason": None}
    cascade = [{"layer_name": "foret_publique", "result": "HARD_EXCLUDE", "severity": None,
                "detail": "Exclue : forêt domaniale (domaine public — terrain inacquérable)."}]
    r = build_resume(verdict, cascade, None, {})
    assert r["statut_label"] == "Exclue"
    assert "écartée" in r["synthese"].lower() and "forêt domaniale" in r["synthese"]
    _no_forbidden(r)


def test_resume_plafond_trois():
    verdict = {"status": "opportunite", "downgrade_reason": None}
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
    verdict = {"status": "opportunite", "downgrade_reason": None}
    fa = {"bilan": {"fiable": True, "fiabilite": "fragile"}}
    r = build_resume(verdict, [], fa, {"has_manual_contact": False})
    assert any("fragile" in v.lower() for v in r["vigilance"])
    _no_forbidden(r)


def test_resume_contact_manuel_retire_vigilance_proprietaire():
    verdict = {"status": "opportunite", "downgrade_reason": None}
    r = build_resume(verdict, [], None, {"has_manual_contact": True})
    assert not any("Propriétaire à identifier" == v for v in r["vigilance"])
