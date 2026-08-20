"""PROJETS (copilote-projet) — M120 : IDENTITÉ + CADRAGE + SHORTLIST FIGÉE.

UN SEUL système de critères : le `cadrage` EST un jeu de filtres `FiltreCriteres`
sauvegardé (forme `Filters` du front). La dérivation parallèle (`derive_filtres`,
M22) a DISPARU — le run applique le cadrage via `FiltreCriteres.where()`, exactement
le filtrage de la carte. Doctrine : un critère = un seul endroit · le budget (et la
date) sont INFORMATIFS et dits tels quels (aucun effet sur la sélection, mesuré) ·
la shortlist est FIGÉE au cadrage, datée, et ne bouge JAMAIS seule (rejeu explicite).
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import models
from ..scoring.score_v_constants import Q_A_RUN_LABEL as RUN  # run de référence
from .ia import SECTEURS
from .tenant import current_compte



def _caps_projets() -> dict:
    """M129-D P0.2 — caps du flux Projet en CONFIG (config/projets.yaml), plus jamais en dur.
    Repli sur les défauts historiques si la config est absente (base de test nue)."""
    try:
        from .. import config as _cfg
        return _cfg.load_yaml_config("projets")
    except Exception:  # noqa: BLE001
        return {}

def _scope(q, cid: int | None):
    """AUDIT PAIEMENT · SEC-IDOR — restreint une query ORM Projet au compte de la session
    (NULL = bucket pilote/démo). Explicite plutôt que magique : la cloison se lit."""
    return q.filter(models.Projet.compte_id.is_(None) if cid is None
                    else models.Projet.compte_id == cid)

router = APIRouter(prefix="/projets", tags=["projets"])


def get_db():  # branché sur la session app au moment de l'inclusion (cf. app.py)
    from .app import get_db as _g
    yield from _g()


DDL = """
CREATE TABLE IF NOT EXISTS projets (
  id serial PRIMARY KEY,
  nom varchar(160) NOT NULL,
  fiche jsonb NOT NULL DEFAULT '{}'::jsonb,
  filtres jsonb NOT NULL DEFAULT '{}'::jsonb,
  programme jsonb,
  statut varchar(16) NOT NULL DEFAULT 'actif',
  derniere_execution_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE projets ADD COLUMN IF NOT EXISTS identite jsonb NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE projets ADD COLUMN IF NOT EXISTS shortlist_perimee boolean NOT NULL DEFAULT false;
ALTER TABLE pipeline_entries ADD COLUMN IF NOT EXISTS projet_id integer
  REFERENCES projets(id) ON DELETE SET NULL
"""


def ensure_tables(engine) -> None:
    from sqlalchemy import text as _t
    with engine.begin() as c:
        for stmt in DDL.split(";"):
            if stmt.strip():
                c.execute(_t(stmt))
        _migrer_fiche_vers_cadrage(c)


def _migrer_fiche_vers_cadrage(c) -> int:
    """M120 — MIGRATION idempotente, NON destructive : les projets de l'ancien format (fiche 7
    champs + `filtres` dérivé partiel) passent au nouveau format. Le cadrage EST déjà un jeu de
    filtres camelCase (`filtres` : communes/sdpMin/flagsExclus — dérivé M114) → on le garde tel quel
    (rien ne se perd). L'IDENTITÉ informative se remplit depuis la fiche legacy (budget/type). On ne
    touche QUE les projets dont l'identité est encore vide ET qui portent une fiche → rejouable sans
    risque (les colonnes `fiche`/`programme` restent en place)."""
    from sqlalchemy import text as _t
    rows = c.execute(_t("SELECT id, fiche, identite FROM projets "
                        "WHERE (identite = '{}'::jsonb OR identite IS NULL) "
                        "AND fiche IS NOT NULL AND fiche <> '{}'::jsonb")).mappings().all()
    n = 0
    for r in rows:
        fiche = r["fiche"] or {}
        identite = {}
        if fiche.get("budget_foncier_eur") is not None:
            identite["budget_eur"] = int(fiche["budget_foncier_eur"])
        if fiche.get("type_programme"):
            identite["type_logement"] = fiche["type_programme"]   # informatif (mesuré : 0 effet moteur)
        identite["migre_m120"] = True                             # trace : ne pas re-migrer
        c.execute(_t("UPDATE projets SET identite = CAST(:ident AS jsonb) WHERE id = :id"),
                  {"ident": _json(identite), "id": r["id"]})
        n += 1
    return n


def _json(v):
    import json
    return json.dumps(v, ensure_ascii=False)


# M120 · Phase 1 — le RÉFÉRENTIEL des types de logement (servi, jamais figé au front). MESURÉ :
# le moteur ne distingue RIEN par type (0 effet sur la sélection ni le scoring) → le type est
# INFORMATIF. On le sert AVEC son drapeau `informatif` pour que l'écran le dise tel quel — jamais
# un faux critère. Les clés viennent de projet_schema.TYPE_LABEL (source unique du vocabulaire),
# élargies (libre/social) : « logement libre » = le défaut promoteur, « social » (LLS/LES) informatif.
_TYPES_LOGEMENT = [
    {"cle": "libre", "libelle": "Logement libre"},
    {"cle": "social", "libelle": "Logement social"},
    {"cle": "etudiant", "libelle": "Logement étudiant"},
    {"cle": "bureaux", "libelle": "Bureaux / tertiaire"},
    {"cle": "autre", "libelle": "Autre programme"},
]


@router.get("/types")
def projet_types() -> dict:
    """Le référentiel des types de logement (Phase 1). Chaque type est INFORMATIF (mesuré : aucun
    effet moteur) — le drapeau le dit pour que l'écran ne présente jamais un champ informatif comme
    s'il filtrait. Servi, jamais figé au front."""
    return {"types": _TYPES_LOGEMENT, "informatif": True,
            "note": "Le type de logement est indicatif : il figure sur le projet mais n'affecte "
                    "pas la sélection des parcelles (le moteur ne distingue pas par type)."}


# ─────────────────── arbitrages SOURCÉS (chiffres servis par la base) ───────────────────

