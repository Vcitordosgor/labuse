"""PROJETS (copilote-projet) — M120 : IDENTITÉ + CADRAGE + SHORTLIST FIGÉE.

UN SEUL système de critères : le `cadrage` EST un jeu de filtres `FiltreCriteres`
sauvegardé (forme `Filters` du front). La dérivation parallèle (`derive_filtres`,
M22) a DISPARU — le run applique le cadrage via `FiltreCriteres.where()`, exactement
le filtrage de la carte. Doctrine : un critère = un seul endroit · le budget (et la
date) sont INFORMATIFS et dits tels quels (aucun effet sur la sélection, mesuré) ·
la shortlist est FIGÉE au cadrage, datée, et ne bouge JAMAIS seule (rejeu explicite).
"""
from __future__ import annotations

import time as _time
from datetime import datetime, timedelta, timezone

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
ALTER TABLE projets ADD COLUMN IF NOT EXISTS cadrage_total integer;
ALTER TABLE projets ADD COLUMN IF NOT EXISTS cadrage_total_at timestamptz;
ALTER TABLE pipeline_entries ADD COLUMN IF NOT EXISTS projet_id integer
  REFERENCES projets(id) ON DELETE SET NULL
"""


def ensure_tables(engine) -> None:
    from sqlalchemy import text as _t
    with engine.begin() as c:
        from ..db import sql_statements  # FIX-GB-011 : plus de split(';') naif
        for stmt in sql_statements(DDL):
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
    "tiers": ("tiers", "csv"),   # FIX-SCOREMIN : scoreMin retiré (FiltreCriteres n'a plus score_min)
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


def _run_cadrage(db: Session, cadrage: dict, limit: int, offset: int = 0,
                 exclude_idus: list[str] | None = None) -> list[dict]:
    """LE RUN : applique le cadrage (jeu de filtres) via `FiltreCriteres.where()` — exactement le
    filtrage de la carte — et rend la liste best-first. AUCUN re-scoring, AUCUne dérivation parallèle.
    M140 Lot A — `offset` + `exclude_idus` : la LISTE COMPLÈTE des retenues se FEUILLETTE en direct
    (page par page, jamais tout chargé), en excluant les parcelles déjà décidées (stockées)."""
    from .app import _q_v2_list
    fc = _cadrage_to_filtre(cadrage)
    where, params = fc.where()
    if exclude_idus:
        where = f"{where} AND p.idu <> ALL(:_excl_idus)"   # p = parcels (alias du moteur de liste)
        params = {**params, "_excl_idus": list(exclude_idus)}
    return _q_v2_list(db, None, limit, offset, run_label=RUN, extra_where=where, extra_params=params)


def _cadrage_page_idus(db: Session, cadrage: dict, limit: int, offset: int,
                       exclude_idus: list[str] | None = None) -> list[str]:
    """M140 Lot A — la PAGE d'IDU du cadrage, best-first (rang), en direct et paginée. Chemin LÉGER :
    on ne veut QUE les idu ordonnés (l'enrichissement carte — adresse/marché/centroïde — se fait
    ensuite en batch sur la seule page). Évite l'enrichissement d'affichage lourd de `_q_v2_list`
    (BAN latéral, propriétaire, cluster…) : ~2,2 s → quelques ms. Même population que `_cadrage_total`
    (plancher sliver, hors étage 0 sauf filtre tiers), même ordre que le figeage (`s2.rang ASC`)."""
    if (cadrage or {}).get("__de_zero__"):
        return []                                   # OUTILS-5 (P3) — projet « de zéro » : vivier VIDE
    from .app import _ETAGE0_SQL, MIN_DISPLAY_SURFACE_M2, _score_v2_run_id
    fc = _cadrage_to_filtre(cadrage)
    where, params = fc.where()
    base = "" if ("f_tiers" in params or "s2.tier" in where or _ETAGE0_SQL in where) \
        else f"AND NOT {_ETAGE0_SQL}"
    excl = ""
    if exclude_idus:
        excl = "AND p.idu <> ALL(:_excl)"
        params = {**params, "_excl": list(exclude_idus)}
    return list(db.execute(text(
        f"SELECT p.idu FROM parcels p "
        f"JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run "
        f"JOIN parcel_p_score_v2 s2 ON s2.parcelle_id = p.idu AND s2.run_id = :v2run "
        f"WHERE (p.surface_m2 IS NULL OR p.surface_m2 >= :minsurf) {base} {where} {excl} "
        f"ORDER BY s2.rang ASC NULLS LAST, p.idu ASC LIMIT :lim OFFSET :off"),
        {"run": RUN, "v2run": _score_v2_run_id(db), "minsurf": MIN_DISPLAY_SURFACE_M2,
         "lim": limit, "off": offset, **params}).scalars().all())


#: M120-B — le cap de la shortlist figée vient de config/projets.yaml (jamais en dur). Défaut nommé
#: en UN seul endroit, si le fichier manque (config error) — plus aucun 60/200 épars dans le code.
_SHORTLIST_MAX_DEFAUT = 200


def _shortlist_max() -> int:
    from ..config import load_yaml_config
    try:
        return int(load_yaml_config("projets").get("shortlist_max", _SHORTLIST_MAX_DEFAUT))
    except Exception:  # noqa: BLE001 — fichier absent/illisible : on retombe sur le défaut nommé
        return _SHORTLIST_MAX_DEFAUT


def _vivier_figeable(db: Session, cadrage: dict) -> int:
    """M120-B — le VIVIER RÉELLEMENT FIGEABLE d'un cadrage : les parcelles qui peuvent entrer dans la
    shortlist, c.-à-d. celles du cadrage HORS exclusions dures (non constructibles / faux positifs =
    étage 0). C'est le dénominateur honnête (« top N sur M »), pas le total gonflé du compteur carte
    (qui compte aussi les 79 % d'étage 0 — mesuré — qui ne peuvent jamais être triées)."""
    from .app import _ETAGE0_SQL, _score_v2_run_id
    fc = _cadrage_to_filtre(cadrage)
    where, params = fc.where()
    return db.execute(text(
        "SELECT count(*) FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id = d.parcel_id "
        "LEFT JOIN parcel_p_score_v2 s2 ON s2.parcelle_id = p.idu AND s2.run_id = :v2run "
        f"WHERE d.run_label = :run AND NOT {_ETAGE0_SQL}{where}"),
        {"run": RUN, "v2run": _score_v2_run_id(db), **params}).scalar() or 0


def _cadrage_total(db: Session, cadrage: dict) -> dict:
    """M130-5 §A / M130-6 §C — cardinal de l'ensemble dont la shortlist est EXTRAITE (même population que
    `_run_cadrage` / `_q_v2_list` sans la limite : sliver < 2 m², base étage 0 sauf filtre `tiers`
    explicite, cadrage) ET sa part à l'étage 0. `{total, etage0}` ; `total=None` sur échec réel
    (exception) — un 0 légitime n'est pas un échec ; jamais `_vivier_figeable` (autre population)."""
    if (cadrage or {}).get("__de_zero__"):
        return {"total": 0, "etage0": 0}            # OUTILS-5 (P3) — projet « de zéro » : vivier VIDE
    try:
        from .app import _ETAGE0_SQL, MIN_DISPLAY_SURFACE_M2, _score_v2_run_id
        fc = _cadrage_to_filtre(cadrage)
        where, params = fc.where()
        base = "" if ("f_tiers" in params or "s2.tier" in where or _ETAGE0_SQL in where) \
            else f"AND NOT {_ETAGE0_SQL}"
        r = db.execute(text(
            f"SELECT count(*) AS total, count(*) FILTER (WHERE {_ETAGE0_SQL}) AS etage0 FROM parcels p "
            "JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run "
            "JOIN parcel_p_score_v2 s2 ON s2.parcelle_id = p.idu AND s2.run_id = :v2run "
            f"WHERE (p.surface_m2 IS NULL OR p.surface_m2 >= :minsurf) {base} {where}"),
            {"run": RUN, "v2run": _score_v2_run_id(db),
             "minsurf": MIN_DISPLAY_SURFACE_M2, **params}).mappings().first()
        return {"total": int(r["total"]), "etage0": int(r["etage0"])}
    except Exception:  # noqa: BLE001 — échec RÉEL de requête → None → État 3 (INDISPONIBLE) à l'affichage
        return {"total": None, "etage0": None}


def _residuel_run_servi(db: Session) -> dict | None:
    """M139 Lot 2 (F2) — le run résiduel SERVI (M135), source des valeurs (SDP/zone/cause) que le
    dossier RELIT en live. Rend `{label, seq, date}` pour DATER ces valeurs au rendu (« valeurs au
    JJ/MM (run N) ») : l'avertissement en prose devient une donnée. `None` si indisponible (table
    absente / aucun run servi) → l'affichage retombe sur la seule date de cadrage, jamais un mensonge.
    Aucun `MAX`/tri : lecture directe du flag `is_served` (doctrine run servi M135)."""
    try:
        r = db.execute(text("SELECT label, run_seq, created_at FROM residuel_runs "
                            "WHERE is_served")).mappings().first()
        if not r:
            return None
        return {"label": r["label"], "seq": int(r["run_seq"]),
                "date": r["created_at"].date().isoformat() if r["created_at"] else None}
    except Exception:  # noqa: BLE001 — migration résiduel non faite → pas de date de valeurs
        return None


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


def _refresh_cadrage_total(db: Session, p: models.Projet) -> int | None:
    """FIX-PROJETS (fin M140) — (re)calcule et MET EN CACHE le total VIF du cadrage (`_cadrage_total`,
    mesuré ~0,2 s commune / ~1 s île). Le compteur « proposées » servi à la LISTE lit ce cache
    (fraîcheur `cadrage_total_at`), plus jamais le figé de la shortlist. Rafraîchi à la création / au
    rejeu / au changement de cadrage / à l'ouverture. Échec réel (None) → garde l'ancienne valeur."""
    r = _cadrage_total(db, p.filtres or {})
    if r.get("total") is not None:
        p.cadrage_total = int(r["total"])
        p.cadrage_total_at = datetime.now(timezone.utc)
    return p.cadrage_total


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
# M137 — le CHIP COURT (v[0]) : un seul vocabulaire servi partout, celui des chips.
_TIER_LABEL = {k: v[0] for k, v in _TC.items()}


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
    out.append(st)   # M130-2 §2.4 : « qualité X/100 » et « Probabilité de mutation » retirés (code mort —
                     # `q_score`/`mult_base` jamais servis par _q_v2_list ; et proscrits sur un exportable).
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


class CadrageIn(BaseModel):
    cadrage: dict = {}


# GB-024b — CACHE du compteur de cadrage. `_q_v2_stats(île)` = ~9,5 s (agrégation full-run avec 2
# joins, structurellement lourde ; `_vivier_figeable` ~0,75 s). Le compteur (vivier/total/cap) d'un
# cadrage donné est STABLE pour un run → on le mémorise EN PROCESS avec un TTL et on SERT sa fraîcheur
# (`calcule_le`), même esprit que le cache `cadrage_total` des projets. La clé inclut le run servi
# (RUN, constante de process) : un changement de run redémarre le process → cache purgé.
_COMPTEUR_CACHE: dict[str, tuple[float, dict]] = {}
_COMPTEUR_TTL_S = 600   # 10 min — la donnée d'un run ne bouge pas dans la vie du process
_REUNION_TZ = timezone(timedelta(hours=4))


def _compteur_cle(cadrage: dict) -> str:
    import hashlib
    import json as _json
    return hashlib.md5((RUN + "|" + _json.dumps(cadrage, sort_keys=True)).encode()).hexdigest()


@router.post("/compteur")
def projet_compteur(body: CadrageIn, db: Session = Depends(get_db)) -> dict:
    """PROJETS-FIX F1 — le compteur du CADRAGE, sorti de LA MÊME requête que le compteur « À trier »
    du projet ouvert : `_cadrage_total(...)["total"]`. C'est, PAR CONSTRUCTION, le nombre que le
    projet servira (`/{pid}/parcelles` appelle `_cadrage_total` sur le même cadrage) — le wizard ne
    peut plus annoncer un nombre que le projet dément.

    Le champ `total` (compte carte GONFLÉ par ~79 % d'exclusions dures — mesuré) est RETIRÉ : il était
    la source du mirage « le wizard annonce 30 000, le projet montre 0 » (le récap lisait `r.total`).
    On ne sert plus qu'UN nombre — le vivier réel, triable. `cap` = taille max de la shortlist figée.

    GB-024b — le cadrage ÎLE coûte ~1 s. On MÉMORISE le résultat par (run, cadrage) avec un TTL et on
    sert sa fraîcheur `calcule_le` : le 1er appel paie, les suivants sont instantanés. La VALEUR est
    identique (même requête), seul le chemin change."""
    cadrage = clean_cadrage(body.cadrage)
    cle = _compteur_cle(cadrage)
    hit = _COMPTEUR_CACHE.get(cle)
    if hit and (_time.time() - hit[0]) < _COMPTEUR_TTL_S:
        return {**hit[1], "cache": True}
    vivier = _cadrage_total(db, cadrage)["total"] or 0   # F1 — LA source unique du « vivier à trier »
    res = {"vivier": vivier, "cap": _shortlist_max(), "cache": False,
           "calcule_le": datetime.now(_REUNION_TZ).isoformat(timespec="minutes")}
    _COMPTEUR_CACHE[cle] = (_time.time(), res)
    return res


class ApercuIn(BaseModel):
    cadrage: dict = {}
    identite: dict = {}
    limit: int = 5


@router.post("/apercu")
def projet_apercu(body: ApercuIn, db: Session = Depends(get_db)) -> dict:
    """M120 — Aperçu du CADRAGE : compteur FIGEABLE (hors exclusions dures) + top parcelles avec leur
    « pourquoi » SORTI DU MOTEUR. Un seul système : le run applique le jeu de filtres (aucune
    dérivation parallèle, aucun M22). Aucune valeur inventée. M120-B : `n` = vivier figeable (pas le
    total gonflé), `total` gardé à part pour la transparence."""
    cadrage = clean_cadrage(body.cadrage)
    identite = body.identite or {}
    sdp_besoin = _sdp_besoin(cadrage)
    carencees = {r[0] for r in db.execute(text(
        "SELECT commune FROM commune_contexte_sru WHERE statut = 'carencee'")).all()}
    lim = max(1, min(body.limit, 20))
    from .app import _q_v2_stats
    fc = _cadrage_to_filtre(cadrage)
    where, params = fc.where()
    total = _q_v2_stats(db, None, run_label=RUN, extra_where=where, extra_params=params)["total"]
    n = _vivier_figeable(db, cadrage)                 # M120-B — le vivier RÉEL, hors exclusions dures
    top = _run_cadrage(db, cadrage, lim)
    top_out = [{
        "idu": it["idu"], "commune": it["commune"],
        "statut": it.get("statut") or it.get("status"),
        # M139 bricole : `q_score` retiré — jamais peuplé par `_q_v2_list` (toujours None) et non rendu.
        "pourquoi": _pourquoi_lignes(it, sdp_besoin, carencees),
    } for it in top]
    return {"nom": _nom_repli(identite, cadrage), "n": n, "total": total,
            "cap": _shortlist_max(), "sdp_besoin_m2": sdp_besoin, "source": RUN, "top": top_out}


class ProjetIn(BaseModel):
    cadrage: dict = {}                 # M120 : le jeu de filtres (les 44 facettes)
    identite: dict = {}                # M120 : infos (budget_eur / type_logement)
    nom: str | None = None            # éditable ; repli déterministe sinon
    limit: int | None = None           # M120-B : None → cap de config (config/projets.yaml), plus de 60 en dur
    de_zero: bool = False              # OUTILS-5 (P3) : projet « de zéro » — naît VIDE (aucun vivier figé)


class ProjetPatchIn(BaseModel):
    nom: str | None = None
    statut: str | None = None          # actif | archive
    cadrage: dict | None = None        # M120 : modifier le cadrage → shortlist PÉRIMÉE (rejeu proposé)
    identite: dict | None = None       # M120 : infos éditables (n'invalide pas la shortlist)


#: M120 — l'identité informative : les seules clés servies (budget/type). Le budget est AFFICHÉ tel
#: quel — il n'alimente AUCUN filtre (mesuré M119/M120). Le type de logement est INFORMATIF : le
#: moteur ne distingue rien par type (mesuré : 0 effet). M120-B : `date_livraison` retirée du flux.
_IDENTITE_KEYS = {"budget_eur", "type_logement"}


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


def _projet_dict_counts(p: models.Projet, by_projet: dict[int, dict]) -> dict:
    # M120-B — la vignette d'emprise (M114) est RETIRÉE de la liste : la ligne garde titre, commune,
    # contexte, compteur à trier et bande d'état. Plus de schéma de centroïdes servi.
    # FIX-PROJETS (fin M140) — le compteur « proposées » est le TOTAL VIF du cadrage MOINS les décidées
    # (retenue/écartée/à-analyser, stockées), EXACTEMENT comme à l'ouverture — plus jamais le figé de
    # la shortlist. Le total vif vient du CACHE `cadrage_total` (fraîcheur `proposee_at`). Les décidées
    # restent lues de projet_parcelles (état réel du tri).
    c = by_projet.get(p.id, {})
    decidees = c.get("retenue", 0) + c.get("ecartee", 0) + c.get("a_analyser", 0)
    proposee = max(0, (p.cadrage_total or 0) - decidees)
    return {**_projet_dict(p),
            "counts": {"proposee": proposee, "retenue": c.get("retenue", 0),
                       "ecartee": c.get("ecartee", 0), "a_analyser": c.get("a_analyser", 0)},
            "proposee_at": p.cadrage_total_at.isoformat() if p.cadrage_total_at else None}


@router.get("")
def projets_list(request: Request, db: Session = Depends(get_db)) -> list[dict]:
    """Liste des projets AVEC leurs compteurs de tri (fiches Lot 4). Une seule source de vérité : les
    compteurs viennent de projet_parcelles (l'état réel du tri), jamais d'un recompte de recherche.
    SEC-IDOR : bornée au compte de la session. M120-B : plus de vignette d'emprise.
    FIX-PROJETS — le compteur « proposées » = total VIF du cadrage (cache `cadrage_total`). Un projet
    au cache FROID (legacy, jamais ouvert depuis le fix) est rafraîchi ICI, une fois (~0,2-1 s) ; les
    ouvertures/rejeux suivants le tiennent à jour. Jamais de retour au figé."""
    cid = current_compte(request)
    rows = _scope(db.query(models.Projet), cid).order_by(models.Projet.updated_at.desc()).all()
    for p in rows:
        if p.cadrage_total is None:                 # cache froid → amorçage unique (borné au compte)
            _refresh_cadrage_total(db, p)
    db.flush()
    ids = [p.id for p in rows]
    by_projet = _counts_by_projet(db, ids)
    return [_projet_dict_counts(p, by_projet) for p in rows]


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
    best-first) et la FIGE (date `derniere_execution_at`).

    FIX-PROJETS (fin M140) — RÔLE RECENTRÉ : le figé sert désormais l'EXPORT UNIQUEMENT (PDF/CSV,
    snapshot REPRODUCTIBLE et DATÉ « cadrage figé le JJ/MM »). Le compteur « proposées » (liste ET
    ouverture) ne lit PLUS ces lignes stockées : il sert le total VIF du cadrage (cache `cadrage_total`
    − décidées). Les DÉCISIONS (retenue/écartée/à-analyser) restent, elles, l'état réel du tri.
    Rejouable : c'est aussi le moteur du
    rejeu. NON destructif — une parcelle déjà décidée (retenue/ecartee/a_analyser) n'est jamais
    re-proposée (ON CONFLICT DO NOTHING). NON-PERTE : une décision qui ne matche plus le cadrage
    RESTE, marquée `hors_criteres` (jamais évincée en silence) ; celle qui rematche est nettoyée.
    Rend le DIFF (entrées/sorties/tris conservés) pour que le rejeu DISE ce qui change."""
    caps = _caps_projets()
    cap = int(caps.get("shortlist_max", 200))         # M120-B — cap servi (dénominateur du « top N sur M »)
    lim = max(1, min(limit or int(caps.get("shortlist_defaut", 60)), cap))  # M129-D — caps en config
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
    # M120-B — le DÉNOMINATEUR HONNÊTE : le vivier figeable (hors exclusions dures). La shortlist se
    # DIT « top {n} sur {vivier} » (ou « c'est tout le vivier » si vivier ≤ cap) — jamais « tout ce
    # qui matche ». `tronquee` : y a-t-il plus de figeables que le cap ?
    # M129-D P4 — `ajoutees_refonte` : les entrées dues au nouveau vivier (refonte cascade), dites au rejeu.
    vivier = _vivier_figeable(db, p.filtres or {})
    return {"ajoutees": ajoutees, "ajoutees_refonte": ajoutees_refonte,
            "sorties": sorties, "tris_conserves": tris_conserves,
            "n_shortlist": len(idus), "vivier": vivier, "cap": cap, "tronquee": vivier > len(idus)}


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
    # OUTILS-5 (P3) — « projet de zéro » : cadrage sentinelle `__de_zero__` (vivier VIDE, jamais figé) ;
    # on y ajoute des parcelles UNE À UNE depuis leurs fiches (→ Retenues).
    if body.de_zero:
        cadrage = {"__de_zero__": True}
    p = models.Projet(nom=nom, filtres=cadrage, identite=identite, compte_id=cid)
    db.add(p)
    db.flush()
    diff = None if body.de_zero else _figer_shortlist(db, p, body.limit)   # LE RUN, une fois (sauf « de zéro »)
    _refresh_cadrage_total(db, p)                   # FIX-PROJETS — amorce le cache du total VIF (compteur liste)
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
        if body.statut != p.statut:                 # M139 Lot 1 — les cartes CRM suivent la transition
            _sync_crm_projet_statut(db, pid, body.statut, datetime.now(timezone.utc), current_compte(request))
        p.statut = body.statut
    if body.identite is not None:
        p.identite = clean_identite(body.identite)
    if body.cadrage is not None:
        nouveau = clean_cadrage(body.cadrage)
        if nouveau != (p.filtres or {}):
            p.filtres = nouveau
            p.shortlist_perimee = True          # la shortlist ne bouge pas seule — rejeu proposé
            _refresh_cadrage_total(db, p)        # FIX-PROJETS — le cache VIF suit le nouveau cadrage
    db.flush()
    return {"ok": True, "projet": _projet_dict(p)}


@router.delete("/{pid}")
def projet_delete(pid: int, request: Request, db: Session = Depends(get_db)) -> dict:
    """M139 Lot 1 (F1) — plus de suppression DURE. Ce endpoint ARCHIVE désormais le projet
    (soft, réversible via PATCH statut=actif), exactement comme le PATCH statut=archive, et ses
    cartes CRM SUIVENT l'archivage (plus d'orphelinage). Le travail de tri (`projet_parcelles`)
    et le figeage sont CONSERVÉS. Aucun chemin ne détruit plus la shortlist ni les décisions.
    Miroir du DELETE→archive du pipeline CRM (M137)."""
    p = _projet_or_404(db, pid, current_compte(request))
    if p.statut != "archive":
        _sync_crm_projet_statut(db, pid, "archive", datetime.now(timezone.utc), current_compte(request))
        p.statut = "archive"
    db.flush()
    return {"ok": True, "archived": True}


@router.post("/{pid}/rejouer")
def projet_rejouer(pid: int, request: Request, db: Session = Depends(get_db)) -> dict:
    """M120 · REJOUER À LA DEMANDE (geste explicite) — relance le run du cadrage sur les données du
    jour et DIT ce qui change : entrées, sorties du cadrage, tris conservés. Les décisions
    (retenue/écartée/peut-être) SURVIVENT ; une parcelle sortie du cadrage le dit (`hors_criteres`)
    au lieu de disparaître. La shortlist ne bouge JAMAIS seule — seul ce bouton la rafraîchit."""
    p = _projet_or_404(db, pid, current_compte(request))
    diff = _figer_shortlist(db, p, None)   # M120-B : cap de config (snapshot EXPORT figé + daté)
    _refresh_cadrage_total(db, p)          # FIX-PROJETS — le rejeu rafraîchit aussi le cache VIF
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
        # M137 — si l'entrée auto de CE projet avait été ARCHIVÉE (quitter/revenir en retenue), la
        # RESTAURER ; jamais toucher une entrée manuelle/d'un autre projet (WHERE projet_id = :pid).
        db.execute(text(
            "INSERT INTO pipeline_entries (parcel_id, status, priority, notes, prospection, "
            "projet_id, compte_id, created_at, updated_at) VALUES (:pc, :st, 'moyenne', '', "
            "'{}'::jsonb, :pid, :cid, :now, :now) ON CONFLICT (compte_id, parcel_id) DO UPDATE "
            "SET archived_at = NULL WHERE pipeline_entries.projet_id = :pid "
            "AND pipeline_entries.archived_at IS NOT NULL"),
            {"pc": parcel_id, "st": st, "pid": pid, "cid": cid, "now": now})
    else:
        # M137 — plus de suppression DURE : on ARCHIVE l'entrée auto-liée (réversible, prospection
        # conservée). « Aucune carte perdue » — même la synchro projet ne détruit plus rien.
        db.execute(text("UPDATE pipeline_entries SET archived_at = :now "
                        "WHERE parcel_id = :pc AND projet_id = :pid AND archived_at IS NULL"),
                   {"pc": parcel_id, "pid": pid, "now": now})


def _sync_crm_projet_statut(db: Session, pid: int, statut: str, now: datetime, cid: int | None) -> None:
    """M139 Lot 1 (F1) — quand un PROJET est archivé/restauré, ses cartes CRM SUIVENT au lieu
    d'être orphelinées ou perdues. `archive` ⇒ archive les entrées pipeline liées à CE projet
    (réversible, prospection conservée) ; `actif` ⇒ les restaure. Ciblé `projet_id` : une carte
    manuelle ou d'un autre projet n'est jamais touchée. Miroir de `_sync_crm_retenue` (M137).
    FIX-PROJETS (P5, défense en profondeur) — l'UPDATE re-filtre `compte_id` : `projet_id` est déjà
    une PK GLOBALE vérifiée-appartenante (pas une fuite, cf. audit), mais la ceinture évite qu'un
    futur refactor du gate amont n'ouvre une écriture cross-compte par id."""
    if statut == "archive":
        db.execute(text("UPDATE pipeline_entries SET archived_at = :now, updated_at = :now "
                        "WHERE projet_id = :pid AND archived_at IS NULL "
                        "AND compte_id IS NOT DISTINCT FROM :cid"),
                   {"pid": pid, "now": now, "cid": cid})
    elif statut == "actif":
        db.execute(text("UPDATE pipeline_entries SET archived_at = NULL, updated_at = :now "
                        "WHERE projet_id = :pid AND archived_at IS NOT NULL "
                        "AND compte_id IS NOT DISTINCT FROM :cid"),
                   {"pid": pid, "now": now, "cid": cid})


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
    limit: int | None = None           # M120-B : None → cap de config


