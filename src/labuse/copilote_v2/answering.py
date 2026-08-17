"""M78 · 1b/1c — COUCHE DE RÉPONSE. Le client écrit, LABUSE instruit.

Pipeline : routeur (intention) → aiguillage. Pour une QUESTION : le modèle CHOISIT un outil + des
paramètres typés (jamais du SQL), le serveur exécute, le modèle FORMULE depuis le résultat en citant
l'outil. Les cinq issues de la doctrine (RAPPORT_M78) sont appliquées ici. Refus = TEMPLATES
déterministes (le ton d'un refus se gagne : on ne l'improvise pas). Sonnet partout.

Verrou anti-invention : tout nombre de la réponse formulée doit exister dans le résultat d'outil ;
sinon la prose est rejetée et remplacée par un gabarit sourcé (jamais l'affirmation douteuse).
"""
from __future__ import annotations

import json
import re
from typing import Any

from sqlalchemy.orm import Session

from ..ai import core
from . import telemetrie
from .outils import OUTILS
from .router import classify

# ───────────────────────── Réponses fixes (issues 5, 3, 4) ─────────────────────────
HORS_SUJET = ("Je suis le copilote foncier de LABUSE — je réponds sur l'immobilier et le foncier de "
              "La Réunion.")
ERREUR_INFRA = ("Je ne peux pas instruire votre demande pour le moment (service d'analyse "
                "indisponible). Réessayez dans un instant.")

REFUS_PP = ("L'identité des propriétaires personnes physiques n'est pas une donnée ouverte en France. "
            "Elle s'obtient par une demande au service de la publicité foncière (SPF) — je peux vous "
            "préparer le courrier.")
REFUS_PROJECTION = ("LABUSE ne projette pas de valeur future. Je peux vous donner le marché CONSTATÉ "
                    "— médiane, tendance sur 12 mois, volume de ventes.")

# ───────────────────────── Catalogue des outils QUESTION (pour la sélection) ─────────────────────────
CATALOGUE = [
    {"nom": "compter_parcelles", "desc": "Compter des parcelles d'une commune selon des critères de la "
     "facette : surface (min/max en m²), tier (brûlante/chaude/opportunités), détention par une "
     "personne morale, événement rouge, signaux de vie (procédure judiciaire/BODACC, friche, cession, "
     "permis actif/caduc, défiscalisation, terrain nu de société), adresse absente, copropriété, "
     "renouvellement urbain, zonage PLU (U/AU/A/N).",
     "params": {"commune": "str", "surface_min": "int m²", "surface_max": "int m²",
                "tier": "brulante|chaude|opportunites", "personne_morale": "bool",
                "evenement": "bool (événement rouge)",
                "signaux": "csv parmi procedure,friche,cession,permis_actif,permis_caduc,defisc,nu_pm,assemblage",
                "adresse_absente": "bool (sans adresse)", "copro": "avec|sans (copropriété)",
                "defisc": "bool (défiscalisation)", "renouvellement": "bool (renouvellement urbain)",
                "zonage": "csv parmi U,AU,A,N (famille de zone PLU)"}},
    {"nom": "parcelles_par_entreprise", "desc": "Parcelles détenues par une personne morale (nom OU SIREN).",
     "params": {"q": "nom ou SIREN"}},
    {"nom": "fiche_parcelle", "desc": "Données d'UNE parcelle précise identifiée par son IDU (14 car.) : "
     "commune, surface, zone, verdict.", "params": {"idu": "str 14 car."}},
    {"nom": "stats_commune", "desc": "Contexte d'une commune : taux de logement social (SRU), statut SRU, "
     "nombre de logements, part de propriétaires.", "params": {"commune": "str"}},
    {"nom": "delais_instruction", "desc": "Délai médian d'instruction ET nombre de permis accordés "
     "d'une commune (Sitadel).", "params": {"commune": "str"}},
    {"nom": "marche", "desc": "Marché immobilier d'une commune : prix ancien, terrain nu, neuf, tendance, "
     "loyer.", "params": {"commune": "str"}},
    {"nom": "recherche_web", "desc": "DERNIER RECOURS (M78-ter) — un fait PUBLIC de La Réunion sur le "
     "foncier/immobilier/urbanisme/collectivités et leurs acteurs (élu, organigramme d'une collectivité, "
     "actualité réglementaire, appel à projets, coordonnées d'un service) que AUCUN autre outil ne couvre.",
     "params": {"question": "la question du client, verbatim"}},
]

