"""RADAR — RATTACHEMENT V2 : convergence de PLUSIEURS critères indépendants (mandat RATTACHEMENT-V2).

Mesure du Lot 0 (RATTACHEMENT-V2) qui fonde cette cascade :
  · surface terrain SEULE (V1) tombait sur une candidate unique dans 7/33 cas, mais ~40 % de justesse :
    la moitié étaient des PARCELLES VIDES (une maison « rattachée » à un terrain nu) ;
  · ajouter l'EMPRISE BÂTIE (BD TOPO) élimine ces faux positifs (une parcelle sans bâti ne peut pas
    porter une maison) → C1∩C2 : 3/33 uniques, 3/3 plausibles à l'ortho ;
  · DVF « à l'envers » ne converge JAMAIS avec la position (C1∩C3 = 0) et n'isole jamais une parcelle
    seule ; DPE et piscine : 0 signal dans le corpus du portail ; Sitadel : bruyant. Ils restent codés
    (ils coûtent peu et peuvent converger ailleurs) mais ne portent pas le résultat.

DOCTRINE V2 : RATTACHÉE exige AU MOINS DEUX critères INDÉPENDANTS qui convergent sur la MÊME parcelle,
et on STOCKE lesquels avec leurs valeurs — un rattachement dont on ne peut pas dire pourquoi il tient
n'est pas un rattachement (le jour où l'un se révèle faux, on doit retrouver ce qui l'a produit). Une
seule candidate d'un SEUL critère reste une PISTE. Trois états : RATTACHÉE / PISTE / NON RATTACHÉE.
Un bien à_qualifier n'est jamais rattaché (garde tenue à l'ingestion). Aucun automatisme ne part d'une
PISTE. Aucun appel réseau (doctrine §2) : on ne lit QUE des données déjà en base.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

RAYON_M = 150            # rayon serré autour du point flouté (Lot 0 : au-delà, l'unicité s'effondre)
TOL_SURFACE = 0.10       # ±10 % surface terrain (cadastre vs annonce) ET DVF terrain — élargi (S5) :
#                          la surface annoncée est souvent arrondie/approximative (« terrain d'environ
#                          500 m² »), ±5 % ratait des candidates légitimes ; ±10 % ré-ouvre la piste sans
#                          diluer (la convergence ≥2 critères reste la garde contre le faux positif).
TOL_DVF_BATI = 0.15      # ±15 % surface réelle bâtie DVF vs surface habitable (habitable ≈ bâti, approx.)
TOL_DPE = 0.10           # ±10 % surface habitable DPE
# Emprise au sol : sans le nombre d'étages, une fourchette LARGE (combles/varangues/garages font varier
# le rapport habitable/emprise). Le rôle DISCRIMINANT est la BORNE BASSE : elle élimine la parcelle vide
# (une maison a une emprise ; un terrain nu, non). Avec les étages, on resserre autour de habitable/étages.
EMPRISE_MIN_ABS = 25     # m² — sous ce bâti, pas une maison (abri de jardin, parcelle nue) : BORNE
#                          DISCRIMINANTE (élimine le faux positif « parcelle vide » du surface-seul).
EMPRISE_LO_FACTEUR = 0.30
EMPRISE_HI_FACTEUR = 1.80  # borne haute large : varangues, garages, annexes gonflent l'emprise au-delà
#                            de la surface habitable (Lot 0 : 5070, bâti 225 pour 135 m² habitables).
MAX_PISTES = 12          # au-delà, trop ambigu même comme piste → NON RATTACHÉE

_TYPES_RATTACHABLES = ("maison", "terrain", "immeuble")
_TYPES_BATIS = ("maison", "immeuble")


def _insee(commune: str) -> str | None:
    from .. import communes
    return communes._OFFICIAL_BY_NAME.get(commune)


def _f(x) -> float | None:
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


# ── DÉTECTEURS DE CRITÈRE ─── chacun renvoie {idu: "valeur lisible"} pour les parcelles candidates ──

def _crit_surface(db: Session, lon, lat, commune, terrain) -> dict[str, str]:
    """C1 — surface cadastrale ≈ surface terrain annoncée (±5 %), dans le rayon du point flouté."""
    if terrain is None:
        return {}
    lo, hi = terrain * (1 - TOL_SURFACE), terrain * (1 + TOL_SURFACE)
    rows = db.execute(text(
        """SELECT p.idu, p.surface_m2 FROM parcels p WHERE p.commune = :c
           AND p.surface_m2 BETWEEN :lo AND :hi
           AND ST_DWithin(p.geom_2975, ST_Transform(ST_SetSRID(ST_MakePoint(:lon,:lat),4326),2975), :r)"""),
        {"c": commune, "lo": lo, "hi": hi, "lon": lon, "lat": lat, "r": RAYON_M}).mappings().all()
    return {r["idu"]: f"terrain {r['surface_m2']:.0f} m² ≈ {terrain:.0f} m² annoncés "
                      f"({abs(r['surface_m2']-terrain)/terrain*100:.0f} %)" for r in rows}


def _emprise_bornes(hab: float, etages) -> tuple[float, float]:
    et = _f(etages)
    if et and et >= 1:
        cible = hab / et
        return max(EMPRISE_MIN_ABS, cible * 0.6), cible * 1.4     # resserré autour de habitable/étages
    return max(EMPRISE_MIN_ABS, hab * EMPRISE_LO_FACTEUR), hab * EMPRISE_HI_FACTEUR


def _crit_emprise(db: Session, lon, lat, commune, hab, etages) -> dict[str, str]:
    """C2 — emprise bâtie (BD TOPO) plausible pour une maison de `hab` m², dans le rayon. La borne basse
    élimine la parcelle vide (le faux positif cardinal du surface-seul)."""
    if hab is None:
        return {}
    lo, hi = _emprise_bornes(hab, etages)
    rows = db.execute(text(
        """SELECT p.idu, mb.emprise_bati_m2 FROM parcels p JOIN p_model_bati mb ON mb.idu = p.idu
           WHERE p.commune = :c AND mb.emprise_bati_m2 BETWEEN :lo AND :hi
           AND ST_DWithin(p.geom_2975, ST_Transform(ST_SetSRID(ST_MakePoint(:lon,:lat),4326),2975), :r)"""),
        {"c": commune, "lo": lo, "hi": hi, "lon": lon, "lat": lat, "r": RAYON_M}).mappings().all()
    return {r["idu"]: f"emprise bâtie {r['emprise_bati_m2']:.0f} m² (attendu {lo:.0f}-{hi:.0f})" for r in rows}


def _crit_dvf(db: Session, insee, hab, terrain) -> dict[str, str]:
    """C3 — DVF à l'envers : une mutation « Maison » de bâti ≈ habitable ET terrain ≈ terrain, dans la
    commune. Position-indépendant (ne dépend pas du floutage). Couverture DVF limitée (millésimes récents)."""
    if not insee or hab is None or terrain is None:
        return {}
    rows = db.execute(text(
        """SELECT DISTINCT id_parcelle, surface_reelle_bati, surface_terrain, EXTRACT(YEAR FROM date_mutation) an
           FROM dvf_mutations_parcelle WHERE code_commune = :ins AND type_local = 'Maison'
           AND surface_reelle_bati BETWEEN :bl AND :bh AND surface_terrain BETWEEN :tl AND :th"""),
        {"ins": insee, "bl": hab*(1-TOL_DVF_BATI), "bh": hab*(1+TOL_DVF_BATI),
         "tl": terrain*(1-TOL_SURFACE), "th": terrain*(1+TOL_SURFACE)}).mappings().all()
    return {r["id_parcelle"]: f"vente DVF {int(r['an'])} : bâti {r['surface_reelle_bati']:.0f} × terrain "
                              f"{r['surface_terrain']:.0f}" for r in rows if r["id_parcelle"]}


def _crit_dpe(db: Session, insee, hab, annee) -> dict[str, str]:
    """C5 — DPE ADEME (déjà rattaché aux parcelles) : surface habitable ≈ ET commune (ET année si connue)
    → parcelle. 0 signal dans le corpus observé du portail (quasi tout « non soumis au DPE »)."""
    if not insee or hab is None:
        return {}
    rows = db.execute(text(
        """SELECT DISTINCT parcelle_idu, surface_habitable FROM dpe_records
           WHERE code_insee = :ins AND parcelle_idu IS NOT NULL
           AND surface_habitable BETWEEN :lo AND :hi
           AND (CAST(:an AS double precision) IS NULL OR annee_construction IS NULL
                OR abs(annee_construction - :an) <= 2)"""),
        {"ins": insee, "lo": hab*(1-TOL_DPE), "hi": hab*(1+TOL_DPE), "an": _f(annee)}).mappings().all()
    return {r["parcelle_idu"]: f"DPE {r['surface_habitable']:.0f} m²" for r in rows if r["parcelle_idu"]}


def _crit_piscine(db: Session, idus: set[str]) -> dict[str, str]:
    """C6 — piscine détectée (ortho 20 cm) sur la parcelle candidate. FILTRE binaire : n'a de sens que
    parmi des candidates déjà trouvées (une piscine seule ne localise rien). 0 signal dans le corpus."""
    if not idus:
        return {}
    rows = db.execute(text(
        "SELECT idu FROM parcel_equipements WHERE idu = ANY(:i) AND piscine = true"),
        {"i": list(idus)}).mappings().all()
    return {r["idu"]: "piscine détectée (ortho)" for r in rows}


def _distances(db: Session, idus: set[str], lon, lat) -> dict[str, float]:
    if not idus or lon is None or lat is None:
        return {}
    rows = db.execute(text(
        """SELECT idu, ST_Distance(geom_2975, ST_Transform(ST_SetSRID(ST_MakePoint(:lon,:lat),4326),2975)) d
           FROM parcels WHERE idu = ANY(:i)"""), {"i": list(idus), "lon": lon, "lat": lat}).mappings().all()
    return {r["idu"]: round(float(r["d"]), 1) for r in rows}


def rattacher(db: Session, rec: dict) -> dict:
    """Cascade V2. Retourne {etat, niveau, idu, confiance, criteres:[…], pistes:[…], motif?}.
    `criteres` = les critères convergents de la parcelle RATTACHÉE (vide sinon). `pistes` = candidates,
    chacune avec les critères qui l'ont désignée. Ne lève jamais (un défaut = NON RATTACHÉE)."""
    typ = rec.get("type")
    if typ == "appartement" or rec.get("est_copro"):
        return _non("appartement en copropriété — position = quartier")
    if typ not in _TYPES_RATTACHABLES:
        return _non(f"type « {typ or '?'} » non rattachable — position = quartier")
    lon, lat, commune = rec.get("lng"), rec.get("lat"), rec.get("commune")
    if lon is None or lat is None or not commune:
        return _non("aucune coordonnée exploitable — position = quartier")
    insee = _insee(commune)
    hab = _f(rec.get("surface_hab"))
    terrain = _f(rec.get("surface_terrain"))
    est_bati = typ in _TYPES_BATIS

    # L'UNIVERS des candidates est POSITIONNEL (dans le rayon du point flouté) : surface ∪ emprise.
    # DVF/DPE/piscine sont position-INDÉPENDANTS (commune-large) : mesuré au Lot 0, seuls, ils désignent
    # des parcelles à plusieurs kilomètres (bruit). On ne les laisse donc PAS introduire de candidate —
    # ils CORROBORENT une candidate déjà retenue par la position (2ᵉ critère indépendant), jamais plus.
    detect: dict[str, dict[str, str]] = {"surface": _crit_surface(db, lon, lat, commune, terrain)}
    if est_bati:
        detect["emprise"] = _crit_emprise(db, lon, lat, commune, hab, rec.get("etages"))
    univers = set().union(*[set(d) for d in detect.values()]) if detect else set()
    if not univers:
        return _non("aucune parcelle candidate dans le rayon (surface/emprise) — quartier retenu")

    corrob: dict[str, dict[str, str]] = {}
    if est_bati:
        corrob["dvf"] = {i: v for i, v in _crit_dvf(db, insee, hab, terrain).items() if i in univers}
        corrob["dpe"] = {i: v for i, v in _crit_dpe(db, insee, hab, rec.get("annee_construction")).items() if i in univers}
    if rec.get("piscine"):
        corrob["piscine"] = _crit_piscine(db, univers)

    # agrège par parcelle : quels critères la désignent, avec leurs valeurs.
    par_idu: dict[str, list[dict]] = {}
    for crit, hits in {**detect, **corrob}.items():
        for idu, val in hits.items():
            par_idu.setdefault(idu, []).append({"critere": crit, "valeur": val})

    dist = _distances(db, set(par_idu), lon, lat)
    # une piste = une candidate avec ses critères ; triée par nb de critères puis distance.
    pistes = sorted(
        ({"idu": idu, "criteres": crits, "n_criteres": len(crits), "distance_m": dist.get(idu)}
         for idu, crits in par_idu.items()),
        key=lambda p: (-p["n_criteres"], p["distance_m"] if p["distance_m"] is not None else 1e9))

    # RATTACHÉE : une SEULE parcelle porte ≥ 2 critères indépendants.
    convergentes = [p for p in pistes if p["n_criteres"] >= 2]
    if len(convergentes) == 1:
        p = convergentes[0]
        conf = min(0.95, 0.75 + 0.10 * (p["n_criteres"] - 2))   # 2 critères → 0.75 ; +0.10 par critère
        return {"etat": "rattachee", "niveau": "source", "idu": p["idu"], "confiance": round(conf, 2),
                "criteres": p["criteres"], "pistes": pistes[:MAX_PISTES],
                "etage": "+".join(sorted(c["critere"] for c in p["criteres"]))}
    if len(convergentes) > 1:
        # plusieurs parcelles à ≥2 critères : ambiguïté → PISTE (jamais un pin faussement sûr).
        return _piste(pistes, motif=f"{len(convergentes)} parcelles à ≥2 critères — à instruire")
    # aucune convergence : des candidates d'un seul critère → PISTE ; sinon rien d'exploitable.
    if len(pistes) <= MAX_PISTES:
        return _piste(pistes, motif="candidates d'un seul critère — à instruire")
    return _non(f"{len(pistes)} candidates d'un seul critère — trop ambigu, quartier retenu")


