"""SOURCES-1 lot 2 — AZI et TRI par commune (Géorisques GASPAR).

Le FAIT documentaire : quelles communes sont couvertes par un atlas des zones inondables
(AZI) et par un territoire à risque important d'inondation (TRI), avec libellé, risques et
dates — vérifié live 07/09/2026 (`gaspar/azi` et `gaspar/tri`, ex. 97411 : AZI « La
Montagne » 2004, TRI Saint-Denis/Sainte-Marie 2013).

La GÉOMÉTRIE d'aléa inondation n'est PAS ré-ingérée ici : l'ALEA_INONDATION du WFS Carmen
DEAL (75 zones) est un doublon vérifié de `georisque_alea` subtype `inondation` (76 entités
DEAL Lizmap) déjà servies par la couche cascade `risques` — l'AZI/TRI entre comme fait par
commune (fiche commune, Risques), jamais deux couches pour la même emprise.
"""
from __future__ import annotations

import json

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import constants
from ..config import get_settings
from .run_all import REUNION_COMMUNES

SOURCE_NAME = "AZI / TRI — inondation (Géorisques GASPAR)"
BASE = "https://www.georisques.gouv.fr/api/v1/gaspar"

DDL = """
CREATE TABLE IF NOT EXISTS azi_communes (
    insee        varchar(5) NOT NULL,
    type_doc     varchar(3) NOT NULL,           -- azi | tri
    code_national varchar(24) NOT NULL,
    libelle      varchar(160),
    risques      text,
    date_diffusion varchar(10),
    maj_at       timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (insee, type_doc, code_national)
)
"""


def ensure_tables(engine) -> None:
    with engine.begin() as cx:
        cx.execute(text(DDL))


def ingest_azi_tri(session: Session, log=print, client: httpx.Client | None = None) -> dict:
    """Réingère AZI + TRI des 24 communes (remplacement complet, idempotent)."""
    session.execute(text("DELETE FROM azi_communes"))
    own = client is None
    c = client or httpx.Client(timeout=max(get_settings().http_timeout_s, 60.0),
                               headers={"User-Agent": constants.USER_AGENT},
                               follow_redirects=True)
    n_azi = n_tri = 0
    communes_azi: set[str] = set()
    communes_tri: set[str] = set()
    try:
        for insee, nom in REUNION_COMMUNES:
            for type_doc in ("azi", "tri"):
                r = c.get(f"{BASE}/{type_doc}",
                          params={"code_insee": insee, "page": 1, "page_size": 100})
                r.raise_for_status()
                for d in (r.json().get("data") or []):
                    code = d.get(f"code_national_{type_doc}")
                    if not code:
                        continue
                    risques = " ; ".join(
                        x.get("libelle_risque_long") or "" for x in
                        (d.get("liste_libelle_risque") or []))
                    session.execute(text(
                        "INSERT INTO azi_communes (insee, type_doc, code_national, libelle, "
                        "risques, date_diffusion, maj_at) VALUES (:i, :t, :c, :l, :r, :d, now()) "
                        "ON CONFLICT (insee, type_doc, code_national) DO UPDATE SET "
                        "libelle = :l, risques = :r, date_diffusion = :d, maj_at = now()"),
                        {"i": insee, "t": type_doc, "c": code,
                         "l": d.get(f"libelle_{type_doc}"), "r": risques,
                         "d": d.get("date_diffusion") or d.get("date_arrete_pcb")})
                    if type_doc == "azi":
                        n_azi += 1
                        communes_azi.add(nom)
                    else:
                        n_tri += 1
                        communes_tri.add(nom)
    finally:
        if own:
            c.close()
    session.flush()
    sans = sorted({nom for _, nom in REUNION_COMMUNES} - communes_azi - communes_tri)
    return {"azi": n_azi, "tri": n_tri, "communes_azi": len(communes_azi),
            "communes_tri": len(communes_tri), "communes_sans_document": sans}


def azi_tri_commune(session: Session, insee: str) -> dict | None:
    """Le fait AZI/TRI d'une commune, sourcé — None si table non peuplée (jamais deviné)."""
    rows = session.execute(text(
        "SELECT type_doc, libelle, risques, date_diffusion FROM azi_communes "
        "WHERE insee = :i ORDER BY type_doc, libelle"), {"i": insee}).mappings().all()
    if not rows:
        peuplee = session.execute(text("SELECT 1 FROM azi_communes LIMIT 1")).first()
        return ({"azi": [], "tri": [],
                 "detail": "aucun AZI ni TRI recensé pour cette commune (GASPAR)"}
                if peuplee else None)
    return {"azi": [dict(r) for r in rows if r["type_doc"] == "azi"],
            "tri": [dict(r) for r in rows if r["type_doc"] == "tri"]}


