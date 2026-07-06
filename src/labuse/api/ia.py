"""COPILOTE IA (Vague 2) — trois capacités, une doctrine absolue.

DOCTRINE : l'IA ne calcule NI ne modifie AUCUN score, et n'accède JAMAIS à la base.
  1. Recherche en langage naturel → JSON de filtres VALIDÉ PAR SCHÉMA → chips existants.
  2. Synthèse de fiche → uniquement depuis le JSON tracé de la parcelle (zéro invention).
  3. « Pourquoi ce score ? » → pédagogie des lignes Q/A tracées.

Provider : Anthropic si ANTHROPIC_API_KEY présent (haiku pour la NL, sonnet pour la synthèse,
timeout + retry), sinon STUB LOCAL DÉTERMINISTE (flaggé `stub: true` dans chaque réponse et
affiché à l'écran). Chaque appel est journalisé (table ia_log : modèle, tokens, coût estimé).
"""
from __future__ import annotations

import json
import os
import re

from fastapi import APIRouter, Depends
from jsonschema import ValidationError, validate
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

router = APIRouter(prefix="/ia", tags=["ia"])

MODEL_NL = "claude-haiku-4-5-20251001"
MODEL_SYNTH = "claude-sonnet-4-6"
#: €/Mtoken approx (log de coût indicatif)
PRICE = {MODEL_NL: (1.0, 5.0), MODEL_SYNTH: (3.0, 15.0)}


def get_db():
    from .app import get_db as _g
    yield from _g()


DDL_IA = """
CREATE TABLE IF NOT EXISTS ia_log (
  id serial PRIMARY KEY, ts timestamptz DEFAULT now(), kind varchar(24), model varchar(64),
  stub boolean, tokens_in integer, tokens_out integer, cout_eur numeric(8,5)
);
"""


def ensure_tables(engine) -> None:
    with engine.begin() as c:
        c.execute(text(DDL_IA))


def _has_key() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _log(db: Session, kind: str, model: str, stub: bool, tin: int = 0, tout: int = 0) -> None:
    pin, pout = PRICE.get(model, (0, 0))
    db.execute(text("INSERT INTO ia_log (kind, model, stub, tokens_in, tokens_out, cout_eur) "
                    "VALUES (:k, :m, :s, :ti, :to, :c)"),
               {"k": kind, "m": model, "s": stub, "ti": tin, "to": tout,
                "c": (tin * pin + tout * pout) / 1_000_000})


@router.get("/status")
def ia_status() -> dict:
    return {"provider": "anthropic" if _has_key() else "stub",
            "modeles": {"recherche": MODEL_NL, "synthese": MODEL_SYNTH},
            "doctrine": "l'IA ne calcule ni ne modifie aucun score ; aucun accès base"}


# ───────────────────────── 1. RECHERCHE NL → FILTRES ─────────────────────────

FILTER_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "statuts": {"type": "array", "items": {"enum": ["chaude", "a_surveiller", "a_creuser", "ecartee"]}},
        "scoreMin": {"type": ["integer", "null"], "minimum": 0, "maximum": 100},
        "surfaceMin": {"type": ["integer", "null"], "minimum": 0},
        "surfaceMax": {"type": ["integer", "null"], "minimum": 0},
        "sdpMin": {"type": ["integer", "null"], "minimum": 0},
        "evenement": {"type": "boolean"},
        "vueMer": {"type": "boolean"},
        "flags": {"type": "array", "items": {"enum": ["sol_pollue", "abf", "icpe", "risques", "prescription_plu"]}},
    },
}


class SearchIn(BaseModel):
    text: str