@router.get("/reperes")
def projet_reperes(dimension: str = Query("secteur", pattern="^(secteur|commune)$"),
                   db: Session = Depends(get_db)) -> dict:
    """Chiffres SOURCÉS par option d'un choix de l'entretien (secteur ou commune) : nombre
    d'opportunités (tiers servis brûlante → à creuser), prix médian du bâti (DVF, €/m²
    habitable) et communes carencées SRU. DÉTERMINISTE, 100 % SQL — l'IA n'en produit AUCUN
    (doctrine : arbitrages sourcés ou tus). Sous les chips : « N opportunités · ~P €/m² ».
    """
    # M36 Lot A (famille M35 Lot D) : « opportunités » = parcelles SERVIES au classement
    # (tiers actifs du run servi) — plus jamais la matrice historique (compteur produit,
    # échappé à l'inventaire M35 ; même dérive que /communes).
    from ..verdict_servi import TIERS_SERVABLES
    opp = {r["commune"]: r["n"] for r in db.execute(text(
        "SELECT p.commune, count(*) n FROM parcels p "
        "JOIN parcel_p_score_v2 s ON s.parcelle_id = p.idu AND s.run_id = :runref "
        " AND s.tier = ANY(:servables) "
        "GROUP BY p.commune"), {"runref": RUN, "servables": list(TIERS_SERVABLES)}).mappings()}
    # prix médian bâti DVF (€/m² habitable) — bornes anti-aberration comme l'affichage marché
    dvf = {r["commune"]: int(r["m"]) for r in db.execute(text(
        "SELECT commune, percentile_cont(0.5) WITHIN GROUP ("
        "  ORDER BY valeur_fonciere / NULLIF(surface_reelle_bati,0)) m "
        "FROM dvf_mutations WHERE surface_reelle_bati > 0 AND valeur_fonciere > 0 "
        "  AND valeur_fonciere / surface_reelle_bati BETWEEN 200 AND 8000 "
        "GROUP BY commune")).mappings() if r["m"]}
    carencees = {r["commune"] for r in db.execute(text(
        "SELECT commune FROM commune_contexte_sru WHERE statut = 'carencee'")).mappings()}

    def bloc(communes: list[str]) -> dict:
        meds = [dvf[c] for c in communes if c in dvf]
        return {
            "nb_opportunites": sum(opp.get(c, 0) for c in communes),
            "dvf_median_eur_m2": round(sum(meds) / len(meds)) if meds else None,
            "communes_carencees": sorted(c for c in communes if c in carencees),
        }

    if dimension == "secteur":
        options = [{"key": s, "label": s, **bloc(SECTEURS[s])} for s in SECTEURS]
    else:
        options = [{"key": c, "label": c, **bloc([c])}
                   for c in sorted(opp, key=lambda x: -opp[x])]
    return {"dimension": dimension, "options": options,
            "note": "Opportunités : parcelles servies au classement (brûlante → à creuser). "
                    "Prix médian : DVF bâti (€/m² habitable). "
                    "Carencées : inventaire SRU. Aucun chiffre produit par l'IA."}


# ─────────────────── M120 · LE CADRAGE = un jeu de filtres FiltreCriteres ───────────────────
# UN SEUL système de critères. Le cadrage est stocké sous la forme `Filters` du front (camelCase).
# Chaque clé connue → l'attribut `FiltreCriteres` (snake_case ; listes → CSV) — le MÊME point
# d'entrée que la carte (`_q_v2_where`). Rejouer un cadrage = rejouer le filtrage de la carte,
# à l'identique (mesuré M120). Une clé inconnue est écartée proprement (jamais un critère inventé).
#: camelCase (cadrage) → (attribut FiltreCriteres, genre) ; genre : "csv" (liste→CSV) · "num" · "bool"
_CADRAGE_MAP: dict[str, tuple[str, str]] = {
    "tiers": ("tiers", "csv"), "scoreMin": ("score_min", "num"),
    "surfaceMin": ("surface_min", "num"), "surfaceMax": ("surface_max", "num"),
    "sdpMin": ("sdp_min", "num"), "sdpMax": ("sdp_max", "num"),
    "evenement": ("evenement", "bool"), "veille": ("veille", "bool"),
    "horsCopro": ("hors_copro", "bool"), "flags": ("flags", "csv"),
    "flagsExclus": ("flags_exclus", "csv"), "communes": ("communes", "csv"),
    "personneMorale": ("personne_morale", "bool"), "zonagePlu": ("zonage", "csv"),
    "constructibilite": ("constructibilite", "csv"), "etatSol": ("etat_sol", "csv"),
    "capaciteMin": ("capacite_min", "num"), "zonePlu": ("zone_plu", "csv"),
    "sousDensite": ("sous_densite", "bool"), "multMin": ("mult_min", "num"),
    "rangMax": ("rang_max", "num"), "renouvellement": ("renouvellement", "bool"),
    "divisionOr": ("division_or", "bool"), "proprietaireType": ("proprietaire_type", "csv"),
    "droitsResiduels": ("droits_residuels", "csv"),
    "etatSociete": ("etat_societe", "csv"), "copro": ("copro", "csv"),
    "npnru": ("npnru", "bool"), "adresseAbsente": ("adresse_absente", "bool"),
    "budgetMax": ("budget_max", "num"), "chargeMin": ("charge_min", "num"),
    "chargeMax": ("charge_max", "num"), "prixMarcheMin": ("prix_marche_min", "num"),
    "prixMarcheMax": ("prix_marche_max", "num"), "marcheFiable": ("marche_fiable", "bool"),
    "caMin": ("ca_min", "num"), "modeBRentable": ("mode_b_rentable", "bool"),
    "modebTravauxM2": ("modeb_travaux_m2", "num"), "modebLoyerM2": ("modeb_loyer_m2", "num"),
    "modebRendementPct": ("modeb_rendement_pct", "num"), "signaux": ("signaux", "csv"),
}


def clean_cadrage(cadrage: dict | None) -> dict:
    """Nettoie un cadrage : ne garde QUE les clés connues (vocabulaire des 44 facettes) et retire
    les valeurs vides (None / "" / [] / False pour les toggles). Une clé hors vocabulaire est
    silencieusement écartée — jamais un critère inventé (doctrine « un critère = un seul endroit »)."""
    out: dict = {}
    for k, (_attr, kind) in _CADRAGE_MAP.items():
        if k not in (cadrage or {}):
            continue
        v = cadrage[k]
        if kind == "bool":
            if v is True:
                out[k] = True
        elif kind == "csv":
            if isinstance(v, list) and v:
                out[k] = list(v)
        else:  # num
            if v is not None:
                out[k] = v
    return out


def _cadrage_to_filtre(cadrage: dict):
    """cadrage (camelCase) → instance `FiltreCriteres` (le point d'entrée unique du filtrage carte).
    Import local : casse le cycle projets ↔ app."""
    from .app import FiltreCriteres
    kw: dict = {"source": RUN}
    for k, v in (cadrage or {}).items():
        spec = _CADRAGE_MAP.get(k)
        if not spec:
            continue
        attr, kind = spec
        if kind == "csv":
            kw[attr] = ",".join(str(x) for x in v) if v else None
        else:
            kw[attr] = v
    return FiltreCriteres(**kw)


def _run_cadrage(db: Session, cadrage: dict, limit: int) -> list[dict]:
    """LE RUN : applique le cadrage (jeu de filtres) via `FiltreCriteres.where()` — exactement le
    filtrage de la carte — et rend la liste best-first. AUCUN re-scoring, AUCUne dérivation parallèle."""
    from .app import _q_v2_list
    fc = _cadrage_to_filtre(cadrage)
    where, params = fc.where()
    return _q_v2_list(db, None, limit, 0, run_label=RUN, extra_where=where, extra_params=params)


def _sdp_besoin(cadrage: dict) -> int | None:
    """La SDP besoin n'est plus dérivée d'un « programme » (M120) : c'est la facette `sdpMin` du
    cadrage, si le promoteur l'a posée. Un seul endroit."""
    v = (cadrage or {}).get("sdpMin")
    return int(v) if v is not None else None


def _nom_repli(identite: dict, cadrage: dict) -> str:
    """Nom de repli déterministe (toujours éditable) : type informatif + périmètre du cadrage."""
    from .projet_schema import TYPE_LABEL as _TL
    t = _TL.get((identite or {}).get("type_logement") or "", "Projet")
    communes = (cadrage or {}).get("communes") or []
    if not communes:
        ou = "toute l'île"
    elif len(communes) == 1:
        ou = communes[0]
    else:
        ou = f"{len(communes)} communes"
    return f"{t} — {ou}"


