"""M39 P1.3 — note de GÉNÉALOGIE au registre interne des seeds AK1442/AL1154 (dette #13).

Arbitrage Vic C1 : les seeds RESTENT au registre à l'identique (ce n'est pas un pis-aller — la
règle générique couvre ce que la machine sait à 90,7 %, le registre couvre ce que l'œil de Vic a
tranché et que la machine conteste). On ajoute au motif INTERNE une note de généalogie pour que,
dans six mois, personne ne croie à un trou de la règle. `motif_client` INCHANGÉ (M35 Lot B :
verdict_servi ne lit QUE motif_client — cette note n'est jamais servie).

Constat P0 corrigé : le « FLAIR 88 m² / 0,888 » du registre est en réalité la confiance
colorimétrique V0 + la surface ; juge FLAIR NON calculé (probe-gaté, probe≈0) ; retenu sur revue
visuelle Vic, HORS couche matérialisée. Voir qa/m39/M39_P0_CONSTAT.md.

Écriture DB HORS SCORING (registre interne, comme M35 Lot B) : ne touche NI tier, NI motif_client,
NI cache scoring, NI vigilances M37. Idempotent (n'ajoute la note qu'une fois).

Usage : PYTHONPATH=src python scripts/m39_registre_genealogie.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sqlalchemy import text  # noqa: E402

from labuse.db import engine  # noqa: E402

RUN = "q_v8_calibre"
MARQUEUR = "[M39 généalogie"
NOTE = (" — [M39 généalogie : « FLAIR » = confiance colorimétrique V0 (AK1442 0,785 / AL1154 0,888) "
        "+ surface, PAS un score FLAIR ; juge FLAIR NON calculé (probe-gaté, probe≈0) ; retenue au "
        "registre sur revue visuelle Vic, HORS couche matérialisée 90,7 % → hors règle générique M39 "
        "(C1). Bande probe-ratée = dette C2 nommée, non exécutée.]")
SEEDS = ("97422000AK1442", "97419000AL1154")


def main() -> None:
    with engine().begin() as c:
        for idu in SEEDS:
            motif = c.execute(text("SELECT motif FROM served_run_exceptions "
                                   "WHERE run_id=:r AND idu=:i"), {"r": RUN, "i": idu}).scalar()
            if motif is None:
                print(f"  ⚠ {idu} : absente du registre {RUN} — ignorée.")
                continue
            if MARQUEUR in motif:
                print(f"  = {idu} : note déjà présente (idempotent).")
                continue
            c.execute(text("UPDATE served_run_exceptions SET motif=:m WHERE run_id=:r AND idu=:i"),
                      {"m": motif + NOTE, "r": RUN, "i": idu})
            print(f"  ✓ {idu} : note de généalogie ajoutée (motif interne).")
    # contrôle : motif_client intact, jamais touché
    with engine().connect() as c:
        for idu in SEEDS:
            mc = c.execute(text("SELECT motif_client FROM served_run_exceptions "
                                "WHERE run_id=:r AND idu=:i"), {"r": RUN, "i": idu}).scalar()
            print(f"    motif_client {idu} (inchangé) : {mc}")
    print("✓ M39 P1.3 — généalogie tracée, motif_client intact, 0 écriture scoring.")


if __name__ == "__main__":
    main()
