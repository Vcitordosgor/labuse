"""M78 · 1b/1c — COUCHE DE RÉPONSE. Le client écrit, LABUSE instruit.

Pipeline : routeur (intention) → aiguillage. Pour une QUESTION : le modèle CHOISIT un outil + des
paramètres typés (jamais du SQL), le serveur exécute, le modèle FORMULE depuis le résultat en citant
l'outil. Les cinq issues de la doctrine (RAPPORT_M78) sont appliquées ici. Refus = TEMPLATES
déterministes (le ton d'un refus se gagne : on ne l'improvise pas). Routeur sur haiku (M113·Ph0),
sélection + formulation sur sonnet.

M113 · Phase 2 — les CHIPS de contexte : le client choisit d'abord CE qu'il veut faire, puis écrit.
Le scénario est connu AVANT de lire le message → classify est court-circuité (web) ou réduit à
l'extraction de paramètres, intent FORCÉ. L'anti-invention s'applique à l'IDENTIQUE sur la voie chip
(extraction vérifiée, chiffres à l'oracle, critères non appliqués dits — M109). Le court-circuit du
routage ne court-circuite JAMAIS le verrou. Sans chip : texte libre → routeur (comportement M112).

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


def _et_fr(items: list[str]) -> str:
    """« a », « b » et « c » — pour nommer les critères non appliqués dans l'aveu."""
    qs = [f"« {x} »" for x in items]
    return qs[0] if len(qs) == 1 else " et ".join([", ".join(qs[:-1]), qs[-1]])


def _reply_compte(db: Session, message: str, res, faits_fil, intent: str) -> dict:
    """Réponse d'un comptage : la prose + le registre + la PORTE CARTE FILTRÉE (M112 P2.1) —
    partagée par la QUESTION « combien de… » et la demande VISUELLE « montre-moi les… »."""
    from . import registre_faits
    cna = res.criteres_non_appliques or []
    labels = (res.data or {}).get("criteres_labels") or []
    # M116 · D11 — l'AVEU D'ABORD, jamais le COMPTE non filtré présenté comme la réponse. Scopé à
    # `compter_parcelles` : c'est là qu'un critère lâché sans autre filtre transforme le résultat en
    # total trompeur. Les autres outils (délai, taux, patrimoine…) servent leur chiffre AVEC leur
    # réserve (M109 via _formuler) — leur nombre reste une vraie réponse, pas un total non filtré.
    if cna and res.tool == "compter_parcelles":
        aveu = "Le critère " + _et_fr(cna) + (" n'est pas encore interrogeable ici."
                                              if len(cna) == 1 else " ne sont pas encore interrogeables ici.")
        if not labels:
            # aucun critère applicable n'a filtré : servir le total serait TROMPEUR → pas de chiffre,
            # une voie (M112) plutôt qu'un mur. Pas de porte carte (elle montrerait le non-filtré).
            voie = (" Je peux compter et croiser sur d'autres critères — surface, zonage PLU, procédure "
                    "judiciaire, friche, copropriété, personne morale… Reformulez avec l'un d'eux.")
            return _reply(aveu + voie, intent, refus="critere_non_applicable", tool=res.tool,
                          criteres_non_appliques=cna, criteres_appliques=labels)
        # des critères applicables ONT filtré : l'aveu d'abord, PUIS le sous-compte (qui les porte).
        commune = (res.data or {}).get("criteres", {}).get("commune")
        corps = (f" Sur les critères que je sais appliquer ({', '.join(labels)}), "
                 f"{res.valeur} parcelle(s)" + (f" à {commune}" if commune else "") + f" ({res.source}).")
        return _reply(aveu + corps, intent, refus=None, tool=res.tool, sources=[res.source],
                      criteres_non_appliques=cna, criteres_appliques=labels,
                      carte_filtre=_carte_depuis_compte(res),
                      _faits_tour=registre_faits.extraire_faits(res))
    text = _formuler(db, message, res, faits_fil)
    return _reply(text, intent, refus=None, tool=res.tool, sources=[res.source],
                  partiel=res.partiel, criteres_non_appliques=cna,
                  criteres_appliques=labels, carte_filtre=_carte_depuis_compte(res),
                  _faits_tour=registre_faits.extraire_faits(res))


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