def _projet_dict(p: models.Projet) -> dict:
    # M120 — le CADRAGE (jeu de filtres) et l'IDENTITÉ (infos) sont les deux faces servies ;
    # `derniere_execution_at` date la shortlist figée, `shortlist_perimee` dit qu'un rejeu est dû.
    return {
        "id": p.id, "nom": p.nom, "statut": p.statut,
        "cadrage": p.filtres or {}, "identite": p.identite or {},
        "shortlist_perimee": bool(p.shortlist_perimee),
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        "derniere_execution_at": (p.derniere_execution_at.isoformat()
                                  if p.derniere_execution_at else None),
    }


# M135 — libellés d'action, mapping CANONIQUE unique (tiers_client). Les clés internes ne bougent pas.
from ..scoring.tiers_client import TIERS_CLIENT as _TC  # noqa: E402
_STATUT_LABEL = {"chaude": "Priorité", "a_surveiller": "À suivre", "a_creuser": "Neutre"}
_TIER_LABEL = {k: v[1] for k, v in _TC.items()}


def _pourquoi_lignes(item: dict, sdp_besoin: int | None, carencees: set[str]) -> list[str]:
    """Le « pourquoi » d'une parcelle RELIÉ au projet — assemblé depuis les DONNÉES du moteur
    (aucune valeur inventée). Ordre : verdict, capacité vs besoin, hauteur PLU, contexte."""
    out: list[str] = []
    statut = item.get("statut") or item.get("status")   # M22 → statut ; q_v2_list → status
    if item.get("etage0"):
        st = "Écartée (exclusion dure)"
    elif item.get("tier_v2") in _TIER_LABEL:
        st = _TIER_LABEL[item["tier_v2"]]
    else:
        # M54-AB F11 : repli sur le libellé CLIENT (verdict_servi), jamais le code technique brut
        # (« ecartee », « declasse_… ») dans le « pourquoi » du projet.
        from ..verdict_servi import TIER_LABELS
        st = _STATUT_LABEL.get(statut) or TIER_LABELS.get(statut) or statut or "—"
    if item.get("q_score") is not None:
        out.append(f"{st} · qualité {item['q_score']}/100")
    else:
        out.append(st)
    # M54-AB F11 : ligne pédagogique quand P (proba de mutation) et Q (qualité intrinsèque)
    # divergent fortement — le classement peut être « chaud » sur une parcelle de qualité limitée.
    _mult, _q = item.get("mult_base"), item.get("q_score")
    _p_eleve = (_mult is not None and _mult >= 1.3) or item.get("tier_v2") in ("brulante", "chaude")
    if _p_eleve and _q is not None and _q < 40:
        out.append("Probabilité de mutation élevée, qualité intrinsèque limitée — voir la fiche.")
    sdp = item.get("sdp") or item.get("sdp_residuelle_m2")
    if sdp and sdp_besoin:
        pct = round(100 * sdp / sdp_besoin)
        cmp = "couvre le besoin" if sdp >= sdp_besoin else f"{pct} % du besoin"
        out.append(f"SDP résiduelle {round(sdp):,} m² pour {sdp_besoin:,} m² requis — {cmp}"
                   .replace(",", " "))
    elif sdp:
        out.append(f"SDP résiduelle {round(sdp):,} m²".replace(",", " "))
    if item.get("hauteur_plu_m") is not None:
        ok = "vérifiée" if item.get("hauteur_verifiee") else "à instruire"
        out.append(f"Hauteur PLU {item['hauteur_plu_m']:.0f} m ({ok})"
                   + (f", zone {item['zone']}" if item.get("zone") else ""))
    if item.get("commune") in carencees:
        out.append("Commune carencée SRU — forte demande de logement social")
    return out


def _pourquoi_court(tier: str | None, carencee: bool, evenement: bool, surface: float | None) -> list[str]:
    """M120 · Phase 4 — le « pourquoi » COURT d'une carte de tri (1-2 lignes), assemblé de signaux
    SOURCÉS (jamais un score interne servi nu) : événement foncier récent, carence SRU, grande
    emprise. Le tier (badge) porte déjà le verdict — on ne le répète pas ici. Aucune ligne inventée :
    liste vide si aucun signal → la carte renvoie à la fiche."""
    out: list[str] = []
    if evenement:
        out.append("Mutation probable — événement foncier récent.")
    if carencee:
        out.append("Commune carencée SRU — forte demande de logement social.")
    if len(out) < 2 and surface and surface >= 2000:
        out.append(f"Grande emprise ({round(surface):,} m²).".replace(",", " "))
    return out[:2]


class ApercuIn(BaseModel):
    cadrage: dict = {}
    identite: dict = {}
    limit: int = 5


@router.post("/apercu")
def projet_apercu(body: ApercuIn, db: Session = Depends(get_db)) -> dict:
    """M120 — Aperçu du CADRAGE : compteur exact (même filtrage que la carte) + top parcelles avec
    leur « pourquoi » SORTI DU MOTEUR. Un seul système : le run applique le jeu de filtres (aucune
    dérivation parallèle, aucun M22). Aucune valeur inventée."""
    cadrage = clean_cadrage(body.cadrage)
    identite = body.identite or {}
    sdp_besoin = _sdp_besoin(cadrage)
    carencees = {r[0] for r in db.execute(text(
        "SELECT commune FROM commune_contexte_sru WHERE statut = 'carencee'")).all()}
    lim = max(1, min(body.limit, 20))
    from .app import _q_v2_stats
    fc = _cadrage_to_filtre(cadrage)
    where, params = fc.where()
    stats = _q_v2_stats(db, None, run_label=RUN, extra_where=where, extra_params=params)
    n = stats["total"]                                # même compteur que la carte (compte = total)
    top = _run_cadrage(db, cadrage, lim)
    top_out = [{
        "idu": it["idu"], "commune": it["commune"],
        "statut": it.get("statut") or it.get("status"),
        "q_score": it.get("q_score"),
        "pourquoi": _pourquoi_lignes(it, sdp_besoin, carencees),
    } for it in top]
    return {"nom": _nom_repli(identite, cadrage), "n": n, "sdp_besoin_m2": sdp_besoin,
            "source": RUN, "top": top_out}


class ProjetIn(BaseModel):
    cadrage: dict = {}                 # M120 : le jeu de filtres (les 44 facettes)
    identite: dict = {}                # M120 : infos (budget_eur / type_logement / date_livraison)
    nom: str | None = None            # éditable ; repli déterministe sinon
    limit: int = 60                    # taille de la shortlist figée (best-first)


class ProjetPatchIn(BaseModel):
    nom: str | None = None
    statut: str | None = None          # actif | archive
    cadrage: dict | None = None        # M120 : modifier le cadrage → shortlist PÉRIMÉE (rejeu proposé)
    identite: dict | None = None       # M120 : infos éditables (n'invalide pas la shortlist)


#: M120 — l'identité informative : les seules clés servies (budget/type/date). Le budget et la date
#: sont AFFICHÉS tels quels — ils n'alimentent AUCUN filtre (mesuré M119/M120). Le type de logement
#: est INFORMATIF : le moteur ne distingue rien par type (mesuré : 0 effet sur la sélection).
_IDENTITE_KEYS = {"budget_eur", "type_logement", "date_livraison"}


def clean_identite(identite: dict | None) -> dict:
    out: dict = {}
    for k in _IDENTITE_KEYS:
        v = (identite or {}).get(k)
        if v not in (None, "", []):
            out[k] = v
    return out