@router.post("/{pid}/proposer")
def projet_proposer(pid: int, body: ProposerIn, request: Request, db: Session = Depends(get_db)) -> dict:
    """M120 — (re)fige la shortlist du cadrage (idempotent, non destructif). Même moteur que la
    création et le rejeu. Le front n'appelle PLUS ceci à l'ouverture — la shortlist est déjà figée."""
    p = _projet_or_404(db, pid, current_compte(request))
    diff = _figer_shortlist(db, p, body.limit)
    return {"ok": True, "propose": diff["n_shortlist"], "shortlist": diff,
            "sdp_besoin_m2": _sdp_besoin(p.filtres or {}), **_counts(db, pid)}


def _analyse_cadrage(db: Session, cadrage: dict) -> dict:
    """PROJETS-V5 (E2) — pour le BANDEAU D'ANALYSE et les chips de tri : le total du cadrage (MÊME
    population que les compteurs de filtres, `_cadrage_total`) ET le décompte des SIGNALÉES par tier
    (Priorité = brûlante, À suivre = chaude). Une seule requête, un FILTER par tier — jamais un moteur
    parallèle. `signalees` = P + S ; les `total − signalees` autres suivent sans jugement."""
    if (cadrage or {}).get("__de_zero__"):
        return {"total": 0, "priorite": 0, "a_suivre": 0, "signalees": 0}
    from .app import _ETAGE0_SQL, MIN_DISPLAY_SURFACE_M2, _score_v2_run_id
    fc = _cadrage_to_filtre(cadrage)
    where, params = fc.where()
    base = "" if ("f_tiers" in params or "s2.tier" in where or _ETAGE0_SQL in where) \
        else f"AND NOT {_ETAGE0_SQL}"
    r = db.execute(text(
        f"SELECT count(*) AS total, "
        f"  count(*) FILTER (WHERE s2.tier = 'brulante') AS priorite, "
        f"  count(*) FILTER (WHERE s2.tier = 'chaude') AS a_suivre "
        f"FROM parcels p JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run "
        f"JOIN parcel_p_score_v2 s2 ON s2.parcelle_id = p.idu AND s2.run_id = :v2run "
        f"WHERE (p.surface_m2 IS NULL OR p.surface_m2 >= :minsurf) {base} {where}"),
        {"run": RUN, "v2run": _score_v2_run_id(db), "minsurf": MIN_DISPLAY_SURFACE_M2,
         **params}).mappings().first()
    p, s = int(r["priorite"] or 0), int(r["a_suivre"] or 0)
    return {"total": int(r["total"] or 0), "priorite": p, "a_suivre": s, "signalees": p + s}


