"""COHERENCE-FIX-1 (lot G) — LE GOLDEN DES TÉMOINS : l'instantané des valeurs affichées.

Sept témoins (les parcelles-fil-rouge des mandats), et pour chaque notion des tables de
vérification la valeur du PREMIER lecteur porteur (l'écran client). L'instantané vit dans
`tests/golden/coherence/<idu>.json` ; toute variation fait échouer le verrou V6b tant
qu'elle n'est pas ACCEPTÉE explicitement :

    labuse coherence --accepter          # régénère les instantanés (motif dans le commit)
    python -m scripts.coherence.golden   # équivalent module

Le golden n'est pas le banc : il fige l'ÉTAT ACCEPTÉ (après recette) et crie sur toute
dérive — bascule oubliée, cache périmé, régression de moteur — même quand les lecteurs
restent cohérents ENTRE EUX (cohérent-mais-changé se voit ici).
"""
from __future__ import annotations

import json
import pathlib
import sys

from .checks_parcelle import CHECKS as CHECKS_P
from .lib import ABSENT, Contexte, Erreur, RACINE, comparer

GOLDEN_DIR = RACINE / "tests" / "golden" / "coherence"

#: les 7 témoins-fil-rouge (fiches recettées par les mandats précédents).
TEMOINS = (
    "97411000BZ1065",   # Saint-Denis — témoin FAISABILITE/SOURCES
    "97415000EO0796",   # Saint-Pierre — témoin ALGO (179 m²)
    "97415000AX0990",   # Saint-Pierre — témoin ALGO (1619 m²)
    "97408000AO1424",   # La Possession — zone A, SDP 0
    "97402000AB1117",   # Bras-Panon — témoin tuiles≠fiche de COHERENCE-1
    "97418000AC0198",   # Sainte-Marie (énoncés historiques : « Sainte-Suzanne »)
    "97415000CK0678",   # témoin Kelfoncier (échantillon COHERENCE-1)
)


def snapshot(ctx: Contexte, idu: str) -> dict:
    """{notion: {lecteur, valeur}} — la valeur du PREMIER lecteur porteur de chaque check."""
    out: dict[str, dict] = {}
    for notion, tol, lecteurs, _cause in CHECKS_P:
        for etiquette, getter in lecteurs:
            try:
                v = getter(ctx, idu)
            except Exception:  # noqa: BLE001
                continue
            if v is ABSENT or isinstance(v, Erreur):
                continue
            out[notion] = {"lecteur": etiquette, "valeur": v, "tolerance": tol}
            break
    return out


def ecrire(ctx: Contexte | None = None) -> list[str]:
    """(Ré)génère les 7 instantanés — le geste d'ACCEPTATION (motif au commit)."""
    ctx = ctx or Contexte()
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    fichiers = []
    for idu in TEMOINS:
        s = snapshot(ctx, idu)
        p = GOLDEN_DIR / f"{idu}.json"
        p.write_text(json.dumps(s, ensure_ascii=False, indent=1, sort_keys=True, default=str)
                     + "\n", encoding="utf-8")
        fichiers.append(str(p))
        print(f"✓ golden {idu} : {len(s)} notions")
    return fichiers


def comparer_tous(ctx: Contexte | None = None) -> list[str]:
    """Rejoue chaque témoin contre son instantané → liste des dérives NON tolérées
    (vide = conforme). Un témoin ABSENT de la base est DIT (base de test) — pas une dérive."""
    ctx = ctx or Contexte()
    derives: list[str] = []
    for idu in TEMOINS:
        p = GOLDEN_DIR / f"{idu}.json"
        if not p.exists():
            derives.append(f"{idu}: golden manquant (jouer labuse coherence --accepter)")
            continue
        en_base = ctx.sql1("SELECT 1 FROM parcels WHERE idu=%(idu)s", idu=idu)
        if en_base is ABSENT or isinstance(en_base, Erreur):
            continue           # base de test sans le témoin : dit par le verrou, pas une dérive
        attendu = json.loads(p.read_text(encoding="utf-8"))
        courant = snapshot(ctx, idu)
        for notion, att in attendu.items():
            cur = courant.get(notion)
            if cur is None:
                derives.append(f"{idu}·{notion}: notion disparue (attendu {att['valeur']!r})")
                continue
            ok, ecart, _cause = comparer(att["valeur"], cur["valeur"], att.get("tolerance", "0"))
            if not ok:
                derives.append(f"{idu}·{notion}: {att['valeur']!r} → {cur['valeur']!r} (écart {ecart})")
    return derives


if __name__ == "__main__":
    if "--comparer" in sys.argv:
        d = comparer_tous()
        print(f"{len(d)} dérive(s)")
        for x in d[:40]:
            print(" ·", x)
        sys.exit(1 if d else 0)
    ecrire()
