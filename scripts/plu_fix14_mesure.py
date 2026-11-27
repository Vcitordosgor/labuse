"""OUTIL-PLU-FIX-14 (LOT 1) — MESURE : passe TOUS les libellés de zonage graphique des 21 communes
servies sur « hauteur », « implantation », « stationnement » et classe chaque recherche avec les lettres
d'Astra (rapport 01-PLU-ASTRA-4) :

  J — article applicable retrouvé, zone/secteur identifié dans le texte (carte PROPRE à la zone)
  R — renvoi EXPRÈS correct (chapitre « AU indicée », renvoi configuré/texte vers une autre zone)
  F — renvoi ANNONCÉ FAUX : le bandeau (renvoi_note) annonce une provenance que les cartes contredisent
  X — règle d'une AUTRE zone présentée sous le filtre (carte d'un chapitre étranger)
  A — règle absente de l'extrait (recherche vide, ou cartes « titres seuls »)
  T — texte commun ou de zone mère servi pour cette recherche
  C — chapitre servi en bloc, article demandé non isolé
  D — absence d’article documentée dans le chapitre vérifié, avec lien à la page du PDF en vigueur
  I — rattachement du libellé graphique au règlement écrit impossible à certifier

Source des libellés : `parcel_zone_plu.zone_lib` (le zonage graphique, pas nos YAML). Appelle la ROUTE
réelle `plu_annuaire_search`. La provenance de CHAQUE carte est lue dans le champ `cas` (OUTIL-PLU-FIX-14
LOT 2/3) quand il existe ; sinon recalculée ici (même logique) pour pouvoir mesurer AVANT la correction.

Déterministe, rejouable à l'identique (avant/après). Usage :
  LABUSE_PLU_CORPUS_DSN=... PYTHONPATH=src python scripts/plu_fix14_mesure.py [--insee 97412] [--csv out]
"""
from __future__ import annotations

import argparse
import re
import os
import sys
from collections import Counter, OrderedDict

sys.path.insert(0, "src")
from sqlalchemy import create_engine, text          # noqa: E402
from sqlalchemy.orm import sessionmaker             # noqa: E402

from labuse.api import modules as M                 # noqa: E402
from labuse.ingestion import plu_ingest as P        # noqa: E402

DSN = os.environ.get("LABUSE_PLU_CORPUS_DSN", "postgresql+psycopg://openclaw@localhost:5432/labuse")
THEMES = ["hauteur", "implantation", "stationnement"]
_BLOC_CHAPITRE = 6          # une carte couvrant ≥ 6 pages = chapitre en bloc (non isolé)


def _labels(s, insee: str) -> list[str]:
    return [z for z in s.execute(text(
        "SELECT DISTINCT zone_lib FROM parcel_zone_plu WHERE idu LIKE :p AND zone_lib IS NOT NULL "
        "ORDER BY zone_lib"), {"p": f"{insee}%"}).scalars().all() if z and z.strip()]


def _card_zone(card: dict) -> str:
    """Zone EFFECTIVE de la carte : le code lu dans l'en-tête d'article via le MÊME analyseur que
    l'ingestion (`_ZONE_FROM_ART` : « ARTICLE U3 10 » → U3, « Article U8 - » → U, « ARTICLE Ucv3 » → UCV),
    sinon l'étiquette `zone` (Saint-Paul « Article 6- » → bannière)."""
    m = P._ZONE_FROM_ART.match((card.get("article_ref") or "").strip())
    ref_z = P._valid_zone(m.group(1)) if m else None
    return (ref_z or (card.get("zone") or "")).upper()


# Témoins indépendants de l’index. Pages physiques, bornes incluses, dans les
# deux éditions contrôlées. Les chapitres étrangers peuvent aussi se retrouver
# dans la rubrique commune, ou à la fin d’un article qui déborde.
def _hors_chapitre_pdf(card: dict, label: str) -> bool:
    doc = card.get("document")
    label = label.strip().upper()
    if doc == "97405_reglement_20230609.pdf":
        if label in {"1AU", "1AUA"}:
            debut, fin = 88, 98
        elif label == "1AUZ":
            debut, fin = 99, 108
        else:
            return False
        if (card.get("page_debut") or 0) >= 163:
            # Les articles 1AU.11 et 1AUZ.11 citent le croquis commun p. 166.
            # Seule l’annexe 4 p. 167 représente expressément UEa.6.
            return card["page_debut"] == 167
        premier_chapitre = 23
    elif doc == "97418_reglement_20251126.pdf":
        if label in {"UA", "UAB", "UAZ", "UB", "UC", "UC1", "UC2", "UD", "UD1"}:
            debut, fin = 16, 28
        elif label in {"UEA", "UEC", "UEM", "UEP", "UR", "UT", "UTP"}:
            debut, fin = 29, 40
        else:
            return False
        premier_chapitre = 16
    else:
        return False
    a, b = card.get("page_debut"), card.get("page_fin")
    if not a or not b or b < premier_chapitre:
        return False
    return a < debut or b > fin


