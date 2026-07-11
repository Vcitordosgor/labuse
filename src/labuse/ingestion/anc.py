"""Wave ANC & Végétation, Lot A — assainissement non collectif.

Trois couches, de la plus fiable à la plus précise :
- A1 INSEE : fichier détail Logements RP2022, variable EGOUL (« mode d'évacuation des
  eaux usées », DOM uniquement : 1=égout, 2=fosse septique, 3=puisard, 4=à même le
  sol), pondérée IPONDL, agrégée à l'IRIS (maille la plus fine diffusée — 330 IRIS au
  974) avec repli commune. Taux de NON-raccordement = modalités 2+3+4.
- A2 zonages officiels : annexes d'assainissement versées au Géoportail de l'urbanisme
  (couches d'information CNIG `typeinf='19'`) — constat du 11/07/2026 : 4 communes sur
  24 en SIG (L'Étang-Salé, Le Port, Saint-Denis, Saint-Paul). Ailleurs : proba seule.
- A3 signal `anc_mutation` : parcelle bâtie × (zone officielle ANC OU proba ≥ seuil) ×
  mutation DVF < 12 mois (fenêtre ANCRÉE sur le dernier millésime DVF, jamais now()).

Mécanisme légal (références vérifiées sur Légifrance le 11/07/2026) : le diagnostic ANC
est joint au DDT à la vente (art. L.1331-11-1 CSP) et, en cas de non-conformité,
l'acquéreur fait procéder aux travaux de mise en conformité dans un délai d'UN AN après
l'acte de vente (art. L.271-4 II CCH). Le module QUALIFIE des travaux probables — il ne
prétend jamais détecter des installations non conformes (donnée qu'on n'a pas).

Calage : Office de l'eau Réunion, Chronique de l'eau n°149 (déc. 2025, données 2023) —
~189 000 installations ANC ≈ 46 % des foyers de l'île. Seed versionné
data/anc/office_eau_chronique_149_2023.csv (chiffres du texte p. 13, pas de scraping).

Attribution : INSEE (RP2022, fichier détail Logements), IGN (contours IRIS),
Géoportail de l'urbanisme. RGPD : agrégats statistiques et niveau parcelle uniquement.
"""
from __future__ import annotations

import csv
import io
import json
import time
import zipfile
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import _repo_root, load_yaml_config
from .run_all import REUNION_COMMUNES

DDL = """
CREATE TABLE IF NOT EXISTS anc_maille_taux (
  maille        varchar(8) NOT NULL,      -- 'iris' | 'commune'
  code          varchar(9) NOT NULL,      -- code IRIS (9) ou INSEE (5)
  insee         varchar(5) NOT NULL,
  taux_non_racc real NOT NULL,            -- % rés. principales NON raccordées (EGOUL 2/3/4)
  n_logements   real,                     -- somme des poids IPONDL (modalités 1-4)
  millesime     varchar(12),
  PRIMARY KEY (maille, code)
);
CREATE TABLE IF NOT EXISTS parcel_anc (
  idu        varchar(14) PRIMARY KEY REFERENCES parcels (idu),
  zone_anc   text,                        -- 'anc' | 'collectif' | NULL (inconnu)
  source     text,                        -- 'zonage_officiel' | 'proba_insee'
  proba_anc  int,                         -- 0-100, renseigné même quand zonage présent
  updated_at timestamptz DEFAULT now()
);
"""

_INSEE_NOM = dict(REUNION_COMMUNES)                       # insee → nom
_NOM_INSEE = {nom: insee for insee, nom in REUNION_COMMUNES}


def _cfg() -> dict[str, Any]:
    return load_yaml_config("anc_vegetation")["anc"]


# ── A1.1 : INSEE EGOUL (fichier détail Logements) ───────────────────────────────

