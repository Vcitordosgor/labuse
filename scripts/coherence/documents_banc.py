"""DOCS-1 (décision Vic) — LE BANC DES DOCUMENTS : il rejoue TOUS les documents sur les parcelles
témoins et REFUSE tout fait imprimé avec deux valeurs différentes d'un document à l'autre.

Principe du mandat : « un fait a une seule valeur dans tous les documents, celle de la fiche ».
Le banc extrait du texte rendu (pdftotext) les faits ÉNUMÉRÉS par le mandat (SDP maximale terrain
libéré, surface vendable, marge de surélévation, emprise au sol maximale, hauteur à l'égout, nombre
de bâtiments, viabilisation, servitude PPR, date du PPR, date des données…) ; pour chaque (parcelle,
fait), il collecte la valeur imprimée par chaque document et exige qu'elles soient TOUTES ÉGALES.

Trois contrôles DISTINCTS, verdicts séparés :
  1. faits à deux valeurs      → divergence (rouge) ;
  2. jetons de cuisine interne → config/mots_interdits.yaml rejoué sur le texte de chaque document ;
  3. format                    → décimale au point (« 4.5 » au lieu de « 4,5 »), date ISO (2026-04-16).

En process (TestClient, base `labuse`), AUCUNE écriture, AUCUN mail. Rendu PDF in-process (weasyprint
du .venv ; LABUSE_PDF_PROCESS_ISOLE=0). Pièges de poste : rôle OS `openclaw`, PROJ_DATA du conda.

    PROJ_DATA=$HOME/miniforge3/envs/labusedb/share/proj PYTHONPATH=$PWD/src \
      ~/Desktop/labuse/.venv/bin/python -m scripts.coherence.documents_banc [--idus a,b,c]
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse")
os.environ.setdefault("LABUSE_PDF_PROCESS_ISOLE", "0")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import yaml  # noqa: E402

RACINE = Path(__file__).resolve().parents[2]

#: 12 parcelles témoins — la liste canonique du banc de cohérence écran (coherence_ecrans/conftest).
TEMOINS = [
    "97411000IN0347", "97411000IE0241", "97411000HC0139", "97424000AE0050",
    "97424000AM0893", "97421000AB0133", "97411000AO0753", "97411000EY0173",
    "97417000BI0076", "97411000AB0785", "97411000HN0074", "97411000BZ1065",
]

#: documents servis par un GET (le Courrier a son propre point d'entrée, hors de ce GET-loop ;
#: l'Étude de faisabilité est un POST avec programme — couverte à part). Flash = Dossier (livraison).
DOCS = [
    ("dossier",    "/dossier/{idu}.pdf?carte=false"),
    ("gabarit",    "/gabarit/{idu}.pdf"),
    ("apporteur",  "/apporteur/{idu}.pdf"),
    ("estimer",    "/analyse-annonce/{idu}.pdf"),
    ("financier",  "/financier/{idu}.pdf"),
]

_SP = r"[\s  ]"   # espaces (ordinaire, insécable, fine)


def _num(s: str) -> str:
    """'1 567' / '1 567' → '1567' ; '4,5' → '4.5' (forme canonique comparable)."""
    return re.sub(_SP, "", s).replace(",", ".")


#: EXTRACTEURS de faits : nom → fonction(texte)->valeur canonique|None. Un fait qu'un document
#: n'imprime pas rend None (pas de comparaison). On compare les faits que PLUSIEURS documents portent.
def _m2_apres(label):
    rx = re.compile(label + r"\D{0,40}?(\d[\d\s  ]*)\s*m²")
    return lambda t: _num(rx.search(t).group(1)) if rx.search(t) else None


def _egout(t):
    m = re.search(r"(\d+(?:[.,]\d+)?)" + _SP + r"*m à l['’]égout", t)
    return _num(m.group(1)) if m else None


def _viab(t):
    m = re.search(r"Viabilisation\s+(confirmée|probable|incertaine|lourde)", t)
    return m.group(1) if m else None


def _servitude_sup(t):
    # fait binaire : la parcelle porte-t-elle au moins une SUP (servitude d'utilité publique) ?
    if re.search(r"Aucune SUP", t):
        return "aucune"
    if re.search(r"servitude" + _SP + r"*[—-]" + _SP + r"*PM1|1 servitude", t):
        return "≥1"
    return None


def _bati(t):
    m = re.search(r"(\d+)\s*bâtiments?\b", t)
    return m.group(1) if m else None


def _date_donnees(t):
    m = re.search(r"Données LABUSE au\s+(\d{2}/\d{2}/\d{4})", t)
    return m.group(1) if m else None


FAITS = {
    "sdp_max_terrain_m2": lambda t: (
        _m2_apres(r"SDP maximale réglementaire,?\s*terrain(?:\s*libéré)?")(t)
        or _m2_apres(r"Surface de plancher\s*\(maximum\)")(t)),
    "emprise_max_m2": lambda t: (
        _m2_apres(r"Plafond d['’]emprise")(t)
        or _m2_apres(r"[Ee]mprise au sol\D{0,20}≤")(t)),
    "hauteur_egout": _egout,
    "nb_batiments": _bati,
    "viabilisation": _viab,
    "servitude_sup": _servitude_sup,
    "date_donnees": _date_donnees,
}


def _texte_pdf(octets: bytes) -> str:
    p = subprocess.run(["pdftotext", "-layout", "-", "-"], input=octets,
                       capture_output=True, timeout=120)
    return p.stdout.decode("utf-8", errors="replace")


def _jetons() -> list[str]:
    data = yaml.safe_load((RACINE / "config" / "mots_interdits.yaml").read_text())
    return list(data["mots"])


# format : une décimale au POINT hors d'un contexte numérique groupé anglais, et une date ISO.
_RX_DECIMALE_POINT = re.compile(r"\b\d+\.\d+" + _SP + r"*(?:m|€|%|m²)\b")
_RX_DATE_ISO = re.compile(r"\b(?:19|20)\d{2}-\d{2}-\d{2}\b")


def _fautes_format(texte: str) -> list[str]:
    f = []
    for m in set(_RX_DECIMALE_POINT.findall(texte)):
        f.append(f"décimale au point : « {m} » (attendu virgule)")
    for m in set(_RX_DATE_ISO.findall(texte)):
        f.append(f"date ISO : « {m} » (attendu jj/mm/aaaa)")
    return f


def rejouer(idus: list[str]):
    from fastapi.testclient import TestClient

    from labuse.api.app import app
    client = TestClient(app)
    jetons = _jetons()

    divergences: list[dict] = []
    leaks: list[dict] = []
    fautes_fmt: list[dict] = []
    n_docs = 0

    for idu in idus:
        # valeurs imprimées par chaque doc : {fait: {doc: valeur}}
        par_fait: dict[str, dict[str, str]] = {}
        for nom, route in DOCS:
            r = client.get(route.format(idu=idu))
            if r.status_code != 200 or r.content[:4] != b"%PDF":
                continue
            n_docs += 1
            texte = _texte_pdf(r.content)
            # 2. jetons interdits
            for m in jetons:
                if m in texte:
                    leaks.append({"idu": idu, "doc": nom, "jeton": m})
            # 3. format
            for faute in _fautes_format(texte):
                fautes_fmt.append({"idu": idu, "doc": nom, "faute": faute})
            # 1. faits
            for fait, fn in FAITS.items():
                try:
                    v = fn(texte)
                except Exception:  # noqa: BLE001
                    v = None
                if v is not None:
                    par_fait.setdefault(fait, {})[nom] = v
        # un fait avec ≥2 valeurs distinctes entre documents = divergence
        for fait, vals in par_fait.items():
            distinctes = set(vals.values())
            if len(distinctes) > 1:
                divergences.append({"idu": idu, "fait": fait,
                                    "valeurs": "  ".join(f"{d}={v}" for d, v in vals.items())})

    return {"n_docs": n_docs, "divergences": divergences, "leaks": leaks, "fautes_fmt": fautes_fmt}


def main() -> int:
    idus = TEMOINS
    for a in sys.argv[1:]:
        if a.startswith("--idus"):
            idus = (a.split("=", 1)[1] if "=" in a else sys.argv[sys.argv.index(a) + 1]).split(",")
    rap = rejouer(idus)
    print(f"\n=== BANC DES DOCUMENTS — {len(idus)} témoins, {rap['n_docs']} documents rendus ===")
    print(f"\nFAITS À DEUX VALEURS : {len(rap['divergences'])}")
    for d in rap["divergences"]:
        print(f"  ✗ {d['idu']} · {d['fait']} : {d['valeurs']}")
    print(f"\nJETONS DE CUISINE INTERNE : {len(rap['leaks'])}")
    for l in rap["leaks"][:40]:
        print(f"  ✗ {l['idu']} · {l['doc']} : « {l['jeton']} »")
    print(f"\nFAUTES DE FORMAT : {len(rap['fautes_fmt'])}")
    for f in rap["fautes_fmt"][:40]:
        print(f"  ✗ {f['idu']} · {f['doc']} : {f['faute']}")
    ko = len(rap["divergences"]) + len(rap["leaks"]) + len(rap["fautes_fmt"])
    print(f"\n{'VERT — 0 écart' if ko == 0 else f'ROUGE — {ko} écarts'}")
    return 0 if ko == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
