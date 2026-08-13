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
    {"nom": "compter_parcelles", "desc": "Compter des parcelles selon commune, surface (min/max en m²), "
     "tier (brûlante / chaude / opportunités), et/ou détention par une personne morale.",
     "params": {"commune": "str", "surface_min": "int m²", "surface_max": "int m²",
                "tier": "brulante|chaude|opportunites", "personne_morale": "bool"}},
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
  nom/SIREN de société → q).
- « Combien de permis (accordés) à X » → outil delais_instruction (il porte AUSSI le nombre de permis).
- REFUS (mets "tool":null et "refus" à la bonne valeur, "args":{{}}) :
  · "proprietaire_pp" : on demande l'identité/nom/adresse du PROPRIÉTAIRE d'une parcelle (personne
    physique — donnée non ouverte). NB : « quelles parcelles possède [société] » n'est PAS un refus
    (c'est parcelles_par_entreprise).
  · "projection" : on demande une valeur/évolution FUTURE (« dans 10 ans », « l'an prochain », « va
    monter »). LABUSE ne projette pas.
  · "aucun_outil" : aucun outil ci-dessus ne couvre la demande (ex. divisibilité d'UNE parcelle).
SORTIE : {{"tool": <nom|null>, "args": {{...}}, "refus": <"proprietaire_pp"|"projection"|"aucun_outil"|null>}}"""

FORMULE_SYSTEM = """Tu es le copilote foncier de LABUSE. Formule une réponse en français, brève et claire, à la
question du client, UNIQUEMENT à partir du RÉSULTAT D'OUTIL fourni (JSON). Règles STRICTES :
- N'invente AUCUN chiffre : tout nombre de ta réponse doit apparaître dans le résultat. Si une valeur
  manque, dis-le, ne la devine pas.
- Cite la source entre parenthèses à la fin (champ "source"), avec le millésime s'il est fourni.
- Si le résultat porte une "reserve" (couverture partielle), INCLUS-la fidèlement — ne la tais jamais.
- Pas de conseil juridique, pas de projection, pas de superlatif. Le ton est sobre et honnête.
Réponds seulement la réponse au client, sans préambule ni balises."""


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


def _anti_invention(prose: str, res) -> bool:
    """Vrai si tout nombre de la prose est justifié par le résultat (tolérance d'arrondi)."""
    autor = _valeurs_autorisees(res)
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
    return {"tool": data.get("tool"), "args": data.get("args") or {}, "refus": data.get("refus")}


# coercition des args du modèle vers les kwargs typés de chaque outil
_ARG_SPEC = {
    "compter_parcelles": {"commune": str, "surface_min": int, "surface_max": int, "tier": str,
                          "personne_morale": bool},
    "parcelles_par_entreprise": {"q": str},
    "fiche_parcelle": {"idu": str},
    "stats_commune": {"commune": str},
    "delais_instruction": {"commune": str},
    "marche": {"commune": str},
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


def _formuler(db: Session, message: str, res) -> str:
    payload = {"question": message, "outil": res.tool, "resultat": res.data,
               "valeur": res.valeur, "source": res.source, "millesime": res.millesime,
               "reserve": res.reserve if res.partiel else None}
    out = core.complete(db, kind="copilote-formule", model=core.MODEL_REASONING, max_tokens=350,
                        system=FORMULE_SYSTEM, context=payload)
    prose = (out.text or "").strip()
    if out.degraded or not prose or not _anti_invention(prose, res):
        # gabarit sourcé (jamais l'affirmation douteuse) — inclut la réserve si partielle
        base = (f"{res.valeur}" if res.valeur is not None
                else json.dumps(res.data, ensure_ascii=False, default=str))
        txt = f"{base} ({res.source}{' · ' + res.millesime if res.millesime else ''})."
        if res.partiel and res.reserve:
            txt += " " + res.reserve
        return txt
    return prose


def answer(db: Session, message: str, history: list[dict] | None = None,
           contexte: dict | None = None) -> dict:
    """Point d'entrée unique du Copilote v2 (API brute Phase 1). Retourne un dict prêt à rendre."""
    route = classify(db, message, history=history, contexte=contexte)
    if route.degraded:
        return _reply(ERREUR_INFRA, None, degraded=True)
    intent = route.intent
    params = route.params
    # §5 Copilote EMBARQUÉ : le contexte visible (la parcelle / la sélection) EST le contexte du
    # Copilote. « ce prix est-il correct ? » sur une fiche part en VERIFICATION sans retaper l'IDU.
    if contexte:
        if contexte.get("idu") and not params.get("idu"):
            params["idu"] = contexte["idu"]
        if contexte.get("selection") and not params.get("selection"):
            params["selection"] = contexte["selection"]

    if route.clarification and intent not in ("HORS_SUJET",):
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
            return _sans_outil(db, message, params, intent)
        tool = sel["tool"]
        if tool not in OUTILS:
            return _sans_outil(db, message, params, intent)
        res = OUTILS[tool](db, **_clean_args(tool, sel.get("args") or {}))
        if not res.ok:
            return _sans_outil(db, message, params, intent, motif=res.refus)
        text = _formuler(db, message, res)
        return _reply(text, intent, refus=None, tool=tool, sources=[res.source],
                      partiel=res.partiel)

    if intent == "OUTIL":
        return _outil(db, message, params)

    if intent == "VERIFICATION":
        from .missions_lourdes import verification
        return verification(db, params)

    if intent == "PROJET":
        # la fiche est préparée ici ; l'ÉCRITURE RÉELLE (API projets) est faite par l'endpoint /ask
        # (il a le compte). Doctrine : quand le Copilote dit « c'est fait », la chose EST faite.
        from .missions_lourdes import preparer_projet
        return _reply("Création du projet…", intent, _action={"type": "projet", **preparer_projet(params, message)})

    if intent == "VEILLE":
        from .missions_lourdes import preparer_veille
        return preparer_veille(db, params, message)

    # RECHERCHE → intercepté par le dispatch frontend (run M26-A)
    return _reply(f"(Mission {intent} — construite dans une phase ultérieure de M78.)", intent,
                  en_construction=True)


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
    (("procedure plu", "revision plu", "sursis a statuer"), ("verif-procedure", "Vérif procédure PLU", "idu")),
    (("due diligence", "controle avant achat", "avant d'acheter"), ("duediligence", "Contrôle avant achat", "idu")),
    (("servitude",), ("o5-servitudes", "Servitudes invisibles", "idu")),
    (("remonter le temps", "evolution dans le temps", "en 1950", "historique du site"),
     ("temps", "Remonter le temps", "idu")),
]
_SANS_OUTIL_KW = ("divis", "decoup", "lotir", "detacher un lot")

from .outils import _fold_py  # accent-fold (réutilisé)


def _match_outil(message: str):
    m = _fold_py(message.lower())
    for kws, cible in _OUTIL_MAP:
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
    txt = ("Je ne tranche pas la divisibilité d'une parcelle : elle dépend d'abord du règlement de la "
           "zone — surface minimale de terrain, accès, emprise au sol.")
    if idu and surface:
        txt += (f" Cette parcelle mesure {surface} m²" + (f" en zone {zone}" if zone else "")
                + (f" à {commune}" if commune else "") + ".")
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