@router.post("/derive")
def projet_derive(body: ProjetIn) -> dict:
    """Prévisualise le NOM de repli d'un cadrage SANS persister (le compteur vivant, lui, vient de
    /apercu ou /filtre — même filtrage que la carte). M120 : plus de dérivation parallèle."""
    cadrage = clean_cadrage(body.cadrage)
    identite = clean_identite(body.identite)
    return {"nom": (body.nom or "").strip()[:160] or _nom_repli(identite, cadrage),
            "cadrage": cadrage, "identite": identite, "sdp_besoin_m2": _sdp_besoin(cadrage)}


def _counts_by_projet(db: Session, projet_ids: list[int]) -> dict[int, dict]:
    """Compteurs de tri (proposee/retenue/ecartee/a_analyser) par projet, en UNE requête —
    alimente les mini-compteurs des fiches projet (Lot 4). Un projet jamais trié → tout à 0.

    M-C (F6) : SCOPÉ aux projets fournis (ceux du compte affiché). Avant : GROUP BY sur TOUTE la
    table projet_parcelles puis on jetait tout sauf le compte courant — aucune fuite (le caller
    filtre) mais un scan global qui grossit avec les tenants pour rien."""
    if not projet_ids:
        return {}
    rows = db.execute(text("SELECT projet_id, statut, count(*) AS n FROM projet_parcelles "
                           "WHERE projet_id = ANY(:ids) GROUP BY projet_id, statut"),
                      {"ids": projet_ids}).all()
    out: dict[int, dict] = {}
    for r in rows:
        out.setdefault(r.projet_id, {})[r.statut] = r.n
    return out


# M114 · Phase 0 (arbitré : vignette RÉELLE) — le SCHÉMA d'emprise de chaque projet : les centroïdes
# des parcelles du projet, normalisés 0–1 dans la bbox du projet, avec le drapeau « retenue ». Le
# front en tire un SVG (contour pour proposée/écartée, aplat mint pour retenue). Une SEULE requête
# batchée pour toute la liste (mesuré ~27 ms/9 projets) ; aucun stockage, aucun cache — lecture live
# de projet_parcelles (une parcelle retenue/écartée se voit au prochain fetch). Projet sans parcelle
# → points vides → le front rend l'initiale de la commune (état vide, jamais un chargement).
_VIGNETTE_MAX_POINTS = 14   # au-delà, un carré de 52–64 px n'est que du bruit


def _vignettes_by_projet(db: Session, projet_ids: list[int]) -> dict[int, list[dict]]:
    if not projet_ids:
        return {}
    rows = db.execute(text(
        "SELECT pc.projet_id AS pid, pc.statut AS st, ST_X(p.centroid) AS x, ST_Y(p.centroid) AS y "
        "FROM projet_parcelles pc JOIN parcels p ON p.id = pc.parcel_id "
        "WHERE pc.projet_id = ANY(:ids) AND p.centroid IS NOT NULL"), {"ids": projet_ids}).all()
    brut: dict[int, list] = {}
    for r in rows:
        brut.setdefault(r.pid, []).append((r.x, r.y, r.st == "retenue"))
    out: dict[int, list[dict]] = {}
    for pid, pts in brut.items():
        xs = [x for x, _, _ in pts]
        ys = [y for _, y, _ in pts]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        dx = (x1 - x0) or 1.0
        dy = (y1 - y0) or 1.0
        # les RETENUES d'abord : garanties visibles si on tronque à _VIGNETTE_MAX_POINTS.
        pts.sort(key=lambda t: not t[2])
        out[pid] = [{"x": round((x - x0) / dx, 4), "y": round((y - y0) / dy, 4), "r": r}
                    for x, y, r in pts[:_VIGNETTE_MAX_POINTS]]
    return out


def _premiere_commune(p: models.Projet) -> str | None:
    # M120 — le périmètre vit dans le cadrage (facette `communes`), plus dans la fiche.
    communes = (p.filtres or {}).get("communes") or []
    return communes[0] if communes else None


def _projet_dict_counts(p: models.Projet, by_projet: dict[int, dict],
                        vignettes: dict[int, list[dict]] | None = None) -> dict:
    c = by_projet.get(p.id, {})
    d = {**_projet_dict(p),
         "counts": {s: c.get(s, 0) for s in ("proposee", "retenue", "ecartee", "a_analyser")}}
    # M114 — la vignette voyage avec la fiche (points normalisés + commune pour l'état vide).
    d["vignette"] = {"commune": _premiere_commune(p),
                     "points": (vignettes or {}).get(p.id, [])}
    return d


@router.get("")
def projets_list(request: Request, db: Session = Depends(get_db)) -> list[dict]:
    """Liste des projets AVEC leurs compteurs de tri (fiches Lot 4) et la VIGNETTE d'emprise (M114).
    Une seule source de vérité : compteurs et vignette viennent de projet_parcelles (l'état réel du
    tri), jamais d'un recompte de recherche. SEC-IDOR : bornée au compte de la session."""
    cid = current_compte(request)
    rows = _scope(db.query(models.Projet), cid).order_by(models.Projet.updated_at.desc()).all()
    ids = [p.id for p in rows]
    by_projet = _counts_by_projet(db, ids)
    vignettes = _vignettes_by_projet(db, ids)
    return [_projet_dict_counts(p, by_projet, vignettes) for p in rows]


def _find_doublon(db: Session, nom: str, filtres: dict, cid: int | None) -> models.Projet | None:
    """Dédup DOUCE (Lot 4) : un projet ACTIF aux mêmes critères dérivés (`filtres`) OU au même nom
    (insensible à la casse) est un doublon. On ne supprime rien — on PROPOSE la reprise de l'existant.
    Compare les filtres en Python (égalité de dict — robuste au JSONB). SEC-IDOR : dans le compte."""
    nom_norm = (nom or "").strip().lower()
    for p in _scope(db.query(models.Projet).filter(models.Projet.statut == "actif"), cid).all():
        if (p.filtres or {}) == filtres or (p.nom or "").strip().lower() == nom_norm:
            return p
    return None


