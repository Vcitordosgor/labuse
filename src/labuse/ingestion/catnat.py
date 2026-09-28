"""CIRCUIT-3 lot 6.1 — INGESTION DES ARRÊTÉS CatNat (GASPAR / Géorisques).

Réparation d'une fuite : `catnat_n` (arrêtés de catastrophe naturelle par commune, fiche commune)
était FAUX — l'ancienne ingestion lisait UNE page (`connector.catnat`, page_size par défaut) et
tronquait à ~10 arrêtés par commune ; la commande d'ingestion avait ensuite été retirée (spin-off
« Vues » M12). On réingère ici via `connector.catnat_arretes` (paginé) → tous les arrêtés.

Idempotent : upsert sur (insee, type_peril, date_arrete, date_debut). `raw` garde l'objet GASPAR.
"""
from __future__ import annotations

import json as _json
import logging
from datetime import date, datetime

from sqlalchemy import text

from .run_all import REUNION_COMMUNES

log = logging.getLogger("labuse.ingestion.catnat")

DDL = """
CREATE TABLE IF NOT EXISTS catnat_arretes (
  id serial PRIMARY KEY,
  insee varchar(5) NOT NULL,
  commune varchar(80),
  type_peril text,
  date_arrete date,
  date_debut date,
  date_fin date,
  raw jsonb,
  ingested_at timestamptz DEFAULT now(),
  UNIQUE (insee, type_peril, date_arrete, date_debut)
);
CREATE INDEX IF NOT EXISTS ix_catnat_commune_date ON catnat_arretes (commune, date_arrete)
"""


def ensure_tables(engine) -> None:
    with engine.begin() as c:
        for stmt in DDL.split(";"):
            if stmt.strip():
                c.execute(text(stmt))


def _parse_date(v) -> date | None:
    """GASPAR livre du JJ/MM/AAAA ; on tolère l'ISO."""
    if not v:
        return None
    s = str(v).strip()
    try:
        return datetime.strptime(s, "%d/%m/%Y").date()
    except ValueError:
        pass
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def ingest_catnat(session, *, connector=None, insee_list: list[str] | None = None,
                  remplacer: bool = False) -> dict:
    """Réingère les arrêtés CatNat des 24 communes (paginé — plus de troncature à 10).

    `remplacer=True` vide la table d'abord (pour solder proprement une version tronquée)."""
    if connector is None:
        from ..connectors.georisques import GeorisquesConnector
        connector = GeorisquesConnector()
    by_insee = dict(REUNION_COMMUNES)
    targets = insee_list or [i for i, _ in REUNION_COMMUNES]
    if remplacer:
        session.execute(text("DELETE FROM catnat_arretes"))
    total, communes_ok, erreurs, par_commune = 0, 0, {}, {}
    for insee in targets:
        try:
            items = list(connector.catnat_arretes(insee))
        except Exception as exc:  # noqa: BLE001 — une commune en panne n'arrête pas le lot
            erreurs[insee] = f"{type(exc).__name__}: {exc}"
            continue
        n_commune = 0
        # COHERENCE-FIX-1 (lot F) — UN ARRÊTÉ = UN CODE NATIONAL (par péril) : GASPAR sert parfois
        # le même arrêté en PLUSIEURS lignes qui ne diffèrent que par date_debut/fin_evt (constaté :
        # INTE1401216A doublé à Saint-Joseph ; Saint-Denis 21 lignes pour 19 arrêtés distincts).
        # L'ancien upsert (clé … + date_debut) gardait ces doublons → la fiche sur-comptait de 1-2.
        # On dédoublonne ICI par (code national, péril, date d'arrêté) — la ligne la plus longue
        # (date_fin la plus tardive) gagne.
        vus: dict[tuple, dict] = {}
        for it in items:
            cle = (it.get("code_national_catnat") or f"sans-code:{it.get('date_publication_arrete')}",
                   it.get("libelle_risque_jo"), it.get("date_publication_arrete"))
            deja = vus.get(cle)
            if deja is None or (it.get("date_fin_evt") or "") > (deja.get("date_fin_evt") or ""):
                vus[cle] = it
        for it in vus.values():
            session.execute(text("""
                INSERT INTO catnat_arretes (insee, commune, type_peril, date_arrete,
                                            date_debut, date_fin, raw)
                VALUES (:insee, :commune, :peril, :arrete, :debut, :fin, CAST(:raw AS jsonb))
                ON CONFLICT (insee, type_peril, date_arrete, date_debut) DO UPDATE SET
                  date_fin = EXCLUDED.date_fin, raw = EXCLUDED.raw"""), {
                "insee": insee,
                "commune": by_insee.get(insee) or it.get("libelle_commune"),
                "peril": it.get("libelle_risque_jo"),
                "arrete": _parse_date(it.get("date_publication_arrete")),
                "debut": _parse_date(it.get("date_debut_evt")),
                "fin": _parse_date(it.get("date_fin_evt")),
                "raw": _json.dumps(it, ensure_ascii=False),
            })
            total += 1
            n_commune += 1
        par_commune[insee] = n_commune
        communes_ok += 1
    session.flush()
    return {"communes_ok": communes_ok, "arretes": total, "erreurs": erreurs,
            "par_commune": par_commune}


