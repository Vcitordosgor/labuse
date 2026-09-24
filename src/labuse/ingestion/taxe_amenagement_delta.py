"""TAXE-AMÉNAGEMENT-1 lot A — taux communaux de taxe d'aménagement (DGFiP, DELTA).

SOURCE AUTOMATIQUE trouvée et vérifiée live le 08/09/2026 : le jeu ouvert
`delta_deliberation_tam_17_01_23` (data.economie.gouv.fr, DGFiP — application DELTA)
« Taxe d'aménagement — éléments de taxation votés par les collectivités à partir de
2022 ». Publié DEUX fois par an (fin janvier + seconde quinzaine d'octobre).
⚠ La taxe d'aménagement n'est PAS dans le fichier REI (cf ingestion/rei.py) : sa
source est CE jeu, distinct.

Structure (une ligne = une délibération, grain PARCELLE quand la commune sectorise) :
  · departement + commune → INSEE (974 + 2 chiffres) ; libelle_commune ;
  · taux (%), date_effet (date d'effet légale de la délibération), date_fin (null = en
    vigueur), def_prov (DEFINITIF / PROVISOIRE), zone_application (Communale /
    Départementale) ; prefixe/section/parcelle remplis pour un secteur MAJORÉ.

Le TAUX COMMUNAL GÉNÉRAL d'une commune = la ligne zone_application=Communale SANS
parcelle, en vigueur (date_fin null). Mesuré au 08/09/2026 : 24/24 communes du 974
présentes, toutes DEFINITIF (1 % à 5 %). La part DÉPARTEMENTALE (zone_application=
Départementale, commune null) vaut 2,5 % — CONFIRMÉE par la source (le YAML la servait
en « plafond légal à confirmer »).

Doctrine « aucun taux inventé » respectée : chaque taux vient de la délibération
officielle portée par la DGFiP, avec sa date d'effet. Purge + upsert (idempotent).
"""
from __future__ import annotations

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import constants
from ..config import get_settings
from ..taxe_amenagement import _SECTEUR_DDL, _TAUX_DDL

SOURCE_NAME = "Taxe d'aménagement — taux communaux (DGFiP / DELTA)"
DATASET = "delta_deliberation_tam_17_01_23"
API_BASE = ("https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/"
            f"{DATASET}/records")
# Le taux communal GÉNÉRAL : zone communale, sans secteur, en vigueur.
_WHERE_COMMUNAL = ('departement="974" and zone_application="Communale" '
                   'and parcelle is null and date_fin is null and taux is not null')
# La part départementale (une seule ligne) : zone départementale, commune null.
_WHERE_DEPARTEMENTAL = ('departement="974" and zone_application="Départementale" '
                        'and date_fin is null and taux is not null')
# TAXE-FIX-1 point 3 — les SECTEURS À TAUX MAJORÉ : zone communale, portée à la PARCELLE
# (prefixe/section/parcelle remplis), en vigueur. Chaque ligne = une parcelle du secteur.
_WHERE_SECTEUR = ('departement="974" and zone_application="Communale" '
                  'and parcelle is not null and date_fin is null and taux is not null')
# Bornes de plausibilité : la part communale légale va de 1 à 5 %, jusqu'à 20 % en
# secteur à aménager (CGI art. 1635 quater E/F). Un taux hors [0 ; 20] est écarté + listé.
# (DELTA porte des lignes sentinelles à 99 % au grain parcelle : les bornes les excluent.)
_BORNE_MIN, _BORNE_MAX = 0.0, 20.0


def _idu_from_delta(row: dict) -> str | None:
    """Reconstruit l'IDU cadastral (14 car.) d'une ligne DELTA au grain parcelle :
    INSEE(5=974+commune) + prefixe(3) + section(2) + parcelle(4), zéro-complétés. None si
    incomplet — on ne fabrique jamais un identifiant partiel."""
    dep = (row.get("departement") or "").strip()
    com = (row.get("commune") or "").strip()
    sec = (row.get("section") or "").strip()
    par = (row.get("parcelle") or "").strip()
    if dep != "974" or len(com) != 2 or not sec or not par:
        return None
    pre = (row.get("prefixe") or "").strip() or "000"
    idu = f"{dep}{com}{pre.zfill(3)}{sec.zfill(2)}{par.zfill(4)}"
    return idu if len(idu) == 14 else None

_SOURCE_LABEL = (f"DGFiP — application DELTA, jeu ouvert « {DATASET} » "
                 "(data.economie.gouv.fr), délibération {def_prov}")


def _fetch_records(where: str, *, client: httpx.Client) -> list[dict]:
    """Récupère toutes les lignes de l'API ODS répondant au filtre (paginé, limit 100)."""
    out: list[dict] = []
    offset = 0
    while True:
        r = client.get(API_BASE, params={"where": where, "limit": 100, "offset": offset})
        r.raise_for_status()
        results = r.json().get("results", [])
        out.extend(results)
        if len(results) < 100:
            break
        offset += 100
    return out


