"""Lot 2 — Droits résiduels sur PARCELLES BÂTIES (le calcul nouveau du mandat).

Recycle le moteur de règles PLU (faisabilite/plu_rules.resolve_zone : YAML calibrés
Saint-Paul « strict » / Saint-Denis « progressif », estimation générique ailleurs)
sur le parc DÉJÀ BÂTI :

  - emprise_max_m2        = surface parcelle × coefficient d'emprise du zonage
                            (emprise_sol_pct) ; NULL si aucune règle d'emprise
                            exploitable pour la commune/zone ;
  - emprise_residuelle_m2 = max(0, emprise_max_m2 − emprise bâtie BD TOPO) ;
  - surelevation_possible = hauteur max du zonage − hauteur bâtiment BD TOPO ≥ 2,8 m ;
  - confiance             = 'haute' (règle calibrée YAML PLU communal) |
                            'moyenne' (estimation générique / hauteur prospect
                            plancher / renvoi partiel).

NE TOUCHE PAS à la table `parcel_residuel` existante (SDP promoteur, clé parcel_id,
recalculée par le run) : table dédiée `parcel_residuel_bati` (clé idu), consommée par
les filtres jardin/emprise/résiduel/surélévation du moteur de segments.

LIBELLÉ UI IMPÉRATIF (repris par le front et les exports) : « potentiel indicatif
estimé — les règles complètes du PLU (retraits, prospects, servitudes) peuvent le
réduire ». C'est un signal de prospection, pas une étude de faisabilité.
"""
from __future__ import annotations

import logging

from sqlalchemy import text

from ..faisabilite.plu_rules import resolve_zone

log = logging.getLogger(__name__)

LIBELLE_UI = ("potentiel indicatif estimé — les règles complètes du PLU "
              "(retraits, prospects, servitudes) peuvent le réduire")

SURELEVATION_MARGE_M = 2.8      # un niveau habitable (mandat)
EMPRISE_BATIE_MIN_M2 = 5.0      # en deçà : cabanon/artefact, parcelle traitée non bâtie
PROSPECT_HAUTEUR_PLANCHER_M = 10.0   # zones « prospect » (L≥H) : plancher règlement (prudent)

DDL = """
CREATE TABLE IF NOT EXISTS parcel_residuel_bati (
  idu varchar(14) PRIMARY KEY,
  commune varchar(80),
  zone varchar(40),
  emprise_batie_m2 double precision,
  hauteur_bati_m double precision,
  emprise_max_m2 double precision,
  emprise_residuelle_m2 double precision,
  hauteur_max_m double precision,
  surelevation_possible boolean,
  confiance varchar(10),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_prb_residuel ON parcel_residuel_bati (emprise_residuelle_m2);
CREATE INDEX IF NOT EXISTS ix_prb_surelevation ON parcel_residuel_bati (surelevation_possible)
"""

# Une passe SQL par commune : emprise bâtie + hauteur BD TOPO + zone PLU (centroïde),
# pour les parcelles RÉELLEMENT bâties. Set-based (aucun aller-retour par parcelle).
_SCAN = text("""
SELECT p.idu, p.commune, p.surface_m2,
       b.emprise AS emprise_batie_m2, b.hauteur AS hauteur_bati_m,
       (SELECT COALESCE(z.attrs->>'libelle', z.subtype, z.name)
          FROM spatial_layers z
         WHERE z.commune = p.commune AND z.kind = 'plu_gpu_zone'
           AND ST_Contains(z.geom, p.centroid)
         ORDER BY ST_Area(z.geom) ASC LIMIT 1) AS zone
FROM parcels p
JOIN LATERAL (
  SELECT COALESCE(sum(ST_Area(ST_Intersection(sl.geom_2975, p.geom_2975))), 0) AS emprise,
         max(NULLIF(sl.attrs->>'hauteur', '')::float) AS hauteur
  FROM spatial_layers sl
  WHERE sl.kind = 'batiment' AND ST_Intersects(sl.geom_2975, p.geom_2975)
) b ON true
WHERE p.commune = :c AND p.surface_m2 >= 2 AND b.emprise >= :emin
""")

_UPSERT = text("""
INSERT INTO parcel_residuel_bati (idu, commune, zone, emprise_batie_m2, hauteur_bati_m,
                                  emprise_max_m2, emprise_residuelle_m2, hauteur_max_m,
                                  surelevation_possible, confiance, updated_at)
VALUES (:idu, :commune, :zone, :eb, :hb, :emax, :eres, :hmax, :sur, :conf, now())
ON CONFLICT (idu) DO UPDATE SET
  commune = EXCLUDED.commune, zone = EXCLUDED.zone,
  emprise_batie_m2 = EXCLUDED.emprise_batie_m2, hauteur_bati_m = EXCLUDED.hauteur_bati_m,
  emprise_max_m2 = EXCLUDED.emprise_max_m2,
  emprise_residuelle_m2 = EXCLUDED.emprise_residuelle_m2,
  hauteur_max_m = EXCLUDED.hauteur_max_m,
  surelevation_possible = EXCLUDED.surelevation_possible,
  confiance = EXCLUDED.confiance, updated_at = now()
""")