def _provenance(card: dict, label: str, insee: str, s) -> str:
    """Un des 5 cas de provenance d'une carte. Lit `cas` si la route le fournit, sinon le recalcule."""
    if card.get("cas"):
        return card["cas"]
    czone = _card_zone(card)
    label_up = P._norm(label).upper()
    cands = {c.upper() for c in P.zone_candidats(label)}
    scope = P._secteurs_regis(card)
    if czone == "AUINDICEE":
        return "renvoi_expres"
    if czone == label_up:
        return "propre"
    if any(label_up == e or label_up.startswith(e) for e in scope):
        return "propre"                                    # l'article régit la zone (ou un sur-secteur)
    if czone and czone != label_up and label_up.startswith(czone) and czone in cands:
        return "zone_mere"
    if czone in cands and czone != label_up:
        return "zone_mere"
    try:
        cible = P._renvoi_cible(label, insee, s)
    except Exception:  # noqa: BLE001
        cible = None
    if cible and czone in {c.upper() for c in P.zone_candidats(cible)}:
        return "renvoi_expres"
    # zone AU servie par la U de même indice (renvoi générique « de même indice »)
    ueq = P._zone_u_equivalente(label)
    if ueq and czone in {c.upper() for c in P.zone_candidats(ueq)}:
        return "renvoi_expres"
    # phasage du plan de zonage : 1AUto → chapitre AUto (préfixe de phase retiré)
    strip = P._sans_prefixe_chiffre(label)
    if strip and czone in {c.upper() for c in P.zone_candidats(strip)}:
        return "renvoi_expres"
    return "foreign"


def _is_title_only(card: dict) -> bool:
    """Carte « titre seul » : le corps n'est qu'un en-tête, sans la règle qui suit."""
    tv = (card.get("texte_verbatim") or "").strip()
    net = len("".join(tv.split()))
    # Une réponse expresse très courte reste une disposition complète (AUst 10 p. 84).
    return net < 60 and not re.search(r"(?:^|\n)\s*(?:Sans objet|Non réglementé)[.]?\s*$", tv, re.I)


def _is_chapter_block(card: dict) -> bool:
    """Carte = chapitre servi EN BLOC, article demandé NON isolé. Signatures : (a) l'en-tête n'est pas un
    article (« ZONE/CHAPITRE… », ou fragment de titre « ET PAYSAGERES ») et le texte s'étend sur plusieurs
    pages ; (b) le texte contient PLUSIEURS numéros d'article distincts (deux articles fondus)."""
    span = (card.get("page_fin") or 0) - (card.get("page_debut") or 0)
    tv = card.get("texte_verbatim") or ""
    ref = (card.get("article_ref") or "")
    if ref.upper().startswith(("ZONE", "CHAPITRE", "TITRE", "SECTION")):
        return True
    if card.get("document") == "97407_reglement_20241209.pdf" and re.fullmatch(
            r"Article 1AUindicée \d+", ref, re.I):
        # Dans cette édition chaque en-tête imprimé a un code, un numéro et un
        # tiret. L’article 12 contient à lui seul quatre pages de barèmes.
        titres = re.findall(r"(?im)^[ \t]*(Article[ \t]+\w+[ \t]+\d+)[ \t]*[-–—]", tv)
        return [" ".join(t.split()).casefold() for t in titres] != [ref.casefold()]
    nums = {n for n in (P._art_num(m.group(0)) for m in P._HEADER.finditer(tv)) if n}
    if len(nums) >= 2:
        return True
    if P._art_num(ref) is None and span >= 3:     # bloc fusionné sans en-tête d'article (ET PAYSAGERES)
        return True
    return False


import re as _re
# zone de DESTINATION explicitement annoncée par un bandeau de RENVOI (« renvoie au règlement de la zone
# Umut de même indice », « le règlement renvoie à Uc »). Le bandeau « articles du chapitre « 1AU » » ne
# cite PAS de zone de destination étrangère : il décrit le chapitre servi (pas un renvoi → pas de F).
_ANNONCE_RENVOI = _re.compile(r"(?i)renvoie\s+(?:au\s+r[èe]glement\s+de\s+la\s+zone|à)\s+([0-9A-Za-z]+)")


