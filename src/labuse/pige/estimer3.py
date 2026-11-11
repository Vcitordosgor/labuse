#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ESTIMER-3 (fix/estimer-3) — une estimation qui se resserre, et qui le prouve.

POINT UNIQUE de l'outil « Estimer un bien » en TROIS TEMPS (maquette nov-2026/11-estimer-3-temps) :

  1. SANS RIEN SAISIR — LABUSE sert ce qu'il a MESURÉ (terrain, emprise bâtie, niveaux LiDAR, surface
     habitable estimée, piscine, pente, zone) et une estimation issue des ventes de biens qui
     RESSEMBLENT au bien (même type, surface/terrain proches, distance, ancienneté — pondération par
     RESSEMBLANCE), pas de toutes les ventes du secteur. La fourchette est large, et l'écran dit pourquoi.
  2. LES QUESTIONS — seules les caractéristiques dont le GAIN est MESURÉ au banc no-leak sont posées
     (surface habitable, nombre de pièces). Pré-remplies quand LABUSE sait. La précision servie est
     celle MESURÉE pour le niveau d'information réellement disponible (sans saisie puis après chaque
     réponse), PAR COMMUNE et PAR TYPE — jamais un chiffre fixe.
  3. L'ESTIMATION AFFINÉE — fourchette resserrée, LISTE DES VENTES RETENUES que l'utilisateur peut
     ÉCARTER (l'API recalcule), et les biens similaires EN VENTE (Radar).

Ce qui a été PROUVÉ au banc (docs/audit-2026-11/estimer-3, no-leak, ventes 2024 ET 2025) décide quelles
questions existent — cf. `QUESTIONS` plus bas et le COMPTE-RENDU :
  · surface habitable : gain FORT et robuste (maison −6 pts d'écart médian, +9 à +11 pts à ±20 % ;
    appartement : surface indispensable) → posée pour les DEUX types ;
  · nombre de pièces  : gain mesuré pour l'APPARTEMENT (Q3 28→27, ±20 % 61→62) ; NUL pour la maison
    (surface connue : 24→25 % médian, ±20 % 43→41 à n=1 500) → posée SEULEMENT pour l'appartement ;
  · piscine : MESURÉE (photo aérienne) et servie en clair, mais AUCUN gain robuste (signe qui s'inverse
    d'une année à l'autre ; le test « comparables à piscine » dégrade le sous-ensemble concerné) → NON
    posée comme question de prix ;
  · vue dégagée, état (bâti), terrain viabilisé : AUCUNE donnée sur les comparables → non mesurable →
    non posées (le rapport le dit).

Calcul et API SEULEMENT (mandat) — aucun fichier du front. Le point no-leak jumeau (banc permanent) vit
dans `banc_estimer.py` (niveaux d'information) et calibre la précision servie par (type, commune, niveau).
"""
from __future__ import annotations

import math
import time

from sqlalchemy import text

# ── Poids de RESSEMBLANCE (mesurés : ESTIMER-PRECISION-1 pour distance/surface/terrain/ancienneté ;
#    H_PIECES réglé ICI au banc ESTIMER-3, confirmé hors-période). Un comparable compte selon sa
#    distance (gaussien), son écart de surface habitable (laplacien), pour la maison son écart de
#    taille de terrain (laplacien), son ancienneté (demi-vie) et, si l'info est donnée, son écart de
#    nombre de pièces (laplacien). Aucun coefficient inventé : chaque échelle est celle du banc.
POIDS = {
    "maison":      {"h_dist": 900.0, "h_surf": 120.0, "halflife": 4.0, "h_terr": 1500.0},
    "appartement": {"h_dist": 500.0, "h_surf": 160.0, "halflife": 2.0, "h_terr": None},
}
_POIDS_DEFAUT = {"h_dist": 900.0, "h_surf": 120.0, "halflife": 4.0, "h_terr": None}
H_PIECES = 0.8                 # échelle d'écart de pièces (mesurée ESTIMER-3)
RAYONS = (500.0, 1000.0, 1500.0)
AN_RECENTE = 2022
SEUIL = 8                      # effectif minimal d'un échantillon « semblable » (sinon repli secteur)
BORNES_BATI = (1000.0, 12000.0)
N_RETENUES = 12                # ventes retenues servies (la plus pesante d'abord)

# Les questions qui DÉPLACENT le prix — et SEULEMENT elles, PAR TYPE (gain mesuré au banc no-leak,
# docs/audit-2026-11/estimer-3). `types` = types de bien pour lesquels le gain est prouvé → la question
# n'est posée QUE là. La surface habitable paie pour les deux ; les pièces n'améliorent que
# l'appartement (maison : neutre/légèrement pire à n=1500 → non posée pour la maison).
QUESTIONS = [
    {"cle": "surface_hab", "label": "Surface habitable", "type": "nombre", "unite": "m²",
     "types": ("maison", "appartement"), "gain": "fort (les deux types)"},
    {"cle": "pieces", "label": "Nombre de pièces", "type": "choix", "options": [2, 3, 4, 5, "6+"],
     "types": ("appartement",), "gain": "appartement : modeste ; maison : nul → non posée pour la maison"},
]
#: caractéristiques NON posées, et pourquoi (servies au rapport et à l'écran « ce qu'on ne demande pas »)
QUESTIONS_ABANDONNEES = [
    {"cle": "pieces_maison", "raison": "pour la MAISON : aucun gain mesuré (surface connue, les pièces "
                                       "ne resserrent pas) — posée seulement pour l'appartement"},
    {"cle": "piscine", "raison": "mesurée (photo aérienne) mais sans gain de précision mesuré "
                                 "(le prix ne bouge pas de façon fiable) — servie en clair, pas posée"},
    {"cle": "vue_degagee", "raison": "aucune donnée sur les ventes comparables — gain non mesurable"},
    {"cle": "etat", "raison": "aucune donnée d'état sur les ventes DVF — gain non mesurable"},
    {"cle": "terrain_viabilise", "raison": "aucune donnée de viabilisation — gain non mesurable"},
]


def _annee_dec(d) -> float | None:
    """date python → année décimale (2024-07-02 ≈ 2024,5)."""
    if d is None:
        return None
    try:
        return d.year + (d.timetuple().tm_yday - 1) / 365.25
    except AttributeError:
        return None


def _wquantiles(vw: list[tuple[float, float]]):
    """(q1, médiane, q3) PONDÉRÉS d'une liste (valeur, poids). None si vide."""
    vw = [(float(v), float(w)) for v, w in vw if w and w > 0 and math.isfinite(w)]
    if not vw:
        return None, None, None
    vw.sort(key=lambda t: t[0])
    total = sum(w for _, w in vw)
    qs: dict[float, float] = {}
    cum = 0.0
    for v, w in vw:
        cum += w
        for cq in (0.25, 0.5, 0.75):
            if cq not in qs and cum >= total * cq:
                qs[cq] = v
    for cq in (0.25, 0.5, 0.75):
        qs.setdefault(cq, vw[-1][0])
    return qs[0.25], qs[0.5], qs[0.75]


# ════════════════════════════════════════════════════════════════════════════════════════════════
#  Pool de comparables (live) — ventes bâties mono-parcelle de la commune, avec leurs caractéristiques
# ════════════════════════════════════════════════════════════════════════════════════════════════
_POOL_SQL = """
WITH subj AS (SELECT geom_2975 g FROM parcels WHERE idu = :idu),
muc AS (SELECT id_mutation, count(DISTINCT id_parcelle) np FROM dvf_mutations_parcelle
        WHERE code_commune = :insee GROUP BY 1)
SELECT dm.id_mutation AS mid, dm.id_parcelle AS idu, dm.type_local,
       round(dm.surface_reelle_bati)::int AS surface_m2,
       round(COALESCE(dm.surface_terrain, 0))::int AS terrain_m2,
       round(dm.valeur_fonciere)::int AS prix_eur,
       (dm.valeur_fonciere / NULLIF(dm.surface_reelle_bati, 0)) AS prix_m2_f,
       to_char(dm.date_mutation, 'YYYY-MM-DD') AS date, dm.date_mutation::date AS d,
       extract(year FROM dm.date_mutation)::int AS annee,
       round(ST_Distance(pp.geom_2975, subj.g))::int AS distance_m,
       dd.nombre_pieces AS pieces,
       EXISTS(SELECT 1 FROM piscines ps WHERE ps.idu = dm.id_parcelle) AS pool
FROM dvf_mutations_parcelle dm
CROSS JOIN subj
JOIN muc ON muc.id_mutation = dm.id_mutation AND muc.np = 1
JOIN parcels pp ON pp.idu = dm.id_parcelle
LEFT JOIN dvf_mutation_detail dd ON dd.id_mutation = dm.id_mutation AND dd.id_parcelle = dm.id_parcelle
WHERE dm.code_commune = :insee
  AND dm.nature_mutation IN ('Vente', 'Vente terrain à bâtir')
  AND dm.type_local IN ('Maison', 'Appartement')
  AND dm.surface_reelle_bati >= 20 AND dm.valeur_fonciere > 0
  AND dm.id_parcelle <> :idu
  AND dm.valeur_fonciere / dm.surface_reelle_bati BETWEEN :lo AND :hi
"""

_POOL_CACHE: dict[str, tuple[float, list[dict]]] = {}
_POOL_TTL = 30.0


def _pool_comparables(db, idu: str, insee: str) -> list[dict]:
    """Toutes les ventes bâties mono-parcelle de la commune (maison + appartement), avec distance au
    sujet et caractéristiques (surface, terrain, pièces, piscine, date). Cache 30 s par (idu).
    SURFAÇAGE : chaque ligne est une vente réelle, jamais un agrégat recalculé."""
    key = f"{idu}"
    now = time.monotonic()
    hit = _POOL_CACHE.get(key)
    if hit and (now - hit[0]) < _POOL_TTL:
        return hit[1]
    rows = [dict(r) for r in db.execute(text(_POOL_SQL),
            {"idu": idu, "insee": insee, "lo": BORNES_BATI[0], "hi": BORNES_BATI[1]}).mappings().all()]
    for r in rows:
        r["ydec"] = _annee_dec(r["d"])
    if len(_POOL_CACHE) > 64:
        _POOL_CACHE.clear()
    _POOL_CACHE[key] = (now, rows)
    return rows


def _selection_rayon(comps: list[dict], type_bien: str):
    """Rayon ADAPTATIF (période récente préférée → élargie, 500→1000→1500 m) jusqu'à SEUIL ventes du
    MÊME type ; sinon repli COMMUNE (toutes les ventes du type). Renvoie (liste, radius|None,
    commune_fallback)."""
    tl = "Maison" if type_bien == "maison" else "Appartement"
    base = [c for c in comps if c["type_local"] == tl]
    for an_min in (AN_RECENTE, 0):
        per = [c for c in base if (c["annee"] or 0) >= an_min]
        for r in RAYONS:
            sel = [c for c in per if (c["distance_m"] or 0) <= r]
            if len(sel) >= SEUIL:
                return sel, int(r), False
    return base, None, True


def eur_m2_semblable(comps: list[dict], subj: dict, type_bien: str, *, use_pieces: bool):
    """€/m² PONDÉRÉ par la ressemblance (q1, médiane, q3) + poids posés sur chaque comparable (`_poids`).
    `subj` : {x, y, surf_poids, terrain, pieces}. Les prix sont les €/m² BRUTS observés (jamais ré-indexés
    au-delà de la demi-vie d'ancienneté). `comps` = échantillon DÉJÀ sélectionné (rayon/commune)."""
    par = POIDS.get(type_bien, _POIDS_DEFAUT)
    is_maison = (type_bien == "maison")
    ref_dec = max((c["ydec"] for c in comps if c.get("ydec")), default=0.0)
    vw = []
    for c in comps:
        w = 1.0
        if c.get("distance_m") is not None:
            w *= math.exp(-((float(c["distance_m"]) / par["h_dist"]) ** 2))
        ss = subj.get("surf_poids")
        if ss and ss > 0 and c.get("surface_m2"):
            w *= math.exp(-abs(float(c["surface_m2"]) - float(ss)) / par["h_surf"])
        ht = par.get("h_terr")
        st = subj.get("terrain")
        if ht and is_maison and st and st > 0 and (c.get("terrain_m2") or 0) > 0:
            w *= math.exp(-abs(float(c["terrain_m2"]) - float(st)) / ht)
        if par.get("halflife") and c.get("ydec"):
            w *= 0.5 ** (max(0.0, ref_dec - c["ydec"]) / par["halflife"])
        if use_pieces and subj.get("pieces"):
            if c.get("pieces"):
                w *= math.exp(-abs(float(c["pieces"]) - float(subj["pieces"])) / H_PIECES)
            # comparable sans pièces connues → poids neutre (pas de pénalité)
        if not (w > 0) or not math.isfinite(w):
            w = 1e-12
        c["_poids"] = w
        vw.append((float(c["prix_m2_f"]), w))
    return _wquantiles(vw)


# ════════════════════════════════════════════════════════════════════════════════════════════════
#  Ce que LABUSE a MESURÉ (servi en clair, sans saisie)
# ════════════════════════════════════════════════════════════════════════════════════════════════
def _piscine_mesuree(db, idu: str) -> dict:
    """Piscine détectée (couche `piscines`, photo aérienne / CoSIA — île entière). Servie en clair ;
    elle NE déplace PAS le prix (aucun gain mesuré au banc), mais l'écran la montre."""
    row = db.execute(text(
        "SELECT count(*) n, COALESCE(round(sum(surface_m2))::int, 0) s FROM piscines WHERE idu = :idu"),
        {"idu": idu}).mappings().first()
    n = int((row or {}).get("n") or 0)
    return {"presente": n > 0, "surface_m2": (int(row["s"]) if n else None),
            "source": "photo aérienne"}


def _pente_mesuree(db, idu: str) -> dict | None:
    deg = db.execute(text("SELECT pente_moy_deg FROM parcel_terrain WHERE idu = :idu"),
                     {"idu": idu}).scalar()
    if deg is None:
        return None
    from ..pente_fmt import pente_pct
    return {"deg": round(float(deg), 1), "pct": pente_pct(float(deg))}


def mesures_labuse(db, idu: str, fiche: dict, *, nature: str | None, zone_lib: str | None,
                   mut: dict | None, insee: str) -> dict:
    """CE QUE LABUSE A MESURÉ — terrain, emprise bâtie, niveaux LiDAR, surface habitable estimée,
    piscine, pente, zone. Tout vient d'une mesure (aucune saisie). `mut` = dernière vente DVF."""
    from .api import (_emprise_bati_fiche_m2, _niveaux_lidar_parcelle, _surface_pour_total)
    emprise = _emprise_bati_fiche_m2(fiche)
    niveaux = _niveaux_lidar_parcelle(db, idu)
    surface_parc = ((fiche or {}).get("surface_terrain_m2")
                    or (fiche or {}).get("contenance_m2") or (fiche or {}).get("surface_m2"))
    # surface habitable ESTIMÉE (sans saisie) : même producteur que le total (emprise×ratio×niveaux).
    surf_est, surf_src = _surface_pour_total(db, idu, emprise, mut, insee, None,
                                             bati_mesure=(nature != "non_mesure"))
    return {
        "nature": nature,
        "terrain_m2": (round(float(surface_parc)) if surface_parc else None),
        "emprise_bati_m2": emprise,
        "niveaux": niveaux,
        "surface_hab_estimee_m2": surf_est,
        "surface_hab_estimee_ligne": (surf_src or {}).get("ligne"),
        "piscine": _piscine_mesuree(db, idu),
        "pente": _pente_mesuree(db, idu),
        "zone": zone_lib,
    }


# ════════════════════════════════════════════════════════════════════════════════════════════════
#  Précision MESURÉE par (type, commune, niveau d'information) — lue du banc permanent
# ════════════════════════════════════════════════════════════════════════════════════════════════
#: niveau d'information servi (décide la précision) : rien / surface connue / surface+pièces connues.
NIVEAUX = ("sans_saisie", "surface", "surface_pieces")
#: repli prudent quand le banc n'a jamais tourné (base de test) — par type, demi-largeur % (q3-ish).
_BANDE_REPLI = {"maison": {"sans_saisie": 40, "surface": 34, "surface_pieces": 33},
                "appartement": {"sans_saisie": 30, "surface": 22, "surface_pieces": 20},
                "terrain": {"sans_saisie": 35, "surface": 35, "surface_pieces": 35}}


def charge_precision(db, type_bien: str, insee: str, niveau: str) -> dict:
    """Précision MESURÉE pour ce (type, commune, niveau) : écart médian + Q3 + part à ±20 %, lue de la
    table `estimer3_precision` (banc permanent). Repli commune→île→bande prudente. Jamais de 500."""
    t = type_bien if type_bien in ("maison", "appartement", "terrain") else "maison"
    try:
        for ins, peri in ((insee, "commune"), ("*", "ile")):
            r = db.execute(text(
                "SELECT n_ventes, ecart_median, ecart_q3, pct_20 FROM estimer3_precision "
                "WHERE type_bien = :t AND insee = :i AND niveau = :n"),
                {"t": t, "i": ins, "n": niveau}).mappings().first()
            if r and r["ecart_q3"] is not None:
                return {"ecart_median": round(float(r["ecart_median"])), "ecart_q3": round(float(r["ecart_q3"])),
                        "pct_20": (round(float(r["pct_20"])) if r["pct_20"] is not None else None),
                        "n": int(r["n_ventes"] or 0), "perimetre": peri, "source": "mesure"}
    except Exception:  # noqa: BLE001 — table absente (banc jamais passé) → repli bande prudente
        try:
            db.rollback()
        except Exception:  # noqa: BLE001
            pass
    q3 = _BANDE_REPLI.get(t, _BANDE_REPLI["maison"]).get(niveau, 35)
    return {"ecart_median": q3, "ecart_q3": q3, "pct_20": None, "n": 0,
            "perimetre": "bande", "source": "bande"}


def _fiabilite_mot(ecart_median: float, n: int) -> tuple[str, str]:
    """(niveau interne, mot client) depuis l'écart médian mesuré + le nombre de ventes (comme ESTIMER-2)."""
    if ecart_median < 15 and n >= 15:
        return "fiable", "Élevée"
    if ecart_median < 25 and n >= 8:
        return "moyen", "Moyenne"
    return "limitee", "Limitée"


def precision_par_niveau(db, type_bien: str, insee: str) -> dict:
    """La JAUGE qui se resserre : ±% TYPIQUE (écart médian mesuré) à chaque niveau d'information, pour ce
    bien. (Le Q3 prudent est servi au niveau courant via `precision_q3_pct`.)"""
    return {niv: charge_precision(db, type_bien, insee, niv)["ecart_median"] for niv in NIVEAUX}


# ════════════════════════════════════════════════════════════════════════════════════════════════
#  Estimation « comparables semblables » — orchestration servie (écran == PDF == API)
# ════════════════════════════════════════════════════════════════════════════════════════════════
def _pieces_sujet(db, idu: str) -> int | None:
    """Nombre de pièces de la DERNIÈRE vente DVF de la parcelle (pré-remplit la question « pièces »
    quand LABUSE le sait). None sinon."""
    return db.execute(text(
        "SELECT dd.nombre_pieces FROM dvf_mutation_detail dd "
        "WHERE dd.id_parcelle = :idu AND dd.nombre_pieces > 0 "
        "ORDER BY dd.id_mutation DESC LIMIT 1"), {"idu": idu}).scalar()


def _vente_retenue(c: dict, ecartee: bool) -> dict:
    """Une vente RETENUE servie (date, surface, terrain, prix, distance) + son identifiant (mutation),
    que l'utilisateur peut décocher pour l'écarter (l'API renvoie le même id dans `ecartees`)."""
    d = c.get("date")
    return {"id": c["mid"],
            "date": (f"{d[5:7]}/{d[0:4]}" if isinstance(d, str) and len(d) >= 7 else None),
            "surface_m2": c.get("surface_m2"), "terrain_m2": c.get("terrain_m2"),
            "prix_eur": c.get("prix_eur"), "distance_m": c.get("distance_m"),
            "pieces": c.get("pieces"), "piscine": bool(c.get("pool")),
            "ecartee": ecartee}


def _arrondi_mille(n):
    return int(round(n / 1000.0)) * 1000 if isinstance(n, (int, float)) else None


def estimation_semblable(db, idu: str, fiche: dict, *, surface_hab: float | None = None,
                         pieces: int | None = None, ecartees: set | None = None) -> dict:
    """ESTIMER-3 — l'estimation « comparables semblables » d'un bien BÂTI (maison / appartement), avec
    repli sur le prix de SECTEUR d'ESTIMER-2 quand il y a trop peu de ventes semblables. Renvoie
    l'estimation (valeur, fourchette, précision, fiabilité), la LISTE DES VENTES RETENUES (écartables),
    la jauge de précision PAR NIVEAU, et les questions. `ecartees` = identifiants de mutation à exclure."""
    from .api import _derniere_mutation_dvf, _nature_parcelle
    from .. import marche_service as _msvc
    ecartees = set(ecartees or ())
    insee = idu[:5]
    mut = _derniere_mutation_dvf(db, idu)
    nature_mut = mut.get("nature") if mut else None
    nature_parc = _nature_parcelle(db, idu)
    copro = bool(((fiche or {}).get("score_v2") or {}).get("copro"))
    # type de bien servi (maison / appartement) — règle de nature ESTIMER-2.
    if copro or nature_mut == "appartement":
        type_bien = "appartement"
    elif nature_mut == "maison":
        type_bien = "maison"
    else:
        # à défaut de vente typée : le comparateur déduit le type dominant du secteur.
        cb0 = _msvc.comparateur_bien(db, idu, type_bien=None)
        type_bien = (cb0 or {}).get("type_bien")
        type_bien = type_bien if type_bien in ("maison", "appartement") else "maison"

    surface_parc = ((fiche or {}).get("surface_terrain_m2")
                    or (fiche or {}).get("contenance_m2") or (fiche or {}).get("surface_m2"))
    # surface du sujet pour PONDÉRER : saisie > dernière surface DVF > surface estimée (emprise×ratio×niv).
    from .api import _emprise_bati_fiche_m2, _surface_pour_total
    emprise = _emprise_bati_fiche_m2(fiche)
    surf_est, surf_src = _surface_pour_total(db, idu, emprise, mut, insee, None,
                                             bati_mesure=(nature_parc != "non_mesure"))
    surf_dvf = round(mut["bati_m2"]) if (mut and (mut.get("bati_m2") or 0) > 0) else None
    surf_saisie = (float(surface_hab) if (isinstance(surface_hab, (int, float)) and surface_hab > 0) else None)
    # La surface ESTIMÉE (emprise×ratio×niveaux) n'a de sens que pour une MAISON ; un appartement sans
    # surface connue n'a pas de total servi (sa surface n'est pas mesurable) — on sert le €/m² seul.
    surf_est_valide = surf_est if type_bien == "maison" else None
    surf_poids = surf_saisie or surf_dvf or surf_est_valide
    # surface du TOTAL : saisie > surface DVF de la vente > surface estimée (maison seulement).
    surface_tot = surf_saisie or surf_dvf or surf_est_valide
    # pièces : réponse utilisateur > pièces de la dernière vente DVF (pré-remplissage). Les pièces ne
    # DÉPLACENT le prix que pour l'APPARTEMENT (gain mesuré) — jamais pour la maison (gain nul au banc).
    pieces_pref = _pieces_sujet(db, idu)
    pieces_rep = int(pieces) if (isinstance(pieces, (int, float)) and pieces > 0) else None
    pieces_connu = bool(pieces_rep or pieces_pref)
    pieces_actif = (type_bien == "appartement")           # la question pièces n'existe que pour l'appart
    pieces_use = (pieces_rep or (int(pieces_pref) if pieces_pref else None)) if pieces_actif else None
    # niveau d'information RÉEL (pas seulement la saisie) : une surface / un nombre de pièces CONNUS
    # d'une vente DVF antérieure valent « connus » — la précision servie suit le vrai contenu d'info.
    # La maison plafonne à « surface » (les pièces n'y ajoutent rien de mesurable).
    surface_connue = bool(surf_saisie or surf_dvf)
    niveau = ("surface_pieces" if (surface_connue and pieces_actif and pieces_connu)
              else ("surface" if surface_connue else "sans_saisie"))
    prec = charge_precision(db, type_bien, insee, niveau)

    # ── échantillon SEMBLABLE : ventes du même type, rayon adaptatif, commune en repli ──
    pool = _pool_comparables(db, idu, insee)
    sel, radius, commune_fallback = _selection_rayon(pool, type_bien)
    active = [c for c in sel if c["mid"] not in ecartees]
    # On ne PONDÈRE par la surface que si elle est CONNUE (saisie / vente DVF) : pondérer par une surface
    # ESTIMÉE (emprise×ratio) ajoute du bruit (la surface du total reste l'estimée, elle). Mesuré au banc.
    surf_poids_pond = (surf_saisie or surf_dvf) if surface_connue else None
    subj = {"surf_poids": surf_poids_pond, "terrain": (float(surface_parc) if surface_parc else None),
            "pieces": pieces_use}
    repli = False
    if len(active) >= SEUIL:
        q1, med, q3 = eur_m2_semblable(active, subj, type_bien, use_pieces=bool(pieces_use))
        n_sembl = len(active)
    else:
        # trop peu de ventes semblables → repli sur le prix de SECTEUR d'ESTIMER-2 (et on le DIT).
        repli = True
        cb = _msvc.comparateur_bien(db, idu, type_bien=type_bien,
                                    surface_sujet=surf_poids, terrain_sujet=surface_parc)
        med = (cb or {}).get("median")
        q1, q3 = (cb or {}).get("q1"), (cb or {}).get("q3")
        n_sembl = (cb or {}).get("n") or len(active)
        radius = (cb or {}).get("radius_m", radius)
        commune_fallback = (cb or {}).get("commune_fallback", commune_fallback)
        # poids pour l'ordre des ventes retenues (même si l'estimation vient du secteur)
        if active:
            eur_m2_semblable(active, subj, type_bien, use_pieces=bool(pieces_use))

    niv_interne, mot = _fiabilite_mot(prec["ecart_median"], prec.get("n") or n_sembl)
    # Fourchette = ± l'écart TYPIQUE mesuré (médian : une estimation sur deux y tombe) ; elle SE RESSERRE
    # à chaque niveau d'information. Le Q3 mesuré (≈75 % des ventes) est servi à part (bande prudente).
    demi = prec["ecart_median"]
    valeur = None
    basse = haute = None
    if med and surface_tot:
        central = float(surface_tot) * float(med)
        valeur = _arrondi_mille(central)
        basse = _arrondi_mille(central * (1 - demi / 100.0))
        haute = _arrondi_mille(central * (1 + demi / 100.0))

    # ── ventes retenues : les plus PESANTES d'abord (actives), puis les écartées (décochées) ──
    active_tri = sorted(active, key=lambda c: c.get("_poids", 0.0), reverse=True)
    retenues = [_vente_retenue(c, False) for c in active_tri[:N_RETENUES]]
    for c in sel:
        if c["mid"] in ecartees:
            retenues.append(_vente_retenue(c, True))
    # périmètre / période / description
    annees = [c["annee"] for c in (active or sel) if c.get("annee")]
    periode = [min(annees), max(annees)] if annees else None
    peri_txt = ("commune entière" if commune_fallback
                else (f"moins de {int(radius)} m" if radius else "secteur"))
    type_pl = "maisons" if type_bien == "maison" else "appartements"
    desc = (f"{n_sembl} vente{'s' if n_sembl > 1 else ''} de {type_pl} semblables "
            f"(surface, terrain) à {peri_txt}"
            + (f" · {periode[0]}–{periode[1]}" if periode and periode[0] != periode[1] else ""))

    return {
        "idu": idu, "type_bien": type_bien,
        "estimation": {
            "valeur_eur": valeur, "valeur_basse": basse, "valeur_haute": haute,
            "eur_m2": (round(med) if med else None),
            "precision_pct": demi, "ecart_median_pct": prec["ecart_median"],
            "precision_q3_pct": prec["ecart_q3"], "pct_20_mesure": prec.get("pct_20"),
            "precision_source": prec["source"], "precision_perimetre": prec.get("perimetre"),
            "fiabilite": niv_interne, "fiabilite_mot": mot,
            "surface_utilisee_m2": (round(surface_tot) if surface_tot else None),
            "surface_source": ("saisie" if surf_saisie else ("vente DVF" if surf_dvf else "estimée")),
            "n_comparables": n_sembl, "comparables_desc": desc,
            "radius_m": radius, "commune_fallback": commune_fallback, "periode": periode,
            "repli_secteur": repli,
            "repli_note": ("Trop peu de ventes semblables dans le secteur — repli sur le prix de "
                           "secteur (ESTIMER-2)." if repli else None),
        },
        "ventes_retenues": retenues,
        "niveau_info": niveau,
        "precision_par_niveau": precision_par_niveau(db, type_bien, insee),
        "surface_hab_prerempli": surf_est,
        "pieces_prerempli": (int(pieces_pref) if pieces_pref else None),
    }


# ════════════════════════════════════════════════════════════════════════════════════════════════
#  Radar — biens SEMBLABLES en vente + écart affiché/vendu (seulement s'il est mesurable)
# ════════════════════════════════════════════════════════════════════════════════════════════════
_GAP_MIN_SAMPLE = 20            # échantillon minimal d'annonces rattachées à une vente pour servir l'écart


def radar_semblables(db, commune: str | None, type_bien: str | None,
                     surface_hab: float | None, pieces: int | None, *, n: int = 6) -> dict:
    """Les biens SIMILAIRES actuellement EN VENTE (Radar) : type, pièces, surface, prix affiché — les
    plus proches en surface d'abord. + l'écart moyen prix affiché vs prix VENDU, SERVI SEULEMENT s'il est
    mesurable sur un échantillon suffisant (annonces rattachées à une vente DVF) ; sinon non servi, avec
    la raison (mandat)."""
    out = {"biens": [], "ecart_affiche_vendu_pct": None, "ecart_note": None, "ecart_n": 0}
    if not commune:
        return out
    tb = type_bien if type_bien in ("maison", "appartement", "terrain") else None
    rows = db.execute(text(
        "SELECT b.type_bien, f.pieces, f.surface_hab, f.surface_terrain, f.prix, b.bien_id "
        "FROM pige_biens b JOIN pige_faits f ON f.bien_id = b.bien_id "
        "WHERE b.commune = :c AND b.statut IN ('active', 'en_vente_longue') "
        "  AND (CAST(:tb AS text) IS NULL OR b.type_bien = :tb) AND f.prix > 0 "
        "ORDER BY (CASE WHEN CAST(:s AS double precision) IS NULL OR f.surface_hab IS NULL THEN 1 ELSE 0 END), "
        "         abs(COALESCE(f.surface_hab, 0) - COALESCE(CAST(:s AS double precision), f.surface_hab, 0)) ASC "
        "LIMIT :n"),
        {"c": commune, "tb": tb, "s": surface_hab, "n": n}).mappings().all()
    out["biens"] = [{
        "type": (r["type_bien"] or "").capitalize() or None,
        "pieces": (int(r["pieces"]) if r["pieces"] else None),
        "surface_m2": (round(float(r["surface_hab"])) if r["surface_hab"] else None),
        "terrain_m2": (round(float(r["surface_terrain"])) if r["surface_terrain"] else None),
        "prix_affiche_eur": (round(float(r["prix"])) if r["prix"] else None),
    } for r in rows]
    # écart affiché / vendu : moyenne sur les biens VENDUS rattachés à une vente DVF (vendue_ecart_prix).
    g = db.execute(text(
        "SELECT count(*) n, avg(vendue_ecart_prix) m FROM pige_biens "
        "WHERE vendue_ecart_prix IS NOT NULL AND (CAST(:tb AS text) IS NULL OR type_bien = :tb) "
        "  AND (commune = :c OR CAST(:c AS text) IS NULL)"), {"tb": tb, "c": commune}).mappings().first()
    n_gap = int((g or {}).get("n") or 0)
    out["ecart_n"] = n_gap
    if n_gap >= _GAP_MIN_SAMPLE and g["m"] is not None:
        pct = round(float(g["m"]) * 100, 1)
        out["ecart_affiche_vendu_pct"] = pct
        out["ecart_note"] = (f"Les prix affichés sont en moyenne {pct:+.0f} % par rapport aux prix "
                             f"vendus dans ce secteur (sur {n_gap} annonces rattachées à une vente).")
    else:
        # repli : écart à l'échelle de l'île si la commune est trop mince, sinon non servi.
        gi = db.execute(text(
            "SELECT count(*) n, avg(vendue_ecart_prix) m FROM pige_biens "
            "WHERE vendue_ecart_prix IS NOT NULL AND (CAST(:tb AS text) IS NULL OR type_bien = :tb)"),
            {"tb": tb}).mappings().first()
        ni = int((gi or {}).get("n") or 0)
        if ni >= _GAP_MIN_SAMPLE and gi["m"] is not None:
            pct = round(float(gi["m"]) * 100, 1)
            out["ecart_affiche_vendu_pct"] = pct
            out["ecart_n"] = ni
            out["ecart_note"] = (f"Les prix affichés sont en moyenne {pct:+.0f} % par rapport aux prix "
                                 f"vendus (île, {ni} annonces rattachées).")
        else:
            out["ecart_note"] = ("Écart affiché/vendu non servi : trop peu d'annonces rattachées à une "
                                 f"vente DVF ({n_gap} localement, {ni} sur l'île ; seuil {_GAP_MIN_SAMPLE}).")
    return out


# ════════════════════════════════════════════════════════════════════════════════════════════════
#  Assemblage servi (endpoint + PDF) — les trois temps en un seul rapport
# ════════════════════════════════════════════════════════════════════════════════════════════════
def _questions_servies(est: dict, type_bien: str) -> list[dict]:
    """Les questions POSÉES pour CE type de bien (gain mesuré, `types`), pré-remplies quand LABUSE sait."""
    out = []
    for q in QUESTIONS:
        if type_bien not in q.get("types", ()):
            continue
        item = {k: v for k, v in q.items() if k != "types"}
        if q["cle"] == "surface_hab":
            item["prerempli"] = est.get("surface_hab_prerempli")
            item["prerempli_source"] = "LABUSE (emprise × niveaux)" if est.get("surface_hab_prerempli") else None
        elif q["cle"] == "pieces":
            item["prerempli"] = est.get("pieces_prerempli")
            item["prerempli_source"] = "dernière vente DVF" if est.get("pieces_prerempli") else None
        out.append(item)
    return out


def rapport3(db, idu: str, fiche: dict, *, surface_hab: float | None = None,
             pieces: int | None = None, ecartees=None) -> dict:
    """ESTIMER-3 — le rapport COMPLET de l'outil « Estimer un bien » en trois temps, POINT UNIQUE lu par
    l'écran (endpoint), l'API et le PDF. Pour un bien BÂTI : mesures LABUSE + estimation semblable +
    questions + ventes retenues + précision par niveau + Radar. Pour un TERRAIN : repère de secteur
    (ESTIMER-2) + mesures, sans question (la viabilisation n'est pas mesurable)."""
    from .api import _derniere_mutation_dvf, _nature_parcelle, estimation_annonce
    insee = idu[:5]
    commune = db.execute(text("SELECT commune FROM parcels WHERE idu = :idu"), {"idu": idu}).scalar()
    mut = _derniere_mutation_dvf(db, idu)
    nature_mut = mut.get("nature") if mut else None
    nature_parc = _nature_parcelle(db, idu)
    # zone en clair (même lecteur que la fiche).
    zone_lib = None
    try:
        from ..faisabilite.potentiel_batir import potentiel_batir
        pot = (fiche or {}).get("potentiel_a_batir") or potentiel_batir(db, idu)
        zone_lib = (pot or {}).get("zone_lib")
    except Exception:  # noqa: BLE001
        zone_lib = None

    est_terrain = (nature_mut == "terrain") or (nature_mut is None and nature_parc == "nu")
    if est_terrain:
        base = estimation_annonce(db, idu, fiche)      # ESTIMER-2 (repère terrain nu + mesurée)
        mesures = mesures_labuse(db, idu, fiche, nature="terrain", zone_lib=zone_lib, mut=mut, insee=insee)
        prec = charge_precision(db, "terrain", insee, "sans_saisie")
        return {"idu": idu, "commune": commune, "type_bien": "terrain",
                "mesures": mesures,
                "estimation": {"valeur_eur": (base.get("valeur_indicative") or {}).get("valeur_eur"),
                               "valeur_basse": (base.get("valeur_indicative") or {}).get("valeur_basse"),
                               "valeur_haute": (base.get("valeur_indicative") or {}).get("valeur_haute"),
                               "eur_m2": base.get("median"), "precision_pct": prec["ecart_median"],
                               "precision_q3_pct": prec["ecart_q3"], "ecart_median_pct": prec["ecart_median"],
                               "fiabilite_mot": base.get("fiabilite_mot"),
                               "n_comparables": base.get("n"), "repli_secteur": False,
                               "comparables_desc": None, "repli_note": None},
                "ventes_retenues": [_vente_retenue({**c, "mid": c.get("date")}, False)
                                    for c in (base.get("comparables") or [])],
                "questions": [], "questions_abandonnees": QUESTIONS_ABANDONNEES,
                "precision_par_niveau": {"sans_saisie": prec["ecart_median"]},
                "radar": radar_semblables(db, commune, "terrain", None, None),
                "note_terrain": "Terrain nu : repère de secteur ESTIMER-2 ; la viabilisation n'est pas "
                                "une donnée mesurable, elle n'est pas demandée."}

    est = estimation_semblable(db, idu, fiche, surface_hab=surface_hab, pieces=pieces, ecartees=ecartees)
    type_bien = est["type_bien"]
    mesures = mesures_labuse(db, idu, fiche, nature=type_bien, zone_lib=zone_lib, mut=mut, insee=insee)
    return {
        "idu": idu, "commune": commune, "type_bien": type_bien,
        "mesures": mesures,
        "estimation": est["estimation"],
        "ventes_retenues": est["ventes_retenues"],
        "niveau_info": est["niveau_info"],
        "precision_par_niveau": est["precision_par_niveau"],
        "questions": _questions_servies(est, type_bien),
        "questions_abandonnees": QUESTIONS_ABANDONNEES,
        "radar": radar_semblables(db, commune, type_bien,
                                  est["estimation"].get("surface_utilisee_m2"), pieces),
    }
