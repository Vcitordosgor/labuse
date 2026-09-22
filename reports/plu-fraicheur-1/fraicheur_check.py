"""PLU-FRAICHEUR-1 — pour les 24 communes : millésime SERVI par l'outil vs millésime EN_VIGUEUR au GPU.
Réutilise la logique GPU de PLU-RACCORD-1/gpu_pack_check.py (grid=insee, filtre PLU/POS/PLUI).
LECTURE SEULE : lit ce que l'outil sert (base `labuse`.plu_reglement_extrait) + ce que le GPU annonce.
Rien re-téléchargé, rien ré-ingéré."""
import csv, datetime as dt, pathlib, re, subprocess
import requests, yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = pathlib.Path(__file__).parent
MIL = yaml.safe_load((ROOT / "config" / "plu_millesimes.yaml").read_text())["communes"]


def date_from_idurba(idurba):
    """AAAAMMJJ en fin d'idurba (97411_PLU_20260423 → date(2026,4,23)). None sinon."""
    m = re.search(r"(\d{4})(\d{2})(\d{2})\D*$", idurba or "")
    if not m:
        return None
    try:
        return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


# ── ce que l'OUTIL SERT : idurba servi par commune (table ingérée plu_reglement_extrait) ──
def psql(sql):
    out = subprocess.run(["psql", "-d", "labuse", "-tAF|", "-c", sql], capture_output=True, text=True)
    return [l.split("|") for l in out.stdout.strip().splitlines() if l]


served = {r[0]: r[1] for r in psql(
    "SELECT insee, min(idurba) FROM plu_reglement_extrait GROUP BY insee")}


# ── ce que le GPU ANNONCE : document EN_VIGUEUR (grid=insee) ──
def gpu_en_vigueur(insee):
    """Retourne (idurba_en_vigueur, date, note). note ∈ ''|'gpu_vide'|'gpu_injoignable'|'pas_en_vigueur'."""
    if not re.fullmatch(r"974\d\d", insee):
        return (None, None, "insee_invalide")
    try:
        r = requests.get("https://www.geoportail-urbanisme.gouv.fr/api/document",
                         params={"grid": insee}, headers={"User-Agent": "labuse/1.0"}, timeout=20)
        r.raise_for_status()
        docs = [d for d in r.json() if (d.get("documentType") or d.get("type")) in ("PLU", "POS", "PLUI")]
    except Exception as e:  # noqa
        return (None, None, f"gpu_injoignable:{e}")
    if not docs:
        return (None, None, "gpu_vide")
    ev = [d for d in docs if (d.get("effectiveStatus") or d.get("status")) == "EN_VIGUEUR"]
    if not ev:
        # aucun EN_VIGUEUR : on prend le plus récent mais on le signale
        docs.sort(key=lambda d: str(d.get("originalName") or ""), reverse=True)
        idu = str(docs[0].get("originalName") or "")
        return (idu, date_from_idurba(idu), "pas_en_vigueur")
    idu = str(ev[0].get("originalName") or "")
    return (idu, date_from_idurba(idu), "")


rows = []
for insee in sorted(MIL):
    c = MIL[insee]
    st = c["statut"]
    idu_servi = served.get(insee)                 # None si non ingéré (révision/RNU)
    d_servi = date_from_idurba(idu_servi) if idu_servi else None
    gpu_idu, gpu_date, note = gpu_en_vigueur(insee)

    # Verdict
    if st == "rnu":
        verdict, ecart = "non comparable (RNU)", ""
        idu_servi = idu_servi or "— (RNU, aucun PLU)"
    elif idu_servi is None:  # révision : outil sert le pack LIVE, base non ingérée
        if note == "gpu_vide":
            verdict, ecart = "non comparable (révision, GPU vide → repli mairie)", ""
        elif note.startswith("gpu_injoignable"):
            verdict, ecart = "non comparable (GPU injoignable)", ""
        else:
            verdict, ecart = "non comparable (révision, non ingéré)", ""
        idu_servi = idu_servi or f"pack live GPU ({note or 'en vigueur'})"
    elif note == "gpu_vide":
        verdict, ecart = "non comparable (GPU vide)", ""
    elif note.startswith("gpu_injoignable"):
        verdict, ecart = "non comparable (GPU injoignable)", ""
    elif gpu_date and d_servi:
        if gpu_idu.lower() == (idu_servi or "").lower() or gpu_date == d_servi:
            verdict, ecart = "à jour", "0"
        elif gpu_date > d_servi:
            nj = (gpu_date - d_servi).days
            verdict, ecart = f"EN RETARD de {nj} j", str(nj)
        else:
            nj = (d_servi - gpu_date).days
            verdict, ecart = f"servi PLUS RÉCENT que GPU EN_VIGUEUR (+{nj} j) — à examiner", str(-nj)
    else:
        verdict, ecart = "non comparable (date illisible)", ""

    rows.append({
        "commune": c["commune"], "insee": insee, "statut_config": st,
        "millesime_servi": idu_servi or "",
        "date_servie": d_servi.isoformat() if d_servi else "",
        "millesime_gpu_en_vigueur": gpu_idu or ("—" if note in ("gpu_vide",) else ""),
        "date_gpu": gpu_date.isoformat() if gpu_date else "",
        "note_gpu": note,
        "verdict": verdict, "ecart_jours": ecart,
    })
    print(f"{insee} {c['commune']:<22} servi={ (d_servi.isoformat() if d_servi else idu_servi):<26} gpu={gpu_date or note:<12} → {verdict}")

out = HERE / "TABLE-24.csv"
with out.open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)

ajour = [r for r in rows if r["verdict"] == "à jour"]
retard = [r for r in rows if "RETARD" in r["verdict"]]
ncomp = [r for r in rows if r["verdict"].startswith("non comparable")]
autre = [r for r in rows if r not in ajour and r not in retard and r not in ncomp]
print("\n==== COMPTE ====")
print(f"à jour        : {len(ajour)}")
print(f"en retard     : {len(retard)}  -> {[(r['insee'],r['commune'],r['ecart_jours']+' j') for r in retard]}")
print(f"non comparable: {len(ncomp)}  -> {[(r['insee'],r['commune']) for r in ncomp]}")
if autre:
    print(f"autre         : {len(autre)} -> {[(r['insee'],r['commune'],r['verdict']) for r in autre]}")
print("\nCSV →", out)
