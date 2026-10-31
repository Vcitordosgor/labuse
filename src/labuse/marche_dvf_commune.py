"""MARCHE-UNIQUE-1 — LE module de marché DVF par (commune, type). Point de calcul UNIQUE de la
médiane €/m² ACTÉE d'une commune, lue à l'identique par la fiche, « Estimer un bien », le Radar,
Communes, la fiche commune, l'Étude et les PDF. Avant ce module, chaque surface recalculait sa
médiane commune avec son propre filtre de nature, sa propre fenêtre et son propre dénominateur —
d'où, sur le MÊME écran du Radar, « acté médian maisons » à 4 030 € d'un côté et 3 750 € de l'autre
(NU-F-001), un prix d'appartement servi sur une maison (NU-A-002 / NU-D-010) et le neuf (VEFA) qui
remontait la médiane « ancien » (NU-A-012 / NU-D-011 / NU-E-025 / NU-E-030).

Doctrine (un critère, un endroit) :
  · NATURE — l'ANCIEN bâti ne retient QUE `nature_mutation = 'Vente'`. Les natures réelles de DVF
    Réunion (mesuré 2026-10-31) sont : Vente · Vente en l'état futur d'achèvement (VEFA, = le NEUF) ·
    Vente terrain à bâtir · Adjudication · Echange (sans accent) · Expropriation. Le viager est
    ABSENT. On exclut donc VEFA (neuf, profil dédié), VTB (terrain nu), et adjudication / échange /
    expropriation (hors marché de gré à gré). Le TERRAIN nu retient `Vente` + `Vente terrain à bâtir`
    (un acte VTB sans bâti EST une vente de terrain nu — arbitrage M101 B2).
  · MULTI-PARCELLES / DÉPENDANCES — le bâti lit `dvf_mutations` (grain MUTATION : une mutation = une
    ligne, dépendances déjà agrégées). Le terrain lit `dvf_mutations_parcelle` et DÉDOUBLONNE par
    mutation (surface = `max()` par (mutation, parcelle) puis `sum()` par mutation) — jamais la somme
    des lignes répétées (NU-E-031).
  · FENÊTRE — le millésime géo-DVF ENTIER disponible (2021-2025 figé), ancré sur `max(date_mutation)`
    de la commune pour la fraîcheur servie ; pas de `now()` glissant (NU-E-033).
  · NEUF — médiane VEFA dédiée (`mediane_neuf_commune`), UN SEUL libellé « neuf (VEFA) » (NU-B-003).

La médiane renvoyée est le flottant BRUT (les appelants arrondissent comme avant) : deux surfaces qui
lisent ce point servent donc le MÊME entier à l'affichage, à l'euro près (recette MARCHE-UNIQUE-1).
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

#: L'ANCIEN bâti = la vente de gré à gré SEULE (jamais VEFA/VTB/adjudication/échange/expropriation).
NATURE_ANCIEN_SQL = "dm.nature_mutation = 'Vente'"
#: Le TERRAIN nu = vente OU vente de terrain à bâtir (M101 B2), toujours sans bâti.
NATURE_TERRAIN_SQL = "dm.nature_mutation IN ('Vente', 'Vente terrain à bâtir')"

#: Domaines €/m² de bon sens (artefacts DVF écartés) — mêmes bornes que le filtre comparables.
BORNE_BATI = (1000, 12000)
BORNE_TERRAIN = (50, 4000)

#: type_local DVF du type de bien bâti.
_FRAG = {"maison": "Maison", "appartement": "Appartement"}


def seuil_commune() -> int:
    """Seuil d'effectif UNIQUE des médianes de référence (config `dvf_profils.yaml`,
    `seuils_effectif.mediane_generique`) ; repli doctrine n≥8 si la config est absente."""
    try:
        from .marche_service import seuil_effectif_local
        return seuil_effectif_local("mediane_generique", 8)
    except Exception:  # noqa: BLE001 — config indisponible : repli doctrine
        return 8


def _vide(type_bien: str, perimetre: str, millesime: str | None = None, n: int = 0) -> dict:
    return {"type_bien": type_bien, "eur_m2": None, "n": n, "periode": None,
            "millesime_dvf": millesime, "perimetre": perimetre}


def _median_bati(db: Session, commune: str, type_bien: str, seuil: int) -> dict:
    """Médiane €/m² BÂTI ancien de la commune pour `maison`/`appartement` (grain mutation,
    `dvf_mutations`, nature = Vente stricte, surface ≥ 20 m², millésime entier)."""
    frag = _FRAG.get(type_bien)
    if frag is None:
        return _vide(type_bien, "commune")
    lo, hi = BORNE_BATI
    r = db.execute(text(
        "WITH s AS ("
        "  SELECT dm.valeur_fonciere / NULLIF(dm.surface_reelle_bati, 0) AS ratio, "
        "         extract(year FROM dm.date_mutation)::int AS annee, dm.date_mutation AS d "
        "  FROM dvf_mutations dm "
        "  WHERE lower(dm.commune) = lower(:c) AND " + NATURE_ANCIEN_SQL + " "
        "    AND dm.type_local = :tl AND dm.surface_reelle_bati >= 20 AND dm.valeur_fonciere > 0) "
        "SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY ratio) "
        "         FILTER (WHERE ratio BETWEEN :lo AND :hi) AS med, "
        "       count(*) FILTER (WHERE ratio BETWEEN :lo AND :hi) AS n, "
        "       min(annee) FILTER (WHERE ratio BETWEEN :lo AND :hi) AS y0, "
        "       max(annee) FILTER (WHERE ratio BETWEEN :lo AND :hi) AS y1, "
        "       to_char(max(d), 'YYYY-MM-DD') AS mill "
        "FROM s"),
        {"c": commune, "tl": frag, "lo": lo, "hi": hi}).mappings().first() or {}
    n = int(r.get("n") or 0)
    mill = r.get("mill")
    if n < seuil or r.get("med") is None:
        return _vide(type_bien, f"{type_bien}s · commune", mill, n)
    return {"type_bien": type_bien, "eur_m2": float(r["med"]), "n": n,
            "periode": [int(r["y0"]), int(r["y1"])] if r.get("y0") else None,
            "millesime_dvf": mill, "perimetre": f"{type_bien}s · commune"}


def _median_terrain(db: Session, commune: str, seuil: int) -> dict:
    """Médiane €/m² du TERRAIN NU de la commune (`dvf_mutations_parcelle`, ventes sans bâti),
    DÉDOUBLONNÉE par mutation (max par parcelle puis somme par mutation), millésime entier."""
    lo, hi = BORNE_TERRAIN
    r = db.execute(text(
        "WITH parc AS ("
        "  SELECT DISTINCT dm.id_mutation, dm.id_parcelle, dm.valeur_fonciere AS vf, dm.date_mutation AS d, "
        "         max(COALESCE(dm.surface_terrain, 0)) OVER (PARTITION BY dm.id_mutation, dm.id_parcelle) AS terr_p "
        "  FROM dvf_mutations_parcelle dm JOIN parcels p ON p.idu = dm.id_parcelle "
        "  WHERE lower(p.commune) = lower(:c) AND " + NATURE_TERRAIN_SQL + " "
        "    AND COALESCE(dm.surface_reelle_bati, 0) = 0 AND dm.surface_terrain > 0), "
        "tot AS (SELECT id_mutation, sum(terr_p) AS terr_tot, max(vf) AS vf, "
        "               min(d) AS d0, max(d) AS d1 FROM parc GROUP BY id_mutation) "
        "SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY vf / NULLIF(terr_tot, 0)) "
        "         FILTER (WHERE vf / NULLIF(terr_tot, 0) BETWEEN :lo AND :hi) AS med, "
        "       count(*) FILTER (WHERE vf / NULLIF(terr_tot, 0) BETWEEN :lo AND :hi) AS n, "
        "       to_char(min(d0), 'YYYY') AS y0, to_char(max(d1), 'YYYY') AS y1, "
        "       to_char(max(d1), 'YYYY-MM-DD') AS mill "
        "FROM tot"),
        {"c": commune, "lo": lo, "hi": hi}).mappings().first() or {}
    n = int(r.get("n") or 0)
    mill = r.get("mill")
    if n < seuil or r.get("med") is None:
        return _vide("terrain", "terrain nu · commune", mill, n)
    return {"type_bien": "terrain", "eur_m2": float(r["med"]), "n": n,
            "periode": [int(r["y0"]), int(r["y1"])] if r.get("y0") else None,
            "millesime_dvf": mill, "perimetre": "terrain nu · commune"}


def mediane_commune(db: Session, commune: str, type_bien: str, *, seuil: int | None = None) -> dict:
    """LA médiane €/m² ACTÉE de la commune pour un type de bien — point de lecture UNIQUE.

    `commune` = NOM de commune (comme en base `dvf_mutations.commune`). `type_bien` ∈
    {maison, appartement, terrain}. Renvoie TOUJOURS un dict (jamais None) :
    `{type_bien, eur_m2(float|None), n, periode:[y0,y1]|None, millesime_dvf, perimetre}`.
    `eur_m2 = None` sous le seuil d'effectif (jamais une médiane sur un échantillon mince)."""
    if not commune:
        return _vide(type_bien, "commune")
    s = int(seuil if seuil is not None else seuil_commune())
    if type_bien == "terrain":
        return _median_terrain(db, commune, s)
    return _median_bati(db, commune, type_bien, s)


