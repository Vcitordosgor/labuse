"""Suggestion unifiée des barres de recherche — RETOURS-16 V5.

Demande Vic : « sur toutes les barres de recherche de l'app, il faut qu'il y ait comme pour une
adresse une recherche qui devine la fin ». UN endpoint (``GET /api/recherche/suggest``), appelé
au fil de la frappe par LE composant de barre partagé (front ``AddressAutocomplete``) — aucune
barre ne garde son autocomplétion maison.

Six grammaires, chacune typée dans la réponse (le type s'affiche en libellé discret) :
``adresse`` (table BAN interne, même requête que /adresses/autocomplete) · ``cadastre`` (IDU
complet/partiel + référence courte « BZ1065 » / « BZ 65 » — si plusieurs communes, elles
apparaissent TOUTES) · ``proprietaire`` (dénomination PM réelle en base) · ``siren`` (préfixe) ·
``commune`` (les 24) · ``projet`` (les projets du COMPTE de la session, jamais ceux d'un autre).

L'aiguillage suit la FORME de la saisie (la grammaire T1, miroir de lib/format.ts — LOI-3 côté
serveur : ce module est le seul endroit) : chiffres → SIREN + IDU ; section+numéro → cadastre ;
texte → adresse/commune/propriétaire/projet. 8 propositions maximum au total. Le serveur ne
devine JAMAIS à la place de l'utilisateur : il propose, la barre ne substitue qu'au clic/Entrée.

Perf (mandat : < 150 ms) : chaque grammaire = une requête indexée LIMIT n ; l'index
``ix_parcels_section_numero`` (posé au heal du boot) rend la référence courte instantanée
(equality + préfixe varchar_pattern_ops ; mesuré : 799 ms seq-scan → < 5 ms). La réponse porte
``ms`` (temps serveur mesuré, honnêteté).
"""
from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/recherche", tags=["recherche"])
log = logging.getLogger("labuse")

MAX_TOTAL = 8   # propositions maximum, tous types confondus (mandat V5.3)

_RE_SECTION_NUMERO = re.compile(r"^([A-Za-z]{1,2})[\s-]?(\d{1,4})$")   # miroir estSectionNumero
_RE_IDU_PARTIEL = re.compile(r"^\d{5}[0-9A-Za-z]{0,9}$")               # IDU en cours de frappe


def ensure_index(engine) -> None:
    """Index du suggest (mandat V5 : réponse < 150 ms, index sur les colonnes interrogées).

    · (section, numéro) : la référence courte se résout en equality/préfixe (799 ms seq-scan
      mesuré sur 431k parcelles → < 5 ms) ; varchar_pattern_ops → « BZ 10 » (préfixe) indexé.
    · GIN trigram sur l'adresse PLIÉE (expression LITTÉRALE sql_plie_lit, la même que la
      requête — un bind casserait le match du planneur) : le LIKE '%…%' plié passait par un
      seq-scan de 340k adresses (~290 ms mesurés SUR CHAQUE frappe texte) → indexé."""
    from ..constants import sql_plie_lit
    expr = sql_plie_lit("coalesce(numero,'') || ' ' || voie")
    with engine.begin() as c:
        c.execute(text("CREATE INDEX IF NOT EXISTS ix_parcels_section_numero "
                       "ON parcels (section, numero varchar_pattern_ops)"))
        c.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        c.execute(text(f"CREATE INDEX IF NOT EXISTS ix_adresses_suggest_trgm ON adresses "
                       f"USING gin (({expr}) gin_trgm_ops) "
                       f"WHERE idu IS NOT NULL AND geom IS NOT NULL"))


def get_db():   # branché sur la session app au moment de l'inclusion (cf. app.py, patron tiles)
    from .app import get_db as _g
    yield from _g()


# ── communes : 24 noms + centre (communes974.geojson, le même fichier que la carte) ──
_communes_cache: list[dict] | None = None