def _telecharger_rp(url: str, dest: Path, log=print) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    log(f"  téléchargement {url} → {dest} (~400 Mo, une fois)")
    tmp = dest.with_suffix(".part")
    with httpx.stream("GET", url, timeout=None,
                      headers={"User-Agent": "labuse/anc-974"}, follow_redirects=True) as r:
        r.raise_for_status()
        with tmp.open("wb") as f:
            for chunk in r.iter_bytes(1 << 20):
                f.write(chunk)
    tmp.rename(dest)
    return dest


def ingest_insee_egoul(session: Session, *, fichier: str | None = None,
                       log=print) -> dict[str, Any]:
    """Streame le fichier détail national (zip, ~26 M de lignes), ne garde que le 974,
    agrège le taux de non-raccordement pondéré (IPONDL) par IRIS et par commune."""
    session.execute(text(DDL))
    cfg = _cfg()["insee"]
    cache = Path(cfg["cache_dir"])
    cache = cache if cache.is_absolute() else _repo_root() / cache
    zpath = Path(fichier) if fichier else _telecharger_rp(
        cfg["url_zip"], cache / Path(cfg["url_zip"]).name, log)
    acc: dict[tuple[str, str], list[float]] = {}   # (maille, code) → [w_total, w_non_racc]
    t0 = time.monotonic()
    n_974 = 0
    with zipfile.ZipFile(zpath) as z:
        name = next(n for n in z.namelist() if n.lower().endswith(".csv"))
        with z.open(name) as raw:
            rd = csv.reader(io.TextIOWrapper(raw, encoding="utf-8", newline=""),
                            delimiter=";")
            header = next(rd)
            idx = {c: header.index(c) for c in ("COMMUNE", "IRIS", "EGOUL", "IPONDL")}
            i_com, i_iris, i_eg, i_w = (idx[c] for c in ("COMMUNE", "IRIS", "EGOUL", "IPONDL"))
            for i, row in enumerate(rd):
                if i % 5_000_000 == 0 and i:
                    log(f"  RP : {i / 1e6:.0f} M lignes lues, {n_974} au 974"
                        f" ({i / (time.monotonic() - t0):.0f}/s)")
                com = row[i_com]
                if not com.startswith("974"):
                    continue
                eg = row[i_eg]
                if eg not in ("1", "2", "3", "4"):   # Y = hors rés. principale, Z = métropole
                    continue
                n_974 += 1
                w = float(row[i_w].replace(",", "."))
                non = w if eg != "1" else 0.0
                for key in (("commune", com),
                            (("iris", row[i_iris]) if len(row[i_iris]) == 9
                             and "Z" not in row[i_iris] else None)):
                    if key is None:
                        continue
                    a = acc.setdefault(key, [0.0, 0.0])
                    a[0] += w
                    a[1] += non
    session.execute(text("DELETE FROM anc_maille_taux"))
    for (maille, code), (w_tot, w_non) in acc.items():
        session.execute(text("""
            INSERT INTO anc_maille_taux (maille, code, insee, taux_non_racc, n_logements,
                                         millesime)
            VALUES (:m, :c, :insee, :t, :n, :mil)
        """), {"m": maille, "c": code, "insee": code[:5], "mil": cfg["millesime"],
               "t": round(100.0 * w_non / w_tot, 2) if w_tot else 0.0,
               "n": round(w_tot, 1)})
    session.commit()
    n_com = sum(1 for (m, _) in acc if m == "commune")
    n_iris = sum(1 for (m, _) in acc if m == "iris")
    if n_com != 24:
        log(f"  ⚠ {n_com} communes agrégées (24 attendues) — vérifier le millésime")
    return {"logements_974": n_974, "communes": n_com, "iris": n_iris,
            "millesime": cfg["millesime"]}


# ── A1.2 : contours IRIS (IGN Géoplateforme, WFS) ───────────────────────────────