def _restant_a_trier(db: Session, pid: int, v2run: str, analyse: dict) -> dict:
    """RETOURS-3 R8 (Vic 31/08) — pour les CHIPS de tri (Tous / Priorité / À suivre) : ce qui reste
    À TRIER par tier = total du cadrage par tier MOINS les DÉCIDÉES (retenues + écartées) du même
    tier. Cohérent avec le compteur « à trier » du haut (total − décidées) : le chip « Priorité 34 »
    affichait le total du cadrage alors que 9 parcelles étaient déjà triées. Le BANDEAU, lui, garde le
    total du cadrage (R10 — il décrit ce que l'analyse a trouvé, pas ce qu'il reste à faire)."""
    rows = db.execute(text(
        "SELECT s2.tier AS tier, count(*) AS n FROM projet_parcelles pp "
        "JOIN parcels p ON p.id = pp.parcel_id "
        "JOIN parcel_p_score_v2 s2 ON s2.parcelle_id = p.idu AND s2.run_id = :v2run "
        "WHERE pp.projet_id = :pid AND pp.statut IN ('retenue', 'ecartee') GROUP BY s2.tier"),
        {"pid": pid, "v2run": v2run}).mappings().all()
    decid = {r["tier"]: int(r["n"] or 0) for r in rows}
    prio = max(0, int(analyse.get("priorite", 0)) - decid.get("brulante", 0))
    suiv = max(0, int(analyse.get("a_suivre", 0)) - decid.get("chaude", 0))
    return {"priorite": prio, "a_suivre": suiv, "signalees": prio + suiv}


