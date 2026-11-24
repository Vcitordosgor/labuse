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
    ligne, dépendances déjà agrégées). Le terrain lit `dvf_mutations_parcelle` : surface d'une parcelle =
    SOMME de ses subdivisions DISTINCTES (couple distinct (nature_culture, surface_terrain)) puis `sum()`
    par mutation — ni la plus grande ligne (`max`, qui perdait une subdivision : ET0142 1 895→1 195 m²,
    FIX-4 LOT 1.c), ni la somme des lignes répétées par `type_local` (NU-E-031, qui gonflait).
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

#: OUTIL-COMMUNES-FIX-3 (B-1/B-2) puis FIX-4 (LOT 1) — LA QUALIFICATION UNIQUE DU TERRAIN NU. Un acte est
#: une vente de terrain nu si et seulement si, sur son ACTE ENTIER (toutes ses lignes DVF, TOUTES communes
#: confondues) :
#:   (0) aucune ligne ne porte de bâti mesuré      — `sum(bati) = 0` ;
#:   (a) aucune ligne ne DÉCLARE de local, même sans surface — `bool_or(type_local IS NOT NULL) = false`.
#:       FIX-4 LOT 1.a : un « Local industriel. commercial ou assimilé » / une dépendance sans surface
#:       bâtie renseignée (surface_reelle_bati NULL→0) passait l'ancien `sum(bati)=0` ; 83 actes avec
#:       local déclaré étaient certifiés « terrain nu » (témoin 2023-1315722 : local sur IZ0236) ;
#:   (b) l'acte ne porte que sur UNE commune — `count(DISTINCT code_commune) = 1`. FIX-4 LOT 1.b : un acte
#:       réparti sur deux communes (témoin 2022-1639451 : 465 m² à Petite-Île + 485 m² à Saint-Joseph)
#:       entrait dans les DEUX populations ; il est désormais écarté PARTOUT.
#: La surface terrain est reconstituée sur l'acte entier comme la SOMME DES SUBDIVISIONS DISTINCTES de
#: chaque parcelle (FIX-4 LOT 1.c) : DVF répète la ligne d'une parcelle par `type_local` (même surface) et
#: la subdivise par `nature_culture` (surfaces différentes). On prend donc le couple DISTINCT
#: (nature_culture, surface_terrain) par parcelle puis on SOMME — jamais la plus grande ligne (`max`, qui
#: perdait les subdivisions : témoin 2021-1676912, ET0142 = 1 195 m² « sols » + 700 m² « terres » = 1 895 m²
#: cadastraux, servi 1 195 → 444 €/m² au lieu de 280), ni la somme des lignes répétées (NU-E-031, qui
#: gonflait la surface). La valeur est la `valeur_fonciere` de l'acte (constante, `max`). Natures Vente + VTB.
#:
#: TOUS les lecteurs du terrain nu (tableau, fiche commune, Comparer/section, Assemblage, fiche parcelle,
#: Estimer, Étude de zone, repère du Bilan, Radar île, série baromètre, banc) EMBARQUENT ce CTE et JOIGNENT
#: dessus leur périmètre (commune, zone, secteur, rayon, polygone) — UNE SEULE qualification, ZÉRO acte
#: bâti / avec local / multi-communes ne survit nulle part.
#:
#: COÛT : scan complet de `dvf_mutations_parcelle` (indispensable pour voir le bâti/local d'une AUTRE
#: commune de l'acte) ~250 ms — le tableau des 24 est CACHÉ (raw_rows), les fiches tolèrent le surcoût. Les
#: lecteurs qui restreignent à une commune AVANT la jointure matérialisent leur `scope` (sinon le planner
#: re-scanne la table en boucle imbriquée : baromètre Cilaos 200 s → 0,2 s, FIX-4 LOT 4).
ACTE_TERRAIN_NU_CTE = """acte_nu AS (
  SELECT id_mutation, sum(terr_p) AS terr_tot, max(val) AS val, max(mill) AS mill,
         min(d0) AS d0, max(d1) AS d1
  FROM (SELECT id_mutation, id_parcelle,
               sum(terr_sub)        AS terr_p,    -- somme des subdivisions DISTINCTES de la parcelle
               max(bati_p)          AS bati_p,    -- bâti mesuré (0 sur tout l'acte = pas de bâti)
               bool_or(a_local)     AS a_local,   -- un local déclaré quelque part sur la parcelle
               max(cc) AS cc, max(val) AS val, max(mill) AS mill,
               min(d0) AS d0, max(d1) AS d1
        FROM (SELECT id_mutation, id_parcelle, code_commune AS cc, nature_culture,
                     COALESCE(surface_terrain, 0) AS terr_sub,
                     max(COALESCE(surface_reelle_bati, 0)) AS bati_p,
                     bool_or(type_local IS NOT NULL)       AS a_local,
                     max(valeur_fonciere) AS val, max(millesime) AS mill,
                     min(date_mutation) AS d0, max(date_mutation) AS d1
              FROM dvf_mutations_parcelle
              WHERE nature_mutation IN ('Vente', 'Vente terrain à bâtir')
              GROUP BY id_mutation, id_parcelle, code_commune, nature_culture,
                       COALESCE(surface_terrain, 0)) sub
        GROUP BY id_mutation, id_parcelle) pp
  GROUP BY id_mutation
  HAVING sum(bati_p) = 0 AND bool_or(a_local) = false
     AND sum(terr_p) > 0 AND count(DISTINCT cc) = 1)"""

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
    """Médiane €/m² du TERRAIN NU de la commune (`dvf_mutations_parcelle`), QUALIFIÉE SUR L'ACTE
    ENTIER (OUTIL-COMMUNES-FIX-1 bloquant 1) : un acte n'est une vente de terrain nu que si AUCUNE de
    ses parcelles ne porte de bâti (`sum(bati) = 0` sur toute la mutation) — un acte mixte (maison +
    jardin nu) n'en est pas une et ne reçoit JAMAIS le prix de l'acte entier rapporté à la seule
    surface nue (cas 2021-1672641). La surface terrain est RECONSTITUÉE sur toutes les parcelles de
    l'acte (max par parcelle puis somme par mutation), millésime entier, natures Vente+VTB (M101 B2).

    OUTIL-COMMUNES-FIX-2 #1 puis FIX-3 B-1/B-2 — QUALIFICATION UNIQUE (`ACTE_TERRAIN_NU_CTE`) sur l'acte
    entier TOUTES COMMUNES : ni `JOIN parcels` (ratait la parcelle disparue), ni `code_commune` (ne voyait
    pas le bâti d'une autre commune de l'acte). On joint la qualification unique à l'appartenance de la
    commune (une parcelle de l'acte en code_commune)."""
    lo, hi = BORNE_TERRAIN
    insee = db.execute(text("SELECT left(min(idu), 5) FROM parcels WHERE lower(commune) = lower(:c)"),
                       {"c": commune}).scalar()
    r = db.execute(text(
        "WITH " + ACTE_TERRAIN_NU_CTE + ", "
        "comm AS (SELECT DISTINCT id_mutation FROM dvf_mutations_parcelle "
        "         WHERE code_commune = :insee AND " + NATURE_TERRAIN_SQL.replace("dm.", "") + "), "
        "tot AS (SELECT a.val AS vf, a.terr_tot, a.d0, a.d1 FROM acte_nu a JOIN comm USING (id_mutation)) "
        "SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY vf / NULLIF(terr_tot, 0)) "
        "         FILTER (WHERE vf / NULLIF(terr_tot, 0) BETWEEN :lo AND :hi) AS med, "
        "       count(*) FILTER (WHERE vf / NULLIF(terr_tot, 0) BETWEEN :lo AND :hi) AS n, "
        "       to_char(min(d0), 'YYYY') AS y0, to_char(max(d1), 'YYYY') AS y1, "
        "       to_char(max(d1), 'YYYY-MM-DD') AS mill "
        "FROM tot"),
        {"insee": insee, "lo": lo, "hi": hi}).mappings().first() or {}
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
