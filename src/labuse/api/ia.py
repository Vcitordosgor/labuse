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
import re

from fastapi import APIRouter, Depends, Request
from jsonschema import ValidationError, validate
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..ai import core  # M11 socle 0 : client IA unique (clé, modèles, log, appel, validation, cache)
from .nl_aggregate import answer_aggregate, is_aggregate  # M11 B2 : questions agrégées (SQL sourcé)
from .nl_semantics import check_semantics  # M11 B1 : validation SÉMANTIQUE (schéma ≠ sens)
from .projet_schema import (
    CONTRAINTE_FLAG, FICHE_SCHEMA, TYPE_LABEL, clean_fiche, prune_to_schema, relocate_niveaux)

router = APIRouter(prefix="/ia", tags=["ia"])

# Alias vers le socle — plus de constantes IA dupliquées ici (source unique = core).
MODEL_NL = core.MODEL_FACTUAL
MODEL_SYNTH = core.MODEL_REASONING
PRICE = core.PRICE


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


# Diagnostic/clé/log : délégués au socle (source unique) — plus de duplication ici.
def _note_erreur(exc: Exception) -> None:
    core._note_error(exc)


def _note_succes() -> None:
    core._note_success()


def _has_key() -> bool:
    return core.has_key()


def _log(db: Session, kind: str, model: str, stub: bool, tin: int = 0, tout: int = 0) -> None:
    core._log_cost(db, kind, model, stub, tin, tout)


@router.get("/status")
def ia_status() -> dict:
    err = core.last_error()
    return {"provider": "anthropic" if _has_key() else "stub",
            "raison": (None if (_has_key() and not err)
                       else err if _has_key()
                       else "ANTHROPIC_API_KEY absente de l'environnement (.env racine non chargé ou clé non posée)"),
            "modeles": {"recherche": MODEL_NL, "synthese": MODEL_SYNTH},
            "doctrine": "l'IA ne calcule ni ne modifie aucun score ; aucun accès base"}


# ───────────────────────── 1. RECHERCHE NL → FILTRES ─────────────────────────

FILTER_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        # M5.1 : les TIERS v2 pilotent (« brûlante » = tier v2). `statuts` (matrice)
        # reste accepté — deprecated, plus jamais émis par le stub ni par le prompt.
        "tiers": {"type": "array", "items": {"enum": [
            "brulante", "chaude", "reserve_fonciere", "a_creuser", "ecartee"]}},
        "veille": {"type": "boolean"},
        "horsCopro": {"type": "boolean"},
        "statuts": {"type": "array", "items": {"enum": ["chaude", "a_surveiller", "a_creuser", "ecartee"]}},
        "scoreMin": {"type": ["integer", "null"], "minimum": 0, "maximum": 100},
        "surfaceMin": {"type": ["integer", "null"], "minimum": 0},
        "surfaceMax": {"type": ["integer", "null"], "minimum": 0},
        "sdpMin": {"type": ["integer", "null"], "minimum": 0},
        "evenement": {"type": "boolean"},
        "vueMer": {"type": "boolean"},
        # M11 B2 : propriétaire personne morale (DGFiP public — SCI/société/commune/HLM…) + zonage PLU par famille
        "personneMorale": {"type": "boolean"},
        "zonage": {"type": "array", "items": {"enum": ["U", "AU", "A", "N"]}},
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


#: UX V1 item 10 — verbes d'ACTION hors périmètre : demander de supprimer/modifier/écrire/
#: envoyer n'est JAMAIS une recherche. Le stub refusait mal (« supprime toutes les parcelles »
#: → « flag risques ») : refus SYSTÉMATIQUE, avant toute extraction de critères.
_VERBES_HORS_PERIMETRE = re.compile(
    r"\b(supprim\w*|efface\w*|d[ée]trui\w*|vide[rz]?\b\w*|modifi\w*|corrig\w*|change[rz]?\w*|"
    r"[ée]cri[stv]\w*|r[ée]dige\w*|ajoute\w*|cr[ée][ée]\w*|ins[éè]re\w*|"
    r"envoie\w*|envoy\w*|transmet\w*|transmett\w*|publie\w*|ignore\w*)\b", re.I)


