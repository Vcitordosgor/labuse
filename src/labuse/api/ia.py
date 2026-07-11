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

from fastapi import APIRouter, Depends, Request
from jsonschema import ValidationError, validate
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from .projet_schema import CONTRAINTE_FLAG, FICHE_SCHEMA, TYPE_LABEL, clean_fiche

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
CREATE TABLE IF NOT EXISTS nl_query_log (
  id serial PRIMARY KEY, ts timestamptz DEFAULT now(),
  question text, statut varchar(16),          -- 'traduit' | 'out_of_scope' | 'erreur'
  reponse jsonb
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
        # contraintes RÉDHIBITOIRES (copilote-projet) : écarter les parcelles portant le flag
        "flagsExclus": {"type": "array", "items": {"enum": ["sol_pollue", "abf", "icpe", "risques", "prescription_plu"]}},
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
4. INTENTION PROJET — la demande décrit une OPÉRATION à monter (« je veux monter… »,
   « je cherche un terrain pour… », « une résidence de X logements ») SANS être une simple
   recherche filtrable → {{"projet_intent": true, "reformulation": "UNE phrase : ce que tu as compris"}}.
   Le front ouvrira l'ENTRETIEN de cadrage (fiche projet). ⚠ Une demande PRÉCISE et filtrable
   (commune nommée + statut, critère chiffré, « les chaudes de X ») → JAMAIS projet_intent :
   forme 1 DIRECTE (un copilote qui interroge pour rien est pénible). Dans le doute entre une
   recherche et un projet, si un critère filtrable est présent → forme 1.
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
                    schema=json.dumps(FILTER_SCHEMA, ensure_ascii=False)),
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
        if data.get("projet_intent"):     # projet à cadrer → le front ouvre l'entretien
            return {"stub": False, "projet_intent": True,
                    "reformulation": str(data.get("reformulation", ""))[:240]}
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


# ─────────────── 1ter. RECHERCHE NL → MOTEUR DE SEGMENTS (mandat wave-adresses, Lot 6) ───────────

class SegmentsSearchIn(BaseModel):
    text: str


def _nl_log(db: Session, question: str, statut: str, reponse: dict) -> None:
    """Log ANONYMISÉ (RGPD : aucun identifiant utilisateur) — la roadmap des filtres
    manquants se lit dans les out_of_scope."""
    db.execute(text("INSERT INTO nl_query_log (question, statut, reponse) "
                    "VALUES (:q, :s, :r)"),
               {"q": question[:500], "s": statut,
                "r": json.dumps(reponse, ensure_ascii=False, default=str)})


@router.post("/segments-search")
def ia_segments_search(body: SegmentsSearchIn, request: Request,
                       db: Session = Depends(get_db)) -> dict:
    """Question libre → JSON de filtres du REGISTRY des segments, validé — jamais de SQL.

    Le front ouvre le query builder avec les filtres visibles/modifiables (pédagogie).
    Quota : LABUSE_NL_QUOTA_JOUR (30/jour/sujet). Hors périmètre → réponse honnête.
    """
    from .. import plans
    from ..ai.nl_segments import traduire
    from ..config import get_settings
    from .protection import _aujourdhui, compteur, sujet_de
    s_cfg = get_settings()
    sujet = sujet_de(request)
    if compteur(db, sujet, "nl") >= max(1, s_cfg.nl_quota_jour):
        return {"out_of_scope": f"Quota de recherches en langage naturel atteint "
                                f"({s_cfg.nl_quota_jour}/jour) — réessayez demain, ou "
                                "utilisez directement le query builder.",
                "quota": True}
    # jour = _aujourdhui() (heure LOCALE python) partout — jamais CURRENT_DATE : autour
    # de minuit, le fuseau du serveur Postgres décale d'un jour et fausse les quotas.
    db.execute(text(
        "INSERT INTO usage_compteurs (jour, sujet, kind, n) "
        "VALUES (:j, :s, 'nl', 1) "
        "ON CONFLICT (jour, sujet, kind) DO UPDATE SET n = usage_compteurs.n + 1"),
        {"j": _aujourdhui(), "s": sujet})

    res = traduire(db, body.text, model=MODEL_NL)
    usage = res.pop("_usage", None) or (0, 0)
    _log(db, "segments-search", MODEL_NL if not res["stub"] else "stub-local",
         res["stub"], usage[0], usage[1])
    if not res["stub"]:
        _note_succes()

    if "out_of_scope" in res:
        rep = {"stub": res["stub"], "out_of_scope": res["out_of_scope"],
               "groupes_disponibles": res["groupes"],
               "message": "Je ne peux filtrer que sur : " + ", ".join(res["groupes"]) + "."}
        _nl_log(db, body.text, "out_of_scope", rep)
        return rep

    # Gating par plan (stub Phase 0 — même mécanique que les presets : grisé + upgrade)
    filtres, gates = res["filtres"], []
    if plans.plan_courant() != plans.INTEGRAL:
        gates = [f for f in filtres if f["cle"] in plans.FILTRES_INTEGRAL]
        filtres = [f for f in filtres if f["cle"] not in plans.FILTRES_INTEGRAL]
    rep = {"stub": res["stub"], "filtres": filtres,
           "filtres_rejetes": res["rejetes"],
           "filtres_gates": [{**f, **plans.refus("recherche_nl")} for f in gates],
           "explication": res["explication"]
           or "Filtres proposés — vérifiez et ajustez dans le query builder."}
    _nl_log(db, body.text, "traduit", rep)
    return rep


