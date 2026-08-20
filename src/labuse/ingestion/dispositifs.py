"""M134 — la couche « Dispositifs et périmètres ». Matérialise dans spatial_layers les items
qui n'y sont pas déjà, pour qu'ils passent par le MÊME endpoint (/map/layers.geojson) et la
MÊME machinerie carte que les couches existantes.

Trois kinds construits ici (QPV et NPNRU/ANRU sont DÉJÀ en base, ingérés ailleurs) :
  · `tva_primo`  — le buffer 500 m autour des QPV (« TVA réduite primo-accédant »). PÉRIMÈTRE
                   DÉRIVÉ, calculé par LABUSE (ST_Buffer sur les QPV) — jamais une source amont.
                   On stocke la COURONNE (buffer − QPV) pour ne pas recouvrir les QPV à l'écran.
  · `zfang`      — aplat de la COMMUNE ENTIÈRE (frontières IGN communes974.geojson), subtype =
                   régime (renforce/standard) pour la couleur data-driven. Attribut commune, PAS
                   un périmètre fin (glose « commune entière »).
  · `frr`        — idem, subtype = classement (totalite/partie ; « hors » n'est pas dessiné,
                   c'est l'absence). territoire_fiscal_commune fait foi.

Idempotent (purge par kind avant réinsertion). geom en 4326 ; geom_2975 posé par le trigger.
"""
from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..territoire_fiscal import (FRR_LIEN, FRR_MILLESIME, ZFANG_LIEN, ZFANG_MILLESIME,
                                 _FRR_LIBELLE, _ZFANG_LIBELLE)

QPV_BUFFER_M = 500   # « QPV + 500 m » — le périmètre TVA réduite primo-accédant (dérivé)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def build_tva_primo(session: Session) -> int:
    """Buffer 500 m autour des QPV, MOINS les QPV eux-mêmes (la couronne). Un item par commune
    portant un QPV (filtrable), géométrie dérivée en 2975 (mètres) puis reprojetée en 4326."""
    session.execute(text("DELETE FROM spatial_layers WHERE kind = 'tva_primo'"))
    # par commune : union des QPV, buffer 500 m, différence = la bande des 500 m
    rows = session.execute(text(
        """WITH q AS (
             SELECT commune, ST_Union(geom_2975) AS g
             FROM spatial_layers WHERE kind = 'qpv' AND commune IS NOT NULL
             GROUP BY commune)
           SELECT commune,
                  ST_AsText(ST_Transform(
                    ST_Multi(ST_Difference(ST_Buffer(g, :d), g)), 4326)) AS ring
           FROM q"""), {"d": QPV_BUFFER_M}).mappings().all()
    n = 0
    for r in rows:
        if not r["ring"]:
            continue
        session.execute(text(
            "INSERT INTO spatial_layers (kind, subtype, name, commune, geom, attrs) VALUES "
            "('tva_primo', 'derive', :nom, :c, ST_GeomFromText(:g, 4326), CAST(:a AS jsonb))"),
            {"nom": f"Bande 500 m — {r['commune']}", "c": r["commune"], "g": r["ring"],
             "a": json.dumps({"derive": True, "buffer_m": QPV_BUFFER_M, "source": "LABUSE (dérivé des QPV)"})})
        n += 1
    return n


def build_zfang_frr(session: Session) -> dict:
    """Aplat commune pour ZFANG et FRR : géométrie IGN (communes974.geojson), attribut de
    territoire_fiscal_commune. Un item par commune ; subtype porte le régime/classement pour
    la couleur. FRR « hors » n'est PAS dessiné (l'absence ne se peint pas)."""
    geo = json.loads((_repo_root() / "frontend" / "public" / "communes974.geojson").read_text("utf-8"))
    fisc = {r["insee"]: r for r in session.execute(text(
        "SELECT insee, commune, zfang_regime, frr_classement FROM territoire_fiscal_commune")).mappings()}
    session.execute(text("DELETE FROM spatial_layers WHERE kind IN ('zfang', 'frr')"))
    n_z = n_f = 0
    for feat in geo["features"]:
        insee = feat["properties"].get("code")
        row = fisc.get(insee)
        if not row:
            continue
        g = json.dumps(feat["geometry"])
        # ZFANG : toutes les communes sont ZFANG (DOM de plein droit) — régime en subtype.
        session.execute(text(
            "INSERT INTO spatial_layers (kind, subtype, name, commune, geom, attrs) VALUES "
            "('zfang', :st, :nom, :c, ST_GeomFromGeoJSON(:g), CAST(:a AS jsonb))"),
            {"st": row["zfang_regime"], "nom": row["commune"], "c": row["commune"], "g": g,
             "a": json.dumps({"regime": row["zfang_regime"], "libelle": _ZFANG_LIBELLE[row["zfang_regime"]],
                              "maille": "commune", "source_ref": ZFANG_MILLESIME, "lien": ZFANG_LIEN})})
        n_z += 1
        # FRR : « hors » = pas classée → pas de dessin.
        if row["frr_classement"] != "hors":
            session.execute(text(
                "INSERT INTO spatial_layers (kind, subtype, name, commune, geom, attrs) VALUES "
                "('frr', :st, :nom, :c, ST_GeomFromGeoJSON(:g), CAST(:a AS jsonb))"),
                {"st": row["frr_classement"], "nom": row["commune"], "c": row["commune"], "g": g,
                 "a": json.dumps({"classement": row["frr_classement"], "libelle": _FRR_LIBELLE[row["frr_classement"]],
                                  "maille": "commune", "source_ref": FRR_MILLESIME, "lien": FRR_LIEN})})
            n_f += 1
    return {"zfang": n_z, "frr": n_f}


def build_all(session: Session, *, commit: bool = True, log=lambda *_: None) -> dict:
    tva = build_tva_primo(session)
    zf = build_zfang_frr(session)
    qpv = int(session.execute(text("SELECT count(*) FROM spatial_layers WHERE kind='qpv'")).scalar() or 0)
    anru = int(session.execute(text("SELECT count(*) FROM spatial_layers WHERE kind='anru'")).scalar() or 0)
    if commit:
        session.commit()
    out = {"qpv": qpv, "anru": anru, "tva_primo": tva, **zf}
    log(f"dispositifs : QPV {qpv} · ANRU {anru} · TVA(500m) {tva} · ZFANG {zf['zfang']} · FRR {zf['frr']}")
    return out