def _communes() -> list[dict]:
    global _communes_cache
    if _communes_cache is not None:
        return _communes_cache
    try:
        from shapely.geometry import shape
        racine = Path(__file__).resolve().parents[3] / "frontend"
        src = next(p for p in (racine / "dist" / "communes974.geojson",
                               racine / "public" / "communes974.geojson") if p.exists())
        out = []
        for f in json.loads(src.read_text(encoding="utf-8"))["features"]:
            pt = shape(f["geometry"]).representative_point()
            out.append({"nom": f["properties"]["nom"], "insee": f["properties"]["code"],
                        "lon": round(pt.x, 5), "lat": round(pt.y, 5)})
        _communes_cache = sorted(out, key=lambda c: c["nom"])
    except Exception as e:  # noqa: BLE001 — fichier absent : les 5 autres grammaires servent
        log.error("recherche/suggest : communes974.geojson illisible (%s)", e)
        _communes_cache = []
    return _communes_cache


def _plie(s: str) -> str:
    import unicodedata
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


# ── une fonction par grammaire — chacune UNE requête bornée, jamais de cascade ──

def _sugg_cadastre(db: Session, q: str, n: int) -> list[dict]:
    dg = q.upper().replace(" ", "").replace("-", "")
    items: list[tuple] = []
    m = _RE_SECTION_NUMERO.match(q.strip())
    if m:
        sec, num = m.group(1).upper(), m.group(2).lstrip("0") or "0"
        # exactes d'abord (toutes les communes apparaissent), puis les préfixes pour compléter
        items = db.execute(text(
            """SELECT idu, commune, surface_m2, ST_X(ST_Centroid(geom)) lon, ST_Y(ST_Centroid(geom)) lat
               FROM parcels WHERE section = :s AND (numero = :n OR numero LIKE :np)
               ORDER BY (numero = :n) DESC, length(numero), numero, commune LIMIT :lim"""),
            {"s": sec, "n": num, "np": f"{num}%", "lim": n}).all()
    elif _RE_IDU_PARTIEL.match(dg):
        items = db.execute(text(
            """SELECT idu, commune, surface_m2, ST_X(ST_Centroid(geom)) lon, ST_Y(ST_Centroid(geom)) lat
               FROM parcels WHERE idu LIKE :p ORDER BY idu LIMIT :lim"""),
            {"p": f"{dg}%", "lim": n}).all()
    out = []
    for idu, commune, surf, lon, lat in items:
        ref = f"{idu[8:10].lstrip('0') or idu[8:10]} {idu[10:].lstrip('0') or '0'}"
        out.append({"label": f"{ref} — {commune}", "sub": f"{round(surf):,} m²".replace(",", " ") if surf else "",
                    "idu": idu, "lon": lon, "lat": lat})
    return out


def _sugg_adresse(db: Session, q: str, n: int) -> list[dict]:
    # Même PLIAGE que /adresses/autocomplete, en variante indexable : expression LITTÉRALE côté
    # colonne (celle de l'index GIN trigram, ensure_index) + aiguille pliée en Python (plie()).
    from ..constants import plie, sql_plie_lit
    col = sql_plie_lit("coalesce(numero,'') || ' ' || voie")
    rows = db.execute(text(
        f"""SELECT trim(coalesce(numero,'') || ' ' || voie) AS label, commune, code_postal, idu,
                   ST_X(geom) lon, ST_Y(geom) lat
            FROM adresses
            WHERE idu IS NOT NULL AND geom IS NOT NULL AND {col} LIKE '%' || :qp || '%'
            ORDER BY ({col} LIKE :qp || '%') DESC, length(voie), voie, numero
            LIMIT :lim"""), {"qp": plie(q), "lim": n}).mappings().all()
    return [{"label": r["label"], "sub": f"{r['code_postal'] or ''} {r['commune'] or ''}".strip(),
             "idu": r["idu"], "lon": r["lon"], "lat": r["lat"]} for r in rows]


def _sugg_proprietaire(db: Session, q: str, n: int) -> list[dict]:
    from ..proprietaire_facettes import autocomplete
    return [{"label": s["denomination"], "sub": f"{s['n']} parcelle{'s' if s['n'] > 1 else ''}",
             "siren": s["siren"]} for s in autocomplete(db, q, limit=n)]


def _sugg_siren(db: Session, q: str, n: int) -> list[dict]:
    dg = re.sub(r"\D", "", q)[:9]
    if len(dg) < 3:
        return []
    rows = db.execute(text(
        """SELECT denomination, siren, count(*) n FROM parcelle_personne_morale
           WHERE siren LIKE :p GROUP BY 1, 2 ORDER BY n DESC LIMIT :lim"""),
        {"p": f"{dg}%", "lim": n}).all()
    return [{"label": d, "sub": f"SIREN {s}", "siren": s} for d, s, _n in rows]


