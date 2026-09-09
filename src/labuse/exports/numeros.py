"""EXPORTS-2 lot 1.6 — NUMÉRO DE RAPPORT unique par document.

Forme : `<préfixe>-<AAAAMMJJ>-<IDU>` — le préfixe dit le document, la date le jour de génération,
l'IDU garantit l'unicité (1.6 « unique par document »). La maquette abrège l'IDU à ses quatre
derniers chiffres pour l'exemple ; ici on porte l'IDU entier, sinon deux parcelles de sections
différentes partageraient un numéro.
"""
from __future__ import annotations

from datetime import date

#: préfixe par document (mandat lot 1.6 + lot 2 pour le Flash).
PREFIXE = {
    "dossier": "DP", "financier": "FI", "apporteur": "AP",
    "predossier_pc": "PC", "flash": "FL",
}


def numero_rapport(document: str, idu: str, jour: date | None = None) -> str:
    """Numéro de rapport, format court des anciens documents : `<préfixe>-<AAAAMMJJ>-<4 derniers
    chiffres de l'IDU>` (lisible en pied de page ; l'IDU ENTIER vit dans le cartouche @page —
    doc_ref — et sur la page de garde). `document` ∈ PREFIXE ; `jour` injectable (test/repro)."""
    if document not in PREFIXE:
        raise ValueError(f"document inconnu : {document!r} (attendu {sorted(PREFIXE)})")
    j = jour or date.today()
    return f"{PREFIXE[document]}-{j:%Y%m%d}-{idu[-4:]}"
