"""RECETTE-7 lot 0 (Z5) — LA PROVENANCE DES NOMBRES IMPRIMÉS.

Le trou de conception attrapé en RECETTE-7 : un calcul peut fabriquer un nombre dans son coin
et l'imprimer dans un document sans passer par le registre CIRCUIT — la sonde, qui ne compare
que des *lecteurs déclarés*, ne peut pas le voir (un producteur non déclaré est invisible).

Ce module ferme le trou côté DOCUMENTS : il prend un document construit (`builder.construire`)
et confronte CHAQUE nombre imprimé aux valeurs RÉELLEMENT servies par le registre pour ce
document (les `Valeur` de la collecte + le contexte Financier/Apporteur). Un nombre qui ne se
rattache à aucune donnée du registre — ni à la liste blanche des nombres de STRUCTURE (numéro de
page, millésime du modèle, seuils de loi cités, dates) — est une FUITE.

Le test Z5 (`tests/test_circuit_provenance.py`, aussi joué par la sonde) génère les documents
sur les quatre témoins, passe chaque nombre au crible et fait ÉCHOUER la construction sur la
moindre fuite. C'est ce test qui règle le problème une fois pour toutes.

Note d'implémentation : on lit le HTML de `construire()` (pas le PDF) — la mise en page
WeasyPrint ne change pas les nombres, seulement leur position. Le test tourne donc sans
WeasyPrint ni pdftotext, avec la seule base (marqueur `db`/`local`).
"""
from __future__ import annotations

import re
from typing import Any

from ..registre.chiffres import CHIFFRES
from ..registre.valeur import Valeur

# ── Extraction des nombres d'un texte français ──────────────────────────────────────────────
# Un nombre = suite de chiffres, séparateurs de milliers (espace fine insécable U+202F, espace
# insécable U+00A0, espace ordinaire) et décimale (virgule OU point — le point est fautif mais
# on veut quand même le rattacher, cf. E9). On rattache l'unité qui suit pour le contexte.
_SEP = "    "
_NOMBRE = re.compile(
    rf"(?<![\w.,])(\d{{1,3}}(?:[{_SEP}]\d{{3}})+|\d+)(?:[.,](\d+))?(?![\w])")

# Contextes où un « nombre » n'en est pas un (référence, identifiant) — on ne le rattache pas.
# Article de loi (L151-36, R111-22, L. 331), n° de rapport, référence — cité en clair.
_REF_AVANT = re.compile(r"(?:art\.?|L\.?|R\.?|D\.?|n°|numéro|référence|réf\.?)\s*[\dLRD.\-]*$",
                        re.IGNORECASE)

#: motifs STRUCTURELS retirés du texte AVANT extraction — ce ne sont pas des grandeurs de
#: données : IDU, n° de rapport, dates, millésimes trimestriels, codes postaux, références
#: cadastrales courtes, articles de loi. Chaque motif est neutralisé (blanc de même longueur).
_STRUCTURE = [
    re.compile(r"\b\d{14}\b"),                       # IDU cadastral (97411000AV0110)
    re.compile(r"\b[A-Z]{2}-\d{8}-\d{3,4}\b"),       # n° de rapport (DP-20260909-0110)
    re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b"),      # date jj/mm/aaaa
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),            # date aaaa-mm-jj
    re.compile(r"\b\d{4}[_-]T[1-4]\b"),              # millésime trimestriel (2026_T1)
    re.compile(r"\b974\d{2}\b"),                     # code postal réunionnais (974xx)
    re.compile(r"\b[A-Z]{1,2}\s?\d{3,4}\b"),        # référence cadastrale courte (DH 1880)
    re.compile(r"\b[LRD]\.?\s?\d+(?:[.\-]\d+)*\b"),  # article de loi (L151-36, R111-22)
    re.compile(r"\bart(?:icle)?s?\.?\s+[A-Za-z]{1,4}\.?\s?\d+(?:[.\-]\d+)*", re.IGNORECASE),
]


def _f(entier: str, dec: str | None) -> float:
    e = re.sub(rf"[{_SEP}]", "", entier)
    return float(f"{e}.{dec}") if dec else float(e)


def nombres_imprimes(texte: str) -> list[tuple[float, str]]:
    """Les nombres imprimés d'un texte, avec un extrait de contexte (±30 car.). Les tokens
    STRUCTURELS (IDU, n° de rapport, dates, codes postaux, références, articles) sont neutralisés
    d'abord ; un nombre collé à une référence de loi restante est aussi ignoré."""
    for motif in _STRUCTURE:
        texte = motif.sub(lambda m: " " * len(m.group(0)), texte)
    out: list[tuple[float, str]] = []
    for m in _NOMBRE.finditer(texte):
        avant = texte[max(0, m.start() - 12):m.start()]
        if _REF_AVANT.search(avant.strip()):
            continue
        ctx = texte[max(0, m.start() - 30):min(len(texte), m.end() + 12)].replace("\n", " ")
        out.append((_f(m.group(1), m.group(2)), re.sub(r"\s+", " ", ctx).strip()))
    return out


