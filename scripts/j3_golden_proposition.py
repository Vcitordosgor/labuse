#!/usr/bin/env python
"""PHASE 0 J3 étape 1 — PROPOSITION de ~88 parcelles golden additionnelles (stratifiées).

LECTURE SEULE. Sélection DÉTERMINISTE (ORDER BY reproductible) qui, en plus des 32 golden
existants (noyau inchangé), couvre : ≥2 parcelles/commune (24, dont Saint-Philippe RNU), ≥5/tier v2,
chaque motif d'exclusion majeur ≥2, et les cas limites. Sort un tableau Markdown à valider par Vic.
"""
from __future__ import annotations

import json
import os
from collections import Counter

import psycopg
from psycopg.rows import dict_row

DB = os.environ.get("LABUSE_DATABASE_URL", "postgresql://openclaw@localhost:5432/labuse").replace("+psycopg", "")
RUN = "q_v6_m8"
CANARI = "97415000AC0253"     # canari événement — NE PAS dupliquer
GOLDEN = json.load(open("reports/m6-audit/golden/golden-parcelles.json"))["parcelles"]
EXISTING = set(GOLDEN) | {CANARI}

COMMUNES = {
    "97401": "Les Avirons", "97402": "Bras-Panon", "97403": "Entre-Deux", "97404": "L'Étang-Salé",
    "97405": "Petite-Île", "97406": "La Plaine-des-Palmistes", "97407": "Le Port",
    "97408": "La Possession", "97409": "Saint-André", "97410": "Saint-Benoît", "97411": "Saint-Denis",
    "97412": "Saint-Joseph", "97413": "Saint-Leu", "97414": "Saint-Louis", "97415": "Saint-Paul",
    "97416": "Saint-Pierre", "97417": "Saint-Philippe", "97418": "Sainte-Marie", "97419": "Sainte-Rose",
    "97420": "Sainte-Suzanne", "97421": "Salazie", "97422": "Le Tampon", "97423": "Les Trois-Bassins",
    "97424": "Cilaos",
}
MOTIFS = ["eau", "zonage_plu_gpu", "risques", "pente", "surface", "osm_faux_positif",
          "foncier_public", "emprise_lineaire", "emprise_routiere", "prescription_plu"]
MOTIF_LABEL = {"eau": "eau/hydrographie", "zonage_plu_gpu": "zone A/N inconstructible",
               "risques": "PPR/aléa fort", "pente": "pente forte", "surface": "micro-surface",
               "osm_faux_positif": "OSM faux positif", "foncier_public": "foncier public",
               "emprise_lineaire": "emprise linéaire (délaissé)", "emprise_routiere": "emprise routière",
               "prescription_plu": "prescription PLU (ER/EBC)"}

conn = psycopg.connect(DB, row_factory=dict_row)
cur = conn.cursor()
cur.execute("SET default_transaction_read_only = on")

sel: dict[str, dict] = {}
comm_count = Counter(idu[:5] for idu in GOLDEN)          # couverture existante par commune
tier_count = Counter((GOLDEN[i].get("db", {}).get("score_v2") or {}).get("tier") for i in GOLDEN)


def take(idu, insee, tier, motif, edge, justif) -> bool:
    if not idu or idu in EXISTING or idu in sel:
        return False
    sel[idu] = {"insee": insee, "commune": COMMUNES.get(insee, insee), "tier": tier,
                "motif": MOTIF_LABEL.get(motif, motif or "—"), "edge": edge, "justif": justif}
    comm_count[insee] += 1
    tier_count[tier] += 1
    return True


def rows(sql, **p):
    cur.execute(sql, p)
    return cur.fetchall()


def motif_of(idu):
    r = rows("""SELECT string_agg(DISTINCT c.layer_name, ',') AS m
                FROM dryrun_cascade_results c JOIN parcels p ON p.id = c.parcel_id
                WHERE c.run_label = %(r)s AND p.idu = %(i)s AND c.result = 'HARD_EXCLUDE'""", r=RUN, i=idu)
    return (r[0]["m"] or "").split(",")[0] if r and r[0]["m"] else None