def ingest_iris_contours(session: Session, log=print) -> dict[str, int]:
    cfg = _cfg()["iris"]
    lat0, lon0, lat1, lon1 = cfg["bbox"]
    feats: list[dict] = []
    start = 0
    with httpx.Client(headers={"User-Agent": "labuse/anc-974"}, timeout=120) as client:
        while True:
            r = client.get(cfg["wfs_url"], params={
                "SERVICE": "WFS", "VERSION": "2.0.0", "REQUEST": "GetFeature",
                "TYPENAMES": cfg["typename"], "COUNT": 1000, "STARTINDEX": start,
                "outputFormat": "application/json",
                "BBOX": f"{lat0},{lon0},{lat1},{lon1},urn:ogc:def:crs:EPSG::4326"})
            r.raise_for_status()
            page = r.json().get("features", [])
            feats.extend(f for f in page
                         if str(f["properties"].get("code_insee", "")).startswith("974"))
            if len(page) < 1000:
                break
            start += 1000
    session.execute(text("DELETE FROM spatial_layers WHERE kind = 'iris_insee'"))
    for f in feats:
        p = f["properties"]
        session.execute(text("""
            INSERT INTO spatial_layers (kind, subtype, name, geom, attrs, commune)
            VALUES ('iris_insee', :code, :nom,
                    ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:gj), 4326)),
                    CAST(:attrs AS jsonb), :commune)
        """), {"code": p["code_iris"], "nom": p.get("nom_iris"),
               "gj": json.dumps(f["geometry"]),
               "attrs": json.dumps({"type_iris": p.get("type_iris"),
                                    "source": "Contours IRIS © IGN/INSEE"}),
               "commune": _INSEE_NOM.get(p.get("code_insee"), p.get("nom_commune"))})
    session.commit()
    log(f"  {len(feats)} IRIS 974 ingérés (spatial_layers kind='iris_insee')")
    return {"iris": len(feats)}


# ── A2 : zonages officiels d'assainissement (GPU, couches d'information) ────────

def _classer_libelle(libelle: str, classification: list[dict]) -> str | None:
    lib = (libelle or "").lower()
    for regle in classification:
        if regle["contient"] in lib:
            return regle["zone"]
    return None


def ingest_zonages_gpu(session: Session, log=print) -> dict[str, Any]:
    """Balaye les 24 communes : couches d'information surfaciques GPU typeinf 19
    (« zonage d'assainissement » CNIG). Tableau de couverture pour le rapport."""
    cfg = _cfg()["gpu"]
    couverture: dict[str, Any] = {}
    session.execute(text(
        "DELETE FROM spatial_layers WHERE kind = 'zonage_assainissement'"))
    with httpx.Client(headers={"User-Agent": "labuse/anc-974"}, timeout=120) as client:
        for insee, nom in REUNION_COMMUNES:
            try:
                r = client.get(cfg["url_info_surf"], params={"partition": f"DU_{insee}"})
                r.raise_for_status()
                feats = [f for f in r.json().get("features", [])
                         if f["properties"].get("typeinf") == cfg["typeinf_assainissement"]]
            except (httpx.HTTPError, ValueError) as e:
                couverture[nom] = {"source": "erreur GPU", "detail": str(e)}
                continue
            n_ok = 0
            libelles: dict[str, int] = {}
            for f in feats:
                lib = f["properties"].get("libelle") or ""
                zone = _classer_libelle(lib, cfg["classification"])
                libelles[lib] = libelles.get(lib, 0) + 1
                if zone is None:
                    continue   # libellé non classable (ex. captages mal typés 19) : ignoré
                session.execute(text("""
                    INSERT INTO spatial_layers (kind, subtype, name, geom, attrs, commune)
                    VALUES ('zonage_assainissement', :zone, :lib,
                            ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:gj), 4326)),
                            CAST(:attrs AS jsonb), :commune)
                """), {"zone": zone, "lib": lib[:255], "gj": json.dumps(f["geometry"]),
                       "attrs": json.dumps({"libelle": lib, "typeinf": "19",
                                            "partition": f"DU_{insee}",
                                            "source": "Géoportail de l'urbanisme"}),
                       "commune": nom})
                n_ok += 1
            couverture[nom] = ({"source": "zonage_officiel (GPU)", "polygones": n_ok,
                                "libelles": libelles} if n_ok
                               else {"source": "proba_insee (aucun zonage SIG au GPU)"})
            log(f"  {nom} : {couverture[nom]['source']}"
                + (f" — {n_ok} polygones" if n_ok else ""))
    session.commit()
    return couverture


