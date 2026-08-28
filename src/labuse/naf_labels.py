"""ÉTUDE DE ZONE — recherche d'activité (NAF) pour l'outil « Étude de zone ».

RECETTE-2 C4 : le référentiel n'est plus une liste curée de 34 commerces mais la NOMENCLATURE NAF
COMPLÈTE (rév. 2, 732 sous-classes, cf. `naf_nomenclature.py`). Deux façons de trouver une activité :
  · recherche libre (`chercher`) sur le LIBELLÉ officiel ET des MOTS USUELS (« notaire » atteint le
    code des activités juridiques même si le libellé ne contient pas le mot) ET le code ;
  · déroulé parcourable par FAMILLES d'activité (`familles`) — 21 sections, pour choisir sans savoir
    quoi taper.

Codes normalisés sans point (ex. 10.71C -> 1071C), comparables à `sirene_etablissements.naf`.
"""
from __future__ import annotations

import unicodedata

from .naf_nomenclature import NAF_SOUS_CLASSES, SECTIONS

# Mots USUELS (métier/enseigne) -> code NAF, pour les cas où le libellé officiel n'emploie pas le mot
# courant (« notaire » -> 6910Z « Activités juridiques »). Extensible ; complète le libellé, ne le
# remplace pas. Plusieurs mots peuvent viser le même code.
SYNONYMES: dict[str, str] = {
    "notaire": "6910Z", "notariat": "6910Z", "avocat": "6910Z", "huissier": "6910Z",
    "juriste": "6910Z", "juridique": "6910Z",
    "pharmacie": "4773Z", "pharmacien": "4773Z", "parapharmacie": "4773Z",
    "medecin": "8621Z", "docteur": "8621Z", "generaliste": "8621Z", "cabinet medical": "8621Z",
    "dentiste": "8623Z", "chirurgien-dentiste": "8623Z",
    "infirmier": "8690D", "infirmiere": "8690D", "sage-femme": "8690D",
    "veterinaire": "7500Z",
    "garage": "4520A", "garagiste": "4520A", "mecanicien": "4520A", "carrosserie": "4520B",
    "station-service": "4730Z", "carburant": "4730Z", "essence": "4730Z",
    "boulangerie": "1071C", "boulanger": "1071C",
    "patisserie": "1071D", "patissier": "1071D",
    "boucherie": "4722Z", "boucher": "4722Z", "charcuterie": "4722Z",
    "poissonnerie": "4723Z", "poissonnier": "4723Z",
    "primeur": "4721Z", "fruits et legumes": "4721Z",
    "epicerie": "4711B", "alimentation generale": "4711B", "superette": "4711B",
    "supermarche": "4711D", "hypermarche": "4711F",
    "coiffeur": "9602A", "coiffure": "9602A", "salon de coiffure": "9602A",
    "esthetique": "9602B", "institut de beaute": "9602B", "onglerie": "9602B",
    "restaurant": "5610A", "restauration": "5610A", "brasserie": "5610A",
    "snack": "5610C", "fast-food": "5610C", "restauration rapide": "5610C",
    "bar": "5630Z", "cafe": "5630Z", "debit de boissons": "5630Z", "pub": "5630Z",
    "tabac": "4726Z", "buraliste": "4726Z", "cigarette": "4726Z",
    "banque": "6419Z", "etablissement bancaire": "6419Z",
    "assurance": "6512Z", "assureur": "6512Z", "mutuelle": "6512Z",
    "agence immobiliere": "6831Z", "immobilier": "6831Z", "agent immobilier": "6831Z",
    "opticien": "4778A", "optique": "4778A", "lunettes": "4778A",
    "fleuriste": "4776Z", "fleurs": "4776Z", "jardinerie": "4776Z",
    "bijouterie": "4777Z", "bijoutier": "4777Z", "horlogerie": "4777Z",
    "librairie": "4761Z", "livres": "4761Z",
    "presse": "4762Z", "journaux": "4762Z", "papeterie": "4762Z", "maison de la presse": "4762Z",
    "habillement": "4771Z", "pret-a-porter": "4771Z", "vetements": "4771Z", "boutique de mode": "4771Z",
    "hotel": "5510Z", "hotellerie": "5510Z",
    "gite": "5520Z", "meuble de tourisme": "5520Z", "chambre d'hotes": "5520Z",
    "creche": "8891A", "garde d'enfants": "8891A", "assistante maternelle": "8891A",
    "salle de sport": "9313Z", "fitness": "9313Z", "musculation": "9313Z",
    "auto-ecole": "8553Z", "ecole de conduite": "8553Z",
    "pressing": "9601B", "blanchisserie": "9601B", "laverie": "9601B",
    "comptable": "6920Z", "expert-comptable": "6920Z", "comptabilite": "6920Z",
    "agence de voyage": "7911Z", "voyagiste": "7911Z",
    "pompes funebres": "9603Z", "funeraire": "9603Z", "marbrier": "9603Z",
    "electricien": "4321A", "plombier": "4322A", "chauffagiste": "4322B",
    "macon": "4399C", "maconnerie": "4399C", "menuisier": "4332A", "menuiserie": "4332A",
    "peintre en batiment": "4334Z", "carreleur": "4333Z", "couvreur": "4391B",
    "banque alimentaire": "4711B", "grande surface": "4711D",
}


