"""Occupation bâtie d'une parcelle — correctif R1 « déjà bâti » (audit 2026-06).

LA BUSE classait comme « opportunités » des parcelles déjà construites (cas vitrine :
BP0571, une résidence entière présentée avec un CA indicatif de 23,5 M€). Ce module
fournit la SOURCE UNIQUE DE VÉRITÉ pour lire l'occupation bâtie d'une parcelle :

- données : couche `spatial_layers.kind='batiment'` (BD TOPO IGN, paginée — la source
  bâtiment open data la plus complète ; OSM sous-cartographie La Réunion) ;
- mesures par parcelle : ratio bâti (surface intersectée / surface parcelle), nombre de
  bâtiments, surface du plus grand bâtiment ;
- classification GRADUÉE (mission R1, phase 9 « ne pas sur-corriger ») :

    vacant                < 5 %        aucun bâti significatif détecté
    peu_bati              5–15 %       présence de bâti à vérifier (PAS de déclassement)
    partiellement_bati    15–30 %      à creuser — occupation à vérifier
    deja_bati_probable    30–50 %      faux positif probable (déclassement fort)
    deja_bati             ≥ 50 %       faux positif probable
    ensemble_bati         ≥3 bâtiments OU un grand bâtiment (≥400 m²), dès 15 % de
                          couverture → faux positif probable (résidences/équipements
                          dont le ratio reste sous 30 % à cause des espaces communs —
                          c'est exactement le cas BP0571)

L'information n'est JAMAIS supprimée : le motif est affiché (« déjà bâtie probable :
X % de la surface intersecte N bâtiments »), le score brut reste visible, et une
parcelle GRANDE et PEU bâtie est signalée « restructuration potentielle » au lieu
d'être jetée. Cœur pur + une requête batch ; aucune modification du scoring.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

# ── Seuils (mission R1 §3) — M129 P1.4 : SORTIS DU DUR (config/seuils_geometrie.yaml,
# section `bati`, valeurs héritées à l'identique ; repli sur les défauts historiques si la
# config est absente — base de test nue). Un critère, un endroit : classify() reste le juge.
def _seuils_cfg() -> dict:
    try:
        from . import config as _cfg
        return _cfg.seuils_geometrie().get("bati", {})
    except Exception:  # noqa: BLE001 — config absente → défauts historiques
        return {}


_S = _seuils_cfg()
RATIO_INFO = float(_S.get("ratio_info", 0.05))            # en deçà : vacant
RATIO_LEGER = float(_S.get("ratio_leger", 0.15))          # 5-15 % : information
RATIO_SIGNIFICATIF = float(_S.get("ratio_significatif", 0.30))   # 15-30 % : à creuser
RATIO_DEJA_BATI = float(_S.get("ratio_deja_bati", 0.50))  # ≥ 50 % : déjà bâtie
ENSEMBLE_MIN_BATIMENTS = int(_S.get("ensemble_min_batiments", 3))
GRAND_BATIMENT_M2 = float(_S.get("grand_batiment_m2", 400.0))
ENSEMBLE_MIN_RATIO = float(_S.get("ensemble_min_ratio", 0.15))
RESTRUCTURATION_MIN_M2 = float(_S.get("restructuration_min_m2", 5000.0))

SOURCE = "BD TOPO IGN (bâtiments)"
CONFIANCE = "haute"          # IGN cartographie l'exhaustif ; OSM resterait « moyenne »


def classify(ratio: float | None, count: int, max_m2: float, surface_m2: float | None) -> dict:
    """Classification graduée → {code, label, declasse, motif}.

    `declasse` : None | "a_creuser" | "faux_positif" — consommé par apply_declassement.
    `label`/`motif` : wording prudent affiché tel quel (fiche, exports, carte)."""
    r = ratio or 0.0
    pct = round(100 * r)
    if r >= RATIO_DEJA_BATI:
        return {"code": "deja_bati", "declasse": "faux_positif",
                "label": "Parcelle déjà bâtie",
                "motif": f"déjà bâtie : {count} bâtiment(s) couvrant {pct} % de la parcelle (BD TOPO)"}
    if r >= RATIO_SIGNIFICATIF:
        return {"code": "deja_bati_probable", "declasse": "faux_positif",
                "label": "Parcelle déjà bâtie probable",
                "motif": f"déjà bâtie probable : {pct} % de la surface intersecte {count} bâtiment(s) (BD TOPO)"}
    if r >= ENSEMBLE_MIN_RATIO and (count >= ENSEMBLE_MIN_BATIMENTS or max_m2 >= GRAND_BATIMENT_M2):
        what = (f"{count} bâtiments" if count >= ENSEMBLE_MIN_BATIMENTS
                else f"un grand bâtiment de {max_m2:.0f} m²")
        return {"code": "ensemble_bati", "declasse": "faux_positif",
                "label": "Ensemble bâti détecté (résidence / équipement)",
                "motif": f"ensemble bâti : {what} couvrant {pct} % de la parcelle (BD TOPO)"}
    if r >= RATIO_LEGER:
        return {"code": "partiellement_bati", "declasse": "a_creuser",
                "label": "Parcelle partiellement bâtie",
                "motif": f"bâti significatif : {pct} % de la surface intersecte des bâtiments (BD TOPO) — occupation à vérifier"}
    if r >= RATIO_INFO:
        restruct = bool(surface_m2 and surface_m2 >= RESTRUCTURATION_MIN_M2)
        return {"code": "peu_bati", "declasse": None,
                "label": ("Peu bâtie — restructuration potentielle (grande parcelle)"
                          if restruct else "Présence de bâti à vérifier"),
                "motif": None}
    return {"code": "vacant", "declasse": None,
            "label": "Aucun bâti significatif détecté", "motif": None}


def layer_available(session: Session) -> bool:
    return bool(session.execute(
        text("SELECT EXISTS(SELECT 1 FROM spatial_layers WHERE kind='batiment')")).scalar())


def stats_batch(session: Session, parcel_ids: list[int]) -> dict[int, dict]:
    """Ratio/nb/plus grand bâtiment par parcelle, EN BATCH (requête indexée geom_2975).

    Le ratio est borné à 1.0 (des bâtiments BD TOPO voisins peuvent se chevaucher en
    limite). Renvoie {} pour chaque parcelle sans bâti intersecté."""
    if not parcel_ids:
        return {}
    out: dict[int, dict] = {pid: {"bati_ratio": 0.0, "bati_count": 0, "bati_max_m2": 0.0}
                            for pid in parcel_ids}
    rows = session.execute(text(
        """
        SELECT p.id,
               LEAST(1.0, SUM(ST_Area(ST_Intersection(b.geom_2975, p.geom_2975)))
                          / NULLIF(ST_Area(p.geom_2975), 0)) AS ratio,
               COUNT(*) FILTER (WHERE ST_Area(ST_Intersection(b.geom_2975, p.geom_2975)) >= 10) AS nb,
               MAX(ST_Area(ST_Intersection(b.geom_2975, p.geom_2975))) AS max_m2
        FROM parcels p
        JOIN spatial_layers b ON b.kind = 'batiment' AND ST_Intersects(b.geom_2975, p.geom_2975)
        WHERE p.id = ANY(:ids)
        GROUP BY p.id
        """), {"ids": list(parcel_ids)}).all()
    for pid, ratio, nb, max_m2 in rows:
        out[pid] = {"bati_ratio": float(ratio or 0.0), "bati_count": int(nb or 0),
                    "bati_max_m2": float(max_m2 or 0.0)}
    return out


def fiche_block(session: Session, parcel_id: int, surface_m2: float | None) -> dict:
    """Bloc « Occupation actuelle / bâti détecté » de la fiche (et des exports).

    Toujours présent : si la couche bâtiments n'est pas ingérée, on le DIT
    (« non vérifiée ») au lieu d'afficher un faux « vacant »."""
    if not layer_available(session):
        return {"disponible": False, "source": SOURCE, "confiance": "indisponible",
                "label": "Couche bâtiments non ingérée — occupation non vérifiée",
                "code": "inconnu", "ratio_pct": None, "nb_batiments": None,
                "plus_grand_m2": None}
    st = stats_batch(session, [parcel_id]).get(parcel_id, {})
    ratio = st.get("bati_ratio", 0.0)
    count = st.get("bati_count", 0)
    max_m2 = st.get("bati_max_m2", 0.0)
    cls = classify(ratio, count, max_m2, surface_m2)
    return {"disponible": True, "source": SOURCE, "confiance": CONFIANCE,
            "code": cls["code"], "label": cls["label"],
            "ratio_pct": round(100 * ratio), "nb_batiments": count,
            "plus_grand_m2": round(max_m2) if max_m2 else 0}