# ── 1. COMMUNE-DRIVEN : pour CHAQUE commune, 2 exclusions (motifs variés, quotas globaux) + 2 promus
#      (tiers variés). Les motifs/tiers sont ainsi ÉTALÉS sur les 24 communes, pas concentrés. ──
motif_count: Counter = Counter()
MOTIF_CYCLE = MOTIFS  # ordre de priorité des motifs à couvrir

for insee, nom in COMMUNES.items():
    # 2 exclusions, en priorisant les motifs les moins couverts globalement
    excl = rows("""SELECT p.idu, c.layer_name motif FROM dryrun_cascade_results c
                   JOIN parcels p ON p.id=c.parcel_id
                   WHERE c.run_label=%(r)s AND c.result='HARD_EXCLUDE' AND left(p.idu,5)=%(i)s
                     AND c.layer_name = ANY(%(m)s)
                   ORDER BY p.idu""", r=RUN, i=insee, m=MOTIFS)
    # trie les candidats de la commune pour couvrir des motifs rares en premier
    excl.sort(key=lambda r: (motif_count[r["motif"]], r["idu"]))
    taken_motifs = set()
    got = 0
    for r in excl:
        if got >= 2:
            break
        if r["motif"] in taken_motifs:
            continue
        if take(r["idu"], insee, "ecartee", r["motif"], "", f"exclusion étage 0 : {MOTIF_LABEL[r['motif']]}"):
            motif_count[r["motif"]] += 1
            taken_motifs.add(r["motif"])
            got += 1
    # 2 promus, tiers variés (priorise reserve_fonciere/brulante/chaude sous quota)
    prom = rows("""SELECT parcelle_id idu, tier, rang FROM parcel_p_score_v2
                   WHERE run_id=%(r)s AND left(parcelle_id,5)=%(i)s
                     AND tier IN ('brulante','chaude','reserve_fonciere','a_creuser')
                   ORDER BY rang NULLS LAST, parcelle_id""", r=RUN, i=insee)
    prom.sort(key=lambda r: (tier_count[r["tier"]], r["rang"] or 1 << 30))
    taken_tiers = set()
    gotp = 0
    for r in prom:
        if gotp >= 1:            # 1 promu/commune (le reste des tiers vient des quotas ≥5 ci-dessous)
            break
        if r["tier"] in taken_tiers:
            continue
        if take(r["idu"], insee, r["tier"], None, "",
                f"tier v2 « {r['tier']} »" + (f" (rang {r['rang']})" if r["rang"] else "") + f" — {nom}"):
            taken_tiers.add(r["tier"])
            gotp += 1

# ── 2. GARANTIES DE QUOTA : chaque motif ≥2, chaque tier promu ≥5 (top-up si le commune-driven n'a pas suffi) ──
for m in MOTIFS:
    for r in rows("""SELECT p.idu, left(p.idu,5) insee FROM dryrun_cascade_results c
                     JOIN parcels p ON p.id=c.parcel_id
                     WHERE c.run_label=%(r)s AND c.layer_name=%(m)s AND c.result='HARD_EXCLUDE'
                     ORDER BY p.idu""", r=RUN, m=m):
        if motif_count[m] >= 2:
            break
        if take(r["idu"], r["insee"], "ecartee", m, "", f"exclusion étage 0 : {MOTIF_LABEL[m]} (quota motif)"):
            motif_count[m] += 1
for tier, need in (("reserve_fonciere", 5), ("chaude", 5), ("brulante", 5), ("a_creuser", 5)):
    for r in rows("""SELECT parcelle_id idu, left(parcelle_id,5) insee, rang FROM parcel_p_score_v2
                     WHERE run_id=%(r)s AND tier=%(t)s ORDER BY rang NULLS LAST, parcelle_id""", r=RUN, t=tier):
        if tier_count[tier] >= need:
            break
        take(r["idu"], r["insee"], tier, None, "", f"tier v2 « {tier} » (quota tier, rang {r['rang']})")