# M113 · Phase 2 — REGISTRE des chips de contexte. Servi par le serveur (GET /scenarios), jamais en
# dur au front. `intent` = l'intent FORCÉ quand le chip est choisi ; `placeholder` = la zone de texte
# adaptée au scénario (étape 2). L'ordre est celui d'affichage. Les noms sont ceux arbitrés par Vic.
SCENARIOS: dict[str, dict] = {
    "donnees": {"libelle": "Interroger mes données", "intent": "QUESTION",
                "placeholder": "Combien de parcelles, quel prix, quel délai… à quelle commune ?"},
    "parcelle": {"libelle": "Trouver une parcelle", "intent": "RECHERCHE",
                 "placeholder": "Ex. 15 logements à Saint-Paul, ≥ 2000 m², détenues par des personnes morales…"},
    "projet": {"libelle": "Créer un projet", "intent": "PROJET",
               "placeholder": "Ex. résidence 12 lots à Bras-Panon (facultatif — le formulaire s'ouvre)"},
    "web": {"libelle": "Rechercher sur le web", "intent": "QUESTION",
            "placeholder": "Ex. qui est le maire de Saint-Denis ?"},
    "surveillance": {"libelle": "Mettre sous surveillance", "intent": "VEILLE",
                     "placeholder": "Ex. les nouveaux permis à Saint-Paul"},
    "outil": {"libelle": "Ouvrir un outil", "intent": "OUTIL",
              "placeholder": "Ex. le baromètre du foncier, écrire au propriétaire, la calculette foncière…"},
}


def scenarios_publies() -> list[dict]:
    """Les chips à servir au front (clé + libellé + placeholder). Point unique."""
    return [{"cle": k, "libelle": v["libelle"], "placeholder": v["placeholder"]} for k, v in SCENARIOS.items()]


def _reply_web(db: Session, message: str) -> dict:
    """Chip « Rechercher sur le web » — classify COURT-CIRCUITÉ (le scénario est connu) : la question
    verbatim part au web. Gain de latence majeur (ni route, ni sélection). Marquage web NON négociable,
    jamais Sourcé/Estimé. Gabarit COURT (Phase 4) piloté par WEB_SYSTEM."""
    res = OUTILS["recherche_web"](db, question=message)
    if not res.ok:
        telemetrie.refus(db, "web_rien_trouve", message, "QUESTION")
        return _reply("Je n'ai rien trouvé de fiable sur le web pour cette demande. Reformulez-la, "
                      "ou posez-la sur les données LABUSE.", "QUESTION", refus="web_rien_trouve", scenario="web")
    telemetrie.web(db, message, res.data.get("domaines", []))
    d = res.data
    marque = f"Source : web · {d['domaines'][0]} · consulté le {d['date']}"
    return _reply(f"{d['reponse']}\n\n{marque}", "QUESTION", tool="recherche_web", web=True,
                  sources=d["domaines"], scenario="web")


def _projet_form(db: Session, message: str, params: dict | None = None) -> dict:
    """M113 · Phase 3 — « Créer un projet » : ouvre le PARCOURS GUIDÉ, JAMAIS une création directe (ni
    par le chip, ni par le texte libre classé PROJET). Le formulaire s'ouvre PRÉREMPLI de ce qui est
    compris (« 15 logements à Saint-Paul ») — l'utilisateur vérifie, complète, valide. Le formulaire
    protège par construction (commune du référentiel, création explicite). `params` fournis → pas de
    second appel modèle (le routeur les a déjà extraits)."""
    p = params
    if p is None and message and message.strip():
        r = classify(db, message)      # extraction de paramètres (haiku) — aucune création
        p = None if r.degraded else (r.params or {})
    prefill = {k: (p or {}).get(k) for k in ("commune", "programme_logements", "budget_eur")
               if (p or {}).get(k) is not None}
    return _reply("Ouvrons votre projet — quelques champs à confirmer avant de le créer.", "PROJET",
                  projet_form={"prefill": prefill}, scenario="projet")


