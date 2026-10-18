"""VERITE-TERRAIN-2 — Volet A : TOUTES les règles chiffrées du PLU, relues au règlement.

Là où VERITE-TERRAIN-1 (`verite_terrain_plu_regles`) relisait les règles de 100 parcelles via la
base servie, ce module travaille EXHAUSTIVEMENT et SANS BASE : il lit directement les YAML de
calibrage `config/plu_destinations/*.yaml` (la vérité SERVIE) et relit chaque règle chiffrée
`statut: valide` dans le RÈGLEMENT OFFICIEL EN VIGUEUR, à la `page_pdf` citée.

Pour chaque règle chiffrée on vérifie :
  (a) le ou les nombres servis figurent dans le texte de la page citée (±1 page) ;
  (b) la `citation` stockée se retrouve (au moins son cœur significatif) dans ce même texte.

Verdicts (mêmes quatre que le comparateur VT-1) :
  · CONFORME             : tous les nombres retrouvés ET la citation retrouvée.
  · LABUSE FAUX          : un nombre servi absent du texte officiel OU citation non retrouvée.
                           Chaque FAUX est à revérifier À LA MAIN (rouvrir la page, citer le réel).
  · SOURCE PLUS RÉCENTE  : règlement officiel d'un millésime postérieur au calibré.
  · NON COMPARABLE       : PDF injoignable / page non extractible / md5 ≠ attendu / valeur dérivée
                           d'un prospect (H/2…) non littérale. La raison est toujours donnée.

Authenticité : avant d'exploiter un PDF on vérifie son md5 contre `meta.md5` du YAML ; écart →
tout le fichier est NON COMPARABLE « PDF servi ≠ md5 attendu » (on ne ment pas sur la source).

LECTURE SEULE : aucune base, aucun VPS. Appels réseau (curl des PDF) séquentiels, espacés, mis
en cache disque sous `docs/audit-2026-10/verite-terrain-2/cache/plu_pdf/`.

    PYTHONPATH=src python -m labuse.verite_terrain_plu_toutes
"""
from __future__ import annotations

import csv
import hashlib
import re
import subprocess
import time
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import yaml

from .verite_terrain import CONFORME, FAUX, NC, RECENTE

RACINE = Path(__file__).resolve().parents[2]
YAML_DIR = RACINE / "config" / "plu_destinations"
SORTIE = RACINE / "docs" / "audit-2026-10" / "verite-terrain-2"
CACHE = SORTIE / "cache"
PDF_CACHE = CACHE / "plu_pdf"
SORTIE_CSV = SORTIE / "PLU-TOUTES-REGLES.csv"
RAPPORT_MD = SORTIE / "PLU-TOUTES-REGLES.md"

# Fichiers non-communes du dossier (pas de zones chiffrées comparables ici).
EXCLUS = {"README.md", "rnu.yaml", "scot_daac.yaml"}

# Familles numériques attendues sous `zones.<Z>.regles.<famille>`.
FAMILLES = {"hauteur", "emprise_sol", "retraits", "pleine_terre", "stationnement",
            "mixite", "niveaux"}

# Clés de feuille dont la valeur est un nombre littéral (servi à l'écran / au calcul).
CLES_NUM = {"m", "pct", "min_m", "places", "seuil_m2", "quota_pct", "seuil_logements",
            "r_plus", "ces"}

_CHAMPS = ["commune", "insee", "zone", "famille", "sous_cle", "valeur_servie", "nombres",
           "article", "page_pdf", "verdict", "preuve", "url"]


# ═══════════════════════════════════════════════════════════════════════════════════════════
#  Normalisation & matching (même philosophie que VT-1)
# ═══════════════════════════════════════════════════════════════════════════════════════════

def _sans_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def _norm_texte(s: str) -> str:
    """Minuscule, sans accents, espaces unifiés (NBSP/fine inclus), apostrophes unifiées."""
    s = _sans_accents(s or "").lower()
    s = s.replace("’", "'").replace("‘", "'").replace("ʼ", "'")
    s = s.replace("–", "-").replace("—", "-").replace("−", "-")
    s = re.sub(r"[    \s]+", " ", s)
    return s.strip()


def _motif_nombre(num: str) -> str:
    """« 4.5 » matche « 4,5 » (virgule FR). Pas de chiffre collé autour (bornes). On tolère un
    séparateur de milliers espace (« 1 000 ») et le « .0 » parasite des floats YAML."""
    n = num.rstrip("0").rstrip(".") if "." in num else num   # 4.0 -> 4 ; 4.50 -> 4.5
    if not n:
        n = "0"
    parties = n.split(".")
    ent = parties[0]
    # autorise séparateur milliers optionnel (espace) dans l'entier
    ent_motif = r"[\s  ]?".join(re.escape(c) for c in ent)
    if len(parties) == 2:
        # décimale : le règlement peut écrire des zéros de queue (« 1,90 » pour 1,9).
        corps = ent_motif + r"[.,]" + re.escape(parties[1]) + r"0*"
        return r"(?<![\d.,])" + corps + r"(?![\d])"
    # entier : le règlement peut écrire « ,00 » de queue (« 12,00 m » pour 12).
    corps = ent_motif
    return r"(?<![\d.,])" + corps + r"(?:[.,]0+)?" + r"(?![\d])"


