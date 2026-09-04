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
    {"nom": "compter_parcelles", "desc": "Compter des parcelles d'une commune (ou de TOUTE L'ÎLE si commune "
     "absente) selon des critères de la facette : surface (min/max en m²), tier (brûlante/chaude/RÉSERVE "
     "FONCIÈRE/opportunités), détention par une personne morale, événement rouge, signaux de vie (procédure "
     "judiciaire/BODACC, friche, cession, permis actif/caduc, défiscalisation, terrain nu de société), "
     "adresse absente, copropriété, renouvellement urbain, zonage PLU (U/AU/A/N). « réserves foncières » "
     "→ tier reserve_fonciere ; « sur toute l'île / partout » → commune absente.",
     "params": {"commune": "str (absent = TOUTE L'ÎLE)", "surface_min": "int m²", "surface_max": "int m²",
                "tier": "brulante|chaude|reserve_fonciere|opportunites", "personne_morale": "bool",
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
    {"nom": "delais_instruction", "desc": "DÉLAI médian d'instruction d'une commune (dépôt→autorisation, "
     "Sitadel). Pour « quel délai / combien de temps / vélocité d'instruction ».", "params": {"commune": "str"}},
    {"nom": "compter_permis", "desc": "NOMBRE de permis accordés d'une commune sur une fenêtre de N mois "
     "(défaut 24). Pour « combien de permis (accordés/délivrés) à X », « permis sur 24 mois ». C'est un "
     "COMPTE, pas un délai.", "params": {"commune": "str", "mois": "int (défaut 24)"}},
    {"nom": "marche", "desc": "Marché immobilier d'une commune : prix de l'ANCIEN (prix_ancien_median), "
     "terrain nu (prix_terrain_nu_par_zone), NEUF (prix_sortie_neuf), tendance (tendance_12m), loyer "
     "(loyer_median). Les grandeurs sont NOMMÉES dans data.valeurs — sers celle demandée.",
     "params": {"commune": "str"}},
    {"nom": "compter_piscines", "desc": "Compter les PISCINES détectées (île entière ou une commune) — "
     "détection ortho/IA gelée. « combien de piscines à X », « piscines détectées ».",
     "params": {"commune": "str (absent = toute l'île)"}},
    {"nom": "destination_zone", "desc": "PEUT-ON OUVRIR/IMPLANTER une activité (restaurant, hôtel, "
     "commerce, bureau, entrepôt, usine…) sur une parcelle (IDU) ou dans une zone PLU d'une commune ? "
     "Verdict autorisé / sous condition / interdit, sourcé au règlement PLU (article, page, millésime), "
     "CDAC incluse. « peut-on ouvrir un restaurant sur cette parcelle », « le commerce est-il autorisé "
     "en zone UE à Saint-Denis ».",
     "params": {"idu": "str 14 car. (si parcelle)", "commune": "str (si zone donnée)",
                "zone": "str (code zone PLU, ex. UE)", "activite": "l'activité, verbatim"}},
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
- « Combien de permis (accordés/délivrés) à X » → outil compter_permis (le COMPTE ; extrais `mois` si
  une fenêtre est dite : « sur 24 mois » → mois=24, « sur 12 mois » → mois=12). « Quel DÉLAI d'instruction
  à X » → delais_instruction. Ne CONFONDS PAS le compte (compter_permis) et le délai (delais_instruction).
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
- GRANDEUR DEMANDÉE (multi-valeurs) : si le résultat porte `valeurs` (grandeurs nommées, ex. marché :
  prix_ancien_median, prix_terrain_nu_par_zone, prix_sortie_neuf, loyer_median, tendance_12m), sers CELLE
  que la question demande (« prix de l'ancien » → prix_ancien_median). Ne réponds « non disponible » QUE
  si la valeur demandée est absente/None — jamais si elle est présente sous une autre clé.
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
    res = core.complete(db, kind="copilote-select", model=core.model_for("copilote-select"), max_tokens=300,
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
    "compter_permis": {"commune": str, "mois": int},
    "marche": {"commune": str},
    "compter_piscines": {"commune": str},
    "destination_zone": {"idu": str, "commune": str, "zone": str, "activite": str},
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
    # DESTINATIONS-1 (X4.4) — le verdict destination voyage jusqu'au front : la PHRASE SOURCÉE
    # (servie telle quelle, jamais reformulée) + la porte « Étude de zone » préremplie (idu/commune/
    # zone/sous_destination). Motif prefill dédié (etudeZonePrefill), même grammaire que M22/PLU.
    extra: dict = {}
    if res.tool == "destination_zone" and isinstance(res.data, dict):
        extra = {"destination_phrase": res.data.get("phrase"),
                 "porte": "etude-zone", "prefill": "etudeZonePrefill",
                 "prefill_etude_zone": res.data.get("prefill")}
    return _reply(text, intent, refus=None, tool=res.tool, sources=[res.source],
                  partiel=res.partiel, criteres_non_appliques=cna,
                  criteres_appliques=labels, carte_filtre=_carte_depuis_compte(res),
                  _faits_tour=registre_faits.extraire_faits(res), **extra)


def _repli_lisible(res) -> str:
    """GB-015 — gabarit de repli (anti-invention échouée / prose vide / dégradé) : une phrase
    LISIBLE, JAMAIS le JSON brut de l'outil. Une valeur simple → « <valeur> (source) » ; un
    résultat multi-lignes ou un dict plat → ses champs en clair ; sinon une clarification honnête.
    Interdit absolu : `json.dumps(res.data)` à l'écran (payload technique au visage du client)."""
    src = (f" ({res.source}{' · ' + res.millesime if res.millesime else ''})") if res.source else ""
    if res.valeur is not None:
        return f"{res.valeur}{src}."
    data = res.data if isinstance(res.data, dict) else {}
    tete = f"{data['commune']} — " if data.get("commune") else ""
    # 1) résultat multi-lignes {cle/libelle, valeur} → en clair (c'est la forme qui fuyait : marché)
    lignes = data.get("lignes")
    if isinstance(lignes, list):
        bouts = [f"{str(l.get('cle') or l.get('libelle')).replace('_', ' ')} : {l.get('valeur')}"
                 for l in lignes if isinstance(l, dict) and l.get("valeur") is not None
                 and (l.get("cle") or l.get("libelle"))]
        if bouts:
            return tete + " · ".join(bouts[:6]) + src + "."
    # 2) dict plat de SCALAIRES (ex. stats commune) → clés lisibles ; jamais une structure imbriquée
    plats = [f"{str(k).replace('_', ' ')} : {v}" for k, v in data.items()
             if k != "commune" and isinstance(v, (int, float, str)) and not str(k).startswith("_")]
    if plats:
        return tete + " · ".join(plats[:6]) + src + "."
    # 3) rien d'exploitable en clair → clarification honnête, JAMAIS json.dumps(data)
    return ("Je n'ai pas de valeur unique à afficher ici — précisez ce que vous cherchez "
            "(un prix, un compte, un délai, un taux…).")


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
    out = core.complete(db, kind="copilote-formule", model=core.model_for("copilote-formule"), max_tokens=350,
                        system=FORMULE_SYSTEM, context=payload)
    prose = (out.text or "").strip()
    if out.degraded or not prose or not _anti_invention(prose, res, registre_faits.valeurs(faits_fil or [])):
        # GB-015 — gabarit sourcé LISIBLE (jamais l'affirmation douteuse NI le JSON brut) — inclut la
        # réserve si partielle. `_repli_lisible` garantit qu'aucun `json.dumps(data)` n'atteint l'écran.
        prose = _repli_lisible(res)
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
# M117 · Phase 2.1 — `sub` = le sous-titre de chaque intention (grille d'accueil, maquette DA v2),
# servi par le serveur. « {n} » dans le sous-titre outil = le compte des outils, substitué au front
# par MODULES.length (aucun nombre en dur — le registre des outils vit côté front).
# M118 — le Copilote resserré à 4 MISSIONS. Le reste (trouver/instruire, créer un projet, surveiller,
# ouvrir un outil, rédiger un courrier) quitte le chat et reçoit un REFUS avec voie cliquable.
# M133 — chaque mission porte un `exemple` : une VRAIE phrase que le client taperait, dans la
# formulation de cette mission. À l'accueil (v3) les 4 capacités deviennent du TEXTE (libellé +
# exemple entre guillemets), plus un menu de modes — le routeur comprend seul, rien à choisir.
# L'`intent` FORCÉ reste dans le registre (mécanisme M113 conservé pour les tests/API), mais
# l'accueil ne l'envoie plus (M133 : aucune intention forcée depuis l'écran d'accueil).
SCENARIOS: dict[str, dict] = {
    "donnees": {"libelle": "Trouver une donnée", "intent": "QUESTION", "sub": "Compter, filtrer, croiser",
                "placeholder": "Combien de parcelles, quel prix, quel délai… à quelle commune ?",
                # RETOURS-7 Z2 — exemple raccourci pour tenir sur UNE ligne dans la tuile d'accueil.
                "exemple": "Parcelles en procédure à Saint-Denis ?"},
    "web": {"libelle": "Renseigner par le web", "intent": "QUESTION", "sub": "Court, sourcé, daté",
            "placeholder": "Ex. qui est le maire de Saint-Denis ?",
            "exemple": "Qui est le maire de Saint-Benoît ?"},
    "expliquer": {"libelle": "Expliquer une notion", "intent": "EXPLIQUER", "sub": "AU, ZFANG, charge foncière…",
                  "placeholder": "Ex. qu'est-ce qu'une zone AU ? c'est quoi la charge foncière ?",
                  "exemple": "C'est quoi une zone AU stricte ?"},
    "preparer": {"libelle": "Préparer un script", "intent": "PREPARER", "sub": "Appel ou argumentaire",
                 "placeholder": "Ex. prépare un argumentaire pour aborder le propriétaire",
                 # RETOURS-7 Z2 — exemple raccourci pour tenir sur UNE ligne dans la tuile d'accueil.
                 "exemple": "Un argumentaire pour un propriétaire"},
}

# M133 · Accueil Copilote v3 — le HERO servi, jamais en dur au front (la promesse suit le produit :
# plus d'« instruit », mort en M118). Le placeholder est un exemple d'une VRAIE mission (donnée).
ACCUEIL: dict[str, str] = {
    "titre": "Posez votre question.",
    "sous_titre": "Réponse courte, sourcée, datée — La Réunion uniquement.",
    "placeholder": "Ex. combien de parcelles en procédure à Saint-Denis ?",
    "aide": "Le Copilote comprend ce que vous demandez — rien à choisir.",
}


def scenarios_publies() -> list[dict]:
    """Les missions à servir au front (clé + libellé + sous-titre + placeholder + exemple). Point unique."""
    return [{"cle": k, "libelle": v["libelle"], "sub": v["sub"],
             "placeholder": v["placeholder"], "exemple": v["exemple"]}
            for k, v in SCENARIOS.items()]


def accueil_publie() -> dict:
    """M133 — le hero de l'accueil (titre/sous-titre/placeholder/aide) + les 4 capacités en TEXTE
    (libellé + exemple réel). Servi, jamais en dur ; ne promet que ce que les 4 missions font."""
    return {**ACCUEIL,
            "capacites": [{"cle": k, "libelle": v["libelle"], "exemple": v["exemple"]}
                          for k, v in SCENARIOS.items()]}


def _reply_web(db: Session, message: str, history: list[dict] | None = None) -> dict:
    """Chip « Rechercher sur le web » — classify COURT-CIRCUITÉ (le scénario est connu) : la question
    verbatim part au web. Gain de latence majeur (ni route, ni sélection). Marquage web NON négociable,
    jamais Sourcé/Estimé. Gabarit COURT (D5) : ≤ 2 phrases via _deux_phrases.

    M117 · D9 — le fil est passé au web : un enchaînement (« et à Saint-Pierre ? ») se résout depuis
    le contexte, sans réintroduire classify (le gain de latence reste). Le modèle RÉSOUT la référence,
    il ne SOMME rien (cohérent M111 : le web répond une question, il n'hérite pas de paramètres)."""
    res = OUTILS["recherche_web"](db, question=message, history=history)
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
           scenario: str | None = None, prior_voie: str | None = None) -> dict:
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
        return _reply_web(db, message, history)
    # COPILOTE-REFONTE — TENUE DE POSITION : « t'es sûr ? » n'est PAS une nouvelle question. On MAINTIENT
    # la dernière réponse et on cite sa source (fait du registre) — pas de re-routage qui retournerait la
    # veste sans donnée nouvelle. Détecté avant classify (économise un appel modèle sur un méta-tour).
    # RÉSUMÉ du fil (« résume-moi ce qu'on s'est dit ») — déterministe, avant classify (0 modèle).
    if (history or faits_fil) and not scenario and _est_resume(message):
        rep = _resume_fil(history, faits_fil)
        rep["_route"] = {"intent": "QUESTION", "params": {}, "voie": prior_voie}
        return rep
    if (faits_fil or prior_voie) and not scenario and _est_mise_en_doute(message):
        rep = _tenue_position(faits_fil, prior_voie)
        # le fil GARDE son mode (une mise en doute ne change pas de voie) — prior_voie reporté.
        rep["_route"] = {"intent": rep.get("intent"), "params": {},
                         "voie": ("generale" if rep.get("general") else None) or prior_voie}
        return rep
    # GB-019 — MÉTA-TOURS adjacents, déterministes (0 appel modèle), AVANT classify :
    if not scenario:
        # (a) provenance : « d'où tu sors ce chiffre ? » → re-cite source+millésime du registre.
        if faits_fil and _est_provenance(message):
            rep = _citer_source(faits_fil)
            rep["_route"] = {"intent": "QUESTION", "params": {}, "voie": prior_voie}
            return rep
        # (b) capacités/limites : « t'as accès à mes emails ? » → réponse EXACTE sur ce qu'il sait faire.
        if _est_capacites(message):
            rep = _reply(_CAPACITE_TXT, "QUESTION", capacites=True)
            rep["_route"] = {"intent": "QUESTION", "params": {}, "voie": prior_voie}
            return rep
        # (c) calcul sur SES PROPRES chiffres : « calcule 3 % de 2 327 » → arithmétique déterministe.
        calc = _calcul_pct(message, faits_fil)
        if calc is not None:
            calc["_route"] = {"intent": "QUESTION", "params": {}, "voie": prior_voie}
            return calc
        # (d) anaphore SPATIALE : « et sa voisine ? » → clarification honnête (plusieurs mitoyennes),
        #     jamais re-servir la même parcelle (le contresens GB-019).
        if _est_voisine(message):
            rep = _reply("Une parcelle a PLUSIEURS voisines (mitoyennes) — je ne peux pas deviner "
                         "laquelle. Donnez-moi l'IDU de la parcelle qui vous intéresse, ou sélectionnez-la "
                         "sur la carte.", "QUESTION", clarification=True)
            rep["_route"] = {"intent": "QUESTION", "params": {}, "voie": prior_voie}
            return rep
    # GB-014 (Q24/Q25) — DÉICTIQUE VAGUE SANS ANTÉCÉDENT : le fil ne la résout pas → clarification courte
    # (déterministe, 0 appel modèle), jamais une réponse au hasard ni un hors-sujet. Un « et là-bas ? »
    # qui hérite d'une commune (prior_params) ou un message qui nomme son lieu ne tombe PAS ici.
    if not scenario:
        clarif = _clarif_anaphore(message, prior_params, contexte)
        if clarif:
            rep = _reply(clarif, "QUESTION", clarification=True)
            rep["_route"] = {"intent": "QUESTION", "params": {}, "voie": prior_voie}
            return rep
    route = classify(db, message, history=history, contexte=contexte, prior_params=prior_params)
    if scenario and scenario in SCENARIOS and not route.degraded:
        # le chip lève l'ambiguïté d'INTENTION : intent forcé, clarification d'intention retirée. La
        # clarification de PARAMÈTRE (commune manquante…) reste, produite en aval par l'outil/le récap.
        route.intent = SCENARIOS[scenario]["intent"]
        route.clarification = None
    if route.degraded:
        return _reply(ERREUR_INFRA, None, degraded=True)
    # GB-014 (Q30) — CRÉOLE RÉUNIONNAIS ON-TOPIC (« kosa i lé in kaz an tol ? ») : le routeur le classe
    # parfois HORS_SUJET faute de reconnaître la langue. Un mot d'habitat/foncier créole présent → c'est
    # une question de vocabulaire du bâti → voie b (connaissance générale), jamais un hors-domaine. Le
    # prompt _general répond DANS la langue qui vient.
    if route.intent == "HORS_SUJET" and _est_creole_foncier(message):
        route.intent = "EXPLIQUER"
    # GB-019 — COÛT D'UNE PRESTATION FONCIÈRE (« ça coûte combien une étude de sol ? ») : hors données
    # LABUSE mais DANS le domaine → voie b honnête (ordre de grandeur + renvoi pro), jamais un mur
    # hors-sujet. Rescousse le HORS_SUJET du routeur, comme le créole.
    if route.intent == "HORS_SUJET" and _est_service_cout(message):
        route.intent = "EXPLIQUER"
    # COPILOTE-REFONTE — DEMANDE VISUELLE anaphorique (« montre-les sur la carte » après un compte) :
    # le routeur la classe parfois OUTIL (« montre » = action). Si le fil porte déjà une commune et que
    # c'est une demande de CARTE, on la ramène sur la voie a visuelle (compte + porte carte), pas un
    # refus « ouvrir un outil ». Les paramètres (commune/tier) sont hérités du fil.
    if _veut_carte(message) and route.intent in ("OUTIL", "QUESTION"):
        # FIX-COPILOTE-BATTERIE (Q3) — « montre-les sur la carte » n'apporte PAS la commune : on l'HÉRITE
        # du fil (prior_params) si le tour ne l'a pas, puis on ramène sur la voie a visuelle (RECHERCHE →
        # compte + carte). Sans ça, le routeur OUTIL sans commune retombait en refus « ouvrir un outil ».
        params = route.params or {}
        for k in ("commune", "tier", "surface_min", "surface_max", "zonage"):
            if params.get(k) in (None, "", []) and (prior_params or {}).get(k) not in (None, "", []):
                params[k] = prior_params[k]
        route.params = params
        if params.get("commune"):
            route.intent = "RECHERCHE"
    # COPILOTE-REFONTE — CONTINUITÉ DE VOIE : un fil en CONNAISSANCE GÉNÉRALE (voie b) le RESTE tant que
    # le tour est une CONTINUATION sans signal de donnée (« elle est toujours en place ? » après Girardin).
    # C'est le cœur du repro Q2 : sans ça, un suivi d'actualité retombait en QUESTION → web bancal / mur.
    # Un vrai nouveau sujet (nouveau_sujet=True) ou un signal de donnée (commune/idu/…) sort de la voie b.
    if (prior_voie == "generale" and not route.nouveau_sujet
            and route.intent not in ("PROJET", "VEILLE")
            and not _a_signal_data(route.params)):
        rep = _general(db, message, history)
    else:
        rep = _answer_with_route(db, message, route, contexte=contexte, confirme=confirme,
                                 faits_fil=faits_fil, history=history)
    # GB-014 (Q29) — MULTI-INTENTIONS : si le message portait plusieurs demandes, on NOMME celles qu'on
    # n'a pas traitées (écho des mots du client, aucun chiffre) — plus jamais un largage silencieux. On
    # n'ajoute rien sur une clarification, un hors-sujet ou un dégradé (rien n'a été « traité »).
    if (not scenario and not rep.get("clarification") and not rep.get("degraded")
            and rep.get("refus") != "hors_sujet"):
        reste = _multi_demandes_reste(message, rep)
        if reste:
            autres = " ; ".join(f"« {s} »" for s in reste)
            rep["text"] = (rep.get("text", "").rstrip()
                           + "\n\nVotre message contenait plusieurs demandes — je n'en traite qu'une à la "
                           "fois. Reposez séparément celles que je n'ai pas couvertes : " + autres + ".")
            rep["multi_intent"] = True
    if scenario:
        rep.setdefault("scenario", scenario)   # M113 — le gabarit de réponse (Phase 4) suit le scénario
    # M102-B1 — contexte du tour attaché en UN point (quel que soit le chemin de réponse) :
    # poppé par l'endpoint pour la persistance du fil, jamais servi au client.
    # COPILOTE-REFONTE — `voie` VOYAGE dans le _route persisté : le tour SUIVANT sait si le fil est en
    # connaissance générale (voie b) et applique la continuité de voie. `None` = voie a (données LABUSE).
    rep.setdefault("_route", {"intent": route.intent, "clarification": bool(route.clarification),
                              "voie": "generale" if rep.get("general") else None,
                              "params": {k: v for k, v in (route.params or {}).items()
                                         if v is not None and k != "selection"}})
    # M102-B2 — RÉCAP SYSTÉMATIQUE (extension Vic de la règle M78) : une phrase « j'ai compris »
    # partout où une interprétation a eu lieu. Les missions lourdes gardent leur récap-péage M78
    # (pas de doublon) ; hors-sujet/dégradé n'interprètent rien. Jamais un slug : clés traduites,
    # clé inconnue ÉLAGUÉE (plutôt muette que jargonnante).
    # M118 — le récap systématique ne vaut plus que pour la MISSION 1 (QUESTION facette) : c'est la
    # seule où une interprétation de paramètres/critères a lieu. Web/expliquer/préparer et les
    # refus-voies n'interprètent pas de critères — pas de récap.
    if (route.intent == "QUESTION" and not rep.get("web") and not rep.get("general")
            and not rep.get("degraded") and rep.get("refus") not in ("hors_sujet", "hors_mission")):
        compris = _compris_fr(route.intent, route.params or {})
        # M110 — le récap NOMME les critères de facette appliqués (au-delà des params du routeur :
        # friche, procédure, copropriété, zone U…) — « comme aujourd'hui » pour commune/surface.
        # M117 · D7 — dédup : un critère déjà nommé dans la tête (mot commun) n'est pas répété.
        base = (compris or "").lower()
        appliques = [a for a in (rep.get("criteres_appliques") or [])
                     if a.split()[0].lower().rstrip("s") not in base]
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
# M117 · D7 — le récap dit chaque information UNE fois, jamais un slug. Le param `sujet` (une
# paraphrase libre de la question — « friches à Cilaos ») est RETIRÉ : il répétait la commune et le
# critère (« Cilaos · friches à Cilaos · friche »). Les descripteurs propres (commune, surface, zone,
# entreprise…) + les critères de facette (« friche », « procédure judiciaire ») suffisent et ne se
# recouvrent pas. Le sujet reste disponible pour le routage, il n'est simplement plus SERVI au récap.
_COMPRIS_PARAM = {"commune": lambda v: str(v), "idu": lambda v: f"parcelle {v}",
                  "zone": lambda v: f"zone {v}", "surface_min": lambda v: f"≥ {v} m²",
                  "surface_max": lambda v: f"≤ {v} m²", "budget_eur": lambda v: f"budget {v} €",
                  "prix_eur": lambda v: f"prix {v} €", "entreprise": lambda v: str(v),
                  "programme_logements": lambda v: f"{v} logements"}


def _compris_fr(intent: str, params: dict) -> str | None:
    """La phrase du récap systématique (M102-B2) — UNE phrase, jamais un formulaire, jamais un
    slug (clé hors table = élaguée)."""
    tete = _COMPRIS_INTENT.get(intent)
    if not tete:
        return None
    bouts = [fmt(params[k]) for k, fmt in _COMPRIS_PARAM.items()
             if params.get(k) not in (None, "", [])]
    return f"J'ai compris : {tete}" + (f" — {' · '.join(bouts)}." if bouts else ".")


# ───────────────────────── M118 — refus-voie + les 2 missions nouvelles ─────────────────────────
def _refus_voie(db: Session, message: str, intent: str, texte: str, cible: str, libelle: str,
                idu: str | None = None) -> dict:
    """Ce qui QUITTE le chat (instruire, créer un projet, surveiller, ouvrir un outil, rédiger un
    courrier) reçoit un REFUS + une VOIE cliquable (gabarit D6, NAVIGATION pure, jamais une exécution).
    `cible` ∈ {projets, surveillance, outils, fiche, courriers}."""
    telemetrie.refus(db, f"hors_mission:{cible}", message, intent)
    return _reply(texte, intent, refus="hors_mission",
                  voie={"cible": cible, "libelle": libelle, **({"idu": idu} if idu else {})})


# COPILOTE-REFONTE (voie b) — la CONNAISSANCE GÉNÉRALE unifiée : notions ET actualité ET vocabulaire
# maison, dans le fil (l'anaphore « elle » se résout sur l'historique). Remplace l'ancien EXPLIQUE
# (notions seules → un « est-ce toujours en vigueur ? » retombait en refus/web bancal). Honnêteté :
# aucun chiffre LABUSE inventé ; l'état DATÉ du droit n'est jamais affirmé (renvoi BOFiP/conseil).
GENERAL_SYSTEM = (
    "Tu es le copilote foncier de LABUSE (La Réunion). On te pose une question de CONNAISSANCE GÉNÉRALE "
    "sur le foncier, la fiscalité, l'urbanisme ou le VOCABULAIRE du métier (loi Girardin, Pinel outre-mer, "
    "ZFANG, SUP, PLU, zone AU, charge foncière, SDP, SHAB, ANRU, PPR, SRU, défiscalisation, notaire, "
    "géomètre, SPF/CERFA…). Tu réponds DE MÉMOIRE — ce n'est PAS une donnée LABUSE.\n"
    "Le fil de conversation t'est donné : une reprise (« elle », « et à la Réunion ? », « ce dispositif ») "
    "se résout sur le tour précédent — ne redemande pas de préciser ce qui est déjà clair dans le fil.\n"
    "LANGUE : réponds DANS la langue de la question — français OU créole réunionnais. Le vocabulaire du "
    "bâti/foncier en créole (« kaz » = maison, « kaz an tol » = maison en tôle, « terin » = terrain, "
    "« lakour » = cour/parcelle) est DANS ton domaine : réponds au fond, ne le traite JAMAIS comme "
    "hors-domaine.\n"
    "RÈGLES ABSOLUES :\n"
    "1. COURT : 2 à 4 phrases, concret, orienté La Réunion quand c'est pertinent.\n"
    "2. AUCUN CHIFFRE inventé sur une commune ou une parcelle précise, aucune statistique LABUSE, aucun "
    "taux/plafond précis sorti de nulle part.\n"
    "3. ÉTAT DU DROIT / ACTUALITÉ : pour « est-ce toujours en vigueur », « ça existe encore », « quel taux "
    "aujourd'hui » — donne le PRINCIPE, mais DIS l'incertitude sur l'état EXACT et la date, et renvoie vers "
    "le BOFiP ou un notaire / conseil fiscal pour confirmer. N'AFFIRME JAMAIS un état du droit daté comme "
    "certain, n'invente pas une date d'abrogation ou de prorogation.\n"
    "4. VOCABULAIRE MAISON — reste cohérent avec LABUSE : SDP = surface de plancher (la surface construite "
    "au sens du code de l'urbanisme) ; SHAB = surface habitable (plus petite, hors murs/circulations) ; "
    "charge foncière = le prix maximal au m² de plancher qu'une opération peut payer pour le terrain en "
    "restant à l'équilibre. Ne donne pas une définition divergente de celles-là.\n"
    "4bis. COÛT D'UNE PRESTATION foncière (étude de sol/géotechnique, géomètre/bornage, honoraires de "
    "notaire, raccordements/viabilisation, diagnostics) : c'est DANS ton domaine — donne un ORDRE DE "
    "GRANDEUR général (une fourchette large), PRÉCISE que ça varie selon le terrain/la prestation, et "
    "renvoie au PROFESSIONNEL pour un devis. N'invente JAMAIS un prix précis ni un tarif réunionnais "
    "exact ; jamais de mur « hors-sujet » sur ces questions.\n"
    "5. HORS-DOMAINE : si la question n'a RIEN à voir avec le foncier / l'immobilier / l'urbanisme / la "
    "fiscalité de La Réunion (cuisine, météo, sport, bavardage), réponds EXACTEMENT : « HORS_DOMAINE ».\n"
    "Pas d'introduction, pas de balises, pas d'URL.")

PREPARE_SYSTEM = (
    "Tu es le copilote foncier de LABUSE (La Réunion). On te demande de PRÉPARER un SCRIPT D'APPEL ou "
    "un ARGUMENTAIRE pour aborder un propriétaire/vendeur. Rends un script COURT et structuré (accroche "
    "courtoise · intérêt · proposition · ouverture), ton professionnel et respectueux. RÈGLES : (1) "
    "n'INVENTE ni ne CALCULE aucun chiffre (prix, surface, valeur) ; (2) si des FAITS SOURCÉS te sont "
    "fournis, tu peux les reprendre tels quels, jamais en dériver d'autres ; (3) sans faits fournis, "
    "reste GÉNÉRIQUE (pas de chiffre). Pas de mise en contexte, va au script.")


def _general(db: Session, message: str, history: list[dict] | None = None) -> dict:
    """VOIE B (COPILOTE-REFONTE) — connaissance générale foncier/fiscalité/urbanisme/vocabulaire.
    Portée dans le FIL (l'historique résout l'anaphore « elle »). Réponse COURTE, honnête sur l'état
    du droit, badgée `voie="generale"` (le front l'annonce « Réponse générale — hors données LABUSE »).
    Hors-domaine (cuisine/météo) → refus d'UNE phrase. JAMAIS un chiffre LABUSE inventé."""
    hist = [{"role": str(m.get("role", "user")), "content": str(m.get("content", ""))[:600]}
            for m in (history or [])[-4:]]
    out = core.complete(db, kind="copilote-general", model=core.model_for("copilote-general"), max_tokens=300,
                        system=GENERAL_SYSTEM, history=hist, context={"question": message})
    if out.degraded:
        return _reply(ERREUR_INFRA, "EXPLIQUER", degraded=True)
    txt = (out.text or "").strip()
    if not txt or txt.upper().startswith("HORS_DOMAINE"):
        telemetrie.refus(db, "hors_domaine", message, "EXPLIQUER")
        return _reply(HORS_SUJET, "HORS_SUJET", refus="hors_sujet")
    # `general=True` = le discriminant servi au front (badge « Réponse générale — hors données LABUSE »
    # + surface IA assumée) ; `tool="general"` reste pour la télémétrie. La promesse « sourcée/datée » de
    # l'en-tête ne vaut QUE pour la voie a. NB : distinct du champ `voie` (objet de NAVIGATION des refus).
    return _reply(txt, "EXPLIQUER", general=True, tool="general")


# COPILOTE-REFONTE — helpers de conversation (continuité de voie + tenue de position).
_DATA_KEYS = ("commune", "idu", "surface_min", "surface_max", "budget_eur", "prix_eur",
              "entreprise", "programme_logements")
_DOUTE_KW = ("t'es sur", "t es sur", "tu es sur", "es-tu sur", "es tu sur", "es-tu certain",
             "es tu certain", "vraiment ", "vraiment?", "c'est sur", "c est sur", "sur de toi",
             "sure de toi", "certain de", "certaine de", "t'es certain", "t es certain",
             "vous etes sur", "vous etes certain")


def _a_signal_data(params: dict | None) -> bool:
    """Le tour porte-t-il un signal de DONNÉE LABUSE (commune, idu, surface, budget, société…) ?
    Si oui, il ne reste pas « collé » à la voie b — il peut appeler la voie a."""
    return any((params or {}).get(k) not in (None, "", []) for k in _DATA_KEYS)


# ═════════════════════════ GB-014 — clarification · multi-intentions · créole ═════════════════════════
# Trois faiblesses du grand oral (RAPPORT-CYCLE-3), soldées EN DÉTERMINISTE (le prompt LLM reste un
# filet) pour que chaque cas ait un test reproductible sans dépendre d'un appel modèle.

# (Q24/Q25) DÉICTIQUE VAGUE SANS ANTÉCÉDENT — « c'est cher là-bas ? », « compare les deux » : le fil ne
# porte aucun référent qui les résolve → on POSE une clarification courte, jamais une réponse au hasard
# ni un hors-sujet. Ne se déclenche PAS si le fil résout la déictique (un « et là-bas ? » après « prix à
# Saint-Leu » hérite de la commune) ni si le message NOMME lui-même un lieu.
_DEICT_LIEU = ("la-bas", "la bas", "cet endroit", "cette commune", "cette ville", "ici", "sur place")
_DEICT_LIEU_CLARIF = ("De quelle commune (ou de quel bien) parlez-vous ? Je n'ai pas de lieu en tête "
                      "dans ce fil — nommez-le et je réponds.")
_DEICT_PAIRE = ("les deux", "les 2", "ces deux", "ces 2", "lesquels", "lesquelles")
_DEICT_PAIRE_CLARIF = ("Comparer quoi, exactement ? Deux communes, deux parcelles, deux prix ? "
                       "Précisez les deux éléments et je les compare.")


def _nomme_un_lieu(message: str) -> bool:
    """Le message contient-il déjà un toponyme des 24 communes ? (alors la déictique est superflue)."""
    from .outils import _plier_toponyme, _referentiel_plie
    pile = _plier_toponyme(message or "")
    return any(k and len(k) >= 5 and k in pile for k in _referentiel_plie())


def _a_antecedent(prior_params: dict | None, contexte: dict | None) -> bool:
    """Le fil porte-t-il un référent résoluble (commune/idu/société déjà en jeu, ou une parcelle
    embarquée dans la surface) ? Si oui, une déictique s'y rattache — pas de clarification."""
    if contexte and (contexte.get("idu") or contexte.get("selection")):
        return True
    return bool(prior_params and any(prior_params.get(k) for k in ("commune", "idu", "entreprise")))


def _clarif_anaphore(message: str, prior_params: dict | None, contexte: dict | None) -> str | None:
    """La clarification COURTE à poser si le message est une déictique vague SANS antécédent, sinon
    None. Déterministe, avant classify (0 appel modèle)."""
    m = _fold_py((message or "").strip().lower())
    if not m or len(m.split()) > 8:            # une vraie phrase porte son propre contexte
        return None
    if _a_antecedent(prior_params, contexte) or _nomme_un_lieu(message):
        return None
    if any(k in m for k in _DEICT_PAIRE) or ("compare" in m and not _nomme_un_lieu(message)):
        return _DEICT_PAIRE_CLARIF
    if any(k in m for k in _DEICT_LIEU):
        return _DEICT_LIEU_CLARIF
    if "cher" in m and not any(c.isdigit() for c in m):   # « c'est cher ? » sans lieu = le « où » manque
        return _DEICT_LIEU_CLARIF
    return None


# (Q30) CRÉOLE RÉUNIONNAIS ON-TOPIC — « kosa i lé in kaz an tol ? » (qu'est-ce qu'une maison en tôle) est
# une question de VOCABULAIRE du bâti → voie b, jamais hors-domaine. Détection par le lexique de l'habitat/
# foncier créole (tokens, pas sous-chaîne — évite les collisions).
_CREOLE_HABITAT = {"kaz", "kaze", "tol", "tôl", "tole", "terin", "teren", "tèrin", "lakour", "karo",
                   "karé", "kare", "bardo", "ti-kaz", "tikaz", "boukan", "païaman"}


def _est_creole_foncier(message: str) -> bool:
    """Le message est-il une question créole réunionnaise sur le bâti/foncier ? (≥1 nom d'habitat créole)."""
    toks = set(_fold_py((message or "").lower()).replace("-", " ").split())
    return bool(toks & {_fold_py(w) for w in _CREOLE_HABITAT})


# (Q29) MULTI-INTENTIONS — un message qui porte PLUSIEURS demandes : on traite la principale (comme avant)
# et on NOMME ce qu'on laisse (« reposez séparément : … »), jamais un largage silencieux. Découpe
# déterministe (ponctuation + connecteurs d'énumération) ; on écho les demandes non traitées avec les
# mots du client (aucune paraphrase, aucun chiffre inventé).
_ENUM_CONNECT = ("d'abord", "dabord", "ensuite", "enfin", "puis", "premierement", "deuxiemement",
                 "troisiemement", "par ailleurs", "egalement", "et aussi", "autre chose",
                 "derniere chose", "et enfin")
_DEMANDE_KW = ("combien", "quel", "quelle", "quels", "quelles", "est-ce", "est ce", "comment",
               "pourquoi", "faisable", "peux-tu", "peux tu", "peu tu", "dis-moi", "dis moi",
               "je voudrais savoir", "je me demande", "savoir si", "montre", "calcule", "compare",
               "verifie", "prepare", "ecris", "trouve", "liste", "en vigueur", "toujours actif",
               "toujours en vigueur", "vaut", "prix", "delai", "délai")


def _segments_demande(message: str) -> list[str]:
    """Découpe le message en SEGMENTS qui portent chacun une demande (question/impératif). Sépare sur la
    ponctuation forte et les connecteurs d'énumération. Garde le texte original (pour l'écho)."""
    marked = re.sub(r"(?i)\b(d'abord|dabord|ensuite|enfin|puis|premi[eè]rement|deuxi[eè]mement|"
                    r"troisi[eè]mement|par ailleurs|[ée]galement|et aussi|autre chose|"
                    r"derni[eè]re chose|et enfin)\b", "¦", message or "")
    segs: list[str] = []
    for p in re.split(r"[?!.;\n¦]+", marked):
        s = p.strip(" ,-—·:¦\t")
        if len(s) < 8:
            continue
        if any(k in _fold_py(s.lower()) for k in _DEMANDE_KW):
            segs.append(re.sub(r"\s+", " ", s))
    return segs


def _multi_demandes_reste(message: str, rep: dict) -> list[str]:
    """Les demandes NON traitées à nommer (max 4, déterministe), ou [] si le message est mono-demande.
    Ne sur-découpe pas une simple question composée (exige ≥3 segments OU un connecteur d'énumération)."""
    segs = _segments_demande(message)
    if len(segs) < 2:
        return []
    mfold = _fold_py((message or "").lower())
    has_enum = any(c in mfold for c in _ENUM_CONNECT)
    if len(segs) < 3 and not has_enum:
        return []
    traite: set[str] = set()
    if rep.get("prefill_programme") or rep.get("porte") == "programme":
        traite |= {"immeuble", "immeubles", "logement", "logements", "faisab", "plancher", "batiment",
                   "batiments", "r+", "maison", "maisons", "sdp", "surface de plancher"}
    reste = [s for s in segs if not any(k in _fold_py(s.lower()) for k in traite)] if traite else segs[1:]
    if not reste or len(reste) == len(segs):     # segment traité non identifié → tout sauf le 1ᵉ (servi en tête)
        reste = segs[1:]
    vus, out = set(), []
    for s in reste:
        disp = (s[:90].rstrip() + "…") if len(s) > 90 else s
        key = _fold_py(disp.lower())[:40]
        if key in vus:
            continue
        vus.add(key)
        out.append(disp)
    return out[:4]


_RESUME_KW = ("resume", "resumes", "recapitule", "recapitul", "ce qu'on s'est dit", "ce qu on s est dit",
              "ce que je t'ai demande", "ce que je t ai demande", "reprends ce qu", "fais le point")


def _est_resume(message: str) -> bool:
    """« résume-moi ce qu'on s'est dit », « récapitule » — une demande de RÉSUMÉ du fil, pas une
    question foncière. Traitée en déterministe (0 modèle), depuis l'historique et les faits servis."""
    m = _fold_py((message or "").strip().lower())
    return any(k in m for k in _RESUME_KW)


def _resume_fil(history: list[dict] | None, faits_fil: list[dict] | None) -> dict:
    """RÉSUMÉ déterministe du fil : les questions posées + les chiffres SERVIS (avec leur source).
    Jamais un chiffre inventé — uniquement ce qui a réellement été servi (registre de faits)."""
    qs = [str(h.get("content") or "") for h in (history or []) if h.get("role") == "user"][-6:]
    figs, vus = [], set()
    for f in (faits_fil or []):
        src = f.get("source")
        if not src or src in vus:
            continue
        vus.add(src)
        val = f.get("valeur")
        val = int(val) if isinstance(val, float) and val.is_integer() else val
        figs.append(f"{val} ({src})")
        if len(figs) >= 5:
            break
    if not qs and not figs:
        return _reply("On n'a encore rien établi dans cette conversation — posez-moi une question.",
                      "QUESTION", resume=True)
    txt = ("Dans cette conversation, vous avez demandé : " + " ; ".join(qs) + "."
           if qs else "Résumé de la conversation.")
    if figs:
        txt += " Chiffres servis : " + " · ".join(figs) + "."
    return _reply(txt, "QUESTION", resume=True,
                  sources=list(vus)[:5] if vus else None)


# FIX-COPILOTE-BATTERIE (Q11) — extraction d'un PROGRAMME de construction (pour pré-remplir la Faisabilité).
_RE_BAT = re.compile(r"(\d+)\s*(?:immeubles?|batiments?|blocs?|plots?)")
_RE_NIV = re.compile(r"r\s*\+\s*(\d+)")
_RE_LGT = re.compile(r"(\d+)\s*logements?")


def _extract_programme(message: str) -> dict | None:
    """« un terrain pour 3 immeubles R+3 de 8 logements » → {batiments:3, niveaux:3, logements_par_batiment:8}.
    Exige des BÂTIMENTS ou des niveaux R+N (un vrai programme) : « combien de logements à X » (question de
    donnée) n'a ni l'un ni l'autre → pas capté. Déterministe, aucun modèle."""
    m = _fold_py((message or "").lower())
    bat, niv, lgt = _RE_BAT.search(m), _RE_NIV.search(m), _RE_LGT.search(m)
    if not (bat or niv):
        return None
    prog: dict[str, int] = {}
    if bat:
        prog["batiments"] = int(bat.group(1))
    if niv:
        prog["niveaux"] = int(niv.group(1))
    if lgt:
        prog["logements_par_batiment"] = int(lgt.group(1))
    return prog or None


_RE_REF_PARC = re.compile(r"\b([A-Z]{1,2}\d{1,4})\b")


def _resoudre_idu_court(db, message: str, commune: str | None) -> str | None:
    """FIX-COPILOTE-BATTERIE (Q13) — « ma parcelle BZ1065 à Saint-Denis » → IDU 14 car. via `parcels`
    (commune + suffixe section-numéro). None si absent ou ambigu (jamais deviné). Lecture seule."""
    if db is None or not commune:
        return None
    from sqlalchemy import text
    from .outils import resoudre_commune
    com = resoudre_commune(commune)
    if not com:
        return None
    for ref in _RE_REF_PARC.findall((message or "").upper()):
        try:
            rows = db.execute(text("SELECT idu FROM parcels WHERE commune = :c AND idu LIKE :suf LIMIT 2"),
                              {"c": com, "suf": f"%{ref}"}).fetchall()
        except Exception:  # noqa: BLE001
            return None
        if len(rows) == 1:
            return rows[0][0]
    return None


def _programme_fr(prog: dict) -> str:
    bouts = []
    if prog.get("batiments"):
        bouts.append(f"{prog['batiments']} bâtiment{'s' if prog['batiments'] > 1 else ''}")
    if prog.get("niveaux"):
        bouts.append(f"R+{prog['niveaux']}")
    if prog.get("logements_par_batiment"):
        bouts.append(f"{prog['logements_par_batiment']} logements/bât.")
    return " · ".join(bouts)


def _est_mise_en_doute(message: str) -> bool:
    """« t'es sûr ? », « vraiment ? », « es-tu certain ? » — une remise en cause de la réponse
    précédente, pas une nouvelle question. Court (≤ ~6 mots), sans autre contenu interrogeable."""
    m = _fold_py((message or "").strip().lower())
    if len(m.split()) > 8:
        return False        # une vraie question qui contient « sûr » n'est pas une simple mise en doute
    return any(k in m for k in _DOUTE_KW)


def _tenue_position(faits_fil: list[dict] | None, prior_voie: str | None) -> dict:
    """TENUE DE POSITION — on MAINTIENT la dernière réponse, on ne retourne pas sa veste sans donnée
    nouvelle. Si un FAIT sourcé a été servi, on le re-cite avec sa source. Sinon (voie b), on assume
    la réponse générale et on renvoie au conseil pour confirmation."""
    fait = (faits_fil or [None])[0] if faits_fil else None
    if fait and fait.get("source"):
        val = fait.get("valeur")
        val = int(val) if isinstance(val, float) and val.is_integer() else val
        mill = f" · {fait['millesime']}" if fait.get("millesime") else ""
        return _reply(f"Oui, je maintiens : {val} ({fait['source']}{mill}). C'est la donnée servie par "
                      "l'outil, je ne la change pas sans élément nouveau — dis-moi lequel si tu en as un.",
                      "QUESTION", tenue=True, sources=[fait["source"]])
    if prior_voie == "generale":
        return _reply("Je maintiens ma réponse précédente — mais c'était une réponse GÉNÉRALE (hors "
                      "données LABUSE) : pour l'état exact du droit, confirme auprès du BOFiP ou d'un "
                      "notaire / conseil fiscal.", "EXPLIQUER", general=True, tenue=True)
    return _reply("Je m'appuie sur ce que je viens de te répondre ; si tu as un élément nouveau, "
                  "donne-le-moi et je reprends.", "QUESTION", tenue=True)


# ═════════════ GB-019 — méta-tours adjacents (déterministes, 0 appel modèle) ═════════════
# Même esprit que la tenue de position : provenance d'un chiffre, calcul sur ses propres chiffres,
# capacités/limites réelles, anaphore spatiale. Tous SANS appel modèle, tous honnêtes.

_PROVENANCE_KW = ("d'ou tu sors", "d ou tu sors", "d'ou vient", "d ou vient", "d'ou sort", "d ou sort",
                  "d'ou ca vient", "d ou ca vient", "ca vient d'ou", "ca vient d ou", "tu sors ca",
                  "quelle source", "quelles sources", "ta source", "tes sources", "source comment",
                  "source de ce", "sur quoi tu te base", "sur quoi te base", "c'est sourc", "c est sourc")


def _est_provenance(message: str) -> bool:
    """« d'où tu sors ce chiffre ? », « quelle source ? » — une question sur la PROVENANCE du dernier
    chiffre servi (méta-tour), pas une nouvelle question de donnée."""
    m = _fold_py((message or "").strip().lower())
    return any(k in m for k in _PROVENANCE_KW)


def _citer_source(faits_fil: list[dict] | None) -> dict:
    """Re-cite la SOURCE + le MILLÉSIME du dernier fait servi (registre) — à chaque fois, déterministe."""
    fait = (faits_fil or [None])[0] if faits_fil else None
    if fait and fait.get("source"):
        val = fait.get("valeur")
        val = int(val) if isinstance(val, float) and float(val).is_integer() else val
        mill = f", millésime {fait['millesime']}" if fait.get("millesime") else ""
        return _reply(f"Ce chiffre ({val}) vient de : {fait['source']}{mill}. Toute donnée LABUSE porte "
                      "sa source et sa date — c'est le principe.", "QUESTION", tenue=True,
                      sources=[fait["source"]])
    return _reply("Je n'ai pas de chiffre sourcé à re-citer dans ce fil. Reposez la question de donnée et "
                  "je vous donne la valeur AVEC sa source et sa date.", "QUESTION")


_CAPACITE_KW = ("t'as acces", "t as acces", "tu as acces", "as-tu acces", "acces a mes", "acces a mon",
                "tu peux voir mes", "tu vois mes", "mes emails", "mes e-mails", "mes mails", "mes courriels",
                "mes messages", "mon compte bancaire", "mes donnees perso", "mes donnees personnelles",
                "que sais-tu faire", "que peux-tu faire", "qu'est-ce que tu sais faire", "tes capacites",
                "t'es capable de quoi", "tu peux faire quoi")


def _est_capacites(message: str) -> bool:
    """« t'as accès à mes emails ? », « qu'est-ce que tu sais faire ? » — méta-question sur les
    capacités/limites du Copilote."""
    m = _fold_py((message or "").strip().lower())
    return any(k in m for k in _CAPACITE_KW)


_CAPACITE_TXT = (
    "Je lis UNIQUEMENT des données foncières publiques de La Réunion (cadastre, DVF, permis Sitadel, "
    "PLU/zonages, personnes morales SIREN, détections piscines/solaire) et le classement LABUSE. "
    "Je n'ai AUCUN accès à vos e-mails, vos messages, votre compte bancaire, ni à l'identité des "
    "propriétaires personnes physiques (donnée non ouverte en France). Ce que je fais : répondre à des "
    "questions de données (sourcées, datées), expliquer des notions, vous orienter vers les outils — "
    "je n'exécute rien à votre place (créer un projet, poser une veille, envoyer un courrier se font "
    "dans leur écran).")


_RE_CALCUL_PCT = re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:%|pour ?cent)\s*(?:de|d'|of|sur)\s*([\d][\d\s.,]*)?")


def _calcul_pct(message: str, faits_fil: list[dict] | None) -> dict | None:
    """« calcule-moi 3 % de 2 327 » → calcul déterministe. Base numérique dans le message, ou (si un
    verbe de calcul est présent) le dernier chiffre du fil. Renvoie None si ce n'est pas un vrai calcul
    (« 3 % de logements sociaux » n'a pas de base numérique et pas de verbe → on laisse le routeur)."""
    m = _fold_py((message or "").lower())
    mt = _RE_CALCUL_PCT.search(m)
    if not mt:
        return None
    pct = float(mt.group(1).replace(",", "."))
    base = None
    if mt.group(2):
        raw = mt.group(2).replace(" ", "").replace(",", ".").rstrip(".")
        try:
            base = float(raw)
        except ValueError:
            base = None
    if base is None:                       # « X % de ce chiffre » → dernier fait, SI verbe de calcul
        if not any(k in m for k in ("calcul", "combien font", "ca fait", "ca donne", "ca fais")):
            return None
        fait = (faits_fil or [None])[0] if faits_fil else None
        base = fait.get("valeur") if fait else None
    if base is None:
        return None
    res = pct / 100.0 * float(base)
    bf = int(base) if float(base).is_integer() else round(base, 2)
    rf = int(res) if float(res).is_integer() else round(res, 2)
    return _reply(f"{pct:g} % de {bf} = {rf}.", "QUESTION", calcul=True)


_VOISINE_KW = ("sa voisine", "la voisine", "ses voisines", "les voisines", "parcelle voisine",
               "parcelles voisines", "mitoyenne", "mitoyennes", "d'a cote", "d a cote", "celle d'a cote",
               "la parcelle d'a cote", "les parcelles autour")


def _est_voisine(message: str) -> bool:
    """« et sa voisine ? » — anaphore SPATIALE : une parcelle a plusieurs mitoyennes, on ne devine pas."""
    m = _fold_py((message or "").strip().lower())
    return any(k in m for k in _VOISINE_KW)


_SERVICE_COUT_KW = ("etude de sol", "geometre", "bornage", "borne le terrain", "diagnostic amiante",
                    "diagnostic plomb", "raccordement", "honoraires notaire", "frais de notaire",
                    "cout d'un notaire", "cout du notaire", "prix d'un geometre", "devis geometre",
                    "etude geotechnique", "diagnostic technique")


def _est_service_cout(message: str) -> bool:
    """« ça coûte combien une étude de sol ? » — coût d'une PRESTATION foncière : hors données LABUSE,
    mais DANS le domaine → voie b honnête (ordre de grandeur + renvoi pro), jamais un mur hors-sujet."""
    m = _fold_py((message or "").lower())
    return any(k in m for k in _SERVICE_COUT_KW)


def _preparer(db: Session, message: str, params: dict, contexte: dict | None) -> dict:
    """Mission 4 — préparer un script/argumentaire. Faits SOURCÉS repris si contexte parcelle, sinon
    générique métier. Jamais inventer ni calculer un chiffre."""
    idu = params.get("idu") or (contexte or {}).get("idu")
    faits = _substance(db, idu) if idu else ""      # faits déjà sourcés de la fiche (jamais recalculés)
    ctx = {"demande": message}
    if faits:
        ctx["faits_sources"] = f"Sur la parcelle {idu} : {faits}"
    out = core.complete(db, kind="copilote-prepare", model=core.model_for("copilote-prepare"), max_tokens=420,
                        system=PREPARE_SYSTEM, context=ctx)
    if out.degraded or not (out.text or "").strip():
        return _reply(ERREUR_INFRA, "PREPARER", degraded=True)
    return _reply(out.text.strip(), "PREPARER", tool="prepare",
                  sources=(["fiche parcelle (faits sourcés)"] if faits else None))


# ───────────── SUITE-1 S9 — LES MISSIONS LOURDES (RECHERCHE / VERIFICATION) DANS v2 ─────────────
# Décision Vic : un seul Copilote, le v2. M118 avait renvoyé RECHERCHE/VERIFICATION hors du chat
# (refus-voie). S9 les RAPATRIE : elles s'exécutent DANS le chat par le moteur de mission run-scopé
# (copilote/{executeur,moteurs}, servi sous /api/copilote-v2/runs), avec le récap-péage M78-bis. Le
# récap est produit ICI (needs_confirmation + brief_effectif) ; le FRONT lance le run (RECHERCHE) ou
# renvoie `confirme=True` (VERIFICATION → avis instruit missions_lourdes). PROJET/VEILLE/OUTIL restent
# refus-voie (leur exécution vit ailleurs — Projets/Surveillance/Outils).
def _brief_effectif_recherche(message: str, params: dict) -> str:
    """Brief NATUREL recomposé des paramètres compris (commune héritée du fil comprise) : c'est le
    `brief_raw` que le moteur run-scopé réinterprète. Garantit que le run part des critères annoncés
    au récap, jamais d'un fil perdu. Vide de params → le message verbatim."""
    bits = []
    if params.get("commune"):
        bits.append(f"à {params['commune']}")
    if params.get("programme_logements"):
        bits.append(f"pour {int(params['programme_logements'])} logements")
    if params.get("budget_eur"):
        bits.append(f"avec un budget de {int(params['budget_eur'])} €")
    if params.get("surface_min"):
        bits.append(f"d'au moins {int(params['surface_min'])} m²")
    if params.get("zone"):
        bits.append(f"en zone {params['zone']}")
    return ("Trouve des terrains à instruire " + " ".join(bits)) if bits else (message or "")


def _recap_recherche(params: dict) -> str:
    bits = []
    if params.get("commune"):
        bits.append(str(params["commune"]))
    if params.get("programme_logements"):
        bits.append(f"{int(params['programme_logements'])} logements")
    if params.get("budget_eur"):
        bits.append(f"budget {int(params['budget_eur'])} €")
    if params.get("surface_min"):
        bits.append(f"≥ {int(params['surface_min'])} m²")
    if params.get("zone"):
        bits.append(f"zone {params['zone']}")
    return ("J'ai compris : une recherche de terrains à instruire"
            + (" — " + " · ".join(bits) if bits else "") + ".")


def _mission_recherche(db: Session, message: str, params: dict) -> dict:
    """RECHERCHE → récap-péage (needs_confirmation) ; le front lancera le run lourd. Le moteur cherche
    commune par commune : sans commune, on DEMANDE (clarification-récap), jamais un run à vide."""
    if not params.get("commune"):
        return _reply("Sur quelle commune dois-je chercher ? J'instruis commune par commune.",
                      "RECHERCHE", needs_confirmation=True, brief_effectif=message,
                      clarification_recap={"question": "Sur quelle commune dois-je chercher les terrains ?",
                                           "options": [], "champ": "commune"})
    recap = _recap_recherche(params)
    return _reply(recap, "RECHERCHE", needs_confirmation=True, recap=recap,
                  brief_effectif=_brief_effectif_recherche(message, params))


def _mission_verification(db: Session, message: str, params: dict, contexte: dict | None,
                          confirme: bool) -> dict:
    """VERIFICATION → récap-péage, puis (confirme=True) AVIS instruit face au prix (missions_lourdes :
    marché DVF, réserve de méthode, verrou anti-invention). Sans IDU résoluble, on DEMANDE l'IDU."""
    idu = (params.get("idu") or (contexte or {}).get("idu")
           or _resoudre_idu_court(db, message, params.get("commune")))
    if idu:
        params["idu"] = idu
    if confirme:
        from . import missions_lourdes
        av = missions_lourdes.verification(db, params)
        if av.get("clarification"):
            return _reply(av["text"], "VERIFICATION", clarification=True)
        if av.get("refus"):
            return _reply(av["text"], "VERIFICATION", refus=av["refus"],
                          voie={"cible": "fiche", "libelle": "Ouvrir la fiche", **({"idu": idu} if idu else {})})
        return _reply(av["text"], "VERIFICATION", tool=av.get("tool"), idu=av.get("idu"),
                      sources=av.get("sources"), actions=av.get("actions"))
    if not idu:
        return _reply("Quelle parcelle dois-je vérifier ?", "VERIFICATION", needs_confirmation=True,
                      brief_effectif=message,
                      clarification_recap={"question": "Donnez-moi l'IDU (14 caractères) de la parcelle "
                                                       "à vérifier — et son prix demandé si vous l'avez.",
                                           "options": [], "champ": "idu"})
    prix = params.get("prix_eur") or params.get("budget_eur")
    recap = (f"J'ai compris : vérifier la parcelle {idu}"
             + (f" face à un prix de {int(prix)} €" if prix else " (donnez-moi le prix demandé pour l'avis complet)")
             + ".")
    brief_eff = f"Vérifie la parcelle {idu}" + (f" proposée à {int(prix)} €" if prix else "")
    return _reply(recap, "VERIFICATION", needs_confirmation=True, recap=recap, brief_effectif=brief_eff)


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

    # M118 — les 2 MISSIONS NOUVELLES d'abord (le chip force l'intent ; ne pas laisser un mot-clé
    # concept/document les intercepter). « prépare un argumentaire » ne doit pas matcher un document.
    if intent == "EXPLIQUER":
        return _general(db, message, history)     # COPILOTE-REFONTE — voie b unifiée (notion/actualité/vocab)
    if intent == "PREPARER":
        return _preparer(db, message, params, contexte)

    # FIX-COPILOTE-BATTERIE (Q11) — PROGRAMME de construction (« un terrain pour 3 immeubles R+3 de 8
    # logements ») → pré-remplit la FAISABILITÉ (porte 'programme' + m22Prefill) : la promesse d'écran
    # « le copilote sait pré-remplir » est TENUE. Extraction déterministe ; l'outil relance le formulaire.
    prog = _extract_programme(message)
    if prog:
        return _reply("Je pré-remplis la Faisabilité avec votre programme (" + _programme_fr(prog)
                      + ") — ajustez les hypothèses et le périmètre dans l'outil.", "OUTIL",
                      porte="programme", prefill="m22Prefill", prefill_programme=prog)

    # M118 — un CONCEPT-OUTIL (baromètre, où investir, parcelles fantômes…) ou un DOCUMENT (dossier,
    # courrier) reconnu QUITTE le chat : refus + voie cliquable. Ouvrir un outil → barre Outils ;
    # rédiger un document → fiche/CRM (le générateur existant). Navigation, jamais exécution.
    concept = _match_concept(message)
    if concept:
        _, label = concept
        return _refus_voie(db, message, "OUTIL", f"« {label} » s'ouvre depuis la barre Outils — je ne "
                           "l'ouvre plus depuis le chat.", "outils", "Ouvrir les outils")
    doc = _match_document(message)
    if doc:
        _, label = doc
        idu = params.get("idu") or (contexte or {}).get("idu")
        return _refus_voie(db, message, "OUTIL", f"Le {label} se génère depuis la fiche de la parcelle "
                           "(ou le CRM), pas depuis le chat.", "courriers", "Ouvrir la fiche", idu)

    # M118 — les intentions qui QUITTENT le chat : refus + voie (jamais une exécution). Chacune vers
    # sa surface : instruire/créer → Projets, vérifier → fiche, surveiller → Surveillance, outil/
    # courrier → Outils/CRM. Le routeur les CLASSE encore ; l'aiguillage les redirige.
    if intent == "RECHERCHE":
        # M112/M118 — une demande VISUELLE de données (« montre-moi les friches à Saint-Paul », « où
        # sont les parcelles en procédure ») est de la MISSION 1 (compte + carte), pas de l'instruction :
        # on la GARDE. Une vraie recherche part désormais en MISSION LOURDE dans le chat (S9).
        if _veut_carte(message) and not params.get("programme_logements") and not params.get("budget_eur"):
            sel = _select_tool(db, message, params)
            if sel.get("tool") == "compter_parcelles":
                res = OUTILS["compter_parcelles"](db, **_clean_args("compter_parcelles", sel.get("args") or {}))
                res.criteres_non_appliques = sel.get("criteres_non_appliques") or []
                if res.ok:
                    return _reply_compte(db, message, res, faits_fil, "QUESTION")
        # SUITE-1 S9 — RECHERCHE instruite DANS le chat (moteur run-scopé), via le récap-péage.
        return _mission_recherche(db, message, params)
    if intent == "PROJET":
        return _refus_voie(db, message, intent, "La création d'un projet se fait dans Projets, avec le "
                           "parcours guidé.", "projets", "Ouvrir Projets")
    if intent == "VERIFICATION":
        # SUITE-1 S9 — VERIFICATION instruite DANS le chat : récap-péage puis avis complet (marché DVF).
        return _mission_verification(db, message, params, contexte, confirme)
    if intent == "VEILLE":
        return _refus_voie(db, message, intent, "La veille se pose et se règle dans "
                           "Veille.", "surveillance", "Ouvrir la Veille")
    if intent == "OUTIL":
        m = _fold_py(message.lower())
        if any(k in m for k in ("courrier", "ecrire au proprietaire", "ecrire au proprio", "lettre",
                                "dossier", "argumentaire ecrit")):
            idu = params.get("idu") or (contexte or {}).get("idu")
            return _refus_voie(db, message, intent, "La rédaction d'un courrier au propriétaire se fait "
                               "depuis la fiche / le CRM (le générateur existant).", "courriers",
                               "Ouvrir la fiche", idu)
        return _refus_voie(db, message, intent, "Les outils d'analyse s'ouvrent depuis la barre Outils.",
                           "outils", "Ouvrir les outils")

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
            # M116 · D2 — une question de COMPTAGE à qui il manque juste la commune : demander la
            # commune (précision, son champ = le fil), jamais un refus « aucun outil ». La division
            # garde sa voie (règlement) et n'est pas interceptée ici.
            m = _fold_py(message.lower())
            compte = ("combien" in m or "nombre de" in m) and "parcelle" in m
            if compte and not params.get("commune") and not any(k in m for k in _SANS_OUTIL_KW):
                telemetrie.refus(db, "manque_commune", message, intent)
                return _reply("Sur quelle commune ? Je compte les parcelles commune par commune.",
                              intent, clarification=True)
            return _sans_outil(db, message, params, intent, history=history)
        tool = sel["tool"]
        if tool not in OUTILS:
            return _sans_outil(db, message, params, intent, history=history)
        # M78-ter — recherche_web : DERNIER recours, la question verbatim ; marquage web distinct.
        if tool == "recherche_web":
            res = OUTILS["recherche_web"](db, question=message)
            if not res.ok:                                 # rien trouvé → refus honnête + télémétrie
                telemetrie.refus(db, "web_rien_trouve", message, intent)
                return _sans_outil(db, message, params, intent, history=history)
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
            return _sans_outil(db, message, params, intent, motif=res.refus, history=history)
        return _reply_compte(db, message, res, faits_fil, intent)

    # M118 — OUTIL/RECHERCHE/VERIFICATION/PROJET/VEILLE sont interceptés PLUS HAUT (refus-voie). Il ne
    # reste ici que QUESTION (missions 1/2), EXPLIQUER (3), PREPARER (4) — déjà traités. Filet.
    return _reply(f"(Mission {intent} — hors du Copilote resserré.)", intent, en_construction=True)


# ───────────────────────── Aiguillage OUTIL (1c) ─────────────────────────
# demande-type (mot-clé folded) → (module registre, libellé, prefill). None = AUCUN outil (division).
_OUTIL_MAP = [
    (("assembl",), ("assemblage", "Assemblage", "parcelPrefill")),
    (("faisabil", "constructib", "capacit", "que peut accueillir"), ("programme", "Faisabilité", "parcelPrefill")),
    # RETOURS-8 (R12) — « pièges »/« risques » ouvrent l'outil Pièges et risques (prérempli IDU) : plus
    # jamais « pas de mesure dédiée » alors que l'outil existe. « taxe (d'aménagement) » → Taxe d'aménagement.
    (("piege", "pieges", "risque", "risques", "a surveiller sur cette parcelle", "points de vigilance"),
     ("risques", "Pièges et risques", "idu")),
    (("taxe d'amenagement", "taxe damenagement", "taxe amenagement", "combien de taxe", "montant de la taxe"),
     ("taxe-amenagement", "Taxe d'aménagement", "idu")),
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
    # M137-N (Vic 20/08/2026) — les concepts « fantôme » et « bailleur » sont RETIRÉS : leurs outils
    # (M07 fantome, M06 bailleur) ont quitté le produit (DORMANT). Router vers eux serait un LIEN MORT
    # (porte vers un module absent). Le signal succession (ex-fantôme) sera repris en facette ; d'ici là
    # ces demandes retombent sur le traitement normal du Copilote (facette/web/refus). Endpoints + tests
    # conservés au dépôt.
    # M112 — les 11 outils invisibles du registre (mots-clés SPÉCIFIQUES, sans collision avec le
    # comptage/marché/délais : jamais « permis » nu, jamais « renouvellement » nu, jamais « marché »).
    # Marché & veille d'abord (valeur d'usage), reconnaissance depuis les libellés servis du registre.
    # M137-Z — outil « Communes » (fusion Marché·Comparateur·Vélocité·Rareté). Les concepts
    # « comparer les communes » et « rareté du foncier » y mènent (table des 24 → fiche commune).
    (("comparateur de communes", "comparer les communes", "comparer des communes", "ou investir",
      "quelle commune investir", "quelle commune pour investir", "meilleures communes ou investir"),
     ("communes", "Communes")),
    # Baromètre retiré du menu → l'évolution du marché + le Rapport PDF vivent dans l'onglet
    # « Évolution » de Communes. La concept-route y mène (plus de lien vers un outil absent).
    (("barometre", "état du marché foncier", "etat du marche foncier", "barometre foncier"),
     ("communes", "Communes")),
    # §3 (23/08/2026) — « Radar permis » + « Permis au point mort » fusionnés en UN outil « Permis ».
    # Le radar : la clé `permis` ouvre la carte des permis. Label recablé « Radar permis » → « Permis ».
    (("radar permis", "qui construit quoi", "qui construit a", "qui construit dans",
      "quels permis dans la commune"), ("permis", "Permis")),
    # Le « point mort » est désormais un FILTRE de l'outil Permis : la clé `promesses` reste (ALIASÉE) et
    # ouvre l'outil avec le filtre déjà actif. On GARDE tous les anciens mots-clés (« promesses mortes »…).
    (("permis au point mort", "permis non lancés", "permis non lances", "promesses mortes",
      "permis jamais sortis", "permis jamais construits", "permis anciens jamais", "permis abandonnes"),
     ("promesses", "Permis au point mort")),
    # 21/08/2026 — outil « Simulateur ZAN » retiré (DORMANT) : router vers lui = lien mort. L'enveloppe ZAN
    # (budget/reste/%) vit désormais dans l'outil « Communes » → la concept-route y mène.
    (("simulateur zan", "artificialisation", "contrainte d'artificialisation", "contrainte zan",
      "zan de la commune", "objectif zan"), ("communes", "Communes")),
    (("rarete du foncier", "rarete foncier", "le foncier se rarefie", "ou le foncier se rarefie",
      "combien de constructible reste"), ("communes", "Communes")),
    # §5 — outil renommé « Densifier l'existant » (libellé client) ; clé interne `renouvellement`
    # INCHANGÉE. Anciens mots-clés CONSERVÉS + nouveaux (« densifier »…) ajoutés.
    (("potentiel de renouvellement", "renouvellement du territoire", "outil renouvellement",
      "vue renouvellement du", "densifier", "densification de l'existant", "densification de l existant",
      "construire plus", "surelever", "surélever"), ("renouvellement", "Densifier l'existant")),
    (("changement de plu", "si cette zone passait", "zone passait constructible",
      "si cette zone devenait constructible", "zone devenait constructible",
      "prospective de territoire", "simuler un plu", "simuler un changement de zonage"),
     ("simulplu", "Changement PLU")),
    # Retiré du produit le 21/08/2026 (DORMANT) : outil « Quoi de neuf » (o10-bascules). Sa concept-route
    # est SUPPRIMÉE — router vers un module absent = lien mort (piège attrapé sur « Foncier fantôme »).
    # Ces demandes retombent sur le traitement normal du Copilote. Le flux d'événements reste servi
    # ailleurs (la cloche de notifications lit le même endpoint /events).
    # 21/08/2026 — outil « Suivi de secteur » (o7-carnet) retiré (DORMANT) : concept-route SUPPRIMÉE
    # (router vers un module absent = lien mort, piège Foncier fantôme). Le VRAI suivi = la Veille ;
    # ces demandes retombent sur le traitement normal du Copilote (mission VEILLE / surveillance).
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
    """Ce que LABUSE SAIT déjà sur une parcelle citée (fond), sans outil. RETOURS-8 (R12) — enrichi du
    VERDICT servi (même source que la fiche, `_q_v2_fiche`) pour un résumé plus riche que « surface·zone »."""
    if not idu:
        return ""
    from .outils import fiche_parcelle
    r = fiche_parcelle(db, idu=idu)
    if not r.ok:
        return ""
    d = r.data
    bout = [f"{d['surface_m2']} m²" if d.get("surface_m2") else None,
            f"zone {d['zone']}" if d.get("zone") else None,
            f"à {d['commune']}" if d.get("commune") else None,
            f"verdict LABUSE : {d['verdict']}" if d.get("verdict") else None]
    return " · ".join(x for x in bout if x)


_COUVRE = ("LABUSE couvre les données foncières et de marché : parcelles (comptage, surface, zonage, "
           "verdict), prix et délais d'instruction par commune, patrimoine des sociétés.")


def _sans_outil(db: Session, message: str, params: dict, intent: str, motif: str | None = None,
                history: list[dict] | None = None) -> dict:
    """Aucun outil LABUSE ne couvre la demande. COPILOTE-REFONTE — plus de MUR « je n'ai pas d'outil
    dédié » : la division garde sa voie (règlement, jamais trancher) ; une parcelle citée reçoit ce que
    LABUSE en sait + la voie fiche ; SINON on bascule sur la CONNAISSANCE GÉNÉRALE (voie b, badgée) —
    le Copilote dit ce qu'il sait de plus proche plutôt qu'un refus sec."""
    m = _fold_py(message.lower())
    idu = params.get("idu")
    if "divis" in m or "decoup" in m or "detacher un lot" in m or "lotir" in m:
        telemetrie.refus(db, "aucun_outil", message, intent)
        return _division(db, idu, intent)
    # RETOURS-8 (R12) — une intention COUVERTE par un outil (pièges/risques, taxe, faisabilité…) OUVRE
    # l'outil (prérempli IDU) : le message « pas de mesure LABUSE dédiée » ne peut plus apparaître pour
    # une intention couverte — soit on répond, soit on ouvre l'outil.
    if _match_outil(message):
        return _outil(db, message, params)
    if idu:
        # RETOURS-8 (R12) — une PARCELLE est citée : on RÉPOND avec la vraie donnée (même fond que la
        # fiche : surface, zone, commune, verdict) + la voie fiche pour la synthèse complète. Plus de
        # mur « pas de mesure dédiée » : on dit ce que LABUSE sait, puis on tend la fiche.
        telemetrie.refus(db, "aucun_outil", message, intent)
        fond = _substance(db, idu)
        txt = (f"Sur la parcelle {idu} : {fond}. Pour l'analyse complète (constructibilité, risques, "
               f"marché), ouvrez la fiche." if fond
               else "Je n'ai pas de mesure LABUSE dédiée à cette demande précise. " + _COUVRE)
        return _reply(txt, intent, refus="aucun_outil",
                      voie={"cible": "fiche", "libelle": "Ouvrir la fiche", "idu": idu})
    # ni parcelle ni donnée : c'est une question de CONNAISSANCE GÉNÉRALE → voie b (honnête, badgée).
    return _general(db, message, history)


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
    # M129-C (Vic 19/08/2026) : l'enrichissement M82 (score géométrique module_division) est RETIRÉ —
    # la division sort du produit. Reste le refus honnête (réglementaire > géométrique) + la porte PLU.
    txt += mesure
    txt += " Je peux ouvrir l'Annuaire PLU pour le règlement applicable — à vous de conclure."
    # M137-P — les 3 outils PLU (annuaire, procédure, changement) fusionnés dans l'outil unique « plu » ;
    # le prefill_plu ouvre le hub directement sur l'Annuaire (règlement de la zone).
    return _reply(txt, intent, refus="aucun_outil", porte="plu", prefill="pluPrefill",
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
