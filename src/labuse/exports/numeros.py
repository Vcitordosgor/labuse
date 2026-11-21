"""EXPORTS-2 lot 1.6 — NUMÉRO DE RAPPORT unique par document.

Forme : `<préfixe>-<AAAAMMJJ>-<IDU>` — le préfixe dit le document, la date le jour de génération,
l'IDU garantit l'unicité (1.6 « unique par document »). La maquette abrège l'IDU à ses quatre
derniers chiffres pour l'exemple ; ici on porte l'IDU entier, sinon deux parcelles de sections
différentes partageraient un numéro.
"""
from __future__ import annotations

import hashlib
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


def numero_rapport(document: str, idu: str, jour: date | None = None, *,
                   discriminant: str | None = None) -> str:
    """Numéro de rapport : `<préfixe>-<AAAAMMJJ>-<IDU ENTIER>[-<clé>]`. `document` ∈ PREFIXE ; `jour`
    injectable (test/repro).

    CHIRURGICAL-FIX-1 (LOT F, E4) — on portait les 4 DERNIERS caractères de l'IDU (`idu[-4:]`) :
    deux parcelles de sections/communes différentes mais de même suffixe (97404000AY**0153** et
    97414000CO**0153**) recevaient le MÊME numéro le même jour. On porte l'IDU ENTIER.

    CHIRURGICAL-FIX-1 (LOT I pt4) — `discriminant` ajoute une clé stable de 4 caractères : DEUX versions
    du même export le même jour (données ou saisies différentes) reçoivent des numéros DIFFÉRENTS, et
    une génération à l'identique garde le même numéro (déterministe). Pour un Comparatif, le
    discriminant porte TOUTES ses parcelles → le numéro tient compte de chacune, pas de la seule
    première."""
    if document not in PREFIXE:
        raise ValueError(f"document inconnu : {document!r} (attendu {sorted(PREFIXE)})")
    j = jour or today_reunion()
    base = f"{PREFIXE[document]}-{j:%Y%m%d}-{idu}"
    if discriminant:
        cle = hashlib.sha1(str(discriminant).encode("utf-8")).hexdigest()[:4].upper()
        base += f"-{cle}"
    return base
