"""ETUDE-AUDIT-FIX-1 — génère les PDF « après » des 4 terrains du mandat dans ~/Desktop/etude-audit-fix-1/.
Exécuté HORS suite de tests (script de livrable). Reproduit le chemin du worker PDF (etudier_payload +
enrichissements + rendu). Pas committé dans le périmètre fonctionnel (utilitaire de livraison)."""
import os

from labuse.db import session_scope
from labuse.implantation.service import etudier_payload
from labuse.api.modules import (_attach_au_ouverture, _attach_contraintes_signalees,
                                _attach_zone_gabarit, _attach_garde_fiche)
from labuse.exports import etude_faisabilite as ef
from labuse.exports.rendu import render_pdf

OUT = os.path.expanduser("~/Desktop/etude-audit-fix-1")


def gen(fname, idus, data):
    with session_scope() as s:
        p = etudier_payload(s, data)
        _attach_au_ouverture(s, p, idus)
        _attach_contraintes_signalees(s, p, idus)
        _attach_zone_gabarit(s, p, idus)
        _attach_garde_fiche(s, p, idus)
        if p.get("lotissement"):
            rendu = ef.rendu_lotissement(p, genere_le="25/11/2026")
        elif p.get("hors_perimetre"):
            rendu = ef.rendu_hors_perimetre(p, genere_le="25/11/2026")
        else:
            rendu = ef.rendu_etude(p, genere_le="25/11/2026", scenario_ref=None)
    pdf = render_pdf(rendu["html"])
    path = os.path.join(OUT, fname)
    with open(path, "wb") as f:
        f.write(pdf)
    print(f"OK {fname}  {len(pdf)} octets  n°{rendu.get('numero')}")


def main():
    os.makedirs(OUT, exist_ok=True)
    gen("apres-01-etang-sale-UA-social.pdf",
        ["97404000AW0099", "97404000AW0451", "97404000AW0624", "97404000AW0625"],
        {"idus": ["97404000AW0099", "97404000AW0451", "97404000AW0624", "97404000AW0625"],
         "type_projet": "social", "stationnement": "sous_sol", "niveaux_sous_sol": 1,
         "terrain": "libere", "programme": {"demande": {"T2": 23, "T3": 6}}})
    gen("apres-02-saint-andre-UC-social.pdf", ["97409000AX0255", "97409000AX0256"],
        {"idus": ["97409000AX0255", "97409000AX0256"], "type_projet": "social",
         "stationnement": "aerien", "terrain": "libere",
         "programme": {"demande": {"T2": 17, "T3": 22, "T4": 9}}})
    gen("apres-03-saint-denis-Ui-senior.pdf", ["97411000DL0247", "97411000DL0248"],
        {"idus": ["97411000DL0247", "97411000DL0248"], "type_projet": "senior",
         "stationnement": "aerien", "terrain": "libere", "programme": {"demande": {"T2": 22}}})
    gen("apres-04-saint-leu-UD-lotissement.pdf", ["97413000AC0264"],
        {"idus": ["97413000AC0264"], "type_projet": "lotissement", "terrain": "libere",
         "programme": None})


if __name__ == "__main__":
    main()