# ── 4. CAS LIMITES ──
edge_specs = [
    ("copro flaggée", "SELECT r.parcelle_idu idu FROM rnic_coproprietes r JOIN parcel_p_score_v2 s "
                      "ON s.parcelle_id=r.parcelle_idu AND s.run_id=%(r)s WHERE r.parcelle_idu IS NOT NULL "
                      "AND s.copro ORDER BY r.parcelle_idu LIMIT 2"),
    ("bailleur social (V NULL + badge)", "SELECT v.parcelle_id idu FROM parcel_v_score v "
                      "JOIN parcel_p_score_v2 s ON s.parcelle_id=v.parcelle_id AND s.run_id=%(r)s "
                      "WHERE v.owner_type='bailleur' AND v.v_score IS NULL ORDER BY v.parcelle_id LIMIT 2"),
    ("événement rouge (≠ canari)", "SELECT DISTINCT pm.idu FROM parcelle_personne_morale pm "
                      "JOIN bodacc_procedures b ON b.siren=pm.siren JOIN parcel_p_score_v2 s ON s.parcelle_id=pm.idu "
                      "AND s.run_id=%(r)s WHERE pm.idu <> %(c)s ORDER BY pm.idu LIMIT 2"),
    ("vue mer dégagée", "SELECT p.idu FROM parcel_vue_mer v JOIN parcels p ON p.id=v.parcel_id "
                      "JOIN parcel_p_score_v2 s ON s.parcelle_id=p.idu AND s.run_id=%(r)s "
                      "WHERE v.vue='oui' AND s.tier IN ('chaude','a_creuser','reserve_fonciere') ORDER BY p.idu LIMIT 2"),
    ("SDP résiduelle > 0", "SELECT p.idu FROM parcel_residuel rr JOIN parcels p ON p.id=rr.parcel_id "
                      "JOIN parcel_p_score_v2 s ON s.parcelle_id=p.idu AND s.run_id=%(r)s "
                      "WHERE rr.sdp_residuelle_m2 > 0 AND s.tier IN ('chaude','a_creuser') ORDER BY p.idu LIMIT 2"),
    ("propriétaire personne physique (masquage)", "SELECT s.parcelle_id idu FROM parcel_p_score_v2 s "
                      "LEFT JOIN parcelle_personne_morale pm ON pm.idu=s.parcelle_id "
                      "WHERE s.run_id=%(r)s AND pm.idu IS NULL AND s.tier IN ('chaude','a_creuser') "
                      "ORDER BY s.parcelle_id LIMIT 2"),
]
for edge, sql in edge_specs:
    for r in rows(sql, r=RUN, c=CANARI):
        idu = r["idu"]
        t = rows("SELECT tier FROM parcel_p_score_v2 WHERE run_id=%(r)s AND parcelle_id=%(i)s", r=RUN, i=idu)
        take(idu, idu[:5], t[0]["tier"] if t else "—", motif_of(idu), edge, f"cas limite : {edge}")

# ── restitution ──
by = sorted(sel.items(), key=lambda kv: (kv[1]["insee"], kv[0]))
print(f"# PROPOSITION GOLDEN — {len(sel)} additions (noyau 32 conservé → total {len(sel)+32})\n")
print("Couverture communes :", {c: comm_count[c] for c in sorted(COMMUNES) if comm_count[c] < 2} or "toutes ≥2")
print("Couverture tiers :", dict(tier_count), "\n")
print("| # | IDU | Commune | Tier v2 | Motif exclusion | Cas limite | Justification |")
print("| --- | --- | --- | --- | --- | --- | --- |")
for n, (idu, m) in enumerate(by, 1):
    print(f"| {n} | `{idu}` | {m['commune']} | {m['tier']} | {m['motif']} | {m['edge'] or '—'} | {m['justif']} |")
conn.close()
