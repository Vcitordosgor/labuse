"""PLU-CALIBRAGE-1 lot 4 — LA REVUE HUMAINE des règles chiffrées proposées.

`labuse plu revue <insee>` affiche chaque proposition (`propose`) avec sa citation, zone par
zone, rubrique par rubrique, et attend une décision : [v]alider · [c]orriger (saisir la bonne
valeur) · [r]ejeter. Écrit `valide` dans le YAML (verrou V6a : un `valide` porte toujours
article + page + citation). Le geste `corriger` remplace la valeur SANS toucher à la source
(article/page/citation restent la preuve) puis passe `valide`.

`--apercu` : affiche sans rien écrire (revue en lecture seule, pour relire ou pour la preuve).
"""
from __future__ import annotations

import copy

import typer

from . import destinations as D
from . import extraction as X

# ordre d'affichage stable des rubriques et feuilles
_ORDRE = [("hauteur", ("faitage", "egout", "niveaux")),
          ("emprise_sol", ("ces",)),
          ("retraits", ("voie", "limites_separatives")),
          ("stationnement", ("par_logement", "par_m2_sdp", "par_typologie")),
          ("mixite", (None,))]

_VAL_KEYS = ("m", "r_plus", "pct", "m2", "formule", "min_m", "places", "par_m2", "detail",
             "seuil_logements", "seuil_m2", "quota_pct", "portee")


def _resume_valeur(leaf: dict) -> str:
    """Le résumé lisible d'une valeur de feuille (ce qui la distingue de sa preuve)."""
    if leaf.get("absent"):
        return "non réglementé (silence prouvé)"
    bouts = [f"{k}={leaf[k]}" for k in _VAL_KEYS if k in leaf and leaf.get(k) is not None]
    return " · ".join(bouts) if bouts else "(valeur non renseignée)"


def _feuilles_ordonnees(regles: dict):
    """(chemin, feuille) dans l'ordre canonique, feuilles inconnues à la fin."""
    vus = set()
    for rub, sous in _ORDRE:
        bloc = regles.get(rub)
        if not isinstance(bloc, dict):
            continue
        if sous == (None,):
            if "statut" in bloc:
                vus.add((rub,))
                yield (rub,), bloc
            continue
        for f in sous:
            leaf = bloc.get(f)
            if isinstance(leaf, dict) and "statut" in leaf:
                vus.add((rub, f))
                yield (rub, f), leaf
    for chemin, leaf in D.iter_regles_feuilles(regles):
        if chemin not in vus:
            yield chemin, leaf


def _zones_avec_regles(insee: str, zones: list[str] | None) -> list[tuple[str, dict]]:
    doc = D._doc(insee) or {}
    out = []
    for zone in sorted((doc.get("zones") or {}).keys()):
        zv = (doc.get("zones") or {}).get(zone) or {}
        if not isinstance(zv, dict) or not zv.get("regles"):
            continue
        if zones and zone not in zones:
            continue
        out.append((zone, copy.deepcopy(zv["regles"])))
    return out


def _pose(chemin: tuple, regles: dict, leaf: dict) -> None:
    """Repose une feuille (mutée) à son chemin dans un bloc regles."""
    if len(chemin) == 1:
        regles[chemin[0]] = leaf
    else:
        regles.setdefault(chemin[0], {})[chemin[1]] = leaf


def _retire(chemin: tuple, regles: dict) -> None:
    if len(chemin) == 1:
        regles.pop(chemin[0], None)
    else:
        regles.get(chemin[0], {}).pop(chemin[1], None)
        if not regles.get(chemin[0]):
            regles.pop(chemin[0], None)


def afficher(insee: str, zones: list[str] | None = None, *, echo=typer.echo) -> int:
    """Affiche les propositions zone par zone, rubrique par rubrique. Renvoie le nombre de
    feuilles affichées."""
    ec = D.etat_commune(insee)
    echo(f"— Revue PLU {ec.get('commune') or insee} ({ec.get('insee') or insee}) · "
         f"millésime {ec.get('millesime')} · {ec.get('document')}")
    n = 0
    for zone, regles in _zones_avec_regles(insee, zones):
        feuilles = list(_feuilles_ordonnees(regles))
        echo(f"\n═ Zone {zone} · {len(feuilles)} règle(s)")
        rub_vue = None
        for chemin, leaf in feuilles:
            if chemin[0] != rub_vue:
                rub_vue = chemin[0]
                echo(f"  ▸ {D.REGLES_RUBRIQUES_LIB.get(rub_vue, rub_vue)}")
            n += 1
            tag = leaf.get("statut", "?")
            echo(f"    · {'.'.join(chemin):26} [{tag}] {_resume_valeur(leaf)}")
            echo(f"        art. {leaf.get('article')} · p.{leaf.get('page_pdf')} (PDF)")
            echo(f"        {leaf.get('citation')}")
    if n == 0:
        echo("\n(aucune règle proposée — lancer d'abord `labuse plu extraire`.)")
    return n


