"""SOLIDITE-1 (Lot 5) — LA VÉRITÉ FACE AUX SOURCES, CHAQUE MOIS.

Une fois par mois, on tire 20 parcelles AU HASARD — stratifiées par commune et par cas difficile
(bizone, zone rouge, nouvelle, contenance ≠ dessin) — et on compare ce que LABUSE SERT à ce que disent
les sources officielles EN LIGNE : cadastre IGN (API Carto), GPU/Géorisques, DVF, bâtiments. On réutilise
l'oracle ORACLE-1 (`scripts.coherence.oracles`), qui sait déjà interroger ces sources (curl, backoff,
respect des cadences) et rendre des lignes {notion, objet, valeur_labuse, valeur_oracle, verdict}.

La fiche servie est lue EN-PROCESS (TestClient + session pilote) — comme le banc — pour que l'auth de prod
ne bloque pas la sonde. Les appels aux sources officielles, eux, partent en direct (curl), séquentiels et
espacés : aucun quota maltraité. AUCUNE écriture en base hors le rapport (`verite_sources_runs`)."""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

from sqlalchemy import text

log = logging.getLogger("labuse.verite")

_RACINE = Path(__file__).resolve().parents[2]

DDL = """
CREATE TABLE IF NOT EXISTS verite_sources_runs (
  id serial PRIMARY KEY,
  ts timestamptz NOT NULL DEFAULT now(),
  n_parcelles integer NOT NULL,
  n_vrai integer NOT NULL,
  n_faux integer NOT NULL,
  n_non_verifiable integer NOT NULL,
  faux jsonb NOT NULL DEFAULT '[]'::jsonb,
  echantillon jsonb NOT NULL DEFAULT '[]'::jsonb
)
"""

# Strates « cas difficiles » — chacune best-effort (une colonne/table absente → strate sautée, jamais
# d'erreur) ; tirage AU HASARD (ORDER BY random()) dans chaque strate, puis complément aléatoire.
_STRATES = [
    ("contenance_diff",
     "SELECT idu, commune FROM parcels WHERE contenance_m2 IS NOT NULL AND surface_m2 > 0 "
     "AND abs(contenance_m2 - surface_m2) > 0.05 * surface_m2 AND cadastre_disparue_le IS NULL "
     "ORDER BY random() LIMIT %(k)s"),
    ("bizone",
     "SELECT p.idu, p.commune FROM parcels p JOIN "
     "(SELECT idu FROM parcel_zone_plu GROUP BY idu HAVING count(DISTINCT zone_fam) > 1) z "
     "ON z.idu = p.idu WHERE p.cadastre_disparue_le IS NULL ORDER BY random() LIMIT %(k)s"),
    ("nouvelle",
     "SELECT idu, commune FROM parcels WHERE created_at > now() - interval '180 days' "
     "AND cadastre_disparue_le IS NULL ORDER BY random() LIMIT %(k)s"),
    ("zone_rouge",
     "SELECT p.idu, p.commune FROM parcels p JOIN parcel_residuel r ON r.idu = p.idu "
     "WHERE r.exigu_raison = 'ppr_rouge' ORDER BY random() LIMIT %(k)s"),
]


def _dsn() -> str:
    from .config import get_settings
    return get_settings().database_url.replace("postgresql+psycopg://", "postgresql://").replace(
        "postgresql+psycopg2://", "postgresql://")


def echantillon_stratifie(conn, n: int = 20) -> list[dict]:
    """20 parcelles tirées au hasard, stratifiées : ~n/5 par cas difficile (tant qu'il y en a), le reste
    en aléatoire réparti sur les communes. Robuste : une strate qui échoue est sautée (best-effort)."""
    par_strate = max(2, n // (len(_STRATES) + 1))
    vus: set[str] = set()
    sample: list[dict] = []
    for label, sql in _STRATES:
        try:
            with conn.cursor() as cur:
                cur.execute(sql, {"k": par_strate})
                for idu, commune in cur.fetchall():
                    if idu not in vus:
                        vus.add(idu)
                        sample.append({"idu": idu, "commune": commune, "slot": label})
        except Exception as exc:  # noqa: BLE001 — strate indisponible → sautée, jamais bloquant
            log.warning("strate %s indisponible (%s)", label, exc)
    # complément aléatoire réparti sur les communes jusqu'à n
    if len(sample) < n:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT DISTINCT ON (commune) idu, commune FROM parcels "
                    "WHERE cadastre_disparue_le IS NULL ORDER BY commune, random() LIMIT %(k)s",
                    {"k": n})
                for idu, commune in cur.fetchall():
                    if idu not in vus and len(sample) < n:
                        vus.add(idu)
                        sample.append({"idu": idu, "commune": commune, "slot": "aleatoire"})
        except Exception as exc:  # noqa: BLE001
            log.warning("complément aléatoire indisponible (%s)", exc)
    return sample[:n]