#: PROJETS-V5 (E4) — les signaux de vie AFFICHÉS sur une ligne (jusqu'à 2) : code interne →
#: (libellé client, « fort »). Fort (rouge) = ce qui pèse le plus sur la mutation. L'ordre EST la
#: priorité d'affichage (forts d'abord). Chaque signal a sa table SOURCÉE (jamais inventé).
_SIGNAUX_LIGNE = [
    ("succession", "succession", True),
    ("procedure", "société en procédure", True),
    ("permis_caduc", "permis abandonné", True),
    ("permis_actif", "permis récent", False),
    ("friche", "friche recensée", False),
    ("defisc", "sortie de défisc", False),
]


def _signaux_parcelles(db: Session, idus: list[str]) -> dict[str, list[dict]]:
    """PROJETS-V5 (E4) — pour un LOT d'idu, la liste des signaux de vie présents (batch, tables gardées :
    une table absente → signal ignoré, jamais une erreur). Rend {idu: [{label, fort}]}, forts d'abord,
    plafonné à 2. Mêmes tables que le filtre `signaux` de la carte (app.py `_SIG_SQL`)."""
    if not idus:
        return {}
    present: dict[str, set] = {}

    def add(code: str, sql: str) -> None:
        try:
            for row in db.execute(text(sql), {"ids": idus}):
                present.setdefault(row[0], set()).add(code)
        except Exception:  # noqa: BLE001 — table optionnelle : signal simplement absent
            pass

    add("succession", "SELECT DISTINCT parcelle_id FROM parcel_veille_succession WHERE parcelle_id = ANY(:ids)")
    add("procedure", "SELECT DISTINCT pms.idu FROM parcelle_personne_morale pms "
        "JOIN bodacc_procedures bp ON bp.siren = pms.siren WHERE pms.idu = ANY(:ids)")
    add("permis_caduc", "SELECT DISTINCT idu FROM pc_caducs WHERE idu = ANY(:ids)")
    add("permis_actif", "SELECT DISTINCT idu FROM parcel_signaux_vie WHERE idu = ANY(:ids) AND signal = 'permis_actif'")
    add("friche", "SELECT DISTINCT idu FROM parcel_signaux_vie WHERE idu = ANY(:ids) AND signal = 'friche'")
    add("defisc", "SELECT DISTINCT idu FROM defisc_fenetres WHERE idu = ANY(:ids) AND fenetre_active")
    out: dict[str, list[dict]] = {}
    for idu, codes in present.items():
        picked = [(lbl, fort) for code, lbl, fort in _SIGNAUX_LIGNE if code in codes]
        out[idu] = [{"label": lbl, "fort": fort} for lbl, fort in picked[:2]]
    return out


