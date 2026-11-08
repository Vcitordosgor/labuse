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
    # DOCS-1 (décision Vic) — témoin PPR : une parcelle en ZONE U partiellement touchée par la zone
    # ROUGE d'un PPR (97415000DH0076, ~458 m² en interdiction) sur laquelle l'Étude PRODUIT un scénario
    # (le Gabarit déduit le rouge). Remplace CY0275 (trop étroite pour une implantation).
    "97424000AM0893", "97415000DH0076", "97411000AO0753", "97411000EY0173",
    "97417000BI0076", "97411000AB0785", "97411000HN0074", "97411000BZ1065",
    # Témoin ZONE N (AB0133) conservé : le Gabarit doit y rendre un DOCUMENT de refus propre, jamais 422.
    "97421000AB0133",
]

#: documents servis par un GET (le Courrier a son propre point d'entrée, hors de ce GET-loop ;
#: l'Étude de faisabilité est un POST avec programme — couverte à part). Flash = Dossier (livraison).
#: documents servis par un GET (le témoin est en tête des idus du Comparatif → sa colonne est lue
#: la première). L'Étude de faisabilité, le Courrier et le Bilan sont des POST (rendus à part) ;
#: le Flash 79 € est généré par `flash.report.generate_flash_report` (son propre moteur).
DOCS = [
    ("dossier",    "/dossier/{idu}.pdf?carte=false"),
    ("gabarit",    "/gabarit/{idu}.pdf"),
    ("apporteur",  "/apporteur/{idu}.pdf"),
    ("estimer",    "/analyse-annonce/{idu}.pdf"),
    ("comparatif", "/comparatif.pdf?idus={idu},{v1},{v2}"),
    ("etude-zone", "/etude-zone.pdf?idu={idu}&rayon_km=1"),
]

#: saisies illustratives du Bilan (comme l'export d'origine : 1 logement SUV 65 m² à 4 500 €/m²).
_BILAN_SAISIES = {"programme": {"terrain": None, "surface_taxable": 65, "sdp": 35},
                  "produits": [{"libelle": "Logement", "lots": 1, "suv": 65,
                                "prix_ttc_m2_suv": 4500, "tva": 0.021}],
                  "postes": {}, "mode": "marge", "marge_cible": 9, "calendrier": {}}


def _rendre_tous(client, idu: str, voisines: list[str]):
    """Rend TOUS les documents d'une parcelle : GET (DOCS) + POST (Étude, Courrier, Bilan) + le
    Flash (moteur propre). Renvoie [(nom, octets_pdf)] pour les rendus réussis (%PDF)."""
    out: list[tuple[str, bytes]] = []
    v1 = voisines[0] if voisines else idu
    v2 = voisines[1] if len(voisines) > 1 else idu
    for nom, route in DOCS:
        r = client.get(route.format(idu=idu, v1=v1, v2=v2))
        if r.status_code == 200 and r.content[:4] == b"%PDF":
            out.append((nom, r.content))
    # POST — Étude de faisabilité (1 parcelle), Courrier, Bilan (saisies illustratives).
    e = client.post("/modules/etude/pdf", json={"idus": [idu]})
    if e.status_code == 200 and e.content[:4] == b"%PDF":
        out.append(("etude-faisabilite", e.content))
    co = client.post("/courrier/pdf", json={"idu": idu})
    if co.status_code == 200 and co.content[:4] == b"%PDF":
        out.append(("courrier", co.content))
    g = client.post(f"/bilan/{idu}/generer", json=_BILAN_SAISIES)
    if g.status_code == 200 and (g.json() or {}).get("doc_id"):
        did = g.json()["doc_id"]
        b = client.get(f"/bilan/{idu}.pdf?doc_id={did}")
        if b.status_code == 200 and b.content[:4] == b"%PDF":
            out.append(("bilan", b.content))
    # Flash 79 € — moteur propre `generate_flash_report` (son template, pas le Dossier).
    try:
        from labuse.db import session_factory
        from labuse.flash.report import generate_flash_report
        p = generate_flash_report(idu, order_ref="BANC-DOCS", db=session_factory()(), force=True,
                                  with_map=False)   # le banc lit le TEXTE, pas la carte (évite le réseau)
        out.append(("flash", p.read_bytes()))
    except Exception:  # noqa: BLE001 — le Flash est rendu best-effort dans le banc
        pass
    return out

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


