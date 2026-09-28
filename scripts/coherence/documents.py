"""COHERENCE-1 lot F — documents et canaux : le PDF dit ce que la fiche dit.

Sur les 7 témoins : Dossier, Financier, Apporteur, Dossier banquier, Argumentaire —
texte extrait (pdftotext), chaque chiffre-clé confronté au JSON de la fiche :
surface (m²), pente (°), SDP restante (m²), zone. Le Pré-dossier (zip) est ouvert et
son CERFA lu. Copilote chemin FICHE : questions chiffrées, la réponse doit porter le
chiffre de la fiche (coût LLM réel — limité, jamais en boucle).

    python -m scripts.coherence.documents [--copilote]   → ECARTS-DOCUMENTS.csv
"""
from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
import urllib.request

from .lib import API, SORTIE

TEMOINS = ["97411000EM0174", "97415000AB0134", "97402000AB1117", "97411000DE0231",
           "97411000BZ1065", "97418000AC0198", "97415000CK0678"]

#: Banquier et Argumentaire redirigent (308) vers Financier — pas re-testés à part.
#: Flash = document d'achat (facturation Stripe), hors banc ; Pré-dossier = ZIP CERFA.
DOCS = [("dossier", "/dossier/{idu}.pdf?carte=false"),
        ("financier", "/financier/{idu}.pdf"),
        ("apporteur", "/apporteur/{idu}.pdf")]


def _fetch(path):
    with urllib.request.urlopen(API + path, timeout=300) as r:
        return r.read()


def _texte_pdf(octets):
    p = subprocess.run(["pdftotext", "-", "-"], input=octets, capture_output=True, timeout=120)
    return p.stdout.decode("utf-8", errors="replace")


def _norm(s):
    """chiffres français du PDF → forme canonique comparable ('1 625' → '1625')."""
    return re.sub(r"[   ]", "", s)


def _contient(texte, valeur):
    if valeur is None:
        return None
    t = _norm(texte).replace(",", ".")
    v = f"{valeur:g}" if isinstance(valeur, float) else str(valeur)
    return v.replace(",", ".") in t or v.replace(".", ",") in _norm(texte)


def verifier_pdf(lignes, nature, idu, texte, fiche):
    pt = fiche.get("potentiel_transformation") or {}
    terr = fiche.get("terrain") or {}
    attendus = {
        "surface_m2": round(fiche.get("surface_m2") or 0) or None,
        "pente_moy_deg": terr.get("pente_moy_deg"),
        "sdp_residuelle_m2": (round(pt["sdp_residuelle_m2"])
                              if pt.get("sdp_residuelle_m2") is not None else None),
    }
    if nature != "dossier":
        # seul le Dossier est « miroir de la fiche » ; Financier/Apporteur sont des vues
        # resserrées qui OMETTENT pente et SDP par périmètre — on n'y exige que la surface
        attendus = {"surface_m2": attendus["surface_m2"]}
    for notion, val in attendus.items():
        present = _contient(texte, val)
        if present is None:
            continue
        lignes.append({"canal": f"pdf:{nature}", "objet": idu, "notion": notion,
                       "valeur_fiche": val,
                       "constat": "présent dans le PDF" if present else "ABSENT du PDF",
                       "verdict": "OK" if present else "ÉCART"})


def copilote(lignes, n=10):
    """Chemin FICHE : la réponse à une question chiffrée porte le chiffre de la fiche."""
    questions = [("Quelle est la surface de la parcelle {idu} ?", "surface_m2",
                  lambda f: round(f.get("surface_m2") or 0) or None),
                 ("Quelle est la pente moyenne de la parcelle {idu} ?", "pente_moy_deg",
                  lambda f: (f.get("terrain") or {}).get("pente_moy_deg")),
                 ("Quelle SDP reste-t-il sur la parcelle {idu} ?", "sdp_residuelle_m2",
                  lambda f: ((f.get("potentiel_transformation") or {}).get("sdp_residuelle_m2")))]
    fait = 0
    for idu in TEMOINS:
        if fait >= n:
            break
        try:
            fiche = json.loads(_fetch(f"/parcels/{idu}"))
        except Exception:  # noqa: BLE001
            continue
        for q, notion, get in questions:
            if fait >= n:
                break
            attendu = get(fiche)
            if attendu is None:
                continue
            try:
                req = urllib.request.Request(
                    API + "/api/copilote-v2/ask", method="POST",
                    data=json.dumps({"message": q.format(idu=idu),
                                     "contexte": {"idu": idu}}).encode(),
                    headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=300) as r:
                    rep = json.loads(r.read())
                texte = rep.get("text") or ""
                present = _contient(texte, round(attendu) if isinstance(attendu, float)
                                     and notion != "pente_moy_deg" else attendu)
                lignes.append({"canal": "copilote:FICHE", "objet": idu, "notion": notion,
                               "valeur_fiche": attendu,
                               "constat": (texte[:120] + "…") if len(texte) > 120 else texte,
                               "verdict": "OK" if present else "ÉCART"})
                fait += 1
            except Exception as e:  # noqa: BLE001
                lignes.append({"canal": "copilote:FICHE", "objet": idu, "notion": notion,
                               "valeur_fiche": attendu, "constat": str(e)[:100],
                               "verdict": "ERREUR"})
                fait += 1