def _sous_filtre(sf: str | None) -> dict:
    """PROJETS-V5 (E5) — le sous-cadrage du TIROIR « Filtrer » (JSON camelCase, mêmes clés que le
    wizard), nettoyé aux seules facettes connues. Vide / illisible → {} (le cadrage du projet seul)."""
    if not sf:
        return {}
    try:
        import json as _json
        return clean_cadrage(_json.loads(sf))
    except Exception:  # noqa: BLE001 — filtre illisible : on ignore, jamais un 500
        return {}


@router.get("/{pid}/parcelles")
def projet_parcelles(pid: int, request: Request, db: Session = Depends(get_db),
                     offset: int = 0, limit: int = 60, tier: str | None = None,
                     sf: str | None = None) -> dict:
    """M140 Lot A — l'ÉTAT du parcours, la LISTE ENTIÈRE sans la stocker. Les DÉCIDÉES
    (retenue/écartée/à analyser) sont stockées (petites — toujours toutes servies) ; les PROPOSÉES
    sont la liste COMPLÈTE des retenues du cadrage, servie EN DIRECT et PAGINÉE (`offset`/`limit`),
    jamais une copie, jamais tout chargé. Enrichissement par BATCH sur la seule PAGE (adresse BAN,
    marché, événement, carence). `counts.proposee` = total VIF restant (pas la page). Base de la
    reprise : rouvrir = relire cet état."""
    p = _projet_or_404(db, pid, current_compte(request))
    from .app import _ETAT_BIEN_SQL, _score_v2_run_id
    from ..scoring.p_v2.libelles_client import raison_dominante as _raison_dominante
    v2 = _score_v2_run_id(db)
    limit = max(1, min(limit, 200))          # borne de page — on ne charge JAMAIS tout
    # OUTILS-5 (P1) — FILTRE DE NAVIGATION « classement » : on RESSERRE le vivier à trier sur un tier
    # (Priorité/À suivre…) via la MÊME facette `tiers` que la carte — jamais un moteur parallèle. Le
    # cadrage du projet est préservé ; on ne fait que naviguer dedans.
    # PROJETS-V5 (E4/E5) — le cadrage SERVI. Une SEULE requête, aucun moteur parallèle. Sans tiroir, c'est
    # le cadrage du projet. Avec tiroir (`sf`), le sous-filtre REMPLACE les facettes (il est initialisé
    # depuis le cadrage du projet côté front → retirer une puce = servir sans cette facette) ; le PÉRIMÈTRE
    # (communes) du projet reste FIXE. Le chip de classement (`tier`) se superpose. « Tout effacer » = pas de sf.
    sous = _sous_filtre(sf)
    if sous:
        cadrage = dict(sous)
        pc = (p.filtres or {}).get("communes")
        cadrage["communes"] = pc if pc else None
        cadrage = {k: v for k, v in cadrage.items() if v not in (None, [], "")}
    else:
        cadrage = dict(p.filtres or {})
    if tier:
        cadrage["tiers"] = [tier]
    # 1) DÉCIDÉES stockées (statut != proposee) — petites, servies en entier (ordre de proposition).
    decided = db.execute(text(
        "SELECT pp.statut, pp.rang, pp.hors_criteres, par.idu FROM projet_parcelles pp "
        "JOIN parcels par ON par.id = pp.parcel_id "
        "WHERE pp.projet_id = :pid AND pp.statut <> 'proposee' "
        "ORDER BY pp.rang NULLS LAST, pp.id"), {"pid": pid}).mappings().all()
    decided_idus = [r["idu"] for r in decided]
    # 2) PAGE de proposées = cadrage VIF paginé, hors décidées (la liste complète se feuillette).
    page_idus = _cadrage_page_idus(db, cadrage, limit, offset, exclude_idus=decided_idus)
    # 3) total COMPLET des retenues (dénominateur « X sur N ») — la liste complète EXISTE, vive.
    #    M140 Lot A — le count est LOURD (~4 s sur l'île) : on ne le paie qu'à la PREMIÈRE page
    #    (offset 0) ; feuilleter (offset > 0) ne recompte pas, le front garde le total. `None` sur
    #    les pages suivantes = « inchangé, garde la valeur de la 1re page », jamais un faux 0.
    tot = _cadrage_total(db, cadrage)["total"] if offset == 0 else None
    if tot is not None:                      # FIX-PROJETS — l'ouverture RAFRAÎCHIT le cache → la liste
        p.cadrage_total = tot                #   sert le même nombre (fraîcheur `cadrage_total_at`).
        p.cadrage_total_at = datetime.now(timezone.utc)
    proposee_total = max(0, (tot or 0) - len(decided_idus)) if tot is not None else None
    # 4) méta statut/hors_criteres + ordre d'affichage (décidées d'abord, puis la page best-first).
    meta = {r["idu"]: (r["statut"], bool(r["hors_criteres"])) for r in decided}
    ordre = {idu: i for i, idu in enumerate(decided_idus)}
    for i, idu in enumerate(page_idus):
        meta[idu] = ("proposee", False)      # une proposée VIVE matche le cadrage → jamais hors_criteres
        ordre[idu] = len(decided_idus) + i
    all_idus = decided_idus + page_idus
    # 5) enrichissement BATCH — sur la PAGE + les décidées SEULEMENT (jamais toute la population).
    rows = db.execute(text(
        f"""SELECT par.idu, par.commune, par.surface_m2, s2.tier, {_ETAT_BIEN_SQL} AS etat_bien,
                  s2.top5_contributions AS top5,   -- OUTILS-5 (P1) : le signal qui a classé la parcelle
                  ST_X(ST_Transform(ST_Centroid(par.geom_2975), 4326)) AS lng,
                  ST_Y(ST_Transform(ST_Centroid(par.geom_2975), 4326)) AS lat
           FROM parcels par
           LEFT JOIN parcel_p_score_v2 s2 ON s2.parcelle_id = par.idu AND s2.run_id = :v2
           LEFT JOIN parcel_residuel rb ON rb.parcel_id = par.id   -- M131 P3 : 1 ligne/parcelle
           WHERE par.idu = ANY(:idus)"""),
        {"v2": v2, "idus": all_idus}).mappings().all() if all_idus else []
    # M2 — badges parcelle (défisc / PC caduc), gardés to_regclass : absents en base → pas de badge, jamais d'erreur.
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
    # PROJETS-V5 (E4) — jusqu'à 2 signaux de vie SOURCÉS par ligne (batch), le fort en rouge côté front.
    signaux_map = _signaux_parcelles(db, all_idus)

    groups: dict[str, list] = {s: [] for s in ("proposee", "retenue", "ecartee", "a_analyser")}
    for r in rows:
        evt = r["idu"] in event_set
        statut, hors = meta.get(r["idu"], ("proposee", False))   # M140 : statut vient de meta, pas de la ligne
        groups.setdefault(statut, []).append({
            "idu": r["idu"], "commune": r["commune"], "statut": statut,
            "tier": r["tier"], "surface_m2": r["surface_m2"],
            "etat_bien": r["etat_bien"],   # M131 P3 : nu | bati_encore | bati_max (affichage)
            "adresse": adrs.get(r["idu"]), "evenement": evt,
            "marche_eur_m2": marche.get(r["commune"]),
            "pourquoi": _pourquoi_court(r["tier"], r["commune"] in carencees, evt, r["surface_m2"]),
            # OUTILS-5 (P1) — le SIGNAL dominant (succession, permis jamais lancé…), MÊME source que la
            # carte (`raison_dominante` sur les contributions du score). Jamais inventé : None possible.
            "raison": _raison_dominante(r["top5"]),
            "signaux": signaux_map.get(r["idu"], []),   # PROJETS-V5 (E4) — ≤ 2 signaux, forts d'abord
            "hors_criteres": hors,
            "defisc": r["idu"] in defisc_set, "caduc": r["idu"] in caduc_set,
            "center": [round(r["lng"], 6), round(r["lat"], 6)] if r["lng"] is not None else None,
        })
    for g in groups.values():        # M140 — ordre stable : décidées (ordre de proposition) puis page best-first
        g.sort(key=lambda c: ordre.get(c["idu"], 0))
    # PRIVACY : les RETENUES portent le contact proprio (elles vont au CRM) — personne morale nommée
    # (public DGFiP), particulier JAMAIS nommé (« non communiqué »). Réutilise le helper du CRM.
    from .app import _proprietaire_public
    for it in groups["retenue"]:
        it["proprietaire_public"] = _proprietaire_public(db, it["idu"])
    # PROJETS-V5 (E2) / RETOURS-3 R8 — le bandeau garde le total du cadrage ; les chips comptent le RESTANT.
    analyse_val = _analyse_cadrage(db, p.filtres or {}) if offset == 0 else None
    restant = _restant_a_trier(db, pid, v2, analyse_val) if analyse_val else None
    return {"nom": p.nom, "sdp_besoin_m2": _sdp_besoin(cadrage),
            # M139 Lot 2 (F2) — les deux dates à l'écran : figeage du cadrage + run résiduel servi.
            "figee_le": p.derniere_execution_at.date().isoformat() if p.derniere_execution_at else None,
            "valeurs_run": _residuel_run_servi(db),
            # PROJETS-V5 (E2) — le bandeau d'analyse : total du cadrage du PROJET (pas le sous-filtré) +
            # signalées par tier. Calculé à la 1re page seulement (offset 0) ; les pages suivantes le gardent.
            "analyse": analyse_val,
            # RETOURS-3 R8 — restant À TRIER par tier (chips) ; None hors 1re page (le front le mémorise).
            "restant": restant,
            "proposees": groups["proposee"], "retenues": groups["retenue"],
            "ecartees": groups["ecartee"], "a_analyser": groups["a_analyser"],
            # M140 Lot A — `counts.proposee` = total VIF restant (liste complète), PAS la taille de page.
            "counts": {"proposee": proposee_total or 0, "retenue": len(groups["retenue"]),
                       "ecartee": len(groups["ecartee"]), "a_analyser": len(groups["a_analyser"])},
            "total_retenues": tot,                 # dénominateur « X sur N » (None = requête en échec)
            "page": {"offset": offset, "limit": limit, "returned": len(page_idus),
                     "has_more": len(page_idus) == limit}}


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
    """OUTILS-5 (P3) — ajoute UNE parcelle précise (par IDU, depuis sa fiche) en **RETENUE** : la choisir
    depuis sa fiche EST une décision, pas une proposition à trier. Alimente la colonne Retenues, y compris
    d'un projet « de zéro » (vide). Dédupliqué : `already=true` si déjà retenue. Crée la piste CRM."""
    _projet_or_404(db, pid, current_compte(request))
    pc = db.execute(text("SELECT id FROM parcels WHERE idu = :i"), {"i": body.idu}).scalar()
    if not pc:
        raise HTTPException(404, f"Parcelle {body.idu} inconnue")
    now = datetime.now(timezone.utc)
    res = db.execute(text(
        "INSERT INTO projet_parcelles (projet_id, parcel_id, statut, created_at, updated_at) "
        "VALUES (:pj, :pc, 'retenue', :now, :now) "
        "ON CONFLICT (projet_id, parcel_id) DO UPDATE SET statut = 'retenue', updated_at = :now "
        "WHERE projet_parcelles.statut <> 'retenue'"),
        {"pj": pid, "pc": pc, "now": now})
    added = res.rowcount == 1
    if added:
        _sync_crm_retenue(db, pid, pc, "retenue", now, current_compte(request))
    db.flush()
    return {"ok": True, "added": added, "already": not added, "idu": body.idu, **_counts(db, pid)}


