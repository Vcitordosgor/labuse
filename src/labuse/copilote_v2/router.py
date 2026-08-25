"""M78 · 1a — ROUTEUR D'INTENTION.

Un appel modèle classe chaque message client en SEPT intentions et extrait des paramètres typés.
Sortie JSON strict, validée par schéma (jsonschema) côté serveur ; invalide → une re-demande, puis
erreur honnête. Le modèle ROUTE, il ne répond JAMAIS une donnée (doctrine RAPPORT_M78.md).

Mirroir du motif éprouvé de `/ia/search` (core.complete + schéma garde-fou), sur **MODEL_FACTUAL**
(haiku) — M113 · Phase 0 a MESURÉ que le tri n'a pas besoin de sonnet : haiku fait 100 % au gate
routeur (45 cas, mieux que 97,1 % sonnet), pour ⅓ du coût et ~2–4 s de moins par message. Le
routage EST une extraction (intent + params dans un vocabulaire fermé), pas un raisonnement libre.
Contexte de session : les N derniers tours sont passés au modèle ; une correction (« non, je voulais
dire… ») re-classe SANS perdre les paramètres déjà extraits (fusion serveur `prior_params`).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from jsonschema import ValidationError, validate
from sqlalchemy.orm import Session

from ..ai import core

# Les SEPT intentions — l'enum est le garde-fou dur du schéma.
# M118 — le Copilote resserré à 4 missions : QUESTION (donnée app / web), EXPLIQUER (notion),
# PREPARER (script). OUTIL/RECHERCHE/VERIFICATION/VEILLE/PROJET restent CLASSÉS (l'aiguillage les
# renvoie à leur voie cliquable — Projets/Surveillance/Outils/fiche — ils ne s'exécutent plus au chat).
INTENTS = ["QUESTION", "EXPLIQUER", "PREPARER", "OUTIL", "RECHERCHE", "VERIFICATION", "VEILLE",
           "PROJET", "HORS_SUJET"]

# Paramètres typés extractibles (liste blanche — une clé hors liste est ÉLAGUÉE, jamais avalée).
PARAM_KEYS = [
    "commune", "idu", "zone", "surface_min", "surface_max", "budget_eur", "prix_eur",
    "entreprise", "programme_logements", "perimetre", "sujet",  # FIX-VEILLE : `veille_type` retiré (plus consommé — la veille se pose dans la Surveillance)
]

HISTORIQUE_TOURS = 6   # contexte de session passé au routeur (dimensionné §1a — rapporté)

ROUTE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "intent": {"enum": INTENTS},
        "params": {
            "type": "object",
            "properties": {
                "commune": {"type": ["string", "null"]},
                "idu": {"type": ["string", "null"]},
                "zone": {"type": ["string", "null"]},
                "surface_min": {"type": ["number", "null"]},
                "surface_max": {"type": ["number", "null"]},
                "budget_eur": {"type": ["number", "null"]},
                "prix_eur": {"type": ["number", "null"]},
                "entreprise": {"type": ["string", "null"]},
                "programme_logements": {"type": ["number", "null"]},
                "perimetre": {"type": ["string", "null"]},
                "sujet": {"type": ["string", "null"]},
            },
            "additionalProperties": False,
        },
        "clarification": {"type": ["string", "null"]},
        "confidence": {"type": ["number", "null"]},
        # M111 — RUPTURE DE SUJET : le message change-t-il de sujet (demande autonome) ou
        # continue-t-il le fil (réponse à une clarification, correction, ajout de critère) ?
        "nouveau_sujet": {"type": ["boolean", "null"]},
    },
    "required": ["intent"],
    "additionalProperties": False,
}

ROUTER_SYSTEM = """Tu es le ROUTEUR d'intention du Copilote foncier LABUSE (immobilier/foncier de La Réunion UNIQUEMENT).
Ta SEULE tâche : classer le message du client dans UNE des sept intentions et extraire ses paramètres.
Tu ne réponds JAMAIS à la question, tu ne donnes AUCUNE donnée, AUCUN chiffre, AUCUN conseil. Tu routes.

