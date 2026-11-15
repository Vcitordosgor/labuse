"""EXPORTS-2 lot 1.6 — NUMÉRO DE RAPPORT unique par document.

Forme : `<préfixe>-<AAAAMMJJ>-<IDU>` — le préfixe dit le document, la date le jour de génération,
l'IDU garantit l'unicité (1.6 « unique par document »). La maquette abrège l'IDU à ses quatre
derniers chiffres pour l'exemple ; ici on porte l'IDU entier, sinon deux parcelles de sections
différentes partageraient un numéro.
"""
from __future__ import annotations

from datetime import date

from ..tz import today_reunion   # FIX-ORFEVRE-1 pt 3 (ORF-17/D-13) — numéro daté au jour Réunion

#: préfixe par document (mandat lot 1.6 + lot 2 pour le Flash).
PREFIXE = {
    "dossier": "DP", "financier": "FI", "apporteur": "AP",
    "predossier_pc": "PC", "flash": "FL",
    # DOCS-1 (Lot C) — les 3 nouveaux documents.
    "gabarit": "GA", "comparatif": "CO", "etude-zone": "EZ",
    # ANNONCE-3 — le document « Analyse d'annonce » (miroir de l'outil Analyser une annonce).
    "analyse-annonce": "AA",
    # BILAN-1 (Lot 5) — le bilan promoteur (code propre, jamais « Financier » côté client).
    "bilan": "BI",
}


def numero_rapport(document: str, idu: str, jour: date | None = None) -> str:
    """Numéro de rapport : `<préfixe>-<AAAAMMJJ>-<IDU ENTIER>`. `document` ∈ PREFIXE ; `jour`
    injectable (test/repro).

    CHIRURGICAL-FIX-1 (LOT F, E4) — on portait les 4 DERNIERS caractères de l'IDU (`idu[-4:]`) :
    deux parcelles de sections/communes différentes mais de même suffixe (97404000AY**0153** et
    97414000CO**0153**) recevaient le MÊME numéro le même jour (434 582 parcelles pour 4 358 suffixes
    distincts → ~100 collisions par suffixe). On porte l'IDU ENTIER (comme l'affirme déjà l'en-tête du
    module) : un numéro ne peut plus désigner deux parcelles. Toujours lisible, et le préfixe + la date
    gardent leur sens."""
    if document not in PREFIXE:
        raise ValueError(f"document inconnu : {document!r} (attendu {sorted(PREFIXE)})")
    j = jour or today_reunion()
    return f"{PREFIXE[document]}-{j:%Y%m%d}-{idu}"