def criteres_pour_idu(db: Session, rec: dict, idu: str) -> list[dict]:
    """RATTACHEMENT-V2 (Lot 2) — pour UNE parcelle candidate, l'état de CHAQUE critère applicable :
    convergent (matche) ou divergent (testé mais ne matche pas), avec sa valeur. Sert l'écran Instruire :
    le client voit POURQUOI une candidate est proposée, et ce qui cloche."""
    commune = rec.get("commune")
    insee = _insee(commune or "")
    hab = _f(rec.get("surface_hab"))
    terrain = _f(rec.get("surface_terrain"))
    est_bati = rec.get("type") in _TYPES_BATIS
    p = db.execute(text(
        """SELECT p.surface_m2, COALESCE(mb.emprise_bati_m2, 0) bati,
                  COALESCE(pe.piscine, false) piscine
           FROM parcels p LEFT JOIN p_model_bati mb ON mb.idu = p.idu
           LEFT JOIN parcel_equipements pe ON pe.idu = p.idu WHERE p.idu = :i"""),
        {"i": idu}).mappings().first()
    if not p:
        return []
    out: list[dict] = []

    def add(crit, converge, valeur):
        out.append({"critere": crit, "converge": bool(converge), "valeur": valeur})

    if terrain is not None:
        ecart = abs(float(p["surface_m2"]) - terrain) / terrain
        add("surface", ecart <= TOL_SURFACE,
            f"terrain {p['surface_m2']:.0f} m² vs {terrain:.0f} annoncés ({ecart*100:.0f} %)")
    if est_bati and hab is not None:
        lo, hi = _emprise_bornes(hab, rec.get("etages"))
        add("emprise", lo <= float(p["bati"]) <= hi,
            f"emprise bâtie {p['bati']:.0f} m² (attendu {lo:.0f}-{hi:.0f})")
    if est_bati and insee and hab is not None and terrain is not None:
        d = _crit_dvf(db, insee, hab, terrain)
        add("dvf", idu in d, d.get(idu, "pas de vente DVF concordante sur cette parcelle"))
    if rec.get("piscine"):
        add("piscine", bool(p["piscine"]),
            "piscine détectée (ortho)" if p["piscine"] else "aucune piscine détectée")
    return out


def _non(motif: str) -> dict:
    return {"etat": "non_rattachee", "niveau": "absent", "idu": None, "confiance": None,
            "criteres": [], "pistes": [], "motif": motif}


def _piste(pistes: list[dict], *, motif: str) -> dict:
    return {"etat": "piste", "niveau": "estime", "idu": None,
            "confiance": None, "criteres": [], "pistes": pistes[:MAX_PISTES], "motif": motif}