LES SEPT INTENTIONS :
- QUESTION : le client pose une question factuelle qui appelle UNE réponse chiffrée/sourcée depuis la base
  (un compte, un prix médian, un délai d'instruction, la population/le taux SRU d'une commune, les
  parcelles d'une société, le contenu d'une fiche parcelle, le nombre de PISCINES détectées d'une
  commune, le nombre de réserves foncières de l'île). Les données PISCINES/SOLAIRE, PERMIS, MARCHÉ,
  COMMUNES sont des données LABUSE → QUESTION (jamais hors-sujet). Ex : « combien de parcelles > 1000 m²
  à Saint-Paul ? », « prix du terrain nu à Saint-Pierre ? », « délai d'instruction à Saint-Benoît ? »,
  « quelles parcelles possède la SCI Dupont ? », « combien de piscines à Saint-Paul ? », « combien de
  réserves foncières sur toute l'île ? », « population de Cilaos ? ».
- EXPLIQUER : le client veut de la CONNAISSANCE GÉNÉRALE sur le foncier/urbanisme/immobilier/fiscalité —
  une NOTION (zone AU, ZFANG, charge foncière, ANRU, PPR, SUP, SDP vs SHAB, coefficient d'emprise, SRU,
  défiscalisation, loi Girardin/Pinel outre-mer…), sa DÉFINITION, son PRINCIPE, ou son ÉTAT / son ACTUALITÉ
  (« la loi X est-elle toujours en vigueur ? », « ce dispositif existe-t-il encore ? », « quel est le
  principe de… »). C'est une explication de MÉMOIRE, PAS un chiffre ni un fait LABUSE sur une commune ou
  parcelle précise. Signal : « explique », « qu'est-ce que », « c'est quoi », « à quoi sert », « définition
  de », « comment marche », « toujours en vigueur / en place », « existe encore ». Ex : « qu'est-ce qu'une
  zone AU ? », « c'est quoi la loi Girardin ? », « elle est toujours en place ? » (suite de Girardin),
  « c'est quoi une SUP pm1 ? », « différence entre SDP et SHAB ». (« population de Cilaos », « prix à
  Saint-Pierre » restent QUESTION : ce sont des faits CHIFFRÉS LABUSE, pas de la connaissance générale.)
