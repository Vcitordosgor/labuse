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


#: dernier échec du provider réel (diagnostic C1) — None = dernier appel OK
_DERNIERE_ERREUR: str | None = None


def _note_erreur(exc: Exception) -> None:
    """Classe l'échec pour le bandeau : clé invalide vs erreur API — un diagnostic, pas une
    devinette. Remis à None au premier appel réussi."""
    global _DERNIERE_ERREUR
    name = type(exc).__name__
    if "Authentication" in name or "401" in str(exc):
        _DERNIERE_ERREUR = "clé invalide (authentification refusée par l'API Anthropic)"
    elif "Permission" in name or "403" in str(exc):
        _DERNIERE_ERREUR = "clé refusée (permissions insuffisantes)"
    else:
        _DERNIERE_ERREUR = f"erreur API Anthropic ({name})"


def _note_succes() -> None:
    global _DERNIERE_ERREUR
    _DERNIERE_ERREUR = None


def _has_key() -> bool:
    # config importe load_dotenv(racine/.env) — la clé est là quel que soit le lanceur (C1)
    from .. import config as _cfg  # noqa: F401  (garantit le chargement du .env racine)
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
            "raison": (None if (_has_key() and not _DERNIERE_ERREUR)
                       else _DERNIERE_ERREUR if _has_key()
                       else "ANTHROPIC_API_KEY absente de l'environnement (.env racine non chargé ou clé non posée)"),
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
        "communes": {"type": "array", "maxItems": 24, "items": {"enum": [
            "Les Avirons", "Bras-Panon", "Entre-Deux", "L'Étang-Salé", "Petite-Île",
            "La Plaine-des-Palmistes", "Le Port", "La Possession", "Saint-André", "Saint-Benoît",
            "Saint-Denis", "Saint-Joseph", "Saint-Leu", "Saint-Louis", "Saint-Paul",
            "Saint-Pierre", "Saint-Philippe", "Sainte-Marie", "Sainte-Rose", "Sainte-Suzanne",
            "Salazie", "Le Tampon", "Les Trois-Bassins", "Cilaos"]}},
        "commune": {"type": ["string", "null"], "enum": [
            "Les Avirons", "Bras-Panon", "Entre-Deux", "L'Étang-Salé", "Petite-Île",
            "La Plaine-des-Palmistes", "Le Port", "La Possession", "Saint-André", "Saint-Benoît",
            "Saint-Denis", "Saint-Joseph", "Saint-Leu", "Saint-Louis", "Saint-Paul",
            "Saint-Pierre", "Saint-Philippe", "Sainte-Marie", "Sainte-Rose", "Sainte-Suzanne",
            "Salazie", "Le Tampon", "Les Trois-Bassins", "Cilaos", None]},
    },
}

#: cadrage conversationnel (R2) : reformulation + AU PLUS 2 questions à chips — validé
CADRAGE_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["reformulation", "questions"],
    "properties": {
        "reformulation": {"type": "string", "maxLength": 240},
        "questions": {"type": "array", "minItems": 1, "maxItems": 2, "items": {
            "type": "object", "additionalProperties": False,
            "required": ["id", "texte", "chips"],
            "properties": {
                "id": {"enum": ["secteur", "ampleur", "contrainte"]},
                "texte": {"type": "string", "maxLength": 120},
                "chips": {"type": "array", "minItems": 2, "maxItems": 6, "items": {
                    "type": "object", "additionalProperties": False,
                    "required": ["label"],
                    "properties": {"label": {"type": "string", "maxLength": 40},
                                   "value": {"type": "string", "maxLength": 80}},
                }},
            },
        }},
    },
}

#: microrégions (secteurs du cadreur) → communes officielles
SECTEURS = {
    "Nord": ["Saint-Denis", "Sainte-Marie", "Sainte-Suzanne"],
    "Ouest": ["Le Port", "La Possession", "Saint-Paul", "Les Trois-Bassins", "Saint-Leu"],
    "Sud": ["L'Étang-Salé", "Les Avirons", "Saint-Louis", "Cilaos", "Saint-Pierre",
            "Petite-Île", "Le Tampon", "Entre-Deux", "Saint-Joseph", "Saint-Philippe"],
    "Est": ["Bras-Panon", "Salazie", "Saint-André", "Saint-Benoît",
            "La Plaine-des-Palmistes", "Sainte-Rose"],
}