# ───────────────────── 1bis. ENTRETIEN DE CADRAGE PROJET (copilote-projet) ─────────────────────

#: l'entretien construit une FICHE par touches successives. Chaque tour renvoie la fiche
#: MERGÉE (validée FICHE_SCHEMA — vocabulaire fermé), une reformulation, les questions pour
#: ce qui MANQUE (≤6, chacune skippable avec un défaut honnête affiché) et l'état `pret`.
#: P1.2 (revue Vic n°3) : plafond relevé (4→6) + dimension `gabarit` (R+n → M22 niveaux)
#: pour vraiment affiner — chaque question reste facultative, zéro question si tout est su.
ENTRETIEN_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["reformulation", "fiche", "questions", "pret"],
    "properties": {
        "reformulation": {"type": "string", "maxLength": 240},
        "fiche": FICHE_SCHEMA,
        "nom": {"type": "string", "maxLength": 160},
        "pret": {"type": "boolean"},
        "questions": {"type": "array", "maxItems": 6, "items": {
            "type": "object", "additionalProperties": False,
            "required": ["id", "texte", "chips"],
            "properties": {
                "id": {"enum": ["perimetre", "type", "ampleur", "gabarit", "contrainte", "budget"]},
                "texte": {"type": "string", "maxLength": 120},
                # `dimension` déclenche les REPÈRES sourcés côté front (chiffres SQL sous les chips)
                "dimension": {"enum": ["secteur", "commune"]},
                "defaut": {"type": "string", "maxLength": 80},   # défaut honnête au SKIP
                "chips": {"type": "array", "minItems": 2, "maxItems": 6, "items": {
                    "type": "object", "additionalProperties": False, "required": ["label"],
                    "properties": {"label": {"type": "string", "maxLength": 40},
                                   "value": {"type": "string", "maxLength": 80}},
                }},
            },
        }},
    },
}

#: lexique d'OPINION MARCHÉ non chiffrée — INTERDIT (doctrine : arbitrages sourcés ou tus).
#: le garde-fou neutralise toute réponse IA qui en contient dans un champ de texte libre.
_MARCHE_OPINION = re.compile(
    r"plus porteur|meilleur potentiel|plus rentable|march[ée] porteur|forte demande|"
    r"tr[èe]s demand[ée]|bon investissement|plus attractif|meilleur choix|meilleure affaire|"
    r"je (?:te |vous )?recommande|conseill|id[ée]al pour investir|plus int[ée]ressant",
    re.I)


def contient_opinion_marche(*textes: str) -> bool:
    """True si un texte porte une opinion de marché non chiffrée (à bannir). Pur, testable."""
    return any(t and _MARCHE_OPINION.search(t) for t in textes)