SELECT_SYSTEM = """Tu aiguilles une QUESTION du client LABUSE (foncier de La Réunion) vers UN outil, ou vers un refus.
Tu ne réponds PAS à la question. Tu choisis. Réponds un objet JSON STRICT, rien d'autre.

OUTILS DISPONIBLES :
{catalogue}

RÈGLES :
- Choisis l'outil dont la description couvre la question, et remplis "args" avec les paramètres typés
  déductibles (surfaces en m² ; « au moins X » → surface_min=X ; « au plus X » → surface_max=X ;
  « brûlantes » SEULES → tier "brulante" ; « opportunités » OU « brûlantes ET chaudes » → tier
  "opportunites" ; « personnes morales » → personne_morale=true ; un IDU = 14 caractères ; un
  nom/SIREN de société → q). MAPPING FACETTE (M110) : « en procédure judiciaire / redressement /
  liquidation / BODACC » → signaux "procedure" ; « friche(s) » → signaux "friche" ; « cession de
  fonds » → signaux "cession" ; « en défiscalisation / défisc » → defisc=true ; « renouvellement
  urbain » → renouvellement=true ; « sans adresse / adresse absente » → adresse_absente=true ;
  « copropriété(s) / en copro » → copro "avec" ; « hors copropriété » → copro "sans" ; « à événement
  (rouge) » → evenement=true ; « en zone U / AU / A / N » → zonage (ex. "U"). Ces critères sont
  APPLIQUÉS (ne les mets JAMAIS dans criteres_non_appliques).
- « Combien de permis (accordés) à X » → outil delais_instruction (il porte AUSSI le nombre de permis).
- REFUS (mets "tool":null et "refus" à la bonne valeur, "args":{{}}) :
  · "proprietaire_pp" : on demande l'identité/nom/adresse du PROPRIÉTAIRE d'une parcelle (personne
    physique — donnée non ouverte). NB : « quelles parcelles possède [société] » n'est PAS un refus
    (c'est parcelles_par_entreprise).
  · "projection" : on demande une valeur/évolution FUTURE (« dans 10 ans », « l'an prochain », « va
    monter »). LABUSE ne projette pas.
  · "aucun_outil" : aucun outil ci-dessus ne couvre la demande (ex. divisibilité d'UNE parcelle).
- HIÉRARCHIE DES SOURCES (M78-ter) : la BASE LABUSE prime TOUJOURS. `recherche_web` est le DERNIER
  recours — ne le choisis QUE si (a) aucun outil interne ne couvre, ET (b) ce n'est PAS une action
  couverte par un outil LABUSE (une procédure PLU, un règlement de zone, un prix/délai/marché, des
  parcelles… restent des outils internes, JAMAIS le web), ET (c) le sujet reste dans la barrière :
  foncier/immobilier/urbanisme/collectivités et acteurs de LA RÉUNION. Hors barrière → pas le web.
- CRITÈRES NON APPLIQUÉS (M109/M110, RÈGLE DURE) : les critères listés au MAPPING FACETTE ci-dessus
  sont APPLICABLES — mappe-les. Restent NON applicables par `compter_parcelles` : la constructibilité
  calibrée, le budget/prix (charge foncière, prix marché), la densité/capacité, le rang, la fiabilité
  marché. Si la demande porte un tel critère, tu choisis quand même `compter_parcelles` avec les
  paramètres applicables, MAIS tu listes ce ou ces critères dans "criteres_non_appliques" (langage
  client, ex. "constructibilité", "budget maximum"). NE JAMAIS faire passer un critère non applicable
  pour appliqué. Rien à signaler → [].
SORTIE : {{"tool": <nom|null>, "args": {{...}}, "refus": <"proprietaire_pp"|"projection"|"aucun_outil"|null>,
  "criteres_non_appliques": [<critères de la demande que l'outil ne peut pas appliquer>]}}"""

FORMULE_SYSTEM = """Tu es le copilote foncier de LABUSE. Formule une réponse en français, brève et claire, à la
question du client, UNIQUEMENT à partir du RÉSULTAT D'OUTIL fourni (JSON). Règles STRICTES :
- N'invente AUCUN chiffre : tout nombre de ta réponse doit apparaître dans le résultat. Si une valeur
  manque, dis-le, ne la devine pas.
- Si un champ "faits_du_fil" est fourni (chiffres déjà servis plus tôt dans CETTE conversation), tu
  peux reprendre UNIQUEMENT un chiffre qui y figure, en citant sa source et son millésime. Un chiffre
  absent des faits_du_fil ET du résultat d'outil N'EXISTE PAS pour toi — jamais de reprise « de
  mémoire ».
- Cite la source entre parenthèses à la fin (champ "source"), avec le millésime s'il est fourni.
- Si le résultat porte une "reserve" (couverture partielle), INCLUS-la fidèlement — ne la tais jamais.
- Si un champ "criteres_non_appliques" est fourni, ta réponse ne doit PAS prétendre que ces critères
  sont appliqués (le système ajoute lui-même l'avertissement). Réponds sur les critères APPLIQUÉS
  seulement, sans habiller le chiffre du critère manquant.
- Pas de conseil juridique, pas de projection, pas de superlatif. Le ton est sobre et honnête.
Réponds seulement la réponse au client, sans préambule ni balises."""


