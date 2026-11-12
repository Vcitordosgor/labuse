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
import re
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
# DÉFAUT A (Vic, ESTIMER-ECRAN-1) — surface habitable INCONNUE + bande « 3 fois sur 4 » au-delà de ce
# seuil % : on n'affiche PAS de valeur totale (trop incertaine), on sert le prix au m² et sa fourchette.
SEUIL_Q3_MASQUE = 50
# DÉFAUT B (Vic, correction) — sur un bien BÂTI, AUCUNE valeur de terrain n'est servie ni affichée : la
# mesure no-leak sur 2 060 maisons montre que la retenir (plancher, ou même l'exposer) DÉGRADE la précision
# des cas concernés (terrain > bâti, 28,6 % des maisons : écart médian 29,7 % → 45,2 %, ±20 % 35,3 % →
# 26,9 %). La fiabilité reste celle mesurée au banc. Mesure : docs/audit-2026-11/estimer-3/mesure_plancher.py.

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
                "SELECT n_ventes, ecart_median, ecart_q3, pct_20, methode FROM estimer3_precision "
                "WHERE type_bien = :t AND insee = :i AND niveau = :n"),
                {"t": t, "i": ins, "n": niveau}).mappings().first()
            if r and r["ecart_q3"] is not None:
                return {"ecart_median": round(float(r["ecart_median"])), "ecart_q3": round(float(r["ecart_q3"])),
                        "pct_20": (round(float(r["pct_20"])) if r["pct_20"] is not None else None),
                        "n": int(r["n_ventes"] or 0), "perimetre": peri, "source": "mesure",
                        "methode": (r["methode"] or "semblable")}
    except Exception:  # noqa: BLE001 — table absente (banc jamais passé) → repli bande prudente
        try:
            db.rollback()
        except Exception:  # noqa: BLE001
            pass
    q3 = _BANDE_REPLI.get(t, _BANDE_REPLI["maison"]).get(niveau, 35)
    return {"ecart_median": q3, "ecart_q3": q3, "pct_20": None, "n": 0,
            "perimetre": "bande", "source": "bande", "methode": "semblable"}


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
def _multi_logement(db, idu: str) -> bool:
    """OUTILS-P0-2 (recette) — la parcelle porte-t-elle un IMMEUBLE à PLUSIEURS logements ? (copropriété
    RNIC avec > 1 lot d'habitation). Si oui, la dernière vente DVF n'est qu'UN lot : sa surface ne décrit
    PAS le bien estimé → on ne préremplit pas le champ, et le badge « connue » est réservé au mono-logement."""
    try:
        n = db.execute(text(
            "SELECT max(nb_lots_habitation) FROM rnic_coproprietes WHERE parcelle_idu = :idu"),
            {"idu": idu}).scalar()
        return bool(n and int(n) > 1)
    except Exception:  # noqa: BLE001 — table absente / base partielle : pas de signal, comportement nominal
        return False


def _pieces_sujet(db, idu: str) -> int | None:
    """Nombre de pièces de la DERNIÈRE vente DVF de la parcelle (pré-remplit la question « pièces »
    quand LABUSE le sait). None sinon."""
    return db.execute(text(
        "SELECT dd.nombre_pieces FROM dvf_mutation_detail dd "
        "WHERE dd.id_parcelle = :idu AND dd.nombre_pieces > 0 "
        "ORDER BY dd.id_mutation DESC LIMIT 1"), {"idu": idu}).scalar()


def _mois_annee(d) -> str | None:
    """Date d'une vente → « MM/YYYY ». Accepte « YYYY-MM-DD » (pool bâti) ET « MM/YYYY » déjà formaté
    (comparables terrain) — ne re-formate JAMAIS une date déjà en mois/année (sinon « 05/2022 »→« 22/05/2 »)."""
    if not isinstance(d, str) or len(d) < 7:
        return None
    if d[2] == "/":          # déjà « MM/YYYY »
        return d[:7]
    return f"{d[5:7]}/{d[0:4]}"   # « YYYY-MM-DD » → « MM/YYYY »


