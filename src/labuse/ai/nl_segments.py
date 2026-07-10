"""Recherche en langage naturel → filtres du MOTEUR DE SEGMENTS (mandat wave-adresses, Lot 6).

ARCHITECTURE STRICTE (mandat) :
 - le LLM reçoit UNIQUEMENT la question + le registry des filtres (clés, types, unités,
   énums, descriptions) — AUCUNE donnée de la base ne lui est envoyée ;
 - il retourne UN JSON de filtres ; chaque clé est validée contre le registry — tout
   champ inconnu est REJETÉ ; les valeurs repassent par le contrat du moteur
   (engine._validate_values). JAMAIS de SQL généré, jamais de texte libre exécuté ;
 - le résultat s'ouvre dans le query builder standard, filtres visibles et modifiables ;
 - hors périmètre → réponse honnête avec la liste des groupes de filtres disponibles.
"""
from __future__ import annotations

import json
import logging
import unicodedata

log = logging.getLogger("labuse.ia.nl_segments")

#: communes officielles (mêmes 24 que api/ia.py — la source du stub commune)
COMMUNES_974 = (
    "Les Avirons", "Bras-Panon", "Entre-Deux", "L'Étang-Salé", "Petite-Île",
    "La Plaine-des-Palmistes", "Le Port", "La Possession", "Saint-André", "Saint-Benoît",
    "Saint-Denis", "Saint-Joseph", "Saint-Leu", "Saint-Louis", "Saint-Paul",
    "Saint-Pierre", "Saint-Philippe", "Sainte-Marie", "Sainte-Rose", "Sainte-Suzanne",
    "Salazie", "Le Tampon", "Les Trois-Bassins", "Cilaos")


def registry_pour_prompt(avail: dict[str, dict]) -> list[dict]:
    """Le registry sérialisé pour le prompt système — descriptions incluses (c'est ce qui
    permet au modèle de mapper « villa avec grand jardin » → jardin_m2)."""
    from ..segments.registry import FILTERS
    out = []
    for f in FILTERS.values():
        a = avail.get(f.cle, {})
        out.append({"cle": f.cle, "libelle": f.libelle, "type": f.type,
                    "unite": f.unite, "groupe": f.groupe,
                    "enum_values": list(f.enum_values) or None,
                    "description": f.description,
                    "disponible": bool(a.get("disponible", True)),
                    **({"mandat": a["mandat"]} if a.get("mandat") else {})})
    return out


PROMPT_SYSTEME = """Tu traduis une demande de prospection foncière (île de La Réunion) en
filtres du moteur de segments LA BUSE. Réponds par UN SEUL objet JSON brut — pas de
markdown, pas de ```, pas de texte autour.

REGISTRY des filtres autorisés (les SEULES clés permises) :
{registry}

Communes officielles (les seules valeurs permises pour "communes") : {communes}

Formes de réponse :
1. Recherche traduisible → {{"filtres": [{{"cle": "...", ...}}], "explication": "une phrase"}}
   - filtre range  : {{"cle": "jardin_m2", "min": 300}} et/ou "max"
   - filtre bool   : {{"cle": "surelevation_possible", "value": true}}
   - filtre enum   : {{"cle": "type_bien", "values": ["Maison"]}}
   - commune(s) nommée(s) → {{"cle": "communes", "values": ["Nom Officiel"]}}
   Repères utiles : « récemment muté/vendu » → anciennete_mutation_mois max 12 (6 si
   « très récemment ») ; « grand jardin » → jardin_m2 min 300 ; « villa/maison » →
   type_bien ["Maison"] ; « sans piscine » → piscine value false ; « pente douce » →
   pente_moy_deg max 10 ; « vieux bâti/avant 1980 » → periode_construction max 1980.
   Un filtre marqué "disponible": false PEUT être utilisé (l'interface l'affiche grisé
   « disponible prochainement ») — ne l'invente jamais pour autant.
2. La demande ne correspond à AUCUN filtre du registry → {{"out_of_scope": "raison
   courte", "manque": ["ce qui manque au registry"]}}. Sois honnête, n'approxime JAMAIS
   un filtre qui n'existe pas par un autre. Sont notamment HORS registry aujourd'hui :
   l'état du propriétaire (redressement, liquidation, BODACC), la classe énergétique /
   DPE (« passoires thermiques » ≠ année de construction), une ESTIMATION de valeur
   (« combien vaut… »), et toute demande non foncière (météo, rédaction…).
Règles : n'invente JAMAIS une clé hors registry ; n'ajoute JAMAIS un filtre non demandé ;
température zéro ; unités converties (hectare → m² ×10000).
"""


def _sans_accents(t: str) -> str:
    return unicodedata.normalize("NFKD", t.lower()).encode("ascii", "ignore").decode()


