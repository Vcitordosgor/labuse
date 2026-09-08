"""Bloc « 4. Risques, servitudes, patrimoine ». Rendu depuis la cascade servie (aléas). L'encart
PPR ressort en tête ; seuls les signaux RELEVÉS sont listés (pas de liste d'exemple ; « aucun
signal » n'est affirmé que si la donnée l'établit)."""
from __future__ import annotations

from ..lignes import pied, val
from ..rendu import aside, chip_span, esc, ligne_kv, note, section, table_kv

IDS = ("aleas_parcelle_liste",)


def rendu(valeurs) -> str:
    liste = val(valeurs, "aleas_parcelle_liste") or []
    if not liste:
        return ""      # aucune donnée d'aléa servie → section omise (aucun ◌)
    corps = ""
    # l'encart en tête : le premier aléa réglementaire (PPR / zone bleue), s'il existe
    tete = next((a for a in liste if isinstance(a, dict)
                 and ("PPR" in (a.get("libelle") or "") or "bleue" in (a.get("libelle") or "").lower())), None)
    lignes = []
    for a in liste:
        if not isinstance(a, dict):
            continue
        if a is tete:
            corps += aside(f"<strong>{esc(a.get('libelle') or a.get('nature'))}</strong>", "blue")
            continue
        lib = a.get("libelle") or ""
        niveau = a.get("niveau")
        txt = esc(lib) + (f" — aléa de niveau {esc(niveau)}" if niveau and niveau not in lib else "")
        lignes.append(ligne_kv(a.get("nature") or "Aléa", txt, chip_span("s", "sourcé")))
    if lignes:
        corps += table_kv(lignes)
    corps += note("Aléas et servitudes vérifiés via la DEAL et Géorisques ; seuls les signaux "
                  "relevés sur la parcelle sont listés.")
    corps += pied(valeurs, IDS)
    return section("4. Risques, servitudes, patrimoine", corps)