def _vente_retenue(c: dict, ecartee: bool) -> dict:
    """Une vente RETENUE servie (date, surface, terrain, prix, distance) + son identifiant (mutation),
    que l'utilisateur peut décocher pour l'écarter (l'API renvoie le même id dans `ecartees`)."""
    return {"id": c["mid"],
            "date": _mois_annee(c.get("date")),
            "surface_m2": c.get("surface_m2"), "terrain_m2": c.get("terrain_m2"),
            "prix_eur": c.get("prix_eur"), "distance_m": c.get("distance_m"),
            "pieces": c.get("pieces"), "piscine": bool(c.get("pool")),
            "ecartee": ecartee}


def _arrondi_mille(n):
    return int(round(n / 1000.0)) * 1000 if isinstance(n, (int, float)) else None


def _arr_m2(n):
    """Surface en m² lisible (espace fine insécable comme séparateur de milliers)."""
    return f"{int(round(n)):,}".replace(",", " ") if isinstance(n, (int, float)) else "—"


def _zone_code(s) -> str | None:
    """Code de zone PLU court (« A », « N », « 1AU »…) extrait d'un libellé ou d'un motif : « Zone non
    constructible (A) » → « A », « N - Naturelle » → « N ». None si rien d'exploitable."""
    if not isinstance(s, str) or not s.strip():
        return None
    m = re.search(r"\(([0-9]{0,2}[A-Za-z]{1,4}[0-9a-z]?)\)", s)   # code entre parenthèses
    if m:
        return m.group(1)
    tete = s.strip().split()[0].rstrip("-–—,").strip()
    if re.fullmatch(r"[0-9]{0,2}[A-Za-z]{1,4}[0-9a-z]?", tete) and len(tete) <= 5:
        return tete
    return None