def _norme(s: str) -> str:
    """Minuscule, sans accents — recherche tolérante (« pâtisserie » ≡ « patisserie »)."""
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.lower().strip()


def chercher(q: str, *, maxi: int = 25) -> list[dict]:
    """Cherche une activité par LIBELLÉ officiel, MOT USUEL (synonyme) ou CODE. Retour [{"code","label"}]
    trié (préfixes d'abord, puis sous-chaînes), dédupliqué, sur toute la nomenclature."""
    ql = _norme(q)
    if not ql:
        return []
    prefixes: list[dict] = []
    contient: list[dict] = []
    seen: set[str] = set()

    def add(bucket: list[dict], code: str) -> None:
        if code in seen or code not in NAF_SOUS_CLASSES:
            return
        seen.add(code)
        bucket.append({"code": code, "label": NAF_SOUS_CLASSES[code][0]})

    # 1) code exact / préfixe de code
    for code in NAF_SOUS_CLASSES:
        if _norme(code) == ql or _norme(code).startswith(ql):
            add(prefixes, code)
    # 2) mots usuels (synonymes) — « notaire » -> code juridique
    for mot, code in SYNONYMES.items():
        nm = _norme(mot)
        if nm.startswith(ql):
            add(prefixes, code)
        elif ql in nm:
            add(contient, code)
    # 3) libellé officiel (sous-chaîne accent-insensible)
    for code, (lab, _sec) in NAF_SOUS_CLASSES.items():
        nl = _norme(lab)
        if nl.startswith(ql):
            add(prefixes, code)
        elif ql in nl:
            add(contient, code)
    return (prefixes + contient)[:maxi]


def familles() -> list[dict]:
    """Nomenclature groupée par FAMILLE (section A-U) pour le déroulé parcourable :
    [{"section","nom","activites":[{"code","label"}]}], triée par code."""
    out: list[dict] = []
    for lt, nom in SECTIONS.items():
        acts = sorted(
            ({"code": c, "label": lab} for c, (lab, sec) in NAF_SOUS_CLASSES.items() if sec == lt),
            key=lambda x: x["code"])
        if acts:
            out.append({"section": lt, "nom": nom, "activites": acts})
    return out


def label(code: str) -> str | None:
    """Libellé d'un code NAF normalisé (None si hors nomenclature)."""
    entry = NAF_SOUS_CLASSES.get((code or "").replace(".", "").upper())
    return entry[0] if entry else None