def _zone_famille(code: str | None) -> str | None:
    """M130-2 §3.3 — la FAMILLE de zone d'un code PLU, libellé correct (U = urbaine, AU = à
    urbaniser…) — jamais le faux libellé « urbaine / à urbaniser » corrigé en M128-2-J. On teste AU
    AVANT U (« 2AUe » commence par un chiffre puis AU) : on retire les indices numériques de tête."""
    if not code:
        return None
    import re as _re
    u = _re.sub(r"^\d+", "", str(code)).strip().upper()
    if u.startswith("AU"):
        return "à urbaniser"
    if u.startswith("U"):
        return "urbaine"
    if u.startswith("N"):
        return "naturelle"
    if u.startswith("A"):
        return "agricole"
    return None


def _part_ouverte(code: str | None) -> bool:
    """M130-8 §A — une part de zone est OUVERTE à l'urbanisation (constructible) ssi U ou 1AU (ou AU
    sans indice). A, N, et 2AU / 3AU… (zones AU FERMÉES, à ouvrir par révision) → False. C'est ce test
    — et lui seul — qui autorise à annoncer une part constructible ; jamais la seule famille dominante."""
    if not code:
        return False
    import re as _re
    u = str(code).strip().upper()
    m = _re.match(r"^(\d+)", u)
    lead = int(m.group(1)) if m else None
    core = _re.sub(r"^\d+", "", u)
    if core.startswith("AU"):
        return lead is None or lead == 1           # AU / 1AU ouvertes ; 2AU+ fermées
    return core.startswith("U")                    # U = urbaine ; A / N → False


def _hauteur_src_dezone(zone_code: str | None, src: str | None) -> str | None:
    """M130-10 §C — retire d'une source de hauteur la référence d'article qui désigne une AUTRE zone
    (bavardage d'une entrée YAML PARTAGÉE, ex. `["Us","AU01",…]` : « … Art. Us1 p.130 ; Art. AU01,
    p.200 » servi sur une parcelle Us). On coupe au « ; Art. AU0… » sauf si la zone EST une AU0.
    Une source incomplète est acceptable ; une source qui pointe une autre zone ne l'est pas."""
    if not src:
        return src
    import re as _re
    if not str(zone_code or "").upper().startswith("AU0") and _re.search(r";\s*Art\.\s*AU0", src):
        src = _re.split(r"\s*;\s*Art\.\s*AU0", src)[0]
    return src


def _plu_millesime(idurba: str | None) -> str | None:
    """M130-2 §6 — le MILLÉSIME AMONT du zonage = la date d'approbation du PLU portée par `idurba`
    (ex. « 97401_PLU_20241206 » → 06/12/2024). Jamais une date de run. None si non renseigné."""
    if not idurba:
        return None
    import re as _re
    m = _re.search(r"(\d{4})(\d{2})(\d{2})", str(idurba))
    return f"{m.group(3)}/{m.group(2)}/{m.group(1)}" if m else None