def _avert_cna(cna: list[str]) -> str:
    """M109 — l'avertissement DÉTERMINISTE des critères lâchés (jamais laissé au hasard du modèle) :
    le chiffre est servi POUR CE QU'IL EST, le critère non appliqué est nommé."""
    if not cna:
        return ""
    crit = ", ".join(f"« {c} »" for c in cna)
    pl = "s" if len(cna) > 1 else ""
    return (f" ⚠️ Le critère{pl} {crit} n'est pas encore interrogeable ici : ce chiffre couvre les "
            "critères appliqués seulement, pas celui-là.")


def _reply(text: str, intent: str, **extra: Any) -> dict:
    return {"text": text, "intent": intent, **extra}


def _extract_json(text: str) -> dict | None:
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = raw.strip("`").removeprefix("json").strip()
    a, b = raw.find("{"), raw.rfind("}")
    if a == -1 or b < a:
        return None
    try:
        return json.loads(raw[a:b + 1])
    except json.JSONDecodeError:
        return None


_NUM = re.compile(r"\d[\d\s.,]*")


def _nombres(s: str) -> set[float]:
    out = set()
    for m in _NUM.finditer(s or ""):
        t = m.group().strip().replace(" ", "").replace(" ", "")
        # 1.234,5 (fr) ou 1234.5 — on normalise en float, tolère séparateurs
        t = t.rstrip(".,")
        if t.count(",") == 1 and t.count(".") == 0:
            t = t.replace(",", ".")
        else:
            t = t.replace(",", "")
        try:
            out.add(round(float(t), 2))
        except ValueError:
            pass
    return out


def _valeurs_autorisees(res) -> set[float]:
    """Nombres légitimes = ceux du résultat d'outil (valeur + data + réserve citée)."""
    autor: set[float] = set()
    blob = json.dumps(res.data, ensure_ascii=False, default=str) + " " + str(res.valeur or "")
    if res.reserve:
        blob += " " + res.reserve
    # la source + le millésime sont légitimes à citer (ex. « q_v9_m81 », « 2013–2026 »)
    blob += " " + str(res.source or "") + " " + str(res.millesime or "")
    autor |= _nombres(blob)
    # tolérance d'arrondi : ±1 sur chaque valeur entière (formulations « ~9 mois », « 9 » vs « 9.0 »)
    autor |= {round(v) for v in list(autor)}
    return autor


def _anti_invention(prose: str, res, valeurs_fil: set[float] | None = None) -> bool:
    """Vrai si tout nombre de la prose est justifié par le résultat DU TOUR ou par le REGISTRE
    DE FAITS DU FIL (M102-B3 — chaque fait du registre vient d'un ToolResult antérieur, avec
    outil/source/millésime : c'est l'oracle de la reprise). Un nombre dans AUCUN des deux →
    False → gabarit du tour courant (le chiffre n'est PAS servi, jamais de reprise de mémoire)."""
    autor = _valeurs_autorisees(res)
    if valeurs_fil:
        autor = autor | valeurs_fil
    for n in _nombres(prose):
        if n in autor or round(n) in autor or any(abs(n - a) <= 1 for a in autor):
            continue
        return False
    return True


def _select_tool(db: Session, message: str, params: dict) -> dict:
    cat = "\n".join(f"- {t['nom']} : {t['desc']} params={t['params']}" for t in CATALOGUE)
    res = core.complete(db, kind="copilote-select", model=core.MODEL_REASONING, max_tokens=300,
                        system=SELECT_SYSTEM.format(catalogue=cat),
                        context={"question": message, "params_extraits": params})
    if res.degraded:
        return {"tool": None, "refus": "_infra"}
    data = _extract_json(res.text) or {}
    cna = data.get("criteres_non_appliques") or []
    cna = [str(c).strip() for c in cna if str(c or "").strip()][:5] if isinstance(cna, list) else []
    return {"tool": data.get("tool"), "args": data.get("args") or {}, "refus": data.get("refus"),
            "criteres_non_appliques": cna}


# coercition des args du modèle vers les kwargs typés de chaque outil
_ARG_SPEC = {
    "compter_parcelles": {"commune": str, "surface_min": int, "surface_max": int, "tier": str,
                          "personne_morale": bool, "evenement": bool, "signaux": str,
                          "adresse_absente": bool, "copro": str, "defisc": bool,
                          "renouvellement": bool, "zonage": str},
    "parcelles_par_entreprise": {"q": str},
    "fiche_parcelle": {"idu": str},
    "stats_commune": {"commune": str},
    "delais_instruction": {"commune": str},
    "marche": {"commune": str},
    "recherche_web": {"question": str},
}


