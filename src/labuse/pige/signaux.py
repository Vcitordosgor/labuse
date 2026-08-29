"""RADAR-HTML (Lot 4) — SIGNAUX CROISÉS commune/zone. Ce qu'aucune pige concurrente ne produit, parce
que ça sort de NOTRE référentiel calibré. Ils fonctionnent AU NIVEAU COMMUNE/ZONE → ils ne dépendent
PAS du rattachement parcellaire (rare, cf. Lot 0).

DOCTRINE : un signal est un ÉCART CONSTATÉ entre DEUX SOURCES DATÉES (le prix AFFICHÉ du Radar,
Sourcé portail ; le prix ACTÉ DVF, Sourcé cadastre), JAMAIS une estimation de valeur ni une
prévision. Aucun verdict. Chaque côté porte son millésime et son n ; sous SEUIL_N, on ne sert pas.

Trois usages :
  1. « prix affiché vs référentiel de zone » — par annonce (terrain) et par commune ;
  2. « écart demandé / acté » par commune — médiane Radar (demandé) vs médiane DVF (acté) ;
  3. alimentation de l'Étude de zone (« annonces actives ») et de Communes (onglet Marché).
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

SEUIL_N = 5   # même honnêteté statistique que l'onglet Marché : sous 5, pas de médiane servie


def _radar_medianes(db: Session, commune: str) -> dict:
    """Médianes des prix AFFICHÉS du Radar (demandé) pour une commune : terrain €/m² et bâti €/m².
    Exclut les annonces à qualifier et les non validées — jamais un fait faux dans une stat."""
    r = db.execute(text("""
        SELECT
          percentile_cont(0.5) WITHIN GROUP (ORDER BY f.prix / f.surface_terrain)
            FILTER (WHERE b.type_bien = 'terrain' AND f.prix IS NOT NULL AND f.surface_terrain > 0) AS med_terrain,
          count(*) FILTER (WHERE b.type_bien = 'terrain' AND f.prix IS NOT NULL AND f.surface_terrain > 0) AS n_terrain,
          percentile_cont(0.5) WITHIN GROUP (ORDER BY f.prix / f.surface_hab)
            FILTER (WHERE b.type_bien IN ('maison','appartement','immeuble') AND f.prix IS NOT NULL AND f.surface_hab > 0) AS med_bati,
          count(*) FILTER (WHERE b.type_bien IN ('maison','appartement','immeuble') AND f.prix IS NOT NULL AND f.surface_hab > 0) AS n_bati,
          count(*) FILTER (WHERE b.statut = 'active') AS actives
        FROM pige_biens b JOIN pige_faits f ON f.bien_id = b.bien_id
        WHERE f.valide_at IS NOT NULL AND b.a_qualifier = false
          AND b.statut IN ('active','en_vente_longue') AND b.commune = :c"""),
        {"c": commune}).mappings().first() or {}
    return dict(r)


def _dvf_terrain(db: Session, commune: str) -> dict:
    """DVF acté terrain nu (référentiel UNIQUE) — médiane commune = zone U de préférence sinon AU."""
    try:
        from ..faisabilite.marche_commune import ligne2_terrain_zone
        l = ligne2_terrain_zone(db, commune)
    except Exception:  # noqa: BLE001
        return {"eur_m2": None, "n": 0, "millesime": None}
    par_zone = ((l.get("valeurs") or {}).get("par_zone")) or {}
    for fam in ("U", "AU"):
        cell = par_zone.get(fam) or {}
        if cell.get("calculable") and cell.get("median_eur_m2"):
            return {"eur_m2": float(cell["median_eur_m2"]), "n": int(cell.get("n") or 0),
                    "millesime": l.get("date_amont"), "zone": fam}
    return {"eur_m2": None, "n": 0, "millesime": l.get("date_amont")}


def _dvf_bati(db: Session, commune: str) -> dict:
    """DVF acté bâti ancien (référentiel UNIQUE `ligne1_prix_ancien` / sector_price)."""
    try:
        from ..faisabilite.marche_commune import ligne1_prix_ancien
        l = ligne1_prix_ancien(db, commune)
    except Exception:  # noqa: BLE001
        return {"eur_m2": None, "n": 0, "millesime": None}
    v = l.get("valeurs") or {}
    if v.get("median_eur_m2"):
        return {"eur_m2": float(v["median_eur_m2"]), "n": int(v.get("n") or 0),
                "millesime": l.get("date_amont")}
    return {"eur_m2": None, "n": 0, "millesime": l.get("date_amont")}


def _ecart(demande: float | None, n_dem: int, acte: dict) -> dict | None:
    """Un écart CONSTATÉ demandé/acté, servi seulement si les DEUX côtés tiennent le seuil. Porte les
    deux valeurs, les deux n, le millésime DVF, et le signe (« au-dessus »/« sous le marché »)."""
    acte_v, n_acte = acte.get("eur_m2"), int(acte.get("n") or 0)
    if demande is None or acte_v is None or n_dem < SEUIL_N or n_acte < SEUIL_N:
        return {"calculable": False, "demande_eur_m2": round(demande) if demande else None,
                "n_demande": n_dem, "acte_eur_m2": round(acte_v) if acte_v else None,
                "n_acte": n_acte, "millesime_dvf": acte.get("millesime"),
                "motif": "échantillon insuffisant d'un des deux côtés (< 5)"}
    ecart_pct = round(100.0 * (demande - acte_v) / acte_v, 1)
    return {"calculable": True, "demande_eur_m2": round(demande), "n_demande": n_dem,
            "acte_eur_m2": round(acte_v), "n_acte": n_acte, "millesime_dvf": acte.get("millesime"),
            "ecart_pct": ecart_pct,
            "sens": "au-dessus du marché acté" if ecart_pct > 0 else "sous le marché acté"}


def ecart_demande_acte(db: Session, commune: str) -> dict:
    """SIGNAL #2 — médiane des prix AFFICHÉS du Radar (demandé) contre médiane DVF (acté), par commune.
    C'est la marge de négociation du moment. Terrain ET bâti, chacun avec ses deux millésimes/n."""
    radar = _radar_medianes(db, commune)
    return {
        "commune": commune,
        "terrain": _ecart(radar.get("med_terrain"), int(radar.get("n_terrain") or 0), _dvf_terrain(db, commune)),
        "bati": _ecart(radar.get("med_bati"), int(radar.get("n_bati") or 0), _dvf_bati(db, commune)),
    }


