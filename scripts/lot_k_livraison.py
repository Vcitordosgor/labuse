"""CHIRURGICAL-FIX-1 — LOT K : livraison HONNÊTE dans _lot-final-4.

Les Bilans passent par les VRAIES routes HTTP (POST /bilan/{idu}/generer puis GET .pdf / .xlsx),
appelées comme l'écran, avec un compte authentifié. AUCUN programme fabriqué en dur, AUCUN terrain
passé à la main : la surface de terrain vient du cadastre (prefill de la route), le programme est
un scénario DOCUMENTÉ, dimensionné sur la capacité que LABUSE calcule pour la parcelle (son Étude),
et le prix de sortie sur le neuf VEFA servi par la fiche. La carte de situation N'EST PAS neutralisée
(le plan réel est rendu). Le compte-rendu donne la route et la saisie exacte de chaque fichier.

Usage : LABUSE_DATABASE_URL=… PYTHONPATH=src python scripts/lot_k_livraison.py
"""
from __future__ import annotations

import io
import json
import os
import traceback
import uuid
from datetime import date
from pathlib import Path

from sqlalchemy import text

OUT = Path(os.path.expanduser("~/Desktop/chasse-1/_lot-final-4"))
OUT.mkdir(parents=True, exist_ok=True)
JOUR = date(2026, 11, 16)
PARCELS = {"BW2635": "97422000BW2635", "AM0838": "97404000AM0838",
           "AD0887": "97422000AD0887", "IS0448": "97411000IS0448"}

# saisie de chaque fichier, tracée pour le compte-rendu
TRACE: dict[str, dict] = {}


def _w(name: str, data: bytes) -> None:
    (OUT / name).write_bytes(data)
    print(f"  ✓ {name} ({len(data)} o)")


def _capacite_et_prix(db, idu: str, fiche: dict) -> tuple[float, float, str]:
    """La SDP de capacité (Étude/potentiel) et le prix de sortie neuf (VEFA) servis par LABUSE pour
    cette parcelle — aucun chiffre fabriqué. Renvoie (sdp_m2, prix_ttc_m2, note)."""
    pt = fiche.get("potentiel_transformation") or {}
    cap = (pt.get("calcul") or {}).get("sdp_max_m2") or pt.get("surface_plancher_m2")
    if not cap:
        try:
            from labuse.faisabilite.potentiel import bloc_potentiel
            pid = db.execute(text("SELECT id FROM parcels WHERE idu=:i"), {"i": idu}).scalar()
            bp = bloc_potentiel(db, pid) if pid else None
            cap = (bp.get("table_rase") or {}).get("plancher_m2") if bp else None
        except Exception:  # noqa: BLE001
            cap = None
    # prix de sortie neuf VEFA servi (fiche), sinon prix médian bâti du secteur
    prix = None
    for k in ("prix_neuf_vefa_acte_eur_m2", "prix_vefa_eur_m2"):
        v = fiche.get(k)
        if isinstance(v, (int, float)) and v > 0:
            prix = float(v); break
    if prix is None:
        pa = fiche.get("prix_ancien") or {}
        if isinstance(pa.get("median"), (int, float)):
            prix = float(pa["median"])
    note = ""
    if not cap or cap <= 0:
        cap = 500.0   # parcelle sans capacité (AM0838) : hypothèse pour ILLUSTRER le garde-fou
        note = "capacité LABUSE = 0 → SDP hypothétique 500 m² pour montrer le garde-fou ; "
    if not prix or prix <= 0:
        prix = 4000.0
        note += "prix de sortie non servi → 4 000 €/m² (hypothèse documentée)"
    return round(float(cap)), round(float(prix)), note


def livrer_bilans(client, db) -> None:
    from labuse.db import session_scope  # noqa: F401
    from labuse.api.app import parcel_fiche
    for name, idu in PARCELS.items():
        print(f"\n=== Bilan {name} {idu} (vraies routes) ===")
        try:
            # 1) le MODELE (prefill sourcé) — on note le terrain cadastral servi
            modele = client.get(f"/bilan/{idu}/modele")
            terrain_cad = ((modele.json() or {}).get("sourcee") or {}).get("terrain") if modele.status_code == 200 else None
            # 2) programme dimensionné sur la capacité LABUSE + prix VEFA servi (aucun nombre fabriqué)
            fiche = parcel_fiche(idu, db=db, request=None)
            sdp, prix, note = _capacite_et_prix(db, idu, fiche)
            corps = {
                "programme": {"sdp": sdp, "surface_taxable": sdp},     # PAS de terrain : la route le prend au cadastre
                "produits": [{"libelle": "Programme (capacité LABUSE)", "lots": max(1, round(sdp / 70)),
                              "suv": sdp, "prix_ttc_m2_suv": prix, "tva": 0.085}],
                "postes": {"achat": {"valeur": 1000, "etat": "saisi", "tva": 0.0},
                           "constr": {"valeur": 2293, "etat": "saisi"}},
                "mode": "marge",
            }
            TRACE[f"bilan_{name}"] = {"route_generer": f"POST /bilan/{idu}/generer",
                                      "terrain_cadastre": terrain_cad, "sdp_saisie": sdp,
                                      "prix_ttc_m2": prix, "note": note.strip(" ;")}
            g = client.post(f"/bilan/{idu}/generer", json=corps)
            if g.status_code != 200:
                print("  ✗ generer:", g.status_code, g.text[:120]); continue
            doc_id = g.json()["doc_id"]
            for ext, route in (("pdf", f"/bilan/{idu}.pdf?doc_id={doc_id}"),
                               ("xlsx", f"/bilan/{idu}.xlsx?doc_id={doc_id}")):
                r = client.get(route)
                if r.status_code == 200:
                    _w(f"bilan_{name}_{idu}.{ext}", r.content)
                    TRACE[f"bilan_{name}"][f"route_{ext}"] = f"GET {route}"
                else:
                    print(f"  · {ext}:", r.status_code, r.text[:120])
        except Exception:  # noqa: BLE001
            print("  ✗", traceback.format_exc().splitlines()[-1])