def ensure_tables(engine) -> None:
    with engine.begin() as c:
        for stmt in DDL.split(";"):
            if stmt.strip():
                c.execute(text(stmt))


def _num(v) -> float | None:
    return float(v) if isinstance(v, (int, float)) else None


def _regles(zone: str | None, commune: str) -> dict:
    """Règles d'emprise/hauteur d'une zone via le moteur PLU existant.

    {emprise_pct, hauteur_m, constructible, approx} — `approx=True` quand une valeur
    vient d'une règle CONNEXE ou d'une estimation (→ confiance 'moyenne') :
      - emprise non réglementée (Art. 9 « pas de règle », ex. Saint-Paul) mais pleine
        terre chiffrée (Art. 13) → coefficient = 100 − pleine_terre (borne supérieure) ;
      - hauteur 'prospect' (L≥H par parcelle) → plancher règlement 10 m ;
      - zone hors YAML calibré → estimation générique du moteur (calibree=False).
    Les marqueurs 'a_verifier' ne sont JAMAIS comblés (→ None)."""
    out = {"emprise_pct": None, "hauteur_m": None, "constructible": False, "approx": False}
    if not zone:
        return out
    try:
        r = resolve_zone(zone, commune)
    except Exception:  # noqa: BLE001 — YAML communal malformé → règle indisponible
        return out
    if r is None or not r.constructible_neuf:
        return out
    out["constructible"] = True
    out["approx"] = not r.calibree
    out["emprise_pct"] = _num(r.emprise_sol_pct)
    if out["emprise_pct"] is None:
        pleine_terre = _num(r.pleine_terre_pct)
        if pleine_terre is not None:
            out["emprise_pct"] = max(0.0, 100.0 - pleine_terre)
            out["approx"] = True
    out["hauteur_m"] = _num(r.hf_m) or _num(r.he_m)
    if out["hauteur_m"] is None and r.hauteur_mode == "prospect":
        out["hauteur_m"] = PROSPECT_HAUTEUR_PLANCHER_M
        out["approx"] = True
    return out


def compute_commune(session, commune: str, *, batch: int = 2000) -> dict:
    """Calcule/rafraîchit les droits résiduels des parcelles bâties d'une commune."""
    rows = session.execute(_SCAN, {"c": commune, "emin": EMPRISE_BATIE_MIN_M2}).mappings().all()
    zone_cache: dict[str, dict] = {}
    payload: list[dict] = []
    for r in rows:
        zone = (r["zone"] or "").strip() or None
        key = zone or "∅"
        if key not in zone_cache:
            zone_cache[key] = _regles(zone, commune)
        rg = zone_cache[key]
        emprise_pct, hauteur_max = rg["emprise_pct"], rg["hauteur_m"]

        surface = float(r["surface_m2"] or 0.0)
        eb = float(r["emprise_batie_m2"] or 0.0)
        hb = float(r["hauteur_bati_m"]) if r["hauteur_bati_m"] is not None else None

        emax = round(surface * emprise_pct / 100.0, 1) if (rg["constructible"] and emprise_pct) else None
        eres = round(max(0.0, emax - eb), 1) if emax is not None else None
        sur = None
        if rg["constructible"] and hauteur_max is not None and hb is not None:
            sur = (hauteur_max - hb) >= SURELEVATION_MARGE_M

        # confiance : 'haute' = règle directe d'un YAML PLU calibré ; 'moyenne' = règle
        # connexe (pleine terre), plancher prospect ou estimation générique ; NULL =
        # aucune règle exploitable (emprise ET surélévation indéfinies).
        conf = None
        if eres is not None or sur is not None:
            conf = "moyenne" if rg["approx"] else "haute"

        payload.append({"idu": r["idu"], "commune": commune, "zone": zone,
                        "eb": round(eb, 1), "hb": hb, "emax": emax, "eres": eres,
                        "hmax": hauteur_max, "sur": sur, "conf": conf})
    for i in range(0, len(payload), batch):
        session.execute(_UPSERT, payload[i:i + batch])
    session.flush()
    n_regles = sum(1 for p in payload if p["conf"] is not None)
    log.info("residuel_bati %s : %s parcelles bâties, %s avec règle exploitable",
             commune, len(payload), n_regles)
    return {"commune": commune, "baties": len(payload), "avec_regle": n_regles}