_ENTRETIEN_SYSTEM = """Tu MÈNES un entretien de cadrage pour un promoteur foncier (La Réunion).
Ton rôle : l'aider à FORMALISER son opération en remplissant une FICHE structurée. Réponds
par UN SEUL objet JSON brut (pas de markdown, pas de ```), conforme EXACTEMENT à ce schéma :
{schema}

RÈGLES ABSOLUES (frontière IA/moteur) :
- Tu ne CALCULES ni n'ESTIMES JAMAIS un chiffre (surface, SDP, prix, marge, capacité, prix au
  m², rendement). Le moteur déterministe s'en charge. Tu ne fais que RECUEILLIR ce que le
  promoteur dit (ex. « 40 logements » va dans ampleur.logements — c'est SA donnée, pas un calcul).
- INTERDIT d'émettre une opinion de marché non chiffrée : jamais « plus porteur », « meilleur
  potentiel », « plus rentable », « je recommande », « idéal pour investir ». Reste NEUTRE et
  factuel. Les chiffres d'aide au choix sont servis séparément par la base (tu ne les inventes pas).

DÉROULÉ :
1. `fiche` = la fiche MERGÉE : reprends tout ce qui était déjà connu (fiche fournie) + ce que
   le dernier message apporte. Vocabulaire FERMÉ : type_programme ∈ {types} ; perimetre.mode ∈
   ile|secteur|communes (secteur ∈ Nord/Ouest/Sud/Est) ; contraintes ∈ {contraintes}.
   « logements étudiants » → type_programme "etudiant". « 40 logements » → ampleur.logements 40.
   « R+3 / immeuble R+3 / sur 3 niveaux » → ampleur.niveaux 3 (le n de R+n ; « R+2 »→2).
   « dans l'Ouest » → perimetre secteur "Ouest". « éviter les zones inondables/PPR » →
   contraintes ["eviter_ppr"]. Une commune nommée → perimetre mode "communes",
   communes:["Nom Officiel"]. Budget « 800 k€ » → budget_foncier_eur 800000.
2. `reformulation` = UNE phrase neutre de ce que tu as compris.
3. `questions` = UNIQUEMENT pour ce qui MANQUE encore, AU MAXIMUM 6, dans cet ordre de priorité.
   Pose-en assez pour VRAIMENT cadrer l'opération (une question par dimension manquante), MAIS
   n'invente rien : si une dimension est déjà connue ou déductible, ne la redemande pas.
     - perimetre (id "perimetre", dimension "secteur", chips Nord/Ouest/Sud/Est/Toute l'île)
     - type (id "type", chips Logements/Logement étudiant/Bureaux/Autre)
     - ampleur (id "ampleur", chips d'ordres de grandeur de logements, ex. ~20/~40/~80/~150)
     - gabarit (id "gabarit" — la hauteur/gabarit souhaité, chips R+2/R+3/R+4/R+6)
     - contrainte (id "contrainte", chips des contraintes rédhibitoires)
     - budget (id "budget")
   type + ampleur sont DEUX questions distinctes (ne les fusionne pas). Ne RE-DEMANDE JAMAIS une
   dimension déjà présente dans la fiche. Chaque question porte un `defaut` honnête (ce que tu
   retiens si l'utilisateur passe, ex. "→ toute l'île", "→ R+2 par défaut", "→ sans contrainte
   rédhibitoire"). Chips courtes (2 à 6). Si plus rien ne manque → questions = [].
4. `pret` = true dès que le PÉRIMÈTRE est déterminé — un secteur/des communes cités, OU « toute
   l'île » par défaut quand l'utilisateur reste vague ou passe la question. Le type/l'ampleur/le
   gabarit raffinent le programme mais NE BLOQUENT PAS le lancement (les questions restent proposées).
5. `nom` = un nom de projet court et neutre (ex. "Résidence étudiante Ouest").
Si le dernier message dit « je ne sais pas / passer » sur une dimension → applique le défaut
honnête dans la fiche (ex. perimetre.mode "ile", ampleur.niveaux 2) et n'y reviens pas."""