def answer(db: Session, message: str, history: list[dict] | None = None,
           contexte: dict | None = None, confirme: bool = False,
           prior_params: dict | None = None, faits_fil: list[dict] | None = None,
           scenario: str | None = None) -> dict:
    """Point d'entrée unique du Copilote v2. Retourne un dict prêt à rendre. `confirme=True` : le client
    a validé le récap (§M78-bis) → on produit la mission lourde (VERIFICATION) au lieu du récap.

    M113 · Phase 2 — `scenario` (chip choisi) FORCE le scénario : `web` court-circuite classify (la
    question verbatim au web) ; `projet` ouvre le parcours guidé (aucune création directe) ; les autres
    passent par classify RÉDUIT à l'extraction de paramètres (haiku) avec l'intent FORCÉ. Le verrou
    anti-invention, le récap M109 et les gardes restent IDENTIQUES à la voie texte libre.

    M102-B1 — `history`/`prior_params` viennent du FIL persisté (rechargés par l'endpoint depuis
    conversation_id) : le tour est interprété DANS son contexte (une réponse à une clarification
    hérite de l'intention et des paramètres — le prompt routeur est conçu pour, gate 45 msgs).
    La réponse porte `_route` (intent + params du tour, jamais servi au client — poppé par
    l'endpoint) pour alimenter le contexte du tour SUIVANT. AUCUNE reprise de chiffre d'un tour
    antérieur ici : une clarification apporte des PARAMÈTRES, pas des faits — l'anti-invention
    reste vérifiée contre l'outil du tour courant (le registre de faits est le mandat B3)."""
    # M113 — les deux scénarios qui NE passent pas par classify : le web (court-circuit total) et le
    # projet (parcours guidé, jamais de création directe). Les autres forcent l'intent après classify.
    if scenario == "web":
        return _reply_web(db, message)
    if scenario == "projet":
        return _projet_form(db, message)
    route = classify(db, message, history=history, contexte=contexte, prior_params=prior_params)
    if scenario and scenario in SCENARIOS and not route.degraded:
        # le chip lève l'ambiguïté d'INTENTION : intent forcé, clarification d'intention retirée. La
        # clarification de PARAMÈTRE (commune manquante…) reste, produite en aval par l'outil/le récap.
        route.intent = SCENARIOS[scenario]["intent"]
        route.clarification = None
    if route.degraded:
        return _reply(ERREUR_INFRA, None, degraded=True)
    rep = _answer_with_route(db, message, route, contexte=contexte, confirme=confirme,
                             faits_fil=faits_fil, history=history)
    if scenario:
        rep.setdefault("scenario", scenario)   # M113 — le gabarit de réponse (Phase 4) suit le scénario
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

    # M110/M112 — CONCEPTS-OUTILS du registre reconnus AVANT tout (même si le routeur a deviné une
    # clarification, une recherche vague ou un HORS_SUJET) : « bascules du mois », « où investir »,
    # « parcelles fantômes »… routent vers l'OUTIL (porte cliquable, mécanique M102). Les outils
    # EXISTENT — un mot-clé spécifique ne matche jamais un vrai hors-sujet.
    concept = _match_concept(message)
    if concept:
        module, label = concept
        return _reply(f"Je peux ouvrir l'outil {label}.", "OUTIL", porte=module, prefill=None)

    # M112 P2.3 — DOCUMENTS : « fais-moi le dossier banquier de cette parcelle » → porte vers
    # l'export, IDU résolu (params ou contexte embarqué). Sans IDU → on demande (champ M107).
    doc = _match_document(message)
    if doc:
        kind, label = doc
        idu = params.get("idu") or (contexte or {}).get("idu")
        if not idu:
            return _reply(f"Pour éditer le {label}, donnez-moi l'IDU de la parcelle (14 caractères).",
                          "OUTIL", clarification=True)
        return _reply(f"Je peux éditer le {label} de la parcelle {idu}.", "OUTIL",
                      document={"kind": kind, "idu": idu, "libelle": label})

    # §M78-bis 2d : RECHERCHE/VERIFICATION ne court-circuitent PAS sur la clarification du routeur — elle
    # ALIMENTE leur récap (qui pose une clarification COURTE, ≤ 4 options). Pas de double question.
    # M116 · D3 — PROJET non plus : l'intention PROJET doit OUVRIR le formulaire guidé (prérempli de ce
    # qui est compris, même vide), en texte libre comme au chip — c'est ce que M113 promet. Avant, une
    # clarification du routeur pré-emptait `_projet_form` et ré-servait l'ancienne question-texte.
    if route.clarification and intent not in ("HORS_SUJET", "RECHERCHE", "VERIFICATION", "PROJET"):
        return _reply(route.clarification, intent, clarification=True)

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
            # M116 · D2 — une question de COMPTAGE à qui il manque juste la commune : demander la
            # commune (précision, son champ = le fil), jamais un refus « aucun outil ». La division
            # garde sa voie (règlement) et n'est pas interceptée ici.
            m = _fold_py(message.lower())
            compte = ("combien" in m or "nombre de" in m) and "parcelle" in m
            if compte and not params.get("commune") and not any(k in m for k in _SANS_OUTIL_KW):
                telemetrie.refus(db, "manque_commune", message, intent)
                return _reply("Sur quelle commune ? Je compte les parcelles commune par commune.",
                              intent, clarification=True)
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
        return _reply_compte(db, message, res, faits_fil, intent)

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
        # M113 · Phase 3 — le Copilote ne CRÉE PLUS directement (fin du « c'est fait » sans garde-fou) :
        # le parcours guidé s'ouvre, prérempli de ce que le routeur a compris. La création réelle passe
        # par le formulaire (valeurs contrôlées, commune du référentiel, action explicite).
        return _projet_form(db, message, params)

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
        # M112 P2.1 — demande VISUELLE sans programme (« montre-moi les friches à Saint-Paul »,
        # « où sont les parcelles en procédure ») : la réponse naturelle est une CARTE, pas une
        # mission de recherche. On route vers le comptage facette (qui porte la carte filtrée).
        # Une vraie mission (avec programme/budget) n'est PAS interceptée.
        if _veut_carte(message) and not route.params.get("programme_logements") \
                and not route.params.get("budget_eur"):
            sel = _select_tool(db, message, route.params)
            if sel.get("tool") == "compter_parcelles":
                res = OUTILS["compter_parcelles"](db, **_clean_args("compter_parcelles", sel.get("args") or {}))
                res.criteres_non_appliques = sel.get("criteres_non_appliques") or []
                if res.ok:
                    return _reply_compte(db, message, res, faits_fil, "QUESTION")
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
    # M110 — fantôme / bailleur
    (("parcelle fantome", "parcelles fantomes", "parcelles fantome", "parcelle fantome",
      "bien fantome", "biens fantomes"), ("fantome", "Parcelles fantômes")),
    # NB : le concept-outil vise le FONCIER/PATRIMOINE des bailleurs — un mot foncier/parcelle est
    # REQUIS. PAS « bailleurs sociaux » nu (= « qui gère le financement des bailleurs » → web,
    # « taux de logements sociaux » → stats SRU). Piège écarté (accueil #5, audit M108).
    (("parcelles des bailleurs", "parcelles de bailleur", "foncier des bailleurs", "foncier bailleur",
      "patrimoine des bailleurs", "parc social bailleur", "mode bailleur", "foncier social bailleur"),
     ("bailleur", "Bailleurs sociaux")),
    # M112 — les 11 outils invisibles du registre (mots-clés SPÉCIFIQUES, sans collision avec le
    # comptage/marché/délais : jamais « permis » nu, jamais « renouvellement » nu, jamais « marché »).
    # Marché & veille d'abord (valeur d'usage), reconnaissance depuis les libellés servis du registre.
    (("comparateur de communes", "comparer les communes", "comparer des communes", "ou investir",
      "quelle commune investir", "quelle commune pour investir", "meilleures communes ou investir"),
     ("o6-comparateur", "Comparateur de communes")),
    (("barometre", "état du marché foncier", "etat du marche foncier", "barometre foncier"),
     ("barometre", "Baromètre foncier")),
    (("radar permis", "qui construit quoi", "qui construit a", "qui construit dans",
      "quels permis dans la commune"), ("permis", "Radar permis")),
    (("promesses mortes", "permis jamais sortis", "permis jamais construits",
      "permis anciens jamais", "permis abandonnes"), ("promesses", "Promesses mortes")),
    (("simulateur zan", "artificialisation", "contrainte d'artificialisation", "contrainte zan",
      "zan de la commune", "objectif zan"), ("zan", "Simulateur ZAN")),
    (("rarete du foncier", "rarete foncier", "le foncier se rarefie", "ou le foncier se rarefie",
      "combien de constructible reste"), ("o9-rarete", "Rareté du foncier")),
    (("potentiel de renouvellement", "renouvellement du territoire", "outil renouvellement",
      "vue renouvellement du"), ("renouvellement", "Renouvellement")),
    (("changement de plu", "si cette zone passait", "zone passait constructible",
      "si cette zone devenait constructible", "zone devenait constructible",
      "prospective de territoire", "simuler un plu", "simuler un changement de zonage"),
     ("simulplu", "Changement PLU")),
    (("quoi de neuf", "les bascules du mois", "bascules du secteur", "bascules du mois",
      "evenements du secteur", "qui a bascule ce mois"), ("o10-bascules", "Quoi de neuf")),
    (("suivi de secteur", "suivre le secteur", "portefeuille de secteur", "suivre un secteur comme"),
     ("o7-carnet", "Suivi de secteur")),
    (("scorer une adresse", "scorer un bien", "seconde opinion avant d'offrir", "avis sur cette adresse",
      "noter une adresse"), ("scoreur-adresse", "Scorer une adresse")),
]