# ── A1.3 + A2.3 : proba par parcelle bâtie + application des zonages ────────────

def compute_proba(session: Session, *, batch: int = 20000, log=print) -> dict[str, Any]:
    session.execute(text(DDL))
    cfg = _cfg()["proba"]
    params = {"emin": float(cfg["emprise_batie_min_m2"]),
              "bonus": int(cfg["bonus_hors_zone_u_pts"]),
              "dist": float(cfg["distance_zone_u_m"]),
              "plancher": int(cfg["plancher"]), "plafond": int(cfg["plafond"]),
              "batch": batch}
    total = 0
    t0 = time.monotonic()
    while True:
        # le bonus « loin de toute zone U » ne s'applique que si la commune a un PLU
        # ingéré (sinon on surestimerait TOUTES ses parcelles)
        n = session.execute(text("""
            WITH lot AS (
              SELECT p.idu, p.commune, p.geom_2975, ST_Centroid(p.geom_2975) AS c
              FROM parcels p
              JOIN parcel_residuel_bati rb ON rb.idu = p.idu AND rb.emprise_batie_m2 > :emin
              WHERE NOT EXISTS (SELECT 1 FROM parcel_anc pa WHERE pa.idu = p.idu)
              LIMIT :batch
            ),
            calc AS (
              SELECT lot.idu,
                     coalesce(ir.taux_non_racc, amc.taux_non_racc) AS taux,
                     CASE WHEN EXISTS (SELECT 1 FROM spatial_layers zc
                                       WHERE zc.kind = 'plu_gpu_zone'
                                         AND zc.commune = lot.commune)
                           AND NOT EXISTS (SELECT 1 FROM spatial_layers z
                                           WHERE z.kind = 'plu_gpu_zone' AND z.subtype = 'U'
                                             AND ST_DWithin(z.geom_2975, lot.c, :dist))
                          THEN :bonus ELSE 0 END AS bonus
              FROM lot
              LEFT JOIN LATERAL (
                SELECT amt.taux_non_racc FROM spatial_layers sl
                JOIN anc_maille_taux amt ON amt.maille = 'iris' AND amt.code = sl.subtype
                WHERE sl.kind = 'iris_insee' AND ST_Contains(sl.geom_2975, lot.c)
                LIMIT 1) ir ON true
              LEFT JOIN LATERAL (
                SELECT amt2.taux_non_racc FROM anc_maille_taux amt2
                WHERE amt2.maille = 'commune'
                  AND amt2.code = (CAST(:insee_map AS jsonb) ->> lot.commune)
                LIMIT 1) amc ON true
            )
            INSERT INTO parcel_anc (idu, source, proba_anc, updated_at)
            SELECT idu, 'proba_insee',
                   LEAST(:plafond, GREATEST(:plancher, round(taux + bonus)))::int, now()
            FROM calc WHERE taux IS NOT NULL
            ON CONFLICT (idu) DO NOTHING
        """), {**params, "insee_map": json.dumps(_NOM_INSEE)}).rowcount
        if not n:
            break
        session.commit()
        total += n
        log(f"  proba_anc : {total} parcelles ({total / (time.monotonic() - t0):.0f}/s)")
    n_zonage = _appliquer_zonages(session)
    session.commit()
    return {"parcelles": total, "zonage_officiel": n_zonage}


def _appliquer_zonages(session: Session) -> int:
    """Là où un zonage officiel couvre le centroïde : zone_anc + source. proba_anc est
    CONSERVÉ (mandat : renseigné même quand le zonage officiel est présent)."""
    return session.execute(text("""
        UPDATE parcel_anc pa
        SET zone_anc = z.subtype, source = 'zonage_officiel', updated_at = now()
        FROM parcels p
        CROSS JOIN LATERAL (
          SELECT sl.subtype FROM spatial_layers sl
          WHERE sl.kind = 'zonage_assainissement'
            AND ST_Contains(sl.geom_2975, ST_Centroid(p.geom_2975))
          ORDER BY (sl.subtype = 'anc') DESC LIMIT 1
        ) z
        WHERE p.idu = pa.idu
          AND (pa.zone_anc IS DISTINCT FROM z.subtype OR pa.source <> 'zonage_officiel')
    """)).rowcount


