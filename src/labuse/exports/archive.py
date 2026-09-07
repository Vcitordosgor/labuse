"""EXPORTS-2 lot 1.6 — ARCHIVAGE JSON des Valeur lues, à côté de tout PDF vendu ou envoyé
(Flash, Apporteur, Financier) : le document est reproductible à l'identique — mêmes Valeur,
même numéro de rapport, même jour. Le JSON porte la valeur ET le tampon de chaque id (run,
réservoirs/millésimes, portée, couverture, état).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

from ..registre.valeur import Valeur


def payload_archive(document: str, idu: str, numero: str, valeurs: Mapping[str, Valeur],
                    genere_le: str) -> dict:
    """Le contenu JSON archivable : méta + chaque id (valeur + tampon complet). Déterministe
    (ids triés) pour un diff propre."""
    return {
        "document": document, "idu": idu, "numero_rapport": numero, "genere_le": genere_le,
        "valeurs": {cid: {"valeur": valeurs[cid].valeur, "tampon": valeurs[cid].tampon()}
                    for cid in sorted(valeurs)},
    }


def ecrire_archive(pdf_path: str | Path, payload: dict) -> Path:
    """Écrit le JSON à côté du PDF (même nom, extension .json). Rend le chemin écrit."""
    p = Path(pdf_path).with_suffix(".json")
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return p


def lire_archive(json_path: str | Path) -> dict:
    return json.loads(Path(json_path).read_text(encoding="utf-8"))
