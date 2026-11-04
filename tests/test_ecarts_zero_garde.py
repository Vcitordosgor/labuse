"""ECARTS-ZERO-1 (décision Vic) — LE GARDE-FOU : la notion d'« écart toléré » ne peut pas revenir.

Vic : « Aucun écart n'est tolérable, même d'un euro ou d'un mot. Un fait a une seule fonction de
lecture, un seul arrondi, un seul format, partout. » Ces tests refusent, de façon permanente :

  1. qu'une TOLÉRANCE non nulle réapparaisse dans une vérification du banc de cohérence
     (checks_parcelle / checks_commune / croisements) — un arrondi ou un point de %
     « acceptés » rouvriraient la porte à un fait servi à deux valeurs ;
  2. que la gravité « TOLERABLE » redevienne assignable — tout écart (y compris un arrondi)
     est ROUGE ; l'arrondi reste une CAUSE lisible, jamais une excuse ;
  3. qu'un arrondi d'AFFICHAGE soit réintroduit dans le PRODUCTEUR de la surface servie
     (la fiche sert la valeur brute ; l'arrondi se fait UNE fois au bord, via lib/format
     `fmtM2` côté écran et `registre_fmt.fmt_m2` côté PDF).

C'est le filet qui rend « un même fait, deux valeurs » impossible à réintroduire sans qu'un test
tombe en rouge.
"""
from __future__ import annotations

import pathlib

RACINE = pathlib.Path(__file__).resolve().parents[1]


def _est_tolerance_zero(tol: str) -> bool:
    """Tolérance acceptable = une PRÉCISION D'AFFICHAGE (nombre de décimales de l'arrondi unique du
    fait) : "0", "0 (entier)", "1" … — JAMAIS une marge floue qui « tolère » un écart : "0,5 point",
    "1 %", "n %". On refuse donc tout jeton contenant « % », « point » ou une virgule décimale."""
    t = tol.strip()
    if "%" in t or "point" in t or "," in t:
        return False
    return t[:1].isdigit()


def test_banc_aucune_tolerance_non_nulle():
    """Chaque vérification du banc (parcelle, commune, croisement) compare à tolérance ZÉRO."""
    from scripts.coherence.checks_parcelle import CHECKS as P
    from scripts.coherence.checks_commune import CHECKS as C, CROISEMENTS_PARCELLE as X

    fautifs = []
    for notion, tol, *_ in P:
        if not _est_tolerance_zero(tol):
            fautifs.append(f"parcelle:{notion} tol={tol!r}")
    for notion, tol, *_ in C:
        if not _est_tolerance_zero(tol):
            fautifs.append(f"commune:{notion} tol={tol!r}")
    for notion, tol, *_ in X:
        if not _est_tolerance_zero(tol):
            fautifs.append(f"croisement:{notion} tol={tol!r}")
    assert not fautifs, (
        "ECARTS-ZERO-1 — tolérance non nulle réintroduite dans le banc (tout écart doit être "
        "corrigé à la SOURCE, pas toléré) :\n  " + "\n  ".join(fautifs))


def test_gravite_tolerable_supprimee_du_banc():
    """À la précision d'affichage : un écart d'UN m² (100 vs 101) est ROUGE (INCOHERENT), jamais
    « TOLERABLE ». Et le bruit SOUS l'unité affichée (11 vs 11,3 → tous deux « 11 ») n'est PAS un écart."""
    from scripts.coherence.lib import Ecarts

    # bruit sous l'unité : pas un écart (même valeur affichée « 11 »)
    ec0 = Ecarts()
    ec0.noter("surface_m2", "TEST", "fiche", 11, "sql", 11.3, "0")
    assert ec0.lignes == [], "le bruit flottant sous l'unité affichée ne doit pas être un écart"

    # écart d'un m² : ROUGE, jamais toléré
    ec = Ecarts()
    ec.noter("surface_m2", "TEST", "fiche", 100, "sql", 101, "0")
    assert len(ec.lignes) == 1, "un écart d'un m² à la précision affichée doit être noté"
    assert ec.lignes[0]["gravite"] == "INCOHERENT", (
        f"ECARTS-ZERO-1 — un écart d'un m² doit être ROUGE, pas {ec.lignes[0]['gravite']!r}")


def test_mot_tolerable_absent_de_la_notation():
    """Le mot « TOLERABLE » n'est plus assigné comme gravité dans lib.noter (scan source)."""
    src = (RACINE / "scripts" / "coherence" / "lib.py").read_text(encoding="utf-8")
    # On autorise le mot en COMMENTAIRE (il explique sa disparition) mais pas une affectation.
    for ligne in src.splitlines():
        nu = ligne.split("#", 1)[0]          # retire le commentaire
        if "TOLERABLE" in nu:
            raise AssertionError(
                "ECARTS-ZERO-1 — gravité « TOLERABLE » réassignée dans lib.py (hors commentaire) : "
                + ligne.strip())


def test_surface_fiche_servie_brute_sans_arrondi():
    """La fiche sert surface_m2 BRUTE : pas de round() dans le producteur (l'arrondi est au bord).

    Garde ciblée sur le fait unifié par ECARTS-ZERO-1 (seul écart fiche↔carte↔SQL avant correctif).
    """
    src = (RACINE / "src" / "labuse" / "api" / "app.py").read_text(encoding="utf-8")
    for ligne in src.splitlines():
        if '"surface_m2":' in ligne and "head[" in ligne and "round(" in ligne.split("#", 1)[0]:
            raise AssertionError(
                "ECARTS-ZERO-1 — surface_m2 de la fiche ré-arrondie dans le producteur : "
                + ligne.strip() + "  (servir brut ; arrondir au bord via fmtM2 / registre_fmt.fmt_m2)")