def jouer(n: int = 20) -> dict:
    """Tire l'échantillon, lit les sources officielles via l'oracle (fiche servie en-process), et rend
    {lignes, echantillon, bilan}. Aucune écriture en base ici (le rapport est posé par journaliser_passage)."""
    import psycopg
    if str(_RACINE) not in sys.path:
        sys.path.insert(0, str(_RACINE))
    from scripts.coherence import oracles

    dsn = _dsn()
    oracles.DSN = dsn                       # l'oracle ouvre sa propre connexion de lecture sur CETTE base
    conn = psycopg.connect(dsn)
    conn.read_only = True
    conn.autocommit = True        # lectures indépendantes : une strate qui casse n'avorte pas les suivantes
    try:
        sample = echantillon_stratifie(conn, n)
    finally:
        conn.close()
    if not sample:
        return {"lignes": [], "echantillon": [], "bilan": {"vrai": 0, "faux": 0, "non_verifiable": 0}}

    # la fiche SERVIE est lue en-process (auth active, session pilote) — pas d'HTTP public ni de quota.
    from fastapi.testclient import TestClient
    from .api import auth
    from .api.app import app
    from .api.protection import HOTE_INTERNE
    client = TestClient(app, client=(HOTE_INTERNE, 0))
    client.cookies.set(auth.COOKIE, auth.make_token())

    def _fiche_ep(idu: str):
        r = client.get(f"/parcels/{idu}")
        r.raise_for_status()
        return json.loads(r.content)

    ancien = oracles._fiche
    oracles._fiche = _fiche_ep
    try:
        v = oracles.lancer(temoins=[dict(t) for t in sample])   # copie : lancer enrichit en place
    finally:
        oracles._fiche = ancien

    lignes = [{k: l.get(k) for k in ("notion", "objet", "valeur_labuse", "valeur_oracle",
                                     "source_oracle", "url", "verdict")} for l in v.lignes]
    bilan = {verd: sum(1 for l in lignes if l["verdict"] == verd)
             for verd in ("vrai", "faux", "non_verifiable")}
    return {"lignes": lignes, "echantillon": sample, "bilan": bilan}


def ensure_table(db) -> None:
    db.execute(text(DDL))


def journaliser_passage(db, resultat: dict) -> dict:
    """Pose le rapport (`verite_sources_runs`) et, s'il y a des écarts « faux » (LABUSE ≠ source
    officielle), ouvre UN incident agrégé par la porte unique (parcelle + les deux valeurs dans le
    détail) ; un passage sans faux le referme. Les « non vérifiable » (source injoignable, aire ≠
    contenance DGFiP assumée) ne sont JAMAIS une alerte."""
    ensure_table(db)
    lignes = resultat.get("lignes") or []
    faux = [l for l in lignes if l["verdict"] == "faux"]
    bilan = resultat.get("bilan") or {}
    sample = resultat.get("echantillon") or []
    db.execute(text(
        "INSERT INTO verite_sources_runs (n_parcelles, n_vrai, n_faux, n_non_verifiable, faux, echantillon) "
        "VALUES (:np, :v, :f, :nv, CAST(:fx AS jsonb), CAST(:ec AS jsonb))"),
        {"np": len({l["objet"] for l in lignes}) or len(sample),
         "v": bilan.get("vrai", 0), "f": len(faux), "nv": bilan.get("non_verifiable", 0),
         "fx": json.dumps(faux, ensure_ascii=False), "ec": json.dumps(sample, ensure_ascii=False)})
    from . import ops_alertes
    if faux:
        détail = "\n".join(
            f"  • {l['objet']} — {l['notion']} : servi « {l['valeur_labuse']} » vs source « {l['valeur_oracle']} »"
            f" ({l['source_oracle']})" for l in faux[:15])
        plus = f"\n  (+{len(faux) - 15} autre(s))" if len(faux) > 15 else ""
        ops_alertes.signaler(db, "verite-sources",
                             f"Vérité sources : {len(faux)} écart(s) parcelle ↔ source officielle",
                             "Des valeurs servies divergent des sources officielles en ligne :\n"
                             + détail + plus + "\n(Détail : page Données › Vérité sources.)")
    else:
        ops_alertes.resoudre(db, "verite-sources")
    return {"n_parcelles": len(sample), "faux": len(faux), **bilan}


def derniers_passages(db, n: int = 12) -> list[dict]:
    ensure_table(db)
    rows = db.execute(text(
        "SELECT ts, n_parcelles, n_vrai, n_faux, n_non_verifiable, faux FROM verite_sources_runs "
        "ORDER BY id DESC LIMIT :n"), {"n": n}).mappings().all()
    return [{**dict(r), "ts": r["ts"].isoformat()} for r in rows]