# DONNEES-2 — les 15 classes CoSIA (IGN 20 cm) regroupées en 3 parts pour la fiche §2 Terrain.
# Imperméabilisé = surfaces qui SCELLENT le sol (bâti, revêtement imperméable, piscine, serre) ;
# végétalisé/boisé = végétation vivante (feuillu/conifère boisés + broussaille/pelouse/culture/vigne) ;
# sol nu = terre nue. Hors des 3 (ni imperméable, ni végétal, ni terre) : « Zone perméable » (minéral
# perméable), « Surface eau », « Neige » — les trois parts ne somment donc pas 100 % (résidu dit honnête).
_COSIA_IMPERMEABLE = frozenset({"Bâtiment", "Zone imperméable", "Piscine", "Serre"})
_COSIA_VEGETAL = frozenset({"Feuillu", "Conifère", "Broussaille", "Pelouse", "Culture", "Vigne"})
_COSIA_SOL_NU = frozenset({"Sol nu", "Terre labourée"})


def _cosia_couverture(session: Session, idu: str, surface: float | None) -> dict | None:
    """DONNEES-2 — couverture du sol CoSIA agrégée par parcelle : part imperméabilisée / végétalisée-
    boisée / sol nu = Σ(surface de classe CoSIA) / contenance cadastrale. COMPLÈTE OCS GE (donnée
    d'îlot, part artificialisée) sans la recouper : CoSIA mesure la parcelle elle-même à 20 cm, et
    « imperméabilisé » n'est pas « artificialisé ». Table absente ou parcelle hors couverture → None."""
    if not surface or surface <= 0:
        return None
    try:
        if not session.execute(text("SELECT to_regclass('parcel_cosia_couverture')")).scalar():
            return None
        rows = session.execute(text(
            "SELECT classe, m2 FROM parcel_cosia_couverture WHERE idu = :i"), {"i": idu}).mappings().all()
    except Exception:  # noqa: BLE001 — CoSIA ne casse jamais le tiroir « Le bien »
        session.rollback()
        return None
    if not rows:
        return None
    imper = veg = nu = 0.0
    for r in rows:
        c, m2 = r["classe"], float(r["m2"] or 0.0)
        if c in _COSIA_IMPERMEABLE:
            imper += m2
        elif c in _COSIA_VEGETAL:
            veg += m2
        elif c in _COSIA_SOL_NU:
            nu += m2
    return {
        "part_impermeabilisee_pct": round(100.0 * imper / surface, 1),
        "part_vegetalisee_boisee_pct": round(100.0 * veg / surface, 1),
        "part_sol_nu_pct": round(100.0 * nu / surface, 1),
        "source": "CoSIA (IGN, détection par IA, 20 cm)",
    }