# ───────────── SOURCES-2 lot 4 — les SCÉNARIOS d'inondation des TRI (Directive Inondation) ─────────────

#: les 12 couches d'iso-hauteurs d'eau des 6 TRI du 974 (WFS Lizmap DEAL, projet 01risque —
#: vérifié 13/09/2026). TYP_INOND 01 = débordement de cours d'eau, 03 = submersion marine.
_TRI_ISO_LAYERS = [
    f"N_TRI_{tri}_ISO_HT_{alea}_S_974"
    for tri in ("BENO", "DENI", "JOSE", "PAUL", "PIER", "SUZA")
    for alea in ("DEBCE", "SUBMAR")
]
_LIZMAP_RISQUE = ("https://deal974.lizmap.com/cartes/index.php/lizmap/service"
                  "?repository=02sprinr&project=01risque")

SOURCE_TRI = "AZI / TRI — inondation (Géorisques GASPAR)"


def _scenario_di(code: str | None) -> str | None:
    """Code SCENARIO mesuré chez le producteur → scénario Directive Inondation.
    01For* = FRÉQUENT (forte probabilité) · 02Moy*/03Mcc* = MOYEN · 04Fai* = EXTRÊME (faible
    probabilité). None si code inconnu — jamais deviné."""
    c = (code or "").strip()
    if c.startswith("01"):
        return "frequent"
    if c.startswith(("02", "03")):
        return "moyen"
    if c.startswith("04"):
        return "extreme"
    return None


def ingest_tri_scenarios(session: Session, source_id: int | None = None,
                         run_id: int | None = None, log=print, client=None) -> dict:
    """SOURCES-2 lot 4 — les zones d'iso-hauteurs d'eau des TRI par SCÉNARIO
    (fréquent / moyen / extrême, + variantes « changement climatique » dites en attrs)
    → spatial_layers kind='tri_zone', subtype=scénario. Purge par kind, idempotent."""
    import httpx as _httpx

    from .. import constants as _constants
    from ..config import get_settings as _get_settings
    from .deal_carmen import _fetch_geojson, _nettoyer_geom
    from .layers_ingest import _insert_layer

    def _p(props: dict, cle: str):
        # les couches PIER/SUZA servent les champs en minuscules, les autres en MAJUSCULES
        for k, v in props.items():
            if k.lower() == cle.lower():
                return v
        return None

    session.execute(text("DELETE FROM spatial_layers WHERE kind = 'tri_zone'"))
    own = client is None
    c = client or _httpx.Client(timeout=max(_get_settings().http_timeout_s, 180.0),
                                headers={"User-Agent": _constants.USER_AGENT},
                                follow_redirects=True)
    n = inconnus = 0
    par_scenario: dict[str, int] = {}
    try:
        for typename in _TRI_ISO_LAYERS:
            feats = _fetch_geojson(_LIZMAP_RISQUE, typename, c)
            for f in feats:
                g = _nettoyer_geom(f.get("geometry")) if f.get("geometry") else None
                p = f.get("properties") or {}
                sc = _scenario_di(_p(p, "SCENARIO"))
                if not g or sc is None:
                    inconnus += 0 if g else 1
                    if g and sc is None:
                        inconnus += 1
                        log(f"  ⚠ {typename} : SCENARIO {p.get('SCENARIO')!r} inconnu — écarté")
                    continue
                alea = "submersion_marine" if (_p(p, "TYP_INOND") == "03"
                                               or "SUBMAR" in typename) else "debordement"
                _insert_layer(
                    session, "tri_zone", sc,
                    f"TRI {_p(p, 'ID_TRI') or typename} — scénario {sc}", g,
                    source_id, None, run_id,
                    attrs={"tri": _p(p, "ID_TRI"), "alea": alea,
                           "scenario_code": _p(p, "SCENARIO"),
                           "changement_climatique": "cc" in (_p(p, "SCENARIO") or "").lower(),
                           "hauteur_min_m": _p(p, "HT_MIN"), "hauteur_max_m": _p(p, "HT_MAX"),
                           "zone": _p(p, "ID_ZONE"), "date_entree": _p(p, "DATENTREE"),
                           "source": "DEAL Réunion — Lizmap (01risque, standard DI v2)"})
                n += 1
                par_scenario[sc] = par_scenario.get(sc, 0) + 1
    finally:
        if own:
            c.close()
    session.flush()
    return {"zones": n, "par_scenario": par_scenario, "ecartes": inconnus}