# M112 P2.3 — les 4 DOCUMENTS du registre (porte vers l'export, IDU résolu). « banquier » avant
# « dossier » nu (le plus spécifique gagne). Chaque kind = une URL PDF connue du front.
_DOC_MAP = [
    (("dossier banquier", "dossier bancaire", "dossier pour la banque", "dossier pour le banquier",
      "dossier de financement"), ("dossier-banquier", "dossier banquier")),
    (("argumentaire", "argument de negociation", "argumentaire de negociation",
      "lettre de negociation"), ("argumentaire", "argumentaire de négociation")),
    (("pre-dossier", "predossier", "pre dossier", "fiche flash", "note flash"),
     ("pre-dossier", "pré-dossier")),
    (("dossier complet", "le dossier", "faire le dossier", "editer le dossier", "sors le dossier",
      "monte le dossier", "monter le dossier"), ("dossier", "dossier complet")),
]

from .outils import _fold_py  # accent-fold (réutilisé)


def _match_document(message: str):
    """(kind, libellé) si la demande vise un DOCUMENT du registre, sinon None."""
    m = _fold_py(message.lower())
    for kws, cible in _DOC_MAP:
        if any(k in m for k in kws):
            return cible
    return None


# M112 P2.1 — CARTE FILTRÉE. Traducteur critères facette (compter_parcelles) → filtres du front
# (le même point unique : la facette). `carte_filtre` = {commune, filtres, libelle} → le front pose
# setCommune + setFilters + vue carte. Aucune requête parallèle : ce sont les critères DÉJÀ comptés.
def _criteres_vers_filtres(crit: dict) -> dict:
    f: dict[str, Any] = {}
    if crit.get("surface_min") is not None:
        f["surfaceMin"] = crit["surface_min"]
    if crit.get("surface_max") is not None:
        f["surfaceMax"] = crit["surface_max"]
    if crit.get("tier"):
        f["tiers"] = [t for t in str(crit["tier"]).split(",") if t]
    if crit.get("personne_morale"):
        f["personneMorale"] = True
    if crit.get("evenement"):
        f["evenement"] = True
    sig = [s for s in str(crit.get("signaux") or "").split(",") if s]
    if crit.get("defisc") and "defisc" not in sig:
        sig.append("defisc")
    if sig:
        f["signaux"] = sig
    if crit.get("adresse_absente"):
        f["adresseAbsente"] = True
    if crit.get("copro"):
        f["copro"] = [crit["copro"]]
    if crit.get("renouvellement"):
        f["renouvellement"] = True
    if crit.get("zonage"):
        f["zonagePlu"] = [z for z in str(crit["zonage"]).split(",") if z]
    return f


