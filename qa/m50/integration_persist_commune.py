"""M50-SUITE-2 — Test d'intégration : rebuild d'une commune → NOUVELLE connexion → l'état persiste.

Prouve, sur la vraie base, ce que la fixture pytest (base dédiée + transaction rollback-ée) ne peut
pas : le commit ATOMIQUE PAR COMMUNE de build_divisions est visible d'une AUTRE connexion après la
sortie de la session appelante. Commune synthétique (aucune parcelle) → 0 détecté, la PURGE tourne.
Auto-nettoyant (finally). Aucune écriture sur une commune réelle servie.

    PYTHONPATH=src /Users/openclaw/Desktop/labuse/.venv/bin/python qa/m50/integration_persist_commune.py
"""
from sqlalchemy import text
from labuse.db import session_factory
from labuse.ingestion import division_or

COMMUNE = "ZZ-INTEG-PERSIST"          # nom synthétique : 0 parcelle → 0 détecté, seule la purge agit
OK = True


def q(session, sql, **p):
    return session.execute(text(sql), p)


try:
    # --- SEED (session S0, commitée) : 1 périmé non-revu + 1 REVU, sous la commune synthétique ---
    s0 = session_factory()()
    division_or.build_divisions(s0, ["ZZ-DDL"], commit=False, log=lambda *_: None)  # garantit la DDL
    q(s0, "DELETE FROM division_or_candidates WHERE commune = :c", c=COMMUNE)
    q(s0, "INSERT INTO division_or_candidates (idu, commune, type_division, run_label, note_revue) "
          "VALUES ('99999000ZZ0001', :c, 'libre', 'q_v7_defisc', NULL),"        # périmé non-revu
          "       ('99999000ZZ0002', :c, 'libre', 'q_v7_defisc', 'revu Vic')", c=COMMUNE)  # REVU
    s0.commit()
    s0.close()

    # --- ACTE (session S1) : rebuild de la commune, commit=True (donc commit par commune) ---
    s1 = session_factory()()
    division_or.build_divisions(s1, [COMMUNE], commit=True, log=lambda *_: None)
    s1.close()   # la session appelante DISPARAÎT — comme un process CLI qui se termine

    # --- CONSTAT (session S2, NOUVELLE connexion) : l'état est-il persisté et visible ? ---
    s2 = session_factory()()
    rows = {r[0]: r[1] for r in q(s2,
        "SELECT idu, note_revue FROM division_or_candidates WHERE commune = :c", c=COMMUNE)}
    s2.close()

    purge_ok = "99999000ZZ0001" not in rows          # périmé non-revu PURGÉ + commité + visible ailleurs
    revu_ok = rows.get("99999000ZZ0002") == "revu Vic"  # REVU préservé, visible ailleurs
    print(f"[cross-connexion] périmé non-revu purgé & persisté : {purge_ok}")
    print(f"[cross-connexion] tracé REVU préservé & persisté   : {revu_ok}")
    OK = purge_ok and revu_ok
finally:
    # --- NETTOYAGE : aucune trace synthétique ne subsiste ---
    sc = session_factory()()
    n = q(sc, "DELETE FROM division_or_candidates WHERE commune = :c", c=COMMUNE).rowcount
    sc.commit()
    sc.close()
    print(f"[cleanup] {n} ligne(s) synthétique(s) supprimée(s)")

print("INTEGRATION_OK" if OK else "INTEGRATION_FAIL")