#: variantes usuelles → nom officiel (le stub ET la projection du réel passent par là)
_COMMUNE_ALIASES: dict[str, str] = {
    "avirons": "Les Avirons", "bras-panon": "Bras-Panon", "bras panon": "Bras-Panon",
    "entre-deux": "Entre-Deux", "entre deux": "Entre-Deux",
    "etang-sale": "L'Étang-Salé", "etang sale": "L'Étang-Salé", "étang-salé": "L'Étang-Salé", "étang salé": "L'Étang-Salé",
    "petite-ile": "Petite-Île", "petite ile": "Petite-Île", "petite-île": "Petite-Île", "petite île": "Petite-Île",
    "plaine-des-palmistes": "La Plaine-des-Palmistes", "plaine des palmistes": "La Plaine-des-Palmistes",
    "le port": "Le Port", "possession": "La Possession",
    "saint-andre": "Saint-André", "saint andre": "Saint-André", "saint-andré": "Saint-André", "saint andré": "Saint-André",
    "saint-benoit": "Saint-Benoît", "saint benoit": "Saint-Benoît", "saint-benoît": "Saint-Benoît", "saint benoît": "Saint-Benoît",
    "saint-denis": "Saint-Denis", "saint denis": "Saint-Denis",
    "saint-joseph": "Saint-Joseph", "saint joseph": "Saint-Joseph",
    "saint-leu": "Saint-Leu", "saint leu": "Saint-Leu",
    "saint-louis": "Saint-Louis", "saint louis": "Saint-Louis",
    "saint-paul": "Saint-Paul", "saint paul": "Saint-Paul",
    "saint-pierre": "Saint-Pierre", "saint pierre": "Saint-Pierre",
    "saint-philippe": "Saint-Philippe", "saint philippe": "Saint-Philippe",
    "sainte-marie": "Sainte-Marie", "sainte marie": "Sainte-Marie",
    "sainte-rose": "Sainte-Rose", "sainte rose": "Sainte-Rose",
    "sainte-suzanne": "Sainte-Suzanne", "sainte suzanne": "Sainte-Suzanne",
    "salazie": "Salazie", "tampon": "Le Tampon",
    "trois-bassins": "Les Trois-Bassins", "trois bassins": "Les Trois-Bassins",
    "cilaos": "Cilaos",
}


def _detect_commune(low: str) -> str | None:
    """La commune extraite du texte (l'île entière est couverte — plus de refus « hors périmètre »
    pour « les chaudes de Saint-Pierre »). Les noms longs d'abord (saint-pierre avant pierre)."""
    for alias in sorted(_COMMUNE_ALIASES, key=len, reverse=True):
        if alias in low:
            return _COMMUNE_ALIASES[alias]
    return None


class SearchIn(BaseModel):
    text: str
    #: historique COURT du cadrage (R2, ≤6 tours) — transmis tel quel au modèle, jamais à la base
    history: list[dict] = []


def _stub_programme(low: str) -> dict | None:
    """Détection « programme immobilier » → préremplissage du formulaire M22 (sens 2)."""
    if not re.search(r"immeuble|b[âa]timent|r\s*\+\s*\d|programme|r[ée]sidence|logements? pour", low):
        return None
    prog: dict = {}
    m = re.search(r"(\d+)\s*(?:immeubles?|b[âa]timents?)", low)
    if m:
        prog["batiments"] = int(m.group(1))
    m = re.search(r"r\s*\+\s*(\d+)", low)
    if m:
        prog["niveaux"] = int(m.group(1))
    m = re.search(r"(\d+)\s*(?:logements?|unit[ée]s?|studios?)", low)
    if m:
        prog["logements_par_batiment"] = max(1, int(m.group(1)) // max(1, prog.get("batiments", 1)))
    if re.search(r"[ée]tudiant", low):
        prog["type"] = "etudiant"
        prog.setdefault("surface_unite_m2", 25)
    if re.search(r"bureau", low):
        prog["type"] = "bureaux"
    prog["parking"] = not re.search(r"sans parking", low)
    return prog if len(prog) > 1 else None


def _stub_nl(t: str) -> tuple[dict | None, str]:
    """Stub local : règles lexicales déterministes. Renvoie (filtres, explication) ou (None, refus)."""
    low = t.lower()
    f: dict = {"statuts": [], "scoreMin": None, "surfaceMin": None, "surfaceMax": None,
               "sdpMin": None, "evenement": False, "vueMer": False, "flags": [], "commune": None}
    hits = []
    commune = _detect_commune(low)
    if commune:
        f["commune"] = commune
        hits.append(f"commune {commune}")
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
                      "(commune, statut, vue mer, surface, SDP, score, événement, flags). Reformulez ?")
    return f, "Filtres appliqués : " + ", ".join(hits) + "."