def _absence_evaluee(carte, insee, label, theme):
    """Oracle des deux éditions relues. Une carte vide, générique ou mal paginée reste A."""
    secteur = label.upper()
    if insee == "97408" and secteur == "UP" and theme == "hauteur":
        url = "https://data.geopf.fr/annexes/gpu/documents/DU_97408/77244f114938a3230afb98948d9498bc/97408_reglement_20260625.pdf"
        ok = (carte.get("nature") == "rattachement_incertain" and "rattachement non établi" in carte.get("texte", "")
              and carte.get("page_debut") == carte.get("page_fin") == 7 and carte.get("url") == url + "#page=7")
        return "I" if ok else "A"
    if insee != "97410" or theme != "stationnement":
        return "A"
    match = re.fullmatch(r"(NS|NTA)(\d+)", secteur)
    if match:
        numero = int(match[2])
        if not ((match[1] == "NS" and 20 <= numero <= 46) or (match[1] == "NTA" and 47 <= numero <= 54)):
            return "A"
    elif secteur not in {"A", "ACOR", "ACU", "AI", "N", "NCI", "NERL", "NP", "NPNR"}:
        return "A"
    url = "https://data.geopf.fr/annexes/gpu/documents/DU_97410/77260522306e0350ed054b54d35a35fa/97410_reglement_20200206.pdf"
    debut, fin = (32, 39) if secteur.startswith("A") else (40, 48)
    if (carte.get("nature") != "absence_documentee" or "nombre de places" not in carte.get("texte", "")
            or (carte.get("page_debut"), carte.get("page_fin"), carte.get("url")) != (debut, fin, f"{url}#page={debut}")):
        return "A"
    if match:
        # Premier et dernier secteurs imprimés sur chaque fiche annexe, pages 74 à 87.
        bornes = [(21, 74), (22, 75), (25, 76), (34, 77), (36, 78), (40, 79), (41, 80), (46, 81),
                  (47, 82), (48, 83), (52, 84), (53, 86), (54, 87)]
        page = next(p for fin_secteur, p in bornes if numero <= fin_secteur)
        complement = carte.get("complement") or {}
        if not complement.get("texte") or complement.get("url") != f"{url}#page={page}" or complement.get("page") != page:
            return "A"
    return "D"


def classify(s, insee: str, label: str, theme: str) -> str:
    r = M.plu_annuaire_search(q=theme, insee=insee, zone=label, limit=25, offset=0, db=s)
    res = r.get("resultats") or []
    dc = r.get("dispositions_communes") or []
    note = r.get("renvoi_note")
    cats = [_provenance(c, label, insee, s) for c in res]
    # X — règle étrangère sous le filtre (prime sur tout, comme Astra)
    if any(_hors_chapitre_pdf(c, label) for c in [*res, *dc]) or "foreign" in cats:
        return "X"
    # F — le bandeau ANNONCE un renvoi vers une zone X que les cartes servies ne portent PAS (Le Port
    # annonçait « renvoie à Umut » en servant des articles 1AU). On ne retient F que pour une annonce
    # EXPLICITE de zone de destination, pas pour un bandeau qui décrit le chapitre réellement servi.
    m = _ANNONCE_RENVOI.search(note or "")
    if m and res:
        ann = m.group(1).upper()
        ann_fam = {c.upper() for c in P.zone_candidats(ann)}
        if not any(_card_zone(c) == ann or _card_zone(c) in ann_fam or _card_zone(c).startswith(ann)
                   for c in res):
            return "F"
    # A — rien de servi, ou titres seuls (ni carte zonée ni disposition commune portant la règle)
    if not res and not dc:
        return _absence_evaluee(r.get("absence_article") or {}, insee, label, theme)
    if res and all(_is_title_only(c) for c in res):
        return "A"
    # C — chapitre servi en bloc
    if any(_is_chapter_block(c) for c in res):
        return "C"
    # Une réserve de rattachement sur chaque carte zonée ne peut devenir une
    # règle de la zone mère par simple ressemblance de libellé.
    cartes = res or dc
    if cartes and all(c.get("mention_rattachement") == "rattachement non établi dans le règlement écrit, à vérifier"
                      for c in cartes):
        return "I"
    # J / R / T / I
    if "propre" in cats:
        return "J"
    if "renvoi_expres" in cats:
        return "R"
    if "zone_mere" in cats or dc:
        return "T"
    return "I"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--insee", default=None)
    ap.add_argument("--csv", default=None)
    args = ap.parse_args()
    s = sessionmaker(bind=create_engine(DSN))()
    communes = s.execute(text("SELECT DISTINCT insee, commune FROM plu_reglement_extrait ORDER BY insee")).all()
    grand = Counter()
    lignes = []
    print(f"{'INSEE':6} {'commune':22} " + " ".join(f"{l:>3}" for l in "JRFXATCID") + "  total")
    for insee, commune in communes:
        if args.insee and insee != args.insee:
            continue
        per = Counter()
        for label in _labels(s, insee):
            for theme in THEMES:
                try:
                    lt = classify(s, insee, label, theme)
                except Exception as e:  # noqa: BLE001
                    lt = "A"
                    print(f"   !! {insee} {label} {theme}: {e}", file=sys.stderr)
                per[lt] += 1
                grand[lt] += 1
                lignes.append((insee, commune, label, theme, lt))
        tot = sum(per.values())
        print(f"{insee:6} {commune[:22]:22} " + " ".join(f"{per.get(l,0):>3}" for l in "JRFXATCID") + f"  {tot}")
    print("-" * 60)
    print(f"{'TOTAL':29} " + " ".join(f"{grand.get(l,0):>3}" for l in "JRFXATCID") + f"  {sum(grand.values())}")
    if args.csv:
        with open(args.csv, "w") as f:
            f.write("insee,commune,label,theme,lettre\n")
            for row in lignes:
                f.write(",".join(str(x) for x in row) + "\n")
        print(f"\nCSV → {args.csv} ({len(lignes)} lignes)")
    s.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