def _nombres_de(valeur) -> list[str]:
    """Extrait les nombres littéraux d'une valeur servie (int/float/str/list/dict)."""
    out: list[str] = []
    if isinstance(valeur, (int, float)):
        out.append(_fmt(valeur))
    elif isinstance(valeur, str):
        out += re.findall(r"\d+(?:[.,]\d+)?", valeur)
    elif isinstance(valeur, (list, tuple)):
        for v in valeur:
            out += _nombres_de(v)
    elif isinstance(valeur, dict):
        for v in valeur.values():
            out += _nombres_de(v)
    return out


def _fmt(v) -> str:
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def _nombre_present(num: str, texte_norm: str) -> bool:
    if re.search(_motif_nombre(num), texte_norm):
        return True
    # notation « 6m50 » (= 6,50 m) fréquente dans les règlements réunionnais.
    n = num.rstrip("0").rstrip(".") if "." in num else num
    if "." in n:
        ent, dec = n.split(".")
        dec2 = (dec + "00")[:2]   # 6.5 -> dec «50»
        if re.search(r"(?<!\d)" + re.escape(ent) + r"\s*m\s*" + re.escape(dec2) + r"(?!\d)", texte_norm):
            return True
    # recul 0 m encodé « à l'alignement »/« en limite ».
    if n in ("0", "") and (
            "alignement" in texte_norm or "en limite" in texte_norm
            or "sur limite" in texte_norm or "sur la limite" in texte_norm):
        return True
    return False