def _figer_shortlist(db: Session, p: models.Projet, limit: int) -> dict:
    """M120 · LE RUN, UNE FOIS — applique le cadrage, ÉCRIT la shortlist (statut `proposee`,
    best-first) et la FIGE (date `derniere_execution_at`). Rejouable : c'est aussi le moteur du
    rejeu. NON destructif — une parcelle déjà décidée (retenue/ecartee/a_analyser) n'est jamais
    re-proposée (ON CONFLICT DO NOTHING). NON-PERTE : une décision qui ne matche plus le cadrage
    RESTE, marquée `hors_criteres` (jamais évincée en silence) ; celle qui rematche est nettoyée.
    Rend le DIFF (entrées/sorties/tris conservés) pour que le rejeu DISE ce qui change."""
    caps = _caps_projets()
    lim = max(1, min(limit or int(caps.get("shortlist_defaut", 60)),
                     int(caps.get("shortlist_max", 200))))  # M129-D : caps en config
    avant = {r.idu: r.statut for r in db.execute(text(
        "SELECT par.idu, pp.statut FROM projet_parcelles pp JOIN parcels par ON par.id = pp.parcel_id "
        "WHERE pp.projet_id = :p"), {"p": p.id}).all()}
    items = _search_items(db, p.filtres or {}, lim)   # point unique (monkeypatchable) → _run_cadrage
    idus = [it["idu"] for it in items]
    id_by_idu = {r.idu: r.id for r in db.execute(
        text("SELECT id, idu FROM parcels WHERE idu = ANY(:idus)"), {"idus": idus})}
    now = datetime.now(timezone.utc)
    ajoutees = 0
    ajoutees_refonte = 0
    # M129-D P4 — une entrée due au NOUVEAU VIVIER se DIT (« entrée par refonte cascade »),
    # jamais un « +N nouvelles » muet qui laisserait croire à un mouvement de marché : une
    # parcelle est « par refonte » si elle était à l'étage 0 du run PRÉCÉDENT (run_precedent.txt).
    from ..scoring.score_v_constants import RUN_PRECEDENT as _prev_run
    _etait_exclue = {r.idu for r in db.execute(text(
        "SELECT par.idu FROM dryrun_parcel_evaluations d JOIN parcels par ON par.id = d.parcel_id "
        "WHERE d.run_label = :prev AND d.status IN ('exclue', 'faux_positif_probable') "
        "AND par.idu = ANY(:idus)"), {"prev": _prev_run, "idus": idus})}
    for rang, it in enumerate(items):
        pc = id_by_idu.get(it["idu"])
        if not pc:
            continue
        res = db.execute(text(
            "INSERT INTO projet_parcelles (projet_id, parcel_id, statut, rang, proposee_at, "
            "created_at, updated_at) VALUES (:pj, :pc, 'proposee', :rg, :now, :now, :now) "
            "ON CONFLICT (projet_id, parcel_id) DO UPDATE SET rang = :rg, updated_at = :now "
            "WHERE projet_parcelles.statut = 'proposee'"),   # ne réécrit QUE les non-décidées
            {"pj": p.id, "pc": pc, "rg": rang, "now": now})
        if res.rowcount and it["idu"] not in avant:
            ajoutees += 1
            if it["idu"] in _etait_exclue:
                ajoutees_refonte += 1
    # NON-PERTE : les décisions hors cadrage RESTENT, marquées ; celles qui rematchent sont nettoyées.
    db.execute(text(
        "UPDATE projet_parcelles pp SET hors_criteres = NOT (par.idu = ANY(:idus)), updated_at = :now "
        "FROM parcels par WHERE par.id = pp.parcel_id AND pp.projet_id = :pj "
        "AND pp.statut IN ('retenue', 'a_analyser', 'ecartee')"),
        {"idus": idus, "pj": p.id, "now": now})
    matched = set(idus)
    sorties = sum(1 for idu, st in avant.items() if idu not in matched and st != "proposee")
    # les 'proposee' d'avant qui ne matchent plus ne sont plus utiles → retirées (pas une décision)
    db.execute(text(
        "DELETE FROM projet_parcelles pp USING parcels par WHERE par.id = pp.parcel_id "
        "AND pp.projet_id = :pj AND pp.statut = 'proposee' AND NOT (par.idu = ANY(:idus))"),
        {"pj": p.id, "idus": idus})
    tris_conserves = sum(1 for st in avant.values() if st in ("retenue", "ecartee", "a_analyser"))
    p.derniere_execution_at = now
    p.shortlist_perimee = False
    db.flush()
    return {"ajoutees": ajoutees, "ajoutees_refonte": ajoutees_refonte,
            "sorties": sorties, "tris_conserves": tris_conserves,
            "n_shortlist": len(idus)}


@router.post("")
def projet_create(body: ProjetIn, request: Request, db: Session = Depends(get_db)) -> dict:
    """M120 — Crée un projet PUIS FIGE sa shortlist EN UNE FOIS (fin du cadrage = le run part une
    fois). DÉDUP DOUCE : un projet actif au même cadrage OU même nom est RENVOYÉ (`existing: true`).
    Le projet revient clôturé, prêt à ouvrir (plus de run à l'ouverture)."""
    cadrage = clean_cadrage(body.cadrage)
    identite = clean_identite(body.identite)
    nom = (body.nom or "").strip()[:160] or _nom_repli(identite, cadrage)
    cid = current_compte(request)
    dup = _find_doublon(db, nom, cadrage, cid)
    if dup is not None:
        return {"ok": True, "existing": True, "projet": _projet_dict(dup)}
    p = models.Projet(nom=nom, filtres=cadrage, identite=identite, compte_id=cid)
    db.add(p)
    db.flush()
    diff = _figer_shortlist(db, p, body.limit)     # LE RUN, une fois → shortlist figée + datée
    return {"ok": True, "existing": False, "projet": _projet_dict(p), "shortlist": diff}


# M2 — fusion des doublons : statut le plus AVANCÉ gagne (retenue > écartée > à analyser > proposée).
_STATUT_PRIORITE = {"retenue": 3, "ecartee": 2, "a_analyser": 1, "proposee": 0}


class FusionIn(BaseModel):
    ids: list[int]


@router.post("/fusionner")
def projets_fusionner(body: FusionIn, request: Request, db: Session = Depends(get_db)) -> dict:
    """Fusionne des projets DOUBLONS en un seul (le plus ancien = cible) : UNION des parcelles et
    des statuts. Conflit de statut entre doublons → le statut le plus AVANCÉ gagne (retenue >
    écartée > à analyser > proposée), tout conflit est SIGNALÉ dans le résultat, jamais résolu en
    silence. Les sources sont ARCHIVÉES (statut='archive'), jamais supprimées → réversible."""
    cid = current_compte(request)
    ids = sorted(set(body.ids))
    if len(ids) < 2:
        raise HTTPException(422, "Fusion : au moins deux projets requis.")
    # SEC-IDOR : chaque projet fusionné doit appartenir au compte (sinon 404, jamais fusion croisée).
    projets = [_scope(db.query(models.Projet).filter(models.Projet.id == i), cid).one_or_none()
               for i in ids]
    if any(pr is None for pr in projets):
        raise HTTPException(404, "Un des projets à fusionner est inconnu.")
    cible, sources = projets[0], projets[1:]             # id min = cible (le plus ancien)
    rows = db.execute(text("SELECT parcel_id, statut FROM projet_parcelles WHERE projet_id = ANY(:ids)"),
                      {"ids": ids}).all()
    by_parcel: dict[int, set[str]] = {}
    for r in rows:
        by_parcel.setdefault(r.parcel_id, set()).add(r.statut)
    now = datetime.now(timezone.utc)
    conflits = []
    for pc, statuts in by_parcel.items():
        gagnant = max(statuts, key=lambda s: _STATUT_PRIORITE.get(s, 0))
        if len(statuts) > 1:
            conflits.append({"parcel_id": pc, "statuts": sorted(statuts), "retenu": gagnant})
        db.execute(text(
            "INSERT INTO projet_parcelles (projet_id, parcel_id, statut, created_at, updated_at) "
            "VALUES (:pj, :pc, :st, :now, :now) "
            "ON CONFLICT (projet_id, parcel_id) DO UPDATE SET statut = :st, updated_at = :now"),
            {"pj": cible.id, "pc": pc, "st": gagnant, "now": now})
        _sync_crm_retenue(db, cible.id, pc, gagnant, now, cid)
    for s in sources:
        s.statut = "archive"                             # réversible : rien n'est supprimé
    db.flush()
    return {"ok": True, "cible": cible.id, "sources_archivees": [s.id for s in sources],
            "n_parcelles": len(by_parcel), "conflits": conflits, **_counts(db, cible.id)}


