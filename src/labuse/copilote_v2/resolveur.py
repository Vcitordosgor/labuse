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
# CHASSE-FIX-1 (B-5) — articles/prépositions à IGNORER quand on juge si une VOIE et une COMMUNE
# saisies correspondent vraiment à une candidate (ne comptent pas comme des mots de voie significatifs).
_ARTICLES_PREP = frozenset((
    "a", "au", "aux", "le", "la", "les", "l", "de", "du", "des", "d", "et", "sur", "sous", "en",
))
_RE_CP5 = re.compile(r"^\d{5}$")

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


def _mots_adresse(adresse: str) -> tuple[list[str], list[str], str | None]:
    """CHASSE-FIX-1 (B-5) — sépare les mots SIGNIFICATIFS de la VOIE et de la COMMUNE saisies, et le
    code postal. Sert à vérifier qu'une candidate correspond VRAIMENT (sa voie ET sa commune), et pas
    au seul mot-type « avenue » + numéro. Significatif = longueur ≥ 3, hors articles/prépositions, hors
    mots-types de voie (chemin/rue/avenue…), hors code postal. `adresse` = fragment déjà plié (tokens
    [0-9a-z] séparés par des espaces, cf. `_extraire_adresse`)."""
    toks = adresse.split()
    cp = next((t for t in toks if _RE_CP5.match(t)), None)
    vi = next((i for i, t in enumerate(toks) if t in _VOIE_KW), None)
    if cp is not None:                                   # frontière voie|commune = le code postal
        bound = toks.index(cp)
        commune_raw = toks[bound + 1:]
    else:                                                # sinon un « a »/« au » isolé après la voie
        debut = (vi + 2) if vi is not None else 1
        sep = next((i for i in range(debut, len(toks)) if toks[i] in ("a", "au", "aux")), None)
        if sep is not None:
            bound, commune_raw = sep, toks[sep + 1:]
        else:
            bound, commune_raw = len(toks), []
    voie_raw = toks[((vi + 1) if vi is not None else 0):bound]

    def _sig(ts: list[str]) -> list[str]:
        return [t for t in ts if len(t) >= 3 and t not in _ARTICLES_PREP
                and t not in _VOIE_KW and not _RE_CP5.match(t)]
    return _sig(voie_raw), _sig(commune_raw), cp


def _resoudre_adresse(db: Session, message: str) -> Resolution | None:
    """Résout une adresse en parcelle(s) via la MÊME grammaire que l'omnibox (`_sugg_adresse`), avec
    relaxe par jetons : on retire le dernier jeton tant que la recherche ne rend rien (un quartier
    hors toponyme officiel — « La Montagne » pour 97417 Saint-Denis — ne doit pas tout faire échouer).

    CHASSE-FIX-1 (B-5) — la relaxe dépouillait jusqu'au seul mot-type « avenue » + numéro, puis
    matchait des voies ARBITRAIRES d'une autre commune sur le seul numéro, présentées comme des
    correspondances sûres (« 777 avenue bidon à Gotham » → 781 Avenue de Bourbon, 97440 Saint-André).
    Désormais une candidate n'est RETENUE que si la VOIE **et** la COMMUNE saisies correspondent ;
    sinon « adresse introuvable », avec les candidates PROCHES (voie seule) proposées, jamais imposées."""
    from ..api.recherche import _sugg_adresse
    extrait = _extraire_adresse(message)
    if extrait is None:
        return None
    adresse, num = extrait
    voie_sig, commune_sig, cp = _mots_adresse(adresse)
    toks = adresse.split()
    cands: list[dict] = []
    needle = adresse
    while len(toks) >= 2:
        r = [x for x in _sugg_adresse(db, " ".join(toks), 8) if x.get("idu")]
        if r:
            cands, needle = r, " ".join(toks)
            break
        toks = toks[:-1]
    if not cands:
        # rien ne matche : si un numéro de voie était donné (vraie tentative d'adresse) → introuvable ;
        # sinon (simple mention de voie dans une phrase) → None, le flux normal reprend la main.
        return _introuvable(needle) if num is not None else None
    # dédup par idu (l'ordre de l'omnibox = la pertinence).
    vus: set[str] = set()
    uniques: list[dict] = []
    for c in cands:
        if c["idu"] in vus:
            continue
        vus.add(c["idu"])
        uniques.append({"idu": c["idu"], "label": c.get("label") or c["idu"], "sub": c.get("sub") or ""})

    # CHASSE-FIX-1 (B-5) — valide VOIE et COMMUNE. `voie_ok` : tous les mots significatifs de la voie
    # figurent dans le libellé de la candidate. `commune_ok` : aucune commune/CP nommé, OU la commune/CP
    # de la candidate correspond. `proches` = voie seule (candidates à PROPOSER) ; `retenues` = voie ET
    # commune (une correspondance sûre).
    def _voie_ok(c: dict) -> bool:
        lab = set(_tokens(c["label"] + " " + c["sub"]))
        return all(t in lab for t in voie_sig) if voie_sig else True

    def _commune_ok(c: dict) -> bool:
        if not commune_sig and not cp:
            return True
        sub = set(_tokens(c["sub"]))
        if cp and cp in sub:
            return True
        return bool(commune_sig) and all(t in sub for t in commune_sig)

    proches = [c for c in uniques if _voie_ok(c)]
    retenues = [c for c in proches if _commune_ok(c)]
    if not retenues:
        if num is not None:
            return _introuvable(needle, candidats=proches[:MAX_CANDIDATS])
        return None
    # numéro demandé → les candidates qui le PORTENT exactement (le reste = voisins de numéro).
    if num is not None:
        exacts = [c for c in retenues if _lead_num(c["label"]) == num]
        if len(exacts) == 1:
            return Resolution("idu", idu=exacts[0]["idu"], requete=needle, famille="adresse")
        if len(exacts) > 1:
            retenues = exacts
    if len(retenues) == 1:
        return Resolution("idu", idu=retenues[0]["idu"], requete=needle, famille="adresse")
    return Resolution("candidats", candidats=retenues[:MAX_CANDIDATS], requete=needle, famille="adresse")


def _introuvable(needle: str, candidats: list[dict] | None = None) -> Resolution:
    """CHASSE-FIX-1 (B-5) — la voie/commune saisies ne correspondent à aucune parcelle. Honnête :
    « adresse introuvable », avec les candidates proches (voie seule) à PROPOSER si on en a."""
    return Resolution("introuvable", candidats=candidats or [], requete=needle, famille="adresse")


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


def message_introuvable(res: Resolution) -> str:
    """CHASSE-FIX-1 (B-5) — la voie et la commune saisies ne désignent aucune parcelle. On le DIT,
    sans imposer une parcelle au hasard. Si des voies PROCHES existent (même nom, autre commune ou
    numéro voisin), on les PROPOSE explicitement comme pistes à confirmer, jamais comme la réponse."""
    if res.candidats:
        lignes = "\n".join(f"• {c['label']}" + (f" — {c['sub']}" if c["sub"] else "") + f"  ({c['idu']})"
                           for c in res.candidats)
        return ("Adresse introuvable — aucune parcelle ne correspond à cette voie dans cette commune.\n"
                "Vouliez-vous dire l'une de celles-ci ?\n" + lignes + "\n"
                "Donnez l'adresse complète (voie + commune), le code postal, ou l'identifiant (14 caractères).")
    return ("Adresse introuvable — aucune parcelle ne correspond à cette voie dans cette commune. "
            "Vérifiez la voie et la commune, ou donnez l'identifiant de la parcelle (14 caractères).")