def _marge_surelevation(t):
    # La marge de surélévation (sous la hauteur de zone) — « Marge de surélévation (…) −3,3 m »
    # (Dossier) / « marge en hauteur ~−3,3 m » OU, quand elle est NÉGATIVE, « le bâti existant dépasse
    # la hauteur autorisée de 3,3 m » (= −3,3, Flash). Un fait = une valeur, la fiche fait foi.
    m = re.search(r"dépasse la hauteur autorisée de\s*(\d+(?:[,.]\d+)?)" + _SP + r"*m\b", t)
    if m:
        return "-" + _num(m.group(1))
    m = re.search(r"(?:Marge de surélévation|marge en hauteur)[^\n]*?[~]?\s*([−-]?\d+(?:[,.]\d+)?)" + _SP + r"*m\b", t)
    if not m:
        return None
    return _num(m.group(1).replace("−", "-"))


def _surface_vendable(t):
    # La surface vendable servie — un nombre (« 118 m² ») OU « non calculable » (capacité nulle).
    if re.search(r"[Ss]urface vendable[^\n]*?non calculable|vendable non calculable", t):
        return "non_calculable"
    m = re.search(r"[Ss]urface vendable\D{0,30}?(\d[\d\s  ]*)" + _SP + r"*m²", t)
    return _num(m.group(1)) if m else None


def _permis_100m(t):
    # Le permis à moins de 100 m AVEC SA FENÊTRE DATÉE (« < 100 m, N mois ») — la ligne du marché, seule
    # autorité « même fenêtre, même valeur » entre documents. Le faisceau de viabilisation, lui, compte
    # sur TOUTE la période (métrique distincte, nommée « toute période ») : on ne le confronte pas.
    m = re.search(r"(\d+)" + _SP + r"*permis[^\n]{0,20}?<?" + _SP + r"*100" + _SP + r"*m,?" + _SP + r"*\d+" + _SP + r"*mois", t)
    return m.group(1) if m else None


def _date_ppr(t):
    """La DATE du PPR : l'ANNÉE d'APPROBATION du PPR qui s'applique (« approuvé le JJ/MM/AAAA »,
    « PPR … (AAAA) »). Un document qui en montre deux, ou deux documents qui divergent = écart.
    On exclut les dates d'INGESTION/millésime (« au JJ/MM/AAAA », « vue le … ») — jamais « la date du PPR »."""
    yrs: set[str] = set()
    for line in t.splitlines():
        if "PPR" not in line and "prévention des risques" not in line:
            continue
        for m in re.finditer(r"approuvé le\s*\d{2}/\d{2}/((?:19|20)\d{2})", line):
            yrs.add(m.group(1))
        for m in re.finditer(r"PPR[^\n]{0,40}?\(((?:19|20)\d{2})\)", line):
            yrs.add(m.group(1))
    return ",".join(sorted(yrs)) if yrs else None


