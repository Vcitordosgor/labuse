"""Phase 4 — populations en attente : classification des zones des 21 YAML PLU
+ pool servi réel par zone (lecture seule). Sorties JSON dans /tmp/phase4/out/.

Populations dérivées des YAML (comptes annoncés à vérifier : 15 / 92 / 14 / 11 / 89) :
  - dette_calibrage : zones `zones:` avec he_m ET hf_m non chiffrés dont >=1 'a_verifier'
    (hors prospect) — « capacité non calculable » (strict) ou repli générique (progressif).
  - gel (population e) : tous les libellés de zones_au_st.liste.
  - habitat_interdit_gele : sous-ensemble du gel = zones PLEINES à habitat interdit
    portées par la st-liste faute de hauteur (classification par commune, cf. rapports).
  - sans_hauteur : zones `zones:` avec he_m ET hf_m null (sans 'a_verifier', hors
    prospect) — retombent en générique (progressif) / non calculables (strict).
  - emprise_implicite : zones `zones:` habitat admis, hauteur exploitable, avec
    emprise_sol_pct null — emprise bornée par les seuls reculs.
"""
import json, os, re, unicodedata

import yaml
from sqlalchemy import text
from sqlalchemy.orm import Session
from labuse.db import make_engine

OUT = "/tmp/phase4/out"
os.makedirs(OUT, exist_ok=True)

SLUG2COMMUNE = {
    "bras_panon": "Bras-Panon", "cilaos": "Cilaos", "entre_deux": "Entre-Deux",
    "l_etang_sale": "L'Étang-Salé", "la_plaine_des_palmistes": "La Plaine-des-Palmistes",
    "la_possession": "La Possession", "le_port": "Le Port", "le_tampon": "Le Tampon",
    "les_avirons": "Les Avirons", "les_trois_bassins": "Les Trois-Bassins",
    "petite_ile": "Petite-Île", "saint_benoit": "Saint-Benoît",
    "saint_denis": "Saint-Denis", "saint_joseph": "Saint-Joseph",
    "saint_louis": "Saint-Louis", "saint_paul": "Saint-Paul",
    "saint_pierre": "Saint-Pierre", "sainte_marie": "Sainte-Marie",
    "sainte_rose": "Sainte-Rose", "sainte_suzanne": "Sainte-Suzanne",
    "salazie": "Salazie",
}
RESIDUELLES = ["Saint-André", "Saint-Leu", "Saint-Philippe"]

num = lambda x: isinstance(x, (int, float))

pops = {"dette_calibrage": [], "gel": [], "sans_hauteur": [], "emprise_implicite": []}
for slug, commune in sorted(SLUG2COMMUNE.items()):
    doc = yaml.safe_load(open(f"config/plu_{slug}.yaml", encoding="utf-8"))
    for code, v in (doc.get("zones") or {}).items():
        he, hf = v.get("he_m"), v.get("hf_m")
        hauteur_ok = num(he) or num(hf) or v.get("hauteur_mode") == "prospect"
        if not hauteur_ok:
            av = (he == "a_verifier") or (hf == "a_verifier")
            pops["dette_calibrage" if av else "sans_hauteur"].append(
                {"commune": commune, "zone": code, "habitat": v.get("habitat"),
                 "he": he, "hf": hf})
            continue
        if v.get("habitat") != "interdit" and v.get("emprise_sol_pct") is None:
            pops["emprise_implicite"].append(
                {"commune": commune, "zone": code,
                 "pleine_terre_pct": v.get("pleine_terre_pct")})
    st = (doc.get("zones_au_st") or {})
    for code in st.get("liste", []) or []:
        pops["gel"].append({"commune": commune, "zone": code})

# Pool servi par zone (toutes communes concernées + résiduelles)
POOL_ZONE = text("""
    SELECT COALESCE(z.attrs->>'libelle', z.subtype, z.name) AS lib,
           count(DISTINCT p.id) AS n
    FROM parcel_p_score_v2 s
    JOIN parcels p ON p.idu = s.parcelle_id
    JOIN spatial_layers z ON z.kind = 'plu_gpu_zone' AND z.commune = p.commune
         AND ST_Intersects(z.geom_2975, ST_PointOnSurface(p.geom_2975))
    WHERE s.run_id = 'q_v7_defisc' AND s.tier <> 'ecartee' AND p.commune = :c
    GROUP BY 1 ORDER BY 2 DESC""")

eng = make_engine(os.environ["LABUSE_DATABASE_URL"])
zone_pools = {}
with Session(eng) as s:
    for commune in sorted(set(SLUG2COMMUNE.values()) | set(RESIDUELLES)):
        zone_pools[commune] = {r.lib: r.n for r in s.execute(POOL_ZONE, {"c": commune})}

def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).strip().lower()

for name, entries in pops.items():
    for e in entries:
        zp = zone_pools.get(e["commune"], {})
        if e["zone"] in zp:
            e["pool_servi"] = zp[e["zone"]]
        else:  # graphie : tentative insensible casse/espaces
            cand = [lib for lib in zp if norm(lib) == norm(e["zone"])]
            e["pool_servi"] = zp[cand[0]] if cand else 0
            e["match"] = cand[0] if cand else "AUCUN_POLYGONE"

json.dump({"populations": pops, "zone_pools": zone_pools},
          open(f"{OUT}/populations.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

for name, entries in pops.items():
    tot = sum(e.get("pool_servi", 0) for e in entries)
    print(f"{name}: {len(entries)} zones, pool servi total {tot}")
print("\nRésiduelles (U/AU au sens noyau, préfixes U/AU) :")
for commune in RESIDUELLES:
    tot_uau, det = 0, {}
    for lib, n in zone_pools[commune].items():
        noyau = re.sub(r"^\d+", "", lib or "").strip().upper()
        if noyau.startswith("U") or noyau.startswith("AU"):
            tot_uau += n
            det[lib] = n
    tot = sum(zone_pools[commune].values())
    print(f"  {commune}: pool total {tot}, U/AU {tot_uau} ({json.dumps(det, ensure_ascii=False)})")