@router.get("/pour-parcelle/{idu}")
def projets_pour_parcelle(idu: str, request: Request, db: Session = Depends(get_db)) -> dict:
    """F7 (M12) — les projets ACTIFS du compte auxquels cette parcelle est déjà rattachée (id, nom,
    statut de la parcelle dans le projet). Alimente le bouton « Projet » de la fiche : état actif +
    nom du projet si déjà attachée. SEC-IDOR : borné au compte (jointure projets.compte_id).
    Déclaré AVANT `/{pid}` : « pour-parcelle » n'est pas un int, mais on lève l'ambiguïté à la source."""
    cid = current_compte(request)
    # SEC-IDOR : la cloison est branchée en Python (NULL = bucket pilote) — évite un bind NULL
    # non typé côté Postgres (AmbiguousParameter) tout en gardant la clause explicite.
    scope = "p.compte_id IS NULL" if cid is None else "p.compte_id = :cid"
    params: dict = {"idu": idu}
    if cid is not None:
        params["cid"] = cid
    rows = db.execute(text(
        f"""SELECT p.id, p.nom, pp.statut
           FROM projet_parcelles pp
           JOIN projets p ON p.id = pp.projet_id
           JOIN parcels par ON par.id = pp.parcel_id
           WHERE par.idu = :idu AND p.statut = 'actif' AND {scope}
           ORDER BY p.updated_at DESC"""),
        params).mappings().all()
    return {"idu": idu,
            "projets": [{"id": r["id"], "nom": r["nom"], "statut": r["statut"]} for r in rows]}


@router.get("/{pid}")
def projet_get(pid: int, request: Request, db: Session = Depends(get_db)) -> dict:
    p = _projet_or_404(db, pid, current_compte(request))
    return _projet_dict(p)


@router.patch("/{pid}")
def projet_patch(pid: int, body: ProjetPatchIn, request: Request, db: Session = Depends(get_db)) -> dict:
    """M120 — édite un projet. Modifier le CADRAGE n'invalide PAS la shortlist en silence : elle est
    marquée PÉRIMÉE (`shortlist_perimee`) et le front propose un rejeu explicite (jamais un run
    automatique). L'identité (infos) et le nom n'affectent pas la shortlist."""
    p = _projet_or_404(db, pid, current_compte(request))
    if body.nom is not None:
        nom = body.nom.strip()[:160]
        if not nom:
            raise HTTPException(422, "Nom vide")
        p.nom = nom
    if body.statut is not None:
        if body.statut not in ("actif", "archive"):
            raise HTTPException(422, f"Statut invalide : {body.statut}")
        p.statut = body.statut
    if body.identite is not None:
        p.identite = clean_identite(body.identite)
    if body.cadrage is not None:
        nouveau = clean_cadrage(body.cadrage)
        if nouveau != (p.filtres or {}):
            p.filtres = nouveau
            p.shortlist_perimee = True          # la shortlist ne bouge pas seule — rejeu proposé
    db.flush()
    return {"ok": True, "projet": _projet_dict(p)}


@router.delete("/{pid}")
def projet_delete(pid: int, request: Request, db: Session = Depends(get_db)) -> dict:
    """Supprime un projet (les pistes CRM rattachées gardent leur parcelle : projet_id → NULL
    par la FK ON DELETE SET NULL)."""
    p = _projet_or_404(db, pid, current_compte(request))
    db.delete(p)
    db.flush()
    return {"ok": True}


@router.post("/{pid}/rejouer")
def projet_rejouer(pid: int, request: Request, db: Session = Depends(get_db)) -> dict:
    """M120 · REJOUER À LA DEMANDE (geste explicite) — relance le run du cadrage sur les données du
    jour et DIT ce qui change : entrées, sorties du cadrage, tris conservés. Les décisions
    (retenue/écartée/peut-être) SURVIVENT ; une parcelle sortie du cadrage le dit (`hors_criteres`)
    au lieu de disparaître. La shortlist ne bouge JAMAIS seule — seul ce bouton la rafraîchit."""
    p = _projet_or_404(db, pid, current_compte(request))
    diff = _figer_shortlist(db, p, 60)
    return {"ok": True, "projet": _projet_dict(p), "shortlist": diff, **_counts(db, pid)}


# ─────────────────────────  M120 — Parcours de sélection : statuts parcelle×projet  ─────────────────────────
# La shortlist est FIGÉE au cadrage ; ces routes gèrent l'ÉTAT de tri (proposee/retenue/ecartee/
# a_analyser). Zéro re-scoring : les parcelles viennent du run servi, on rattache un statut.

_STATUTS = {"proposee", "retenue", "ecartee", "a_analyser"}
_RETENUE_CRM_STATUS = "contact_a_preparer"    # colonne « Contact à préparer » (cf config/pipeline.yaml)


def _sync_crm_retenue(db: Session, pid: int, parcel_id: int, statut: str, now: datetime,
                      cid: int | None) -> None:
    """Auto-CRM + cohérence (Phase 2). `retenue` ⇒ crée l'entrée pipeline liée au projet (à
    contacter) ; quitter `retenue` ⇒ retire l'entrée AUTO-liée à CE projet (une entrée manuelle
    d'un autre projet est préservée : ON CONFLICT DO NOTHING / DELETE ciblé sur projet_id).
    SEC-IDOR : l'entrée pipeline créée porte le compte du projet."""
    if statut == "retenue":
        # M12 LOT H : les colonnes sont PAR TENANT — la carte doit atterrir dans une colonne que
        # CE compte possède réellement (sinon elle serait invisible = carte perdue en silence).
        # « Contact à préparer » si présente, sinon la 1re colonne du kanban du compte.
        from . import crm_columns
        keys = crm_columns.col_keys(db, cid)
        st = _RETENUE_CRM_STATUS if _RETENUE_CRM_STATUS in keys else crm_columns.default_status(db, cid)
        db.execute(text(
            "INSERT INTO pipeline_entries (parcel_id, status, priority, notes, prospection, "
            "projet_id, compte_id, created_at, updated_at) VALUES (:pc, :st, 'moyenne', '', "
            "'{}'::jsonb, :pid, :cid, :now, :now) ON CONFLICT (compte_id, parcel_id) DO NOTHING"),
            {"pc": parcel_id, "st": st, "pid": pid, "cid": cid, "now": now})
    else:
        db.execute(text("DELETE FROM pipeline_entries WHERE parcel_id = :pc AND projet_id = :pid"),
                   {"pc": parcel_id, "pid": pid})


def _projet_or_404(db: Session, pid: int, cid: int | None) -> models.Projet:
    # SEC-IDOR : un projet d'un AUTRE compte → 404 (jamais un 403 qui confirmerait l'existence).
    p = _scope(db.query(models.Projet).filter(models.Projet.id == pid), cid).one_or_none()
    if not p:
        raise HTTPException(404, "Projet inconnu")
    return p


def _counts(db: Session, pid: int) -> dict:
    """Compteurs par statut (progression + sections)."""
    rows = db.execute(text("SELECT statut, count(*) AS n FROM projet_parcelles "
                           "WHERE projet_id = :p GROUP BY statut"), {"p": pid}).all()
    c = {r.statut: r.n for r in rows}
    return {"counts": {s: c.get(s, 0) for s in ("proposee", "retenue", "ecartee", "a_analyser")}}


def _search_items(db: Session, cadrage: dict, limit: int, overrides: dict | None = None) -> list[dict]:
    """M120 — applique le CADRAGE (jeu de filtres), best-first. `overrides` assouplit une facette
    pour « chercher plus » (communes=None → toute l'île ; surfaceMin↓). Un seul moteur : le run
    servi via `FiltreCriteres.where()` (le même filtrage que la carte)."""
    c = {**(cadrage or {}), **(overrides or {})}
    c = {k: v for k, v in c.items() if v is not None}   # None efface une facette (chercher-plus île)
    return _run_cadrage(db, c, limit)