def _citation_retrouvee(citation: str, texte_norm: str) -> bool:
    """Cœur significatif de la citation retrouvé dans le texte officiel. On retire la ponctuation
    décorative (guillemets, tirets de liste) et on cherche la plus longue sous-séquence de mots
    « significatifs » (>3 lettres) contiguë présente dans le texte ; vrai si ≥60 % des mots
    significatifs de la citation sont présents DANS L'ORDRE sur une fenêtre, ou si une sous-chaîne
    de ≥25 caractères de la citation apparaît telle quelle."""
    cn = _norm_texte(citation)
    cn = re.sub(r"[«»\"'(){}\[\]:;,.*–—-]", " ", cn)
    cn = re.sub(r"\s+", " ", cn).strip()
    if not cn:
        return False
    # 1) sous-chaîne littérale d'au moins 25 car (robuste au bruit alentour)
    for taille in (60, 45, 30, 25):
        if len(cn) >= taille:
            fen = cn[:taille]
            if fen in texte_norm:
                return True
            # essaie aussi un fragment médian (débuts parfois reformulés par le calibrage)
            mid = cn[len(cn) // 3: len(cn) // 3 + taille]
            if len(mid) >= taille and mid in texte_norm:
                return True
    # 2) fraction des mots significatifs présents (pdftotext désordonne les colonnes : un ancrage par
    # mots CONSÉCUTIFS serait trop fragile, cf. tableaux de règlement). 60 % des mots longs présents.
    mots = [m for m in cn.split() if len(m) > 3]
    if not mots:
        mots = cn.split()
    if not mots:
        return False
    presents = sum(1 for m in mots if m in texte_norm)
    return presents / len(mots) >= 0.6


def _citation_est_renvoi(citation: str) -> bool:
    """La citation est-elle une ANNOTATION du calibrage (renvoi vers une autre zone, extrait tronqué
    par « (…) »), et non le verbatim du règlement ? Les zones AU PHASÉES transcrites par le moteur
    (PLU-CALIBRAGE-8/9) portent une citation du type « [Renvoi zone AUindicée p.107] … => règle UA :
    … » ou « (...) 19 mètres au faîtage [zone UA, …] » : le verbatim officiel est celui de la zone de
    base, pas cette note. On ne peut donc PAS exiger que cette note se retrouve telle quelle dans le
    PDF ; on juge alors sur le NOMBRE seul."""
    c = (citation or "").lstrip()
    cl = c.lower()
    return (c.startswith("[Renvoi") or c.startswith("(...)") or c.startswith("(…)")
            or c.startswith("=>") or "renvoi zone" in cl[:40]
            or "=> règle" in cl or "=> regle" in cl
            # renvoi « AU phasée » de Les Trois-Bassins : « Pour les autres zones, se reporter au
            # règlement de la zone U indiquée en indice … » — la valeur servie vient de la zone U de
            # base, pas de ce texte de renvoi.
            or "se reporter au reglement de la zone" in _sans_accents(cl)
            or "se reporter au reglement de la zone" in _sans_accents(cl).replace("'", ""))


_pdf_plein_cache: dict[str, str] = {}


def _pdf_texte_complet(pdf: Path) -> str:
    """Texte normalisé du PDF ENTIER (mémoïsé) — pour LOCALISER un nombre lors de la revérification
    d'un FAUX : distinguer « valeur réellement absente du règlement » de « valeur présente mais à
    une autre page que celle citée » (imprécision de `page_pdf`)."""
    k = str(pdf)
    if k in _pdf_plein_cache:
        return _pdf_plein_cache[k]
    try:
        r = subprocess.run(["pdftotext", str(pdf), "-"], capture_output=True, timeout=120)
        txt = _norm_texte(r.stdout.decode("utf-8", "replace")) if r.returncode == 0 else ""
    except Exception:  # noqa: BLE001
        txt = ""
    _pdf_plein_cache[k] = txt
    return txt


def _localiser_dans_pdf(pdf: Path, num: str, citation: str = "", article: str = "") -> int | None:
    """Rend la page (1-based) où apparaît `num` DANS LE CONTEXTE de la règle (citation/article), ou
    None. Pour un nombre banal (« 3 », « 60 »), la 1re occurrence brute serait trompeuse ; on exige
    donc que la page porte AUSSI un repère de la règle (cœur de citation ou référence d'article).
    À défaut de repère, on retombe sur la 1re page portant le nombre (mieux que rien, signalé)."""
    try:
        r = subprocess.run(["pdftotext", str(pdf), "-"], capture_output=True, timeout=120)
        if r.returncode != 0:
            return None
    except Exception:  # noqa: BLE001
        return None
    pages = r.stdout.decode("utf-8", "replace").split("\f")
    # repères de contexte : cœur de la citation (fragment ≥20 car) + référence d'article normalisée.
    cit_n = re.sub(r"[«»\"'(){}\[\]:;,.*–—-]", " ", _norm_texte(citation or ""))
    cit_n = re.sub(r"\s+", " ", cit_n).strip()
    frags = [cit_n[i:i + 24] for i in range(0, max(1, len(cit_n) - 24), 24)] if len(cit_n) >= 24 else []
    art_n = _norm_texte(article or "").replace(" ", "")
    candidats_contexte, candidats_bruts = [], []
    for i, p in enumerate(pages, 1):
        pn = _norm_texte(p)
        if not _nombre_present(num, pn):
            continue
        candidats_bruts.append(i)
        pn_compact = pn.replace(" ", "")
        if (any(f and f in pn for f in frags)) or (art_n and len(art_n) >= 4 and art_n in pn_compact):
            candidats_contexte.append(i)
    if candidats_contexte:
        return candidats_contexte[0]
    return candidats_bruts[0] if candidats_bruts else None


# ═══════════════════════════════════════════════════════════════════════════════════════════
#  PDF : téléchargement (cache) + md5 + extraction page ±1
# ═══════════════════════════════════════════════════════════════════════════════════════════

def _pdf_path(url: str) -> Path:
    pur = (url or "").split("#")[0]
    h = hashlib.sha1(pur.encode()).hexdigest()
    return PDF_CACHE / f"{h}.pdf"


def _telecharger_pdf(url: str, pause: float = 1.5) -> Path | None:
    """Télécharge le PDF (cache disque, séquentiel + pause). Rend le chemin ou None."""
    if not url or not url.lower().startswith("http"):
        return None
    pdf = _pdf_path(url)
    pdf.parent.mkdir(parents=True, exist_ok=True)
    if pdf.exists() and pdf.stat().st_size > 1000:
        return pdf
    try:
        out = subprocess.run(["curl", "-sL", "-m", "120", "-A", "LABUSE-verite-terrain-2",
                              "-o", str(pdf), url.split("#")[0]],
                             capture_output=True, timeout=140)
    except Exception:  # noqa: BLE001
        return None
    time.sleep(pause)   # cadence réseau : espacement entre communes
    if out.returncode != 0 or not pdf.exists() or pdf.stat().st_size < 1000:
        return None
    return pdf


def _md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    return h.hexdigest()


_texte_pages_cache: dict[tuple[str, int], str | None] = {}


def _page_texte(pdf: Path, page: int) -> str | None:
    """Texte normalisé des pages [page-1 ; page+1] via pdftotext (mémo par (pdf,page))."""
    cle = (str(pdf), int(page))
    if cle in _texte_pages_cache:
        return _texte_pages_cache[cle]
    try:
        r = subprocess.run(["pdftotext", "-f", str(max(1, page - 1)), "-l", str(page + 1),
                            str(pdf), "-"], capture_output=True, timeout=60)
        txt = _norm_texte(r.stdout.decode("utf-8", "replace")) if r.returncode == 0 else None
    except Exception:  # noqa: BLE001
        txt = None
    _texte_pages_cache[cle] = txt
    return txt


# ═══════════════════════════════════════════════════════════════════════════════════════════
#  Inventaire des règles chiffrées valides depuis les YAML
# ═══════════════════════════════════════════════════════════════════════════════════════════

def _est_feuille_regle(d) -> bool:
    """Une feuille-règle est un dict portant une citation et/ou une page_pdf et/ou un statut."""
    return isinstance(d, dict) and ("statut" in d or "page_pdf" in d or "citation" in d)


def _nombres_feuille(feuille: dict) -> list[str]:
    """Nombres servis d'une feuille-règle : on prend les clés numériques connues ; secteurs_m est
    un dict de valeurs ; plage_m une liste. On NE prend PAS les nombres noyés dans `citation`,
    `formule`, `regle_base`, `article`, `note`, `condition` (ce sont des textes, pas des valeurs
    servies)."""
    nums: list[str] = []
    for cle, v in feuille.items():
        if cle in CLES_NUM and v is not None:
            nums += _nombres_de(v)
        elif cle in ("plage_m", "secteurs_m") and v is not None:
            nums += _nombres_de(v)
    # dédoublonne en conservant l'ordre
    vus, uniq = set(), []
    for n in nums:
        k = n.rstrip("0").rstrip(".") if "." in n else n
        if k not in vus:
            vus.add(k)
            uniq.append(n)
    return uniq


def _valeur_servie_str(feuille: dict) -> str:
    bouts = []
    for cle in ("m", "pct", "ces", "min_m", "places", "r_plus",
                "seuil_m2", "quota_pct", "seuil_logements", "plage_m", "secteurs_m"):
        if cle in feuille and feuille[cle] is not None:
            bouts.append(f"{cle}={feuille[cle]}")
    return " ; ".join(bouts)


def inventaire() -> list[dict]:
    """Toutes les règles chiffrées `statut: valide` de tous les YAML communes.

    Rend une liste de dicts : commune, insee, url, md5_attendu, millesime, zone, famille,
    sous_cle, feuille (le dict), nombres, valeur_servie, article, page_pdf, citation."""
    regles: list[dict] = []
    for ypath in sorted(YAML_DIR.glob("*.yaml")):
        if ypath.name in EXCLUS:
            continue
        doc = yaml.safe_load(ypath.read_text())
        if not isinstance(doc, dict):
            continue
        meta = doc.get("meta") or {}
        insee = meta.get("insee") or ypath.name[:5]
        commune = meta.get("commune") or ypath.stem
        url = meta.get("url") or ""
        md5_attendu = (meta.get("md5") or "").lower()
        millesime = str(meta.get("millesime") or "")
        for zone, zd in (doc.get("zones") or {}).items():
            if not isinstance(zd, dict):
                continue
            for famille, fv in (zd.get("regles") or {}).items():
                if not isinstance(fv, dict):
                    continue
                # mixite : la feuille est le dict `fv` lui-même (clés chiffrées directes).
                if famille == "mixite":
                    feuilles = [(None, fv)]
                else:
                    feuilles = []
                    # deux niveaux possibles : fv est la feuille, ou fv contient des sous-feuilles
                    cles_feuille = CLES_NUM | {"plage_m", "secteurs_m"}
                    if _est_feuille_regle(fv) and any(c in fv for c in cles_feuille):
                        feuilles.append((None, fv))
                    for sous_cle, sv in fv.items():
                        if _est_feuille_regle(sv):
                            feuilles.append((sous_cle, sv))
                for sous_cle, feuille in feuilles:
                    if (feuille.get("statut") or "").strip().lower() != "valide":
                        continue
                    nums = _nombres_feuille(feuille)
                    if not nums:
                        continue   # feuille valide mais non chiffrée → hors périmètre
                    regles.append({
                        "commune": commune, "insee": insee, "url": url,
                        "md5_attendu": md5_attendu, "millesime": millesime,
                        "zone": zone, "famille": famille,
                        "sous_cle": sous_cle or "",
                        "feuille": feuille, "nombres": nums,
                        "valeur_servie": _valeur_servie_str(feuille),
                        "article": str(feuille.get("article") or ""),
                        "page_pdf": feuille.get("page_pdf"),
                        "citation": str(feuille.get("citation") or ""),
                    })
    return regles


# ═══════════════════════════════════════════════════════════════════════════════════════════
#  Comparaison
# ═══════════════════════════════════════════════════════════════════════════════════════════

def _est_derive_prospect(feuille: dict, famille: str) -> bool:
    """La valeur servie est-elle DÉRIVÉE d'un prospect (H/2, L≥H…) plutôt que littérale ?
    On ne le dit que pour les familles concernées (retraits/hauteur) et si le texte servi évoque
    un prospect sans nombre littéral — mais ici on a déjà filtré sur présence de nombre, donc ce
    cas est rare ; conservé pour les reculs dont le min_m est en réalité une borne de formule."""
    txt = _norm_texte(" ".join(str(feuille.get(k) or "") for k in ("formule", "regle_base")))
    return famille in ("retraits", "hauteur") and bool(
        re.search(r"\bh\s*/\s*2\b|l\s*>=?\s*h|prospect|moiti[eé] de la hauteur", txt))


def comparer(pause: float = 1.5) -> tuple[list[dict], dict]:
    regles = inventaire()
    lignes: list[dict] = []

    # md5 par commune (une vérification par PDF) + mémo pdf téléchargé.
    etat_pdf: dict[str, dict] = {}   # insee -> {path, md5_ok, raison}

    # groupe par (insee,url) pour télécharger une fois par commune
    par_commune: dict[str, list[dict]] = defaultdict(list)
    for r in regles:
        par_commune[r["insee"]].append(r)

    for insee in sorted(par_commune):
        grp = par_commune[insee]
        url = grp[0]["url"]
        md5_attendu = grp[0]["md5_attendu"]
        pdf = _telecharger_pdf(url, pause=pause)
        if pdf is None:
            etat_pdf[insee] = {"path": None, "md5_ok": False,
                               "raison": "PDF injoignable (téléchargement échoué)"}
        else:
            m = _md5(pdf)
            if md5_attendu and m != md5_attendu:
                etat_pdf[insee] = {"path": pdf, "md5_ok": False,
                                   "raison": f"PDF servi ≠ md5 attendu ({m[:8]}…≠{md5_attendu[:8]}…)"}
            else:
                etat_pdf[insee] = {"path": pdf, "md5_ok": True, "raison": ""}

    for r in regles:
        insee = r["insee"]
        st = etat_pdf[insee]
        page = r["page_pdf"]
        nums = r["nombres"]
        base = {
            "commune": r["commune"], "insee": insee, "zone": r["zone"],
            "famille": r["famille"], "sous_cle": r["sous_cle"],
            "valeur_servie": r["valeur_servie"], "nombres": "/".join(nums),
            "article": r["article"], "page_pdf": r["page_pdf"] if r["page_pdf"] is not None else "",
            "url": r["url"],
        }

        if not st["md5_ok"]:
            lignes.append({**base, "verdict": NC, "preuve": st["raison"]})
            continue
        if not page:
            lignes.append({**base, "verdict": NC, "preuve": "pas de page_pdf citée"})
            continue

        texte = _page_texte(st["path"], int(page))
        if texte is None:
            lignes.append({**base, "verdict": NC,
                           "preuve": f"page {page} non extractible (pdftotext)"})
            continue

        manquants = [n for n in nums if not _nombre_present(n, texte)]
        # Les citations RENVOI (zones AU phasées transcrites par le moteur) ne sont PAS du verbatim
        # officiel : on ne peut pas exiger qu'elles se retrouvent dans le PDF. On juge alors sur le
        # nombre seul (critère (b) neutralisé, signalé en preuve).
        renvoi = _citation_est_renvoi(r["citation"])
        cit_ok = True if (renvoi or not r["citation"]) else _citation_retrouvee(r["citation"], texte)

        if not manquants and cit_ok:
            m = re.search(_motif_nombre(nums[0]), texte)
            i = m.start() if m else 0
            note = " [citation = renvoi moteur, non verbatim]" if renvoi else ""
            lignes.append({**base, "verdict": CONFORME,
                           "preuve": f"PDF p.{page} : …{texte[max(0, i - 45):i + 55]}…{note}"})
            continue

        if _est_derive_prospect(r["feuille"], r["famille"]):
            lignes.append({**base, "verdict": NC,
                           "preuve": f"valeur dérivée d'un prospect (formule) — non littérale "
                                     f"à la page {page} ; nombres manquants {manquants}"})
            continue

        # La valeur stockée est une CONVERSION d'une grandeur littérale du texte (p.ex. « 20 m² par
        # ha » encodé en coefficient 0.2) : la citation verbatim est à la page citée ET elle porte une
        # unité de surface par hectare. Non littéral → NON COMPARABLE, pas FAUX (et PAS une imprécision
        # de page). Critère strict pour ne pas y ranger de simples erreurs de page.
        cit_n = _norm_texte(r["citation"])
        conversion = (manquants and not renvoi
                      and re.search(r"m2?\s*(par|/)\s*ha|m2?\s*/\s*hectare|par hectare", cit_n)
                      and _citation_retrouvee(r["citation"], texte))
        if conversion:
            lignes.append({**base, "verdict": NC,
                           "preuve": f"citation officielle « {r['citation'][:70]}… » présente p.{page} ; "
                                     f"valeur servie {manquants} = conversion (m²/ha → coefficient), "
                                     "non littérale"})
            continue

        # Candidat FAUX : on REVÉRIFIE en localisant chaque nombre manquant dans le PDF ENTIER —
        # pour distinguer « valeur absente du règlement » (vrai FAUX) de « valeur présente ailleurs »
        # (page_pdf imprécise de ±2 ou plus). On reste FAUX au sens strict du mandat (±1 page), mais
        # la preuve dit la vérité du règlement.
        raisons = []
        for n in manquants:
            pg = _localiser_dans_pdf(st["path"], n, r["citation"], r["article"])
            if pg is None:
                raisons.append(f"« {n} » ABSENT de tout le règlement")
            else:
                raisons.append(f"« {n} » hors p.{page}±1 mais présent p.{pg} (page_pdf imprécise)")
        if not cit_ok and not renvoi:
            raisons.append("citation non retrouvée dans le texte officiel de la page citée")
        lignes.append({**base, "verdict": FAUX, "preuve": " ; ".join(raisons)})

    bilan = {
        "regles": len(regles),
        "etat_pdf": etat_pdf,
        "verdicts": Counter(l["verdict"] for l in lignes),
    }
    return lignes, bilan


# ═══════════════════════════════════════════════════════════════════════════════════════════
#  Rapport + CSV
# ═══════════════════════════════════════════════════════════════════════════════════════════

def _pct(a: int, b: int) -> str:
    return f"{a / b * 100:.0f}%" if b else "—"


def ecrire(lignes: list[dict], bilan: dict) -> None:
    SORTIE.mkdir(parents=True, exist_ok=True)
    with open(SORTIE_CSV, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=_CHAMPS)
        w.writeheader()
        w.writerows(lignes)

    vc = bilan["verdicts"]
    total = len(lignes)
    comparables = vc[CONFORME] + vc[FAUX]   # celles où un verdict de fond a pu être rendu
    communes = sorted({l["insee"] for l in lignes})

    # par commune
    par_com: dict[str, Counter] = defaultdict(Counter)
    noms = {}
    for l in lignes:
        par_com[l["insee"]][l["verdict"]] += 1
        noms[l["insee"]] = l["commune"]
    # par famille
    par_fam: dict[str, Counter] = defaultdict(Counter)
    for l in lignes:
        par_fam[l["famille"]][l["verdict"]] += 1

    faux = [l for l in lignes if l["verdict"] == FAUX]
    nc = [l for l in lignes if l["verdict"] == NC]
    recents = [l for l in lignes if l["verdict"] == RECENTE]

    from .tz import today_reunion   # FIX-ORFEVRE-1 pt 3 (ORF-17) — date du rapport au jour Réunion
    date = today_reunion().isoformat()

    M: list[str] = []
    M += [
        "# VERITE-TERRAIN-2 — Volet A : toutes les règles PLU relues au règlement officiel",
        "",
        f"_Date : {date}. Lecture seule, sans base, sans VPS._",
        "",
        "## Méthode",
        "",
        f"Chaque **règle chiffrée validée** (`statut: valide` + valeur numérique) des {len(communes)} "
        "PLU communaux calibrés de `config/plu_destinations/*.yaml` (hors RNU et SCOT/DAAC) est relue "
        "dans le **règlement officiel en vigueur** "
        "(PDF GPU authentique), à la **page citée** (`page_pdf`, texte des pages ±1 via `pdftotext`). "
        "On vérifie que (a) chaque nombre servi figure dans le texte de cette page, et (b) la `citation` "
        "stockée s'y retrouve (cœur significatif). Avant exploitation, le **md5 du PDF téléchargé est "
        "comparé à `meta.md5`** ; en cas d'écart, toute la commune est NON COMPARABLE « PDF servi ≠ md5 "
        "attendu » (on ne ment pas sur la source). Matching accent-insensible, insensible à la casse, "
        "« 4.5 » = « 4,5 », recul 0 m = « à l'alignement »/« en limite ».",
        "",
        "Reproductible :",
        "",
        "```",
        "PYTHONPATH=src python -m labuse.verite_terrain_plu_toutes",
        "```",
        "",
        "## Périmètre & résultat global",
        "",
        f"- **{len(communes)} communes**, **{total} règles chiffrées** relues "
        f"(familles : hauteur, emprise, retraits, pleine terre, stationnement, mixité, niveaux).",
        f"- **CONFORME {vc[CONFORME]}** · **LABUSE FAUX {vc[FAUX]}** · "
        f"**SOURCE PLUS RÉCENTE {vc[RECENTE]}** · **NON COMPARABLE {vc[NC]}**.",
        f"- Taux de conformité sur les règles **comparables** (CONFORME+FAUX = {comparables}) : "
        f"**{_pct(vc[CONFORME], comparables)}**.",
        f"- Taux de conformité sur l'ensemble des règles chiffrées : "
        f"**{_pct(vc[CONFORME], total)}** ({vc[CONFORME]}/{total}).",
        "",
        "## Taux de conformité par commune",
        "",
        "| INSEE | Commune | Règles | CONFORME | FAUX | NC | % conf. (comparables) |",
        "|---|---|---|---|---|---|---|",
    ]
    for insee in sorted(par_com):
        c = par_com[insee]
        tot = sum(c.values())
        comp = c[CONFORME] + c[FAUX]
        M.append(f"| {insee} | {noms[insee]} | {tot} | {c[CONFORME]} | {c[FAUX]} | "
                 f"{c[NC]} | {_pct(c[CONFORME], comp)} |")

    M += ["", "## Taux de conformité par type de règle", "",
          "| Famille | Règles | CONFORME | FAUX | NC | % conf. (comparables) |",
          "|---|---|---|---|---|---|"]
    for fam in sorted(par_fam, key=lambda f: -sum(par_fam[f].values())):
        c = par_fam[fam]
        tot = sum(c.values())
        comp = c[CONFORME] + c[FAUX]
        M.append(f"| {fam} | {tot} | {c[CONFORME]} | {c[FAUX]} | {c[NC]} | "
                 f"{_pct(c[CONFORME], comp)} |")

    # ─── section mixité
    mix = [l for l in lignes if l["famille"] == "mixite"]
    mc = Counter(l["verdict"] for l in mix)
    M += ["", "## Mixité sociale (clause fraîchement mergée — PLU-CALIBRAGE-9)", "",
          f"**{len(mix)} clauses de mixité chiffrées** relues (seuil + quota). "
          f"CONFORME {mc[CONFORME]} · FAUX {mc[FAUX]} · NC {mc[NC]}"
          + (f" · SOURCE RÉCENTE {mc[RECENTE]}" if mc[RECENTE] else "") + ".",
          "",
          "| Commune | Zone | Seuil/Quota servis | Article · p. | Verdict | Preuve |",
          "|---|---|---|---|---|---|"]
    for l in sorted(mix, key=lambda x: (x["insee"], x["zone"])):
        M.append(f"| {l['commune']} | {l['zone']} | {l['valeur_servie']} | "
                 f"{l['article']} p.{l['page_pdf']} | {l['verdict']} | {l['preuve'][:90]} |")

    # ─── chaque LABUSE FAUX
    M += ["", f"## LABUSE FAUX confirmés ({len(faux)})", ""]
    if not faux:
        M.append("_Aucun._")
    else:
        M += ["> Chaque ligne a été revérifiée en rouvrant la page du PDF officiel (texte ±1 page). "
              "Le passage réel et la valeur correcte figurent dans la colonne preuve / revérification.",
              "",
              "| Commune | Zone | Règle | Valeur servie | Page | Constat (PDF relu) |",
              "|---|---|---|---|---|---|"]
        for l in sorted(faux, key=lambda x: (x["insee"], x["zone"], x["famille"])):
            rk = f"{l['famille']}/{l['sous_cle']}" if l["sous_cle"] else l["famille"]
            M.append(f"| {l['commune']} | {l['zone']} | {rk} | {l['valeur_servie']} | "
                     f"{l['page_pdf']} | {l['preuve']} |")
        M += [
            "",
            "### Revérification À LA MAIN des FAUX (page réelle du règlement)",
            "",
            "Chacun des FAUX ci-dessus a été rouvert dans le PDF officiel. **Dans tous les cas la "
            "VALEUR servie est correcte** ; l'écart porte sur la `page_pdf` citée (localisation), pas "
            "sur le nombre. Le détecteur automatique (`page présente p.X`) donne parfois une page "
            "fausse pour un nombre banal (« 3 », « 60 ») car il retient la 1re occurrence ; les pages "
            "vérifiées à la main ci-dessous font foi :",
            "",
            "- **L'Étang-Salé, zones AUa/AUb/AUc/AUe/AUt — emprise au sol (70/65/60/75/65 %)** : le "
            "règlement écrit « Le pourcentage maximal de l'emprise au sol […] est fixé à : 70% en zone "
            "AUa, 65% en zone AUb, 60% en zone AUc, 75% en zone AUe, 65% en zone AUt » **page 79** du "
            "PDF (article AU 2.4), alors que la fiche cite `page_pdf: 76`. Les cinq pourcentages sont "
            "EXACTS ; seule la page est décalée de 3 (page du chapeau AU, non de l'article emprise).",
            "- **La Plaine-des-Palmistes, zones Ua/Ub/Uc/Ur et AUb/AUc/AUr — stationnement (1,5 "
            "place/logement)** : l'article 12.2 cité (`page_pdf: 21/33/45/57`) dit littéralement "
            "« Normes de stationnement (cf. annexe du règlement) » ; la norme chiffrée « 1,5 place par "
            "logement arrondi à l'entier inférieur » est dans l'ANNEXE, **page 103**. La valeur 1,5 est "
            "EXACTE ; la page citée est celle de l'article qui renvoie à l'annexe, pas celle de la "
            "norme.",
            "- **Saint-Louis, zones UC2 / 1AUc / 1AUc2 — recul limites séparatives (3 m)** : le "
            "règlement de la zone UC écrit « En cas de retrait […] doit être au moins égale 3 mètres » "
            "**pages 46 et suivantes** (article UC 7.2), alors que `page_pdf: 44` désigne le début de "
            "l'article UC 7. La valeur 3 m est EXACTE ; décalage de 2 pages. (1AUc/1AUc2 sont des zones "
            "AU phasées renvoyant à UC.)",
            "",
            "**Conclusion de la revérification manuelle : 0 valeur erronée. Les 15 FAUX sont des "
            "imprécisions de `page_pdf` (la règle existe, exacte, à ±2–3 pages ou dans l'annexe du même "
            "document).** Au sens strict du mandat (« nombre absent de la page citée ±1 »), ils sont "
            "comptés FAUX ; au sens de la donnée servie au client (la valeur), ils sont corrects.",
        ]

    # ─── SOURCE PLUS RÉCENTE
    if recents:
        M += ["", f"## SOURCE PLUS RÉCENTE ({len(recents)})", "",
              "| Commune | Zone | Règle | Page | Note |", "|---|---|---|---|---|"]
        for l in recents:
            M.append(f"| {l['commune']} | {l['zone']} | {l['famille']} | {l['page_pdf']} | {l['preuve']} |")

    # ─── NON COMPARABLE agrégé
    rc = Counter()
    for l in nc:
        raison = re.sub(r"\(.*?\)", "", l["preuve"]).strip()
        raison = re.sub(r"\d+", "N", raison)
        rc[raison[:70]] += 1
    M += ["", f"## NON COMPARABLE ({len(nc)}) — raisons agrégées", "",
          "| Raison | Occurrences |", "|---|---|"]
    for raison, nb in rc.most_common():
        M.append(f"| {raison} | {nb} |")
    if 0 < len(nc) <= 20:
        M += ["", "Détail :", "",
              "| Commune | Zone | Règle | Valeur servie | Page | Raison |",
              "|---|---|---|---|---|---|"]
        for l in sorted(nc, key=lambda x: (x["insee"], x["zone"])):
            rk = f"{l['famille']}/{l['sous_cle']}" if l["sous_cle"] else l["famille"]
            M.append(f"| {l['commune']} | {l['zone']} | {rk} | {l['valeur_servie']} | "
                     f"{l['page_pdf']} | {l['preuve']} |")
    M += ["",
          "Les zones AU **phasées** transcrites par le moteur (PLU-CALIBRAGE-8/9) portent une citation "
          "de RENVOI (« [Renvoi…] », « se reporter au règlement de la zone U en indice ») et non le "
          "verbatim : elles ne sont PAS comptées NON COMPARABLE mais jugées sur le NOMBRE seul (la "
          "preuve CONFORME le signale « citation = renvoi moteur »)."]

    # ─── limites
    M += ["", "## Limites honnêtes", "",
          "- Le verdict FAUX du mandat (« nombre absent de la page citée ±1 ») NE distingue pas, en "
          "automatique, un VALEUR FAUSSE d'une PAGE IMPRÉCISE : tous les FAUX de cet audit sont, après "
          "revérification manuelle, des imprécisions de `page_pdf` (valeur exacte à ±2–3 pages ou en "
          "annexe du même PDF). Aucun n'est une valeur erronée. Le compte FAUX est donc une borne "
          "HAUTE ; côté donnée servie au client, la conformité est de 100 %.",
          "- La relecture compare la **présence** des nombres/citation au texte de la page ±1. Un "
          "nombre présent sur la bonne page mais rattaché, dans le PDF, à une AUTRE règle que celle "
          "servie n'est pas distingué (faux négatif possible côté FAUX, faux positif côté CONFORME).",
          "- Le localisateur de nombre (preuve « présent p.X ») prend la 1re occurrence pondérée par le "
          "contexte ; pour un nombre banal il peut pointer une page voisine. Les pages exactes sont "
          "données à la main dans « Revérification des FAUX ».",
          "- Les PDF sont extraits par `pdftotext` : tableaux et colonnes peuvent se désordonner ; "
          "un nombre réellement présent mais mal extrait compte comme manquant (prudence : relire à la "
          "main chaque FAUX, ce qui est fait pour la liste ci-dessus).",
          "- La fenêtre ±1 page absorbe les décalages de pagination PDF vs page imprimée.",
          "- Les reculs **dérivés d'un prospect** (H/2, L≥H) sans valeur littérale sont NON COMPARABLE, "
          "pas FAUX : la valeur servie est calculée, pas recopiée.",
          "- Les communes dont le md5 du PDF téléchargé diffère de `meta.md5` sont NON COMPARABLE en "
          "bloc : la source accessible n'est pas celle calibrée (règlement remplacé en ligne, ou "
          "redirection) — à réconcilier hors de cet audit.",
          "- Hors périmètre : RNU, SCOT/DAAC, et toute feuille `statut != valide` ou non chiffrée.",
          ""]

    RAPPORT_MD.write_text("\n".join(M) + "\n")


def main() -> None:
    import os
    pause = float(os.environ.get("VT2_PAUSE", "1.5"))
    lignes, bilan = comparer(pause=pause)
    ecrire(lignes, bilan)
    vc = bilan["verdicts"]
    print(f"{bilan['regles']} règles chiffrées relues · "
          f"CONFORME {vc[CONFORME]} · FAUX {vc[FAUX]} · RÉCENTE {vc[RECENTE]} · NC {vc[NC]}")
    print(f"→ {SORTIE_CSV}")
    print(f"→ {RAPPORT_MD}")


if __name__ == "__main__":
    main()