def stub_nl_segments(question: str) -> dict:
    """Repli local DÉTERMINISTE (clé absente / API down) — règles lexicales sur le registry."""
    import re
    low = _sans_accents(question)
    filtres: list[dict] = []
    hits: list[str] = []
    for c in sorted(COMMUNES_974, key=len, reverse=True):
        base = _sans_accents(c)
        court = re.sub(r"^(le |la |les |l')", "", base)     # « au Tampon », « à l'Étang-Salé »
        if re.search(rf"\b{re.escape(base)}\b", low) or re.search(rf"\b{re.escape(court)}\b", low):
            filtres.append({"cle": "communes", "values": [c]})
            hits.append(c)
            break
    if re.search(r"jardin", low):
        m = re.search(r"(\d[\d\s]{1,8})\s*(?:m2|m²)", low)
        filtres.append({"cle": "jardin_m2", "min": int(m.group(1).replace(" ", "")) if m else 300})
        hits.append("jardin")
    if re.search(r"mut[ée]e?s?|vendu|emm[ée]nag", low):
        filtres.append({"cle": "anciennete_mutation_mois", "max": 12})
        hits.append("mutation récente")
    if re.search(r"\bvillas?\b|\bmaisons?\b", low):
        filtres.append({"cle": "type_bien", "values": ["Maison"]})
        hits.append("maison")
    if re.search(r"sans piscine", low):
        filtres.append({"cle": "piscine", "value": False})
        hits.append("sans piscine")
    elif re.search(r"piscine", low):
        filtres.append({"cle": "piscine", "value": True})
        hits.append("piscine")
    if re.search(r"sur[ée]l[ée]vation", low):
        filtres.append({"cle": "surelevation_possible", "value": True})
        hits.append("surélévation")
    if not filtres:
        return {"out_of_scope": "je n'ai pas reconnu de critère filtrable (repli local)",
                "stub": True}
    return {"filtres": filtres, "explication": "Repli local : " + ", ".join(hits),
            "stub": True}


def valider_filtres(data: dict, avail: dict[str, dict]) -> dict:
    """GARDE-FOU : ne laisse passer QUE des clés du registry et des valeurs au contrat
    du moteur. Tout champ inconnu est rejeté (listé), jamais exécuté (mandat §6.2)."""
    from ..segments import engine as seg
    from ..segments.registry import FILTERS
    valides: list[dict] = []
    rejetes: list[dict] = []
    for f in (data.get("filtres") or []):
        if not isinstance(f, dict) or not f.get("cle"):
            rejetes.append({"filtre": f, "raison": "forme invalide"})
            continue
        cle = str(f["cle"])
        fd = FILTERS.get(cle)
        if fd is None:
            rejetes.append({"filtre": f, "raison": f"clé hors registry : {cle}"})
            continue
        propre = {k: v for k, v in f.items() if k in ("cle", "min", "max", "value", "values")}
        if cle == "communes":       # valeurs bornées aux 24 communes officielles
            vals = [v for v in (propre.get("values") or []) if v in COMMUNES_974]
            if not vals:
                rejetes.append({"filtre": f, "raison": "commune hors liste officielle"})
                continue
            propre["values"] = vals
        try:
            seg._validate_values(fd, propre, cle)
        except seg.FiltreInvalide as exc:
            rejetes.append({"filtre": f, "raison": str(exc)})
            continue
        valides.append(propre)
    return {"filtres": valides, "rejetes": rejetes}


def groupes_disponibles(avail: dict[str, dict]) -> list[str]:
    """Pour la réponse honnête « je ne peux filtrer que sur : … »."""
    from ..segments.registry import FILTERS
    vus, ordre = set(), []
    for f in FILTERS.values():
        if avail.get(f.cle, {}).get("disponible") and f.groupe not in vus:
            vus.add(f.groupe)
            ordre.append(f.groupe)
    return ordre


def prompt_systeme(avail: dict[str, dict]) -> str:
    return PROMPT_SYSTEME.format(
        registry=json.dumps(registry_pour_prompt(avail), ensure_ascii=False),
        communes=json.dumps(list(COMMUNES_974), ensure_ascii=False))


def traduire(session, question: str, *, model: str, timeout_s: float = 20.0) -> dict:
    """Cœur partagé (endpoint /ia/segments-search + labuse nl-eval) : question → filtres
    VALIDÉS contre le registry, ou out_of_scope, ou repli stub (clé absente / API down).

    Retour : {"filtres", "rejetes", "explication", "stub"} | {"out_of_scope", "stub"}.
    """
    import os

    from ..segments.registry import compute_availability
    avail = compute_availability(session)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        data, stub = stub_nl_segments(question), True
    else:
        import anthropic
        try:
            client = anthropic.Anthropic(timeout=timeout_s, max_retries=2)
            msg = client.messages.create(
                model=model, max_tokens=700, temperature=0,
                system=prompt_systeme(avail),
                messages=[{"role": "user", "content": question[:600]}])
            raw = msg.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.strip("`").removeprefix("json").strip()
            data, stub = json.loads(raw), False
            data["_usage"] = (msg.usage.input_tokens, msg.usage.output_tokens)
        except Exception as exc:  # noqa: BLE001 — repli honnête, jamais un 500
            log.warning("segments-search : repli stub (%s)", type(exc).__name__)
            data, stub = stub_nl_segments(question), True
    if "out_of_scope" in data:
        return {"out_of_scope": str(data["out_of_scope"])[:240], "stub": stub,
                "groupes": groupes_disponibles(avail)}
    verdict = valider_filtres(data, avail)
    return {"filtres": verdict["filtres"], "rejetes": verdict["rejetes"],
            "explication": str(data.get("explication", ""))[:240], "stub": stub,
            "_usage": data.get("_usage")}
