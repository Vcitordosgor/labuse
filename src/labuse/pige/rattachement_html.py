"""RADAR-HTML (Lot 3) — RATTACHEMENT à la parcelle, calé sur la MESURE du Lot 0 (voir MANDAT-PIGE-V0).

TROIS ÉTATS, jamais deux :
  · RATTACHÉE       — une seule candidate CORROBORÉE, ou source=address tombant dans une parcelle
                      cohérente. Seul cet état alimente le rapprochement DVF et peut nourrir le Courrier.
  · PISTE           — plusieurs candidates (ou une candidate non corroborée). S'affiche AVEC son
                      nombre ; AUCUN automatisme n'en part (ni courrier, ni « vendue », ni stat parcellaire).
  · NON RATTACHÉE   — appartement en copropriété, ou aucun critère (pas de coordonnée exploitable /
                      pas de surface de terrain). La position servie est le QUARTIER, et c'est DIT.

Ce que le Lot 0 a mesuré et que ce code respecte :
  · le floutage `city` est un jitter PAR ANNONCE (exploitable), mais dépasse souvent 150 m → au-delà
    d'un rayon serré l'unicité s'effondre : RAYON = 150 m, surface ±5 % ;
  · `source=address` est du STREET-LEVEL HERE, pas du rooftop : le point tombe dans UNE parcelle mais
    pas toujours la bonne → on exige la cohérence de surface avant de conclure RATTACHÉE ;
  · « une candidate unique n'est pas un rattachement juste » (M4) → corroboration par le bâti pour un
    bâti (maison/immeuble sur parcelle sans emprise = PISTE, pas RATTACHÉE). Doctrine : jamais un fait
    faux servi.

Aucun appel réseau (doctrine §2) : on ne lit QUE le parcellaire déjà en base.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

RAYON_M = 150            # rayon serré (Lot 0 : au-delà, l'unicité s'effondre)
TOL_SURFACE = 0.05       # ±5 % sur land_plot_surface vs surface cadastrale
BATI_MIN_M2 = 10         # emprise bâtie minimale pour corroborer un bâti (maison/immeuble)
MAX_PISTES = 8           # au-delà, trop ambigu même comme piste → NON RATTACHÉE

_TYPES_RATTACHABLES = ("maison", "terrain", "immeuble")


def _non_rattachee(motif: str) -> dict:
    return {"etat": "non_rattachee", "niveau": "absent", "idu": None, "confiance": None,
            "pistes": [], "motif": motif}


def _rattachee(idu: str, conf: float, etage: str) -> dict:
    return {"etat": "rattachee", "niveau": "source", "idu": idu, "confiance": conf,
            "pistes": [{"idu": idu}], "etage": etage}


def _piste(cands: list[dict], etage: str) -> dict:
    return {"etat": "piste", "niveau": "estime", "idu": None,
            "confiance": cands[0].get("confiance") if cands else None,
            "pistes": cands, "etage": etage}


def _parcelle_contenante(db: Session, lon: float, lat: float, commune: str) -> dict | None:
    return db.execute(text(
        """SELECT p.idu, p.surface_m2, COALESCE(b.emprise_bati_m2, 0) AS bati
           FROM parcels p LEFT JOIN p_model_bati b ON b.idu = p.idu
           WHERE p.commune = :c
             AND ST_Contains(p.geom, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)) LIMIT 1"""),
        {"c": commune, "lon": lon, "lat": lat}).mappings().first()


def _candidates_surface(db: Session, lon: float, lat: float, commune: str, terrain: float) -> list[dict]:
    """Parcelles de la commune, dans RAYON_M du point (flouté), dont la surface cadastrale matche la
    surface de terrain déclarée à ±5 %. Portent leur distance, leur écart de surface et leur bâti."""
    lo, hi = terrain * (1 - TOL_SURFACE), terrain * (1 + TOL_SURFACE)
    rows = db.execute(text(
        """SELECT p.idu, p.surface_m2, COALESCE(b.emprise_bati_m2, 0) AS bati,
                  ST_Distance(p.geom_2975,
                     ST_Transform(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), 2975)) AS d
           FROM parcels p LEFT JOIN p_model_bati b ON b.idu = p.idu
           WHERE p.commune = :c AND p.surface_m2 BETWEEN :lo AND :hi
             AND ST_DWithin(p.geom_2975,
                    ST_Transform(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), 2975), :ray)
           ORDER BY d LIMIT 20"""),
        {"c": commune, "lo": lo, "hi": hi, "lon": lon, "lat": lat, "ray": RAYON_M}).mappings().all()
    out = []
    for r in rows:
        ecart = abs(float(r["surface_m2"]) - terrain) / terrain if terrain else None
        out.append({"idu": r["idu"], "surface_m2": round(float(r["surface_m2"]), 1),
                    "distance_m": round(float(r["d"]), 1), "bati_m2": round(float(r["bati"]), 1),
                    "surface_ecart_pct": round(ecart * 100, 1) if ecart is not None else None})
    return out


def _bati_coherent(typ: str, bati: float | None) -> bool:
    """Corroboration de TYPE : un bâti (maison/immeuble) attend une emprise bâtie ; un terrain n'a pas
    d'exigence (un terrain nu candidat est légitime — un « terrain » réellement bâti est déjà écarté
    « à qualifier » par le Lot 2 et ne sera pas servi)."""
    if typ in ("maison", "immeuble"):
        return (bati or 0) >= BATI_MIN_M2
    return True


def rattacher(db: Session, rec: dict) -> dict:
    """Cascade de rattachement sur un enregistrement aplati (`html_next.aplatir`). Retourne
    {etat, niveau, idu, confiance, pistes:[…], motif?}. Ne lève jamais (un défaut = NON RATTACHÉE)."""
    typ = rec.get("type")
    if rec.get("type") == "appartement" or rec.get("est_copro"):
        return _non_rattachee("appartement en copropriété — position = quartier")
    if typ not in _TYPES_RATTACHABLES:
        return _non_rattachee(f"type « {typ or '?'} » non rattachable — position = quartier")
    lon, lat = rec.get("lng"), rec.get("lat")
    commune = rec.get("commune")
    if lon is None or lat is None or not commune:
        return _non_rattachee("aucune coordonnée exploitable — position = quartier")
    terrain = rec.get("surface_terrain")

    # 1) source=address — point-dans-parcelle, MAIS street-level : on exige la cohérence de surface.
    if rec.get("source_position") == "address":
        cont = _parcelle_contenante(db, lon, lat, commune)
        if cont:
            if terrain:
                ecart = abs(float(cont["surface_m2"]) - float(terrain)) / float(terrain)
                if ecart <= TOL_SURFACE and _bati_coherent(typ, cont["bati"]):
                    return _rattachee(cont["idu"], 0.92, "address+surface")
                # point dans une parcelle mais surface incohérente → candidate, pas certitude.
                cands = _candidates_surface(db, lon, lat, commune, float(terrain))
                idus = {c["idu"] for c in cands}
                if cont["idu"] not in idus:
                    cands = [{"idu": cont["idu"], "surface_m2": round(float(cont["surface_m2"]), 1),
                              "distance_m": 0.0, "bati_m2": round(float(cont["bati"]), 1),
                              "surface_ecart_pct": round(ecart * 100, 1), "confiance": 0.5}] + cands
                if cands:
                    return _piste(cands, "address+piste")
                return _non_rattachee("point address dans parcelle mais surface incohérente, aucune "
                                      "alternative — quartier retenu")
            # pas de surface de terrain (souvent appartement/maison de ville) : point-dans-parcelle
            # seul. Corroboration bâti pour un bâti ; sinon la position reste address sans parcelle sûre.
            if _bati_coherent(typ, cont["bati"]):
                return _rattachee(cont["idu"], 0.80, "address")
            return _non_rattachee("point address dans une parcelle sans bâti — bâti attendu, quartier retenu")
        # address hors de toute parcelle (voirie) → on bascule sur la recherche par surface.

    # 2) source=city (ou address hors parcelle) — rayon serré + surface ±5 %.
    if not terrain:
        return _non_rattachee("pas de surface de terrain pour une recherche par surface — quartier retenu")
    cands = _candidates_surface(db, lon, lat, commune, float(terrain))
    if not cands:
        return _non_rattachee("aucune parcelle de surface compatible dans le rayon — quartier retenu")
    if len(cands) == 1:
        c = cands[0]
        if _bati_coherent(typ, c["bati_m2"]):
            return _rattachee(c["idu"], 0.72, "city+unique")
        # candidate unique mais NON corroborée (maison sur parcelle sans bâti — cf. faux positif M4).
        c["confiance"] = 0.5
        return _piste(cands, "city+unique_non_corroboree")
    if len(cands) <= MAX_PISTES:
        return _piste(cands, "city+pistes")
    return _non_rattachee(f"{len(cands)} candidates de surface compatible — trop ambigu, quartier retenu")