def _clean_args(tool: str, args: dict) -> dict:
    spec = _ARG_SPEC.get(tool, {})
    out = {}
    for k, typ in spec.items():
        if k not in args or args[k] is None:
            continue
        v = args[k]
        try:
            out[k] = bool(v) if typ is bool else int(v) if typ is int else str(v)
        except (TypeError, ValueError):
            continue
    return out


def _formuler(db: Session, message: str, res, faits_fil: list[dict] | None = None) -> str:
    from . import registre_faits
    cna = res.criteres_non_appliques or []
    payload = {"question": message, "outil": res.tool, "resultat": res.data,
               "valeur": res.valeur, "source": res.source, "millesime": res.millesime,
               "reserve": res.reserve if res.partiel else None,
               "criteres_non_appliques": cna or None}
    if faits_fil:
        # M102-B3 — les faits du fil (chiffres déjà servis, avec outil/source/millésime) : le
        # formuler ne peut reprendre QUE ceux-là, le verrou le vérifie contre le registre.
        payload["faits_du_fil"] = registre_faits.contexte_formuler(faits_fil)
    out = core.complete(db, kind="copilote-formule", model=core.MODEL_REASONING, max_tokens=350,
                        system=FORMULE_SYSTEM, context=payload)
    prose = (out.text or "").strip()
    if out.degraded or not prose or not _anti_invention(prose, res, registre_faits.valeurs(faits_fil or [])):
        # gabarit sourcé (jamais l'affirmation douteuse) — inclut la réserve si partielle
        base = (f"{res.valeur}" if res.valeur is not None
                else json.dumps(res.data, ensure_ascii=False, default=str))
        prose = f"{base} ({res.source}{' · ' + res.millesime if res.millesime else ''})."
        if res.partiel and res.reserve:
            prose += " " + res.reserve
    # M109 — LE VERROU ÉTENDU : un chiffre servi doit correspondre à la demande INTERPRÉTÉE. Si un
    # critère a été lâché, la réponse le DIT — déterministe, jamais laissé au modèle. Le sous-total
    # muet n'est plus possible : si la prose ne dit pas déjà l'absence (marqueur), on l'ajoute ; le
    # chemin gabarit (anti-invention échouée) ne dit jamais rien → l'avertissement y tombe toujours.
    if cna and not any(w in prose.lower() for w in
                       ("pas pu être appliqué", "pas pu etre applique", "non appliqué", "non applique",
                        "pas appliqué", "pas applique", "pas interrogeable")):
        return prose + _avert_cna(cna)
    return prose


def answer(db: Session, message: str, history: list[dict] | None = None,
           contexte: dict | None = None, confirme: bool = False,
           prior_params: dict | None = None, faits_fil: list[dict] | None = None) -> dict:
    """Point d'entrée unique du Copilote v2. Retourne un dict prêt à rendre. `confirme=True` : le client
    a validé le récap (§M78-bis) → on produit la mission lourde (VERIFICATION) au lieu du récap.

    M102-B1 — `history`/`prior_params` viennent du FIL persisté (rechargés par l'endpoint depuis
    conversation_id) : le tour est interprété DANS son contexte (une réponse à une clarification
    hérite de l'intention et des paramètres — le prompt routeur est conçu pour, gate 45 msgs).
    La réponse porte `_route` (intent + params du tour, jamais servi au client — poppé par
    l'endpoint) pour alimenter le contexte du tour SUIVANT. AUCUNE reprise de chiffre d'un tour
    antérieur ici : une clarification apporte des PARAMÈTRES, pas des faits — l'anti-invention
    reste vérifiée contre l'outil du tour courant (le registre de faits est le mandat B3)."""
    route = classify(db, message, history=history, contexte=contexte, prior_params=prior_params)
    if route.degraded:
        return _reply(ERREUR_INFRA, None, degraded=True)
    rep = _answer_with_route(db, message, route, contexte=contexte, confirme=confirme,
                             faits_fil=faits_fil, history=history)
    # M102-B1 — contexte du tour attaché en UN point (quel que soit le chemin de réponse) :
    # poppé par l'endpoint pour la persistance du fil, jamais servi au client.
    rep.setdefault("_route", {"intent": route.intent, "clarification": bool(route.clarification),
                              "params": {k: v for k, v in (route.params or {}).items()
                                         if v is not None and k != "selection"}})
    # M102-B2 — RÉCAP SYSTÉMATIQUE (extension Vic de la règle M78) : une phrase « j'ai compris »
    # partout où une interprétation a eu lieu. Les missions lourdes gardent leur récap-péage M78
    # (pas de doublon) ; hors-sujet/dégradé n'interprètent rien. Jamais un slug : clés traduites,
    # clé inconnue ÉLAGUÉE (plutôt muette que jargonnante).
    if (route.intent in ("QUESTION", "OUTIL", "PROJET", "VEILLE")
            and not rep.get("degraded") and rep.get("refus") != "hors_sujet"):
        compris = _compris_fr(route.intent, route.params or {})
        # M110 — le récap NOMME les critères de facette appliqués (au-delà des params du routeur :
        # friche, procédure, copropriété, zone U…) — « comme aujourd'hui » pour commune/surface.
        appliques = rep.get("criteres_appliques") or []
        if compris and appliques:
            compris = compris.rstrip(".") + " · " + " · ".join(appliques) + "."
        # M111 — un héritage DIT n'est pas une contamination : les paramètres VENUS DU FIL (continuation)
        # sont nommés explicitement au récap, jamais muets. (Le tour autonome n'hérite plus — herites vide.)
        herites = getattr(route, "herites", None) or {}
        hlabs = [_COMPRIS_PARAM[k](herites[k]) for k in _COMPRIS_PARAM
                 if herites.get(k) not in (None, "", [])]
        if compris and hlabs:
            compris = compris.rstrip(".") + " (repris du fil : " + " · ".join(hlabs) + ")."
        # M109 — le récap dit AUSSI ce qui n'est PAS appliqué : un critère lâché est nommé DANS le
        # récap (pas seulement dans la réponse), jamais passé sous silence.
        cna = rep.get("criteres_non_appliques") or []
        if compris and cna:
            compris = compris.rstrip(".") + " — critère non appliqué : " + ", ".join(cna) + "."
        if compris:
            rep.setdefault("compris", compris)
    return rep


