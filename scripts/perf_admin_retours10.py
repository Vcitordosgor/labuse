"""RETOURS-10 (T2) — audit de performance des endpoints admin sur la base RÉELLE de Vic.

Mesure, pour chaque page du dashboard, le temps de réponse du handler (hors HTTP : DB + assemblage),
le nombre de requêtes SQL exécutées et la requête la plus lente. Ne modifie RIEN (lectures + endpoints
GET seulement). Lancer : `python scripts/perf_admin_retours10.py`.
"""
from __future__ import annotations

import time

from sqlalchemy import event

from labuse.db import engine, session_scope

_eng = engine()
_curr: list[tuple[str, float]] = []


@event.listens_for(_eng, "before_cursor_execute")
def _before(conn, cursor, statement, parameters, context, executemany):  # noqa: ANN001, PLR0913
    conn.info["_t0"] = time.perf_counter()


@event.listens_for(_eng, "after_cursor_execute")
def _after(conn, cursor, statement, parameters, context, executemany):  # noqa: ANN001, PLR0913
    dt = time.perf_counter() - conn.info.get("_t0", time.perf_counter())
    origine = ""
    if dt > 0.5:  # pour les requêtes lentes, on note la ligne source labuse qui l'a émise
        import traceback
        for fr in reversed(traceback.extract_stack()):
            if "/src/labuse/" in fr.filename:
                origine = f"{fr.filename.split('/src/labuse/')[-1]}:{fr.lineno}"
                break
    _curr.append((" ".join(statement.split())[:140], dt, origine))


# neutralise la garde admin : on teste la REQUÊTE, pas l'authentification.
import labuse.api.auth as auth  # noqa: E402

auth.exiger_admin = lambda request=None: None

from labuse.api import courrier, dashboard, ops  # noqa: E402
from labuse.api import app as appmod  # noqa: E402


def measure(nom: str, fn) -> dict:
    _curr.clear()
    t0 = time.perf_counter()
    err = None
    try:
        fn()
    except Exception as e:  # noqa: BLE001
        err = f"{type(e).__name__}: {e}"[:80]
    total = time.perf_counter() - t0
    n = len(_curr)
    slow = max(_curr, key=lambda x: x[1]) if _curr else ("—", 0.0)
    return {"page": nom, "total_s": total, "n_sql": n, "slow_s": slow[1], "slow_sql": slow[0], "err": err}


def run() -> list[dict]:
    out = []
    with session_scope() as db:
        cases = [
            ("Pilotage", lambda: dashboard.admin_pilotage(request=None)),
            ("Comptes (licences)", lambda: dashboard.admin_licences(request=None)),
            ("Comptes (partage)", lambda: dashboard.admin_partage(request=None)),
            ("IA", lambda: dashboard.admin_ia(request=None)),
            ("Données · Catalogue (sources)", lambda: dashboard.admin_sources(request=None)),
            ("Données · Circuit (flux)", lambda: dashboard.admin_flux(request=None)),
            ("Données · Circuit (flux/runs)", lambda: dashboard.admin_flux_runs(request=None)),
            ("Produit", lambda: dashboard.admin_produit(request=None, jours=30)),
            ("Signalements", lambda: dashboard.admin_signalements(request=None)),
            ("Courrier", lambda: courrier.courrier_admin_demandes(request=None, statut=None, db=db)),
            ("Radar (check)", lambda: _radar_check()),
            ("Contacts (institutionnels)", lambda: ops.admin_contacts(request=None)),
            ("Contacts (commune)", lambda: _commune_contacts()),
            ("Sources client (liste)", lambda: appmod.list_sources(db=db)),
            ("Sources client (couverture)", lambda: appmod.sources_couverture(db=db)),
        ]
        for nom, fn in cases:
            out.append(measure(nom, fn))
    return out


def _radar_check():
    from labuse.pige import api as pige_api
    return pige_api.radar_check(request=None)


def _commune_contacts():
    # signature variable selon la version — on tente l'appel le plus simple.
    import inspect
    fn = ops.admin_commune_contacts if hasattr(ops, "admin_commune_contacts") else None
    if fn is None:
        return None
    sig = inspect.signature(fn)
    kw = {"request": None}
    return fn(**{k: v for k, v in kw.items() if k in sig.parameters})


if __name__ == "__main__":
    rows = run()
    rows_sorted = sorted(rows, key=lambda r: r["total_s"], reverse=True)
    print(f"\n{'PAGE':<34}{'TOTAL':>9}{'SQL':>6}{'+LENTE':>9}   REQUÊTE LA PLUS LENTE")
    print("-" * 120)
    for r in rows_sorted:
        flag = "  ⚠>2s" if r["total_s"] > 2 else ""
        err = f"  [ERR {r['err']}]" if r["err"] else ""
        print(f"{r['page']:<34}{r['total_s']*1000:>7.0f}ms{r['n_sql']:>6}{r['slow_s']*1000:>7.0f}ms   {r['slow_sql'][:70]}{flag}{err}")
    print("-" * 120)
    worst = max(rows, key=lambda r: r["total_s"])
    print(f"pire page : {worst['page']} — {worst['total_s']:.2f}s")