def ingest_taxe_amenagement(
    session: Session, *,
    records_communaux: list[dict] | None = None,
    record_departemental: dict | None = None,
    records_secteurs: list[dict] | None = None,
    client: httpx.Client | None = None,
    log=print,
) -> dict:
    """Alimente `taxe_amenagement_taux` (taux GÉNÉRAUX) et `taxe_amenagement_secteur` (SECTEURS à
    taux majoré, au grain parcelle) depuis DELTA — ou depuis des `records_*` fournis (tests).

    Rend {"n", "communes", "manquantes", "hors_bornes", "taux_departemental_pct", "secteurs",
    "secteurs_communes", "secteurs_hors_bornes"}. Le taux départemental est REMONTÉ (confirmation)
    mais N'entre PAS dans la table communale — il reste porté par la config datée (décision Vic)."""
    from .run_all import REUNION_COMMUNES

    if records_communaux is None:
        own = client is None
        c = client or httpx.Client(
            timeout=max(get_settings().http_timeout_s, 120.0),
            headers={"User-Agent": constants.USER_AGENT}, follow_redirects=True)
        try:
            records_communaux = _fetch_records(_WHERE_COMMUNAL, client=c)
            if record_departemental is None:
                dep = _fetch_records(_WHERE_DEPARTEMENTAL, client=c)
                record_departemental = dep[0] if dep else None
            # TAXE-FIX-1 point 3 — les secteurs à taux majoré (grain parcelle) : réingérés ici même.
            if records_secteurs is None:
                records_secteurs = _fetch_records(_WHERE_SECTEUR, client=c)
        finally:
            if own:
                c.close()

    session.execute(text(_TAUX_DDL))   # idempotent, sur la session (transaction-safe)

    # Dédup défensive : on garde, par commune, la délibération à la date d'effet la plus
    # récente (l'API filtre déjà date_fin null, mais deux effets successifs peuvent coexister).
    par_insee: dict[str, dict] = {}
    hors_bornes: list[str] = []
    for row in records_communaux:
        dep = (row.get("departement") or "").strip()
        com = (row.get("commune") or "").strip()
        if dep != "974" or not com:
            continue
        insee = f"{dep}{com}"
        if len(insee) != 5 or not insee.startswith("974"):
            continue
        taux = row.get("taux")
        try:
            taux = float(taux)
        except (TypeError, ValueError):
            continue
        if not (_BORNE_MIN <= taux <= _BORNE_MAX):
            hors_bornes.append(f"{insee}={taux}")
            continue
        effet = (row.get("date_effet") or "").strip() or None
        prev = par_insee.get(insee)
        if prev is None or (effet or "") > (prev.get("date_effet") or ""):
            par_insee[insee] = {"taux": taux, "date_effet": effet,
                                "def_prov": (row.get("def_prov") or "").strip() or "?",
                                "libelle": (row.get("libelle_commune") or "").strip()}

    # Purge + upsert : la table reflète EXACTEMENT le millésime servi (idempotent).
    session.execute(text("DELETE FROM taxe_amenagement_taux"))
    for insee, d in sorted(par_insee.items()):
        session.execute(text(
            "INSERT INTO taxe_amenagement_taux (insee, part_communale_pct, source, delib_date, maj_at) "
            "VALUES (:i, :t, :s, :d, now())"),
            {"i": insee, "t": d["taux"],
             "s": _SOURCE_LABEL.format(def_prov=d["def_prov"]),
             "d": d["date_effet"]})
    session.flush()

    vus = set(par_insee)
    manquantes = sorted(nom for insee, nom in REUNION_COMMUNES if insee not in vus)
    if manquantes:
        log(f"  ⚠ taxe d'aménagement : communes absentes de DELTA : {manquantes}")
    if hors_bornes:
        log(f"  ⚠ taxe d'aménagement : taux hors bornes écartés : {hors_bornes}")

    taux_dep = None
    if record_departemental is not None:
        try:
            taux_dep = float(record_departemental.get("taux"))
        except (TypeError, ValueError):
            taux_dep = None

    # TAXE-FIX-1 point 3 — SECTEURS À TAUX MAJORÉ (grain parcelle → IDU exact). Purge + upsert,
    # même doctrine (bornes [0;20] excluent les sentinelles 99 %, dédup sur la date d'effet).
    session.execute(text(_SECTEUR_DDL))
    par_idu: dict[str, dict] = {}
    secteurs_hors_bornes: list[str] = []
    for row in (records_secteurs or []):
        idu = _idu_from_delta(row)
        if not idu:
            continue
        try:
            taux = float(row.get("taux"))
        except (TypeError, ValueError):
            continue
        if not (_BORNE_MIN <= taux <= _BORNE_MAX):
            secteurs_hors_bornes.append(f"{idu}={taux}")
            continue
        effet = (row.get("date_effet") or "").strip() or None
        prev = par_idu.get(idu)
        if prev is None or (effet or "") > (prev.get("date_effet") or ""):
            par_idu[idu] = {"taux": taux, "date_effet": effet,
                            "def_prov": (row.get("def_prov") or "").strip() or "?"}
    session.execute(text("DELETE FROM taxe_amenagement_secteur"))
    for idu, d in sorted(par_idu.items()):
        session.execute(text(
            "INSERT INTO taxe_amenagement_secteur (idu, insee, part_communale_pct, source, delib_date, maj_at) "
            "VALUES (:i, :n, :t, :s, :d, now())"),
            {"i": idu, "n": idu[:5], "t": d["taux"],
             "s": _SOURCE_LABEL.format(def_prov=d["def_prov"]), "d": d["date_effet"]})
    session.flush()
    secteurs_communes = sorted({idu[:5] for idu in par_idu})
    if par_idu:
        log(f"  taxe d'aménagement : {len(par_idu)} parcelles en secteur à taux majoré "
            f"({len(secteurs_communes)} communes)")
    if secteurs_hors_bornes:
        log(f"  ⚠ taxe d'aménagement : secteurs hors bornes écartés : {len(secteurs_hors_bornes)}")

    return {"n": len(par_insee), "communes": sorted(vus),
            "manquantes": manquantes, "hors_bornes": hors_bornes,
            "taux_departemental_pct": taux_dep,
            "secteurs": len(par_idu), "secteurs_communes": secteurs_communes,
            "secteurs_hors_bornes": secteurs_hors_bornes}
