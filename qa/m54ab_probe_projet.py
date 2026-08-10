"""M54-AB F4 — mesure : le filtre périmètre s'applique-t-il au top 5 du PDF projet ?

On construit des fiches projet et on appelle projet_apercu directement + _perimetre_label,
pour trancher bug filtre vs bug affichage. Aucune écriture.
"""
from __future__ import annotations

from labuse.db import session_scope
from labuse.api.projets import projet_apercu, ApercuIn
from labuse.api.pdf_projet import _perimetre_label

FICHES = {
    "communes=[Saint-Paul] sans programme": {
        "perimetre": {"mode": "communes", "communes": ["Saint-Paul"]}},
    "secteur=Ouest sans programme": {
        "perimetre": {"mode": "secteur", "secteur": "Ouest"}},
    "communes=[Saint-Paul] + programme 30 logements": {
        "perimetre": {"mode": "communes", "communes": ["Saint-Paul"]},
        "programme": {"logements": 30}},
    "toute l'île sans programme": {"perimetre": {"mode": "ile"}},
}


def main() -> None:
    with session_scope() as db:
        for nom, fiche in FICHES.items():
            label = _perimetre_label(fiche)
            try:
                ap = projet_apercu(ApercuIn(fiche=fiche, limit=5), db)
                communes_top = [it["commune"] for it in ap.get("top", [])]
                print(f"\n### {nom}")
                print(f"  _perimetre_label = {label!r}")
                print(f"  source={ap.get('source')}  n={ap.get('n')}  programme_defini={ap.get('programme_defini')}")
                print(f"  top communes = {communes_top}")
            except Exception as e:  # noqa: BLE001
                print(f"\n### {nom}\n  _perimetre_label={label!r}  ERREUR {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