class ProposerIn(BaseModel):
    limit: int = 60


@router.post("/{pid}/proposer")
def projet_proposer(pid: int, body: ProposerIn, request: Request, db: Session = Depends(get_db)) -> dict:
    """M120 — (re)fige la shortlist du cadrage (idempotent, non destructif). Même moteur que la
    création et le rejeu. Le front n'appelle PLUS ceci à l'ouverture — la shortlist est déjà figée."""
    p = _projet_or_404(db, pid, current_compte(request))
    diff = _figer_shortlist(db, p, body.limit)
    return {"ok": True, "propose": diff["n_shortlist"], "shortlist": diff,
            "sdp_besoin_m2": _sdp_besoin(p.filtres or {}), **_counts(db, pid)}


@router.get("/{pid}/parcelles")
def projet_parcelles(pid: int, request: Request, db: Session = Depends(get_db)) -> dict:
    """L'ÉTAT du parcours : les parcelles du projet groupées par statut (proposées best-first),
    avec centroïde pour la carte. Base de la reprise (fermer/rouvrir = relire cet état)."""
    p = _projet_or_404(db, pid, current_compte(request))
    from .app import _score_v2_run_id, _ETAT_BIEN_SQL
    v2 = _score_v2_run_id(db)
    rows = db.execute(text(
        f"""SELECT pp.statut, pp.rang, pp.hors_criteres, par.idu, par.commune, par.surface_m2,
                  d.q_score, s2.tier, {_ETAT_BIEN_SQL} AS etat_bien,
                  ST_X(ST_Transform(ST_Centroid(par.geom_2975), 4326)) AS lng,
                  ST_Y(ST_Transform(ST_Centroid(par.geom_2975), 4326)) AS lat
           FROM projet_parcelles pp
           JOIN parcels par ON par.id = pp.parcel_id
           LEFT JOIN dryrun_parcel_evaluations d ON d.parcel_id = par.id AND d.run_label = :run
           LEFT JOIN parcel_p_score_v2 s2 ON s2.parcelle_id = par.idu AND s2.run_id = :v2
           LEFT JOIN parcel_residuel rb ON rb.parcel_id = par.id   -- M131 P3 : 1 ligne/parcelle
           WHERE pp.projet_id = :pid
           ORDER BY pp.rang NULLS LAST, pp.id"""),
        {"run": RUN, "v2": v2, "pid": pid}).mappings().all()
    # M2 — badges parcelle (défisc / PC caduc), gardés to_regclass : absents en base → pas de badge, jamais d'erreur.
    all_idus = [r["idu"] for r in rows]
    defisc_set, caduc_set = set(), set()
    if all_idus:
        for tbl, col, dest in (("defisc_fenetres", "AND fenetre_active", defisc_set), ("pc_caducs", "", caduc_set)):
            try:
                if db.execute(text("SELECT to_regclass(:t)"), {"t": tbl}).scalar() is not None:
                    dest.update(x[0] for x in db.execute(
                        text(f"SELECT idu FROM {tbl} WHERE idu = ANY(:ids) {col}"), {"ids": all_idus}))
            except Exception:  # noqa: BLE001 - badge optionnel, jamais bloquant
                pass
    # M120 · Phase 4 — enrichissement BATCH de la carte de tri (jamais un calcul client) :
    #  · adresse postale BAN ;  · événement rouge (mutation probable, run servi) ;
    #  · prix marché médian de la COMMUNE (DVF bâti, dit « commune » — jamais présenté par parcelle) ;
    #  · carence SRU. De ces signaux SOURCÉS on assemble un « pourquoi » COURT (_pourquoi_court).
    from .export_commun import adresses_ban, format_adresse
    adrs = {i: format_adresse(a) for i, a in adresses_ban(db, all_idus).items()} if all_idus else {}
    event_set = set()
    if all_idus:
        event_set = {x[0] for x in db.execute(text(
            "SELECT DISTINCT p.idu FROM dryrun_cascade_results cr JOIN parcels p ON p.id = cr.parcel_id "
            "WHERE cr.run_label = :r AND cr.evenement = 'rouge' AND p.idu = ANY(:ids)"),
            {"r": RUN, "ids": all_idus})}
    communes_lst = list({r["commune"] for r in rows if r["commune"]})
    marche = {r["commune"]: int(r["m"]) for r in db.execute(text(
        "SELECT commune, percentile_cont(0.5) WITHIN GROUP ("
        "  ORDER BY valeur_fonciere / NULLIF(surface_reelle_bati,0)) m "
        "FROM dvf_mutations WHERE surface_reelle_bati > 0 AND valeur_fonciere > 0 "
        "  AND valeur_fonciere / surface_reelle_bati BETWEEN 200 AND 8000 AND commune = ANY(:cs) "
        "GROUP BY commune"), {"cs": communes_lst}).mappings() if r["m"]} if communes_lst else {}
    carencees = {x[0] for x in db.execute(text(
        "SELECT commune FROM commune_contexte_sru WHERE statut = 'carencee'")).all()}

    groups: dict[str, list] = {s: [] for s in ("proposee", "retenue", "ecartee", "a_analyser")}
    for r in rows:
        evt = r["idu"] in event_set
        groups.setdefault(r["statut"], []).append({
            "idu": r["idu"], "commune": r["commune"], "statut": r["statut"],
            "tier": r["tier"], "surface_m2": r["surface_m2"],
            "etat_bien": r["etat_bien"],   # M131 P3 : nu | bati_encore | bati_max (affichage)
            "adresse": adrs.get(r["idu"]), "evenement": evt,
            "marche_eur_m2": marche.get(r["commune"]),
            "pourquoi": _pourquoi_court(r["tier"], r["commune"] in carencees, evt, r["surface_m2"]),
            "hors_criteres": bool(r["hors_criteres"]),
            "defisc": r["idu"] in defisc_set, "caduc": r["idu"] in caduc_set,
            "center": [round(r["lng"], 6), round(r["lat"], 6)] if r["lng"] is not None else None,
        })
    # PRIVACY : les RETENUES portent le contact proprio (elles vont au CRM) — personne morale nommée
    # (public DGFiP), particulier JAMAIS nommé (« non communiqué »). Réutilise le helper du CRM.
    from .app import _proprietaire_public
    for it in groups["retenue"]:
        it["proprietaire_public"] = _proprietaire_public(db, it["idu"])
    return {"nom": p.nom, "sdp_besoin_m2": _sdp_besoin(p.filtres or {}),
            "proposees": groups["proposee"], "retenues": groups["retenue"],
            "ecartees": groups["ecartee"], "a_analyser": groups["a_analyser"], **_counts(db, pid)}


