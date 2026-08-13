"""M26-A — interpréteur de besoin : brief_raw → brief_json validé OU clarification.

Seul endroit du Copilote où le LLM intervient (avec la rédaction M26-C, hors mandat).
Socle M7 (`ai/core.complete`, MODEL_REASONING) ; prompt versionné dans `prompts.py`.
La sortie du modèle repasse TOUJOURS par une validation stricte côté code : schéma JSON,
communes contre la liste officielle des 24, types/bornes. Jamais de devinette : champ
obligatoire manquant → clarification (statut awaiting_user).

La conversion logements → SDP est une règle déterministe CODE (jamais le LLM) :
SDP_PAR_LOGEMENT_M2, constante documentée ci-dessous.

Mission verifier_adresse : parsing regex/BAN d'abord ; le LLM n'est appelé QUE si le
parsing déterministe ne trouve rien, et sa sortie repasse par la même validation.
"""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from typing import Callable

from jsonschema import Draft202012Validator

from ..ingestion.run_all import REUNION_COMMUNES
from .prompts import SORTIE_SCHEMA, SYSTEM_EXTRACTION_REFS, SYSTEM_INTERPRETEUR

#: Conversion programme : 1 logement collectif ≈ 70 m² de surface de plancher (SDP).
#: Règle de pouce promoteur (logement + circulations + murs), alignée sur le
#: m2_par_logement de /moteurs/assemblage. Modifiable ici, nulle part ailleurs.
SDP_PAR_LOGEMENT_M2 = 70

MISSIONS = ("instruire", "shortlist", "verifier_adresse")

_SORTIE_VALIDATOR = Draft202012Validator(SORTIE_SCHEMA)
_IDU_RE = re.compile(r"\b974\d{2}[0-9A-Z]{9}\b")


class IAIndisponible(RuntimeError):
    """Clé/API IA indisponible : le run échoue honnêtement (jamais de brief deviné)."""


@dataclass
class Interpretation:
    brief: dict | None = None
    clarification: dict | None = None      # {question, champ_manquant, options}


# ── Communes : validation contre la liste officielle des 24 ─────────────────────────────
def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"\bst\b", "saint", s.lower())
    s = re.sub(r"\bste\b", "sainte", s)
    return re.sub(r"[^a-z]", "", s)


_COMMUNES_OFFICIELLES = [nom for _insee, nom in REUNION_COMMUNES]
_COMMUNES_NORM = {_norm(nom): nom for nom in _COMMUNES_OFFICIELLES}


def commune_officielle(nom: str) -> str | None:
    return _COMMUNES_NORM.get(_norm(nom or ""))


# ── Appel modèle (injectable pour les tests — le défaut passe par le socle M7) ──────────
def _llm_reel(system: str, payload: dict, db=None) -> str:
    from ..ai import core
    res = core.complete(db, kind="agent-brief", system=system,
                        context=json.dumps(payload, ensure_ascii=False),
                        model=core.MODEL_REASONING, max_tokens=700)
    if res.degraded:
        raise IAIndisponible(res.reason or "IA indisponible")
    return res.text


def _parse_json(texte: str) -> dict:
    """JSON strict, tolérant aux clôtures markdown que les modèles ajoutent parfois."""
    t = texte.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    m = re.search(r"\{.*\}", t, re.S)
    if not m:
        raise ValueError("sortie modèle sans objet JSON")
    return json.loads(m.group())


def _clarif(question: str, champ: str, options: list[str] | None = None) -> Interpretation:
    c: dict = {"question": question, "champ_manquant": champ}
    if options:
        c["options"] = options
    return Interpretation(clarification=c)


# ── Mission instruire / shortlist ───────────────────────────────────────────────────────
def interpreter_brief(brief_raw: str, mission: str, *, precisions: list[str] | None = None,
                      llm: Callable[..., str] | None = None, db=None) -> Interpretation:
    """Interprète la phrase en brief structuré validé, ou demande une clarification."""
    if mission not in ("instruire", "shortlist"):
        raise ValueError(f"mission inconnue pour l'interpréteur de brief : {mission!r}")
    if not (brief_raw or "").strip():
        return _clarif("Décrivez votre besoin foncier (commune, programme visé, "
                       "budget éventuel).", "besoin")

    payload = {"mission": mission, "phrase": brief_raw,
               "communes_connues": _COMMUNES_OFFICIELLES,
               "precisions": precisions or []}
    sortie = _parse_json((llm or _llm_reel)(SYSTEM_INTERPRETEUR, payload, db=db))

    err = next(iter(_SORTIE_VALIDATOR.iter_errors(sortie)), None)
    if err is not None:
        raise ValueError(f"sortie interpréteur hors schéma : {err.message}")

    if "clarification" in sortie:
        c = sortie["clarification"]
        return _clarif(c["question"], c["champ_manquant"], c.get("options"))

    return _valider_brief(sortie["brief"])