def annonce_vs_referentiel(db: Session, bien_id: int) -> dict | None:
    """SIGNAL #1 (par annonce) — pour un TERRAIN, prix affiché €/m² vs terrain nu de la commune. Écart
    constaté, Sourcé des deux côtés, avec les deux millésimes. None si non applicable/non calculable."""
    row = db.execute(text(
        "SELECT b.commune, b.type_bien, f.prix, f.surface_terrain, b.a_qualifier "
        "FROM pige_biens b JOIN pige_faits f ON f.bien_id = b.bien_id WHERE b.bien_id = :b"),
        {"b": bien_id}).mappings().first()
    if not row or row["type_bien"] != "terrain" or row["a_qualifier"]:
        return None
    if not row["prix"] or not row["surface_terrain"] or float(row["surface_terrain"]) <= 0:
        return None
    affiche = float(row["prix"]) / float(row["surface_terrain"])
    dvf = _dvf_terrain(db, row["commune"])
    if not dvf.get("eur_m2"):
        return {"calculable": False, "affiche_eur_m2": round(affiche),
                "motif": "pas de référentiel terrain nu calculable pour la commune"}
    ecart_pct = round(100.0 * (affiche - dvf["eur_m2"]) / dvf["eur_m2"], 1)
    return {"calculable": True, "affiche_eur_m2": round(affiche),
            "referentiel_eur_m2": round(dvf["eur_m2"]), "n_referentiel": dvf["n"],
            "millesime_dvf": dvf.get("millesime"), "zone": dvf.get("zone"),
            "ecart_pct": ecart_pct,
            "sens": "au-dessus du terrain nu" if ecart_pct > 0 else "sous le terrain nu"}


def annonces_actives_zone(db: Session, commune: str) -> dict:
    """SIGNAL #3 — alimente l'Étude de zone (case « annonces actives ») et Communes (onglet Marché) :
    nombre d'annonces Radar actives + médiane affichée. À qualifier et non validées exclues."""
    r = _radar_medianes(db, commune)
    n_terr = int(r.get("n_terrain") or 0)
    n_bati = int(r.get("n_bati") or 0)
    return {
        "commune": commune,
        "actives": int(r.get("actives") or 0),
        "prix_m2_terrain": {"valeur": round(float(r["med_terrain"])) if r.get("med_terrain") and n_terr >= SEUIL_N else None,
                            "n": n_terr, "insuffisant": n_terr < SEUIL_N},
        "prix_m2_bati": {"valeur": round(float(r["med_bati"])) if r.get("med_bati") and n_bati >= SEUIL_N else None,
                        "n": n_bati, "insuffisant": n_bati < SEUIL_N},
        "ecart_demande_acte": ecart_demande_acte(db, commune),
    }
