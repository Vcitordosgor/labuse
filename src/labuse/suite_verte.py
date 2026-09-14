"""TESTS-1 lot 3 — LA SUITE EST UNE PORTE, comme les verrous.

`labuse circuit suite` joue la suite pytest complète et confronte ses échecs à
`docs/TESTS-TOLERES.md` : un échec SANS ligne de tolérance (raison + date + échéance),
ou dont l'échéance est passée, fait sortir en erreur — deploy.sh refuse alors de
déployer, au même titre qu'un verrou cassé. Règle du mandat TESTS-1 : *un mandat ne se
déclare pas livré avec un test rouge qu'il n'a pas nommé, daté et justifié.*

Le fichier des tolérances est une liste COURTE, en tableau markdown :

    | test | raison | depuis | échéance |
    |---|---|---|---|
    | tests/x.py::test_y | pourquoi c'est toléré | 2026-09-14 | 2026-09-21 |

Analyse séparée de l'exécution : `confronter()` est pur (testé par la suite elle-même,
sans récursion) ; `jouer()` lance pytest en sous-processus.
"""
from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

FICHIER_TOLERES = "docs/TESTS-TOLERES.md"

_LIGNE = re.compile(
    r"^\|\s*(?P<test>[^|]+?)\s*\|\s*(?P<raison>[^|]+?)\s*\|\s*(?P<depuis>\d{4}-\d{2}-\d{2})\s*"
    r"\|\s*(?P<echeance>\d{4}-\d{2}-\d{2})\s*\|\s*$")


@dataclass
class Tolerance:
    test: str
    raison: str
    depuis: date
    echeance: date


@dataclass
class Verdict:
    ok: bool
    refus: list[str] = field(default_factory=list)      # ce qui fait refuser, une phrase par ligne
    avertissements: list[str] = field(default_factory=list)


def charger_tolerances(chemin: Path) -> list[Tolerance]:
    """Les lignes de tolérance du tableau — les entêtes/séparateurs/texte libre sont ignorés ;
    une ligne de tableau MALFORMÉE (pas 4 colonnes datées) est une erreur, jamais un silence."""
    tolerances: list[Tolerance] = []
    if not chemin.exists():
        return tolerances
    for n, ligne in enumerate(chemin.read_text(encoding="utf-8").splitlines(), 1):
        if not ligne.strip().startswith("|") or set(ligne.replace("|", "").strip()) <= {"-", " "}:
            continue
        if re.match(r"^\|\s*test\s*\|", ligne.strip()):   # l'entête, pas « | tests/… »
            continue
        m = _LIGNE.match(ligne.strip())
        if not m:
            raise ValueError(f"{chemin}:{n} : ligne de tolérance malformée "
                             "(attendu : | test | raison | AAAA-MM-JJ | AAAA-MM-JJ |)")
        tolerances.append(Tolerance(
            m["test"], m["raison"],
            date.fromisoformat(m["depuis"]), date.fromisoformat(m["echeance"])))
    return tolerances


def confronter(echecs: list[str], tolerances: list[Tolerance], *, aujourd_hui: date) -> Verdict:
    """L'arbitrage PUR : chaque échec doit avoir sa tolérance NON échue ; une tolérance
    échue refuse ; une tolérance dont le test passe est signalée (à purger, pas un refus)."""
    v = Verdict(ok=True)
    par_test = {t.test: t for t in tolerances}
    for e in sorted(echecs):
        t = par_test.get(e)
        if t is None:
            v.refus.append(f"{e} : échec SANS ligne dans {FICHIER_TOLERES} — nommer, dater, "
                           "justifier (ou corriger)")
        elif t.echeance < aujourd_hui:
            v.refus.append(f"{e} : tolérance ÉCHUE depuis le {t.echeance.isoformat()} "
                           f"(raison d'alors : {t.raison})")
        else:
            v.avertissements.append(f"{e} : toléré jusqu'au {t.echeance.isoformat()} — {t.raison}")
    for t in tolerances:
        if t.test not in echecs:
            v.avertissements.append(f"{t.test} : la tolérance est MORTE (le test passe) — "
                                    f"retirer la ligne de {FICHIER_TOLERES}")
    v.ok = not v.refus
    return v


def jouer(racine: Path, *, pytest_args: tuple[str, ...] = ()) -> tuple[list[str], str]:
    """Joue la suite complète (sous-processus, même interpréteur) et rend (échecs, résumé).
    pytest introuvable ou suite injouable → RuntimeError : on ne déploie pas sans jouer."""
    cmd = [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=no", "-rf", *pytest_args]
    p = subprocess.run(cmd, cwd=racine, capture_output=True, text=True)
    sortie = (p.stdout or "") + (p.stderr or "")
    if "no tests ran" in sortie or "error: unrecognized" in sortie or p.returncode in (3, 4):
        raise RuntimeError(f"suite injouable (pytest code {p.returncode}) :\n{sortie[-2000:]}")
    echecs = re.findall(r"^(?:FAILED|ERROR)\s+(\S+?)(?:\s+-.*)?$", sortie, re.M)
    resume = next((l for l in reversed(sortie.splitlines()) if "passed" in l or "failed" in l), "")
    return [e.rstrip() for e in echecs], resume.strip()
