"""ETUDE-V6 (Lot A, étape 1) — validation de l'assiette foncière AVANT le moteur.

Rapide (pas d'implantation) : pour 1 à 8 parcelles, on remonte les faits par parcelle (commune,
référence, contenance cadastrale = surface de référence retenue, surface réelle géométrique et écart,
zone PLU, qualité géométrique), les métriques de l'union, les signaux (communes/zones/ravine
différentes, propriétaires présumés) et les sources + millésimes. La **contiguïté** suit le mandat :
graphe d'adjacence où deux parcelles sont voisines si elles partagent une **portion de frontière de
longueur > tolérance** (jamais un simple sommet, jamais la distance entre centroïdes) ; l'assiette est
valide seulement si le graphe COMPLET est connexe (une seule composante). La connexité est donc
réévaluée telle quelle à chaque ajout/retrait côté client (il rappelle cette validation).

Volontairement distinct de `terrain.charger()` (qui, lui, fait l'union morphologique pour le moteur) :
ici on REFUSE le contact par un sommet, plus strict. Un graphe connexe ⇒ vraie limite partagée ⇒ le
moteur unira sans trou. Le chiffre servi (contenance) reste LU du cadastre, jamais recalculé.
"""
from __future__ import annotations

from typing import Optional

from shapely import wkt as shp_wkt
from shapely.geometry.base import BaseGeometry

TOL_CONTIGUITE_M = 0.5  # même seuil que la classification « voisin cadastré ≤ 0,5 m » (IMPLANTATION-4)
_PP_IRREGULIERE = 0.40  # Polsby-Popper sous ce seuil → géométrie « irrégulière » (allongée / dentelée)


def longueur_frontiere_partagee(a: BaseGeometry, b: BaseGeometry) -> float:
    """Longueur (m, CRS 2975) de la frontière commune entre deux polygones. Un contact par un seul
    sommet donne une intersection de dimension 0 (longueur nulle) → non contiguës. On ignore les
    composantes ponctuelles d'une GeometryCollection, on ne somme que les segments (lineaires)."""
    inter = a.boundary.intersection(b.boundary)
    if inter.is_empty:
        return 0.0
    # length vaut 0 pour Point/MultiPoint ; pour (Multi)LineString et GeometryCollection, shapely
    # somme la longueur des seules parties linéaires — exactement ce qu'on veut.
    return float(getattr(inter, "length", 0.0) or 0.0)


def contiguite_graphe(geoms: dict[str, BaseGeometry], *, tol_m: float = TOL_CONTIGUITE_M) -> dict:
    """Graphe d'adjacence des parcelles (arête = frontière partagée > tol_m) + composantes connexes.

    Renvoie {ok, composantes: [[idu,…],…], aretes: [[a,b,longueur],…]}. ok = True ssi une seule
    composante couvre toutes les parcelles (≥ 1). Déterministe (idus triés)."""
    idus = sorted(geoms)
    aretes: list[list] = []
    adj: dict[str, set[str]] = {i: set() for i in idus}
    for ia in range(len(idus)):
        for ib in range(ia + 1, len(idus)):
            a, b = idus[ia], idus[ib]
            lg = longueur_frontiere_partagee(geoms[a], geoms[b])
            if lg > tol_m:
                adj[a].add(b)
                adj[b].add(a)
                aretes.append([a, b, round(lg, 2)])

    vus: set[str] = set()
    composantes: list[list[str]] = []
    for depart in idus:
        if depart in vus:
            continue
        pile, comp = [depart], []
        vus.add(depart)
        while pile:
            n = pile.pop()
            comp.append(n)
            for v in adj[n]:
                if v not in vus:
                    vus.add(v)
                    pile.append(v)
        composantes.append(sorted(comp))

    ok = len(idus) >= 1 and len(composantes) == 1
    return {"ok": ok, "composantes": composantes, "aretes": aretes}


def qualite_geometrique(valide: bool, polsby_popper: Optional[float]) -> str:
    """Étiquette lisible de la qualité géométrique d'une parcelle."""
    if not valide:
        return "invalide"
    if polsby_popper is None:
        return "non mesurée"
    return "irrégulière" if polsby_popper < _PP_IRREGULIERE else "régulière"


MSG_NON_CONTIGUES = (
    "Ces parcelles ne partagent pas de limite commune. Choisissez des parcelles contiguës "
    "ou lancez deux études."
)


def _plu_millesime_insee(session, insee: str) -> Optional[str]:
    from sqlalchemy import text
    try:
        m = session.execute(text("SELECT max(millesime) FROM plu_reglement_extrait WHERE insee = :i"),
                            {"i": insee}).scalar()
        return str(m) if m else None
    except Exception:  # noqa: BLE001
        return None


