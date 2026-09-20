#!/usr/bin/env python3
"""OUTILS-FIX-5 Lot 3 — preuve : la fiche et les 5 outils qui affichent une zone servent la MÊME
zone dominante (token = premier mot du libellé GPU, zone_servie._TOK), plus jamais le liseré/confetti.

Vérification, pas correctif : REBRANCHEMENT-1 (main edcebed7, lot 0) a rebranché la fiche
`_reglement_plu_block` sur le token (identique à `faisabilite/zone_servie._TOK`). Ce script
constate que rien n'étiquette plus au confetti sur la parcelle témoin (N 99,8 % + liseré Nerl 0,2 %).

Usage : LABUSE_API=http://127.0.0.1:8065 python captures/outils-fix5/L3-zone-preuve.py
"""
import json
import os
import urllib.request

API = os.environ.get("LABUSE_API", "http://127.0.0.1:8065")
IDU = "97410000AN0347"  # Saint-Benoît — dominante N 99,8 %, liseré Nerl 0,2 % (le piège du confetti)


def _get(path):
    with urllib.request.urlopen(f"{API}{path}", timeout=30) as r:
        return json.load(r)


def _post(path, body):
    req = urllib.request.Request(f"{API}{path}", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def main():
    resultats = {}
    # 1) Fiche §5 — bloc règlement PLU (rebranché REBRANCHEMENT-1)
    fiche = _get(f"/parcels/{IDU}?source=app")
    zones = (fiche.get("reglement_plu") or {}).get("zones") or []
    resultats["fiche_reglement_plu"] = zones[0]["zone"] if zones else None
    # 2) Faisabilité — capacite.zone = zone_servie.zone_dominante
    resultats["faisabilite"] = (_get(f"/modules/faisabilite/{IDU}").get("capacite") or {}).get("zone")
    # 3) Comparer — fa.get("zone") (fiche_payload = zone_servie)
    cmp = _get(f"/compare?idus={IDU}")
    resultats["comparer"] = (cmp.get("parcels") or [{}])[0].get("zone")
    # 4) Risques — ligne cascade « Zone <code> PLU » (parcel_zone_plu.zone_lib)
    dd = _post("/modules/duediligence", {"refs": IDU})
    blob = json.dumps(dd, ensure_ascii=False)
    import re
    m = re.search(r"Zone (\w+) PLU", blob)
    resultats["risques_cascade"] = m.group(1) if m else None
    # 5) PLU / Étudier un bien n'affichent pas d'ÉTIQUETTE de zone par parcelle (procédures ; prix
    #    terrain-par-zone) — on constate seulement l'ABSENCE du confetti dans leurs payloads.
    plu = _get(f"/modules/verif-procedure/{IDU}")
    scoreur = _post("/scoreur-adresse", {"q": IDU, "idu": IDU, "with_constat": True})
    confetti_ailleurs = {
        "plu_verif": "Nerl" in json.dumps(plu, ensure_ascii=False),
        "etudier_bien": "Nerl" in json.dumps(scoreur, ensure_ascii=False),
        "fiche": "Nerl" in json.dumps(fiche, ensure_ascii=False),
        "faisabilite_hors_zone_parts": "Nerl" in json.dumps(
            {k: v for k, v in _get(f"/modules/faisabilite/{IDU}").get("capacite", {}).items()
             if k != "zone_parts"}, ensure_ascii=False),
    }

    print("Zone dominante servie par outil (attendu : « N » partout) :")
    for k, v in resultats.items():
        print(f"  {k:22s} = {v}")
    print("\nConfetti « Nerl » présent hors zone_parts (attendu : False partout) :")
    for k, v in confetti_ailleurs.items():
        print(f"  {k:32s} = {v}")

    labels = set(v for v in resultats.values() if v)
    ok_dominante = labels == {"N"}
    ok_confetti = not any(confetti_ailleurs.values())
    print(f"\nUNE seule zone dominante servie : {ok_dominante} ({labels})")
    print(f"AUCUN confetti hors zone_parts   : {ok_confetti}")
    assert ok_dominante, f"divergence de zone entre outils : {resultats}"
    assert ok_confetti, f"confetti Nerl servi comme étiquette : {confetti_ailleurs}"
    print("\nVERT — fiche et outils servent la même zone dominante (token), zéro confetti.")


if __name__ == "__main__":
    main()
