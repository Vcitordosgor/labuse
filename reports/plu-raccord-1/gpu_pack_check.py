"""PLU-RACCORD-1 — contrôle live : rejoue la logique de /plu-annuaire/pack/{insee}
sur le GPU pour les 24 communes, et croise l'idurba servi avec config/plu_millesimes.yaml.
LECTURE SEULE (GET publics GPU). Aucune écriture hors ce rapport CSV."""
import csv, pathlib, re, sys
import requests, yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
MIL = yaml.safe_load((ROOT / "config" / "plu_millesimes.yaml").read_text())["communes"]


def pack(insee):
    """Réplique exacte de modules.py:plu_annuaire_pack (issue trouvé/vide/injoignable)."""
    if not re.fullmatch(r"974\d\d", insee):
        return {"err": "insee_invalide"}
    try:
        r = requests.get("https://www.geoportail-urbanisme.gouv.fr/api/document",
                         params={"grid": insee}, headers={"User-Agent": "labuse/1.0"}, timeout=20)
        r.raise_for_status()
        docs = [d for d in r.json() if (d.get("documentType") or d.get("type")) in ("PLU", "POS", "PLUI")]
    except Exception as e:  # noqa
        return {"err": f"gpu_injoignable:{e}"}
    if not docs:
        return {"vide": True}
    docs.sort(key=lambda d: ((d.get("effectiveStatus") or d.get("status")) == "EN_VIGUEUR",
                             str(d.get("originalName") or "")), reverse=True)
    doc = docs[0]
    idurba = str(doc.get("originalName") or "")
    return {"idurba": idurba, "statut_gpu": doc.get("effectiveStatus") or doc.get("status"),
            "id": doc.get("id"),
            "url": f"https://www.geoportail-urbanisme.gouv.fr/api/document/{doc.get('id')}/download/{idurba}.zip",
            "n_docs": len(docs)}


rows = []
for insee in sorted(MIL):
    c = MIL[insee]
    p = pack(insee)
    served = p.get("idurba", "")
    # Le zip servi appartient-il à CETTE commune ? l'idurba GPU doit commencer par l'INSEE.
    own = served.startswith(insee) if served else None
    # Concorde-t-il avec l'idurba de config (même document) ?
    cfg = c.get("idurba")
    match_cfg = (served.lower() == (cfg or "").lower()) if (served and cfg) else None
    # Taille du zip (>0) — HEAD léger.
    size = None
    if p.get("url"):
        try:
            h = requests.head(p["url"], headers={"User-Agent": "labuse/1.0"},
                              allow_redirects=True, timeout=20)
            size = h.headers.get("Content-Length") or ("chunked/200" if h.status_code == 200 else f"HTTP{h.status_code}")
        except Exception as e:  # noqa
            size = f"head_err:{e}"
    rows.append({
        "insee": insee, "commune": c["commune"], "statut_config": c["statut"],
        "idurba_config": cfg, "idurba_servi_gpu": served or p.get("err") or ("VIDE" if p.get("vide") else ""),
        "statut_gpu": p.get("statut_gpu", ""), "n_docs_gpu": p.get("n_docs", ""),
        "zip_appartient_commune": own, "concorde_config": match_cfg,
        "zip_taille": size, "zip_url": p.get("url", ""),
    })
    print(f"{insee} {c['commune']:<22} servi={served or p.get('err') or 'VIDE':<28} own={own} cfg={match_cfg} taille={size}")

out = pathlib.Path(__file__).parent / "gpu_pack_check.csv"
with out.open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
print("\nCSV →", out)
# Synthèse
own_ko = [r["insee"] for r in rows if r["zip_appartient_commune"] is False]
vide = [r["insee"] for r in rows if r["idurba_servi_gpu"] == "VIDE"]
print(f"own_ko={own_ko} vide={vide}")