_COMPRIS_INTENT = {"QUESTION": "répondre à votre question", "OUTIL": "vous ouvrir un outil",
                   "PROJET": "cadrer votre projet", "VEILLE": "poser une veille"}
_COMPRIS_PARAM = {"commune": lambda v: str(v), "idu": lambda v: f"parcelle {v}",
                  "zone": lambda v: f"zone {v}", "surface_min": lambda v: f"≥ {v} m²",
                  "surface_max": lambda v: f"≤ {v} m²", "budget_eur": lambda v: f"budget {v} €",
                  "prix_eur": lambda v: f"prix {v} €", "entreprise": lambda v: str(v),
                  "programme_logements": lambda v: f"{v} logements", "sujet": lambda v: str(v)}


def _compris_fr(intent: str, params: dict) -> str | None:
    """La phrase du récap systématique (M102-B2) — UNE phrase, jamais un formulaire, jamais un
    slug (clé hors table = élaguée)."""
    tete = _COMPRIS_INTENT.get(intent)
    if not tete:
        return None
    bouts = [fmt(params[k]) for k, fmt in _COMPRIS_PARAM.items()
             if params.get(k) not in (None, "", [])]
    return f"J'ai compris : {tete}" + (f" — {' · '.join(bouts)}." if bouts else ".")


