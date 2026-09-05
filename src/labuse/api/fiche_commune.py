"""OUTILS-6 — LES BLOCS AJOUTÉS DE LA FICHE COMMUNE (C5) + les compteurs des passerelles (C6).

Doctrine transversale : **un seul moteur, une seule donnée**. Aucune donnée n'est recalculée ici — chaque
bloc CONSOMME le point de calcul EXISTANT de l'outil d'origine (Radar, Pièges & risques, Étude de zone,
veille PLU, Permis, Densifier) et se contente de le présenter à la maille commune. Introuvable = null (le
front affiche « non disponible » sourcé, jamais un zéro menteur). Rien n'entre dans le scoring.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


# ───────────────────────────── C2 — les chiffres COMMUNS au comparateur ─────────────────────────────
def comparable(db: Session, commune: str) -> dict | None:
    """Les chiffres que la fiche PARTAGE avec le comparateur des 24 communes (OUTILS-6 C2) : ils viennent
    de la MÊME source (`comparateur.raw_rows`, même run, mêmes requêtes) → chaque valeur est identique des
    deux côtés, par construction. Le prix ancien est la médiane COMMUNE ENTIÈRE (baromètre DVF), jamais le
    `sector_price` local d'une parcelle représentative."""
    from .comparateur import raw_rows
    r = raw_rows(db).get(commune)
    if not r:
        return None
    velo = r.get("velocite")
    return {
        "ancien_median_eur_m2": r.get("prix_ancien"),
        "ancien_n": r.get("prix_ancien_n"),
        "neuf_eur_m2": r.get("prix_neuf"),
        "permis_5a": r.get("permis"),
        "delai_median_mois": round(float(velo), 1) if velo is not None else None,
        "stock_opportunites_n": r.get("stock"),
        "source": "DVF (baromètre commune entière) + SITADEL + m10 — même moteur et même run que le "
                  "comparateur des 24 communes.",
    }


# ───────────────────────────── C5 — le marché des annonces (Radar) ─────────────────────────────
def marche_annonces(db: Session, commune: str) -> dict | None:
    """Radar LABUSE, à la maille commune. Même seuil d'affichage que le bloc Communes (OUTILS-2) :
    servi à partir de `SEUIL_N` biens, sinon `sous_seuil=True` (le front replie en une phrase). L'écart
    demandé/acté — le signal exclusif LABUSE — est calculé entre le prix demandé (annonces, bâti) et le
    prix acté commune entière (baromètre DVF, cf. `comparable`). None si Radar ne couvre pas la commune."""
    from ..pige.marche import SEUIL_N, stats
    row = next((c for c in stats(db).get("communes", []) if c.get("commune") == commune), None)
    if not row:
        return None
    demande = (row.get("prix_m2_bati") or {}).get("valeur")
    cmp = comparable(db, commune) or {}
    acte = cmp.get("ancien_median_eur_m2")
    ecart = round(100.0 * (demande - acte) / acte, 1) if (demande and acte) else None
    biens = int(row.get("actives") or 0)
    return {
        "biens": biens,
        "seuil_n": SEUIL_N,
        "sous_seuil": biens < SEUIL_N,
        "prix_demande_median_eur_m2": demande,
        "prix_demande_n": (row.get("prix_m2_bati") or {}).get("n"),
        "ecart_demande_acte_pct": ecart,
        "prix_acte_eur_m2": acte,
        "source": "Radar LABUSE (annonces relevées) · écart mesuré contre le baromètre DVF commune entière.",
    }