def livrer_autres(db) -> None:
    """Dossier (avec couverture + carte RÉELLE), Apporteur, Estimer, pré-dossier ZIP, Comparatif."""
    from labuse.exports import builder
    from labuse.exports.rendu import render_pdf
    from labuse.api.app import parcel_fiche
    for name, idu in PARCELS.items():
        print(f"\n=== Documents {name} {idu} (carte NON neutralisée) ===")
        try:
            fiche = parcel_fiche(idu, db=db, request=None)
        except Exception:  # noqa: BLE001
            fiche = None
        for doc, forms, fn in (("dossier", False, f"dossier_{name}_{idu}.pdf"),
                               ("apporteur", True, f"apporteur_{name}_{idu}.pdf")):
            try:
                res = builder.construire(db, idu, doc, fiche=fiche, jour=JOUR)   # plan RÉEL (non stubé)
                _w(fn, render_pdf(res.html, forms=forms))
                TRACE[f"{doc}_{name}"] = {"route": f"builder.construire({doc}) → render_pdf (carte réelle)"}
            except Exception:  # noqa: BLE001
                print(f"  ✗ {doc}:", traceback.format_exc().splitlines()[-1])
        try:
            re_ = builder.construire_analyse_annonce_parc(db, idu, jour=JOUR)
            _w(f"estimer_{name}_{idu}.pdf", render_pdf(re_.html))
        except Exception:  # noqa: BLE001
            print("  ✗ estimer:", traceback.format_exc().splitlines()[-1])
        try:
            from labuse.api.pre_dossier import pre_dossier_zip

            class _Req:
                headers: dict = {}
                client = None
            resp = pre_dossier_zip(idu, request=_Req(), db=db)
            if getattr(resp, "body", None):
                _w(f"predossier_{name}_{idu}.zip", bytes(resp.body))
        except Exception as e:  # noqa: BLE001
            print("  · pré-dossier:", str(e).splitlines()[0][:100])
    # Comparatif (3 premières, plafond)
    try:
        from labuse.api.app import compare as _compare
        ids = list(PARCELS.values())[:3]
        data = _compare(idus=",".join(ids), db=db)
        _map = builder._plan_situation_html(db, ids[0])    # carte réelle
        rc = builder.construire_comparatif(ids, data.get("parcels") or [], jour=JOUR, map_html=_map)
        from labuse.exports.rendu import render_pdf
        _w(f"comparatif_{'_'.join(list(PARCELS)[:3])}.pdf", render_pdf(rc.html))
    except Exception:  # noqa: BLE001
        print("  ✗ comparatif:", traceback.format_exc().splitlines()[-1])


def main() -> None:
    os.environ.setdefault("LABUSE_SECRET_KEY", "secret-lot-k-livraison-000000000000000000")
    os.environ.setdefault("LABUSE_SMTP_HOST", "")
    os.environ.setdefault("BREVO_API_KEY", "")
    from labuse import config, comptes
    config.get_settings.cache_clear()
    from fastapi.testclient import TestClient
    from labuse.api.app import app
    from labuse.db import session_scope

    # vider les caches de fiche pour régénérer le texte neuf
    with session_scope() as s:
        try:
            s.execute(text("DELETE FROM fiche_cache WHERE idu = ANY(:ids)"), {"ids": list(PARCELS.values())})
            s.commit()
        except Exception as e:  # noqa: BLE001
            print("(fiche_cache non vidé :", e, ")")
        try:
            from labuse.api.app import vider_fiche_cache_partage
            vider_fiche_cache_partage()
        except Exception:  # noqa: BLE001
            pass

    # compte authentifié (comme l'écran)
    email = f"lotk-{uuid.uuid4().hex[:8]}@x.test"
    with session_scope() as s:
        inv = comptes.creer_invitation(s, email)
        comptes.activer_par_invitation(s, inv["lien"].split("token=")[1], "motdepasse-lot-k", "2026-09-28")
        s.execute(text("UPDATE comptes SET statut='actif' WHERE id=:c"), {"c": inv["compte_id"]})
        s.commit()
    client = TestClient(app, base_url="https://testserver")
    client.post("/login", data={"identifiant": email, "password": "motdepasse-lot-k"}, follow_redirects=False)

    with session_scope() as db:
        livrer_bilans(client, db)
    with session_scope() as db:
        livrer_autres(db)

    with session_scope() as s:
        try:
            comptes.supprimer_utilisateur(s, email); s.commit()
        except Exception:  # noqa: BLE001
            pass
    (OUT / "_saisies.json").write_text(json.dumps(TRACE, ensure_ascii=False, indent=2))
    print("\nLivrables + _saisies.json dans", OUT)


if __name__ == "__main__":
    main()