def _answer_with_route(db: Session, message: str, route, contexte: dict | None = None,
                       confirme: bool = False, faits_fil: list[dict] | None = None,
                       history: list[dict] | None = None) -> dict:
    intent = route.intent
    params = route.params
    # §5 Copilote EMBARQUÉ : le contexte visible (la parcelle / la sélection) EST le contexte du
    # Copilote. « ce prix est-il correct ? » sur une fiche part en VERIFICATION sans retaper l'IDU.
    if contexte:
        if contexte.get("idu") and not params.get("idu"):
            params["idu"] = contexte["idu"]
        if contexte.get("selection") and not params.get("selection"):
            params["selection"] = contexte["selection"]

    # §M78-bis 2d : RECHERCHE/VERIFICATION ne court-circuitent PAS sur la clarification du routeur — elle
    # ALIMENTE leur récap (qui pose une clarification COURTE, ≤ 4 options). Pas de double question.
    if route.clarification and intent not in ("HORS_SUJET", "RECHERCHE", "VERIFICATION"):
        return _reply(route.clarification, intent, clarification=True)

    # M110 — CONCEPTS-OUTILS du registre reconnus quel que soit l'intent deviné (« parcelles
    # fantômes », « bailleurs sociaux ») : le Copilote route vers l'OUTIL (porte cliquable, mécanique
    # M102) au lieu d'une recherche vague ou d'un « je ne comprends pas ». Les deux outils EXISTENT.
    concept = _match_concept(message)
    if concept and intent in ("RECHERCHE", "OUTIL", "QUESTION"):
        module, label = concept
        return _reply(f"Je peux ouvrir l'outil {label}.", "OUTIL", porte=module, prefill=None)

    if intent == "HORS_SUJET":
        return _reply(HORS_SUJET, intent, refus="hors_sujet")

    if intent == "QUESTION":
        sel = _select_tool(db, message, params)
        refus = sel.get("refus")
        if refus == "proprietaire_pp":
            telemetrie.refus(db, "proprietaire_pp", message, intent)
            return _reply(REFUS_PP, intent, refus="proprietaire_pp", porte="courriers")
        if refus == "projection":
            telemetrie.refus(db, "projection", message, intent)
            return _reply(REFUS_PROJECTION, intent, refus="projection")
        if refus == "aucun_outil" or not sel.get("tool"):
            return _sans_outil(db, message, params, intent)
        tool = sel["tool"]
        if tool not in OUTILS:
            return _sans_outil(db, message, params, intent)
        # M78-ter — recherche_web : DERNIER recours, la question verbatim ; marquage web distinct.
        if tool == "recherche_web":
            res = OUTILS["recherche_web"](db, question=message)
            if not res.ok:                                 # rien trouvé → refus honnête + télémétrie
                telemetrie.refus(db, "web_rien_trouve", message, intent)
                return _sans_outil(db, message, params, intent)
            telemetrie.web(db, message, res.data.get("domaines", []))
            d = res.data
            # marquage NON négociable : « Source : web · domaine · consulté le date » (jamais Sourcé/Estimé)
            marque = f"Source : web · {d['domaines'][0]} · consulté le {d['date']}"
            return _reply(f"{d['reponse']}\n\n{marque}", intent, tool="recherche_web", web=True,
                          sources=d["domaines"])
        res = OUTILS[tool](db, **_clean_args(tool, sel.get("args") or {}))
        # M109 — les critères de la demande que l'outil ne peut pas appliquer voyagent avec le
        # résultat (le sélecteur les a nommés) : le formuler et le récap DOIVENT les dire.
        res.criteres_non_appliques = sel.get("criteres_non_appliques") or []
        # M110 — ambiguïté d'entité : le Copilote DEMANDE (clarification, champ de réponse M107),
        # il ne tranche pas au hasard entre deux sociétés plausibles.
        if not res.ok and (res.refus or "").startswith("_ambigu:"):
            return _reply(res.refus.split(":", 1)[1], intent, clarification=True)
        if not res.ok:
            return _sans_outil(db, message, params, intent, motif=res.refus)
        text = _formuler(db, message, res, faits_fil)
        # M102-B3 — les faits numériques de CE tour rejoignent le registre (poppé par l'endpoint,
        # persisté avec la conversation — jamais servi au client).
        from . import registre_faits
        return _reply(text, intent, refus=None, tool=tool, sources=[res.source],
                      partiel=res.partiel, criteres_non_appliques=res.criteres_non_appliques,
                      criteres_appliques=(res.data or {}).get("criteres_labels") or [],
                      _faits_tour=registre_faits.extraire_faits(res))

    if intent == "OUTIL":
        return _outil(db, message, params)

    if intent == "VERIFICATION":
        # §M78-bis : PÉAGE de confirmation (avis d'achat = coût élevé d'une mauvaise interprétation).
        # Récap d'abord ; l'avis n'est produit qu'après validation du client (confirme).
        if confirme:
            from .missions_lourdes import verification
            return verification(db, params)
        from .recap import recap_verification
        return recap_verification(params)

    if intent == "PROJET":
        # la fiche est préparée ici ; l'ÉCRITURE RÉELLE (API projets) est faite par l'endpoint /ask
        # (il a le compte). Doctrine : quand le Copilote dit « c'est fait », la chose EST faite.
        from .missions_lourdes import preparer_projet
        return _reply("Création du projet…", intent, _action={"type": "projet", **preparer_projet(params, message)})

    if intent == "VEILLE":
        from .missions_lourdes import preparer_veille
        return preparer_veille(db, params, message)

    if intent == "RECHERCHE":
        # §M78-bis : on n'instruit PAS tout de suite — récap (interprétation sans lancer) + suggestions.
        # Le front lance le run M26-A sur « Lancer ». Une clarification alimente le récap (≤ 3-4 options).
        # M107 — une réponse à une clarification n'est JAMAIS interprétée nue : le BRIEF EFFECTIF =
        # les tours CLIENT du fil (bornés aux 4 derniers) + le message courant. Mesuré : « 15
        # logements » seul re-demandait la commune donnée au tour d'avant. Le brief effectif est
        # SERVI (brief_effectif) — le front relance le récap et le run avec LUI, jamais avec la
        # réponse nue. (Si ce tour est classé RECHERCHE avec un fil, c'est une continuation — le
        # routeur contextuel en atteste, gate 45.)
        from .recap import recap_recherche
        tours_client = [h.get("content", "") for h in (history or []) if h.get("role") == "user"]
        # M111 — RUPTURE DE SUJET : un tour AUTONOME (route.nouveau_sujet) ne concatène plus le fil
        # (fin du « 38 logements [30+8] » et du « ≥ 20000 m² hérité »). Une CONTINUATION compose avec
        # les tours client — la clarification M107 tient toujours (le cas témoin « 15 logements »).
        # Décidé par le routeur (UN seul endroit, jamais une heuristique front).
        if route.nouveau_sujet or not tours_client:
            brief_effectif = message
        else:
            brief_effectif = ", ".join([t for t in tours_client[-4:] if t] + [message])
        rep = recap_recherche(db, brief_effectif)
        rep["brief_effectif"] = brief_effectif
        return rep

    return _reply(f"(Mission {intent} — inconnue.)", intent, en_construction=True)


