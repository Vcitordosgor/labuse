"""SCORING-6 lot G — garanties transverses du mandat (tests PURS) : indépendance aux filtres,
zéro quota/percentile, fuite temporelle (aucune feature nouvelle au Signal), NC ≠ 0.
Le golden 30 témoins + garde-fou 974 (24 communes) sont vérifiés au dry-run (captures/scoring6).
"""
import inspect

from labuse.scoring import score_labuse_combine as comb
from labuse.scoring.p_v2 import qv14, qv15
from labuse.scoring.score_labuse import (ScoreEntrees, charger_bareme,
                                         score_parcelle)

BAREME, VERSION = charger_bareme()


def _e(**kw):
    base = dict(parcel_id=1, idu="x", commune="X", residuel_present=True,
                sdp_residuelle_m2=1200.0, taux_emprise_pct=10.0, cause=None,
                capacite_estimee=False, pente_moy_deg=5.0, aire_m2=800.0,
                perimetre_m=120.0, faitage_m=None, au_classe=None, acces="POSITIVE")
    base.update(kw)
    return ScoreEntrees(**base)


def test_independance_aux_filtres():
    # Le score d'une parcelle NE dépend QUE de ses entrées, jamais du lot où elle est calculée.
    e = _e(parcel_id=42, idu="P42")
    seul = score_parcelle(e, BAREME, VERSION, "run1")
    dans_autre_run = score_parcelle(e, BAREME, VERSION, "run2")
    assert seul.score == dans_autre_run.score and seul.bande == dans_autre_run.bande


def test_aucun_rang_ni_percentile_stocke():
    # La ligne de sortie ne porte AUCUN champ de rang / percentile / quota.
    champs = set(inspect.signature(comb.LigneScoreLabuse).parameters)
    assert not (champs & {"rang", "percentile", "quantile", "quota", "rank"})
    # Le DDL non plus.
    src = inspect.getsource(comb.ensure_schema)
    for interdit in ("rang", "percentile", "quantile", "quota"):
        assert interdit not in src


def test_ordonner_est_un_ordre_pas_un_score():
    # ordonner() ne modifie aucune valeur (score/signal) — c'est un tri, pas un recalcul.
    lignes = [comb.LigneScoreLabuse(
        run_label="t", parcel_id=i, idu=f"P{i}", commune="X", score=s, bande=b,
        non_calculable=False, cause=None, couverture_pct=100, couverture_manquantes=[],
        confiance_niveau="haute", confiance_notes=[], contributions=[],
        score_version=VERSION, signal_p=sp, signal_niveau=None, signal_version=None,
        cascade_exclue=False, cascade_motifs=[], sdp_residuelle_m2=100)
        for i, (s, b, sp) in enumerate([(90, "A", 0.1), (40, "C", 0.2), (55, "B", 0.05)])]
    avant = {l.parcel_id: (l.score, l.signal_p) for l in lignes}
    for l in comb.ordonner(lignes):
        assert (l.score, l.signal_p) == avant[l.parcel_id]


def test_fuite_temporelle_aucune_feature_nouvelle_au_signal():
    # q_v15 est un SOUS-ENSEMBLE strict de q_v14 (banc K0 audité, K4bis) : retirer des features
    # n'ajoute AUCUNE surface de fuite ; aucune variable nouvelle n'est introduite (règle du mandat).
    n14, _, _ = qv14.features_qv14()
    n15, _, _ = qv15.features_qv15()
    assert set(n15).issubset(set(n14))
    assert set(n15) - set(n14) == set()          # zéro feature nouvelle


def test_nc_ne_vaut_jamais_zero():
    for cause in ("zone_non_resolue:Uz", "hors_plu", "regle_plu_non_validee:Ua"):
        r = score_parcelle(_e(cause=cause), BAREME, VERSION, "t")
        assert r.non_calculable and r.score is None
    r2 = score_parcelle(_e(residuel_present=False), BAREME, VERSION, "t")
    assert r2.non_calculable and r2.score is None
