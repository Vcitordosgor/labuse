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
    emprise_bdtopo = session.execute(text(
        "SELECT COALESCE(SUM(ST_Area(ST_Intersection(b.geom_2975, p.geom_2975))), 0) "
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
    return {
        "disponible": True,
        "code": bloc.get("code"), "occupation_label": bloc.get("label"),
        "emprise_batie_m2": emprise_m2, "emprise_source": "BD TOPO IGN",
        "cosia_detecte_m2": cosia_m2,   # None sauf sur-détection CoSIA hors BD TOPO (dit à part)
        "nb_batiments": nb,
        "hauteur_bati_m": round(float(hauteur), 1) if hauteur is not None else None,
        "surface_libre_m2": surface_libre,
        "surface_parcelle_m2": round(surface) if surface is not None else None,
        "toit": toit,          # None = toit non encore relevé (LiDAR non chauffé), sinon 3 états U5
        "source_bati": "BD TOPO® V3 (IGN) + CoSIA 2025",
    }
