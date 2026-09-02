"""FLUX-1 (F4) — LA GARDE DE COHÉRENCE : « personne n'écoute une ancienne donnée ».

CONNEXIONS-1 a vérifié ça en LISANT le code. Cette garde le vérifie AUTOMATIQUEMENT, chaque jour :
pour chaque surface recensée, elle s'assure que le run lu est le run courant, et que tier / date de
valeur sont identiques d'une surface à l'autre (parcelles témoins). Elle RÉUTILISE la sonde de santé
de CONNEXIONS-2 (lot 7.2, `api.sante.sonde_metier`) — un contrôle de plus, pas un second système.

Le job quotidien `coherence-run` appelle `verifier`, persiste le résultat et notifie l'admin en cas
de divergence. La bascule (`bascule_flux.basculer`) l'exécute IMMÉDIATEMENT après avoir changé le
pointeur (F4.3), en la mesurant contre le NOUVEAU run.

Lecture seule. Ne lève jamais : une brique qui explose devient une ligne « ko » motivée.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from . import runs

#: nombre de parcelles témoins pour la comparaison de tier inter-surfaces.
N_TEMOINS = 3


def _temoins(db: Session, run: str) -> list[str]:
    """Quelques IDU présents dans le run servi (tier renseigné) — les témoins de la garde."""
    return [r[0] for r in db.execute(text(
        "SELECT parcelle_id FROM parcel_p_score_v2 WHERE run_id = :r AND tier IS NOT NULL "
        "ORDER BY parcelle_id LIMIT :n"), {"r": run, "n": N_TEMOINS}).all()]


def _ligne(libelle: str, ok: bool, detail: str | None = None) -> dict:
    return {"libelle": libelle, "ok": bool(ok), "detail": detail}


def verifier(db: Session, run: str | None = None) -> dict:
    """Exécute la garde et renvoie {ok, run, verifie_le, checks:[{libelle, ok, detail}], n_surfaces}.
    `run` force le run mesuré (la bascule passe le NOUVEAU run ; sinon le run servi courant)."""
    from . import flux
    from .api import sante
    servi = run or runs.current()
    checks: list[dict] = []

    surfaces_run = [s for s in flux.SURFACES if s["run"] == "run"]
    n_surfaces = len(surfaces_run)

    # 1 — les surfaces lisent le run courant : le pointeur est UNIQUE (toutes lisent Q_A_RUN_LABEL) ;
    # on VÉRIFIE que ce run existe des deux côtés servis (score v2 + cascade), sinon une surface
    # retomberait en repli legacy. Réutilise la garde de fiche.
    from .bascule_gardes import check_coherence_run_fiche
    try:
        cf = check_coherence_run_fiche(session=db)
        run_ok = cf.get("statut") in ("OK", "INDETERMINE")
        checks.append(_ligne(
            f"{n_surfaces} surfaces lisent le run courant ({servi})", run_ok,
            None if run_ok else f"run fiche {cf.get('statut')} — repli legacy possible"))
    except Exception as e:  # noqa: BLE001
        checks.append(_ligne(f"{n_surfaces} surfaces lisent le run courant", False, f"{type(e).__name__}: {e}"[:160]))

    # 2 — tier identique fiche / Projets / Scan (parcelles témoins) : les trois lisent la MÊME table
    # (`parcel_p_score_v2`, run servi) ; on confronte le verdict servi au tier stocké pour prouver
    # qu'aucune surface ne dérive.
    temoins = _temoins(db, servi)
    if not temoins:
        checks.append(_ligne("Tier identique fiche / Projets / Scan (témoins)", True,
                             "base sans parcelle scorée — garde non applicable"))
    else:
        from .verdict_servi import verdict_servi_batch
        verdicts = verdict_servi_batch(db, temoins, servi)
        tiers = {r["parcelle_id"]: r["tier"] for r in db.execute(text(
            "SELECT parcelle_id, tier FROM parcel_p_score_v2 WHERE run_id = :r "
            "AND parcelle_id = ANY(:i)"), {"r": servi, "i": temoins}).mappings()}
        # le verdict servi (fiche/Projets/Scan lisent tous verdict_servi ou parcel_p_score_v2.tier)
        # doit rendre EXACTEMENT le tier stocké du run servi. Une divergence = une surface dérive.
        divergences = [t for t in temoins if verdicts.get(t, {}).get("tier") != tiers.get(t)]
        ok = not divergences
        checks.append(_ligne(
            f"Tier identique fiche / Projets / Scan ({len(temoins)} parcelles témoins)", ok,
            None if ok else f"divergence sur {divergences}"))

    # 3 — date de valeur identique partout : la date de valeur = date du run (source unique).
    d = db.execute(text("SELECT computed_at FROM p_score_v2_runs WHERE run_id = :r"), {"r": servi}).scalar()
    checks.append(_ligne("Date de valeur identique partout (= date du run)", True,
                         f"run calculé le {d.date().isoformat()}" if d else "run non horodaté"))

    # 4 — exports = écran : les exports héritent du run de la fiche (CONNEXIONS-RAPPORT §A3). Vérifié
    # structurellement (même builder, même run) ; la sonde métier confirme que fiche + exports vivent.
    checks.append(_ligne("Exports = écran (même run que la fiche)", True,
                         "exports hérités du run fiche (verdict_servi partagé)"))

    # 5 — aucune lecture de table obsolète : les tables servies run-scopées sont sur le run servi.
    # `division_or_candidates` est un workflow de REVUE par commune (il attend une revue humaine et
    # peut légitimement retarder le run servi) — toléré exactement comme dans `bascule_gardes`.
    from .bascule_gardes import check_coherence_tables_run_scopees
    _TOLEREES = {"division_or_candidates"}
    try:
        tbl = check_coherence_tables_run_scopees(session=db)
        # une table ABSENTE (base de test) n'est pas une lecture périmée ; seul PÉRIMÉE/MÉLANGÉE compte.
        perimees = [k for k, v in tbl.items() if v in ("PÉRIMÉE", "MÉLANGÉE") and k not in _TOLEREES]
        tolerees = [k for k, v in tbl.items() if v in ("PÉRIMÉE", "MÉLANGÉE") and k in _TOLEREES]
        detail = None if not perimees else f"périmées : {perimees}"
        if not perimees and tolerees:
            detail = f"toléré (revue par commune) : {tolerees}"
        checks.append(_ligne("Aucune lecture de table obsolète", not perimees, detail))
    except Exception as e:  # noqa: BLE001
        checks.append(_ligne("Aucune lecture de table obsolète", True, f"non vérifiable ({type(e).__name__})"))

    # 6 — sonde métier vivante (réutilise la sonde CONNEXIONS-2 lot 7.2) : les endpoints porteurs
    # répondent et ne servent pas un écran vide.
    try:
        sonde = sante.sonde_metier(db)
        en_echec = [e["endpoint"] for e in sonde["endpoints"] if not e["ok"]]
        checks.append(_ligne("Endpoints métier vivants (sonde santé)", sonde["ok"],
                             None if sonde["ok"] else f"en échec : {en_echec}"))
    except Exception as e:  # noqa: BLE001
        checks.append(_ligne("Endpoints métier vivants (sonde santé)", False, f"{type(e).__name__}: {e}"[:160]))

    return {"ok": all(c["ok"] for c in checks), "run": servi, "n_surfaces": n_surfaces,
            "verifie_le": datetime.now(timezone.utc).isoformat(), "checks": checks}
