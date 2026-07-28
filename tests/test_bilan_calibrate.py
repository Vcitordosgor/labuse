"""Injection du gabarit de calibration bilan (CSV rempli par Vic) — parsing + upsert par secteur."""
from __future__ import annotations

import pytest

from labuse.faisabilite import bilan_params as bp

pytestmark = pytest.mark.db

_CSV = """\
# commentaire d'en-tête à ignorer
secteur,param,valeur,source,unite,libelle,valeur_actuelle,provenance_actuelle,repere
# ===== socle =====
*,marge_cible_pct,8.5,promoteur X,% du CA,Marge,9,estimee,repere
*,cout_construction_m2_sdp,2650,devis 2026,€/m² SDP,Cout,0,defaut,repere
*,cout_vrd_base,,,€/m² terrain,VRD,90,estimee,non renseigné
Saint-Gilles,prix_m2_neuf,6200,SeLoger,€/m²,Prix neuf,5800,sourcee,repere
*,param_bidon,123,x,,,,,
*,marge_cible_pct,,,,,,,
"""


def _write(tmp_path, content=_CSV):
    p = tmp_path / "calib.csv"
    p.write_text(content, encoding="utf-8")
    return str(p)


def test_read_ignore_commentaires_et_lignes_vides(tmp_path):
    rows = bp.read_calibration_csv(_write(tmp_path))
    # 4 lignes renseignées (marge, cout, prix neuf secteur, param_bidon) ; les 2 « valeur » vides sautent
    params = [(r["secteur"], r["param"], r["valeur"]) for r in rows]
    assert ("*", "marge_cible_pct", "8.5") in params
    assert ("Saint-Gilles", "prix_m2_neuf", "6200") in params
    assert all(r["valeur"] for r in rows)            # aucune valeur vide ne passe
    assert len(rows) == 4


def test_apply_upsert_et_provenance(db_session, tmp_path):
    rows = bp.read_calibration_csv(_write(tmp_path))
    res = bp.apply_calibration(db_session, rows, dry_run=False)
    # param_bidon inconnu → erreur, pas appliqué
    assert ("*", "param_bidon", "paramètre inconnu") in res["errors"]
    applied = {(a["secteur"], a["param"]): a for a in res["applied"]}
    assert applied[("*", "marge_cible_pct")]["value"] == 8.5
    assert applied[("*", "marge_cible_pct")]["provenance"] == "sourcee"   # source fournie

    resolved = bp.resolve(db_session, None)
    assert resolved["marge_cible_pct"]["value"] == 8.5
    assert resolved["marge_cible_pct"]["is_placeholder"] is False
    assert resolved["marge_cible_pct"]["provenance"] == "sourcee"
    # une valeur saisie « sourcee » ne figure plus dans les « à affiner »
    assert "Marge cible promoteur" not in bp.estimated_to_refine(resolved)
    # override secteur bien rangé sous Saint-Gilles
    assert bp.resolve(db_session, "Saint-Gilles")["prix_m2_neuf"]["value"] == 6200.0


def test_dry_run_n_ecrit_rien(db_session, tmp_path):
    avant = bp.resolve(db_session, None)["cout_vrd_base"]["value"]
    csv = "secteur,param,valeur,source\n*,cout_vrd_base,77,test\n"
    bp.apply_calibration(db_session, bp.read_calibration_csv(_write(tmp_path, csv)), dry_run=True)
    apres = bp.resolve(db_session, None)["cout_vrd_base"]["value"]
    assert apres == avant and apres != 77.0           # rien écrit


def test_parametres_morts_retires(db_session):
    """ratio_vendable et bonus_vue_mer_pct RETIRÉS (Vic 28/07/2026) : plus au registre (panneau),
    plus au gabarit, refusés à l'injection — les re-brancher = décision explicite + mesure."""
    assert "ratio_vendable" not in {p["key"] for p in bp.registry()}
    assert "bonus_vue_mer_pct" not in {p["key"] for p in bp.registry()}
    res = bp.apply_calibration(db_session, [{"secteur": "*", "param": "ratio_vendable",
                                             "valeur": "0.9", "source": "x"}], dry_run=True)
    assert res["applied"] == [] and res["errors"][0][1] == "ratio_vendable"


def test_valeur_non_numerique_remonte_une_erreur(db_session, tmp_path):
    csv = "secteur,param,valeur,source\n*,honoraires_pct,douze,x\n"
    res = bp.apply_calibration(db_session, bp.read_calibration_csv(_write(tmp_path, csv)), dry_run=False)
    assert res["applied"] == [] and res["errors"] and res["errors"][0][1] == "honoraires_pct"


def test_le_gabarit_livre_est_vide_par_defaut():
    """Le gabarit committé n'a aucune valeur pré-remplie → injection no-op tant que Vic ne saisit rien."""
    assert bp.read_calibration_csv("config/bilan_calibration_vic.csv") == []
