"""RADAR V0 · P2 — RATTACHEMENT d'un bien à la parcelle (cascade de matching).

Doctrine §2 : Sourcé / Estimé / Absent. Parcelle unique haute confiance = **Sourcé**. 1 à 3 candidates
= **Estimé** (toutes affichées, avec confiance). Rien de plausible (ou trop d'ambiguïté) = **Non
rattachée**, commune seule. JAMAIS un pin unique faussement sûr — le faux positif est le péché cardinal.

Le rattachement tourne sur des FAITS déjà extraits d'une capture HUMAINE (aucune requête portail ici).
Le géocodage d'adresse (BAN, api-adresse.data.gouv.fr) n'est PAS un portail — il est injecté
(`geocode`) pour rester testable hors réseau.
"""
from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import text
from sqlalchemy.orm import Session

# 1-3 candidates = Estimé ; au-delà = trop ambigu → Non rattachée (mieux vaut la commune qu'un faux pin).
MAX_CANDIDATES_ESTIME = 3


def _parcelle_contenante(db: Session, lon: float, lat: float, commune: str) -> str | None:
    return db.execute(text(
        "SELECT idu FROM parcels WHERE commune = :c "
        "AND ST_Contains(geom, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)) LIMIT 1"),
        {"c": commune, "lon": lon, "lat": lat}).scalar()


def _cand_dpe(db: Session, commune_insee: str, surface_hab: float | None,
              dpe_classe: str | None) -> list[str]:
    """Croisement DPE ADEME (déjà ingéré) : classe + surface + commune → parcelle probable.
    Anti-invention : le DPE ingéré ne porte PAS la consommation (colonnes réelles = etiquette_dpe /
    surface_habitable) → on ne filtre QUE sur ce qui existe, jamais sur un champ absent."""
    if not commune_insee or (surface_hab is None and dpe_classe is None):
        return []
    rows = db.execute(text(
        """SELECT DISTINCT parcelle_idu FROM dpe_records
           WHERE code_insee = :insee AND parcelle_idu IS NOT NULL
             AND (CAST(:cls AS text) IS NULL OR etiquette_dpe = :cls)
             AND (CAST(:sh AS numeric) IS NULL OR abs(surface_habitable - :sh) <= greatest(8, 0.05 * :sh))
           LIMIT 10"""),
        {"insee": commune_insee, "cls": dpe_classe, "sh": surface_hab}
    ).scalars().all()
    return [r for r in rows if r]


def _cand_morphologie(db: Session, commune: str, surface_hab: float | None,
                      surface_terrain: float | None, piscine: bool | None) -> list[str]:
    """FLAIR morpho : emprise bâtie (p_model_bati) + piscine (parcel_equipements) + surface terrain
    (aire parcelle) → candidates plausibles de la commune. Signal faible → sert d'ESTIMÉ, jamais Sourcé."""
    if surface_hab is None and surface_terrain is None and not piscine:
        return []
    conds, params = ["p.commune = :c"], {"c": commune}
    joins = ""
    if surface_hab is not None:
        joins += " JOIN p_model_bati b ON b.idu = p.idu"
        conds.append("abs(b.emprise_bati_m2 - :sh) <= greatest(15, 0.15 * :sh)")
        params["sh"] = surface_hab
    if surface_terrain is not None:
        conds.append("abs(ST_Area(p.geom_2975) - :st) <= greatest(50, 0.05 * :st)")
        params["st"] = surface_terrain
    if piscine:
        joins += " JOIN parcel_equipements e ON e.idu = p.idu AND e.piscine = true"
    rows = db.execute(text(
        f"SELECT p.idu FROM parcels p{joins} WHERE {' AND '.join(conds)} LIMIT 10"), params
    ).scalars().all()
    return list(rows)


def rattacher(db: Session, *, commune: str, commune_insee: str | None = None,
              lon: float | None = None, lat: float | None = None, adresse: str | None = None,
              surface_hab: float | None = None, surface_terrain: float | None = None,
              dpe_classe: str | None = None, dpe_conso: int | None = None,
              piscine: bool | None = None,
              geocode: Callable[[str], dict | None] | None = None) -> dict:
    """Cascade GPS → BAN → DPE → morphologie. Retourne
    {niveau: source|estime|absent, idu, confiance, candidates:[{idu,confiance,etage}], etage}."""
    def sourcee(idu: str, conf: float, etage: str) -> dict:
        return {"niveau": "source", "idu": idu, "confiance": conf, "etage": etage,
                "candidates": [{"idu": idu, "confiance": conf, "etage": etage}]}

    # 1) GPS — localisation exploitable sur la vignette → parcelle contenante = haute confiance.
    if lon is not None and lat is not None:
        idu = _parcelle_contenante(db, lon, lat, commune)
        if idu:
            return sourcee(idu, 0.95, "gps")

    # 2) BAN — adresse/lieu-dit lisible → géocodage → parcelle contenante (géocodeur injecté).
    if adresse and geocode:
        g = geocode(adresse)
        if g and g.get("lon") is not None and g.get("lat") is not None:
            idu = _parcelle_contenante(db, g["lon"], g["lat"], commune)
            if idu:
                conf = 0.90 if (g.get("score") or 0) >= 0.8 else 0.75
                return sourcee(idu, conf, "ban")

    # 3) DPE + 4) morphologie — signaux de CANDIDATURE (jamais Sourcé) → Estimé si 1-3, sinon Absent.
    cands: dict[str, dict] = {}
    # dpe_conso accepté (champ de pige_faits) mais NON utilisé au croisement : le DPE ingéré ne le porte
    # pas → on ne devine pas. Il reste un fait affiché, pas un critère de matching.
    _ = dpe_conso
    for idu in _cand_dpe(db, commune_insee or "", surface_hab, dpe_classe):
        cands.setdefault(idu, {"idu": idu, "confiance": 0.55, "etage": "dpe"})
    for idu in _cand_morphologie(db, commune, surface_hab, surface_terrain, piscine):
        if idu in cands:
            cands[idu]["confiance"] = 0.65   # confirmé par deux étages
            cands[idu]["etage"] = "dpe+morpho"
        else:
            cands.setdefault(idu, {"idu": idu, "confiance": 0.40, "etage": "morpho"})

    liste = sorted(cands.values(), key=lambda c: -c["confiance"])
    if 1 <= len(liste) <= MAX_CANDIDATES_ESTIME:
        return {"niveau": "estime", "idu": None, "confiance": liste[0]["confiance"],
                "etage": liste[0]["etage"], "candidates": liste}
    # 0 candidate, ou trop (> 3) = ambiguïté : on ne pose PAS de pin. Commune seule.
    return {"niveau": "absent", "idu": None, "confiance": None, "etage": None,
            "candidates": [], "trop_ambigu": len(liste) > MAX_CANDIDATES_ESTIME}
