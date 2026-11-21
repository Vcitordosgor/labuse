"""CHIRURGICAL-FIX-1 — LOT R : livraison HONNÊTE dans _lot-final-11, par les VRAIES routes HTTP.

Reprend LOT L, avec les corrections de la liste fermée du relecteur (6ᵉ passage) :

  1. Les VRAIES valeurs du parcours écran. L'écran (BilanEcran.tsx:97) envoie comme surface VENDABLE
     la **surface habitable** du scénario (`programme.shab_estimee_m2` : 224 m² BW2635, 572 AD0887),
     PAS la surface de plancher (360 / 795). On transmet donc SDP et SUV DISTINCTES, à l'identique de
     l'écran → le CA n'est plus surestimé de 618 392 € / 962 914 €.
  2. Une seule convention de TVA : la TVA de vente n'est pas saisie → le CA HT, le net promoteur et la
     marge sont « non calculable » (plus de 8,5 % forfaitaires côté PDF). Le CA TTC reste connu.
  3. Le terrain sans programme : AM0838 / IS0448 sont livrés SANS programme → le Bilan de l'outil
     porte « Aucun programme » et aucune « surface à retenir » fantôme.

Aucun programme écrit à la main : surface/lots/SHAB viennent du scénario retenu de l'Étude, le prix du
neuf (VEFA) servi pour le secteur, le terrain du cadastre (prefill de la route). Toutes les pièces
(Dossier, Apporteur, Estimer, pré-dossier, Comparatif) passent par les routes HTTP.

LOT N — régénération après durcissement : couverture qui NOMME les hypothèses (scénario + prix),
bandeau « Aucun programme » qui reprend la distinction du Dossier (bâti conservé / terrain libéré).

Usage : LABUSE_DATABASE_URL=… PYTHONPATH=src python scripts/lot_n_livraison.py
"""
from __future__ import annotations

import json
import os
import traceback
import uuid
from pathlib import Path

from sqlalchemy import text

OUT = Path(os.path.expanduser("~/Desktop/chasse-1/_lot-final-11"))
OUT.mkdir(parents=True, exist_ok=True)
PARCELS = {"BW2635": "97422000BW2635", "AM0838": "97404000AM0838",
           "AD0887": "97422000AD0887", "IS0448": "97411000IS0448"}

TRACE: dict[str, dict] = {}


def _w(name: str, data: bytes) -> None:
    (OUT / name).write_bytes(data)
    print(f"  ✓ {name} ({len(data)} o)")


def _programme_depuis_etude(db, idu: str) -> dict | None:
    """Le programme « depuis l'Étude » tel que l'écran le pré-remplit (BilanEcran.entreesInitiales) +
    le prix de sortie neuf servi pour le secteur. Renvoie None si la parcelle n'a pas d'Étude
    exploitable OU si l'habitat y est interdit (dans ces cas : AUCUN programme injecté).

    LOT M 1 — SDP (plancher) et SUV (vendable = surface HABITABLE estimée) sont DISTINCTES, comme à
    l'écran (`sdp_m2` du résumé ; `shab_estimee_m2` du programme du scénario)."""
    from labuse.exports import etude_faisabilite as ef
    from labuse.bilan import reperes as _rep
    from labuse.ingestion.dvf_prix_neuf import resolve_prix_neuf_marche

    gf = _rep.garde_fou_bilan(db, idu, sdp_saisie=None, postes_saisis=set())
    if gf.get("non_constructible"):
        return None    # habitat interdit → on ne propose jamais un programme de logements
    from labuse.implantation import revisions as _rev
    from labuse.implantation.service import _study_id
    cfg = {"idus": [idu], "type_projet": "collectif", "objectif": "equilibre",
           "stationnement": "aerien", "terrain": "libere", "niveaux_sous_sol": None,
           "programme": None, "hypotheses": None}
    payload = _rev.charger(db, _study_id(cfg))
    retenu = ef.scenario_retenu(payload) if payload else None
    if not retenu:
        return None
    resume = retenu.get("resume") or {}
    prog = retenu.get("programme") or {}
    sdp = resume.get("sdp_m2")
    shab = prog.get("shab_estimee_m2")       # LOT M 1 — la surface VENDABLE de l'écran = la SHAB
    if not sdp or not shab:
        return None    # pas d'Étude exploitable → l'outil ne propose pas de programme
    lots = int(resume.get("logements") or 0) or None
    pid = db.execute(text("SELECT id FROM parcels WHERE idu=:i"), {"i": idu}).scalar()
    prix, niveau, n, _ = resolve_prix_neuf_marche(db, pid) if pid else (None, None, None, None)
    return {"sdp": round(float(sdp)), "suv": round(float(shab)), "lots": lots,
            "prix": round(float(prix)) if prix else None, "niveau_prix": niveau, "n_ventes_prix": n,
            "terrain_libere": bool(gf.get("terrain_libere"))}


