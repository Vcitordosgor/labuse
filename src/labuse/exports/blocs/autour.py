"""Bloc « 7. Autour de la parcelle ». CORRECTION §7 (RELECTURE) : on sert le périmètre RÉELLEMENT
calculé — la maille quartier IRIS de l'INSEE — avec son mode DANS LE TITRE. Jamais un titre
« 10 min à pied » sur un chiffre qui n'est pas celui-là."""
from __future__ import annotations

from collections import Counter

from ..lignes import pied, val
from ..nature import chip
from ..registre_fmt import fmt_pct, groupe
from ..rendu import chip_span, esc, ligne_kv, note, section, table_kv, tuiles

IDS = ("iris_quartier", "equipements_proximite_liste")

#: RECETTE-8 W14 — l'accord singulier/pluriel par catégorie d'équipement, EXPLICITE. L'ancienne
#: règle « retire le s quand n=1 » mangeait le « s » de « bus » (invariable en français : son
#: singulier finit déjà par s) → « 1 bu ». On nomme le singulier ET le pluriel de chaque catégorie
#: servie (`api.app._PROX_EQUIP`) : « bus » reste « bus », « commerces » devient « commerce ».
_EQUIP_ACCORD: dict[str, tuple[str, str]] = {
    "École": ("école", "écoles"),
    "Commerces": ("commerce", "commerces"),
    "Santé": ("service de santé", "services de santé"),
    "Bus": ("arrêt de bus", "arrêts de bus"),
}


def _accord(cat: str, n: int) -> str:
    """« n <singulier> » si n ≤ 1, « n <pluriel> » sinon. Repli prudent (mot non listé) : on ne
    touche PAS le mot (jamais un « 1 bu »), on l'affiche tel quel en minuscules."""
    sing, plur = _EQUIP_ACCORD.get(cat, (cat.lower(), cat.lower()))
    return f"{n} {sing if n <= 1 else plur}"


def rendu(valeurs) -> str:
    iq = val(valeurs, "iris_quartier")
    if not isinstance(iq, dict) or iq.get("habitants") is None:
        return ""     # pas de maille servie → section omise (pas de faux périmètre)
    nom = iq.get("nom") or "de la parcelle"
    titre = f"7. Autour de la parcelle — quartier {nom} (maille IRIS INSEE)"
    tui = []
    if iq.get("habitants") is not None:
        lib = "habitants" + (f", {groupe(iq['menages'])} ménages" if iq.get("menages") else "")
        tui.append((groupe(iq["habitants"]), lib))
    if iq.get("part_60_plus_pct") is not None:
        tui.append((fmt_pct(iq["part_60_plus_pct"]), "de 60 ans et plus"))
    if iq.get("part_locataires_pct") is not None:
        tui.append((fmt_pct(iq["part_locataires_pct"]), "de locataires"))
    corps = tuiles(tui[:3]) if tui else ""
    lignes = []
    if iq.get("logements") is not None:
        lignes.append(ligne_kv("Parc de logements du quartier",
                      esc(f"{groupe(iq['logements'])} logements"
                          + (f", {fmt_pct(iq['vacance_pct'])} de vacance" if iq.get("vacance_pct") is not None else "")),
                      chip(valeurs["iris_quartier"])))
    items = val(valeurs, "equipements_proximite_liste") or []
    if items:
        cnt = Counter(it.get("cat") for it in items if isinstance(it, dict) and it.get("cat"))
        # RECETTE-9 T3 — on appelle le `_accord` de MODULE (table explicite singulier/pluriel), plus
        # de règle naïve locale. La règle `lib[:-1]` mangeait le « s » de « bus » (invariable) → « 1 bu ».
        # Le bug W14 : le correctif avait été posé sur la fonction de module, mais `rendu()` gardait sa
        # propre version imbriquée qui l'ombrait — jamais appelée. Suppression de l'ombre.
        resume = ", ".join(_accord(cat, n) for cat, n in cnt.most_common())
        lignes.append(ligne_kv("Équipements à proximité", esc(resume), chip_span("s", "sourcé")))
    if lignes:
        corps += table_kv(lignes)
    corps += note("Faits sourcés et datés à la maille du quartier IRIS — aucune prévision de "
                  "chiffre d'affaires, aucune note d'attractivité.")
    corps += pied(valeurs, IDS)
    return section(titre, corps)