# ── Les valeurs ANCRÉES : tous les nombres atteignables depuis le registre pour ce document ──

def _scalaires(v: Any) -> list[float]:
    """Tous les nombres scalaires atteignables dans une valeur (scalaire, dict, liste)."""
    out: list[float] = []
    if isinstance(v, bool):
        return out
    if isinstance(v, (int, float)):
        out.append(float(v))
    elif isinstance(v, dict):
        for x in v.values():
            out += _scalaires(x)
    elif isinstance(v, (list, tuple)):
        for x in v:
            out += _scalaires(x)
    elif isinstance(v, str):
        # une valeur textuelle peut porter un nombre déjà formaté (ex. dénomination) — on le lit
        for mm in _NOMBRE.finditer(v):
            out.append(_f(mm.group(1), mm.group(2)))
    return out


def nombres_ancres(valeurs: dict[str, Valeur], ctx: dict | None = None) -> dict[float, str]:
    """{nombre → chiffre_id} pour tout nombre servi par le registre dans ce document.
    On indexe l'ENTIER arrondi ET la valeur à une décimale (les blocs arrondissent au m²/€ mais
    gardent une décimale pour les %, m). Le contexte Financier/Apporteur (bilan dérivé, plan)
    est rattaché à la donnée dont il découle quand elle est au registre, sinon à la liste blanche."""
    ancres: dict[float, str] = {}

    def _poser(x: float, cid: str) -> None:
        for k in {round(x), round(x, 1), round(x, 2), float(x)}:
            ancres.setdefault(float(k), cid)

    def _poser_argent(x: float, cid: str) -> None:
        """Un montant du bilan est imprimé en €, en k€ (÷1000) et parfois en valeur absolue
        (une charge NÉGATIVE affichée « -79 k€ »). On pose toutes ces formes."""
        for base in (x, abs(x)):
            _poser(base, cid)
            _poser(base / 1000.0, cid)

    for cid, v in valeurs.items():
        for x in _scalaires(v.valeur):
            _poser(x, cid)
        # la trace de source (pied) imprime le millésime/couverture de chaque réservoir servi
        # (ex. « Arcep 2026_T1 — 330 051 immeubles 974 ») : ces nombres décrivent la SOURCE, pas
        # la parcelle — rattachés au chiffre dont ils portent la provenance, jamais une fuite.
        for mil in (v.reservoirs or {}).values():
            for x in _scalaires(mil):
                _poser(x, cid)
    # contexte Financier : le bilan est DÉRIVÉ des surfaces (registre) et des hypothèses SAISIES
    # (données `projet` du registre) — chaque poste chiffré est rattaché à `charge_fonciere_eur`
    # (la donnée-tête du bilan) faute d'un id propre par poste ; la liste blanche porte la raison.
    if ctx:
        # le bilan à rebours (charge_fonciere_eur et sa décomposition : CA, coûts, marge, charge
        # supportable, grille de sensibilité) — dérivé des surfaces (registre) et des hypothèses
        # SAISIES (données `projet` du registre) ; imprimé en €/k€, signé.
        for x in _scalaires(ctx.get("bilan")):
            _poser_argent(x, "charge_fonciere_eur")
        for x in _scalaires(ctx.get("program")):
            _poser_argent(x, "capacite_logements")
        # chaque hypothèse résolue EST une donnée *_saisi_*/prefill du registre : sa valeur ET la
        # source (qui justifie un pré-remplissage, ex. « ~9 mois + 20 mois de chantier ») sont
        # rattachées à son id.
        for fid, d in (ctx.get("resolved") or {}).items():
            if isinstance(d, dict):
                for x in _scalaires(d.get("valeur")):
                    _poser_argent(x, fid)
                for x in _scalaires(d.get("source")):
                    _poser(x, fid)
        for x in _scalaires(ctx.get("tfpb")):
            _poser(x, "taux_lls_pct")
        for x in _scalaires(ctx.get("zonage_abc")):
            _poser(x, "statut_plu")
        for x in _scalaires((ctx.get("voisines") or {})):
            _poser(x, "assemblage_surface_m2")
        # l'adresse (numéro de voie) est une donnée d'identité (adresse_ban), pas une grandeur —
        # rattachée pour ne pas la compter comme fuite quand un document l'imprime hors Valeur.
        for x in _scalaires(ctx.get("adresse")):
            _poser(x, "adresse_ban")
    return ancres


