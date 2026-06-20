"""Ingestion des autorisations d'urbanisme (permis/SITADEL) — Région ODS 974  [✓ live].

Le dataset ODS « liste des permis de construire… » porte les références cadastrales
(sec_cadastre / num_cadastre) : on reconstruit l'IDU 14 caractères et on géolocalise
par jointure à parcels (centroïde). Alimente sitadel_permits → signal de veille
new_permit_nearby (§7bis : rattachement IDU vs proximité).
"""
from __future__ import annotations

import json

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import constants
from ..config import get_settings

ODS = "https://data.regionreunion.com/api/explore/v2.1/catalog/datasets"
PERMIS_DS = "liste-des-permis-de-construire-et-autres-autorisations-d-urbanisme-a-la-reunion"


def _idu(insee: str, sec, num) -> str | None:
    if not sec or num in (None, ""):
        return None
    return f"{insee}000{str(sec).strip().upper().zfill(2)}{str(num).strip().zfill(4)}"


def ingest_permits(session: Session, insee: str, commune: str, run_id: int | None = None,
                   *, page: int = 100, cap: int = 10000) -> int:
    """Télécharge les permis de la commune (ODS) et les ingère, géolocalisés par IDU."""
    # 1.B : on capte aussi la NATURE (logements/surface/destination) et le STATUT (achèvement).
    sel = ("type_dau,num_dau,date_reelle_autorisation,date_reelle_daact,etat_dau,"
           "nb_lgt_tot_crees,surf_hab_creee,destination_principale,"
           "sec_cadastre1,num_cadastre1,sec_cadastre2,num_cadastre2,sec_cadastre3,num_cadastre3")
    recs: list[dict] = []
    with httpx.Client(timeout=max(get_settings().http_timeout_s, 60.0),
                      headers={"User-Agent": constants.USER_AGENT}, follow_redirects=True) as c:
        off = 0
        while off < cap:
            r = c.get(f"{ODS}/{PERMIS_DS}/records",
                      params={"where": f'comm="{insee}"', "limit": page, "offset": off, "select": sel})
            r.raise_for_status()
            res = r.json().get("results", []) or []
            recs.extend(res)
            if len(res) < page:
                break
            off += page
    n = 0
    for rec in recs:
        idus = []
        for si, ni in (("sec_cadastre1", "num_cadastre1"), ("sec_cadastre2", "num_cadastre2"),
                       ("sec_cadastre3", "num_cadastre3")):
            idu = _idu(insee, rec.get(si), rec.get(ni))
            if idu:
                idus.append(idu)
        if not idus:
            continue
        session.execute(
            text(
                """INSERT INTO sitadel_permits (permit_id, type, date, idu_codes, commune, geom, raw)
                   SELECT :pid, :typ, :dt, CAST(:idus AS jsonb), :c,
                          (SELECT centroid FROM parcels WHERE idu = ANY(:idu_arr) LIMIT 1),
                          CAST(:raw AS jsonb)"""
            ),
            {"pid": rec.get("num_dau"), "typ": rec.get("type_dau"), "dt": rec.get("date_reelle_autorisation"),
             "idus": json.dumps(idus), "idu_arr": idus, "c": commune,
             "raw": json.dumps({"src": "Région ODS — permis 974",
                                "nb_lgt": rec.get("nb_lgt_tot_crees"),
                                "surf_hab": rec.get("surf_hab_creee"),
                                "destination": rec.get("destination_principale"),
                                "daact": rec.get("date_reelle_daact"),
                                "etat": rec.get("etat_dau")})},
        )
        n += 1
    session.flush()
    return n


_TYPE_LABEL = {"PC": "Permis de construire", "PA": "Permis d'aménager",
               "DP": "Déclaration préalable", "PD": "Permis de démolir"}


def _nature(raw: dict | None) -> str:
    """Nature lisible d'un permis depuis le raw ODS (nb logements / surface habitable)."""
    raw = raw or {}
    nb = raw.get("nb_lgt")
    surf = raw.get("surf_hab")
    bits = []
    if nb not in (None, "", 0, "0"):
        try:
            n = int(float(nb))
            if n > 0:
                bits.append(f"{n} logement" + ("s" if n > 1 else ""))
        except (TypeError, ValueError):
            pass
    if surf not in (None, "", 0, "0"):
        try:
            s = int(float(surf))
            if s > 0:
                bits.append(f"~{s} m² hab.")
        except (TypeError, ValueError):
            pass
    return " · ".join(bits) or "projet (non résidentiel ou non précisé)"


def _statut(raw: dict | None, date) -> str:
    """Statut : ces flux ne contiennent que des AUTORISATIONS (jamais de refus inventé)."""
    raw = raw or {}
    d = date.date().isoformat() if date else "—"
    return f"autorisé le {d}" + (" · travaux achevés" if raw.get("daact") else "")