def le_bien_block(session: Session, idu: str) -> dict | None:
    """FICHE-1 lot 1 — bloc « Le bien » : le bâtiment EXISTANT de la parcelle, une fois pour la
    fiche (le tiroir consomme ce producteur unique, aucun calcul au front).

    Sert : emprise bâtie au sol (BD TOPO au sol + CoSIA — l'emprise détectée l'emporte), nombre
    de bâtiments (BD TOPO), hauteur du bâti (potentiel._hauteur_bati_m), surface au sol libre
    restante (surface parcelle − emprise), et la nature/pente du toit (LiDAR HD, cache seul).

    Trois états, jamais confondus : servie · « non déterminée » (la couche ne dit pas) · « non
    calculée » (chaîne en échec). Renvoie None si RIEN n'est évaluable (couche bâtiments non
    ingérée) → le front OMET le tiroir (jamais un bloc creux)."""
    head = session.execute(text(
        "SELECT id, round(surface_m2) AS surface_m2 FROM parcels WHERE idu = :i"),
        {"i": idu}).mappings().first()
    if head is None:
        return None
    # Couche bâtiments absente → on ne peut RIEN affirmer sur le bâti : tiroir omis (pas un faux « nu »).
    if not layer_available(session):
        return None
    pid = head["id"]
    surface = float(head["surface_m2"]) if head["surface_m2"] is not None else None
    bloc = fiche_block(session, pid, surface)
    nb = bloc.get("nb_batiments")
    # Emprise au sol du bâti = empreinte VECTEUR BD TOPO (SUM des intersections) — cohérente avec
    # le nombre de bâtiments. CoSIA (raster) sur-détecte à la maille parcelle (surfaces
    # imperméables non bâties) : on ne l'utilise PAS comme emprise, on le SERT à part comme
    # « détecté, non cartographié » quand BD TOPO ne voit rien mais que CoSIA en signale (le
    # front le dit honnêtement, jamais mélangé à l'emprise).
    # RECETTE-5 (V21) — GARDE contre l'emprise impossible (ex. 302 m² sur une parcelle de 273 m²).
    # La cause n'était PAS un débord sur la voisine : c'était le SUM des intersections qui DOUBLE-COMPTE
    # la zone où deux polygones bâtiment de la BD TOPO se CHEVAUCHENT (mur mitoyen, bâtiment scindé en
    # plusieurs faces qui se recouvrent). Mesuré sur 97418000AD0191 : SUM = 301,7 m² alors que l'UNION
    # réelle des empreintes = 150,8 m² (chevauchement de 150,8 m²), bien dans les 272,7 m² de la parcelle.
    # ST_Union fusionne les empreintes AVANT de mesurer l'aire : plus de double-compte, et le résultat est
    # naturellement borné par la géométrie de la parcelle (une intersection ne sort jamais de la parcelle).
    emprise_bdtopo = session.execute(text(
        "SELECT COALESCE(ST_Area(ST_Union(ST_Intersection(b.geom_2975, p.geom_2975))), 0) "
        "FROM spatial_layers b JOIN parcels p ON p.id = :pid "
        "WHERE b.kind = 'batiment' AND ST_Intersects(b.geom_2975, p.geom_2975)"),
        {"pid": pid}).scalar()
    emprise = float(emprise_bdtopo or 0.0)
    emprise_m2 = round(emprise) if emprise > 0 else 0
    emprise_cosia = session.execute(text(
        "SELECT emprise_cosia_m2 FROM parcel_bati_revele WHERE idu = :i"), {"i": idu}).scalar()
    # CoSIA « détecté non cartographié » : seulement s'il dépasse nettement BD TOPO (≥ 50 m² de plus).
    cosia_m2 = round(float(emprise_cosia)) if emprise_cosia and float(emprise_cosia) > emprise + 50 else None
    from .faisabilite.potentiel import _hauteur_bati_m
    hauteur = _hauteur_bati_m(session, pid)
    surface_libre = (max(0, round(surface - emprise)) if surface is not None else None)
    from . import solaire_toiture
    toit = solaire_toiture.toiture_depuis_cache(session, idu)
    # RECETTE-9 T9 — POINT UNIQUE de la hauteur : quand le LiDAR HD a été mesuré sur cette parcelle,
    # la hauteur passe d'`estimé` (BD TOPO déclaré) à `sourcé` (faîtage ET égout MESURÉS). Sinon repli
    # BD TOPO. L'égout (bord de toit) — que BD TOPO ne donne pas — est servi à part (décide la surélévation).
    from .faisabilite.hauteur_lidar import hauteur_lidar_servie
    lid = hauteur_lidar_servie(session, idu)
    hauteur_bati = (lid["faitage_m"] if lid else (round(float(hauteur), 1) if hauteur is not None else None))
    # REPARATIONS-1 lot 4 — L'IDENTITÉ des bâtiments : le RNB ID de chaque bâtiment de la
    # parcelle (RNB actifs dont l'emprise recoupe la parcelle, du plus grand recouvrement au
    # plus petit), avec le lien officiel. Table absente (base sans RNB) → liste vide, jamais
    # un tiroir cassé. C'est la pièce qui relie BD TOPO, LiDAR et RNB au MÊME bâtiment.
    rnb: list[dict] = []
    try:
        if session.execute(text("SELECT to_regclass('rnb_batiments')")).scalar():
            rnb = [{"rnb_id": r["rnb_id"], "statut": r["statut"],
                    "lien": f"https://rnb.beta.gouv.fr/batiments/{r['rnb_id']}"}
                   for r in session.execute(text(
                       "SELECT r.rnb_id, r.statut FROM rnb_batiments r "
                       "JOIN parcels p ON p.id = :pid "
                       "WHERE r.is_active AND r.shape_2975 && p.geom_2975 "
                       "  AND ST_Intersects(r.shape_2975, p.geom_2975) "
                       "ORDER BY ST_Area(ST_Intersection(r.shape_2975, p.geom_2975)) DESC "
                       "LIMIT 12"), {"pid": pid}).mappings()]
    except Exception:  # noqa: BLE001 — le RNB ne casse jamais le tiroir « Le bien »
        session.rollback()
        rnb = []
    # SOURCES-2 lot 3 — BAN PLUS : le lien adresse ↔ bâtiment ↔ parcelle (IGN). Dit combien
    # d'adresses officielles desservent le bâti de la parcelle (clé de jointure ID-RNB en base).
    # Table absente → None, jamais un tiroir cassé.
    adresses_bati = None
    try:
        if session.execute(text("SELECT to_regclass('ban_plus_liens')")).scalar():
            row = session.execute(text(
                "SELECT count(*) AS liens, count(DISTINCT id_adr) AS adresses, "
                "count(DISTINCT id_bat) AS batiments "
                "FROM ban_plus_liens WHERE idu = :i"), {"i": idu}).mappings().first()
            if row and row["liens"]:
                adresses_bati = {"liens": int(row["liens"]), "adresses": int(row["adresses"]),
                                 "batiments": int(row["batiments"]),
                                 "source": "BAN PLUS (IGN) — lien adresse ↔ bâtiment"}
    except Exception:  # noqa: BLE001 — BAN PLUS ne casse jamais le tiroir « Le bien »
        session.rollback()
        adresses_bati = None
    # REPARATIONS-1 lot 5 — l'usage du sol et l'artificialisation OFFICIELS (OCS GE, précalcul
    # parcel_ocsge). Donnée d'ÎLOT : la fiche dit « d'après OCS GE », jamais la précision
    # cadastrale. Aucun effet score. Table absente → None, jamais un tiroir cassé.
    ocsge = None
    try:
        if session.execute(text("SELECT to_regclass('parcel_ocsge')")).scalar():
            row = session.execute(text(
                "SELECT part_artif_pct, cs_dominant, us_dominant, millesime "
                "FROM parcel_ocsge WHERE idu = :i"), {"i": idu}).mappings().first()
            if row:
                ocsge = {"part_artif_pct": (round(float(row["part_artif_pct"]), 1)
                                            if row["part_artif_pct"] is not None else None),
                         "cs_dominant": row["cs_dominant"], "us_dominant": row["us_dominant"],
                         "millesime": row["millesime"],
                         "source": "OCS GE (IGN) — donnée d'îlot, matrice du décret 2023-1096"}
    except Exception:  # noqa: BLE001
        session.rollback()
        ocsge = None
    # DONNEES-2 — CoSIA COMPLÈTE OCS GE : la couverture du sol de la PARCELLE mesurée à 20 cm
    # (parcel_cosia_couverture), agrégée en 3 parts — imperméabilisée / végétalisée-boisée / sol nu.
    # Ni remplacement ni doublon d'OCS GE (donnée d'ÎLOT, part ARTIFICIALISÉE) : imperméabilisé n'est
    # pas artificialisé, et la maille est la parcelle elle-même. Table absente → None.
    cosia_couverture = _cosia_couverture(session, idu, surface)
    return {
        "disponible": True,
        "code": bloc.get("code"), "occupation_label": bloc.get("label"),
        "emprise_batie_m2": emprise_m2, "emprise_source": "BD TOPO IGN",
        "cosia_detecte_m2": cosia_m2,   # None sauf sur-détection CoSIA hors BD TOPO (dit à part)
        "nb_batiments": nb,
        "hauteur_bati_m": hauteur_bati,
        # RECETTE-9 T9 — faîtage/égout MESURÉS + nature (« sourcé » LiDAR / « estimé » BD TOPO).
        "hauteur_faitage_m": (lid["faitage_m"] if lid else None),
        "hauteur_egout_m": (lid["egout_m"] if lid else None),
        "hauteur_nature": ("sourcé" if lid else ("estimé" if hauteur is not None else None)),
        "adresses_bati": adresses_bati,   # SOURCES-2 lot 3 — BAN PLUS (None si table absente)
        # RECETTE-11 A3 — la date de survol servie avec la mesure (jamais une mesure sans date).
        "hauteur_survol": (lid.get("survol") if lid else None),
        "hauteur_source": (lid["source"] if lid else ("BD TOPO® (hauteur déclarée)" if hauteur is not None else None)),
        "surface_libre_m2": surface_libre,
        "surface_parcelle_m2": round(surface) if surface is not None else None,
        "toit": toit,          # None = toit non encore relevé (LiDAR non chauffé), sinon 3 états U5
        # REPARATIONS-1 lot 4 — identifiants RNB des bâtiments de la parcelle (lien officiel).
        "rnb": rnb,
        # REPARATIONS-1 lot 5 — occupation du sol / artificialisation d'après OCS GE (îlot).
        "ocsge": ocsge,
        # DONNEES-2 — couverture du sol CoSIA 20 cm (imperméabilisée / végétalisée-boisée / sol nu), en
        # complément d'OCS GE ; None si table absente ou parcelle hors couverture CoSIA.
        "cosia_couverture": cosia_couverture,
        "source_bati": "BD TOPO® V3 (IGN) + CoSIA 2025",
    }