def mediane_neuf_commune(db: Session, insee: str, *, seuil: int | None = None) -> dict:
    """LA médiane €/m² du NEUF (VEFA) de la commune — UN SEUL libellé « neuf (VEFA) » partout
    (NU-B-003). Délègue au calcul VEFA existant (`ingestion.dvf_marche.neuf_vefa_commune`,
    fenêtre 5 ans ancrée, lots d'habitation seuls) ; applique le seuil d'effectif ici. `insee` =
    code commune (left(idu, 5)). Renvoie le même contrat que `mediane_commune`."""
    from .ingestion.dvf_marche import neuf_vefa_commune, NEUF_VEFA_FENETRE_ANS
    s = int(seuil if seuil is not None else seuil_commune())
    r = neuf_vefa_commune(db, insee)
    n = int(r.get("n") or 0)
    med = r.get("mediane_prix_m2_bati")
    if n < s or med is None:
        return {"type_bien": "neuf", "eur_m2": None, "n": n, "periode": None,
                "millesime_dvf": None, "perimetre": "neuf (VEFA) · commune",
                "fenetre_ans": r.get("fenetre_ans", NEUF_VEFA_FENETRE_ANS)}
    return {"type_bien": "neuf", "eur_m2": float(med), "n": n, "periode": None,
            "millesime_dvf": None, "perimetre": "neuf (VEFA) · commune",
            "fenetre_ans": r.get("fenetre_ans", NEUF_VEFA_FENETRE_ANS)}


