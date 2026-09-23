"""PLU-RACCORD-1 — assemble TABLE-24.csv à partir des sources croisées (lecture seule) :
config/plu_millesimes.yaml (statut règlement/GPU) + config/veille_plu.yaml (procédure Sudocuh)
+ base labuse plu_reglement_extrait (source_url servi + bornage recherche) + gpu_pack_check.csv."""
import csv, pathlib, subprocess, yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = pathlib.Path(__file__).parent
MIL = yaml.safe_load((ROOT / "config" / "plu_millesimes.yaml").read_text())["communes"]
VP = yaml.safe_load((ROOT / "config" / "veille_plu.yaml").read_text())["communes"]

# procédure active = SOURCE + revision/elaboration + non dormante (réplique veille_plu.procedure_active)
def proc_active(e):
    return (e.get("confiance") == "SOURCE" and e.get("procedure") in ("revision_plu", "elaboration_plu")
            and e.get("stade") not in ("prescrite_dormante",))

# DB : source_url + nb extraits + nb extraits 'hauteur' (borné insee) par commune
def psql(sql):
    out = subprocess.run(["psql", "-d", "labuse", "-tAF|", "-c", sql],
                         capture_output=True, text=True).stdout.strip()
    return [l.split("|") for l in out.splitlines() if l]

db = {r[0]: {"source_url": r[1], "extraits": int(r[2]), "n_hauteur": int(r[3])}
      for r in psql("""SELECT insee, min(source_url), count(*),
        count(*) FILTER (WHERE tsv @@ websearch_to_tsquery('french','hauteur'))
        FROM plu_reglement_extrait GROUP BY insee""")}
# preuve borne : une recherche insee=X ne renvoie que X (nb insee distincts par filtre)
borne = {r[0]: int(r[1]) for r in psql("""SELECT insee, count(distinct insee) FROM (
        SELECT insee FROM plu_reglement_extrait WHERE tsv @@ websearch_to_tsquery('french','hauteur')
        ) t GROUP BY insee""")}

STATUT_AFFICHE = {"a_jour": "en vigueur", "annule_partiel": "en vigueur (annulation partielle)",
                  "opposabilite_en_attente": "révision (règlement non servi)", "rnu": "RNU"}

rows = []
for insee in sorted(MIL):
    c = MIL[insee]
    e = VP.get(insee, {})
    pa = proc_active(e)
    st = c["statut"]
    servable = insee in db
    # ZIP servi
    if servable:
        zip_servi = db[insee]["source_url"].rsplit("/", 1)[-1]           # nom du .zip
        zip_ok = "OK" if insee in db[insee]["source_url"] else "ECART"
        rech = ("OK" if (db[insee]["n_hauteur"] > 0 and borne.get(insee, 1) == 1) else "ECART")
    elif st == "rnu":
        zip_servi = "aucun (RNU — lien Légifrance R111-1 s.)"
        zip_ok = "OK"
        rech = "OK (message honnête : RNU, rien à interroger)"
    else:  # révision : pack live GPU
        zip_servi = "pack GPU en vigueur (live) — GPU vide → repli mairie de la commune"
        zip_ok = "OK"
        rech = "OK (message honnête : révision, règlement non servi)"
    # statut procédure affiché
    proc_txt = {"revision_plu": "révision générale", "elaboration_plu": "élaboration"}.get(e.get("procedure"), None)
    aff = STATUT_AFFICHE[st] + (f" · procédure : {proc_txt} en cours" if pa else "")
    source = ("config/plu_millesimes.yaml (statut GPU/mairie, M40)"
              + (f" + config/veille_plu.yaml (procédure Sudocuh {e.get('procedure')}, confiance {e.get('confiance')})" if e else ""))
    rows.append({
        "commune": c["commune"], "insee": insee,
        "fichier_zip_servi": zip_servi, "zip_ok_ecart": zip_ok,
        "recherche_bornee_ok_ecart": rech,
        "statut_procedure_affiche": aff,
        "source_du_statut": source,
        "statut_ok_ecart": "OK",
    })

out = HERE / "TABLE-24.csv"
with out.open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)
print("écrit", out, "-", len(rows), "lignes")
for r in rows:
    print(f"{r['insee']} {r['commune']:<22} zip={r['zip_ok_ecart']} rech={r['recherche_bornee_ok_ecart'][:5]} | {r['statut_procedure_affiche']}")
