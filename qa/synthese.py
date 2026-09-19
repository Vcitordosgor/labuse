"""SOURCES-AUDIT-1 — synthèse finale : verdicts Remplie/Visible + capture + verdict global,
et les 4 listes. Lecture seule. Sortie: /tmp/audit_table.tsv + résumés stdout.
"""
import json, os
d = json.load(open("/tmp/sources_audit_full.json"))
inv = json.load(open("/tmp/stored_to_front.json"))  # stored kind -> [front]
CAPDIR = "/Users/openclaw/Desktop/labuse-sources-audit/captures/sources-audit"

def cap_exists(name):
    return os.path.exists(os.path.join(CAPDIR, name))

# ── corrections tardives (notes RESERVOIR périmées vs état réel DB) ──
for o in d:
    if o["slug"] == "taxe_amenagement":
        o["reinjectable"], o["reinjectable_why"] = "oui", "ingest-taxe-amenagement — 24 communes (part communale 5 %, DGFiP DELTA), maj 2026-09-08 (note 'a_faire' périmée)"
    if o["slug"] == "communes_ign":
        o["rempli_total"] = 24  # mvt_communes matérialisé (24)

# sources sans table PROPRE par conception (rempli=n/a, pas un échec)
SANS_TABLE_NA = {"deal_wms_wfs":"hub (proxys qpv/npnru)", "loyers_dhup":"repli JSON embarqué",
                 "rtaa_dom":"règles portées par le code", "sirene_recherche_entreprises":"API INSEE en direct",
                 "spanc_epci":"saisie → parcel_anc (pas de table propre)"}

# couche front pour la capture : slug -> première couche stockée -> front
def couche_front(o):
    cs = [c for c in (o["couches"].split(",") if o["couches"] else []) if c]
    for stored in cs:
        fr = inv.get(stored)
        if fr:
            for f in fr:
                if cap_exists(f"couche_{f}.png"):
                    return f
    return None

# assignation Remplie + Visible + capture
for o in d:
    slug, n = o["slug"], o["rempli_total"]
    # REMPLIE
    if slug in SANS_TABLE_NA:
        o["remplie"] = "n/a"; o["remplie_note"] = SANS_TABLE_NA[slug]
    elif slug == "dpe_ademe":
        o["remplie"] = "non"; o["remplie_note"] = "16 lignes (quasi-vide ; attendu : logements des 24 communes)"
    elif n and n > 0:
        o["remplie"] = "oui"; o["remplie_note"] = f"{n} lignes"
    else:
        o["remplie"] = "non"; o["remplie_note"] = "0 ligne"
    # VISIBLE + capture
    if o["lue"] == "non":
        o["visible"] = "non"; o["capture"] = "—"
    elif o["lue"] == "na":  # rtaa_dom
        o["visible"] = "n/a"; o["capture"] = "—"
    else:
        fr = couche_front(o)
        rob = o["lue_robinet"].lower()
        if fr:
            o["capture"] = f"couche_{fr}.png"
        elif "radar" in rob:
            o["capture"] = "radar.png"
        elif ("fiche commune" in rob or "contextepanel" in rob or "fiche_commune" in rob
              or "commune '" in rob or "fiche commune" in o["lue_robinet"].lower()):
            o["capture"] = "fiche_commune_1.png"
        elif "étude de zone" in rob or "etude de zone" in rob:
            o["capture"] = "outil_etude-zone.png"
        elif "prospection solaire" in rob or "solaire" in rob:
            o["capture"] = "outil_prospection-solaire.png"
        elif "veille promoteurs" in rob or "scan patrimoine" in rob or "patrimoine" in rob:
            o["capture"] = "outil_veille-promoteurs.png"
        elif "permis" in rob and "sitadel" in rob:
            o["capture"] = "outil_permis.png"
        elif "servitudes" in rob:
            o["capture"] = "outil_risques.png"
        elif "export" in rob and "loyers" in rob:
            o["capture"] = "(export md/html — pas d'écran React)"
        else:
            o["capture"] = "fiche_parcelle_3.png"
        o["visible"] = "oui" if o["capture"].endswith(".png") else "oui*"
    # VERDICT global (vert aux 4)
    checks = [o["remplie"], o["lue"], o["visible"], o["reinjectable"]]
    o["vert4"] = all(c == "oui" for c in checks)

json.dump(d, open("/tmp/audit_final.json", "w"), ensure_ascii=False, indent=1)

from collections import Counter
print("REMPLIE:", Counter(o["remplie"] for o in d))
print("LUE:", Counter(o["lue"] for o in d))
print("VISIBLE:", Counter(o["visible"] for o in d))
print("REINJECTABLE:", Counter(o["reinjectable"] for o in d))
print("VERT aux 4:", sum(1 for o in d if o["vert4"]), "/", len(d))
print("\n=== VIDES (Remplie=non) ===")
for o in d:
    if o["remplie"] == "non": print(f'  {o["slug"]:26} {o["remplie_note"]}')
print("\n=== LUES PAR PERSONNE (Lue=non) ===")
for o in d:
    if o["lue"] == "non": print(f'  {o["slug"]:26} {o["lue_robinet"][:80]}')
print("\n=== JAMAIS AFFICHÉES (Visible=non) ===")
for o in d:
    if o["visible"] == "non": print(f'  {o["slug"]:26}')
print("\n=== SANS VANNE (Réinjectable=non) ===")
for o in d:
    if o["reinjectable"] == "non": print(f'  {o["slug"]:26} {o["reinjectable_why"]}')
print("\n=== n/a divers ===")
for o in d:
    nas=[k for k in ("remplie","lue","visible","reinjectable") if o[k] in ("n/a","na")]
    if nas: print(f'  {o["slug"]:26} {",".join(nas)}')
# captures manquantes ?
miss=[o["slug"] for o in d if o["capture"].endswith(".png") and not cap_exists(o["capture"])]
print("\ncaptures référencées manquantes:", miss)