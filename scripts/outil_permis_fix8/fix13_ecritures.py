"""OUTIL-PERMIS-FIX-13 — ÉCRITURES autorisées dans `labuse` (ces DEUX tables seulement) :
  · pc_caducs  — RECONSTRUCTION (règle d'échéance par date + décret, lecture directe sitadel) ;
  · alertes    — ANNOTATION « · annulé depuis » des 258 alertes dont le permis est aujourd'hui annulé.

Discipline (mandat) : garde-fou base = labuse ; sauvegarde DATÉE avant ; empreinte AVANT et APRÈS ;
retour arrière TESTÉ (sur copie, en sous-transaction annulée) ; AUCUNE notification réémise (event_log
jamais écrit). Rien d'autre n'est touché.
"""
from __future__ import annotations

import datetime as dt
import os

os.environ.setdefault("LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse")

from sqlalchemy import text  # noqa: E402

from labuse import alertes_migration as mig  # noqa: E402
from labuse.db import session_scope  # noqa: E402
from labuse.ingestion.pc_caducs import _SELECT_RAW, _echeance, build_pc_caducs  # noqa: E402

TS = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
REF = dt.date.today()


def _empreinte_caducs(s) -> dict:
    r = s.execute(text(
        "SELECT count(*) n, md5(coalesce(string_agg(idu||':'||caduc_depuis||':'||libelle_court, "
        "'|' ORDER BY idu), '')) h FROM pc_caducs")).mappings().first()
    return {"n": int(r["n"]), "md5": r["h"]}


def _garde(s):
    base = s.execute(text("SELECT current_database()")).scalar()
    if base != "labuse":
        raise SystemExit(f"REFUS — base {base!r} ≠ 'labuse'")


def main() -> int:
    with session_scope() as s:
        _garde(s)

        # ═══ pc_caducs ═══
        av = _empreinte_caducs(s)
        bak_pc = f"pc_caducs_bak_fix13__{TS}"
        s.execute(text(f'DROP TABLE IF EXISTS "{bak_pc}"'))
        s.execute(text(f'CREATE TABLE "{bak_pc}" AS SELECT * FROM pc_caducs'))
        print(f"[pc_caducs] AVANT n={av['n']} md5={av['md5']} · sauvegarde {bak_pc}")
        # reconstruction (retry : la bascule DROP/RENAME exige un verrou exclusif ; lecteurs concurrents)
        for essai in range(5):
            try:
                build_pc_caducs(s, ref_date=REF, commit=True); break
            except Exception as exc:  # noqa: BLE001
                s.rollback()
                if essai == 4:
                    raise
                print(f"   rebuild essai {essai+1} : {type(exc).__name__} — retry")
        ap = _empreinte_caducs(s)
        print(f"[pc_caducs] APRÈS n={ap['n']} md5={ap['md5']}")
        # recompte INDÉPENDANT depuis sitadel (même règle) → écart zéro
        indep = 0
        for r in s.execute(text(_SELECT_RAW)).mappings():
            if _echeance(r["d_octroye"])[0] < REF:
                indep += 1
        print(f"[pc_caducs] recompte indépendant sitadel (règle date) = {indep} · écart = {indep - ap['n']}")
        # rollback TESTÉ sur copie (sous-transaction annulée)
        sp = s.begin_nested()
        s.execute(text("TRUNCATE pc_caducs"))
        s.execute(text(f'INSERT INTO pc_caducs SELECT * FROM "{bak_pc}"'))
        restaure = _empreinte_caducs(s)
        ok_pc = (restaure == av)
        sp.rollback()
        print(f"[pc_caducs] rollback testé (copie) : empreinte restaurée == AVANT : {ok_pc}")

        # ═══ alertes (258 annulées) ═══
        ev_av = s.execute(text("SELECT count(*) FROM event_log")).scalar()
        emp_av = mig.empreinte(s)
        a_faire = mig.a_annoter(s)
        bak_al = mig.sauvegarder(s, suffix=f"annule_{TS}")
        print(f"\n[alertes] AVANT n={emp_av['n']} md5={emp_av['md5']} · à annoter {a_faire} · sauvegarde {bak_al}")
        n_annote = mig.annoter_annules(s)
        emp_ap = mig.empreinte(s)
        ev_ap = s.execute(text("SELECT count(*) FROM event_log")).scalar()
        print(f"[alertes] annotées {n_annote} · APRÈS n={emp_ap['n']} md5={emp_ap['md5']}")
        print(f"[alertes] event_log AVANT={ev_av} APRÈS={ev_ap} → réémission : {'AUCUNE' if ev_ap == ev_av else 'ANOMALIE'}")
        # rollback TESTÉ sur copie (sous-transaction annulée)
        sp2 = s.begin_nested()
        mig.rollback(s, bak_al)
        ok_al = (mig.empreinte(s) == emp_av)
        sp2.rollback()
        print(f"[alertes] rollback testé (copie) : empreinte restaurée == AVANT : {ok_al}")
        # témoin audit
        det = s.execute(text("SELECT payload->>'detail' FROM alertes WHERE source_ref='97441513A0361' "
                             "AND kind='permis_in_zone'")).scalar()
        print(f"[alertes] témoin 97441513A0361 : {det!r}")

        ok = ok_pc and ok_al and indep == ap["n"] and n_annote == a_faire and ev_ap == ev_av
        if not ok:
            raise SystemExit("REFUS — un contrôle a échoué, pas de commit")
        print("\nTOUT VERT — commit")
        # session_scope commit à la sortie
        print(f"RETOUR ARRIÈRE pc_caducs : TRUNCATE pc_caducs; INSERT SELECT * FROM {bak_pc};")
        print(f"RETOUR ARRIÈRE alertes   : labuse ... alertes_migration.rollback({bak_al})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