# ───────────────────────────── C5 — les risques (Géorisques / Pièges & risques) ─────────────────────────────
def risques(db: Session, commune: str, insee: str | None) -> dict:
    """Part des parcelles de la commune exposées, par couche Géorisques déjà ingérée (mêmes couches
    `spatial_layers` que l'outil Pièges & risques), + le nombre d'arrêtés CatNat (table `catnat_arretes`)
    et la présence du Parc National. Les libellés restent fidèles à la donnée : la couche `ppr` n'ayant
    pas de sous-type dans nos attributs, on n'invente pas « inondation » — on dit « PPR (risque naturel) »."""
    tot = db.execute(text("SELECT count(*) FROM parcels WHERE commune = :c"), {"c": commune}).scalar() or 0

    def _pct_layer(kind: str) -> float | None:
        if not tot:
            return None
        n = db.execute(text(
            "SELECT count(DISTINCT p.idu) FROM parcels p JOIN spatial_layers sl ON sl.kind = :k "
            "AND ST_Intersects(p.geom_2975, sl.geom_2975) WHERE p.commune = :c"),
            {"k": kind, "c": commune}).scalar() or 0
        return round(100.0 * n / tot, 1)

    catnat = (db.execute(text("SELECT count(*) FROM catnat_arretes WHERE insee = :i"),
                         {"i": insee}).scalar() or 0) if insee else 0
    parc = db.execute(text(
        "SELECT EXISTS (SELECT 1 FROM parcels p JOIN spatial_layers sl ON sl.kind = 'parc_national' "
        "AND ST_Intersects(p.geom_2975, sl.geom_2975) WHERE p.commune = :c)"), {"c": commune}).scalar()
    return {
        "ppr_pct": _pct_layer("ppr"),
        "mouvement_terrain_pct": _pct_layer("mvt"),
        "catnat_arretes": int(catnat),
        "parc_national": bool(parc),
        "source": "Géorisques (PPR, mouvement de terrain) · GASPAR (arrêtés CatNat) · BD TOPO (Parc National).",
    }


# ───────────────────────────── C5 — population & revenu (Étude de zone / Filosofi) ─────────────────────────────
def population(db: Session, commune: str, insee: str | None) -> dict:
    """Habitants, ménages et niveau de vie moyen — agrégat des carreaux Filosofi 200 m dont le centroïde
    tombe sur une parcelle de la commune (même donnée que l'Étude de zone). Mémoïsé 1 h (Filosofi est
    statique ; l'agrégat spatial est coûteux) — la fiche reste en LECTURE seule. Complété par le stock de
    logements (`commune_insee_logement`, déjà servi). `ind_snv/ind` est un niveau de vie MOYEN, pas une
    médiane : on le nomme comme tel."""
    from .app import _mem_cached

    def _c():
        r = db.execute(text(
            "SELECT round(sum(f.ind)) hab, round(sum(f.men)) men, "
            "       round(sum(f.ind_snv) / NULLIF(sum(f.ind), 0)) niveau_vie_moyen "
            "FROM filosofi_carreaux_200m f WHERE EXISTS ("
            "  SELECT 1 FROM parcels p WHERE p.commune = :c "
            "  AND ST_Intersects(p.geom_2975, ST_Centroid(f.geom)))"), {"c": commune}).mappings().first()
        return dict(r) if r else {}
    demo = _mem_cached(("fiche-pop", commune), 3600.0, _c)
    log = db.execute(text("SELECT logements, vacants FROM commune_insee_logement WHERE insee = :i"),
                     {"i": insee}).mappings().first() if insee else None
    logements = int(log["logements"]) if log and log["logements"] is not None else None
    vacants = int(log["vacants"]) if log and log["vacants"] is not None else None
    return {
        "habitants": int(demo["hab"]) if demo.get("hab") is not None else None,
        "menages": int(demo["men"]) if demo.get("men") is not None else None,
        "niveau_vie_moyen_eur": int(demo["niveau_vie_moyen"]) if demo.get("niveau_vie_moyen") is not None else None,
        "logements": logements,
        "vacants": vacants,
        "vacance_pct": round(100.0 * vacants / logements, 1) if (logements and vacants is not None) else None,
        "source": "INSEE Filosofi 2021 (carreaux 200 m, agrégat commune) · INSEE RP (logements).",
    }


# ───────────────────────────── C5 — le PLU (statut + document d'urbanisme) ─────────────────────────────
_PLU_STATUT = {
    "cloturee": "à jour", "aucune": "à jour",
    "revision_plu": "en révision", "elaboration_plu": "en élaboration",
    "modification_plu": "en modification",
}