def _sugg_commune(q: str, n: int) -> list[dict]:
    plie = _plie(q)
    hits = [c for c in _communes() if _plie(c["nom"]).startswith(plie)] or \
           [c for c in _communes() if plie in _plie(c["nom"])]
    return [{"label": c["nom"], "sub": "commune", "commune": c["nom"], "insee": c["insee"],
             "lon": c["lon"], "lat": c["lat"]} for c in hits[:n]]


def _sugg_projet(db: Session, request: Request, q: str, n: int) -> list[dict]:
    from .. import models
    from .tenant import current_compte
    cid = current_compte(request)
    query = db.query(models.Projet).filter(models.Projet.nom.ilike(f"%{q}%"))
    query = query.filter(models.Projet.compte_id.is_(None) if cid is None
                         else models.Projet.compte_id == cid)   # SEC-IDOR : jamais un autre compte
    return [{"label": p.nom, "sub": "projet", "projet_id": p.id}
            for p in query.order_by(models.Projet.updated_at.desc()).limit(n).all()]


TYPES = ("cadastre", "adresse", "commune", "proprietaire", "siren", "projet")
FORMATS = "adresse, IDU, référence courte (BZ1065), SIREN, nom de propriétaire, commune, projet"


@router.get("/suggest")
def suggest(request: Request, q: str = Query(..., min_length=1),
            types: str | None = None, db: Session = Depends(get_db)) -> dict:
    """Suggestions groupées par type. `types` (csv) restreint aux grammaires que la barre
    appelante sait consommer (une barre parcelle ne propose pas un projet). Déclenché à
    2 caractères côté client (anti-rebond ~200 ms + annulation)."""
    t0 = time.monotonic()
    q = q.strip()
    voulus = [t for t in (types.split(",") if types else TYPES) if t in TYPES]
    if len(q) < 2 or not voulus:
        return {"q": q, "groupes": [], "total": 0, "ms": 0, "formats": FORMATS}

    # aiguillage par FORME (grammaire T1) : ne lancer QUE les grammaires plausibles, dans
    # l'ordre de pertinence — le budget de 8 se remplit type par type.
    chiffres = re.sub(r"\D", "", q)
    ordre: list[str]
    if len(chiffres) >= 3 and chiffres == q.replace(" ", ""):
        # chiffres PURS : SIREN d'abord (un IDU partiel « 97411… » est AUSSI des chiffres —
        # le cadastre suit ; sans cet ordre, « 428173 » matchait la regex IDU et SIREN ne
        # tournait jamais — mesuré 0 proposition sur un SIREN réel).
        ordre = ["siren", "cadastre"]
    elif _RE_SECTION_NUMERO.match(q) or _RE_IDU_PARTIEL.match(q.upper().replace(" ", "")):
        ordre = ["cadastre", "proprietaire"]      # « BZ1065 » peut aussi être un début de nom
    else:
        ordre = ["adresse", "commune", "proprietaire", "projet"]
    ordre = [t for t in ordre if t in voulus]

    groupes: list[dict] = []
    total = 0
    for t in ordre:
        reste = MAX_TOTAL - total
        if reste <= 0:
            break
        n = min(reste, 5 if len(ordre) == 1 else 4 if t == ordre[0] else 3)
        try:
            items = ({"cadastre": lambda: _sugg_cadastre(db, q, n),
                      "adresse": lambda: _sugg_adresse(db, q, n),
                      "proprietaire": lambda: _sugg_proprietaire(db, q, n),
                      "siren": lambda: _sugg_siren(db, q, n),
                      "commune": lambda: _sugg_commune(q, n),
                      "projet": lambda: _sugg_projet(db, request, q, n)}[t])()
        except Exception as e:  # noqa: BLE001 — une grammaire qui casse ne mange pas les autres
            log.error("recherche/suggest : grammaire « %s » en échec (%s)", t, e)
            items = []
        if items:
            groupes.append({"type": t, "items": items})
            total += len(items)
    return {"q": q, "groupes": groupes, "total": total,
            "ms": round((time.monotonic() - t0) * 1000, 1), "formats": FORMATS}