def _fourchettes(basse, haute, basse_q3, haute_q3, ecart_median, ecart_q3) -> list[dict]:
    """OUTILS-P0-2 (recette) — les BANDES servies, sous leur vrai nom. « 1 fois sur 2 » (écart médian) et
    « 3 fois sur 4 » (Q3) sont DEUX bandes distinctes MESURÉES au banc. Si le banc n'en donne qu'UNE (les
    deux écarts coïncident — repli régional faute de mesure par commune), on n'affiche PAS deux lignes
    identiques : une seule, nommée « Fourchette estimée » (honnête : un repère, pas deux quantiles mesurés)."""
    if basse is None or haute is None:
        return []
    distinctes = (isinstance(ecart_median, (int, float)) and isinstance(ecart_q3, (int, float))
                  and abs(float(ecart_q3) - float(ecart_median)) >= 1)
    if distinctes and basse_q3 is not None and haute_q3 is not None:
        return [{"nom": "1 fois sur 2", "basse": basse, "haute": haute},
                {"nom": "3 fois sur 4", "basse": basse_q3, "haute": haute_q3}]
    return [{"nom": "Fourchette estimée", "basse": basse, "haute": haute}]


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
    surf_dvf_brut = round(mut["bati_m2"]) if (mut and (mut.get("bati_m2") or 0) > 0) else None
    surf_saisie = (float(surface_hab) if (isinstance(surface_hab, (int, float)) and surface_hab > 0) else None)
    # OUTILS-P0-2 (recette) — IMMEUBLE à plusieurs logements : la dernière vente DVF n'est qu'UN lot, sa
    # surface ne décrit pas le bien → on ne la prend NI comme surface servie NI comme préremplissage (le
    # champ reste vide, badge « connue » réservé au mono-logement) ; on sert juste l'indication « dernière
    # vente dans l'immeuble : N m² (AAAA) ». Son prix au m² reste servi (invite à saisir la surface).
    multi_logement = _multi_logement(db, idu)
    surf_dvf = None if multi_logement else surf_dvf_brut
    an_dvf = ((mut.get("date") or "")[:4] if mut else "") or None
    immeuble_derniere_vente = (f"dernière vente dans l’immeuble : {surf_dvf_brut} m² ({an_dvf})"
                               if (multi_logement and surf_dvf_brut and an_dvf) else None)
    # La surface ESTIMÉE (emprise×ratio×niveaux) n'a de sens que pour une MAISON ; un appartement sans
    # surface connue n'a pas de total servi (sa surface n'est pas mesurable) — on sert le €/m² seul.
    surf_est_valide = surf_est if type_bien == "maison" else None
    surf_poids = surf_saisie or surf_dvf or surf_est_valide
    # surface du TOTAL : saisie > surface DVF de la vente > surface estimée (maison seulement).
    surface_tot = surf_saisie or surf_dvf or surf_est_valide
    # pièces : réponse utilisateur > pièces de la dernière vente DVF (pré-remplissage). Les pièces ne
    # DÉPLACENT le prix que pour l'APPARTEMENT (gain mesuré) — jamais pour la maison (gain nul au banc).
    # Immeuble multi-logements : les pièces de la dernière vente sont celles d'un AUTRE lot → pas de préremplissage.
    pieces_pref = None if multi_logement else _pieces_sujet(db, idu)
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
    methode = prec.get("methode", "semblable")
    if len(active) >= SEUIL:
        # On calcule TOUJOURS la médiane pondérée (pose les poids pour l'ordre des ventes retenues) ET la
        # médiane SIMPLE du secteur (ESTIMER-2) ; on SERT la MEILLEURE méthode mesurée au banc pour cette
        # (commune, type, niveau) — « la meilleure des deux à chaque niveau » (mandat).
        q1, med_sembl, q3 = eur_m2_semblable(active, subj, type_bien, use_pieces=bool(pieces_use))
        prix = sorted(float(c["prix_m2_f"]) for c in active)
        med_sect = prix[len(prix) // 2] if prix else None
        med = med_sect if (methode == "secteur" and med_sect) else med_sembl
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
    # DEUX fourchettes servies TELLES QUELLES (mandat ESTIMER-ECRAN-1, jamais une seule donnée pour sûre) :
    #   · « 1 fois sur 2 » = ± l'écart MÉDIAN mesuré (une estimation sur deux y tombe) ;
    #   · « 3 fois sur 4 » = ± le Q3 mesuré (≈75 % des ventes) — la bande prudente.
    # Les deux se resserrent à chaque niveau d'information ; l'API les calcule en euros pour que l'écran
    # et le PDF les affichent à l'identique (aucune largeur recalculée au front).
    demi = prec["ecart_median"]
    demi_q3 = prec["ecart_q3"]
    valeur = None
    basse = haute = None
    basse_q3 = haute_q3 = None
    if med and surface_tot:
        central = float(surface_tot) * float(med)
        valeur = _arrondi_mille(central)
        basse = _arrondi_mille(central * (1 - demi / 100.0))
        haute = _arrondi_mille(central * (1 + demi / 100.0))
        basse_q3 = _arrondi_mille(central * (1 - demi_q3 / 100.0))
        haute_q3 = _arrondi_mille(central * (1 + demi_q3 / 100.0))

    # DÉFAUT A (Vic) — surface habitable INCONNUE (ni saisie ni vente DVF : estimée au LiDAR) ET bande
    # « 3 fois sur 4 » au-delà de ± SEUIL_Q3_MASQUE % : une valeur totale serait trompeuse (elle repose sur
    # une surface devinée et une fourchette trop large). On N'AFFICHE PAS de total — on sert le PRIX AU m²
    # du secteur avec sa fourchette (q1–q3 €/m²) et on invite à saisir la surface. Dès qu'elle est saisie,
    # `surface_connue` devient vrai, le masque tombe, la valeur et ses deux bandes reviennent.
    eur_m2_bas = round(q1) if isinstance(q1, (int, float)) and q1 else None
    eur_m2_haut = round(q3) if isinstance(q3, (int, float)) and q3 else None
    total_masque = (not surface_connue) and (demi_q3 is not None and demi_q3 > SEUIL_Q3_MASQUE)
    if total_masque:
        valeur = basse = haute = basse_q3 = haute_q3 = None

    # DÉFAUT B (Vic, correction) — sur un bien BÂTI, on N'AFFICHE PLUS AUCUNE valeur de terrain (ni bandeau,
    # ni bloc) : la mesure no-leak montre que la retenir DÉGRADE la précision (plancher 29,7 %→45,2 % sur les
    # 28,6 % de maisons concernées ; docs/audit-2026-11/estimer-3/mesure_plancher.py). La fiabilité reste
    # celle MESURÉE au banc pour ce cas — jamais rabaissée à cause du terrain. (La valeur de terrain reste
    # servie pour les TERRAINS NUS, cf. rapport3.)

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
            "valeur_basse_q3": basse_q3, "valeur_haute_q3": haute_q3,
            # OUTILS-P0-2 (recette) — les bandes sous leur vrai nom (deux si mesurées distinctes, une sinon).
            "fourchettes": _fourchettes(basse, haute, basse_q3, haute_q3, prec["ecart_median"], prec["ecart_q3"]),
            # DÉFAUT A — total masqué (surface inconnue + Q3 trop large) → prix au m² + fourchette €/m².
            "total_masque": total_masque, "surface_connue": surface_connue,
            "eur_m2_bas": eur_m2_bas, "eur_m2_haut": eur_m2_haut,
            "eur_m2": (round(med) if med else None),
            "precision_pct": demi, "ecart_median_pct": prec["ecart_median"],
            "precision_q3_pct": prec["ecart_q3"], "pct_20_mesure": prec.get("pct_20"),
            "precision_source": prec["source"], "precision_perimetre": prec.get("perimetre"),
            "fiabilite": niv_interne, "fiabilite_mot": mot,
            "surface_utilisee_m2": (round(surface_tot) if surface_tot else None),
            "surface_source": ("saisie" if surf_saisie else ("vente DVF" if surf_dvf else "estimée")),
            "n_comparables": n_sembl, "comparables_desc": desc,
            "radius_m": radius, "commune_fallback": commune_fallback, "periode": periode,
            # méthode SERVIE (la meilleure mesurée) : « semblable » (pondérée ESTIMER-3) ou « secteur »
            # (médiane simple ESTIMER-2) ; « repli_secteur » = trop peu de semblables.
            "methode_prix": ("repli_secteur" if repli else methode),
            "repli_secteur": repli,
            "repli_note": ("Trop peu de ventes semblables dans le secteur — repli sur le prix de "
                           "secteur (ESTIMER-2)." if repli else None),
            # OUTILS-P0-2 (recette) — immeuble à plusieurs logements : champ surface vide + indication.
            "multi_logement": multi_logement,
            "immeuble_derniere_vente": immeuble_derniere_vente,
        },
        "ventes_retenues": retenues,
        "niveau_info": niveau,
        "precision_par_niveau": precision_par_niveau(db, type_bien, insee),
        # immeuble multi-logements : aucun préremplissage de surface (la dernière vente est un autre lot).
        "surface_hab_prerempli": (None if multi_logement else surf_est),
        "pieces_prerempli": (int(pieces_pref) if pieces_pref else None),
    }


