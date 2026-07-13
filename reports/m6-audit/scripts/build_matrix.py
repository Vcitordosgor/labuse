#!/usr/bin/env python3
"""M6 §1.3 — génère la matrice usage × zone × commune (CSV).
Entrées : /tmp/zones_inventory_full.txt (DB, lecture seule),
          /tmp/verifs_reglement.py (dict VERIF rempli depuis les règlements écrits),
          resolve_zone (moteur faisabilité, lecture seule).
Sortie  : reports/m6-audit/sections/1-3a-matrice-plu.csv
"""
import csv
import sys

sys.path.insert(0, "/Users/openclaw/Desktop/labuse/src")
from labuse.faisabilite.plu_rules import resolve_zone  # noqa: E402

sys.path.insert(0, "/Users/openclaw/Desktop/labuse/reports/m6-audit/scripts")
from verifs_reglement import VERIF  # noqa: E402  # {(commune, zone): (vocation, habitat, source)}

OUT = "/Users/openclaw/Desktop/labuse/reports/m6-audit/sections/1-3a-matrice-plu.csv"

# Liste des zones candidates "vocation économique/activités" (heuristique libellé,
# confirmée par règlement pour les communes échantillonnées — cf. VERIF).
ECO = set()
for line in open("/Users/openclaw/Desktop/labuse/reports/m6-audit/scripts/eco_list2.txt", encoding="utf-8"):
    c, z = line.rstrip("\n").split("|")
    ECO.add((c, z))


def cascade_verdict(typezone: str) -> tuple[str, str]:
    """Reproduit ZonagePluGpuLayer (cascade_rules.yaml : positive [U, AU] ; exclude [A, N])."""
    up = typezone.upper()
    if up.startswith("U") or up.startswith("AU"):
        return ("CONSTRUCTIBLE (bonus zonage_u_au)",
                "aucune distinction d'usage — traitée comme constructible logement")
    if up.startswith("A") or up.startswith("N"):
        return ("EXCLUE si recouvrement A/N >= 90 % (sinon flag)", "aucun (inconstructible)")
    return ("PASS neutre (préfixe inconnu)", "aucun")


def faisa(commune: str, zone: str) -> str:
    try:
        r = resolve_zone(zone, commune)
    except Exception as e:  # pragma: no cover
        return f"erreur: {e}"
    if r is None:
        return "None (mode strict : zone non couverte)"
    cal = "calibrée" if r.calibree else "estimation générique"
    hf = r.hf_m if r.hf_m is not None else "-"
    he = r.he_m if r.he_m is not None else "-"
    if not r.constructible_neuf:
        return f"non constructible ({cal})"
    return f"constructible LOGEMENT ({cal}, he={he} hf={hf})"


rows = []
for line in open("/Users/openclaw/Desktop/labuse/reports/m6-audit/scripts/zones_inventory_full.txt", encoding="utf-8"):
    commune, lib, typezone, libelong, n, ha, n_foreign, foreign_idurbas = \
        line.rstrip("\n").split("|")
    verdict, usages = cascade_verdict(typezone)
    f = faisa(commune, lib)
    key = (commune, lib)
    if key in VERIF:
        vocation, habitat, source = VERIF[key]
    elif libelong:
        vocation, habitat, source = libelong, "", "GPU attrs libelong (non vérifié au règlement)"
    else:
        vocation, habitat, source = "non vérifié", "", ""
    is_eco_candidate = key in ECO
    # écart : vocation non-habitat mais moteur constructible logement
    ecart = ""
    constructible = verdict.startswith("CONSTRUCTIBLE")
    if key in VERIF:
        if vocation.startswith("ANOMALIE"):
            ecart = "ANOMALIE DONNÉE : zone d'un document voisin rattachée à cette commune"
        elif habitat.startswith("non") and constructible:
            ecart = ("ECART MAJEUR : habitat INTERDIT au règlement, "
                     "moteur = constructible logement")
        elif habitat.startswith("conditionnel") and constructible:
            ecart = ("ECART MAJEUR : habitat conditionnel (gardiennage/lié à l'activité), "
                     "moteur = constructible logement sans condition")
        elif habitat.startswith("indéterminé") and constructible:
            ecart = "ECART : règlement en renvoi (OAP) — moteur = constructible logement"
        elif habitat.startswith("oui") and constructible:
            ecart = "conforme (usage habitat admis)"
        elif not constructible and habitat.startswith("non"):
            ecart = "conforme (exclue)"
    elif is_eco_candidate and constructible:
        ecart = ("ECART PROBABLE (libellé économique/activités, non vérifié au règlement) : "
                 "moteur = constructible logement")
    elif typezone == "AUs" and constructible:
        ecart = ("ECART : zone AU STRICTE (typezone GPU AUs — ouverture subordonnée à "
                 "modification/révision) traitée comme constructible par la cascade")
    deb = ""
    if int(n_foreign) > 0:
        deb = f"{n_foreign}/{n} polygone(s) issus d'un document voisin : {foreign_idurbas}"
    if key in VERIF:
        verif = f"règlement lu ({source.split(',')[0]})" if source else "règlement lu"
    else:
        verif = "non vérifié"
    rows.append({
        "commune": commune, "zone": lib, "typezone": typezone,
        "n_polygones": n, "surface_ha": ha,
        "vocation_reglement": vocation,
        "habitat_autorise": habitat,
        "verdict_moteur": verdict,
        "usages_moteur": usages,
        "faisabilite_moteur": f,
        "ecart": ecart,
        "anomalie_rattachement": deb,
        "source": source,
        "verif": verif,
    })

with open(OUT, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
print(f"{len(rows)} lignes -> {OUT}")
n_ecart = sum(1 for r in rows if r["ecart"].startswith("ECART"))
print(f"ecarts: {n_ecart}")
