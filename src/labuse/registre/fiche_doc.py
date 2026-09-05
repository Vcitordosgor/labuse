"""CIRCUIT-2 lot 2 — LE DOCUMENT « la fiche, donnée par donnée », GÉNÉRÉ depuis le registre
(`labuse registre fiche parcelle` → docs/CIRCUIT/FICHE-PARCELLE-DONNEES.md ; `labuse registre
fiche autres` → FICHES-DONNEES.md pour commune, annonce, propriétaire, soleil).

C'est le document que Vic lit : une ligne par donnée, en français, sans le code — id, type,
libellé, source(s) et millésime servis, chemin (moteur ou passe-plat, fichier), portée, états
possibles, et OÙ AILLEURS la donnée s'affiche (couches, outils, autres fiches, PDF, Copilote,
mails). Le générateur ne saisit rien deux fois : tout vient de donnees.py + robinets.py ; les
millésimes viennent de data_sources quand une base est ouverte (sinon « (base fermée) »).
"""
from __future__ import annotations

from datetime import date

from .donnees import DONNEES
from .robinets import ROBINETS
from .valeur import _millesimes

#: catégorie de robinet → étiquette lisible du « où ailleurs »
_CAT = {"couche": "couche", "fond": "fond de carte", "outil": "outil", "fiche": "fiche",
        "copilote": "Copilote", "veille": "veilles", "projets": "projets", "crm": "CRM",
        "notification": "notifications/mails", "pdf": "PDF", "page_client": "page publique",
        "admin": "admin"}

_ETATS = {"nombre": "servie · non couverte (n sous seuil, dit) · non calculée",
          "classe": "servie · non déterminée (la source ne dit pas) · non calculée",
          "texte": "servie · non déterminée · non calculée",
          "liste": "servie (possiblement vide, dit) · non calculée",
          "geometrie": "servie · non calculée",
          "couche": "servie · non fabriquée (eau ancienne dite)"}


def _ailleurs(cid: str, robinet_courant: str) -> str:
    autres = [(rid, r) for rid, r in ROBINETS.items()
              if cid in r.chiffres and rid != robinet_courant]
    if not autres:
        return "nulle part ailleurs"
    return " · ".join(f"{_CAT.get(r.categorie, r.categorie)} « {r.nom} »" for _, r in autres)


def _sources(d, mill: dict) -> str:
    if d.portee == "projet":
        return "saisie du client (aucun réservoir)"
    if not d.reservoirs:
        return "interne (aucun réservoir)"
    parts = []
    for rid in d.reservoirs:
        m = mill.get(rid)
        parts.append(f"{rid} ({m})" if m else rid)
    return ", ".join(parts)


def _chemin(d) -> str:
    tete = f"moteur `{d.moteur}`" if d.moteur else \
        ("passe-plat" if d.calcul == "passe_plat" else d.calcul)
    extra = f" — table lue : {d.table}" if d.table and d.type not in ("couche",) else ""
    fab = f" — fabrication : {d.fabrication}" if d.fabrication else ""
    return f"{tete} · {d.fonction}{extra}{fab}"


def _ligne(cid: str, rid: str, mill: dict) -> str:
    d = DONNEES[cid]
    dom = f" — domaine : {', '.join(d.domaine)}" if d.domaine else ""
    return (f"| `{cid}` | {d.type}{dom} | {d.libelle} | {_sources(d, mill)} | "
            f"{_chemin(d)} | {d.portee} | {_ETATS.get(d.type, 'servie')} | "
            f"{_ailleurs(cid, rid)} |\n| | | *{d.definition}* | | | | | |")


def _tableau(rids: list[str], mill: dict, titre_niveau: str = "##") -> list[str]:
    out: list[str] = []
    for rid in rids:
        r = ROBINETS[rid]
        out.append(f"\n{titre_niveau} {r.nom}\n")
        out.append(f"*Robinet `{rid}` — route `{r.route}`*\n")
        if not r.chiffres:
            out.append(f"> {r.hors_registre}\n")
            continue
        out.append("| id | type | libellé | source(s) et millésime | chemin | portée | états | où ailleurs |")
        out.append("|---|---|---|---|---|---|---|---|")
        for cid in r.chiffres:
            out.append(_ligne(cid, rid, mill))
    return out


def _millesimes_de(rids: list[str], db) -> dict:
    res: set[str] = set()
    for rid in rids:
        for cid in ROBINETS[rid].chiffres:
            res |= set(DONNEES[cid].reservoirs)
    if db is None:
        return {r: "(base fermée)" for r in res}
    return _millesimes(db, res)


def doc_fiche_parcelle(db=None) -> str:
    rids = [rid for rid in ROBINETS if rid.startswith("fiche_parcelle")]
    mill = _millesimes_de(rids, db)
    lignes = [
        "# FICHE PARCELLE — donnée par donnée",
        "",
        f"*Généré du registre le {date.today().isoformat()} par `labuse registre fiche parcelle` "
        "(le code est la vérité — ne pas éditer à la main ; relu avant commit).*",
        "",
        "Chaque section est un tiroir de la fiche. Pour chaque donnée : d'où elle vient (source et "
        "millésime servis), par quel chemin (moteur nommé ou passe-plat), sa portée (`run` = change "
        "à la bascule · `live` = à l'injection · `projet` = saisie du client), ses états possibles, "
        "et où ailleurs elle s'affiche.",
    ]
    lignes += _tableau(rids, mill)
    return "\n".join(lignes) + "\n"


def doc_autres_fiches(db=None) -> str:
    familles = [
        ("Fiche commune", [rid for rid in ROBINETS if rid.startswith("fiche_commune")]),
        ("Fiche annonce (Radar)", ["fiche_annonce"]),
        ("Fiche propriétaire", ["fiche_proprietaire"]),
        ("Fiche soleil", ["fiche_soleil"]),
    ]
    tous = [rid for _, rids in familles for rid in rids]
    mill = _millesimes_de(tous, db)
    lignes = [
        "# FICHES — donnée par donnée (commune · annonce · propriétaire · soleil)",
        "",
        f"*Généré du registre le {date.today().isoformat()} par `labuse registre fiche autres` "
        "(même format que FICHE-PARCELLE-DONNEES.md, plus court).*",
    ]
    for titre, rids in familles:
        lignes.append(f"\n# {titre}")
        lignes += _tableau(rids, mill, titre_niveau="##")
    return "\n".join(lignes) + "\n"