# ───────────────────────── Aiguillage OUTIL (1c) ─────────────────────────
# demande-type (mot-clé folded) → (module registre, libellé, prefill). None = AUCUN outil (division).
_OUTIL_MAP = [
    (("assembl",), ("assemblage", "Assemblage", "parcelPrefill")),
    (("faisabil", "constructib", "capacit", "que peut accueillir"), ("programme", "Faisabilité", "parcelPrefill")),
    (("charge fonci", "combien payer", "combien je peux payer", "marge", "prix d'achat max"),
     ("calculette-fonciere", "Calculette foncière", "calcPrefill")),
    (("courrier", "ecrire au proprietaire", "ecrire au proprio"), ("courriers", "Courrier au propriétaire", "idu")),
    (("comparer", "cote a cote", "cote-a-cote"), ("comparer", "Comparateur de parcelles", "selection")),
    (("reglement", "annuaire plu"), ("plu-annuaire", "Annuaire PLU", "pluPrefill")),
    (("lettre de zonage", "verification de zonage"), ("lettre-zonage", "Lettre de vérification de zonage", "idu")),
    (("procedure plu", "revision plu", "sursis a statuer", "nouveau plu", "plu disponible", "plu a jour",
      "plu en cours", "nouveau document d'urbanisme"), ("verif-procedure", "Vérif procédure PLU", "idu")),
    (("due diligence", "controle avant achat", "avant d'acheter"), ("duediligence", "Contrôle avant achat", "idu")),
    (("servitude",), ("o5-servitudes", "Servitudes invisibles", "idu")),
    (("remonter le temps", "evolution dans le temps", "en 1950", "historique du site"),
     ("temps", "Remonter le temps", "idu")),
]
_SANS_OUTIL_KW = ("divis", "decoup", "lotir", "detacher un lot")

# M110 — CONCEPTS-OUTILS souvent formulés en RECHERCHE/QUESTION mais qui SONT un outil du registre.
# Le routeur les envoyait en recherche vague (« je ne comprends pas ») ; ici ils deviennent une
# porte cliquable vers l'outil qui existe. (module registre, libellé client.)
_CONCEPT_MAP = [
    (("parcelle fantome", "parcelles fantomes", "parcelles fantome", "parcelle fantome",
      "bien fantome", "biens fantomes"), ("fantome", "Parcelles fantômes")),
    # NB : PAS « logements sociaux » nu (= le taux SRU d'une commune → stats_commune, pas l'outil
    # bailleur). Le concept-outil vise le PATRIMOINE des bailleurs, pas la métrique SRU.
    (("bailleur social", "bailleurs sociaux", "parcelles des bailleurs", "parc social bailleur",
      "patrimoine des bailleurs", "parcelles de bailleur"), ("bailleur", "Bailleurs sociaux")),
]

from .outils import _fold_py  # accent-fold (réutilisé)


def _match_outil(message: str):
    m = _fold_py(message.lower())
    for kws, cible in _OUTIL_MAP:
        if any(k in m for k in kws):
            return cible
    return None


def _match_concept(message: str):
    """(module, libellé) si la demande désigne un concept-outil du registre (fantôme, bailleur),
    sinon None. Reconnaissance par mots-clés foldés — jamais une devinette."""
    m = _fold_py(message.lower())
    for kws, cible in _CONCEPT_MAP:
        if any(k in m for k in kws):
            return cible
    return None


def _substance(db: Session, idu: str | None) -> str:
    """Ce que LABUSE SAIT déjà sur une parcelle citée (fond), sans outil."""
    if not idu:
        return ""
    from .outils import fiche_parcelle
    r = fiche_parcelle(db, idu=idu)
    if not r.ok:
        return ""
    d = r.data
    bout = [f"{d['surface_m2']} m²" if d.get("surface_m2") else None,
            f"zone {d['zone']}" if d.get("zone") else None,
            f"à {d['commune']}" if d.get("commune") else None]
    return " · ".join(x for x in bout if x)


