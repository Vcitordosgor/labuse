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
        # RECETTE-7 (E9) — l'accord singulier/pluriel : « 1 commerce », « 3 commerces » (les
        # catégories sont stockées au pluriel ; on retire le « s » quand n vaut 1).
        def _accord(cat: str, n: int) -> str:
            lib = cat.lower()
            return f"{n} {lib[:-1] if (n <= 1 and lib.endswith('s')) else lib}"
        resume = ", ".join(_accord(cat, n) for cat, n in cnt.most_common())
        lignes.append(ligne_kv("Équipements à proximité", esc(resume), chip_span("s", "sourcé")))
    if lignes:
        corps += table_kv(lignes)
    corps += note("Faits sourcés et datés à la maille du quartier IRIS — aucune prévision de "
                  "chiffre d'affaires, aucune note d'attractivité.")
    corps += pied(valeurs, IDS)
    return section(titre, corps)