def _extraits_plu(session, insee: str, zone: Optional[str]) -> dict:
    """ETUDE-V6-4 (item 3) — map {article_ref → (source_url, page_pdf)} pour « Lire l'article » : le lien
    vers le document PLU officiel à la bonne page (table plu_reglement_extrait, zone de l'assiette)."""
    from sqlalchemy import text
    out: dict = {}
    try:
        rows = session.execute(text(
            "SELECT article_ref, source_url, page_pdf FROM plu_reglement_extrait "
            "WHERE insee = :i AND (zone = :z OR zone IS NULL) AND article_ref IS NOT NULL"
        ), {"i": insee, "z": zone}).fetchall()
        for art, url, pg in rows:
            if art and art not in out:
                out[art] = {"source_url": url, "page_pdf": pg}
    except Exception:  # noqa: BLE001
        pass
    return out


def _regles_plu_resume(session, insee: str, commune: Optional[str], zone: Optional[str], cache: dict) -> Optional[list]:
    """ETUDE-V6-2 (Lot 5) / V6-3 (item 2) / V6-4 (item 3) — résumé des règles PLU SERVIES de la zone d'une
    parcelle (hauteur, CES, reculs, pleine terre, + espaces verts / marge si calibrés). Chaque ligne porte
    commune · zone · article · millésime + l'EXTRAIT verbatim (citation) et le lien officiel (source_url) pour
    « Lire l'article ». Seules les règles VALIDÉES et chiffrées (jamais « non vérifié »). Caché par (insee, zone)."""
    if not zone:
        return None
    key = (insee, zone)
    if key not in cache:
        from . import regles as regles_mod
        try:
            rz = regles_mod.charger(insee, zone)
        except Exception:  # noqa: BLE001
            rz = None
        millesime = _plu_millesime_insee(session, insee)
        extraits = _extraits_plu(session, insee, zone)
        lignes = None
        if rz is not None:
            def _ligne(nom, valeur, unite, article, page, citation):
                ex = extraits.get(article or "") or {}
                return {"nom": nom, "valeur": valeur, "unite": unite, "article": article,
                        "page_pdf": page or ex.get("page_pdf"), "commune": commune, "zone": zone,
                        "millesime": millesime, "citation": citation, "source_url": ex.get("source_url")}
            lignes = []
            for nom, r in (("Hauteur à l'égout", rz.hauteur_egout), ("Hauteur au faîtage", rz.hauteur_faitage),
                           ("Emprise au sol (CES)", rz.emprise_ces), ("Recul sur voie", rz.recul_voie),
                           ("Recul séparatives", rz.recul_separatives), ("Pleine terre", rz.pleine_terre)):
                if r and r.validee and r.valeur is not None:
                    lignes.append(_ligne(nom, r.valeur, r.unite, r.article, r.page_pdf, r.citation))
            ev = getattr(rz, "espaces_verts", None)
            if ev and ev.validee and ev.pct is not None:
                lignes.append(_ligne("Espaces verts", ev.pct, "%", ev.article, ev.page_pdf, ev.citation))
            mp = getattr(rz, "marge_plantee", None)
            if mp and mp.validee and mp.largeur_m is not None:
                lignes.append(_ligne("Marge plantée", mp.largeur_m, "m", mp.article, mp.page_pdf, mp.citation))
            lignes = lignes or None
        cache[key] = lignes
    return cache[key]