_COUVRE = ("LABUSE couvre les données foncières et de marché : parcelles (comptage, surface, zonage, "
           "verdict), prix et délais d'instruction par commune, patrimoine des sociétés.")


def _sans_outil(db: Session, message: str, params: dict, intent: str, motif: str | None = None) -> dict:
    """Issue 4 : aucun outil ne correspond. Refus honnête, JAMAIS une réponse plausible. La division
    est traitée à part (dire le règlement, pas trancher). Sinon : dire ce que LABUSE COUVRE (pas un mur)."""
    telemetrie.refus(db, "aucun_outil", message, intent)
    m = _fold_py(message.lower())
    idu = params.get("idu")
    if "divis" in m or "decoup" in m or "detacher un lot" in m or "lotir" in m:
        return _division(db, idu, intent)
    txt = "Je n'ai pas d'outil dédié pour cette demande. " + _COUVRE
    fond = _substance(db, idu)
    if fond:
        txt += f" Sur le terrain cité : {fond}."
    return _reply(txt, intent, refus="aucun_outil", porte=None)


def _division(db: Session, idu: str | None, intent: str) -> dict:
    """Division : ne JAMAIS trancher la divisibilité (arbitrage Vic). Dire ce que le RÈGLEMENT impose
    (surface minimale, accès, emprise) et ce que la parcelle mesure ; laisser le client conclure.
    Zone A/N → la construction nouvelle n'est pas autorisée : le dire. Sinon → porte Annuaire PLU."""
    from .outils import fiche_parcelle
    zone = surface = commune = None
    if idu:
        r = fiche_parcelle(db, idu=idu)
        if r.ok:
            zone, surface, commune = r.data.get("zone"), r.data.get("surface_m2"), r.data.get("commune")
    z = (zone or "").upper()
    non_constructible = z.startswith("N") or (z.startswith("A") and not z.startswith("AU"))
    if idu and non_constructible:
        voc = "agricole" if z.startswith("A") else "naturelle"
        txt = (f"En zone {zone} (à vocation {voc}), la construction nouvelle n'est en principe pas "
               f"autorisée : détacher un lot à bâtir n'a pas d'objet ici. Cette parcelle mesure "
               f"{surface} m² à {commune}.")
        return _reply(txt, intent, refus="aucun_outil", porte=None)
    txt = ("Je ne tranche pas la divisibilité réglementaire d'une parcelle : elle dépend d'abord du "
           "règlement de la zone — surface minimale de terrain, accès, emprise au sol.")
    mesure = ((f" Cette parcelle mesure {surface} m²" + (f" en zone {zone}" if zone else "")
               + (f" à {commune}" if commune else "") + ".") if surface else "")
    # M82 (cas A) : le score GÉOMÉTRIQUE précalculé (module_division, lookup par IDU) ENRICHIT la réponse
    # sans trancher le réglementaire (doctrine réglementaire > géométrique). Candidate ≠ feu vert.
    if idu:
        from .outils import divisibilite
        d = (divisibilite(db, idu=idu)).data or {}
        if d.get("candidate"):
            txt += (mesure + f" Géométriquement, elle est CANDIDATE au détachement d'un lot : facilité "
                    f"{d['score']}/100 (place libre, forme, accès), lot estimé ~{d['lot_estime_m2']} m² — "
                    "un repère de faisabilité géométrique, pas un feu vert réglementaire.")
        else:
            txt += (mesure + " Géométriquement, elle n'est pas repérée comme candidate au détachement "
                    "(surface, bâti, emprise ou zone hors critères) — ce n'est pas un « non divisible ».")
    txt += " Je peux ouvrir l'Annuaire PLU pour le règlement applicable — à vous de conclure."
    return _reply(txt, intent, refus="aucun_outil", porte="plu-annuaire", prefill="pluPrefill",
                  prefill_plu=({"insee": idu[:5], "zone": zone} if idu else None))


def _outil(db: Session, message: str, params: dict) -> dict:
    cible = _match_outil(message)
    idu = params.get("idu")
    if cible is None:
        return _sans_outil(db, message, params, "OUTIL")
    module, label, prefill = cible
    txt = f"Je peux ouvrir l'outil {label}"
    if idu and prefill in ("parcelPrefill", "calcPrefill", "idu", "pluPrefill"):
        txt += f", pré-rempli avec la parcelle {idu}."
    else:
        txt += "."
    return _reply(txt, "OUTIL", porte=module, prefill=prefill,
                  prefill_idu=idu if prefill in ("parcelPrefill", "calcPrefill", "idu") else None)