_NL_SYSTEM = """Tu traduis une demande de prospection foncière (La Réunion) en JSON. Réponds par
UN SEUL objet JSON brut — pas de markdown, pas de ```, pas de texte autour. Trois formes possibles :
1. Recherche filtrable → objet conforme à ce schéma (champs non mentionnés = valeur neutre [], null, false) :
{schema}
   Correspondances : « vue mer/bord de mer » → vueMer ; « usine/industriel » → flags icpe ;
   « pollué » → flags sol_pollue ; « inondation/risque » → flags risques ; « monument » → flags abf ;
   « bodacc/liquidation/événement » → evenement ; les statuts sont chaude/a_surveiller/a_creuser/ecartee.
   ⚠ Les FLAGS SONT FILTRABLES : « proximité d'un monument historique / bâtiment de France »
   = {{"flags": ["abf"]}} (périmètre ABF) ; « près d'une usine » = {{"flags": ["icpe"]}} ;
   « pollué » = sol_pollue ; « inondable » = risques. Ne réponds JAMAIS out_of_scope pour ces cas.
   Une commune de La Réunion nommée dans la demande → commune (nom OFFICIEL de l'enum du schéma,
   ex. « au Tampon » → "Le Tampon", « à l'Étang-Salé » → "L'Étang-Salé"). Les 24 communes de
   l'île sont TOUTES couvertes par le radar — ce n'est jamais hors périmètre.
2. Programme immobilier (« N immeubles R+n, X logements, parking ») →
   {{"programme": {{"type": "logements|etudiant|bureaux", "batiments": n, "niveaux": n,
     "logements_par_batiment": n, "parking": true|false}}}}
3. Hors périmètre (météo, rédaction, géographie non filtrable, ou TOUTE demande de MODIFIER un
   score — les scores sont déterministes, tu ne les changes jamais) →
   {{"out_of_scope": "raison courte et polie"}}
4. CADRAGE — RÉSERVÉ aux demandes de PROJET sans AUCUN critère filtrable. Si la demande
   contient NE SERAIT-CE QU'UN critère traduisible (surface, SDP, score, statut, vue mer,
   événement, pollution/usine/monument/risque → flags, commune ou secteur) → forme 1 DIRECTE,
   même sans commune. Exemple de cadrage légitime : « un terrain pour du logement étudiant » →
   {{"cadrage": {{"reformulation": "UNE phrase : ce que tu as compris",
     "questions": [{{"id": "secteur", "texte": "…", "chips": [{{"label": "Nord"}}, {{"label": "Ouest"}},
       {{"label": "Sud"}}, {{"label": "Est"}}, {{"label": "Toute l'île"}}]}},
      {{"id": "ampleur", "texte": "…", "chips": [{{"label": "…", "value": "sdpMin:300"}}, …]}}]}}}}
   AU MAXIMUM 2 questions (secteur, ampleur, ou contrainte clé), chips courtes. Le champ
   value d'un chip d'ampleur/contrainte = fragment "clé:valeur" du schéma de filtres
   (ex. "sdpMin:800", "surfaceMin:1000"). Un secteur choisi se traduira par "communes"
   (Nord={nord} ; Ouest={ouest} ; Sud={sud} ; Est={est} ; Toute l'île = communes absent).
   ⚠ Une demande PRÉCISE (commune nommée, statut, critère chiffré) → JAMAIS de cadrage,
   filtres DIRECTS (forme 1) : un copilote qui interroge pour rien est pénible.
   Si l'historique contient déjà tes questions et les réponses de l'utilisateur → réponds
   TOUJOURS en forme 1 (filtres consolidés : "communes" du secteur choisi, valeurs des chips
   d'ampleur/contrainte) — JAMAIS en programme ni en nouveau cadrage après un cadrage.
Sois strict : n'invente JAMAIS un filtre non demandé. Le champ "type" n'existe QUE dans
"programme" — jamais dans un objet de filtres."""


