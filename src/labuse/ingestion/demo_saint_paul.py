"""Jeu de démonstration — commune pilote Saint-Paul (synthétique).

Le réseau sortant étant restreint ici, on ne peut pas ingérer le vrai cadastre.
Ce module construit un échantillon SYNTHÉTIQUE mais réaliste (géométries ancrées
sur Saint-Paul, en 4326) qui exerce TOUTE la cascade : opportunité, à creuser,
faux positifs, exclusions. Il rend le moteur exécutable et testable de bout en bout.

⚠ Données fictives : aucune valeur juridique. À remplacer par les vrais
connecteurs (cadastre PCI, GPU, Géorisques, SAR, SAFER…) dès qu'un accès réseau
est disponible.
"""
from __future__ import annotations

import json

from pyproj import Transformer
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from ..models import DataSource, IngestionRun
from . import seed_sources

# Saint-Paul (La Réunion) — point d'ancrage approximatif (lon, lat).
ANCHOR_LON, ANCHOR_LAT = 55.270, -21.010
W, H, STEP = 40.0, 50.0, 100.0  # parcelle 40×50 m, pas de 100 m

KIND_SOURCE = {
    "water": "BD TOPO IGN",
    "voirie": "BD TOPO IGN",
    "parc_national": "Parc National de La Réunion (INPN)",
    "foret_publique": "Forêts publiques (ONF)",
    "sar": "SAR Réunion (PEIGEO)",
    "plu_gpu_zone": "Urbanisme PLU/GPU (API Carto)",
    "safer": "Zonage SAFER (DAAF)",
    "ppr": "Géorisques",
    "georisque_alea": "Géorisques",
    "ocs_ge": "OCS GE (IGN)",
    "osm_faux_positif": "OpenStreetMap / Overpass",
    "pente": "RGE ALTI (altimétrie)",
    "potentiel_foncier": "data.regionreunion.com — Potentiel foncier",
}

# idu 14 car. = INSEE(5) + préfixe(3) + section(2) + numéro(4)
def _idu(insee: str, num: int) -> str:
    return f"{insee}000AB{num:04d}"


# Définition des parcelles : zonage propre + situation testée.
# `pm` (F2) : ligne parcelle_personne_morale DÉTERMINISTE — groupe DGFiP public {1,2,3,4,9} → foncier_public
# HARD_EXCLUDE ; groupe privé → acquérable (PASS). Le seed contrôle ainsi FoncierPublic (plus de fuite).
PARCELS = [
    dict(num=1, plu="U",  sar="territoire_urbain", ocs="artificialise",
         pm=dict(groupe=6, label="Sociétés (SCI, SARL…)", denom="SCI DÉMO SAINT-PAUL"),
         case="opportunité (U, potentiel, marché, permis, morale PRIVÉE — acquérable)"),
    dict(num=2, plu="Ab", sar="espace_agricole",   ocs="agricole",      safer=True, case="faux positif (zone Ab agricole — non constructible au PLU + SAFER)"),
    dict(num=3, plu="Ub", sar="territoire_urbain", ocs="naturel",       ppr_rouge=True, case="exclue (PPR zone rouge = degré INTERDICTION)"),
    dict(num=4, plu="N",  sar="espace_naturel",    ocs="naturel",       case="faux positif (SAR espace naturel > PLU)"),
    dict(num=5, plu="U",  sar="territoire_urbain", ocs="artificialise", parc_coeur=True, case="exclue (cœur Parc National)"),
    dict(num=6, plu="U",  sar="territoire_urbain", ocs="artificialise", osm_cemetery=True, case="faux positif (cimetière OSM)"),
    dict(num=7, plu="U",  sar="territoire_urbain", ocs="artificialise", indivision=True, case="à creuser (indivision)"),
    dict(num=8, plu="Ua", sar="territoire_urbain", ocs="artificialise", parc_adhesion=True, alea_moyen=True, case="à creuser (adhésion Parc + aléa)"),
    # F2 : parcelle volontairement PUBLIQUE (Commune, DGFiP groupe 4) → foncier_public HARD_EXCLUDE.
    # Démontre l'exclusion « domaine public non acquérable » de façon déterministe.
    dict(num=9, plu="U",  sar="territoire_urbain", ocs="artificialise",
         pm=dict(groupe=4, label="Commune", denom="COMMUNE DE SAINT-PAUL"),
         case="exclue (propriété publique — Commune, DGFiP groupe 4)"),
]


class _Geo:
    def __init__(self):
        self.to_m = Transformer.from_crs(4326, 2975, always_xy=True)
        self.to_wgs = Transformer.from_crs(2975, 4326, always_xy=True)
        self.x0, self.y0 = self.to_m.transform(ANCHOR_LON, ANCHOR_LAT)

    def rect_wkt(self, xoff: float, yoff: float, w: float, h: float) -> str:
        x, y = self.x0 + xoff, self.y0 + yoff
        corners_m = [(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)]
        pts = [self.to_wgs.transform(cx, cy) for cx, cy in corners_m]
        return "POLYGON((" + ", ".join(f"{lon} {lat}" for lon, lat in pts) + "))"

    def point_lonlat(self, xoff: float, yoff: float) -> tuple[float, float]:
        return self.to_wgs.transform(self.x0 + xoff, self.y0 + yoff)