class EntretienIn(BaseModel):
    text: str
    fiche: dict = {}                       # la fiche accumulée (front-held) — vérité en cours
    history: list[dict] = []               # tours précédents (≤6), transmis tel quel


def _neutralise_opinion(data: dict, db: Session) -> dict:
    """Garde-fou doctrine : si l'IA a glissé une opinion de marché non chiffrée dans un champ
    de texte libre, on la NEUTRALISE (reformulation générique, chips/questions purgées du
    libellé fautif) et on flague `doctrine_neutralise`. Les arbitrages restent sourcés-ou-tus."""
    libres = [data.get("reformulation", "")]
    for q in data.get("questions", []):
        libres.append(q.get("texte", ""))
        libres += [c.get("label", "") for c in q.get("chips", [])]
    if not contient_opinion_marche(*libres):
        return data
    _log(db, "entretien-neutralise", MODEL_NL, False)
    data["reformulation"] = "Voici ce que j'ai compris de votre projet."
    data["doctrine_neutralise"] = True
    # purge des questions/chips portant l'opinion (on garde la structure, on retire le fautif)
    for q in data.get("questions", []):
        if contient_opinion_marche(q.get("texte", "")):
            q["texte"] = "Précisez votre choix :"
        q["chips"] = [c for c in q.get("chips", []) if not contient_opinion_marche(c.get("label", ""))]
    data["questions"] = [q for q in data.get("questions", []) if len(q.get("chips", [])) >= 2]
    return data


@router.post("/entretien")
def ia_entretien(body: EntretienIn, db: Session = Depends(get_db)) -> dict:
    """L'entretien de cadrage projet — RÉEL uniquement (doctrine : pas d'entretien simulé).
    Sans clé API, on renvoie `fallback` : le front bascule sur la recherche directe."""
    if not _has_key():
        _log(db, "entretien", "stub-local", True)
        return {"stub": True, "fallback": True,
                "message": "L'entretien de cadrage a besoin du copilote IA (indisponible ici). "
                           "Décrivez vos critères pour une recherche directe."}
    import anthropic
    client = anthropic.Anthropic(timeout=20.0, max_retries=2)
    try:
        msg = client.messages.create(
            model=MODEL_NL, max_tokens=900, temperature=0,
            system=_ENTRETIEN_SYSTEM.format(
                schema=json.dumps(ENTRETIEN_SCHEMA, ensure_ascii=False),
                types="/".join(TYPE_LABEL), contraintes="/".join(CONTRAINTE_FLAG)),
            messages=([{"role": m.get("role", "user"), "content": str(m.get("content", ""))[:800]}
                       for m in (body.history or [])[-6:]]
                      + [{"role": "user", "content": json.dumps(
                          {"fiche_connue": body.fiche, "message": body.text}, ensure_ascii=False)}]))
    except Exception as exc:
        _note_erreur(exc)
        _log(db, "entretien", "stub-fallback", True)
        return {"stub": True, "fallback": True,
                "message": "Le copilote est momentanément indisponible — basculons sur une "
                           "recherche directe (décrivez vos critères)."}
    _note_succes()
    raw = msg.content[0].text.strip()
    _log(db, "entretien", MODEL_NL, False, msg.usage.input_tokens, msg.usage.output_tokens)
    if raw.startswith("```"):
        raw = raw.strip("`").removeprefix("json").strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {"stub": False, "fallback": True, "message": "réponse IA illisible — réessayez"}
    if isinstance(data.get("fiche"), dict):
        data["fiche"] = clean_fiche(data["fiche"])    # null/"" = « pas encore su » → drop (hors enum)
    try:
        validate(data, ENTRETIEN_SCHEMA)              # garde-fou : jamais de champ hors vocabulaire
    except ValidationError as exc:
        return {"stub": False, "fallback": True,
                "message": f"cadrage non conforme ({exc.message[:70]}) — réessayez"}
    data = _neutralise_opinion(data, db)              # garde-fou : aucune opinion marché non chiffrée
    data["stub"] = False
    return data


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