@router.post("/search")
def ia_search(body: SearchIn, db: Session = Depends(get_db)) -> dict:
    if _has_key():
        import anthropic
        client = anthropic.Anthropic(timeout=20.0, max_retries=2)
        try:
            msg = client.messages.create(
                model=MODEL_NL, max_tokens=600, temperature=0,   # comportement STABLE (QA réelle)
                system=_NL_SYSTEM.format(
                    schema=json.dumps(FILTER_SCHEMA, ensure_ascii=False),
                    nord=", ".join(SECTEURS["Nord"]), ouest=", ".join(SECTEURS["Ouest"]),
                    sud=", ".join(SECTEURS["Sud"]), est=", ".join(SECTEURS["Est"])),
                messages=([{"role": m.get("role", "user"), "content": str(m.get("content", ""))[:600]}
                           for m in (body.history or [])[-6:]]
                          + [{"role": "user", "content": body.text}]))
        except Exception as exc:   # clé invalide / API down → diagnostic + repli stub GRACIEUX
            _note_erreur(exc)
            prog = _stub_programme(body.text.lower())
            if prog:
                _log(db, "search", "stub-fallback", True)
                return {"stub": True, "programme": prog, "explanation": "Programme détecté (repli stub)."}
            filters, explanation = _stub_nl(body.text)
            _log(db, "search", "stub-fallback", True)
            if filters is None:
                return {"stub": True, "out_of_scope": explanation}
            return {"stub": True, "filters": filters, "explanation": explanation + " (repli stub)"}
        _note_succes()
        raw = msg.content[0].text.strip()
        _log(db, "search", MODEL_NL, False, msg.usage.input_tokens, msg.usage.output_tokens)
        if raw.startswith("```"):
            raw = raw.strip("`").removeprefix("json").strip()   # le réel enrobe parfois — le stub ne l'apprend pas
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return {"stub": False, "out_of_scope": "réponse IA illisible — réessayez"}
        if "out_of_scope" in data:
            return {"stub": False, "out_of_scope": data["out_of_scope"]}
        if "programme" in data:
            return {"stub": False, "programme": data["programme"],
                    "explanation": "Programme détecté → formulaire Faisabilité pré-rempli (le moteur déterministe calcule)."}
        if "cadrage" in data:
            try:
                validate(data["cadrage"], CADRAGE_SCHEMA)   # le garde-fou : jamais de question libre
            except ValidationError as exc:
                return {"stub": False, "out_of_scope": f"cadrage non conforme ({exc.message[:60]}) — réessayez"}
            return {"stub": False, "cadrage": data["cadrage"]}
        # dégradation gracieuse : on PROJETTE sur les clés du schéma (une clé parasite ne doit pas
        # faire échouer une demande par ailleurs valide) — le schéma reste le garde-fou final
        data = {k: v for k, v in data.items() if k in FILTER_SCHEMA["properties"]}
        if isinstance(data.get("commune"), str):   # variante non officielle → normalisée, sinon l'enum tranche
            data["commune"] = _COMMUNE_ALIASES.get(data["commune"].lower().strip(), data["commune"])
        try:
            validate(data, FILTER_SCHEMA)   # le schéma est le GARDE-FOU : jamais de filtre inventé
        except ValidationError as exc:
            return {"stub": False, "out_of_scope": f"filtre non conforme ({exc.message[:60]}) — réessayez"}
        return {"stub": False, "filters": data, "explanation": "Filtres proposés par l'IA (validés par schéma)."}
    prog = _stub_programme(body.text.lower())
    if prog:
        _log(db, "search", "stub-local", True)
        return {"stub": True, "programme": prog,
                "explanation": "Programme détecté → formulaire Faisabilité pré-rempli (le moteur déterministe calcule)."}
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
                 "fourni (fiche tracée). INTERDIT d'inventer un fait absent du JSON. "
                 "FORMAT : texte brut UNIQUEMENT — aucun markdown, aucun tableau, aucun titre #. "
                 "150 mots MAXIMUM, 3 paragraphes : (1) verdict en une phrase, (2) points forts et "
                 "vigilances chiffrés, (3) inconnues à lever. Vocabulaire promoteur : charge "
                 "foncière, SDP, prospect, R+n. Le texte s'affiche dans un panneau étroit.")


def _real_text(db: Session, kind: str, system: str, payload: dict) -> str:
    import anthropic
    client = anthropic.Anthropic(timeout=30.0, max_retries=2)
    try:
        msg = client.messages.create(model=MODEL_SYNTH, max_tokens=700, system=system,
                                     messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}])
    except Exception as exc:
        _note_erreur(exc)
        raise
    _note_succes()
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
                 "INTERDIT d'inventer. FORMAT : texte brut sans markdown, 150 mots max — les 3 "
                 "signaux qui pèsent le plus sur Q, puis sur A, chacun en une ligne « ±N — "
                 "explication ». Rappelle en une phrase que le score est déterministe et tracé.")
        return {"stub": False, "texte": _real_text(db, "pourquoi", sys_p, f),
                "mention": "Explication générée — le score reste 100 % déterministe."}
    _log(db, "pourquoi", "stub-local", True)
    return {"stub": True, "texte": _stub_pourquoi(f),
            "mention": "Explication générée (stub local) — le score reste 100 % déterministe."}
