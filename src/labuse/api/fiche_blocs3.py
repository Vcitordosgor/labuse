"""RETOUCHES-1 lot C (FICHE-3) — six blocs de la fiche parcelle nourris de données DÉJÀ en base,
chacun dans SA section, avec source citée, millésime, et « sans objet » (disponible=False) quand vide.

Aucune donnée nouvelle : Cartofriches (AGORAH/Cerema), loyers OLL, trafic RN, arrêtés CatNat (GASPAR),
acquisitions de personnes morales voisines (DVF × DGFiP), ancienneté de détention (DGFiP / DVF).
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

TMJA_RAYON_M = 300          # « axe le plus proche » : au-delà, la RN n'est plus une nuisance de la parcelle
PM_VOISIN_RAYON_M = 300     # rayon des acquisitions de PM voisines (mandat C.13)
PM_VOISIN_MOIS = 36         # fenêtre 36 mois


def _has(db: Session, *tables: str) -> bool:
    """Toutes les tables/vues existent ? (garde d'ingestion : une table absente ne doit JAMAIS lancer
    une requête qui échoue — elle POISONNERAIT la transaction de la fiche entière → 500. Chaque bloc
    est « sans objet » quand sa source n'est pas ingérée, jamais une erreur.)"""
    return all(db.execute(text("SELECT to_regclass(:t)"), {"t": t}).scalar() is not None
               for t in tables)


# ── C.9 — Cartofriches (§Risques et environnement) ─────────────────────────────────────────────
def cartofriches(db: Session, idu: str) -> dict:
    """La parcelle recoupe-t-elle une friche recensée (AGORAH/Cerema) ? statut, type, surface."""
    if not _has(db, "spatial_layers"):
        return {"disponible": False, "friches": [],
                "source": "Cartofriches (Cerema) / AGORAH", "millesime": "AGORAH 2025"}
    rows = db.execute(text(
        "SELECT sl.attrs->>'site_nom' AS nom, sl.attrs->>'site_statut' AS statut, "
        "       sl.attrs->>'site_type' AS type, sl.attrs#>>'{detail,bati_etat}' AS etat, "
        "       (sl.attrs->>'unite_fonciere_surface')::float AS surface, "
        "       sl.attrs->>'source_nom' AS source "
        "FROM spatial_layers sl JOIN parcels p ON p.idu = :idu "
        "WHERE sl.kind = 'friche' AND ST_Intersects(sl.geom_2975, p.geom_2975)"),
        {"idu": idu}).mappings().all()
    return {
        "disponible": bool(rows),
        "friches": [{"nom": r["nom"], "statut": r["statut"], "type": r["type"], "etat": r["etat"],
                     "surface_m2": round(r["surface"]) if r["surface"] else None} for r in rows],
        "source": (rows[0]["source"] if rows and rows[0]["source"] else
                   "Cartofriches (Cerema) — recensement AGORAH des friches urbaines"),
        "millesime": "AGORAH 2025",
    }


# ── C.10 — Loyers OLL (§Marché) ─────────────────────────────────────────────────────────────────
def loyers_oll(db: Session, idu: str) -> dict:
    """Loyer médian OLL de la zone de la parcelle, par type quand disponible (maison/appartement)."""
    from ..ingestion.oll_loyers import ANNEE, MILLESIME
    if not _has(db, "oll_zonage", "oll_loyers"):
        return {"disponible": False, "source": "Loyers OLL — ADIL / AGORAH", "millesime": MILLESIME}
    base = None
    try:
        from ..ingestion.oll_loyers import oll_parcelle
        base = oll_parcelle(db, idu)
    except Exception:  # noqa: BLE001 — le loyer ne casse jamais la fiche
        base = None
    if base is None:
        return {"disponible": False, "source": "Loyers OLL — ADIL / AGORAH (réseau des observatoires)",
                "millesime": MILLESIME}
    zone = base["zone"]
    par_type = {}
    for r in db.execute(text(
            "SELECT type_habitat, loyer_median FROM oll_loyers "
            "WHERE annee = :a AND zone = :z AND pieces = 'tous' AND loyer_median IS NOT NULL "
            "  AND type_habitat IN ('maison', 'appartement')"),
            {"a": ANNEE, "z": zone}).mappings():
        par_type[r["type_habitat"]] = round(float(r["loyer_median"]), 1)
    return {
        "disponible": True, "zone": zone,
        "loyer_median_eur_m2": base["loyer_median_eur_m2"], "par_type": par_type or None,
        "n_obs": base["n_obs"], "source": "Loyers OLL — ADIL / AGORAH (réseau des observatoires)",
        "millesime": base["millesime"],
    }


# ── C.11 — Trafic routier RN (§Réseaux, « Axes et nuisances ») ──────────────────────────────────
def trafic_rn(db: Session, idu: str) -> dict:
    """TMJA de l'axe RN le plus proche (≤ rayon) + distance. « sans objet » au-delà du rayon."""
    if not _has(db, "trafic_rn"):
        return {"disponible": False, "rayon_m": TMJA_RAYON_M,
                "source": "Trafic RN — Région Réunion (SIR)", "millesime": None}
    r = db.execute(text(
        "SELECT t.route, t.tmja, t.nb_pl, t.annee, "
        "       round(ST_Distance(t.geom::geography, p.centroid::geography)) AS dist "
        "FROM trafic_rn t JOIN parcels p ON p.idu = :idu "
        "WHERE t.tmja IS NOT NULL "
        "  AND ST_DWithin(t.geom::geography, p.centroid::geography, :ray) "
        "ORDER BY dist LIMIT 1"), {"idu": idu, "ray": float(TMJA_RAYON_M)}).mappings().first()
    if not r:
        return {"disponible": False, "rayon_m": TMJA_RAYON_M,
                "source": "Trafic RN — Région Réunion (Système d'Information Routier)", "millesime": None}
    return {
        "disponible": True, "route": r["route"], "tmja": int(r["tmja"]),
        "poids_lourds": int(r["nb_pl"]) if r["nb_pl"] is not None else None,
        "distance_m": int(r["dist"]) if r["dist"] is not None else None,
        "source": "Trafic RN — Région Réunion (Système d'Information Routier)",
        "millesime": f"TMJA {r['annee']}" if r["annee"] else None,
    }


# ── C.12 — CatNat (§Risques) — les 5 derniers arrêtés de la commune ─────────────────────────────
def catnat(db: Session, idu: str) -> dict:
    """Arrêtés de catastrophe naturelle de la commune (GASPAR) : nature + dates, les 5 plus récents."""
    if not _has(db, "catnat_arretes"):
        return {"disponible": False, "total": 0, "arretes": [],
                "source": "GASPAR / Géorisques", "millesime": "GASPAR"}
    insee = idu[:5]
    total = db.execute(text("SELECT count(*) FROM catnat_arretes WHERE insee = :i"),
                       {"i": insee}).scalar() or 0
    rows = db.execute(text(
        "SELECT type_peril, date_arrete, date_debut, date_fin FROM catnat_arretes "
        "WHERE insee = :i ORDER BY date_arrete DESC NULLS LAST LIMIT 5"),
        {"i": insee}).mappings().all()
    def _d(x):
        return x.isoformat() if isinstance(x, date) else (str(x) if x else None)
    return {
        "disponible": bool(rows), "total": int(total),
        "arretes": [{"peril": r["type_peril"], "date_arrete": _d(r["date_arrete"]),
                     "debut": _d(r["date_debut"]), "fin": _d(r["date_fin"])} for r in rows],
        "source": "GASPAR / Géorisques — arrêtés CatNat (au grain commune)", "millesime": "GASPAR",
    }


# ── C.13 — Acquisitions de personnes morales voisines (§Marché) ─────────────────────────────────
def pm_voisines(db: Session, idu: str) -> dict:
    """Personnes morales ayant acquis dans un rayon de 300 m sur 36 mois (DVF × DGFiP) : dénomination
    + SIREN + date de la dernière mutation ; jamais de personne physique nommée."""
    if not _has(db, "parcelle_personne_morale", "v_parcel_dvf_last"):
        return {"disponible": False, "rayon_m": PM_VOISIN_RAYON_M, "mois": PM_VOISIN_MOIS,
                "acquereurs": [], "source": "DVF × DGFiP", "millesime": "DVF + DGFiP 2025"}
    rows = db.execute(text(
        "SELECT pm.denomination, pm.siren, max(dl.date_mutation) AS derniere "
        "FROM parcels p0 "
        "JOIN parcels p2 ON p2.id <> p0.id AND ST_DWithin(p0.geom_2975, p2.geom_2975, :ray) "
        "JOIN parcelle_personne_morale pm ON pm.idu = p2.idu AND pm.siren IS NOT NULL "
        "JOIN v_parcel_dvf_last dl ON dl.idu = p2.idu "
        "WHERE p0.idu = :idu "
        "  AND dl.date_mutation >= (CURRENT_DATE - make_interval(months => :mois)) "
        "GROUP BY pm.denomination, pm.siren ORDER BY derniere DESC LIMIT 20"),
        {"idu": idu, "ray": float(PM_VOISIN_RAYON_M), "mois": PM_VOISIN_MOIS}).mappings().all()
    return {
        "disponible": bool(rows), "rayon_m": PM_VOISIN_RAYON_M, "mois": PM_VOISIN_MOIS,
        "acquereurs": [{"denomination": r["denomination"], "siren": r["siren"],
                        "date": r["derniere"].isoformat() if r["derniere"] else None} for r in rows],
        "source": "DVF (mutations) × DGFiP (fichier des parcelles des personnes morales)",
        "millesime": "DVF + DGFiP 2025",
    }


# ── C.14 — Ancienneté de détention (§Identité) ──────────────────────────────────────────────────
def anciennete_detention(db: Session, idu: str) -> dict:
    """« Propriétaire actuel depuis ≥ N ans ». PM : première apparition du SIREN aux millésimes DGFiP.
    PP (ou non recensé PM) : dernière mutation DVF (sans nom). « sans objet » si ni l'un ni l'autre."""
    if not _has(db, "parcelle_personne_morale", "pm_proprietaires_millesimes", "v_parcel_dvf_last"):
        return {"disponible": False, "source": "DGFiP (PM) / DVF", "millesime": None}
    an = date.today().year
    pm = db.execute(text(
        "SELECT pm.denomination, pm.siren, min(m.millesime) AS depuis "
        "FROM parcelle_personne_morale pm "
        "LEFT JOIN pm_proprietaires_millesimes m ON m.idu = pm.idu AND m.siren = pm.siren "
        "WHERE pm.idu = :idu AND pm.siren IS NOT NULL "
        "GROUP BY pm.denomination, pm.siren LIMIT 1"), {"idu": idu}).mappings().first()
    if pm and pm["depuis"]:
        depuis = int(pm["depuis"])
        return {"disponible": True, "type": "personne_morale", "denomination": pm["denomination"],
                "siren": pm["siren"], "depuis_annee": depuis, "depuis_ans": max(0, an - depuis),
                "source": "DGFiP — fichier des parcelles des personnes morales (millésimes)",
                "millesime": f"DGFiP {depuis}→2025"}
    mut = db.execute(text(
        "SELECT extract(year FROM date_mutation)::int AS an FROM v_parcel_dvf_last "
        "WHERE idu = :idu AND date_mutation IS NOT NULL"), {"idu": idu}).scalar()
    if mut:
        return {"disponible": True, "type": "personne_physique", "depuis_annee": int(mut),
                "depuis_ans": max(0, an - int(mut)),
                "source": "DVF — dernière mutation actée (propriétaire non nommé)",
                "millesime": "DVF"}
    return {"disponible": False, "source": "DGFiP (PM) / DVF (dernière mutation)", "millesime": None}