# ════════════════════════════════════════════════════════════════════════════════════════════════
#  Radar — biens SEMBLABLES en vente + écart affiché/vendu (seulement s'il est mesurable)
# ════════════════════════════════════════════════════════════════════════════════════════════════
_GAP_MIN_SAMPLE = 20            # échantillon minimal d'annonces rattachées à une vente pour servir l'écart
_RADAR_RAYON_M = 10000          # « à proximité » : rayon autour de la parcelle (annonces au-delà écartées)
_RADAR_N = 5                    # les CINQ plus proches (mandat)


def radar_semblables(db, idu: str | None, commune: str | None, type_bien: str | None, *,
                     n: int = _RADAR_N) -> dict:
    """Les biens SIMILAIRES actuellement EN VENTE (Radar) : type, pièces, surface, terrain, prix affiché,
    COMMUNE et DISTANCE à la parcelle — les CINQ PLUS PROCHES (par distance), uniquement À PROXIMITÉ
    (rayon `_RADAR_RAYON_M`). Le bloc reste vide s'il n'y a aucune annonce proche. + l'écart moyen prix
    affiché vs prix VENDU, servi seulement s'il est mesurable (annonces rattachées à une vente DVF)."""
    out = {"biens": [], "ecart_affiche_vendu_pct": None, "ecart_note": None, "ecart_n": 0}
    tb = type_bien if type_bien in ("maison", "appartement", "terrain") else None
    if idu:
        # distance réelle parcelle ↔ annonce (lat/lng du Radar projetés en 2975) ; les 5 plus proches
        # dans le rayon, toutes communes confondues (une annonce voisine peut être dans une autre commune).
        rows = db.execute(text(
            "WITH subj AS (SELECT ST_Centroid(geom_2975) g FROM parcels WHERE idu = :idu) "
            "SELECT b.type_bien, f.pieces, f.surface_hab, f.surface_terrain, f.prix, b.commune, "
            "       round(ST_Distance("
            "         ST_Transform(ST_SetSRID(ST_MakePoint(b.lng, b.lat), 4326), 2975), subj.g))::int AS distance_m "
            "FROM pige_biens b JOIN pige_faits f ON f.bien_id = b.bien_id CROSS JOIN subj "
            "WHERE b.statut IN ('active', 'en_vente_longue') AND f.prix > 0 "
            "  AND b.lat IS NOT NULL AND b.lng IS NOT NULL "
            "  AND (CAST(:tb AS text) IS NULL OR b.type_bien = :tb) "
            "  AND ST_Distance(ST_Transform(ST_SetSRID(ST_MakePoint(b.lng, b.lat), 4326), 2975), subj.g) <= :ray "
            "ORDER BY distance_m ASC LIMIT :n"),
            {"idu": idu, "tb": tb, "ray": _RADAR_RAYON_M, "n": n}).mappings().all()
    else:
        rows = []
    out["biens"] = [{
        "type": (r["type_bien"] or "").capitalize() or None,
        "pieces": (int(r["pieces"]) if r["pieces"] else None),
        "surface_m2": (round(float(r["surface_hab"])) if r["surface_hab"] else None),
        "terrain_m2": (round(float(r["surface_terrain"])) if r["surface_terrain"] else None),
        "prix_affiche_eur": (round(float(r["prix"])) if r["prix"] else None),
        "commune": r["commune"],
        "distance_m": (int(r["distance_m"]) if r["distance_m"] is not None else None),
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


def _derniere_vente_bien(mut: dict | None) -> dict | None:
    """La DERNIÈRE vente de CE bien (sa propre mutation DVF), MONTRÉE sous la boîte parcelle mais JAMAIS
    utilisée dans le calcul : mois/année · surface bâtie · prix. None si la parcelle n'a aucune vente."""
    if not mut or not mut.get("date"):
        return None
    d = mut["date"]
    mmaaaa = f"{d[5:7]}/{d[0:4]}" if isinstance(d, str) and len(d) >= 7 else None
    return {"date": mmaaaa,
            "surface_m2": (round(mut["bati_m2"]) if (mut.get("bati_m2") or 0) > 0 else None),
            "terrain_m2": (round(mut["terrain_m2"]) if (mut.get("terrain_m2") or 0) > 0 else None),
            "prix_eur": (round(mut["valeur"]) if (mut.get("valeur") or 0) > 0 else None),
            "nature": mut.get("nature")}


def _surface_hab_detail(src: str | None, mut: dict | None, mesures: dict, surface_utilisee) -> dict | None:
    """Comment la surface habitable servie est CONNUE (badge + texte) : « connue » si elle vient d'une
    vente DVF (« Surface de la vente de 2025 (DVF) ») ; « estimée » si calculée depuis le bâti (formule
    complète, LiDAR) ; « saisie » si l'utilisateur l'a entrée."""
    if src == "saisie":
        return {"source": "saisie", "badge": "saisie", "texte": "Votre surface."}
    if src == "vente DVF":
        an = (mut.get("date") or "")[:4] if mut else ""
        return {"source": "vente DVF", "badge": "connue", "annee": (int(an) if an else None),
                "texte": (f"Surface de la vente de {an} (DVF)." if an else "Surface de la dernière vente (DVF).")}
    # estimée depuis le bâti (LiDAR) — formule complète.
    emp = mesures.get("emprise_bati_m2")
    niv = mesures.get("niveaux")
    if emp and surface_utilisee and emp > 0:
        ratio = float(surface_utilisee) / float(emp)
        rf = ("%.1f" % ratio).replace(".", ",")
        nivlib = (f"{niv} niveau" + ("x" if niv > 1 else "")) if niv else "bâti"
        return {"source": "estimée", "badge": "estimée",
                "texte": f"{emp} m² au sol × {nivlib} × {rf}, part habitable moyenne du secteur (LiDAR)."}
    return {"source": "estimée", "badge": "estimée",
            "texte": (mesures.get("surface_hab_estimee_ligne") or "Surface habitable estimée depuis le bâti (LiDAR).")}


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
    derniere_vente = _derniere_vente_bien(mut)
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
        constr = base.get("constructibilite") or {}
        non_constructible = constr.get("constructible") is False
        hors_gamme = bool(base.get("terrain_hors_gamme"))

        # OUTILS-P0-2 (recette, point 4) — TERRAIN NON CONSTRUCTIBLE : AUCUNE estimation. Pas de prix au
        # m² en tête, aucune vente de terrain à bâtir listée (elles induiraient en erreur sur une parcelle
        # qui ne peut rien recevoir). On affiche « Pas d'estimation : zone non constructible (A) » et la
        # dernière vente de la parcelle (servie à part). La raison est dite.
        if non_constructible:
            motif = constr.get("motif") or ""
            zcode = _zone_code(motif) or _zone_code(constr.get("zone_lib")) or _zone_code(zone_lib)
            if zcode:
                raison = f"Pas d’estimation : zone non constructible ({zcode})"
            elif motif:
                m = motif.rstrip(" .")
                raison = "Pas d’estimation : " + (m[0].lower() + m[1:] if m else "zone non constructible")
            else:
                raison = "Pas d’estimation : parcelle non constructible"
            return {"idu": idu, "commune": commune, "type_bien": "terrain",
                    "mesures": mesures,
                    "estimation": {"valeur_eur": None, "valeur_basse": None, "valeur_haute": None,
                                   "valeur_basse_q3": None, "valeur_haute_q3": None, "fourchettes": [],
                                   "eur_m2": None, "n_comparables": None, "repli_secteur": False,
                                   "methode_prix": "secteur", "fiabilite_mot": None,
                                   "terrain_non_constructible": True, "terrain_hors_gamme": False,
                                   "terrain_sans_total_raison": raison,
                                   "comparables_desc": None, "repli_note": None},
                    "ventes_retenues": [],   # aucune vente de terrain à bâtir listée
                    "derniere_vente": derniere_vente,
                    "questions": [], "questions_abandonnees": QUESTIONS_ABANDONNEES,
                    "precision_par_niveau": {}, "radar": [],
                    "note_terrain": raison}

        # Terrain nu CONSTRUCTIBLE : repère de secteur + deux fourchettes (ou une seule si le banc n'en
        # donne qu'une). HORS GAMME (surface > p90 des ventes de référence) → pas de total, mais le repère
        # au m² et les ventes de référence restent (la raison est dite).
        central_t = (base.get("valeur_indicative") or {}).get("valeur_eur")
        sans_total_raison = None
        if hors_gamme:
            central_t = None
            g = base.get("surface_gamme") or {}
            sp = base.get("surface_parcelle_m2")
            detail = (f" (parcelle {_arr_m2(sp)} m², ventes de référence jusqu'à ~{_arr_m2(g.get('p90_m2'))} m²)"
                      if (sp and g.get("p90_m2")) else "")
            sans_total_raison = ("Terrain hors gamme des ventes de référence" + detail
                                 + " — surface trop grande pour un total fiable. Le repère au m² et "
                                 "les ventes de référence restent affichés.")
        _bt = (lambda p: _arrondi_mille(float(central_t) * (1 - p / 100.0))) if central_t else (lambda p: None)
        _ht = (lambda p: _arrondi_mille(float(central_t) * (1 + p / 100.0))) if central_t else (lambda p: None)
        v_basse, v_haute = _bt(prec["ecart_median"]), _ht(prec["ecart_median"])
        v_basse_q3, v_haute_q3 = _bt(prec["ecart_q3"]), _ht(prec["ecart_q3"])
        return {"idu": idu, "commune": commune, "type_bien": "terrain",
                "mesures": mesures,
                "estimation": {"valeur_eur": central_t,
                               "valeur_basse": v_basse, "valeur_haute": v_haute,
                               "valeur_basse_q3": v_basse_q3, "valeur_haute_q3": v_haute_q3,
                               "fourchettes": _fourchettes(v_basse, v_haute, v_basse_q3, v_haute_q3,
                                                           prec["ecart_median"], prec["ecart_q3"]),
                               "surface_utilisee_m2": (base.get("valeur_indicative") or {}).get("surface_m2"),
                               "eur_m2": base.get("median"), "precision_pct": prec["ecart_median"],
                               "precision_q3_pct": prec["ecart_q3"], "ecart_median_pct": prec["ecart_median"],
                               "fiabilite_mot": base.get("fiabilite_mot"),
                               "n_comparables": base.get("n"), "repli_secteur": False,
                               "methode_prix": "secteur",
                               # OUTILS-P0-2 (P2) — total non servi (hors gamme) : la raison voyage écran+PDF.
                               "terrain_sans_total_raison": sans_total_raison,
                               "terrain_hors_gamme": hors_gamme,
                               "terrain_non_constructible": False,
                               "surface_gamme": base.get("surface_gamme"),
                               "comparables_desc": None, "repli_note": None},
                "ventes_retenues": [_vente_retenue({**c, "mid": c.get("date")}, False)
                                    for c in (base.get("comparables") or [])],
                "derniere_vente": derniere_vente,
                "questions": [], "questions_abandonnees": QUESTIONS_ABANDONNEES,
                "precision_par_niveau": {"sans_saisie": prec["ecart_median"]},
                "radar": radar_semblables(db, idu, commune, "terrain"),
                "note_terrain": "Terrain nu : repère de secteur ESTIMER-2 ; la viabilisation n'est pas "
                                "une donnée mesurable, elle n'est pas demandée."}

    est = estimation_semblable(db, idu, fiche, surface_hab=surface_hab, pieces=pieces, ecartees=ecartees)
    type_bien = est["type_bien"]
    mesures = mesures_labuse(db, idu, fiche, nature=type_bien, zone_lib=zone_lib, mut=mut, insee=insee)
    # comment la surface habitable servie est connue (badge connue/estimée/saisie + texte DVF / formule LiDAR).
    est["estimation"]["surface_hab_detail"] = _surface_hab_detail(
        est["estimation"].get("surface_source"), mut, mesures,
        est["estimation"].get("surface_utilisee_m2"))
    return {
        "idu": idu, "commune": commune, "type_bien": type_bien,
        "mesures": mesures,
        "estimation": est["estimation"],
        "ventes_retenues": est["ventes_retenues"],
        "derniere_vente": derniere_vente,
        "niveau_info": est["niveau_info"],
        "precision_par_niveau": est["precision_par_niveau"],
        "questions": _questions_servies(est, type_bien),
        "questions_abandonnees": QUESTIONS_ABANDONNEES,
        "radar": radar_semblables(db, idu, commune, type_bien),
    }
