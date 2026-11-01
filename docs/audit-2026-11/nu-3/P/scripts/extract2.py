#!/usr/bin/env python3
"""LOT P — extraction v2 : regex serrées, concepts séparés, docs décrivant LA parcelle.
Produit matrices propres + ecarts vérifiables. Lecture seule."""
import re, subprocess, pathlib, csv, collections, itertools

OUT = pathlib.Path("/Users/openclaw/Desktop/labuse-nu3-p/docs/audit-2026-11/nu-3/P/out")
PDFDIR = OUT / "pdf"
(OUT / "docs").mkdir(exist_ok=True)
PARC = {r["idu"]: r for r in csv.DictReader(open(OUT / "parcelles.csv"))}

# docs décrivant LA parcelle (comparaison stricte) ; les 3 autres (zone/multi) sont lus à part
CORE = ["dossier", "export-fiche", "apporteur", "pre-dossier", "gabarit", "estimer", "flash", "financier"]
CTX = ["etude-zone", "comparatif", "etude-faisabilite"]  # agrégats : lus, pas comparés strictement

def doc_of(stem):
    idu, rest = stem.split("__", 1)
    if rest.startswith("predossier_"):
        return idu, "pre-dossier"
    return idu, rest

def text_of(pdf):
    try:
        return subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True, timeout=60).stdout
    except Exception:
        return ""

def n(s):  # normalise un nombre : retire espaces (insécables inclus)
    return re.sub(r"[\s ]", "", s) if s else s

def first(txt, pat, flags=0, grp=1):
    m = re.search(pat, txt, flags)
    return m.group(grp) if m else None

PLU = r"(?:RNU|AU[a-zA-Z0-9]{0,3}|[UAN][a-zA-Z]?\d?[a-zA-Z]?)"

def extract(txt, doc):
    T = txt.replace(" ", " ").replace(" ", " ")
    f = {}
    # contenance / surface terrain
    v = (first(T, r"(\d[\d ]{1,8})\s*m²\s*\n?\s*SURFACE\b")
         or first(T, r"contenance cadastrale\)?\s*\n?\s*(\d[\d ]{1,8})\s*m²", re.I)
         or first(T, r"Surface(?: du terrain)?\s+(\d[\d ]{2,8})\s*m²")
         or first(T, r"(\d[\d ]{2,8})\s*m²\s*\n\s*contenance"))
    if v: f["contenance_m2"] = n(v)
    # zone PLU (tuile / libellé). On vise le CODE COMPLET (UC, Ud3…), pas la famille « U » de flash.
    cands = re.findall(r"\n\s*(" + PLU + r")\s*\n\s*ZON(?:E|AGE)", T)
    cands += re.findall(r"Zon(?:e|age)(?:\s+PLU)?\s*[:]?\s*(" + PLU + r")\b", T)
    cands += re.findall(r"·\s*Zone\s+(" + PLU + r")\b", T)
    cands += re.findall(r"R[ÈE]GLES DE LA ZONE\s+(" + PLU + r")\b", T)
    cands += re.findall(r"zone\s+(" + PLU + r")\)", T)  # flash « (zone UC) »
    # garder le code le plus spécifique (le plus long) trouvé ; ignore la famille seule si un code existe
    cands = [c for c in cands if c not in ("RNU",)]
    if cands:
        best = max(cands, key=len)
        f["zone"] = best
    if re.search(r"\bRNU\b|r[èe]glement national d.urbanisme", T, re.I): f["zone_rnu"] = "oui"
    # SDP restante/résiduelle : valeur
    v = (first(T, r"SDP\s+(?:restante|r[ée]siduelle)[^\n]{0,40}?(\d[\d ]{1,7})\s*m²", re.I)
         or first(T, r"(\d[\d ]{1,7})\s*m²\s*\n\s*SDP RESTANTE", re.I)
         or first(T, r"sdp r[ée]siduelle[^\n]{0,30}?(\d[\d ]{1,7})\s*m²", re.I)
         or first(T, r"Au sol \(SDP[^\)]*\)\s+(\d[\d ]{1,7})\s*m²", re.I))
    if v: f["sdp_restante_m2"] = n(v)
    # libellé SDP employé
    labs = set()
    if re.search(r"SDP\s+restante", T, re.I): labs.add("restante")
    if re.search(r"SDP\s+r[ée]siduelle|sdp r[ée]siduelle", T, re.I): labs.add("résiduelle")
    if labs: f["sdp_libelle"] = "+".join(sorted(labs))
    # emprise bâti au sol
    v = (first(T, r"(\d[\d ]{1,6})\s*m²\s*au sol")
         or first(T, r"[Bb]âti existant,?\s*emprise\s+(\d[\d ]{1,6})\s*m²")
         or first(T, r"emprise(?: bâtie)?\s*\n?\s*(\d[\d ]{1,6})\s*m²", re.I))
    if v: f["emprise_bati_m2"] = n(v)
    # hauteurs (concepts séparés)
    v = first(T, r"[Hh]auteur (?:maximale|au fa[îi]tage|r[ée]glementaire)[^\n]{0,40}?(\d{1,2})[.,]?(\d)?\s*m\b")
    if v: f["hauteur_faitage_m"] = v
    v = first(T, r"[Hh]auteur d.?.?gout[^\n]{0,30}?(\d{1,2})\s*m\b")
    if v: f["hauteur_egout_m"] = v
    v = first(T, r"[Hh]auteur mesur[ée]e[^\n]{0,30}?(\d{1,2}[.,]\d)\s*m")
    if v: f["hauteur_bati_m"] = v.replace(",", ".")
    # aléas / vigilances : nombre + libellé de tuile. On exclut « 03 Risques » (numéro de section du Flash :
    # zéro en tête) et on n'accepte « risque » que précédé d'un vrai compteur sans zéro.
    m = re.search(r"\b([1-9]\d?)\s+(vigilances?|al[ée]as?)\b", T, re.I)
    if m: f["aleas_count"] = m.group(1); f["aleas_mot"] = m.group(2).lower().rstrip("s").replace("é", "e")
    m2 = re.search(r"\b([1-9]\d?)\s*\n\s*(RISQUES|VIGILANCES)", T)
    if m2 and "aleas_count" not in f: f["aleas_count"] = m2.group(1); f["aleas_mot"] = m2.group(2).lower().rstrip("s")
    # dernière vente
    v = first(T, r"[Dd]erni[èe]re vente[^\n]{0,60}?(\d[\d ]{4,9})\s*€")
    if not v:
        v = first(T, r"(\d[\d ]{4,9})\s*€\s*\n\s*DERNI[ÈE]RE VENTE", re.I)
    if v: f["derniere_vente_eur"] = n(v)
    v = (first(T, r"[Dd]erni[èe]re vente\s+(\w+ 20\d{2})")
         or first(T, r"(\d{2}/20\d{2})\s*·?\s*\n?\s*\d[\d ]{3,}\s*€\s*\n\s*DERNI[ÈE]RE", re.I))
    if v: f["derniere_vente_date"] = v.strip()
    # prix médian maison (€/m²)
    v = (first(T, r"[Pp]rix ancien m[ée]dian\s+(\d[\d ]{2,6})\s*€/m²[^\n]{0,20}maison", re.I)
         or first(T, r"(\d[\d ]{2,6})\s*€/m²\s*de\s*\d[\d ]*\s*à", re.I))
    if v: f["prix_median_maison_m2"] = n(v)
    # taxe d'aménagement
    v = first(T, r"[Tt]axe d.am[ée]nagement[^\n€]{0,60}?(\d[\d ]{2,8})\s*€")
    if v: f["taxe_amenagement_eur"] = n(v)
    # propriétaire (champ propriétaire de la parcelle, pas les entreprises de la zone)
    if re.search(r"propri[ée]taire[^\n]{0,30}non d[ée]termin", T, re.I): f["proprietaire"] = "non déterminé"
    v = first(T, r"(?:D[ée]nomination|Propri[ée]taire(?: moral)?|Type de propri[ée]taire)[^\n]{0,40}?\b((?:SCI|SARL|SAS|SASU|SA|EURL)\s+[A-ZÀ-Ü][\w' À-Ü-]{2,40})")
    if v: f["proprietaire"] = re.sub(r"\s+", " ", v).strip()
    # dates / millésime
    v = first(T, r"Donn[ée]es LABUSE au\s+(\d{2}/\d{2}/\d{4})");
    if v: f["date_donnees"] = v
    v = first(T, r"g[ée]n[ée]r[ée]\s+le\s*\n?\s*(\d{2}/\d{2}/\d{4})", re.I)
    if v: f["date_genere"] = v
    v = first(T, r"\b([A-Z]{2,3}-\d{8}-\d{3,4})\b")
    if v: f["ref_rapport"] = v
    return f

