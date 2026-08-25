"""M102-B3 — LE REGISTRE DE FAITS DU FIL : l'oracle des chiffres repris d'un tour antérieur.

Chaque chiffre servi par un outil est enregistré avec son OUTIL, sa SOURCE et son MILLÉSIME.
Un chiffre repris à un tour ultérieur est vérifié CONTRE CE REGISTRE, pas contre le tour
courant — s'il n'y est pas, il n'est pas servi (le verrou retombe sur le gabarit du tour
courant : le Copilote « redemande à l'outil », jamais une reprise « de mémoire »).

Règles :
· on n'enregistre que les feuilles NUMÉRIQUES d'un ToolResult (valeur + data aplatie) — un
  fait = {clé, valeur, outil, source, millésime} ;
· le registre est borné par la conversation ET par le même TTL que le fil (config
  copilote_v2_contexte_ttl_minutes) — le contexte ne traîne pas ;
· la persistance ne casse JAMAIS une réponse (try/except + rollback, motif historique.py).
"""
from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.orm import Session

DDL = """
CREATE TABLE IF NOT EXISTS copilote_faits (
  id serial PRIMARY KEY,
  conversation_id int REFERENCES copilote_conversations(id) ON DELETE CASCADE,
  outil varchar(32) NOT NULL,
  cle text NOT NULL,
  valeur double precision NOT NULL,
  source text, millesime text,
  ts timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_copilote_faits_conv ON copilote_faits (conversation_id, ts DESC);
"""

#: plafond de faits transmis au formuler (les plus récents d'abord) — un prompt, pas une base.
FAITS_MAX = 40


def _feuilles_numeriques(obj, prefixe: str = "") -> list[tuple[str, float]]:
    """Aplati un dict/list en feuilles (clé.pointée, valeur numérique). Bool exclus."""
    out: list[tuple[str, float]] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.extend(_feuilles_numeriques(v, f"{prefixe}{k}."))  # GB-012 : « if prefixe or True else k » — else mort (toujours vrai)
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj[:20]):
            out.extend(_feuilles_numeriques(v, f"{prefixe}{i}."))
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        out.append((prefixe.rstrip("."), float(obj)))
    return out


def extraire_faits(res) -> list[dict]:
    """Les faits numériques d'un ToolResult — PURE (pas de base), appelée par answering."""
    faits: list[dict] = []
    vus: set[tuple[str, float]] = set()
    sources = {"outil": res.tool, "source": res.source, "millesime": res.millesime}
    if isinstance(res.valeur, (int, float)) and not isinstance(res.valeur, bool):
        faits.append({"cle": "valeur", "valeur": float(res.valeur), **sources})
        vus.add(("valeur", float(res.valeur)))
    for cle, v in _feuilles_numeriques(res.data or {}):
        if (cle, v) not in vus:
            faits.append({"cle": cle, "valeur": v, **sources})
            vus.add((cle, v))
    return faits[:FAITS_MAX]


def enregistrer(db: Session, conversation_id: int | None, faits: list[dict]) -> None:
    """Persiste les faits du tour. Jamais d'exception sortante."""
    if not conversation_id or not faits:
        return
    try:
        db.execute(text(DDL))
        for f in faits:
            db.execute(text(
                "INSERT INTO copilote_faits (conversation_id, outil, cle, valeur, source, millesime) "
                "VALUES (:c, :o, :k, :v, :s, :m)"),
                {"c": conversation_id, "o": str(f.get("outil") or "?")[:32], "k": str(f["cle"])[:200],
                 "v": float(f["valeur"]), "s": f.get("source"), "m": f.get("millesime")})
    except Exception:
        db.rollback()


def du_fil(db: Session, compte_id: int | None, conversation_id: int, ttl_minutes: int) -> list[dict]:
    """Les faits du fil (mêmes bornes que historique.fil : conversation + compte + TTL).
    Jamais d'exception sortante (registre illisible = aucune reprise possible, pas un crash)."""
    try:
        rows = db.execute(text(
            "SELECT f.outil, f.cle, f.valeur, f.source, f.millesime FROM copilote_faits f "
            "JOIN copilote_conversations c ON c.id = f.conversation_id "
            "WHERE f.conversation_id = :i AND c.compte_id IS NOT DISTINCT FROM :cp "
            "  AND c.updated_at >= now() - make_interval(mins => :ttl) "
            "ORDER BY f.ts DESC, f.id DESC LIMIT :n"),
            {"i": conversation_id, "cp": compte_id, "ttl": int(ttl_minutes),
             "n": FAITS_MAX}).mappings().all()
        return [dict(r) for r in rows]
    except Exception:
        db.rollback()
        return []


def valeurs(faits: list[dict]) -> set[float]:
    """Les valeurs autorisées du registre (pour le verrou anti-invention étendu)."""
    out: set[float] = set()
    for f in faits or []:
        try:
            v = round(float(f["valeur"]), 2)
        except (TypeError, ValueError, KeyError):
            continue
        out.add(v)
        out.add(round(v))
    return out


def contexte_formuler(faits: list[dict]) -> list[dict] | None:
    """Les faits présentés au formuler (clé/valeur/source/millésime) — il ne peut reprendre
    QUE ceux-là, en citant leur source (FORMULE_SYSTEM, M102-B3)."""
    if not faits:
        return None
    return [{"cle": f["cle"], "valeur": f["valeur"], "outil": f.get("outil"),
             "source": f.get("source"), "millesime": f.get("millesime")} for f in faits]


def _json(o) -> str:  # utilitaire debug/tests
    return json.dumps(o, ensure_ascii=False, default=str)