def calage_office_eau(session: Session) -> list[dict]:
    """Contrôle croisé : taux INSEE par commune vs chiffres Office de l'eau (seed)."""
    seed = _repo_root() / "data" / "anc" / "office_eau_chronique_149_2023.csv"
    out: list[dict] = []
    with seed.open(encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter=";"):
            if not row["insee"]:
                continue
            t = session.execute(text(
                "SELECT taux_non_racc FROM anc_maille_taux"
                " WHERE maille = 'commune' AND code = :c"), {"c": row["insee"]}).scalar()
            out.append({"commune": row["commune"], "office_eau_pct": float(row["pct_foyers_anc"]),
                        "insee_pct": float(t) if t is not None else None,
                        "delta": round(float(t) - float(row["pct_foyers_anc"]), 1)
                        if t is not None else None})
    return out


# ── A3 : signal anc_mutation ────────────────────────────────────────────────────

def signal_mutation(session: Session) -> int:
    """Parcelle bâtie (⊂ parcel_anc) × (zone ANC officielle OU proba ≥ seuil) ×
    mutation DVF < 12 mois — fenêtre ancrée sur le dernier millésime DVF (convention
    du moteur de segments : DVF publie avec ~6 mois de retard)."""
    cfg = _cfg()["signal"]
    session.execute(text("DELETE FROM parcel_signals WHERE signal_type = 'anc_mutation'"))
    n = session.execute(text("""
        WITH ref AS (SELECT max(date_mutation) AS d FROM dvf_mutations_parcelle)
        INSERT INTO parcel_signals (parcel_id, signal_type, payload, detected_at)
        SELECT p.id, 'anc_mutation',
               jsonb_build_object(
                 'date_mutation', m.date_mutation, 'valeur_fonciere', m.valeur_fonciere,
                 'zone_anc', pa.zone_anc, 'source', pa.source, 'proba_anc', pa.proba_anc,
                 'mecanisme', 'Diagnostic ANC joint au DDT à la vente (art. L.1331-11-1 '
                              'CSP) ; travaux de mise en conformité par l''acquéreur sous '
                              '1 an en cas de non-conformité (art. L.271-4 II CCH)'),
               now()
        FROM parcel_anc pa
        JOIN parcels p ON p.idu = pa.idu
        CROSS JOIN ref
        JOIN LATERAL (
          SELECT d.date_mutation, d.valeur_fonciere FROM dvf_mutations_parcelle d
          WHERE d.id_parcelle = pa.idu
            AND d.date_mutation > ref.d - make_interval(months => CAST(:mois AS int))
          ORDER BY d.date_mutation DESC LIMIT 1
        ) m ON true
        WHERE pa.zone_anc = 'anc' OR pa.proba_anc >= :seuil
    """), {"mois": int(cfg["fenetre_mois"]), "seuil": int(cfg["proba_seuil"])}).rowcount
    session.commit()
    return n


# ── Rapport : tableau de couverture ─────────────────────────────────────────────

def couverture(session: Session) -> list[dict]:
    rows = session.execute(text("""
        SELECT p.commune,
               count(*) FILTER (WHERE pa.source = 'zonage_officiel') AS off,
               count(*) FILTER (WHERE pa.source = 'proba_insee') AS proba,
               round(avg(pa.proba_anc)) AS proba_moy
        FROM parcel_anc pa JOIN parcels p ON p.idu = pa.idu
        GROUP BY p.commune ORDER BY p.commune
    """)).all()
    return [{"commune": c, "parcelles_zonage_officiel": o, "parcelles_proba": pr,
             "proba_moyenne": int(pm or 0)} for c, o, pr, pm in rows]