def _shortlist_pdf(db: Session, p: models.Projet) -> dict:
    """M130-2 §1/§3 — sert la SHORTLIST FIGÉE du projet (table projet_parcelles), JAMAIS un recalcul
    live. Ordre NEUTRE (commune, section, n° — §2.3), aucun verdict/rang. Chaque parcelle enrichie de
    DONNÉE pure : SDP résiduelle (Estimé), hauteurs égout/faîtage calibrées (resolve_zone — source
    corrigée M128-2-A/M129-2), zone PLU + famille + millésime amont. `figee=False` si le projet n'a
    pas de shortlist figée exploitable (date + parcelles) — on le DIT, on ne fabrique aucun run."""
    from ..faisabilite.plu_rules import resolve_zone
    from .app import _ETAGE0_SQL
    from .export_commun import adresses_ban, format_adresse
    rows = db.execute(text(
        f"""SELECT par.idu, par.commune, round(par.surface_m2) AS surface_m2,
                  substr(par.idu, 9, 2) AS section, substr(par.idu, 11) AS numero,
                  pr.sdp_residuelle_m2, pr.cause,   -- SDP résiduelle (Estimé) + motif (capacite_estimee RETIRÉ : jamais lu)
                  {_ETAGE0_SQL} AS etage0
           FROM projet_parcelles pp
           JOIN parcels par ON par.id = pp.parcel_id
           LEFT JOIN parcel_residuel pr ON pr.parcel_id = par.id
           LEFT JOIN dryrun_parcel_evaluations d ON d.parcel_id = par.id AND d.run_label = :run
           WHERE pp.projet_id = :pid AND pp.statut <> 'ecartee'
           ORDER BY par.commune, section, NULLIF(regexp_replace(numero, '\\D', '', 'g'), '')::int"""),
        {"pid": p.id, "run": RUN}).mappings().all()
    figee = bool(p.derniere_execution_at) and bool(rows)
    idus = [r["idu"] for r in rows]
    adrs = {i: format_adresse(a) for i, a in adresses_ban(db, idus).items()} if idus else {}
    # M130-4 §C — PARTS de zone (décompte spatial direct, MÊME chemin que le tableau ZONE/PART du
    # dossier banquier : spatial_layers plu_gpu_zone + pct = surface d'intersection / surface parcelle).
    # Une seule requête batch pour toute la shortlist ; groupée par IDU ensuite.
    # M130-4 : parts AGRÉGÉES PAR LIBELLÉ (une zone multipolygone ne doit pas apparaître deux fois —
    # « Uav ~13 % · Uav ~7 % » → « Uav ~20 % »). GROUP BY libellé, somme des parts.
    zones_par_idu: dict[str, list] = {}
    if idus:
        for zr_row in db.execute(text(
                """SELECT par.idu, sl.attrs->>'libelle' AS lib, max(sl.attrs->>'idurba') AS idurba,
                          round((100 * sum(ST_Area(ST_Intersection(sl.geom_2975, par.geom_2975)))
                                 / NULLIF(ST_Area(par.geom_2975), 0))::numeric) AS pct
                   FROM projet_parcelles pp
                   JOIN parcels par ON par.id = pp.parcel_id
                   JOIN spatial_layers sl ON sl.kind = 'plu_gpu_zone'
                        AND ST_Intersects(sl.geom_2975, par.geom_2975)
                   WHERE pp.projet_id = :pid AND pp.statut <> 'ecartee'
                   GROUP BY par.idu, sl.attrs->>'libelle', par.geom_2975
                   ORDER BY par.idu, pct DESC"""), {"pid": p.id}).mappings():
            if zr_row["lib"]:
                zones_par_idu.setdefault(zr_row["idu"], []).append(
                    (zr_row["lib"], _zone_famille(zr_row["lib"]),
                     int(zr_row["pct"]) if zr_row["pct"] is not None else None, zr_row["idurba"]))
    parcelles = []
    for r in rows:
        zs = zones_par_idu.get(r["idu"], [])
        dom = zs[0] if zs else (None, None, None, None)          # zone dominante = plus forte part
        zone_libelle, famille, _dpct, zone_idurba = dom
        # §C : parts SIGNIFICATIVES (≥ 5 % — un liseré < 5 % n'est pas « multi-zones »).
        parts = [(lib, fam, pct) for (lib, fam, pct, _iu) in zs if pct is not None and pct >= 5]
        multi_zone = len(parts) >= 2
        # M130-5 §C : reliquat = 100 − somme des parts affichées (zones sous le seuil / trou géométrie).
        # Jamais muet : ≥ 2 → ligne « autres zones ~ X % » ; ±1 = arrondi (rien).
        parts_reste = 100 - sum(pct for (_l, _f, pct) in parts) if parts else 0
        # M130-8 §A : la plus grande part réellement OUVERTE à l'urbanisation (U / 1AU) ≥ 5 % — seule
        # base qui autorise à annoncer une part constructible (exclut A, N, 2AU). Remplace le test
        # M130-7 sur la famille (« à urbaniser » incluait 2AU → faux positif).
        _constr = [(lib, pct) for (lib, fam, pct) in parts if _part_ouverte(lib)]
        part_constructible = _constr[0] if _constr else None
        zr = None
        try:
            zr = resolve_zone(zone_libelle, r["commune"]) if zone_libelle else None
        except Exception:  # noqa: BLE001 — une zone non résolue ne casse pas l'export
            zr = None
        he = getattr(zr, "he_m", None) if zr else None
        hf = getattr(zr, "hf_m", None) if zr else None
        # M130-3 §A.2/A.4 : la FAMILLE décide — A (agricole) / N (naturelle) = non constructible,
        # JAMAIS de SDP chiffrée (indépendant du cache résiduel, qui peut avoir calculé sur une
        # sous-zone U chevauchante et laissé « 2 149 m² sur du Nco »).
        non_constructible = famille in ("agricole", "naturelle")
        sdp_m2 = int(r["sdp_residuelle_m2"]) if r["sdp_residuelle_m2"] is not None else None
        # M130-10 §A — hauteur de la PART OUVERTE nommée (résolue sur SA zone, pas la majoritaire) :
        # quand la dominante est fermée mais une part ouverte est nommée, la hauteur servie est celle
        # de cette part. `None` si aucune part ouverte.
        hauteur_part_ouverte = None
        if part_constructible:
            try:
                zro = resolve_zone(part_constructible[0], r["commune"])
            except Exception:  # noqa: BLE001
                zro = None
            _heo, _hfo = (getattr(zro, "he_m", None), getattr(zro, "hf_m", None)) if zro else (None, None)
            hauteur_part_ouverte = {
                "lib": part_constructible[0],
                "he_m": float(_heo) if isinstance(_heo, (int, float)) else None,
                "hf_m": float(_hfo) if isinstance(_hfo, (int, float)) else None,
                "calibree": bool(getattr(zro, "calibree", False)) if zro else False,
                "source": _hauteur_src_dezone(part_constructible[0],
                                              (getattr(zro, "sources", None) or {}).get("hauteur") if zro else None),
                "renvoi": getattr(zro, "via_renvoi", None) if zro else None,
            }
        parcelles.append({
            "idu": r["idu"], "commune": r["commune"], "surface_m2": r["surface_m2"],   # §F.1
            "section": r["section"], "numero": r["numero"],
            "adresse_ban": adrs.get(r["idu"]),
            "non_constructible": non_constructible,
            "sdp_m2": sdp_m2,
            "sdp_indispo": r["cause"],
            # §C : SDP réellement chiffrée = constructible, sans cause, > 0
            "sdp_chiffree": bool(not non_constructible and not r["cause"] and sdp_m2),
            "etage0": bool(r["etage0"]),                # M130-5 §B : état de donnée, pas un rang
            "multi_zone": multi_zone,
            "zones_parts": parts,       # [(lib, famille, pct), …] ≥ 5 %
            "zones_reste": parts_reste,
            "part_constructible": part_constructible,   # M130-7 §C : (libellé, pct) ou None
            "hauteur_part_ouverte": hauteur_part_ouverte,   # M130-10 §A
            "zone_code": zone_libelle,
            "zone_famille": famille,
            "zone_millesime": _plu_millesime(zone_idurba),
            "he_m": float(he) if isinstance(he, (int, float)) else None,
            "hf_m": float(hf) if isinstance(hf, (int, float)) else None,
            "hauteur_calibree": bool(getattr(zr, "calibree", False)) if zr else False,
            # M130-10 §C : source nettoyée d'une référence bavarde vers une autre zone (Us ← AU01)
            "hauteur_source": _hauteur_src_dezone(
                zone_libelle, (getattr(zr, "sources", None) or {}).get("hauteur") if zr else None),
            "hauteur_renvoi": getattr(zr, "via_renvoi", None) if zr else None,   # §F.4
            "zone_resolue": zr is not None,
        })
    # M130-5 §A : le total AFFICHÉ est le cardinal de la population dont la shortlist est EXTRAITE
    # (`_cadrage_total`, MÊME population que `_run_cadrage`), jamais `_vivier_figeable` (autre
    # population). None = échec réel de requête → État 3.
    tot = _cadrage_total(db, p.filtres or {}) if figee else {"total": None, "etage0": None}
    return {
        "figee": figee,
        "figee_le": p.derniere_execution_at.date().isoformat() if p.derniere_execution_at else None,
        # M139 Lot 2 (F2) — la SECONDE date : les valeurs (SDP/zone/cause) sont relues LIVE sur le
        # run résiduel servi ; on la DIT (« valeurs au JJ/MM (run N) »), au lieu du seul avertissement.
        "valeurs_run": _residuel_run_servi(db) if figee else None,
        "n": len(parcelles),
        "total": tot["total"],           # M130-5 §A : None → État 3 (échec) ; > n → État 1 ; <= n → État 2
        "total_etage0": tot["etage0"],   # M130-6 §C : part étage 0 du total
        "etage0_count": sum(1 for it in parcelles if it["etage0"]),   # §B (part étage 0 des FIGÉES)
        # M130-8 §C.1 : parcelles MULTI-ZONES étage 0 gardant une part OUVERTE (= les lignes d'exception
        # réellement rendues). On ne compte plus les mono-zones urbaines (métrique ≠ libellé, cf. C.1).
        "etage0_constructible": sum(
            1 for it in parcelles if it["etage0"] and it["multi_zone"] and it["part_constructible"]),
        "parcelles": parcelles,
    }