def _valider_brief(b: dict) -> Interpretation:
    """Validation sémantique côté CODE (le schéma seul ne suffit pas) + défauts + conversion."""
    communes: list[str] = []
    for c in b.get("communes", []):
        off = commune_officielle(c)
        if off is None:
            return _clarif(f"« {c} » n'est pas une commune de La Réunion couverte. "
                           "Quelle commune visez-vous ?", "communes",
                           options=_COMMUNES_OFFICIELLES)
        if off not in communes:
            communes.append(off)

    prog = b.get("programme") or {}
    logements = prog.get("logements")
    sdp = prog.get("sdp_cible_m2")
    if logements is None and sdp is None:
        return _clarif("Quel programme visez-vous : combien de logements, ou quelle "
                       "surface de plancher (m²) ?", "programme")
    if sdp is None:
        # Règle déterministe CODE (jamais le LLM) — cf. SDP_PAR_LOGEMENT_M2.
        sdp = logements * SDP_PAR_LOGEMENT_M2

    contraintes = b.get("contraintes") or {}
    brief = {
        "communes": communes,
        "programme": {"logements": logements, "sdp_cible_m2": float(sdp)},
        "budget_max_eur": b.get("budget_max_eur"),
        "contraintes": {
            "exclure_ppr_rouge": (True if contraintes.get("exclure_ppr_rouge") is None
                                  else bool(contraintes["exclure_ppr_rouge"])),
            "exclure_abf": bool(contraintes.get("exclure_abf") or False),
            "zones": contraintes.get("zones"),
        },
        "surface_min_m2": b.get("surface_min_m2"),
        # M78 · 2c — critères que le moteur ne sait PAS appliquer (proximité spatiale, risque en
        # recherche, « déjà en vente ») : DITS au client, jamais ignorés en silence (§1e télémétrie).
        "criteres_non_appliques": [str(x)[:60] for x in (b.get("criteres_non_appliques") or [])][:5],
    }
    return Interpretation(brief=brief)


# ── Mission verifier_adresse ────────────────────────────────────────────────────────────
def interpreter_refs(texte: str, *, llm: Callable[..., str] | None = None,
                     db=None) -> Interpretation:
    """Références parcelles/adresses : DÉTERMINISTE d'abord, LLM seulement en secours."""
    texte = (texte or "").strip()
    if not texte:
        return _clarif("Collez une référence cadastrale (IDU 14 caractères) ou une adresse.",
                       "refs")

    refs = [{"type": "idu", "valeur": m} for m in dict.fromkeys(_IDU_RE.findall(texte))]
    if refs:
        return Interpretation(brief={"refs": refs})

    # Une ligne avec numéro + texte = candidate adresse (BAN tranchera au moteur).
    lignes = [ln.strip() for ln in re.split(r"[\n;]+", texte) if ln.strip()]
    adresses = [ln for ln in lignes if re.search(r"\d", ln) and len(ln) >= 8]
    if adresses:
        return Interpretation(brief={"refs": [{"type": "adresse", "valeur": a}
                                              for a in adresses]})

    # Secours LLM : extraction seulement, revalidée par les mêmes règles déterministes.
    sortie = _parse_json((llm or _llm_reel)(SYSTEM_EXTRACTION_REFS, {"texte": texte}, db=db))
    valides = []
    for r in sortie.get("refs", []):
        val = str(r.get("valeur", "")).strip()
        if val not in texte:                      # anti-invention : la réf doit être du texte
            continue
        if r.get("type") == "idu" and _IDU_RE.fullmatch(val):
            valides.append({"type": "idu", "valeur": val})
        elif r.get("type") == "adresse" and len(val) >= 8:
            valides.append({"type": "adresse", "valeur": val})
    if not valides:
        return _clarif("Je n'ai pas identifié de référence cadastrale ni d'adresse dans "
                       "votre message. Collez un IDU (14 caractères) ou une adresse précise.",
                       "refs")
    return Interpretation(brief={"refs": valides})
