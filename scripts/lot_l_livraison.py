"""CHIRURGICAL-FIX-1 — LOT L (4) : livraison HONNÊTE dans _lot-final-5, par les VRAIES routes HTTP.

TOUTES les pièces passent par les endpoints (compte authentifié, comme l'écran) — pas seulement les
Bilans : Dossier, Apporteur, Estimer, pré-dossier, Comparatif. AUCUN programme écrit à la main.

Deux régimes de Bilan, selon ce que LABUSE sait de la parcelle :

  · CONSTRUCTIBLE avec une Étude (AD0887, BW2635) → le vrai parcours « Bilan depuis l'Étude » :
    la SURFACE et les LOTS viennent du scénario retenu de l'Étude (scenario_etude_persiste), le
    PRIX DE VENTE est le neuf (VEFA) servi pour le secteur (resolve_prix_neuf_marche). Tout le RESTE
    reste ce que l'outil préremplit (terrain cadastral + taxe d'aménagement + archéologie, ajoutés
    par la route elle-même). Ce que l'outil ne préremplit PAS (coût d'achat, coût de construction)
    reste vide → le résultat dit « non calculable ». Chaque hypothèse est NOMMÉE dans le libellé.

  · SANS CAPACITÉ (AM0838 habitat interdit ; IS0448 pas d'Étude, potentiel 0 en l'état) → AUCUN
    programme injecté. Le Bilan livré est celui que l'outil produit DE LUI-MÊME : terrain + taxe +
    archéologie préremplis, résultat « non calculable », et surtout son GARDE-FOU affiché en tête.
    Le cas « programme saisi quand même » est prouvé par un TEST (test_chirurgical_fix_l), pas ici.

Usage : LABUSE_DATABASE_URL=… PYTHONPATH=src python scripts/lot_l_livraison.py
"""
from __future__ import annotations

import json
import os
import traceback
import uuid
from datetime import date
from pathlib import Path

from sqlalchemy import text

OUT = Path(os.path.expanduser("~/Desktop/chasse-1/_lot-final-5"))
OUT.mkdir(parents=True, exist_ok=True)
JOUR = date(2026, 11, 16)
PARCELS = {"BW2635": "97422000BW2635", "AM0838": "97404000AM0838",
           "AD0887": "97422000AD0887", "IS0448": "97411000IS0448"}

TRACE: dict[str, dict] = {}


def _w(name: str, data: bytes) -> None:
    (OUT / name).write_bytes(data)
    print(f"  ✓ {name} ({len(data)} o)")


def _programme_depuis_etude(db, idu: str) -> dict | None:
    """Le programme « depuis l'Étude » tel que l'écran le pré-remplit (BilanEcran.entreesInitiales) +
    le prix de sortie neuf servi pour le secteur. Renvoie None si la parcelle n'a pas d'Étude
    exploitable OU si l'habitat y est interdit (dans ces cas : AUCUN programme injecté)."""
    from labuse.exports import etude_faisabilite as ef
    from labuse.bilan import reperes as _rep
    from labuse.ingestion.dvf_prix_neuf import resolve_prix_neuf_marche

    gf = _rep.garde_fou_bilan(db, idu, sdp_saisie=None, postes_saisis=set())
    if gf.get("non_constructible"):
        return None    # habitat interdit → on ne propose jamais un programme de logements
    # scénario retenu de l'Étude (même config par défaut que le Dossier) : surface + lots
    from labuse.implantation import revisions as _rev
    from labuse.implantation.service import _study_id
    cfg = {"idus": [idu], "type_projet": "collectif", "objectif": "equilibre",
           "stationnement": "aerien", "terrain": "libere", "niveaux_sous_sol": None,
           "programme": None, "hypotheses": None}
    payload = _rev.charger(db, _study_id(cfg))
    retenu = ef.scenario_retenu(payload) if payload else None
    resume = (retenu or {}).get("resume") if retenu else None
    if not resume or not resume.get("sdp_m2"):
        return None    # pas d'Étude exploitable → l'outil ne propose pas de programme
    sdp = round(float(resume["sdp_m2"]))
    lots = int(resume.get("logements") or 0) or None
    pid = db.execute(text("SELECT id FROM parcels WHERE idu=:i"), {"i": idu}).scalar()
    prix, niveau, n, _ = resolve_prix_neuf_marche(db, pid) if pid else (None, None, None, None)
    return {"sdp": sdp, "lots": lots, "prix": round(float(prix)) if prix else None,
            "niveau_prix": niveau, "n_ventes_prix": n,
            "terrain_libere": bool(gf.get("terrain_libere"))}


