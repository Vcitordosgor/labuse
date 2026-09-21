"""Signal de mutation V2 · recette q_v15 (SCORING-6 lot D).

q_v15 = **recette q_v14 telle quelle, MOINS `piscine` et `pv_candidat`** — et rien d'autre
(SCORING-5-RETOUR §4 : « garder la recette q_v14 complète pour q_v15, au plus retirer
piscine/pv_candidat, mortes au servi »). Aucune variable nouvelle (règle du mandat SCORING-6
lot D). Cible inchangée : P(vente L2-F dans les 12 mois suivant la date du score).

Toute la mécanique (enrichissement, fit GLOBAL ≤ train_max + isotonique PAR SEGMENT 2024,
ModeleQv12, segmenter) est reprise de `qv14`/`qv12` — SEULE la liste de features change.

Doctrine inchangée : le modèle est GELÉ à l'arène (geste de Vic — `scripts/audit/scoring/…`),
le pipeline le LIT (sha256 au manifeste, refus si mismatch) ; `q_v11_m137` reste servi ; aucun
run île entière ici (mandat SCORING-6 : construction sur run candidat).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ..p_model.features import FeatureSpec
from . import qv12, qv14

ROOT = Path(__file__).resolve().parents[4]

QV15_VERSION = "q_v15"
QV15_DIR = ROOT / "reports/q-v15"
QV15_ARTIFACT_12M = QV15_DIR / "artifacts-q_v15-12m.joblib"
QV15_ARTIFACT_24M = QV15_DIR / "artifacts-q_v15-24m.joblib"
QV15_FREEZE = QV15_DIR / "FREEZE-q_v15.json"

# protocole banc K0 identique (train ≤ 2023 · isotonique par segment 2024 · test 2025)
TRAIN_MIN, TRAIN_MAX, CAL_YEAR = qv14.TRAIN_MIN, qv14.TRAIN_MAX, qv14.CAL_YEAR
TRAIN_MAX_24M, CAL_YEAR_24M = qv14.TRAIN_MAX_24M, qv14.CAL_YEAR_24M
SEGMENTS = qv14.SEGMENTS

#: les DEUX seules features retirées de q_v14 (mortes au servi — SCORING-RAPPORT §B.2).
RETIREES_QV15 = ("piscine", "pv_candidat")

# libellés : ceux de q_v14, sans les deux retirées (elles n'apparaissent plus au top-5).
# (LIBELLES_QV14 est le nom lu par le pipeline pour les recettes candidates.)
LIBELLES_QV12 = {k: v for k, v in qv12.LIBELLES_QV12.items() if k not in RETIREES_QV15}
LIBELLES_QV14 = {k: v for k, v in qv14.LIBELLES_QV14.items() if k not in RETIREES_QV15}


def features_qv15(avec_ventes_pm: bool = True
                  ) -> tuple[list[str], list[FeatureSpec], list[tuple[str, str]]]:
    """Features de q_v15 = q_v14 MOINS piscine/pv_candidat. Aucune variable nouvelle : le
    résultat est un SOUS-ENSEMBLE strict de q_v14."""
    names, specs, inter = qv14.features_qv14(avec_ventes_pm=avec_ventes_pm)
    names = [n for n in names if n not in RETIREES_QV15]
    specs = [s for s in specs if s.name not in RETIREES_QV15]
    inter = [(a, b) for a, b in inter if a not in RETIREES_QV15 and b not in RETIREES_QV15]
    return names, specs, inter


# le modèle q_v15 EST le modèle q_v12/q_v14 (fit global + isotonique par segment).
enrichir = qv14.enrichir
segmenter = qv14.segmenter
copro_de = qv14.copro_de
ModeleQv15 = qv14.ModeleQv14


def fit_qv15(df_all, seg_all, names, specs, inter, **kw):
    """Alias de qv14.fit_qv14 (= qv12.fit_qv12) — q_v15 ne change QUE les features."""
    return qv14.fit_qv14(df_all, seg_all, names, specs, inter, **kw)


def verify_artifacts():
    """Charge les artefacts gelés q_v15 (12/24 mois) et REFUSE tout mismatch sha256 — même
    doctrine que m36/q_v12/q_v14. Les artefacts sont produits par l'arène (geste de Vic) ;
    tant qu'ils n'existent pas, le run q_v15 échoue explicitement (jamais un modèle deviné)."""
    import joblib
    if not QV15_FREEZE.is_file():
        raise RuntimeError(
            "Artefacts q_v15 absents (reports/q-v15/) — le fit/gel est un geste de l'arène "
            "(Vic). SCORING-6 ne bascule ni ne fit l'île entière.")
    freeze = json.loads(QV15_FREEZE.read_text())
    for path, cle in ((QV15_ARTIFACT_12M, "sha256_12m"), (QV15_ARTIFACT_24M, "sha256_24m")):
        sha = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        if sha != freeze[cle]:
            raise RuntimeError(
                f"REFUS : sha256 de {Path(path).name} ({sha[:16]}…) ≠ manifeste — "
                "l'artefact gelé q_v15 seul fait foi.")
    return (joblib.load(QV15_ARTIFACT_12M), joblib.load(QV15_ARTIFACT_24M), freeze)


def geler_artifacts(m12, m24, manifeste: dict) -> dict:
    """Écrit artefacts + manifeste de gel (sha256). Utilisé par l'arène, jamais par le pipeline."""
    import joblib
    QV15_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(m12, QV15_ARTIFACT_12M)
    joblib.dump(m24, QV15_ARTIFACT_24M)
    manifeste = dict(manifeste)
    manifeste["sha256_12m"] = hashlib.sha256(QV15_ARTIFACT_12M.read_bytes()).hexdigest()
    manifeste["sha256_24m"] = hashlib.sha256(QV15_ARTIFACT_24M.read_bytes()).hexdigest()
    QV15_FREEZE.write_text(json.dumps(manifeste, ensure_ascii=False, indent=2, default=str),
                           encoding="utf-8")
    return manifeste