def _stub_nl(t: str) -> tuple[dict | None, str]:
    """Stub local : règles lexicales déterministes. Renvoie (filtres, explication) ou (None, refus)."""
    low = t.lower()
    f: dict = {"statuts": [], "scoreMin": None, "surfaceMin": None, "surfaceMax": None,
               "sdpMin": None, "evenement": False, "vueMer": False, "flags": []}
    hits = []
    if re.search(r"chaude", low):
        f["statuts"].append("chaude")
        hits.append("statut chaude")
    if re.search(r"surveill", low):
        f["statuts"].append("a_surveiller")
        hits.append("à surveiller")
    if re.search(r"creuser", low):
        f["statuts"].append("a_creuser")
        hits.append("à creuser")
    if re.search(r"vue\s*mer|front de mer|voit la mer", low):
        f["vueMer"] = True
        hits.append("vue mer")
    if re.search(r"événement|evenement|bodacc|liquidation|procédure", low):
        f["evenement"] = True
        hits.append("événement BODACC")
    if re.search(r"pollu", low):
        f["flags"].append("sol_pollue")
        hits.append("flag pollution")
    if re.search(r"\babf\b|monument|bâtiment de france", low):
        f["flags"].append("abf")
        hits.append("flag ABF")
    if re.search(r"\bicpe\b|usine|industriel", low):
        f["flags"].append("icpe")
        hits.append("flag ICPE")
    if re.search(r"risque|ppr|inond", low):
        f["flags"].append("risques")
        hits.append("flag risques")
    m = re.search(r"(?:plus de|au moins|>\s*|≥\s*|superieure? à|supérieure? à)\s*([\d\s]{2,9})\s*(?:m2|m²)", low)
    if m:
        f["surfaceMin"] = int(m.group(1).replace(" ", ""))
        hits.append(f"surface ≥ {f['surfaceMin']} m²")
    m = re.search(r"(?:moins de|<\s*|≤\s*|inferieure? à|inférieure? à)\s*([\d\s]{2,9})\s*(?:m2|m²)", low)
    if m:
        f["surfaceMax"] = int(m.group(1).replace(" ", ""))
        hits.append(f"surface ≤ {f['surfaceMax']} m²")
    m = re.search(r"sdp[^\d]{0,20}([\d\s]{2,9})", low)
    if m:
        f["sdpMin"] = int(m.group(1).replace(" ", ""))
        hits.append(f"SDP ≥ {f['sdpMin']} m²")
    m = re.search(r"(?:score|q)\s*(?:>|≥|d'au moins|au dessus de|supérieur à)\s*(\d{2,3})", low)
    if m:
        f["scoreMin"] = int(m.group(1))
        hits.append(f"Q ≥ {f['scoreMin']}")
    if not hits:
        return None, ("Hors périmètre : je sais traduire des critères de recherche foncière "
                      "(statut, vue mer, surface, SDP, score, événement, flags). Reformulez ?")
    return f, "Filtres appliqués : " + ", ".join(hits) + "."


_NL_SYSTEM = """Tu traduis une demande de prospection foncière en JSON de filtres.
Tu renvoies UNIQUEMENT un objet JSON conforme au schéma (aucun texte autour) :
{schema}
Champs non mentionnés → valeur neutre ([], null, false). Si la demande est hors périmètre
(pas une recherche foncière filtrable), renvoie {{"out_of_scope": "raison courte"}}."""


@router.post("/search")
def ia_search(body: SearchIn, db: Session = Depends(get_db)) -> dict:
    if _has_key():
        import anthropic
        client = anthropic.Anthropic(timeout=20.0, max_retries=2)
        msg = client.messages.create(
            model=MODEL_NL, max_tokens=400,
            system=_NL_SYSTEM.format(schema=json.dumps(FILTER_SCHEMA, ensure_ascii=False)),
            messages=[{"role": "user", "content": body.text}])
        raw = msg.content[0].text.strip()
        _log(db, "search", MODEL_NL, False, msg.usage.input_tokens, msg.usage.output_tokens)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return {"stub": False, "out_of_scope": "réponse IA illisible — réessayez"}
        if "out_of_scope" in data:
            return {"stub": False, "out_of_scope": data["out_of_scope"]}
        try:
            validate(data, FILTER_SCHEMA)   # le schéma est le GARDE-FOU : jamais de filtre inventé
        except ValidationError as exc:
            return {"stub": False, "out_of_scope": f"filtre non conforme ({exc.message[:60]}) — réessayez"}
        return {"stub": False, "filters": data, "explanation": "Filtres proposés par l'IA (validés par schéma)."}
    filters, explanation = _stub_nl(body.text)
    _log(db, "search", "stub-local", True)
    if filters is None:
        return {"stub": True, "out_of_scope": explanation}
    validate(filters, FILTER_SCHEMA)
    return {"stub": True, "filters": filters, "explanation": explanation}


# ───────────────────── 2. SYNTHÈSE DE FICHE / 3. POURQUOI CE SCORE ─────────────────────

def _fiche_json(db: Session, idu: str) -> dict:
    from .app import _q_v2_fiche
    return _q_v2_fiche(db, idu)