def _corps_bilan(db, name: str, idu: str) -> tuple[dict, dict]:
    """Le corps envoyé à POST /bilan/{idu}/generer + la trace documentaire. Deux régimes."""
    prog = _programme_depuis_etude(db, idu)
    if prog is None:
        # LOT M 3 — SANS programme : l'outil rend SON Bilan ; le bandeau dira « Aucun programme ».
        corps = {"programme": {}, "produits": [], "postes": {}, "mode": "marge"}
        tr = {"regime": "sans capacité — aucun programme injecté",
              "programme_injecte": None,
              "attendu": "bandeau « Aucun programme », aucune « surface à retenir », « non calculable »"}
        return corps, tr
    # CONSTRUCTIBLE — « Bilan depuis l'Étude » ; surface de plancher ET surface vendable (habitable).
    prix = prog["prix"]
    libelle = (f"Logements — scénario de l'Étude ({prog['lots']} lots, SHAB {prog['suv']} m² "
               f"sur {prog['sdp']} m² de plancher) · prix neuf VEFA {prog['niveau_prix']}")
    corps = {
        # SDP (plancher) = repère ; la route prend le terrain au cadastre.
        "programme": {"sdp": prog["sdp"]},
        # surface VENDABLE = SHAB (≠ SDP), exactement comme l'écran ; TVA de vente laissée VIDE.
        "produits": [{"libelle": libelle, "lots": prog["lots"], "suv": prog["suv"],
                      "prix_ttc_m2_suv": prix, "tva": None}],
        "postes": {},                          # RIEN saisi : la route ajoute taxe + archéologie (sourcés)
        "mode": "marge",
    }
    tr = {"regime": "constructible — Bilan depuis l'Étude",
          "hypotheses_nommees": {
              "surface_de_plancher_m2": {"valeur": prog["sdp"], "source": "scénario retenu de l'Étude"},
              "surface_vendable_m2": {"valeur": prog["suv"],
                                      "source": "surface habitable estimée du scénario (= l'écran)"},
              "lots": {"valeur": prog["lots"], "source": "scénario retenu de l'Étude"},
              "prix_vente_eur_m2": {"valeur": prix, "source": f"neuf (VEFA) servi · {prog['niveau_prix']}",
                                    "n_ventes": prog["n_ventes_prix"]}},
          "ca_ttc_attendu_eur": (prog["suv"] * prix) if prix else None,
          "prefill_outil": "terrain (cadastre) + taxe d'aménagement + redevance d'archéologie",
          "non_prerempli_reste_vide": ["coût d'achat", "coût de construction", "TVA de vente"],
          "attendu": "CA HT / net promoteur / marge « non calculable » (TVA vide) ; résultat « non calculable »"}
    return corps, tr


def livrer_bilans(client, db) -> None:
    for name, idu in PARCELS.items():
        print(f"\n=== Bilan {name} {idu} (vraies routes) ===")
        try:
            corps, tr = _corps_bilan(db, name, idu)
            modele = client.get(f"/bilan/{idu}/modele")
            tr["terrain_cadastre"] = (((modele.json() or {}).get("sourcee") or {}).get("terrain")
                                      if modele.status_code == 200 else None)
            tr["route_generer"] = f"POST /bilan/{idu}/generer"
            TRACE[f"bilan_{name}"] = tr
            g = client.post(f"/bilan/{idu}/generer", json=corps)
            if g.status_code != 200:
                print("  ✗ generer:", g.status_code, g.text[:160]); continue
            doc_id = g.json()["doc_id"]
            for ext in ("pdf", "xlsx"):
                route = f"/bilan/{idu}.{ext}?doc_id={doc_id}"
                r = client.get(route)
                if r.status_code == 200:
                    _w(f"bilan_{name}_{idu}.{ext}", r.content)
                    tr[f"route_{ext}"] = f"GET {route}"
                else:
                    print(f"  · {ext}:", r.status_code, r.text[:160])
        except Exception:  # noqa: BLE001
            print("  ✗", traceback.format_exc().splitlines()[-1])