def valider_parcelles(session, idus: list[str], *, tol_m: float = TOL_CONTIGUITE_M) -> dict:
    """Valide une sélection de 1 à 8 parcelles pour l'étape 1 de l'Étude de faisabilité V6.

    Renvoie un dict sourcé : parcelles[], union{}, contiguite{}, signaux{}, sources{}. Ne conclut
    JAMAIS sur la constructibilité. ValueError si une référence est introuvable ou hors bornes."""
    from sqlalchemy import text

    idus = [i for i in dict.fromkeys(idus) if i]  # dédoublonne en gardant l'ordre
    if not idus:
        raise ValueError("Aucune parcelle sélectionnée.")
    if len(idus) > 8:
        raise ValueError("8 parcelles au maximum pour une même assiette.")

    rows = session.execute(text(
        "SELECT p.id, p.idu, p.commune, p.section, p.numero, p.contenance_m2, "
        "       ST_Area(p.geom_2975) AS aire_geom, ST_Perimeter(p.geom_2975) AS perim_geom, "
        "       ST_IsValid(p.geom_2975) AS valide, ST_AsText(p.geom_2975) AS wkt, "
        "       p.cadastre_disparue_le, "
        "       z.zone_lib, z.zone_fam, "
        "       g.polsby_popper, g.largeur_inscriptible_m "
        "FROM parcels p "
        "LEFT JOIN parcel_zone_plu z ON z.idu = p.idu "
        "LEFT JOIN parcel_geometrie g ON g.idu = p.idu "
        "WHERE p.idu = ANY(:i)"
    ), {"i": idus}).mappings().all()

    trouves = {r["idu"] for r in rows}
    manquantes = [i for i in idus if i not in trouves]
    if manquantes:
        raise ValueError(f"Référence(s) introuvable(s) au cadastre : {', '.join(manquantes)}.")

    par_idu = {r["idu"]: r for r in rows}
    geoms: dict[str, BaseGeometry] = {}
    regles_cache: dict[tuple, Optional[list]] = {}
    parcelles = []
    for idu in idus:
        r = par_idu[idu]
        geom = shp_wkt.loads(r["wkt"]) if r["wkt"] else None
        if geom is not None:
            geoms[idu] = geom
        conten = float(r["contenance_m2"]) if r["contenance_m2"] is not None else None
        aire = round(float(r["aire_geom"]), 1) if r["aire_geom"] is not None else None
        ecart = round(aire - conten, 1) if (aire is not None and conten is not None) else None
        pp = round(float(r["polsby_popper"]), 3) if r["polsby_popper"] is not None else None
        parcelles.append({
            "idu": idu,
            "commune": r["commune"],
            "section": r["section"],
            "numero": r["numero"],
            "reference": f"{r['section']} {r['numero']}",
            "contenance_cadastrale_m2": conten,   # surface de référence retenue (servie)
            "surface_reelle_m2": aire,            # mesurée sur la géométrie
            "ecart_m2": ecart,
            "zone_plu": r["zone_lib"],
            "zone_famille": r["zone_fam"],
            "qualite_geometrique": qualite_geometrique(bool(r["valide"]), pp),
            "polsby_popper": pp,
            "largeur_inscriptible_m": (round(float(r["largeur_inscriptible_m"]), 1)
                                       if r["largeur_inscriptible_m"] is not None else None),
            "disparue_le": r["cadastre_disparue_le"].isoformat() if r["cadastre_disparue_le"] else None,
            # ETUDE-V6-2 (Lot 5) — règles PLU de la zone de CETTE parcelle (sourcées), dès l'étape 1.
            "regles_plu": _regles_plu_resume(session, idu[:5], r["commune"], r["zone_lib"], regles_cache),
        })

    # Union (métriques globales de l'assiette) — surface réelle vs aire cadastrale reportée.
    ids = [par_idu[i]["id"] for i in idus]
    u = session.execute(text(
        "SELECT ST_Area(ST_Union(geom_2975)) AS aire, ST_Perimeter(ST_Union(geom_2975)) AS perim "
        "FROM parcels WHERE id = ANY(:i)"
    ), {"i": ids}).mappings().one()
    aire_cadastrale = sum((p["contenance_cadastrale_m2"] or p["surface_reelle_m2"] or 0.0)
                          for p in parcelles)
    surface_reelle = round(float(u["aire"]), 1) if u["aire"] is not None else None
    union = {
        "surface_reelle_m2": surface_reelle,
        "perimetre_m": round(float(u["perim"]), 1) if u["perim"] is not None else None,
        "aire_cadastrale_m2": round(aire_cadastrale, 1),
        "ecart_m2": (round(surface_reelle - aire_cadastrale, 1)
                     if surface_reelle is not None else None),
        "nb_parcelles": len(parcelles),
    }

    contiguite = contiguite_graphe(geoms, tol_m=tol_m)
    contiguite["tolerance_m"] = tol_m
    contiguite["message"] = None if contiguite["ok"] else MSG_NON_CONTIGUES

    # Signaux (on signale, on ne conclut pas sur la constructibilité).
    communes = {p["commune"] for p in parcelles if p["commune"]}
    zones = {p["zone_plu"] for p in parcelles if p["zone_plu"]}
    ravine = bool(session.execute(text(
        "SELECT EXISTS (SELECT 1 FROM spatial_layers s WHERE s.kind = 'ravine' "
        "AND ST_Intersects(s.geom_2975, (SELECT ST_Union(geom_2975) FROM parcels WHERE id = ANY(:i))))"
    ), {"i": ids}).scalar())
    # Propriétaires présumés : on NE PRÉTEND PAS les connaître ; on ne signale qu'un nombre si la base
    # en porte (table parcelle_personne_morale), sinon « non vérifié ».
    proprios = session.execute(text(
        "SELECT COUNT(DISTINCT siren) FROM parcelle_personne_morale WHERE idu = ANY(:i)"
    ), {"i": idus}).scalar() or 0
    signaux = {
        "communes_differentes": sorted(communes) if len(communes) > 1 else None,
        "zones_differentes": sorted(zones) if len(zones) > 1 else None,
        "ravine_traversante": ravine or None,
        "proprietaires_presumes": int(proprios) if proprios else None,
        "proprietaires_statut": "présumés (personnes morales en base)" if proprios else "non vérifié",
    }

    return {
        "parcelles": parcelles,
        "union": union,
        "contiguite": contiguite,
        "signaux": signaux,
        "sources": _sources(session),
    }


def _sources(session) -> dict:
    """Source + millésime des faits servis (cadastre pour géométrie/contenance, PLU/GPU pour zone)."""
    from sqlalchemy import text

    rows = session.execute(text(
        "SELECT name, category, source_millesime, last_sync_at "
        "FROM data_sources WHERE name IN ('Cadastre (API Carto PCI)', 'Urbanisme PLU/GPU (API Carto)')"
    )).mappings().all()
    out = {}
    for r in rows:
        clef = "cadastre" if r["category"] == "cadastre" else "plu"
        out[clef] = {
            "source": r["name"],
            "millesime": r["source_millesime"],
            "derniere_synchro": r["last_sync_at"].date().isoformat() if r["last_sync_at"] else None,
        }
    return out