- PREPARER : le client veut qu'on lui PRÉPARE un SCRIPT d'appel ou un ARGUMENTAIRE pour aborder un
  propriétaire/vendeur (ce qu'il va DIRE). Signal : « prépare un argumentaire », « script d'appel », « comment
  aborder le propriétaire », « quoi dire au vendeur », « aide-moi à convaincre ». Ex : « prépare-moi un
  argumentaire pour le propriétaire de cette parcelle ». (Un COURRIER écrit / un dossier formel N'EST PAS
  PREPARER → OUTIL, l'aiguillage renvoie au générateur de la fiche/CRM.)
- RECHERCHE : le client veut TROUVER/LISTER un ensemble de parcelles à instruire selon des critères, pour
  en sortir une shortlist classée (une mission, pas une réponse brève). Ex : « trouve des terrains à fort
  potentiel à Saint-Leu pour 15 logements », « montre les meilleures opportunités sous 500 000 € », « liste
  les friches en zone U ». Signal : « trouve », « cherche », « montre-moi des », « liste les », un objectif
  de programme, un budget d'achat, plusieurs critères combinés.
- VERIFICATION : le client veut faire évaluer UNE parcelle précise, en général face à un prix. Ex : « cette
  parcelle 974... vaut-elle 320 000 € ? », « le vendeur demande 280 000 €, est-ce raisonnable ? », « vérifie
  le prix de 974... ». Signal : un IDU (14 caractères) ou « cette parcelle » + une notion de prix/valeur/juste.
- OUTIL : le client décrit une ACTION qui correspond à un outil métier (assembler des parcelles, écrire au
  propriétaire, calculer la charge foncière, comparer des parcelles, diviser/découper un terrain, remonter le
  temps…) OU une question qu'un outil LABUSE couvre : « un nouveau PLU / une révision PLU / une procédure PLU
  à X ? » (Vérif procédure), « le règlement de la zone X » (Annuaire PLU). Signal : une action, ou un sujet
  qu'un outil interne traite. Même si aucun outil n'existe pour l'action (ex. diviser une parcelle précise),
  l'intention reste OUTIL — l'aiguillage en aval décidera.
- VEILLE : le client veut être PRÉVENU/ALERTÉ dans le futur d'un événement (nouveau permis, vente, procédure
  PLU, BODACC sur une société). Signal : « préviens-moi », « alerte-moi », « surveille », « tiens-moi au
  courant », « quand… ».
- PROJET : le client déclare un NOUVEAU projet à créer/enregistrer, OU gère un projet existant (y rattacher
  une parcelle). Ex : « j'ai un nouveau projet : résidence 12 lots à Bras-Panon », « crée un projet 30
  logements à Saint-André », « ajoute/attache cette parcelle à ce projet ». Signal : « nouveau projet »,
  « crée un projet », « enregistre », « ajoute … au projet ».
- HORS_SUJET : rien à voir avec l'immobilier/foncier de La Réunion (météo, cuisine, poésie, bavardage).
  ATTENTION : une question sur la VALEUR ou l'ÉVOLUTION FUTURE d'un bien/terrain/marché réunionnais
  (« combien vaudra… dans 10 ans », « le marché va-t-il monter… ») N'EST PAS hors-sujet — c'est du
  foncier → classe QUESTION (le refus « projection » se décide en aval, pas ici). De même, les
  SERVICES et la FISCALITÉ du foncier/immobilier réunionnais (notaire, géomètre, avocat foncier,
  fiscalité immobilière, financement d'un projet), ainsi que les COLLECTIVITÉS et leurs ACTEURS à La
  Réunion (maire, élu, commune, EPCI, Région, Département, organigramme d'un service, actualité
  réglementaire, appel à projets logement) ne sont PAS hors-sujet → QUESTION (l'aiguillage en aval
  décide : outil interne, recherche web, ou refus). Réserve HORS_SUJET au vraiment étranger au foncier
  réunionnais (météo, cuisine, sport, bavardage).

RÈGLES :
- RÈGLE DURE : tout message qui commence par « Combien » attend un NOMBRE → QUESTION, quel que soit le
  sujet (« combien de parcelles brûlantes à X » = QUESTION, jamais RECHERCHE). Une question « Combien de
  … à [commune] ? » est CLAIRE : "clarification" = null. Ne demande JAMAIS de préciser la métrique
  (« logements existants ou à construire ? », « quel indicateur ? ») — l'outil en aval sert le compte
  naturel. « Combien de logements à Saint-Paul ? » = QUESTION, commune Saint-Paul, clarification null.
- Frontière QUESTION vs RECHERCHE : une réponse BRÈVE et chiffrée (un compte, un prix, un délai) = QUESTION ;
  sortir un ENSEMBLE de parcelles à instruire = RECHERCHE. Une tournure « des parcelles [caractéristique]
  à [commune] », « des terrains [critère] », « donne/sors-moi des parcelles… » désigne un ENSEMBLE à lister
  = RECHERCHE, même sans le verbe « trouve » et même sans budget. « COMBIEN de… » attend un nombre = QUESTION.
  Dans le doute, préférer RECHERCHE dès qu'un objectif de programme, un budget d'achat, ou une demande de
  plusieurs parcelles est présent.
- AMBIGU : si le message est trop vague pour trancher (une commune seule, « cette parcelle » sans verbe,
  « je veux investir »), NE DEVINE PAS : mets "clarification" à UNE question courte, et choisis l'intent le
  plus probable à titre indicatif (confidence basse). Jamais un menu, UNE question.
- CONTEXTE DE SESSION : les tours précédents te sont donnés. « et à Saint-Benoît ? » après une question sur
  Saint-Paul HÉRITE de l'intention et des paramètres non modifiés (ici surface_min), en changeant la commune.
- CORRECTION : « non, je voulais dire… » RE-CLASSE le message, mais CONSERVE les paramètres déjà connus qui
  ne sont pas contredits (un IDU donné au tour précédent survit).
- RUPTURE DE SUJET (M111) : mets "nouveau_sujet" à true si le message est une DEMANDE AUTONOME qui change
  de sujet — une question ou une recherche complète en elle-même, sans lien avec les paramètres connus
  (ex. après « des terrains ≥ 20000 m² à Saint-Paul pour 30 logements », le message « combien de parcelles
  en procédure à Saint-Denis » ou « des friches à Cilaos pour 8 logements » est un NOUVEAU sujet). Mets-le
  à false si le message CONTINUE le fil : réponse à une clarification (« 15 logements »), correction
  (« non, plutôt à Saint-Leu », « et à Saint-Benoît ? »), ajout d'un critère au sujet courant (« hors
  ABF »). Sans contexte antérieur → true. En cas de doute, laisse hériter (false) : un héritage DIT au
  récap n'est pas une faute, l'utilisateur corrige d'un clic.
- EXTRACTION : remplis params avec ce qui est explicitement dit (commune normalisée en toponyme réunionnais ;
  idu = 14 caractères ; surfaces en m² ; budget_eur = budget d'ACHAT ; prix_eur = prix DEMANDÉ à vérifier ;
  entreprise = nom ou SIREN d'une personne morale ; programme_logements = nombre de logements visés ;
  sujet = 3-6 mots résumant la demande, pour la
  télémétrie). Mets null ce qui n'est pas dit. N'INVENTE aucune valeur.

SORTIE : un objet JSON STRICT, rien d'autre (pas de texte autour, pas de balises), de la forme :
{"intent": "<UNE des sept>", "params": {clés ci-dessus, null si absent}, "clarification": <string|null>,
 "confidence": <0..1>, "nouveau_sujet": <true si le message change de sujet, false s'il continue le fil>}"""


@dataclass
class Route:
    """Résultat de routage — jamais une donnée métier, seulement l'aiguillage."""
    intent: str
    params: dict[str, Any] = field(default_factory=dict)
    clarification: str | None = None
    confidence: float | None = None
    degraded: bool = False        # clé absente / API down → repli honnête à l'écran
    error: str | None = None      # JSON illisible après re-demande
    raw: str | None = None        # sortie brute du modèle (audit)
    nouveau_sujet: bool = True     # M111 — rupture de sujet : true = demande autonome (pas d'héritage)
    herites: dict[str, Any] = field(default_factory=dict)   # M111 — params VENUS du fil (récap les nomme)


def _extract_json(text: str) -> dict | None:
    """Le réel enrobe parfois en ```json … ``` ; le stub non. Extraction robuste."""
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.removeprefix("json").strip()
    # tolère du texte autour d'un objet unique
    if not raw.startswith("{"):
        a, b = raw.find("{"), raw.rfind("}")
        if a == -1 or b == -1 or b < a:
            return None
        raw = raw[a:b + 1]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _normalise(data: dict, prior_params: dict | None) -> Route | None:
    """Élague les clés parasites (jamais avalées, jamais inventées), valide par schéma,
    fusionne les paramètres antérieurs non contredits."""
    params = {k: v for k, v in (data.get("params") or {}).items() if k in PARAM_KEYS}
    clean = {"intent": data.get("intent"), "params": params}
    if data.get("clarification") is not None:
        clean["clarification"] = str(data["clarification"])[:240]
    if data.get("confidence") is not None:
        try:
            clean["confidence"] = float(data["confidence"])
        except (TypeError, ValueError):
            pass
    if data.get("nouveau_sujet") is not None:
        clean["nouveau_sujet"] = bool(data["nouveau_sujet"])
    try:
        validate(clean, ROUTE_SCHEMA)
    except ValidationError:
        return None
    # M111 — RUPTURE DE SUJET : on n'hérite du fil QUE si le tour est une continuation. Un tour
    # autonome (nouveau_sujet) part de SES seuls paramètres — fini le « ≥ 20000 m² hérité » appliqué
    # à une question sans rapport (le compte servi retombe juste). En continuation, l'héritage est
    # tracé (`herites`) pour que le récap le NOMME (un héritage dit ≠ une contamination, M109/M111).
    # Défaut prudent (modèle qui omet le champ) : HÉRITER (false) — protège la clarification
    # (« en cas de doute, laisse hériter », mandat M111) ; un fil neuf n'a de toute façon rien à
    # hériter. Le modèle met true pour les vrais nouveaux sujets (mesuré fiable, gate S4/S5).
    nouveau = clean.get("nouveau_sujet", False)
    tour = {k: v for k, v in params.items() if v is not None and k in PARAM_KEYS}
    herites: dict[str, Any] = {}
    if nouveau:
        merged = tour
    else:
        merged = {k: v for k, v in (prior_params or {}).items() if k in PARAM_KEYS and v is not None}
        herites = {k: v for k, v in merged.items() if k not in tour}   # ce qui vient du fil, pas du tour
        merged.update(tour)                                            # le tour courant prime (jamais une somme)
    return Route(intent=clean["intent"], params=merged, clarification=clean.get("clarification"),
                 confidence=clean.get("confidence"), nouveau_sujet=nouveau, herites=herites)


def classify(db: Session | None, message: str, *, history: list[dict] | None = None,
             prior_params: dict | None = None, contexte: dict | None = None) -> Route:
    """Classe `message`. `history` = tours précédents [{role, content}] (session). `prior_params` =
    paramètres déjà extraits à conserver (correction/héritage). `contexte` = {idu|selection} des
    surfaces embarquées (Phase 5). Une re-demande si JSON invalide, puis erreur honnête."""
    hist = [{"role": str(m.get("role", "user")), "content": str(m.get("content", ""))[:600]}
            for m in (history or [])[-HISTORIQUE_TOURS:]]
    payload: dict[str, Any] = {"message": message}
    if contexte:
        payload["contexte"] = contexte
    if prior_params:
        payload["parametres_connus"] = {k: v for k, v in prior_params.items() if v is not None}

    res = core.complete(db, kind="copilote-route", model=core.MODEL_FACTUAL, max_tokens=400,
                        system=ROUTER_SYSTEM, history=hist, context=payload)
    if res.degraded:
        return Route(intent="", degraded=True, error=res.reason or "no_key")
    data = _extract_json(res.text)
    route = _normalise(data, prior_params) if data else None
    if route is None:
        # une re-demande, plus explicite — puis erreur honnête
        res2 = core.complete(db, kind="copilote-route-retry", model=core.MODEL_FACTUAL, max_tokens=400,
                             system=ROUTER_SYSTEM + "\n\nRÉPONDS UNIQUEMENT L'OBJET JSON, sans aucun autre texte.",
                             history=hist, context=payload)
        data2 = _extract_json(res2.text)
        route = _normalise(data2, prior_params) if data2 else None
        if route is None:
            return Route(intent="", error="json_invalide", raw=(res.text or "")[:200])
    route.raw = (res.text or "")[:400]
    return route