#: Libellé client UNIQUE du neuf (NU-B-003) — plus jamais « neuf » nu à côté de « Neuf observé ».
LIBELLE_NEUF = "neuf (VEFA sur plan)"


#: Tables de médianes DVF qui portent un `millesime_dvf` (NU-E-032) : cache → table source du millésime.
_CACHES_MILLESIME = (("dvf_secteur_medianes", "dvf_mutations_parcelle"),
                     ("dvf_prix_sortie_neuf", "dvf_mutations_parcelle"))


def caches_marche_perimes(db: Session) -> list[dict]:
    """NU-E-032 — l'ÂGE des caches de médianes est VÉRIFIABLE : un cache est PÉRIMÉ quand son
    `millesime_dvf` (le max(date_mutation) sur lequel il a été bâti) ≠ le millésime DVF COURANT.
    Un `computed_at` récent ne suffit PAS — il dit quand on a calculé, pas sur quelle donnée.
    Renvoie la liste des caches périmés (vide = tous à jour). Lu par le doctor / un garde de build :
    après chaque ingestion DVF, ces tables doivent être recalculées (leur builder stampe le millésime)."""
    out: list[dict] = []
    for table, source in _CACHES_MILLESIME:
        if db.execute(text("SELECT to_regclass(:t)"), {"t": table}).scalar() is None:
            continue
        cols = db.execute(text(
            "SELECT 1 FROM information_schema.columns WHERE table_name = :t "
            "AND column_name = 'millesime_dvf'"), {"t": table}).scalar()
        if not cols:
            out.append({"cache": table, "motif": "colonne millesime_dvf absente (cache antérieur à NU-E-032)"})
            continue
        courant = db.execute(text(f"SELECT max(date_mutation) FROM {source}")).scalar()
        stampe = db.execute(text(f"SELECT max(millesime_dvf) FROM {table}")).scalar()
        if courant is not None and stampe != courant:
            out.append({"cache": table, "millesime_cache": str(stampe),
                        "millesime_dvf_courant": str(courant),
                        "motif": "cache bâti sur un millésime DVF antérieur — recalcul requis"})
    return out