def plu_statut(db: Session, insee: str | None, commune: str | None) -> dict:
    """Statut du document d'urbanisme (à jour / en révision / RNU), sa date d'opposabilité et le lien vers
    la recherche verbatim. Statut CALCULÉ (registre `veille_plu` + `rnu`), jamais en dur (correctif A5
    d'OUTILS-1). RNU = pas de PLU opposable ; l'emporte sur toute procédure."""
    from .. import rnu as rnu_mod
    if rnu_mod.is_rnu_insee(insee):
        return {"statut": "RNU", "libelle": "Règlement National d'Urbanisme (pas de PLU opposable)",
                "date_reglement": None, "recherche_verbatim": True,
                "source": "config/rnu_communes.yaml"}
    from .. import veille_plu
    e = veille_plu.entry(insee) or {}
    proc = e.get("procedure")
    return {
        "statut": _PLU_STATUT.get(proc, "document local"),
        "libelle": e.get("stade"),
        "procedure": proc,
        "date_reglement": None if e.get("date_acte") in (None, "ABSENT") else e.get("date_acte"),
        "confiance": e.get("confiance"),
        "recherche_verbatim": True,
        "source": e.get("source"),
    }


# ───────────────────────────── C5 — construire ici (permis + point mort) ─────────────────────────────
def permis_bloc(db: Session, commune: str) -> dict:
    """Le bloc « Construire ici » : permis autorisés (12 mois / 5 ans) et délai d'instruction viennent des
    MÊMES sources que le comparateur (SITADEL + m10, cf. `comparable`) ; les permis AU POINT MORT (accordés
    puis frappés de caducité, sans DAACT) sont le gisement dormant déjà calculé par `pc_caducs` — servi ici
    à la maille commune."""
    from ..faisabilite.marche_commune import ligne6_offre_engagee
    offre = ligne6_offre_engagee(db, commune)
    point_mort = db.execute(text(
        "SELECT count(*) FROM pc_caducs pc JOIN parcels p ON p.idu = pc.idu WHERE p.commune = :c"),
        {"c": commune}).scalar() or 0
    cmp = comparable(db, commune) or {}
    return {
        "permis_12m": (offre.get("valeurs") or {}).get("permis_12m") or 0,
        "permis_5a": cmp.get("permis_5a"),
        "logements_12m": (offre.get("valeurs") or {}).get("logements_12m"),
        "delai_median_mois": cmp.get("delai_median_mois"),
        "point_mort": int(point_mort),
        "source": "SITADEL (autorisations) · m10 (délais) · PC caducs (dormants, Estimé).",
    }


# ───────────────────────────── C5 — densifiables / gisement + loyer sourcé ─────────────────────────────
def densifiables(db: Session, commune: str) -> dict | None:
    """Le gisement de densification (parcelles à capacité résiduelle + SDP), depuis le point de calcul de
    l'outil Densifier (`ligne7_gisement`, tiers servables du run servi). None si non calculable."""
    from ..faisabilite.marche_commune import ligne7_gisement
    g = ligne7_gisement(db, commune)
    if not g.get("calculable"):
        return None
    v = g.get("valeurs") or {}
    return {"parcelles": v.get("parcelles"), "sdp_residuelle_m2": v.get("sdp_residuelle_m2"),
            "source": g.get("etiquette")}


def loyer(db: Session, commune: str) -> dict | None:
    """Loyer médian — SOURCÉ (le seul chiffre de l'ancienne fiche sans source ni millésime). On lit la
    ligne loyer du bloc Marché commune (`build_marche_commune`), qui porte sa source. None = non calculable
    (jamais un chiffre nu)."""
    from ..faisabilite.marche_commune import build_marche_commune
    mc = build_marche_commune(db, commune)
    lg = next((l for l in mc.get("lignes", []) if l.get("cle") == "loyer_median"), None)
    if not lg:
        return None
    v = lg.get("valeurs") or {}
    if v.get("loyer_eur_m2") is None:
        return None
    return {"median_eur_m2": v.get("loyer_eur_m2"), "type": v.get("type"),
            "source": lg.get("etiquette") or lg.get("source") or "DHUP (carte des loyers)"}