# ── La liste blanche des nombres de STRUCTURE (pas des grandeurs de données) ─────────────────
#: nombre → raison (documentée, jointe au rapport). Un nombre de structure n'est pas une donnée.
ALLOWLIST: dict[float, str] = {
    2.0: "version du modèle de document (builder.MODELE_VERSION)",
    90.0: "durée de validité du brief apporteur (90 jours, constante d'affichage)",
    100.0: "base de pourcentage (100 %)",
    800.0: "seuil légal L151-36 (800 m) cité en clair — référence de droit, pas une mesure",
    2.5: "plafond légal de la part départementale de la taxe (2,5 %) — référence de droit",
    60.0: "libellé de tranche d'âge INSEE (« 60 ans et plus ») — définition, pas une mesure",
    8.5: "taux légal de TVA sur le logement neuf à La Réunion (8,5 %) — référence de droit",
    2.1: "taux légal de TVA réduit locatif à La Réunion (2,1 %) — référence de droit",
    5.0: "pas de la grille de sensibilité du bilan (±5 %) — paramètre d'affichage",
    974.0: "code du département (La Réunion) cité dans un descriptif de source",
    1990.0: "borne du libellé INSEE « bâti avant 1990 » — définition, pas une mesure",
    0.0: "zéro explicite (rien à construire, aucun aléa) — jamais une valeur inventée",
    2024.0: "millésime/année de source cité", 2025.0: "millésime/année de source cité",
    2026.0: "millésime/année de source cité", 2023.0: "millésime/année de source cité",
    2022.0: "millésime/année de source cité", 2021.0: "millésime/année de source cité",
}
#: années plausibles laissées passer comme millésimes (1990..2035) — citées dans les sources.
_ANNEES = set(float(a) for a in range(1990, 2036))


def _allowliste(x: float) -> str | None:
    if x in ALLOWLIST:
        return ALLOWLIST[x]
    if x in _ANNEES:
        return "millésime/année de source cité"
    return None


# ── Le crible ────────────────────────────────────────────────────────────────────────────────

def _texte_de(html: str) -> str:
    """Texte visible d'un fragment HTML (les nombres, pas la mise en page). On retire le
    contenu des attributs (les data:image base64 du plan portent des chiffres qui ne sont PAS
    imprimés) puis les balises."""
    sans_tete = re.sub(r'(?is)<(style|script|head)\b.*?</\1>', ' ', html)  # CSS/JS/tête @font-face
    sans_img = re.sub(r'<img[^>]*>', ' ', sans_tete)      # les images (base64) ne s'impriment pas
    sans_attr = re.sub(r'<[^>]+>', ' ', sans_img)         # balises → espace
    import html as _h
    return _h.unescape(sans_attr)


def fuites(document: str, valeurs: dict[str, Valeur], texte_ou_html: str,
           ctx: dict | None = None, *, est_html: bool = True) -> list[dict]:
    """Les nombres imprimés du document NON rattachés à une donnée du registre ni à la liste
    blanche. Chaque fuite : {document, nombre, contexte, raison}."""
    texte = _texte_de(texte_ou_html) if est_html else texte_ou_html
    ancres = nombres_ancres(valeurs, ctx)
    dehors: list[dict] = []
    for x, contexte in nombres_imprimes(texte):
        if float(x) in ancres or round(x) in ancres or round(x, 1) in ancres:
            continue
        if _allowliste(x) is not None:
            continue
        dehors.append({"document": document, "nombre": x, "contexte": contexte,
                       "raison": "aucune donnée du registre ne porte ce nombre"})
    return dehors


def inventaire(document: str, valeurs: dict[str, Valeur], html: str,
               ctx: dict | None = None) -> list[dict]:
    """Z2 — l'inventaire : chaque nombre imprimé, son contexte, l'identifiant de la donnée du
    registre dont il provient (ou « FUITE »/« structure »). Pour le rapport."""
    texte = _texte_de(html)
    ancres = nombres_ancres(valeurs, ctx)
    lignes: list[dict] = []
    for x, contexte in nombres_imprimes(texte):
        cid = ancres.get(float(x)) or ancres.get(round(x)) or ancres.get(round(x, 1))
        structure = _allowliste(x)
        lignes.append({"document": document, "nombre": x, "contexte": contexte,
                       "chiffre_id": cid, "structure": structure,
                       "etat": "rattaché" if cid else ("structure" if structure else "FUITE")})
    return lignes
