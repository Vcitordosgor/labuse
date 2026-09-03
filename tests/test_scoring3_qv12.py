"""SCORING-3 · L1 — gardes de la recette q_v12 (fonctions pures, sans DB).

Verrouille : la chaîne de features (mortes/retired/remplacées HORS du fit),
la sémantique K3 (0 = réponse, NULL = hors_plu seul inconnu), le censoring K1c
(couverture 100 % par construction), l'isotonique PAR SEGMENT, et le refus
d'une recette inconnue par le pipeline réel.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from labuse.scoring.p_v2 import qv12


# ─────────────────────────── chaîne de features ───────────────────────────

def test_features_qv12_exclut_mortes_retired_et_remplacees():
    names, specs, inter = qv12.features_qv12()
    for morte in qv12.MORTES_K2:
        assert morte not in names, f"morte K2 présente : {morte}"
    for ret in qv12.RETIREES_M35:
        assert ret not in names, f"retired M35 présente : {ret}"
    for rem in ("tenure_bin", "nu_constructible", "sdp_residuelle_m2",
                "sous_densite", "nu_constructible_v2"):
        assert rem not in names, f"feature remplacée présente : {rem}"
    # les remplaçantes et le voisinage y sont
    assert "tenure_bin_v2" in names and "nu_constructible_v3" in names
    assert "sdp_residuelle_v2_m2" in names and "ventes_400m_12m" in names
    assert len(names) == len(set(names)), "doublon de feature"
    # specs alignées, blocs connus
    assert [s.name for s in specs] == names
    assert all(s.bloc in ("Z", "D") for s in specs)
    # interactions : uniquement entre features du candidat
    assert all(a in names and b in names for a, b in inter)


# ─────────────────────────── censoring K1c ───────────────────────────

def test_appliquer_censoring_couverture_100_pct():
    df = pd.DataFrame({
        "idu": ["A", "B", "C"], "annee": [2026, 2026, 2026],
        "nu": [True, True, False], "zone_plu": ["U", None, "A"],
    })
    cens = pd.DataFrame({
        "idu": ["A"], "annee": [2026],
        "derniere_mutation": ["2020-06-01"], "dernier_permis": [None],
        "debut_histo": ["2014-01-01"],
    })
    out = qv12.appliquer_censoring(df, cens)
    # A : mutation connue à ~5,6 ans → bin « 5-8 » ; B/C : aucune → « censure »
    assert out.loc[out.idu == "A", "tenure_bin_v2"].iloc[0] == "5-8"
    assert (out.loc[out.idu != "A", "tenure_bin_v2"] == "censure").all()
    # jamais un inconnu muet
    assert out["tenure_bin_v2"].notna().all()
    # nu_constructible_v2 : U → constructible ; zone inconnue → nu_zone_inconnue ; bâti → bati
    assert out.loc[out.idu == "A", "nu_constructible_v2"].iloc[0] == "nu_constructible"
    assert out.loc[out.idu == "B", "nu_constructible_v2"].iloc[0] == "nu_zone_inconnue"
    assert out.loc[out.idu == "C", "nu_constructible_v2"].iloc[0] == "bati"


# ─────────────────────────── résiduel K3 : 0 ≠ NULL ───────────────────────────

def test_appliquer_residuel_zero_est_une_reponse_null_est_hors_plu():
    df = pd.DataFrame({
        "idu": ["Z0", "ZP", "HP", "AB"], "annee": [2026] * 4,
        "nu": [True, True, True, True],
    })
    res = pd.DataFrame({
        "idu": ["Z0", "ZP", "HP"],
        "sdp_v2": [0, 250, None],
        "sous_densite_r": [False, True, None],
        "residuel_famille": ["zone_non_constructible", "calculee", "hors_plu"],
    })
    out = qv12.appliquer_residuel(df, res)
    # 0 = réponse du moteur → nu_sans_droits (JAMAIS « inconnue »)
    assert out.loc[out.idu == "Z0", "sdp_residuelle_v2_m2"].iloc[0] == 0
    assert out.loc[out.idu == "Z0", "nu_constructible_v3"].iloc[0] == "nu_sans_droits"
    # > 0 → nu_droits
    assert out.loc[out.idu == "ZP", "nu_constructible_v3"].iloc[0] == "nu_droits"
    # hors_plu → NULL explicite (réellement inconnaissable)
    assert pd.isna(out.loc[out.idu == "HP", "sdp_residuelle_v2_m2"].iloc[0])
    assert out.loc[out.idu == "HP", "nu_constructible_v3"].iloc[0] == "nu_non_calcule"
    # absent du cache → famille explicite, pas un NaN silencieux
    assert out.loc[out.idu == "AB", "residuel_famille"].iloc[0] == "absent_du_cache"


# ─────────────────────────── voisinage : absences codées ───────────────────────────

def test_appliquer_voisinage_absence_est_zero_et_pm_cloisonne():
    df = pd.DataFrame({
        "idu": ["P1", "P2", "P3"], "annee": [2026, 2026, 2019],
        "commune": ["97411", "97411", "97411"],
        "owner_type": ["pp", "pm", "pm"],
    })
    spatial = pd.DataFrame({"idu": ["P1"], "annee": [2026],
                            "ventes_150m_12m": [3], "ventes_150m_24m": [5],
                            "ventes_400m_12m": [7], "ventes_400m_24m": [10],
                            "permis_100m_24m": [1], "operations_pa_400m_24m": [0]})
    marche = pd.DataFrame({"commune": ["97411"], "annee": [2026],
                           "volume_commune_a1": [120], "med_pm2_commune_a1": [2100.0],
                           "tendance_volume_3ans": [1.1]})
    vendeur = pd.DataFrame({"idu": ["P2"], "annee": [2026], "pm_vendeur_actif": [True]})
    out = qv12.appliquer_voisinage(df, spatial, marche, vendeur)
    # aucune vente voisine connue = 0 (pas un NULL)
    assert out.loc[out.idu == "P2", "ventes_400m_24m"].iloc[0] == 0
    # delta = accélération
    assert out.loc[out.idu == "P1", "ventes_400m_delta"].iloc[0] == 7 - (10 - 7)
    # non-PM → False ; PM flagué → True ; PM avant 2021 → manquant explicite (None)
    assert out.loc[out.idu == "P1", "pm_vendeur_actif"].iloc[0] is np.False_ or \
        out.loc[out.idu == "P1", "pm_vendeur_actif"].iloc[0] == False  # noqa: E712
    assert bool(out.loc[out.idu == "P2", "pm_vendeur_actif"].iloc[0]) is True
    assert out.loc[out.idu == "P3", "pm_vendeur_actif"].iloc[0] is None


# ─────────────────────────── segments + isotonique par segment ───────────────────────────

def test_segmenter_priorite_copro_pm_nu_bati():
    df = pd.DataFrame({
        "owner_type": ["pm", "pp", "pp", "public"],
        "nu": [True, True, False, False],
    })
    copro = np.array([True, False, False, False])
    seg = qv12.segmenter(df, copro)
    assert list(seg) == ["copropriete", "terrain_nu", "bati_individuel", "personne_morale"]


class _BaseStub:
    """Stub de PModel : margin contrôlée, pour tester l'isotonique par segment."""

    def __init__(self, z):
        self._z = np.asarray(z, dtype=float)

    def margin(self, df):
        return self._z[: len(df)]