def _stub_nl(t: str) -> tuple[dict | None, str]:
    """Stub local : règles lexicales déterministes. Renvoie (filtres, explication) ou (None, refus)."""
    low = t.lower()
    if _VERBES_HORS_PERIMETRE.search(low):
        return None, ("Hors périmètre : je ne peux ni modifier, ni supprimer, ni rédiger, ni "
                      "envoyer quoi que ce soit — je traduis seulement votre demande en critères "
                      "de recherche foncière (commune, statut, vue mer, surface, SDP, score). "
                      "Reformulez avec des critères ?")
    f: dict = {"tiers": [], "scoreMin": None, "surfaceMin": None, "surfaceMax": None,
               "sdpMin": None, "evenement": False, "vueMer": False, "veille": False,
               "flags": [], "commune": None, "personneMorale": False, "zonage": []}
    hits = []
    commune = _detect_commune(low)
    if commune:
        f["commune"] = commune
        hits.append(f"commune {commune}")
    # M5.1 : les mots du verdict pointent vers les TIERS v2 (« brûlante » = tier v2 ;
    # « à surveiller » n'existe plus — l'équivalent capacité est la réserve foncière)
    if re.search(r"br[ûu]lant", low):
        f["tiers"].append("brulante")
        hits.append("brûlantes v2")
    if re.search(r"chaude", low):
        f["tiers"].append("chaude")
        hits.append("chaudes v2")
    if re.search(r"r[ée]serve\s*fonci|surveill", low):
        f["tiers"].append("reserve_fonciere")
        hits.append("réserve foncière")
    if re.search(r"creuser", low):
        f["tiers"].append("a_creuser")
        hits.append("à creuser")
    if re.search(r"succession|h[ée]ritage|veille", low):
        f["veille"] = True
        hits.append("veille succession")
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
    # M11 B2 : propriétaire personne morale (DGFiP public) + zonage par famille
    if re.search(r"personne\s*morale|\bsci\b|soci[ée]t[ée]|\bsarl\b|\bsas[u]?\b|entreprise", low):
        f["personneMorale"] = True
        hits.append("propriétaire personne morale")
    for rx, fam in ((r"zone\s*u\b|constructible|urbaine?s?\b", "U"), (r"zone\s*au\b|à\s*urbaniser", "AU"),
                    (r"zone\s*a\b|agricole", "A"), (r"zone\s*n\b|naturelle?s?\b", "N")):
        if re.search(rx, low) and fam not in f["zonage"]:
            f["zonage"].append(fam)
            hits.append(f"zonage {fam}")
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
   « bodacc/liquidation/événement » → evenement ; « succession/héritage » → veille.
   « détenue/détenues par une personne morale / une société / une SCI / une entreprise » →
   personneMorale true (donnée DGFiP publique). « zone U / constructible / urbaine » → zonage ["U"] ;
   « zone à urbaniser / AU » → ["AU"] ; « zone agricole / A » → ["A"] ; « zone naturelle / N » → ["N"].
   Les VERDICTS sont les tiers du scoring v2 : « brûlantes » → tiers ["brulante"] ;
   « chaudes » → tiers ["chaude"] ; « réserve foncière / à surveiller » → tiers
   ["reserve_fonciere"] ; « à creuser » → tiers ["a_creuser"]. N'utilise JAMAIS le champ
   deprecated `statuts`.
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
    # M11 B2 : question AGRÉGÉE (compter/classer) → réponse CHIFFRÉE SQL-sourcée, ≠ filtre.
    # Le chiffre vient d'un COUNT/GROUP BY réel ; la couche 2 du socle rejette tout compte inventé.
    # Repli gracieux : answer_aggregate renvoie None (API indispo / question inexploitable) → flux filtres.
    if is_aggregate(body.text):
        agg = answer_aggregate(db, body.text)
        if agg is not None:
            _log(db, "search-aggregate", MODEL_NL, bool(agg.get("rejected")))
            return {"stub": False, **agg}
    if _has_key():
        res = core.complete(
            db, kind="search", model=MODEL_NL, max_tokens=600,   # temp 0 (défaut socle) — QA stable
            system=_NL_SYSTEM.format(schema=json.dumps(FILTER_SCHEMA, ensure_ascii=False)),
            history=[{"role": m.get("role", "user"), "content": str(m.get("content", ""))[:600]}
                     for m in (body.history or [])[-6:]],
            context=body.text)
        if res.degraded:   # clé invalide / API down → repli stub GRACIEUX (diagnostic dans core.last_error)
            prog = _stub_programme(body.text.lower())
            if prog:
                _log(db, "search", "stub-fallback", True)
                return {"stub": True, "programme": prog,
                        "explanation": "Programme détecté → formulaire Faisabilité pré-rempli (le moteur déterministe calcule)."}
            filters, explanation = _stub_nl(body.text)
            _log(db, "search", "stub-fallback", True)
            if filters is None:
                return {"stub": True, "out_of_scope": explanation}
            # UX V1 item 2 : plus de « (repli stub) » face client — le front affiche le badge
            # « mode mots-clés » depuis le drapeau stub, l'explication reste factuelle.
            filters, non_appliques = check_semantics(body.text, filters)  # B1 : sens > schéma
            return {"stub": True, "filters": filters, "explanation": explanation,
                    "criteres_non_appliques": non_appliques}
        raw = res.text.strip()
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
        # B1 : le schéma valide la CLÉ, pas le SENS. Un flag mistraduit (passoire→risques) est
        # retiré, un critère non supporté (personne morale) est signalé — jamais avalé, jamais faux.
        data, non_appliques = check_semantics(body.text, data)
        return {"stub": False, "filters": data,
                "explanation": "Filtres proposés par l'IA (validés par schéma).",
                "criteres_non_appliques": non_appliques}
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
    filters, non_appliques = check_semantics(body.text, filters)  # B1 : sens > schéma (stub local aussi)
    return {"stub": True, "filters": filters, "explanation": explanation,
            "criteres_non_appliques": non_appliques}


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
    res = core.complete(
        db, kind="entretien", model=MODEL_NL, max_tokens=900,
        system=_ENTRETIEN_SYSTEM.format(
            schema=json.dumps(ENTRETIEN_SCHEMA, ensure_ascii=False),
            types="/".join(TYPE_LABEL), contraintes="/".join(CONTRAINTE_FLAG)),
        history=[{"role": m.get("role", "user"), "content": str(m.get("content", ""))[:800]}
                 for m in (body.history or [])[-6:]],
        context=json.dumps({"fiche_connue": body.fiche, "message": body.text}, ensure_ascii=False))
    if res.degraded:
        _log(db, "entretien", "stub-fallback", True)
        return {"stub": True, "fallback": True,
                "message": "Le copilote est momentanément indisponible — basculons sur une "
                           "recherche directe (décrivez vos critères)."}
    raw = res.text.strip()
    if raw.startswith("```"):
        raw = raw.strip("`").removeprefix("json").strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {"stub": False, "fallback": True, "message": "réponse IA illisible — réessayez"}
    if isinstance(data.get("fiche"), dict):
        data["fiche"] = relocate_niveaux(data["fiche"])  # « R+3 » mal placé à la racine → ampleur.niveaux
        data["fiche"] = clean_fiche(data["fiche"])    # null/"" = « pas encore su » → drop (hors enum)
    # Robustesse (FIX post-validation) : un champ inattendu du modèle ne DOIT PAS faire tomber tout
    # le cadrage. On retire proprement ce qui est hors vocabulaire (et on le journalise) plutôt que
    # de renvoyer « réessayez » ; le garde-fou schéma reste en dernier recours pour les valeurs.
    data, champs_ignores = prune_to_schema(data, ENTRETIEN_SCHEMA)
    if champs_ignores:
        _log(db, "entretien-champs-ignores", MODEL_NL, False)
    try:
        validate(data, ENTRETIEN_SCHEMA)              # garde-fou : jamais de VALEUR hors vocabulaire
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
    # Via le socle : sérialisation SÛRE (default=str) → plus de 500 `Decimal not JSON serializable`
    # (la fiche contient des numeric DVF/RPLS/filosofi). timeout=30 pour la synthèse (sonnet).
    res = core.complete(db, kind=kind, system=system, context=payload,
                        model=MODEL_SYNTH, max_tokens=700, timeout=30.0)
    if res.degraded:
        raise RuntimeError(res.reason or "IA indisponible")
    return res.text


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