@router.get("/{pid}/carte/{idu}")
def projet_carte_decision(pid: int, idu: str, request: Request, db: Session = Depends(get_db)) -> dict:
    """Carte de DÉCISION d'une parcelle : adresse, tier, scores + POINTS CLÉS (forces/attentions
    dérivés des facteurs — même logique déterministe que le pack apporteur). Aucune valeur
    inventée : tout vient de `_q_v2_fiche` (run servi). Le front ajoute « voir la fiche complète »."""
    _projet_or_404(db, pid, current_compte(request))
    from .app import _q_v2_fiche
    from .partners import _points_cles
    f = _q_v2_fiche(db, idu)
    forces, attentions = _points_cles(f.get("lines") or [])
    sv = f.get("score_v2") or {}
    return {
        "idu": f["idu"], "adresse": f.get("adresse"), "commune": f.get("commune"),
        "surface_m2": f.get("surface_m2"), "tier": sv.get("tier"), "statut": f.get("statut"),
        "q_score": f.get("q_score"), "a_score": f.get("a_score"),
        "completeness": f.get("completeness_score"), "center": f.get("coords"),
        "forces": [{"titre": t, "detail": d} for _, t, d in forces],
        "attentions": [{"titre": t, "detail": d} for _, t, d in attentions],
    }


class StatutIn(BaseModel):
    statut: str


@router.patch("/{pid}/parcelle/{idu}")
def projet_parcelle_statut(pid: int, idu: str, body: StatutIn, request: Request, db: Session = Depends(get_db)) -> dict:
    """Fixe le statut d'une parcelle dans le projet (le geste Tinder ET la récupération d'une
    écartée). RÉVERSIBLE : repasser en `proposee`/`retenue` depuis `ecartee` ne perd rien."""
    _projet_or_404(db, pid, current_compte(request))
    if body.statut not in _STATUTS:
        raise HTTPException(422, f"Statut invalide : {body.statut}")
    pc = db.execute(text("SELECT id FROM parcels WHERE idu = :i"), {"i": idu}).scalar()
    if not pc:
        raise HTTPException(404, f"Parcelle {idu} inconnue")
    now = datetime.now(timezone.utc)
    db.execute(text(
        "INSERT INTO projet_parcelles (projet_id, parcel_id, statut, created_at, updated_at) "
        "VALUES (:pj, :pc, :st, :now, :now) "
        "ON CONFLICT (projet_id, parcel_id) DO UPDATE SET statut = :st, updated_at = :now"),
        {"pj": pid, "pc": pc, "st": body.statut, "now": now})
    _sync_crm_retenue(db, pid, pc, body.statut, now, current_compte(request))   # auto-CRM (Phase 2)
    db.flush()
    return {"ok": True, "idu": idu, "statut": body.statut, **_counts(db, pid)}


# ─── Chercher plus (Phase 2) : élargir la recherche / ajouter une parcelle à la main ───

def _upsert_proposee(db: Session, pid: int, parcel_id: int, rang: int, now: datetime) -> bool:
    """Rattache une parcelle en `proposee` — DÉDUP par la contrainte unique (une parcelle déjà
    dans le projet, quel que soit son statut, n'est PAS re-proposée). True si réellement ajoutée."""
    res = db.execute(text(
        "INSERT INTO projet_parcelles (projet_id, parcel_id, statut, rang, proposee_at, "
        "created_at, updated_at) VALUES (:pj, :pc, 'proposee', :rg, :now, :now, :now) "
        "ON CONFLICT (projet_id, parcel_id) DO NOTHING"),
        {"pj": pid, "pc": parcel_id, "rg": rang, "now": now})
    return res.rowcount == 1


class ChercherPlusIn(BaseModel):
    limit: int = 24
    surface_min: float | None = None    # assouplir la surface minimale
    ile: bool = False                   # élargir le périmètre à toute l'île


@router.post("/{pid}/chercher-plus")
def projet_chercher_plus(pid: int, body: ChercherPlusIn, request: Request, db: Session = Depends(get_db)) -> dict:
    """Élargit la recherche (critères assouplis) et ajoute les NOUVELLES parcelles en `proposee`
    (dédupliquées). Zéro re-scoring : même moteur que la proposition, filtres relâchés."""
    p = _projet_or_404(db, pid, current_compte(request))
    overrides: dict = {}
    if body.ile:
        overrides["communes"] = None
    if body.surface_min is not None:
        overrides["surfaceMin"] = body.surface_min
    caps = _caps_projets()
    lim = max(1, min(body.limit, int(caps.get("shortlist_max", 200))))  # M129-D : chercher-plus
    # rejoint shortlist_max — la dette M122 « cap 60 » est morte : un projet peut demander
    # jusqu'au plafond CONFIG, et la shortlist DIT toujours son univers (M120-B).
    items = _search_items(db, p.filtres or {}, lim, overrides=overrides or None)
    idus = [it["idu"] for it in items]
    id_by_idu = {r.idu: r.id for r in db.execute(
        text("SELECT id, idu FROM parcels WHERE idu = ANY(:idus)"), {"idus": idus})}
    maxr = db.execute(text("SELECT COALESCE(MAX(rang), -1) FROM projet_parcelles WHERE projet_id = :p"),
                      {"p": pid}).scalar() or -1
    now = datetime.now(timezone.utc)
    added = 0
    for i, it in enumerate(items):
        pc = id_by_idu.get(it["idu"])
        if pc and _upsert_proposee(db, pid, pc, maxr + 1 + i, now):
            added += 1
    db.flush()
    return {"ok": True, "n_added": added, "n_search": len(items),
            "elargi": bool(overrides), **_counts(db, pid)}


class AjouterIn(BaseModel):
    idu: str


@router.post("/{pid}/ajouter")
def projet_ajouter(pid: int, body: AjouterIn, request: Request, db: Session = Depends(get_db)) -> dict:
    """Ajoute UNE parcelle précise (par IDU, ou clic-carte côté front) en `proposee`. Dédupliqué :
    `already=true` si elle est déjà dans le projet (quel que soit son statut)."""
    _projet_or_404(db, pid, current_compte(request))
    pc = db.execute(text("SELECT id FROM parcels WHERE idu = :i"), {"i": body.idu}).scalar()
    if not pc:
        raise HTTPException(404, f"Parcelle {body.idu} inconnue")
    maxr = db.execute(text("SELECT COALESCE(MAX(rang), -1) FROM projet_parcelles WHERE projet_id = :p"),
                      {"p": pid}).scalar() or -1
    added = _upsert_proposee(db, pid, pc, maxr + 1, datetime.now(timezone.utc))
    db.flush()
    return {"ok": True, "added": added, "already": not added, "idu": body.idu, **_counts(db, pid)}


@router.get("/{pid}/export.pdf")
def projet_export_pdf(pid: int, request: Request, db: Session = Depends(get_db)):
    """Dossier PROJET en PDF : la fiche de cadrage + les meilleures parcelles avec leur
    « pourquoi » (aperçu recalculé sur les données ACTUELLES). Mécanique fpdf2 existante."""
    from fastapi.responses import Response

    from .export_commun import adresses_ban, format_adresse
    from .pdf_projet import render_projet_pdf
    p = _projet_or_404(db, pid, current_compte(request))   # SEC-IDOR : export borné au compte
    apercu = projet_apercu(ApercuIn(cadrage=p.filtres or {}, identite=p.identite or {}, limit=5), db)
    # M6 2a : adresse postale BAN de chaque parcelle du top (1 requête, page 1 du PDF)
    adrs = adresses_ban(db, [it["idu"] for it in apercu.get("top", [])])
    for it in apercu.get("top", []):
        it["adresse_ban"] = format_adresse(adrs.get(it["idu"]))
    pdf = render_projet_pdf(_projet_dict(p), apercu)
    slug = "".join(c if c.isalnum() else "-" for c in (p.nom or "projet")).strip("-").lower()[:48]
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="projet-{slug or pid}.pdf"'})