def _carte_depuis_compte(res) -> dict | None:
    """La porte CARTE FILTRÉE d'un ToolResult compter_parcelles (commune + filtres facette)."""
    if res.tool != "compter_parcelles":
        return None
    crit = (res.data or {}).get("criteres") or {}
    commune = crit.get("commune")
    filtres = _criteres_vers_filtres(crit)
    if not commune and not filtres:
        return None
    labs = (res.data or {}).get("criteres_labels") or []
    libelle = ("les parcelles " + ", ".join(labs) if labs else "les parcelles") + (f" à {commune}" if commune else "")
    return {"commune": commune, "filtres": filtres, "libelle": libelle}


# M112 P2.1 — la demande VISUELLE (« montre-moi », « où sont », « sur la carte ») dont la réponse
# naturelle est une carte, pas un nombre : on route vers le comptage facette (qui porte la carte).
_CARTE_KW = ("montre", "montre-moi", "montre moi", "affiche", "ou sont", "où sont", "sur la carte",
             "sur une carte", "localise", "visualise", "voir sur la carte", "cartographie")


def _veut_carte(message: str) -> bool:
    m = _fold_py(message.lower())
    return any(k in m for k in ("montre", "affiche", "ou sont", "sur la carte", "sur une carte",
                                "localise", "visualise", "cartographie"))


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
        m = _fold_py(message.lower())
        if any(k in m for k in _SANS_OUTIL_KW):     # division/découpe : renvoyer au règlement, pas la liste
            return _sans_outil(db, message, params, "OUTIL")
        # M116 · D4 — intention explicite « ouvrir un outil » sans outil précis → proposer la LISTE des
        # outils (une voie cliquable, M112), jamais un refus sec « je n'ai pas d'outil dédié ».
        telemetrie.refus(db, "outil_a_choisir", message, "OUTIL")
        return _reply("Dites-moi ce que vous voulez faire, ou choisissez parmi les outils d'analyse.",
                      "OUTIL", outils_liste=True)
    module, label, prefill = cible
    txt = f"Je peux ouvrir l'outil {label}"
    if idu and prefill in ("parcelPrefill", "calcPrefill", "idu", "pluPrefill"):
        txt += f", pré-rempli avec la parcelle {idu}."
    else:
        txt += "."
    return _reply(txt, "OUTIL", porte=module, prefill=prefill,
                  prefill_idu=idu if prefill in ("parcelPrefill", "calcPrefill", "idu") else None)