def appliquer(insee: str, decisions: dict[str, dict[str, dict]]) -> dict:
    """Applique des décisions programmatiques (revue non interactive / tests). `decisions` :
    {zone: {chemin_pointé: {"geste": "valider"|"rejeter"|"corriger", "valeur": {…}}}}.
    « valider » → statut=valide ; « corriger » → remplace les champs de valeur puis valide ;
    « rejeter » → retire la feuille. Écrit le YAML. Renvoie un compte {valide, corrige, rejete}."""
    path = D._fichier_commune(insee)
    if path is None:
        raise ValueError(f"commune {insee} non calibrée")
    compte = {"valide": 0, "corrige": 0, "rejete": 0}
    regles_par_zone: dict[str, dict] = {}
    for zone, regles in _zones_avec_regles(insee, list(decisions.keys())):
        zdec = decisions.get(zone) or {}
        chemins = {".".join(c): (c, leaf) for c, leaf in D.iter_regles_feuilles(regles)}
        for cle, dec in zdec.items():
            if cle not in chemins:
                continue
            chemin, leaf = chemins[cle]
            geste = dec.get("geste", "valider")
            if geste == "rejeter":
                _retire(chemin, regles)
                compte["rejete"] += 1
                continue
            leaf = dict(leaf)
            if geste == "corriger":
                for k, v in (dec.get("valeur") or {}).items():
                    leaf[k] = v
                compte["corrige"] += 1
            else:
                compte["valide"] += 1
            leaf["statut"] = "valide"
            _pose(chemin, regles, leaf)
        regles_par_zone[zone] = regles
    X._ecrire_regles(path, regles_par_zone)
    return compte


def revue_interactive(insee: str, zones: list[str] | None = None, *, apercu: bool = False) -> None:
    """La revue à la main : v(alider) / c(orriger) / r(ejeter) chaque proposition, ou `--apercu`
    pour seulement afficher."""
    if apercu:
        afficher(insee, zones)
        return
    decisions: dict[str, dict[str, dict]] = {}
    for zone, regles in _zones_avec_regles(insee, zones):
        typer.echo(f"\n═ Zone {zone}")
        for chemin, leaf in _feuilles_ordonnees(regles):
            if leaf.get("statut") == "valide":
                continue
            cle = ".".join(chemin)
            typer.echo(f"  · {cle} — {_resume_valeur(leaf)}")
            typer.echo(f"      art. {leaf.get('article')} · p.{leaf.get('page_pdf')} · {leaf.get('citation')}")
            rep = typer.prompt("    [v]alider / [c]orriger / [r]ejeter / [p]asser", default="p").strip().lower()
            if rep.startswith("v"):
                decisions.setdefault(zone, {})[cle] = {"geste": "valider"}
            elif rep.startswith("r"):
                decisions.setdefault(zone, {})[cle] = {"geste": "rejeter"}
            elif rep.startswith("c"):
                brut = typer.prompt("      valeur corrigée (clé=valeur, séparées par des virgules)")
                valeur: dict = {}
                for pair in brut.split(","):
                    if "=" in pair:
                        k, v = pair.split("=", 1)
                        v = v.strip()
                        valeur[k.strip()] = int(v) if v.lstrip("-").isdigit() else v
                decisions.setdefault(zone, {})[cle] = {"geste": "corriger", "valeur": valeur}
    if not decisions:
        typer.echo("— rien de tranché (aucune décision).")
        return
    compte = appliquer(insee, decisions)
    typer.echo(f"— écrit : {compte['valide']} validée(s), {compte['corrige']} corrigée(s), "
               f"{compte['rejete']} rejetée(s).")