def livrer_pieces(client) -> None:
    """Dossier, Apporteur, Estimer, pré-dossier, Comparatif — TOUT par les routes HTTP."""
    pieces = (("dossier", "/dossier/{idu}.pdf", "pdf"),
              ("apporteur", "/apporteur/{idu}.pdf", "pdf"),
              ("estimer", "/analyse-annonce/{idu}.pdf", "pdf"),
              ("predossier", "/pre-dossier/{idu}.zip", "zip"))
    for name, idu in PARCELS.items():
        print(f"\n=== Pièces {name} {idu} (routes HTTP) ===")
        for doc, tmpl, ext in pieces:
            route = tmpl.format(idu=idu)
            try:
                r = client.get(route)
                if r.status_code == 200:
                    _w(f"{doc}_{name}_{idu}.{ext}", r.content)
                    TRACE[f"{doc}_{name}"] = {"route": f"GET {route}"}
                else:
                    print(f"  · {doc}: {r.status_code} {r.text[:120]}")
                    TRACE[f"{doc}_{name}"] = {"route": f"GET {route}", "statut": r.status_code,
                                             "motif": r.text[:160]}
            except Exception:  # noqa: BLE001
                print(f"  ✗ {doc}:", traceback.format_exc().splitlines()[-1])
    ids = list(PARCELS.values())[:3]
    route = f"/comparatif.pdf?idus={','.join(ids)}"
    try:
        r = client.get(route)
        if r.status_code == 200:
            _w(f"comparatif_{'_'.join(list(PARCELS)[:3])}.pdf", r.content)
            TRACE["comparatif"] = {"route": f"GET {route}"}
        else:
            print("  · comparatif:", r.status_code, r.text[:160])
            TRACE["comparatif"] = {"route": f"GET {route}", "statut": r.status_code, "motif": r.text[:160]}
    except Exception:  # noqa: BLE001
        print("  ✗ comparatif:", traceback.format_exc().splitlines()[-1])


def main() -> None:
    os.environ.setdefault("LABUSE_SECRET_KEY", "secret-lot-r-livraison-000000000000000000")
    os.environ.setdefault("LABUSE_SMTP_HOST", "")
    os.environ.setdefault("BREVO_API_KEY", "")
    os.environ.setdefault("LABUSE_PLAN_DEFAUT", "integral")   # pré-dossier PC (plan Intégral)
    from labuse import config, comptes
    config.get_settings.cache_clear()
    from fastapi.testclient import TestClient
    from labuse.api.app import app
    from labuse.db import session_scope

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

    email = f"lotr-{uuid.uuid4().hex[:8]}@x.test"
    with session_scope() as s:
        inv = comptes.creer_invitation(s, email)
        comptes.activer_par_invitation(s, inv["lien"].split("token=")[1], "motdepasse-lot-r", "2026-09-28")
        s.execute(text("UPDATE comptes SET statut='actif', nom='SCCV Les Alizés (livraison LOT R)' "
                       "WHERE id=:c"), {"c": inv["compte_id"]})
        s.commit()
    client = TestClient(app, base_url="https://testserver")
    client.post("/login", data={"identifiant": email, "password": "motdepasse-lot-r"}, follow_redirects=False)

    with session_scope() as db:
        livrer_bilans(client, db)
    livrer_pieces(client)

    with session_scope() as s:
        try:
            comptes.supprimer_utilisateur(s, email); s.commit()
        except Exception:  # noqa: BLE001
            pass
    (OUT / "_saisies.json").write_text(json.dumps(TRACE, ensure_ascii=False, indent=2))
    print("\nLivrables + _saisies.json dans", OUT)


if __name__ == "__main__":
    main()
