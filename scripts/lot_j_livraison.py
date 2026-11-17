"""CHIRURGICAL-FIX-1 — LOT J : génère les livrables (vraies routes, en process) pour les 4 parcelles.

Dossier PDF (avec couverture), Apporteur PDF, pré-dossier ZIP (PCMI4), Estimer PDF, Bilan PDF + Excel,
Comparatif PDF. On NEUTRALISE le plan de situation (fetch ortho réseau qui pend) → couverture rendue
sans la vignette. Chaque document est best-effort : un échec n'arrête pas les autres.

Usage : LABUSE_DATABASE_URL=… PYTHONPATH=src python scripts/lot_j_livraison.py
"""
from __future__ import annotations

import os
import traceback
from datetime import date
from pathlib import Path

from sqlalchemy import text

from labuse.db import session_scope
from labuse.exports import builder
from labuse.exports.rendu import render_pdf

# Le plan de situation va chercher des tuiles ortho (réseau) → il peut PENDRE. On le neutralise.
builder._plan_situation_html = lambda db, idu: ""  # noqa: E731

OUT = Path(os.path.expanduser("~/Desktop/chasse-1/_lot-final-3"))
OUT.mkdir(parents=True, exist_ok=True)
JOUR = date(2026, 11, 15)
PARCELS = {"BW2635": "97422000BW2635", "AM0838": "97404000AM0838",
           "AD0887": "97422000AD0887", "IS0448": "97411000IS0448"}
# contenance réelle (LOT J 1e) pour le Bilan
TERRAIN = {"BW2635": 2003, "AM0838": 1270, "AD0887": 1703, "IS0448": 1450}


def _w(name: str, data: bytes) -> None:
    (OUT / name).write_bytes(data)
    print(f"  ✓ {name} ({len(data)} o)")


def _fiche(db, idu):
    from labuse.api.app import parcel_fiche
    return parcel_fiche(idu, db=db, request=None)


def main() -> None:
    with session_scope() as db:
        # vider les caches de fiche pour régénérer le texte neuf (LOT J)
        try:
            db.execute(text("DELETE FROM fiche_cache WHERE idu = ANY(:ids)"),
                       {"ids": list(PARCELS.values())})
            db.commit()
        except Exception as e:  # noqa: BLE001
            print("  (fiche_cache non vidé :", e, ")")
        try:
            from labuse.api.app import vider_fiche_cache_partage
            vider_fiche_cache_partage()
        except Exception:  # noqa: BLE001
            pass

        for name, idu in PARCELS.items():
            print(f"\n=== {name} {idu} ===")
            try:
                fiche = _fiche(db, idu)
            except Exception:  # noqa: BLE001
                fiche = None
                print("  (fiche indisponible)")

            # Dossier
            try:
                r = builder.construire(db, idu, "dossier", fiche=fiche, jour=JOUR)
                _w(f"dossier_{name}_{idu}.pdf", render_pdf(r.html))
            except Exception:  # noqa: BLE001
                print("  ✗ dossier :", traceback.format_exc().splitlines()[-1])

            # Apporteur
            try:
                ra = builder.construire(db, idu, "apporteur", fiche=fiche, jour=JOUR)
                _w(f"apporteur_{name}_{idu}.pdf", render_pdf(ra.html, forms=True))
            except Exception:  # noqa: BLE001
                print("  ✗ apporteur :", traceback.format_exc().splitlines()[-1])

            # Estimer (analyse d'annonce de la parcelle)
            try:
                re_ = builder.construire_analyse_annonce_parc(db, idu, jour=JOUR)
                _w(f"estimer_{name}_{idu}.pdf", render_pdf(re_.html))
            except Exception:  # noqa: BLE001
                print("  ✗ estimer :", traceback.format_exc().splitlines()[-1])

            # Pré-dossier ZIP (contient le PCMI4) — refusé si non constructible (AM0838)
            try:
                from labuse.api.pre_dossier import pre_dossier_zip

                class _Req:  # quota : requête minimale
                    headers: dict = {}
                    client = None
                resp = pre_dossier_zip(idu, request=_Req(), db=db)
                body = getattr(resp, "body", None)
                if body:
                    _w(f"predossier_{name}_{idu}.zip", bytes(body))
            except Exception as e:  # noqa: BLE001
                print("  · pré-dossier :", str(e).splitlines()[0][:120])

            # Bilan PDF + Excel
            try:
                from labuse.bilan.moteur import EntreesBilan, Moteur, Produit, Programme, SaisiePoste
                from labuse.bilan.pdf import construire_pdf as bilan_pdf
                from labuse.bilan.excel import classeur_bilan_bytes
                prog = Programme(terrain=TERRAIN[name], sdp=800, surface_taxable=800)
                prods = [Produit("Logements", 10, 800.0, 4500.0, 0.085)]
                postes = {"achat": SaisiePoste(1000, "saisi", tva=0.0),
                          "constr": SaisiePoste(2293, "saisi")}
                e = EntreesBilan(programme=prog, produits=prods, postes=postes)
                r_bil = Moteur().calculer(e)
                _w(f"bilan_{name}_{idu}.pdf",
                   bilan_pdf(r_bil, idu=idu, programme={"terrain": TERRAIN[name]}, jour=JOUR))
                _w(f"bilan_{name}_{idu}.xlsx", classeur_bilan_bytes(e, titre=f"Bilan — {idu}"))
            except Exception:  # noqa: BLE001
                print("  ✗ bilan :", traceback.format_exc().splitlines()[-1])

        # Comparatif (les 4, plafonné à 3 + note)
        try:
            from labuse.api.app import compare as _compare
            ids = list(PARCELS.values())[:3]
            data = _compare(idus=",".join(ids), db=db)
            rc = builder.construire_comparatif(ids, data.get("parcels") or [], jour=JOUR)
            _w(f"comparatif_{'_'.join(list(PARCELS)[:3])}.pdf", render_pdf(rc.html))
        except Exception:  # noqa: BLE001
            print("  ✗ comparatif :", traceback.format_exc().splitlines()[-1])

    print("\nLivrables dans", OUT)


if __name__ == "__main__":
    main()
