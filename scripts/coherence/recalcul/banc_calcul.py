"""CALCULS-AUDIT-1 lot B — LE BANC DE RECALCUL, rejouable en une commande.

    PYTHONPATH=src python -m scripts.coherence.recalcul.banc_calcul

Joue chaque recalcul indépendant sur l'échantillon gelé (120 parcelles, 24 communes) + les
cas limites construits, compare au servi/stocké, écrit ECARTS-CALCUL.csv et un résumé.
Lecture seule (statement_timeout). Aucune fonction de calcul de production n'est importée
pour RECALCULER — seulement, quand nécessaire, pour lire une valeur SERVIE (comme la fiche).
"""
from __future__ import annotations

import time

from . import socle, dvf, geometrie, residuel, taxe, score

MODULES = [
    ("géométrie (surface, pente, %couche)", geometrie.verifier),
    ("résiduel/hauteur (identités servies)", residuel.verifier),
    ("médianes DVF secteur", dvf.verifier),
    ("taxe d'aménagement", taxe.verifier),
    ("signal/bandes (mult_base, frontières)", score.verifier),
]


def run() -> dict:
    ech = socle.charger_echantillon()
    conn = socle.connect()
    rec = socle.Recalc()
    t0 = time.time()
    print(f"banc de recalcul — {len(ech)} parcelles, run servi {socle.RUN}")
    for nom, fn in MODULES:
        t1 = time.time()
        try:
            fn(rec, conn, ech)
            print(f"  ✓ {nom} ({time.time()-t1:.0f}s) — {rec.n} comparaisons cumulées")
        except Exception as e:  # noqa: BLE001 — un module qui casse est un résultat, pas un arrêt
            print(f"  ✗ {nom} : {type(e).__name__}: {str(e)[:160]}")
    chemin = rec.ecrire()
    res = rec.resume()
    print(f"\n{res['comparaisons']} comparaisons · {res['ecarts']} écarts")
    print(f"  par gravité : {res['par_gravite']}")
    print(f"  par cause   : {res['par_cause']}")
    print(f"→ {chemin} ({time.time()-t0:.0f}s)")
    return res


if __name__ == "__main__":
    run()