def _stub_synthese(f: dict) -> str:
    pos = sorted([ln for ln in f["lines"] if (ln["weight"] or 0) > 0], key=lambda x: -x["weight"])[:3]
    neg = sorted([ln for ln in f["lines"] if (ln["weight"] or 0) < 0], key=lambda x: x["weight"])[:3]
    unk = [ln for ln in f["lines"] if ln["result"] == "UNKNOWN"]
    p = [f"Parcelle {f['idu']} ({f.get('surface_m2') or '?'} m², {f['commune']}) — statut "
         f"« {f['statut']} » : qualité {f['q_score']}/100, accessibilité {f['a_score']}/100, "
         f"complétude {f['completeness_score']} %."]
    if f.get("evenement") == "rouge":
        p.append(f"⚠ Événement : {f.get('evenement_detail')}")
    if pos:
        p.append("Points forts : " + " · ".join(f"{ln['layer']} ({ln['weight']:+d}) — {ln['detail']}" for ln in pos))
    if neg:
        p.append("Points de vigilance : " + " · ".join(f"{ln['layer']} ({ln['weight']:+d}) — {ln['detail']}" for ln in neg))
    if unk:
        p.append(f"Inconnues ({len(unk)}) : " + ", ".join(ln["layer"] for ln in unk[:5]) + ".")
    return "\n\n".join(p)


def _stub_pourquoi(f: dict) -> str:
    def axe(name: str, key: str, score: int) -> str:
        lines = sorted([ln for ln in f["lines"] if ln["axis"] == key and ln["weight"]],
                       key=lambda x: -abs(x["weight"]))
        detail = "\n".join(f"  {ln['weight']:+d}  {ln['layer']} — {ln['detail']}" for ln in lines) or "  (aucun signal chiffré)"
        return f"{name} = base 50 {'+' if score >= 50 else '−'} signaux → {score}/100 :\n{detail}"
    return (axe("QUALITÉ (le terrain vaut-il le coup ?)", "q", f["q_score"]) + "\n\n"
            + axe("ACCESSIBILITÉ (peut-on l'acheter ?)", "a", f["a_score"])
            + "\n\nChaque ligne est tracée à sa source (cliquable dans la fiche). "
              "Le score est 100 % déterministe — l'IA n'y contribue pas.")


_SYNTH_SYSTEM = ("Tu rédiges une synthèse de prospection foncière EXCLUSIVEMENT à partir du JSON "
                 "fourni (fiche tracée). INTERDIT d'inventer un fait absent du JSON. Concis, "
                 "professionnel, français. Termine par les inconnues à lever.")


def _real_text(db: Session, kind: str, system: str, payload: dict) -> str:
    import anthropic
    client = anthropic.Anthropic(timeout=30.0, max_retries=2)
    msg = client.messages.create(model=MODEL_SYNTH, max_tokens=700, system=system,
                                 messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}])
    _log(db, kind, MODEL_SYNTH, False, msg.usage.input_tokens, msg.usage.output_tokens)
    return msg.content[0].text


@router.post("/synthese/{idu}")
def ia_synthese(idu: str, db: Session = Depends(get_db)) -> dict:
    f = _fiche_json(db, idu)
    if _has_key():
        return {"stub": False, "texte": _real_text(db, "synthese", _SYNTH_SYSTEM, f),
                "mention": "Synthèse générée — vérifier les sources (chaque fait est tracé dans la fiche)."}
    _log(db, "synthese", "stub-local", True)
    return {"stub": True, "texte": _stub_synthese(f),
            "mention": "Synthèse générée (stub local, clé IA absente) — vérifier les sources."}


@router.post("/pourquoi/{idu}")
def ia_pourquoi(idu: str, db: Session = Depends(get_db)) -> dict:
    f = _fiche_json(db, idu)
    if _has_key():
        sys_p = ("Tu expliques pédagogiquement un score foncier à partir du JSON de lignes tracées. "
                 "INTERDIT d'inventer. Rappelle que le score est déterministe et tracé.")
        return {"stub": False, "texte": _real_text(db, "pourquoi", sys_p, f),
                "mention": "Explication générée — le score reste 100 % déterministe."}
    _log(db, "pourquoi", "stub-local", True)
    return {"stub": True, "texte": _stub_pourquoi(f),
            "mention": "Explication générée (stub local) — le score reste 100 % déterministe."}