# ───────────── SOURCES-2 lot 1 — recoupement API GASPAR ↔ export CSV national ─────────────

GASPAR_ZIP = "https://files.georisques.fr/GASPAR/gaspar.zip"


def recouper_csv_national(session, *, client=None) -> dict:
    """Le rapport producteurs signale que l'API CatNat renvoie PARFOIS moins d'arrêtés que le
    site (codes de risque non mappés) : on recoupe la base (ingérée par l'API paginée) avec
    l'export CSV national GASPAR (`catnat_gaspar_*.csv` du zip officiel), à la maille
    (commune, ligne d'arrêté) sur le 974. Rend les deux comptes et l'écart — un écart > 0 dit
    que l'API a perdu des arrêtés (à réingérer/documenter), jamais l'inverse silencieux.
    Mesuré 13/09/2026 : CSV 426 = base 426, écart 0."""
    import csv
    import io
    import zipfile

    import httpx

    from .. import constants
    from ..config import get_settings

    own = client is None
    c = client or httpx.Client(timeout=max(get_settings().http_timeout_s, 180.0),
                               headers={"User-Agent": constants.USER_AGENT},
                               follow_redirects=True)
    try:
        r = c.get(GASPAR_ZIP)
        r.raise_for_status()
    finally:
        if own:
            c.close()
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    nom = next((n for n in zf.namelist() if n.startswith("catnat_gaspar")), None)
    if nom is None:
        raise RuntimeError(f"catnat_gaspar_*.csv absent du zip GASPAR ({zf.namelist()})")
    # COHERENCE-FIX-1 (lot F) — même règle de compte que l'ingestion : UN arrêté = UN code
    # national par (péril, date d'arrêté). Le CSV national porte les mêmes lignes doublées que
    # l'API (date_debut_evt qui varie) — les compter brutes faisait crier le recoupement sur un
    # écart qui n'existe pas.
    cles_csv: set[tuple] = set()
    with zf.open(nom) as f:
        for row in csv.DictReader(io.TextIOWrapper(f, encoding="utf-8"), delimiter=";"):
            if (row.get("code_commune") or "").startswith("974"):
                # colonnes RÉELLES du CSV GASPAR : id_gaspar (code arrêté), lib_risque_jo,
                # date_signature_arrete — même grain que l'ingestion API dédoublonnée.
                cles_csv.add((row.get("code_commune"), row.get("id_gaspar"),
                              row.get("lib_risque_jo"), row.get("date_signature_arrete")))
    n_csv = len(cles_csv)
    n_base = int(session.execute(text("SELECT count(*) FROM catnat_arretes")).scalar() or 0)
    return {"csv_national": n_csv, "base_api": n_base, "ecart": n_csv - n_base,
            "fichier": nom}
