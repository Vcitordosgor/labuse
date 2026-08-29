"""GOLDEN-REGEN · LOT 2 — GARDE-FOU : le golden DOIT être gravé sur le RUN SERVI.

C'est ce qui manquait (diagnostic LOT 0) : la garde `bascule_gardes.check_golden_regenere` EXISTE et
lève si `golden.meta.run_v2_servi ≠ run servi`, mais elle n'était testée qu'avec un golden BIDON
(`parcelles: {}`, run codé en dur). Aucun test ne la lançait sur le VRAI golden + le VRAI run servi —
si bien que la bascule q_v10_m129 → q_v11_m137 a laissé le golden périmé sans qu'AUCUN test ne rougisse
(filet décroché du gate de merge).

Ce test lie les deux vérités du dépôt : le golden VERSIONNÉ (`GOLDEN_PATH`) et le run servi VERSIONNÉ
(`Q_A_RUN_LABEL` = `config/served_run.txt`). Il ÉCHOUE BRUYAMMENT (GoldenPerimeError « GOLDEN PÉRIMÉ »)
tant que le golden n'est pas regravé sur le run servi. LECTURE SEULE (aucune DB, aucun réseau).
"""
from __future__ import annotations

from labuse.bascule_gardes import check_golden_regenere
from labuse.scoring.score_v_constants import Q_A_RUN_LABEL


def test_golden_grave_sur_le_run_servi():
    # GOLDEN_PATH par défaut = reports/m6-audit/golden/golden-parcelles.json (le VRAI golden versionné).
    # Lève GoldenPerimeError si le golden cite un autre run que Q_A_RUN_LABEL (bascule ratée).
    rep = check_golden_regenere(Q_A_RUN_LABEL)
    assert rep["ok"], f"golden gravé sur {rep.get('run_v2_servi')!r} ≠ run servi {Q_A_RUN_LABEL!r}"
    assert rep["run_v2_servi"] == Q_A_RUN_LABEL
