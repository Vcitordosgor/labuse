"""SOURCES-4 lot 2 — DVF+ : adresse, nombre de pièces, surfaces Carrez, nombre de lots.

Ces champs SONT publiés par géo-DVF (Etalab) mais n'étaient PAS ingérés (ni colonne, ni raw).
Le mandat les veut sur la liste des ventes de la fiche. **Approche strictement ADDITIVE** : une
table LATÉRALE `dvf_mutation_detail`, clé `(id_mutation, id_parcelle)`, remplie depuis le MÊME
géo-DVF (mêmes années 2021-2025, filtre 974). On NE TOUCHE PAS `dvf_mutations` /
`dvf_mutations_parcelle` / la vue `v_parcel_dvf_last` / le scoring / le run servi — la table
latérale n'est lue PAR AUCUN d'eux ; la fiche des ventes la joint en LEFT JOIN. Le marché servi
(prix ancien/neuf, médianes) ne bouge pas : aucune valeur foncière n'est recalculée.

Une mutation peut porter plusieurs lignes (dispositions) sur une même parcelle : on agrège par
`(id_mutation, id_parcelle)` — adresse = 1re non vide, pièces = max, Carrez = somme des lots, lots
= max, ancien_id_parcelle conservé (traçabilité division/remembrement).
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from .layers_ingest import GEO_DVF_URL, GEO_DVF_YEARS, _client

TABLE = "dvf_mutation_detail"

DDL = f"""
CREATE TABLE IF NOT EXISTS {TABLE} (
    id_mutation        text NOT NULL,
    id_parcelle        varchar(14) NOT NULL,
    adresse            text,
    code_postal        varchar(5),
    nombre_pieces      integer,
    surface_carrez_m2  numeric(10,2),
    nombre_lots        integer,
    ancien_id_parcelle text,
    source_millesime   text,
    ingere_le          timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (id_mutation, id_parcelle)
)
"""


def ensure_table(session: Session) -> None:
    session.execute(text(DDL))


def _int(v: str | None) -> int | None:
    try:
        return int(float(v)) if v not in (None, "") else None
    except ValueError:
        return None


def _carrez(row: dict) -> float | None:
    tot = 0.0
    seen = False
    for i in range(1, 6):
        v = (row.get(f"lot{i}_surface_carrez") or "").replace(",", ".").strip()
        if v:
            try:
                tot += float(v)
                seen = True
            except ValueError:
                pass
    return round(tot, 2) if seen else None


def build_dvf_detail(session: Session, years: tuple[int, ...] = GEO_DVF_YEARS,
                     dep: str = "974", log=lambda *_: None) -> dict:
    """Remplit `dvf_mutation_detail` depuis géo-DVF (974). Idempotent (purge de la table).
    N'insère que les parcelles présentes dans `parcels` (île 974). Retourne les comptes."""
    import csv
    import gzip
    ensure_table(session)
    idus = {r[0] for r in session.execute(text("SELECT idu FROM parcels")).all()}
    # agrégat par (id_mutation, id_parcelle)
    agg: dict[tuple[str, str], dict] = {}
    with _client() as c:
        for y in years:
            r = c.get(GEO_DVF_URL.format(year=y, dep=dep), timeout=120.0)
            r.raise_for_status()
            txt = gzip.decompress(r.content).decode("utf-8", "replace")
            for row in csv.DictReader(txt.splitlines()):
                idm, idp = row.get("id_mutation"), row.get("id_parcelle")
                if not idm or not idp or idp not in idus:
                    continue
                adresse = " ".join(x for x in (
                    (row.get("adresse_numero") or "").strip(), (row.get("adresse_suffixe") or "").strip(),
                    (row.get("adresse_nom_voie") or "").strip()) if x) or None
                pieces, lots, carrez = _int(row.get("nombre_pieces_principales")), _int(row.get("nombre_lots")), _carrez(row)
                d = agg.setdefault((idm, idp), {
                    "adresse": None, "cp": None, "pieces": None, "carrez": None,
                    "lots": None, "anc": None, "mil": f"géo-DVF Etalab {y}"})
                if adresse and not d["adresse"]:
                    d["adresse"] = adresse
                    d["cp"] = (row.get("code_postal") or "").strip() or None
                if pieces is not None:
                    d["pieces"] = max(d["pieces"] or 0, pieces)
                if carrez is not None:
                    d["carrez"] = max(d["carrez"] or 0.0, carrez)
                if lots is not None:
                    d["lots"] = max(d["lots"] or 0, lots)
                if (anc := (row.get("ancien_id_parcelle") or "").strip()):
                    d["anc"] = anc
    session.execute(text(f"TRUNCATE {TABLE}"))
    rows = [{"idm": idm, "idp": idp, "adr": d["adresse"], "cp": d["cp"], "pc": d["pieces"],
             "cz": d["carrez"], "lo": d["lots"], "anc": d["anc"], "mil": d["mil"]}
            for (idm, idp), d in agg.items()]
    for i in range(0, len(rows), 5000):
        session.execute(text(
            f"INSERT INTO {TABLE} (id_mutation, id_parcelle, adresse, code_postal, nombre_pieces, "
            " surface_carrez_m2, nombre_lots, ancien_id_parcelle, source_millesime) "
            "VALUES (:idm, :idp, :adr, :cp, :pc, :cz, :lo, :anc, :mil)"), rows[i:i + 5000])
    session.execute(text("UPDATE data_sources SET last_sync_at = now() WHERE name = 'DVF / valeurs foncières'"))
    session.flush()
    n = session.execute(text(f"SELECT count(*) FROM {TABLE}")).scalar()
    log(f"dvf_mutation_detail : {n} couples (mutation, parcelle) 974")
    return {"couples": int(n or 0), "avec_adresse": sum(1 for r in rows if r["adr"]),
            "avec_carrez": sum(1 for r in rows if r["cz"])}