# ───────────────────────────── C6 — les compteurs des passerelles ─────────────────────────────
def outils_counters(db: Session, commune: str, insee: str | None,
                    blocs: dict) -> dict:
    """Le chiffre que porte chaque passerelle (C6) : un lien qui annonce ce qu'il contient se clique. On
    réutilise les compteurs DÉJÀ calculés pour les blocs (aucune requête en double) ; on n'ajoute que ceux
    qui manquent (piscines pour le Solaire, acquisitions PM pour le Scan). Un outil dont le compteur vaut 0
    n'apparaît pas (le front l'omet) — jamais un lien grisé à zéro."""
    piscines = db.execute(text(
        "SELECT count(*) FROM parcel_equipements e JOIN parcels p ON p.idu = e.idu "
        "WHERE p.commune = :c AND e.piscine"), {"c": commune}).scalar() or 0
    scan_pm = 0
    if insee:
        scan_pm = db.execute(text(
            "SELECT count(DISTINCT idu) FROM parcelle_personne_morale "
            "WHERE left(idu, 5) = :i"), {"i": insee}).scalar() or 0
    permis = blocs.get("permis") or {}
    dens = blocs.get("densifiables") or {}
    radar = blocs.get("marche_annonces") or {}
    return {
        "permis_en_cours": permis.get("permis_12m") or 0,
        "permis_point_mort": permis.get("point_mort") or 0,
        "densifiables": dens.get("parcelles") or 0,
        "radar_biens": radar.get("biens") or 0,
        "scan_pm": int(scan_pm),
        "solaire_piscines": int(piscines),
    }


import logging

log = logging.getLogger("labuse.fiche_commune")

# Replis VALIDES (même forme que la donnée nominale) — une source absente ou une table manquante dégrade
# le bloc concerné SANS casser la fiche entière (« introuvable = null, jamais un zéro menteur »).
_FALLBACK = {
    "comparable": None, "marche_annonces": None, "densifiables": None, "loyer": None,
    "risques": {"ppr_pct": None, "mouvement_terrain_pct": None, "catnat_arretes": 0,
                "parc_national": False, "source": "Géorisques · GASPAR · BD TOPO"},
    "population": {"habitants": None, "menages": None, "niveau_vie_moyen_eur": None,
                   "logements": None, "vacants": None, "vacance_pct": None,
                   "source": "INSEE Filosofi · INSEE RP"},
    "plu_statut": {"statut": "document local", "libelle": None, "procedure": None,
                   "date_reglement": None, "confiance": None, "recherche_verbatim": True, "source": None},
    "permis": {"permis_12m": 0, "permis_5a": None, "logements_12m": None,
               "delai_median_mois": None, "point_mort": 0, "source": "SITADEL · m10 · PC caducs"},
    "outils": {"permis_en_cours": 0, "permis_point_mort": 0, "densifiables": 0,
               "radar_biens": 0, "scan_pm": 0, "solaire_piscines": 0},
}


def _safe(db: Session, key: str, fn):
    """Exécute un builder ; en cas d'échec (table absente, source manquante), ROLLBACK la session (sinon
    la transaction reste avortée et les blocs suivants échouent en cascade) et rend le repli valide."""
    try:
        return fn()
    except Exception as exc:   # noqa: BLE001 — un bloc défaillant ne doit jamais casser la fiche
        log.warning("fiche_commune: bloc %s indisponible (%s)", key, exc)
        db.rollback()
        return _FALLBACK[key]


def build(db: Session, commune: str, insee: str | None) -> dict:
    """Assemble tous les blocs ajoutés + les compteurs de passerelles, en un seul objet servi à la fiche.
    Chaque bloc est isolé : une source indisponible dégrade CE bloc, pas la fiche."""
    blocs = {
        "comparable": _safe(db, "comparable", lambda: comparable(db, commune)),
        "marche_annonces": _safe(db, "marche_annonces", lambda: marche_annonces(db, commune)),
        "risques": _safe(db, "risques", lambda: risques(db, commune, insee)),
        "population": _safe(db, "population", lambda: population(db, commune, insee)),
        "plu_statut": _safe(db, "plu_statut", lambda: plu_statut(db, insee, commune)),
        "permis": _safe(db, "permis", lambda: permis_bloc(db, commune)),
        "densifiables": _safe(db, "densifiables", lambda: densifiables(db, commune)),
        "loyer": _safe(db, "loyer", lambda: loyer(db, commune)),
    }
    blocs["outils"] = _safe(db, "outils", lambda: outils_counters(db, commune, insee, blocs))
    return blocs