def test_modele_qv12_isotonique_par_segment():
    from sklearn.isotonic import IsotonicRegression
    z = np.array([-2.0, -1.0, 0.0, 1.0])
    df = pd.DataFrame({"x": range(4)})
    seg = pd.Series(["bati_individuel", "bati_individuel",
                     "terrain_nu", "terrain_nu"])
    iso_a = IsotonicRegression(out_of_bounds="clip", y_min=0, y_max=1)
    iso_a.fit([-2.0, -1.0], [0.0, 1.0])
    iso_b = IsotonicRegression(out_of_bounds="clip", y_min=0, y_max=1)
    iso_b.fit([0.0, 1.0], [0.2, 0.4])
    m = qv12.ModeleQv12(base=_BaseStub(z), iso_par_segment={
        "bati_individuel": iso_a, "terrain_nu": iso_b}, blocs={})
    p = m.predict_proba(df, seg)
    # chaque segment est calibré par SA courbe (pas une courbe globale)
    assert p[1] > p[3], "le segment bâti doit suivre iso_a, pas iso_b"
    assert abs(p[2] - 0.2) < 1e-9 and abs(p[3] - 0.4) < 1e-9
    # clip : jamais 0 ni 1 exacts
    assert (p > 0).all() and (p < 1).all()
    # segment sans calibration → échec BRUYANT
    with pytest.raises(AssertionError):
        m.predict_proba(df, pd.Series(["copropriete"] * 4))


# ─────────────────────────── pipeline réel : gardes ───────────────────────────

def test_run_score_v2_refuse_recette_inconnue():
    from labuse.scoring.p_v2.pipeline import run_score_v2
    with pytest.raises(RuntimeError, match="recette inconnue"):
        run_score_v2(None, recette="fantaisie")


def test_verify_artifacts_refuse_sha_mismatch(tmp_path, monkeypatch):
    import joblib
    a12 = tmp_path / "a12.joblib"
    a24 = tmp_path / "a24.joblib"
    joblib.dump({"x": 1}, a12)
    joblib.dump({"x": 2}, a24)
    freeze = tmp_path / "FREEZE.json"
    freeze.write_text('{"sha256_12m": "deadbeef", "sha256_24m": "deadbeef"}')
    monkeypatch.setattr(qv12, "QV12_ARTIFACT_12M", a12)
    monkeypatch.setattr(qv12, "QV12_ARTIFACT_24M", a24)
    monkeypatch.setattr(qv12, "QV12_FREEZE", freeze)
    with pytest.raises(RuntimeError, match="REFUS"):
        qv12.verify_artifacts()


def test_libelles_qv12_couvrent_les_features_candidates():
    """Chaque feature candidate (hors registre servi) a un libellé français
    pour le top 5 lisible de la fiche."""
    candidates = {s.name for s in
                  qv12.SPECS_CENSORING + qv12.SPECS_RESIDUEL + qv12.SPECS_VOISINAGE}
    manquants = candidates - set(qv12.LIBELLES_QV12)
    assert not manquants, f"libellés manquants : {manquants}"