# collecte
per = collections.defaultdict(lambda: collections.defaultdict(dict))
for pdf in sorted(PDFDIR.glob("*.pdf")):
    idu, doc = doc_of(pdf.stem)
    ff = extract(text_of(pdf), doc)
    if doc == "pre-dossier":
        for k, v in ff.items():
            per[idu][doc].setdefault(k, v)  # première pièce qui porte le fait
    else:
        per[idu][doc] = ff

FACTS = ["contenance_m2", "zone", "zone_rnu", "sdp_restante_m2", "sdp_libelle", "emprise_bati_m2",
         "hauteur_faitage_m", "hauteur_egout_m", "hauteur_bati_m", "aleas_count", "aleas_mot",
         "derniere_vente_eur", "derniere_vente_date", "prix_median_maison_m2", "taxe_amenagement_eur",
         "proprietaire", "date_donnees", "date_genere", "ref_rapport"]
STRICT = [f for f in FACTS if f not in ("ref_rapport",)]  # ref varie par type de doc = normal

ecarts = []; couples = 0; long_rows = []
for idu in sorted(per):
    docs = per[idu]
    core_present = [d for d in CORE if d in docs]
    ctx_present = [d for d in CTX if d in docs]
    order = core_present + ctx_present
    with open(OUT / "docs" / f"{idu}.csv", "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["fait"] + order)
        for fact in FACTS:
            row = [fact] + [docs[d].get(fact, "") for d in order]
            w.writerow(row)
            for d in order:
                if docs[d].get(fact):
                    long_rows.append({"idu": idu, "role": PARC[idu]["role"], "doc": d, "fact": fact, "valeur": docs[d][fact]})
            # écart STRICT : seulement entre docs CORE
            if fact in STRICT:
                vals = {d: docs[d][fact] for d in core_present if docs[d].get(fact)}
                for a, b in itertools.combinations(vals, 2):
                    couples += 1
                    if vals[a] != vals[b]:
                        ecarts.append({"idu": idu, "role": PARC[idu]["role"], "fact": fact,
                                       "doc_a": a, "val_a": vals[a], "doc_b": b, "val_b": vals[b]})

with open(OUT / "facts_long.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["idu", "role", "doc", "fact", "valeur"]); w.writeheader(); w.writerows(long_rows)
with open(OUT / "ecarts.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["idu", "role", "fact", "doc_a", "val_a", "doc_b", "val_b"]); w.writeheader(); w.writerows(ecarts)

print("CORE couples comparés:", couples, "| écarts stricts CORE:", len(ecarts), "| faits:", len(long_rows))
print("écarts par fait:", dict(collections.Counter(e["fact"] for e in ecarts)))