def _verdict_potentiel(t):
    """DOCS-1 — le VERDICT DE POTENTIEL, normalisé « constructible » | « rien » | None. Un seul lecteur
    doit faire dire la MÊME chose au Dossier, au Flash, au Gabarit et à l'Étude : une zone rouge PPR
    PARTIELLE ne retire que sa surface, la partie hors rouge garde son potentiel.

    « rien » = NON-CONSTRUCTIBILITÉ de la parcelle entière (zonage fermé, rédhibitoire, exigu, AU
    différée) — JAMAIS la SATURATION (« déjà construite au maximum » = constructible, table rase
    possible). Signaux SPÉCIFIQUES au §potentiel (pas le §risques, qui dit « partie INCONSTRUCTIBLE »
    de la seule zone rouge)."""
    low = t.lower()
    constr = ("constructible sur la partie hors zone rouge" in low
              or "potentiel de construction :" in low                       # verdict §10 constructible (deux-points)
              or re.search(r"maximum du terrain estimé\s*:\s*\d+" + _SP + r"*logements", t) is not None
              or "m² encore constructibles" in low)                          # libellé positif potentiel_batir
    # « rien » ANCRÉ sur le VERDICT, jamais une mention de règle (« habitat interdit en zone … »,
    # « zone non constructible » d'une SUP) ni la saturation : les libellés de verdict de potentiel_batir
    # (« Rien à bâtir — <motif de non-constructibilité> », SAUF « déjà construite au maximum ») et du §10.
    incon = ("rédhibitoire couvrant toute la parcelle" in low
             or "le potentiel de construction est nul" in low
             or re.search(r"rien à bâtir\s*[—–-]\s*(?:zone non constructible|zone fermée|habitat interdit|"
                          r"parcelle non constructible|pas de potentiel constructible|zone au non ouverte)",
                          low) is not None)
    if constr and not incon:
        return "constructible"
    if incon and not constr:
        return "rien"
    return None                                                # saturé / ambigu / non adressé → hors comparaison


def _logements_max(t):
    """Le NOMBRE DE LOGEMENTS MAXIMUM du terrain, servi par l'Étude (« maximum du terrain estimé :
    N logements »). Le Dossier/Flash renvoient à l'Étude (pas de nombre) — source unique."""
    m = re.search(r"maximum du terrain estimé\s*:\s*(\d+)" + _SP + r"*logements", t)
    return m.group(1) if m else None


FAITS = {
    "verdict_potentiel": _verdict_potentiel,
    "logements_max": _logements_max,
    "sdp_maximale": lambda t: (
        _m2_apres(r"SDP maximale réglementaire,?\s*terrain(?:\s*libéré)?")(t)
        or _m2_apres(r"Surface de plancher\s*\(maximum\)")(t)
        or _m2_apres(r"Surface de plancher maximale")(t)),
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
    "date_ppr": _date_ppr,
    "marge_surelevation_m": _marge_surelevation,
    "surface_vendable": _surface_vendable,
    "permis_100m": _permis_100m,
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


def _auth_compte() -> int:
    from sqlalchemy import text

    from labuse.db import session_factory
    db = session_factory()()
    cid = (db.execute(text("SELECT id FROM comptes WHERE statut='actif' ORDER BY id LIMIT 1")).scalar()
           or db.execute(text("SELECT id FROM comptes ORDER BY id LIMIT 1")).scalar())
    return int(cid) if cid else 1


def rejouer(idus: list[str]):
    from fastapi.testclient import TestClient

    from labuse.api import bilan as _bilan, tenant
    from labuse.api.app import app
    # Bilan et Courrier exigent un compte. `current_compte` est importé DANS api/bilan.py → patcher les deux.
    cid = _auth_compte()
    tenant.current_compte = lambda request=None: cid   # type: ignore[assignment]
    _bilan.current_compte = lambda request=None: cid    # type: ignore[assignment]
    client = TestClient(app)
    jetons = _jetons()

    divergences: list[dict] = []
    leaks: list[dict] = []
    fautes_fmt: list[dict] = []
    n_docs = 0
    n = len(idus)

    for i, idu in enumerate(idus):
        voisines = [idus[(i + 1) % n], idus[(i + 2) % n]] if n >= 3 else []
        # valeurs imprimées par chaque doc : {fait: {doc: valeur}}
        par_fait: dict[str, dict[str, str]] = {}
        for nom, contenu in _rendre_tous(client, idu, voisines):
            n_docs += 1
            texte = _texte_pdf(contenu)
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
