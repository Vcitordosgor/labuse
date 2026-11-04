"""COPILOTE-5 — RÉSOLUTION D'ENTRÉE : la PREMIÈRE étape du Copilote.

Les TROIS familles de l'omnibox deviennent la première étape du Copilote :
  · ADRESSE (BAN interne) — « 3 chemin de la Citerne, 97417 La Montagne » ;
  · RÉFÉRENCE CADASTRALE courte — « BZ 1065 », « la parcelle BZ1065 » (l'IDU complet 14 car. est
    déjà capté en amont par `_idu_dans`) ;
  · PROPRIÉTAIRE — « les parcelles de la SCI ALOE » (résolu par l'outil `parcelles_par_entreprise`).

Une adresse est résolue en PARCELLE **avant toute réponse** ; s'il y a plusieurs candidates, le
Copilote les PROPOSE (il ne tire jamais au hasard). Une référence/propriétaire suit la même logique.

MÊME point de calcul que la barre de recherche : on appelle EXACTEMENT les grammaires du suggest
(`api.recherche._sugg_adresse` / `_sugg_cadastre`), jamais une 2e source ni une requête maison.
Déterministe — aucun appel modèle : le Copilote résout comme l'omnibox résout.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from .outils import _fold_py

# ── Mots-types de voie réunionnais (déclencheur d'une recherche d'adresse) — cherchés comme JETONS
# (membres de la liste de tokens), jamais en sous-chaîne (sinon « route » matcherait « déroute »). ──
_VOIE_KW = frozenset(_fold_py(w) for w in (
    "chemin", "rue", "route", "impasse", "allee", "allée", "boulevard", "bd", "avenue", "av",
    "ruelle", "cite", "cité", "residence", "résidence", "lotissement", "sentier", "cours",
    "quai", "montee", "montée", "traverse", "chaussee", "chaussée", "passage", "hameau",
    "rampe", "ravine", "radier", "cd", "rn", "rd",
))
# rep (bis/ter/…) qui peut s'intercaler entre le numéro et la voie (« 4 bis Chemin … »).
_REP = frozenset(("bis", "ter", "quater", "a", "b", "c", "d", "e"))
_RE_NUM = re.compile(r"^\d{1,4}$")
_RE_LEAD_NUM = re.compile(r"^\s*(\d{1,4})\b")
# référence cadastrale courte dans une phrase : « BZ 1065 », « bz1065 » (1-2 lettres + 1-4 chiffres).
_RE_REF = re.compile(r"\b([A-Za-z]{1,2})\s?(\d{1,4})\b")
# Un IDU complet (14 car.) : traité en amont (`_idu_dans`) — on ne le re-résout pas ici.
_RE_IDU = re.compile(r"\b\d{5}[0-9A-Za-z]{9}\b")

MAX_CANDIDATS = 5


@dataclass
class Resolution:
    """Le résultat de la résolution d'entrée. `kind` :
      · "idu"      — une parcelle UNIQUE résolue (on sert sa fiche) ;
      · "candidats"— plusieurs candidates (on les propose, jamais un tir au hasard)."""
    kind: str
    idu: str | None = None
    candidats: list[dict] = field(default_factory=list)   # [{idu, label, sub}]
    requete: str = ""        # ce qui a été cherché (message honnête)
    famille: str = ""        # "adresse" | "cadastre"


def _tokens(message: str) -> list[str]:
    """Jetons alphanumériques du message plié (accents retirés, minuscules)."""
    return [t for t in re.split(r"[^0-9a-z]+", _fold_py((message or "").lower())) if t]


def _extraire_adresse(message: str) -> tuple[str, int | None] | None:
    """Extrait la portion ADRESSE d'un message en langage naturel et le numéro de tête s'il existe.
    Rend (texte_adresse, numero|None), ou None si aucune voie n'est nommée. On part du numéro (ou du
    mot-voie) jusqu'à la FIN (le CP et la commune aident la résolution ; la relaxe par jetons les
    laisse tomber si besoin)."""
    toks = _tokens(message)
    idx = next((i for i, t in enumerate(toks) if t in _VOIE_KW), None)
    if idx is None:
        return None
    start = idx
    num: int | None = None
    # numéro de tête : « 3 chemin », ou « 4 bis chemin » (un rep intercalé).
    if idx >= 1 and _RE_NUM.match(toks[idx - 1]):
        start = idx - 1
    elif idx >= 2 and toks[idx - 1] in _REP and _RE_NUM.match(toks[idx - 2]):
        start = idx - 2
    if _RE_NUM.match(toks[start]):
        num = int(toks[start])
    frag = toks[start:]
    # signal faible : une voie nommée nue sans numéro ni nom de voie (« c'est quoi une rue ») → pas une
    # adresse. On exige un numéro OU au moins deux jetons après le mot-voie (un vrai nom de voie).
    apres = len(toks) - idx - 1
    if num is None and apres < 2:
        return None
    return " ".join(frag), num


def _resoudre_adresse(db: Session, message: str) -> Resolution | None:
    """Résout une adresse en parcelle(s) via la MÊME grammaire que l'omnibox (`_sugg_adresse`), avec
    relaxe par jetons : on retire le dernier jeton tant que la recherche ne rend rien (un quartier
    hors toponyme officiel — « La Montagne » pour 97417 Saint-Denis — ne doit pas tout faire échouer)."""
    from ..api.recherche import _sugg_adresse
    extrait = _extraire_adresse(message)
    if extrait is None:
        return None
    adresse, num = extrait
    toks = adresse.split()
    cands: list[dict] = []
    needle = adresse
    while len(toks) >= 2:
        r = [x for x in _sugg_adresse(db, " ".join(toks), 6) if x.get("idu")]
        if r:
            cands, needle = r, " ".join(toks)
            break
        toks = toks[:-1]
    if not cands:
        return None
    # dédup par idu (l'ordre de l'omnibox = la pertinence), cap MAX_CANDIDATS.
    vus: set[str] = set()
    uniques: list[dict] = []
    for c in cands:
        if c["idu"] in vus:
            continue
        vus.add(c["idu"])
        uniques.append({"idu": c["idu"], "label": c.get("label") or c["idu"], "sub": c.get("sub") or ""})
    # numéro demandé → les candidates qui le PORTENT exactement (le reste = voisins de numéro).
    if num is not None:
        exacts = [c for c in uniques if _lead_num(c["label"]) == num]
        if len(exacts) == 1:
            return Resolution("idu", idu=exacts[0]["idu"], requete=needle, famille="adresse")
        if len(exacts) > 1:
            return Resolution("candidats", candidats=exacts[:MAX_CANDIDATS], requete=needle, famille="adresse")
    if len(uniques) == 1:
        return Resolution("idu", idu=uniques[0]["idu"], requete=needle, famille="adresse")
    return Resolution("candidats", candidats=uniques[:MAX_CANDIDATS], requete=needle, famille="adresse")


def _lead_num(label: str) -> int | None:
    m = _RE_LEAD_NUM.match(label or "")
    return int(m.group(1)) if m else None


# mots qui annoncent une référence cadastrale courte (pour ne pas confondre « R+3 », « zone U2 »…).
_REF_ANCRE = ("parcelle", "section", "cadastr")
# une question de COMPTAGE / SURFACE ne doit pas voir « de 1000 » comme une section « DE 1000 ».
_REF_STOP = ("combien", "plus de", "moins de", "superieur", "superieure", "inferieur", "au moins",
             "m2", "m²", "metres carres", "mètres carrés", "hectare")


def _resoudre_cadastre(db: Session, message: str) -> Resolution | None:
    """Résout une référence cadastrale courte (« BZ 1065 ») via `_sugg_cadastre` (même grammaire que
    l'omnibox). Déclenché seulement si le message l'ANCRE (« parcelle », « section », « cadastr… ») —
    jamais sur un « R+3 », une « zone U2 », ou un « plus de 1000 m² » de comptage. La section doit être
    écrite en MAJUSCULES (convention cadastrale « BZ 1065 ») — « de 1000 » (préposition) est ignoré."""
    if _RE_IDU.search(message or ""):
        return None                     # IDU complet → capté en amont
    m = _fold_py((message or "").lower())
    if not any(a in m for a in _REF_ANCRE) or any(s in m for s in _REF_STOP):
        return None
    from ..api.recherche import _RE_IDU_PARTIEL, _RE_SECTION_NUMERO, _sugg_cadastre
    for mm in _RE_REF.finditer(message or ""):
        if not mm.group(1).isupper():    # section cadastrale = majuscules (« BZ »), pas « de »/« la »
            continue
        ref = f"{mm.group(1).upper()}{mm.group(2)}"
        if not (_RE_SECTION_NUMERO.match(ref) or _RE_IDU_PARTIEL.match(ref)):
            continue
        r = [x for x in _sugg_cadastre(db, ref, 6) if x.get("idu")]
        if not r:
            continue
        uniques, vus = [], set()
        for c in r:
            if c["idu"] in vus:
                continue
            vus.add(c["idu"])
            uniques.append({"idu": c["idu"], "label": c.get("label") or c["idu"], "sub": c.get("sub") or ""})
        if len(uniques) == 1:
            return Resolution("idu", idu=uniques[0]["idu"], requete=ref, famille="cadastre")
        return Resolution("candidats", candidats=uniques[:MAX_CANDIDATS], requete=ref, famille="cadastre")
    return None


def resoudre(db: Session, message: str) -> Resolution | None:
    """La première étape du Copilote : résout une adresse / référence cadastrale en parcelle(s).
    Rend None si le message ne nomme ni adresse ni référence (le flux normal reprend la main).
    L'ADRESSE prime (la plus riche) ; à défaut la référence cadastrale ancrée."""
    try:
        return _resoudre_adresse(db, message) or _resoudre_cadastre(db, message)
    except Exception:  # noqa: BLE001 — une résolution qui casse ne doit pas manger la réponse
        return None


def message_candidats(res: Resolution) -> str:
    """Le message de proposition quand plusieurs parcelles correspondent (clarification honnête)."""
    quoi = "adresse" if res.famille == "adresse" else "référence"
    lignes = "\n".join(f"• {c['label']}" + (f" — {c['sub']}" if c["sub"] else "") + f"  ({c['idu']})"
                       for c in res.candidats)
    return (f"Plusieurs parcelles correspondent à cette {quoi} — laquelle ?\n{lignes}\n"
            "Donnez le numéro exact, le code postal, ou l'identifiant (14 caractères).")