@router.get("/{pid}/export.pdf")
def projet_export_pdf(pid: int, request: Request, db: Session = Depends(get_db)):
    """Dossier PROJET en PDF — document de PRÉSENTATION. M130-2 : sert la SHORTLIST FIGÉE du projet
    (jamais un recalcul live), datée par son figeage ; aucun verdict/rang/score ; chaque parcelle
    porte de la DONNÉE (SDP estimée, hauteurs calibrées, zone). Mécanique fpdf2 existante."""
    from fastapi.responses import Response

    from .pdf_projet import render_projet_pdf
    p = _projet_or_404(db, pid, current_compte(request))   # SEC-IDOR : export borné au compte
    shortlist = _shortlist_pdf(db, p)
    pdf = render_projet_pdf(_projet_dict(p), shortlist)
    slug = "".join(c if c.isalnum() else "-" for c in (p.nom or "projet")).strip("-").lower()[:48]
    # M130-2 §5.3 — nommage doctrine : projet-{id}-{slug}-labuse.pdf (id stable = pas de collision)
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition":
                             f'inline; filename="projet-{pid}-{slug or "projet"}-labuse.pdf"'})


@router.get("/{pid}/export.csv")
def projet_export_csv(pid: int, request: Request, db: Session = Depends(get_db)):
    """M140 Lot B — la LISTE COMPLÈTE des retenues du cadrage, STREAMÉE : jamais stockée, jamais
    tout en mémoire (curseur serveur). Colonnes de DONNÉE du PDF, ordre GÉOGRAPHIQUE, **aucun
    rang/score** (doctrine M133 B.6 sur le flux aussi). SEC-IDOR : borné au compte. La 1re ligne
    porte les DEUX dates comme le PDF (cadrage figé le X · valeurs au Y (run N) · export généré le Z).
    Le curseur vit dans une connexion PROPRE au générateur (la session `Depends` est fermée quand
    le stream se consomme — piège FastAPI classique)."""
    import csv
    import io

    from fastapi.responses import StreamingResponse

    from ..db import engine
    from .app import _ETAGE0_SQL, _ETAT_BIEN_SQL, MIN_DISPLAY_SURFACE_M2, _ban_lateral, _ban_ready, _score_v2_run_id
    p = _projet_or_404(db, pid, current_compte(request))    # SEC-IDOR : export borné au compte
    cadrage = p.filtres or {}
    fc = _cadrage_to_filtre(cadrage)
    where, params = fc.where()
    base = "" if ("f_tiers" in params or "s2.tier" in where or _ETAGE0_SQL in where) \
        else f"AND NOT {_ETAGE0_SQL}"
    ban_ok = _ban_ready(db)
    ban_sel = (", ban.ban_voie, ban.ban_cp, ban.ban_commune" if ban_ok
               else ", NULL AS ban_voie, NULL AS ban_cp, NULL AS ban_commune")
    ban_join = _ban_lateral("p.idu") if ban_ok else ""
    sql = text(
        f"""SELECT p.idu, p.commune, substr(p.idu, 9, 2) AS section, substr(p.idu, 11) AS numero,
                   round(p.surface_m2) AS surface_m2, {_ETAT_BIEN_SQL} AS etat_bien,
                   round(rb.sdp_residuelle_m2) AS sdp_residuelle_m2, rb.cause AS sdp_indispo,
                   (d.status IN ('exclue', 'faux_positif_probable')) AS etage0 {ban_sel}
            FROM parcels p
            JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run
            JOIN parcel_p_score_v2 s2 ON s2.parcelle_id = p.idu AND s2.run_id = :v2run
            LEFT JOIN parcel_residuel rb ON rb.parcel_id = p.id
            {ban_join}
            WHERE (p.surface_m2 IS NULL OR p.surface_m2 >= :minsurf) {base} {where}
            ORDER BY p.commune, section,
                     NULLIF(regexp_replace(substr(p.idu, 11), '\\D', '', 'g'), '')::int NULLS LAST, p.idu""")
    prm = {"run": RUN, "v2run": _score_v2_run_id(db), "minsurf": MIN_DISPLAY_SURFACE_M2, **params}
    vr = _residuel_run_servi(db) or {}
    figee = p.derniere_execution_at.date().isoformat() if p.derniere_execution_at else "non figé"
    # RETOURS-7 Z12.2 — libellé lisible (date) servi au client ; l'identifiant technique du run reste
    # au dashboard, plus dans les documents client.
    val = f"valeurs au {vr['date']}" if vr.get("date") else "valeurs : run résiduel indisponible"
    genere = datetime.now(timezone.utc).date().isoformat()
    cols = ["idu", "commune", "section", "numero", "surface_m2", "adresse", "code_postal",
            "ville", "etat_bien", "sdp_residuelle_m2", "sdp_indispo", "etage0"]

    def rows_iter():
        buf = io.StringIO()
        w = csv.writer(buf, delimiter=";", lineterminator="\r\n")
        # FIX-C6 (GB-057) — l'en-tête ne dit plus « cadrage figé le non figé » : le libellé suit
        # l'état RÉEL du cadrage (figé à une date, ou explicitement non figé).
        entete = f"# cadrage figé le {figee}" if figee != "non figé" else "# cadrage NON figé (jamais exécuté)"
        # FIX-C6 (GB-056) — BOM UTF-8 en tête (comme l'export parcelles utf-8-sig) : sans lui
        # Excel FR casse les accents. Cohérence inter-exports.
        buf.write("\ufeff")  # BOM UTF-8
        w.writerow([f"{entete} · {val} · export généré le {genere} "
                    "· ordre géographique · aucune sélection ni classement interne"])
        w.writerow(cols)
        yield buf.getvalue()
        buf.seek(0)
        buf.truncate(0)
        # connexion PROPRE au stream (la session Depends est déjà fermée à ce stade)
        with engine().connect() as conn:
            res = conn.execution_options(stream_results=True, max_row_buffer=1000).execute(sql, prm)
            n = 0
            for r in res.mappings():
                w.writerow([r["idu"], r["commune"], r["section"], r["numero"], r["surface_m2"],
                            r["ban_voie"], r["ban_cp"], r["ban_commune"], r["etat_bien"],
                            r["sdp_residuelle_m2"], r["sdp_indispo"], "oui" if r["etage0"] else "non"])
                n += 1
                if n % 1000 == 0:
                    yield buf.getvalue()
                    buf.seek(0)
                    buf.truncate(0)
            if buf.tell():
                yield buf.getvalue()

    slug = "".join(c if c.isalnum() else "-" for c in (p.nom or "projet")).strip("-").lower()[:48]
    return StreamingResponse(rows_iter(), media_type="text/csv; charset=utf-8",
                             headers={"Content-Disposition":
                                      f'attachment; filename="projet-{pid}-{slug or "projet"}-retenues.csv"'})