def geocode_permits_via_cadastre(session, insee: str | None = None) -> dict:
    """1.B-fix-a — géolocalise les permis NON géocodés via le cadastre (API Carto), PAR SECTION.

    Les permis référencent ~2 663 parcelles cadastrales, dont peu sont dans notre référentiel bbox.
    Plutôt que d'ingérer tout le cadastre, on récupère par SECTION (84 appels) les centroïdes des
    parcelles cadastrales référencées et on pose le geom des permis. N'ingère AUCUNE parcelle
    (baseline préservée). Retourne le gain (avant/après)."""
    from ..connectors.cadastre import CadastreConnector, parse_parcelles
    insee = insee or get_settings().pilot_commune_insee
    before = session.execute(text("SELECT count(*) FROM sitadel_permits WHERE geom IS NOT NULL")).scalar()
    # sections référencées par des permis encore non géocodés
    sections = [r[0] for r in session.execute(text(
        """SELECT DISTINCT substring(idu FROM 9 FOR 2) AS section
           FROM (SELECT jsonb_array_elements_text(idu_codes) AS idu FROM sitadel_permits
                 WHERE geom IS NULL) q WHERE idu IS NOT NULL""")).all()]
    conn = CadastreConnector()
    lookup: dict[str, str] = {}   # idu -> geometry GeoJSON (str)
    import json as _json
    for sec in sections:
        try:
            fc = conn.fetch_by_section(insee, sec)
        except Exception:  # noqa: BLE001 - une section qui échoue n'arrête pas le lot
            continue
        for p in parse_parcelles(fc):
            if p.get("idu") and p.get("geometry"):
                lookup[p["idu"]] = _json.dumps(p["geometry"])
    # poser le geom (centroïde de la parcelle cadastrale) pour chaque permis non géocodé
    n = 0
    rows = session.execute(text(
        "SELECT id, idu_codes FROM sitadel_permits WHERE geom IS NULL")).all()
    for pid, idus in rows:
        gj = next((lookup[i] for i in (idus or []) if i in lookup), None)
        if not gj:
            continue
        session.execute(text(
            "UPDATE sitadel_permits SET geom = ST_Centroid(ST_SetSRID(ST_GeomFromGeoJSON(:gj),4326)) WHERE id = :id"),
            {"gj": gj, "id": pid})
        n += 1
    session.flush()
    after = session.execute(text("SELECT count(*) FROM sitadel_permits WHERE geom IS NOT NULL")).scalar()
    return {"avant": int(before), "ajoutes": n, "apres": int(after),
            "sections_recuperees": len(sections), "parcelles_cadastre": len(lookup)}


def nearby_permits(session, parcel_id: int, radius_m: float = 300.0, limit: int = 12,
                   dynamique_years: int = 5) -> dict:
    """Historique des autorisations d'urbanisme à proximité (C4 + 1.B) — pour la fiche.

    Permis rattachés (par IDU) + géolocalisés dans le rayon, avec NATURE (logements/surface) et
    STATUT (autorisé/achevé). Plus un indicateur de DYNAMIQUE de secteur (nb d'autorisations
    récentes dans le rayon). Lecture seule."""
    rows = session.execute(
        text(
            """
            WITH p AS (SELECT idu, centroid FROM parcels WHERE id = :pid)
            SELECT s.permit_id, s.type, s.date, s.raw,
                   jsonb_exists(s.idu_codes, p.idu) AS rattache,
                   CASE WHEN s.geom IS NULL THEN NULL
                        ELSE round(ST_Distance(ST_Transform(p.centroid, 2975),
                                               ST_Transform(s.geom, 2975))) END AS dist_m
            FROM sitadel_permits s, p
            WHERE jsonb_exists(s.idu_codes, p.idu)
               OR (s.geom IS NOT NULL
                   AND ST_DWithin(ST_Transform(p.centroid, 2975), ST_Transform(s.geom, 2975), :r))
            ORDER BY rattache DESC, dist_m NULLS LAST
            LIMIT :lim
            """
        ), {"pid": parcel_id, "r": radius_m, "lim": limit},
    ).mappings().all()
    items = [{"num": r["permit_id"], "type": r["type"],
              "type_label": _TYPE_LABEL.get(r["type"], r["type"]),
              "date": r["date"].date().isoformat() if r["date"] else None,
              "rattache": bool(r["rattache"]),
              "distance_m": int(r["dist_m"]) if r["dist_m"] is not None else None,
              "nature": _nature(r["raw"]), "statut": _statut(r["raw"], r["date"])}
             for r in rows]

    # Dynamique de secteur : nb d'autorisations géolocalisées dans le rayon, < N ans + nb logements.
    dyn = session.execute(
        text(
            """WITH p AS (SELECT centroid FROM parcels WHERE id = :pid)
               SELECT count(*) AS n,
                      coalesce(sum(NULLIF(s.raw->>'nb_lgt','')::int), 0) AS logts
               FROM sitadel_permits s, p
               WHERE s.geom IS NOT NULL
                 AND ST_DWithin(ST_Transform(p.centroid,2975), ST_Transform(s.geom,2975), :r)
                 AND (s.date IS NULL OR s.date >= now() - (:yrs || ' years')::interval)"""
        ), {"pid": parcel_id, "r": radius_m, "yrs": dynamique_years},
    ).mappings().first()
    n_recent = int(dyn["n"]) if dyn else 0
    niveau = "actif" if n_recent >= 5 else "modéré" if n_recent >= 1 else "calme"
    rattaches = sum(1 for i in items if i["rattache"])
    # 1.B-fix-b — couverture : part des autorisations de la commune effectivement géolocalisées.
    cov = session.execute(text(
        "SELECT count(*) FILTER (WHERE geom IS NOT NULL) AS g, count(*) AS t FROM sitadel_permits")).mappings().first()
    geoloc, total = (int(cov["g"]), int(cov["t"])) if cov else (0, 0)
    couverture_pct = round(100 * geoloc / total) if total else 0
    return {"radius_m": int(radius_m), "count": len(items), "rattaches": rattaches,
            "items": items, "source": "SITADEL / Région ODS 974",
            "dynamique": {"niveau": niveau, "permis_recents": n_recent,
                          "logements_recents": int(dyn["logts"]) if dyn else 0,
                          "annees": dynamique_years,
                          # couverture : ne jamais lire « calme » sans la qualifier.
                          "couverture_pct": couverture_pct, "geolocalises": geoloc, "total": total,
                          "fiable": couverture_pct >= 60}}