def _corps_bilan(db, name: str, idu: str) -> tuple[dict, dict]:
    """Le corps envoyé à POST /bilan/{idu}/generer + la trace documentaire. Deux régimes."""
    prog = _programme_depuis_etude(db, idu)
    if prog is None:
        # SANS CAPACITÉ — aucun programme injecté : l'outil rend SON Bilan + son garde-fou.
        corps = {"programme": {}, "produits": [], "postes": {}, "mode": "marge"}
        tr = {"regime": "sans capacité — aucun programme injecté",
              "programme_injecte": None,
              "attendu": "résultat « non calculable » + garde-fou de la fiche en tête"}
        return corps, tr
    # CONSTRUCTIBLE — « Bilan depuis l'Étude ». 3 hypothèses nommées ; le RESTE = prefill outil.
    prix = prog["prix"]
    libelle = (f"Logements — scénario de l'Étude ({prog['lots']} lots, {prog['sdp']} m²) · "
               f"prix neuf VEFA {prog['niveau_prix']}")
    corps = {
        "programme": {"sdp": prog["sdp"]},     # surface du scénario ; terrain pris au cadastre par la route
        "produits": [{"libelle": libelle, "lots": prog["lots"], "suv": prog["sdp"],
                      "prix_ttc_m2_suv": prix, "tva": None}],   # tva non servie → laissée vide
        "postes": {},                          # RIEN saisi : la route ajoute taxe + archéologie (sourcés)
        "mode": "marge",
    }
    tr = {"regime": "constructible — Bilan depuis l'Étude",
          "hypotheses_nommees": {
              "surface_m2": {"valeur": prog["sdp"], "source": "scénario retenu de l'Étude"},
              "lots": {"valeur": prog["lots"], "source": "scénario retenu de l'Étude"},
              "prix_vente_eur_m2": {"valeur": prix, "source": f"neuf (VEFA) servi · {prog['niveau_prix']}",
                                    "n_ventes": prog["n_ventes_prix"]}},
          "prefill_outil": "terrain (cadastre) + taxe d'aménagement + redevance d'archéologie",
          "non_prerempli_reste_vide": ["coût d'achat", "coût de construction", "TVA de vente"],
          "attendu": "résultat « non calculable » (achat/construction non préremplis)"}
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
    # Comparatif (2-3 parcelles, route HTTP)
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
    os.environ.setdefault("LABUSE_SECRET_KEY", "secret-lot-l-livraison-000000000000000000")
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

    # compte authentifié AVEC un nom (l'Apporteur est signé du client → refuse sans nom)
    email = f"lotl-{uuid.uuid4().hex[:8]}@x.test"
    with session_scope() as s:
        inv = comptes.creer_invitation(s, email)
        comptes.activer_par_invitation(s, inv["lien"].split("token=")[1], "motdepasse-lot-l", "2026-09-28")
        s.execute(text("UPDATE comptes SET statut='actif', nom='SCCV Les Alizés (livraison LOT L)' "
                       "WHERE id=:c"), {"c": inv["compte_id"]})
        s.commit()
    client = TestClient(app, base_url="https://testserver")
    client.post("/login", data={"identifiant": email, "password": "motdepasse-lot-l"}, follow_redirects=False)

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