_RESET_TABLES = [
    "cascade_results", "parcel_evaluations", "parcel_source_results", "parcel_signals",
    "parcel_feedback", "parcels", "spatial_layers", "dvf_mutations", "sitadel_permits", "ingestion_runs",
    # F2 : le seed CONTRÔLE parcelle_personne_morale (sinon FoncierPublic fuit d'un seed à l'autre).
    "parcelle_personne_morale",
]


def reset_demo(session: Session) -> None:
    session.execute(text("TRUNCATE " + ", ".join(_RESET_TABLES) + " RESTART IDENTITY CASCADE"))


def seed_demo(session: Session, commune_insee: str = "97415", commune_name: str = "Saint-Paul") -> dict:
    # Catalogue de sources requis (pour résoudre data_source_id).
    if session.query(DataSource).count() == 0:
        seed_sources.seed(session)
    src_id = {name: sid for (name, sid) in session.execute(select(DataSource.name, DataSource.id)).all()}

    reset_demo(session)
    g = _Geo()

    run = IngestionRun(commune=commune_name, status="ok", parcels_count=len(PARCELS))
    session.add(run)
    session.flush()

    def add_layer(kind, subtype, name, wkt, attrs=None):
        session.execute(
            text(
                """INSERT INTO spatial_layers (kind, subtype, name, geom, attrs, data_source_id, commune, ingestion_run_id)
                   VALUES (:k,:s,:n, ST_GeomFromText(:w,4326), CAST(:a AS jsonb), :sid, :c, :run)"""
            ),
            {"k": kind, "s": subtype, "n": name, "w": wkt, "a": json.dumps(attrs or {}),
             "sid": src_id.get(KIND_SOURCE.get(kind)), "c": commune_name, "run": run.id},
        )

    # ── Couches "ambiantes" (présentes partout → familles non-UNKNOWN) ──
    span = STEP * len(PARCELS)
    add_layer("pente", "calcul", "Pente RGE ALTI", g.rect_wkt(-50, -50, span + 100, H + 200), {"slope_pct": 12})
    add_layer("voirie", "route", "Voirie BD TOPO", g.rect_wkt(-10, -6, span, 8))           # touche toutes les parcelles
    add_layer("water", "ravine", "Ravine (hors parcelles)", g.rect_wkt(-300, -300, 50, 50))
    add_layer("foret_publique", "domaniale", "Forêt domaniale (hors parcelles)", g.rect_wkt(span + 200, 0, 50, 50))

    # ── Parcelles + overlays propres (PLU / SAR / OCS) + contraintes ciblées ──
    parcel_ids: dict[int, int] = {}
    for i, p in enumerate(PARCELS):
        xoff = i * STEP
        wkt = g.rect_wkt(xoff, 0, W, H)
        idu = _idu(commune_insee, p["num"])
        pid = session.execute(
            text(
                """INSERT INTO parcels (idu, commune, section, numero, geom, surface_m2, centroid, bbox, ingestion_run_id)
                   VALUES (:idu,:c,'AB',:num,
                           ST_GeomFromText(:w,4326),
                           ST_Area(ST_Transform(ST_GeomFromText(:w,4326),2975)),
                           ST_Centroid(ST_GeomFromText(:w,4326)),
                           ST_Envelope(ST_GeomFromText(:w,4326)), :run)
                   RETURNING id"""
            ),
            {"idu": idu, "c": commune_name, "num": str(p["num"]), "w": wkt, "run": run.id},
        ).scalar_one()
        parcel_ids[p["num"]] = pid

        # overlays propres couvrant exactement la parcelle
        add_layer("plu_gpu_zone", p["plu"], f"Zone PLU {p['plu']}", wkt)
        add_layer("sar", p["sar"], f"SAR {p['sar']}", g.rect_wkt(xoff - 2, -2, W + 4, H + 4))
        add_layer("ocs_ge", p["ocs"], f"OCS {p['ocs']}", wkt)

        # propriétaire personne morale DÉTERMINISTE (F2) — pilote foncier_public
        if p.get("pm"):
            _add_pm(session, idu, p["pm"])

        big = g.rect_wkt(xoff - 5, -5, W + 10, H + 10)  # contrainte englobant la parcelle
        if p.get("ppr_rouge"):
            # F1 : subtype = DEGRÉ réel du PPR ZONÉ DEAL. « zone rouge » = 'INTERDICTION'
            # (∈ ppr_red_subtypes de config/cascade_rules.yaml) → RisquesLayer HARD_EXCLUDE.
            add_layer("ppr", "INTERDICTION", "PPR zone rouge (degré INTERDICTION)", big)
        if p.get("parc_coeur"):
            add_layer("parc_national", "coeur", "Cœur Parc National", big)
        if p.get("parc_adhesion"):
            add_layer("parc_national", "adhesion", "Aire d'adhésion Parc National", big)
        if p.get("safer"):
            add_layer("safer", "preemption", "Zonage SAFER", big)
        if p.get("alea_moyen"):
            add_layer("georisque_alea", "mvt_terrain", "Aléa mouvement de terrain", big,
                      {"niveau": "moyen", "type": "mouvement de terrain"})
        if p.get("osm_cemetery"):
            add_layer("osm_faux_positif", "cemetery", "Cimetière (OSM)", big)
        if p["num"] == 1:
            add_layer("potentiel_foncier", "ilot", "Îlot potentiel foncier Région", big)

    # ── DVF : nuage de mutations au centre (→ marché liquide pour les promues) ──
    center = (len(PARCELS) // 2) * STEP
    dvf_pts = [(center + dx, 20 + dy, val) for (dx, dy, val) in
               [(-40, 0, 285000), (10, 10, 312000), (60, -10, 298000), (-10, 40, 305000),
                (30, 30, 264000), (-60, 20, 321000)]]
    for k, (dx, dy, val) in enumerate(dvf_pts):
        lon, lat = g.point_lonlat(dx, dy)
        session.execute(
            text(
                """INSERT INTO dvf_mutations (mutation_id, date_mutation, valeur_fonciere, type_local, surface_terrain,
                                              nature_mutation, commune, geom, raw)
                   VALUES (:mid, now() - interval '1 year', :val, 'Maison', 420, 'Vente', :c,
                           ST_SetSRID(ST_MakePoint(:lon,:lat),4326), CAST(:raw AS jsonb))"""
            ),
            {"mid": f"DVF-DEMO-{k}", "val": val, "c": commune_name, "lon": lon, "lat": lat,
             "raw": json.dumps({"synthetique": True})},
        )

    # ── SITADEL : un permis RATTACHÉ par IDU (P1), un permis de ZONE (proche P2) ──
    session.execute(
        text(
            """INSERT INTO sitadel_permits (permit_id, type, date, idu_codes, commune, geom, raw)
               VALUES (:pid,'PC', now() - interval '5 months', CAST(:idus AS jsonb), :c, NULL, CAST(:raw AS jsonb))"""
        ),
        {"pid": "PC974-DEMO-1", "idus": json.dumps([_idu(commune_insee, 1)]), "c": commune_name,
         "raw": json.dumps({"synthetique": True, "rattachement": "IDU"})},
    )
    lon, lat = g.point_lonlat(1 * STEP + 10, 25)  # ~proche P2
    session.execute(
        text(
            """INSERT INTO sitadel_permits (permit_id, type, date, idu_codes, commune, geom, raw)
               VALUES (:pid,'PC', now() - interval '8 months', CAST(:idus AS jsonb), :c,
                       ST_SetSRID(ST_MakePoint(:lon,:lat),4326), CAST(:raw AS jsonb))"""
        ),
        {"pid": "PC974-DEMO-2", "idus": json.dumps([]), "c": commune_name, "lon": lon, "lat": lat,
         "raw": json.dumps({"synthetique": True, "rattachement": "zone"})},
    )

    # ── Propriétaire (Fichiers fonciers — manuel/mock) : P1 morale, P7 indivision ──
    ff_id = src_id["Fichiers fonciers (Cerema)"]
    _add_owner(session, parcel_ids[1], ff_id, {"personne_morale": True, "categorie": "SCI", "indivision": False},
               "Propriétaire personne morale (SCI) — acquérable.")
    _add_owner(session, parcel_ids[7], ff_id, {"personne_morale": False, "nb_droits_propriete": 7, "indivision": True},
               "Indivision successorale : 7 droits de propriété sur le compte.")

    session.flush()
    return {"ingestion_run_id": run.id, "parcels": len(PARCELS), "parcel_ids": parcel_ids}


def _add_pm(session: Session, idu: str, pm: dict) -> None:
    """F2 : ligne parcelle_personne_morale déterministe (source `owner_pm` de FoncierPublic).
    `groupe` DGFiP : ∈ {1,2,3,4,9} = public (→ HARD_EXCLUDE), sinon PM privée (→ acquérable)."""
    session.execute(
        text(
            """INSERT INTO parcelle_personne_morale (idu, groupe, groupe_label, denomination, source, date_import)
               VALUES (:idu, :g, :gl, :d, 'demo', now())"""
        ),
        {"idu": idu, "g": pm["groupe"], "gl": pm.get("label"), "d": pm.get("denom")},
    )


def _add_owner(session: Session, parcel_id: int, source_id: int, payload: dict, summary: str) -> None:
    session.execute(
        text(
            """INSERT INTO parcel_source_results (parcel_id, data_source_id, status, raw_payload, summary, fetched_at)
               VALUES (:pid,:sid,'repondu', CAST(:raw AS jsonb), :sum, now())"""
        ),
        {"pid": parcel_id, "sid": source_id, "raw": json.dumps(payload), "sum": summary},
    )