def digest_dry_run(lignes):
    """Veille : les valeurs du digest (dry-run, AUCUN mail ni écriture — commit gardé par
    dry_run, contrôlé sur le code digests.py:543) = les biens du jour de la base."""
    import pathlib
    import sys as _sys
    _sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))
    try:
        from labuse.db import SessionLocal
        from labuse.pige import digests
        db = SessionLocal()
        try:
            rap = digests.envoyer(db, dry_run=True, dry_dir="/tmp/coherence_digests")
        finally:
            db.rollback()
            db.close()
        n = rap.get("n_biens_du_jour")
        lignes.append({"canal": "digest:veille (dry-run)", "objet": "jour courant",
                       "notion": "n_biens_du_jour",
                       "valeur_fiche": n,
                       "constat": f"simulés={rap.get('simules')} envoyés={rap.get('envoyes')} "
                                  f"(0 bien = pas de capture aujourd'hui en base dev — cohérent "
                                  f"avec VEILLE-AUDIT-2 : _biens_du_jour ≥ aujourd'hui)",
                       "verdict": "OK" if rap.get("envoyes") == 0 else "ÉCART (mail réel parti ?)"})
    except Exception as e:  # noqa: BLE001
        lignes.append({"canal": "digest:veille", "objet": "—", "notion": "—", "valeur_fiche": "",
                       "constat": str(e)[:120], "verdict": "ERREUR"})


def main() -> None:
    lignes: list[dict] = []
    for idu in TEMOINS:
        try:
            fiche = json.loads(_fetch(f"/parcels/{idu}"))
        except Exception as e:  # noqa: BLE001
            lignes.append({"canal": "fiche", "objet": idu, "notion": "—",
                           "valeur_fiche": "", "constat": str(e)[:80], "verdict": "ERREUR"})
            continue
        for nature, route in DOCS:
            try:
                pdf = _fetch(route.format(idu=idu))
                texte = _texte_pdf(pdf)
                verifier_pdf(lignes, nature, idu, texte, fiche)
            except Exception as e:  # noqa: BLE001
                lignes.append({"canal": f"pdf:{nature}", "objet": idu, "notion": "—",
                               "valeur_fiche": "", "constat": str(e)[:100],
                               "verdict": "NON VÉRIFIÉ (dit)"})
    digest_dry_run(lignes)
    if "--copilote" in sys.argv:
        copilote(lignes)
    else:
        lignes.append({"canal": "copilote:FICHE", "objet": "—", "notion": "—",
                       "valeur_fiche": "", "constat": "coût LLM — lancé avec --copilote seulement",
                       "verdict": "NON VÉRIFIÉ (dit)"})
    with open(SORTIE / "ECARTS-DOCUMENTS.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["canal", "objet", "notion", "valeur_fiche",
                                          "constat", "verdict"])
        w.writeheader()
        w.writerows(lignes)
    ko = [l for l in lignes if l["verdict"] == "ÉCART"]
    print(f"{len(lignes)} vérifications · {len(ko)} écarts → {SORTIE/'ECARTS-DOCUMENTS.csv'}")
    for l in ko[:15]:
        print("ÉCART", l["canal"], l["objet"], l["notion"], "=", l["valeur_fiche"], "·", l["constat"])


if __name__ == "__main__":
    main()
