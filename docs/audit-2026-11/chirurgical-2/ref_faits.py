#!/usr/bin/env python3
"""Extrait les FAITS DE RÉFÉRENCE (servis par la fiche) pour les 12 parcelles → ref_faits.csv.
C'est la colonne FICHE de MATRICE-2 et la vérité contre laquelle les documents sont comparés."""
import csv, json
from pathlib import Path

OUT = Path.home() / "Desktop" / "chasse-1"
PARCELLES = [
    "97422000AD0887","97416000HT0538","97403000AR1517","97404000AM0838",
    "97417000AO0050","97411000IS0448","97404000AY0153","97414000CO0153",
    "97421000BN0260","97422000BW2635","97412000CV0446","97424000AO1198",
]

def g(d, *path, default=None):
    for k in path:
        if isinstance(d, dict) and k in d:
            d = d[k]
        else:
            return default
    return d

rows = []
for idu in PARCELLES:
    f = OUT / idu / "fiche.json"
    if not f.exists():
        rows.append({"idu": idu, "fait": "FICHE_ABSENTE", "valeur": ""}); continue
    d = json.load(f.open())
    pab = d.get("potentiel_a_batir") or {}
    lb = d.get("le_bien") or {}
    pa = d.get("prix_ancien") or {}
    tx = d.get("taxe_amenagement") or {}
    sv = d.get("score_v2") or {}
    al = d.get("aleas") or {}
    rp = d.get("reglement_plu") or {}
    dv = g(d, "dvf_parcelle", "secteur", default=[]) or []
    zones = rp.get("zones") or []
    facts = {
        "commune": d.get("commune"),
        "surface_dessin_m2": d.get("surface_dessin_m2") or d.get("surface_m2"),
        "contenance_cadastre_m2": d.get("contenance_m2") or d.get("surface_terrain_m2"),
        "surface_source": d.get("surface_source"),
        "zone_fam": pab.get("zone_fam"),
        "zone_lib": pab.get("zone_lib"),
        "zone_a_cheval": rp.get("a_cheval"),
        "n_zones": len(zones),
        "constructible": pab.get("constructible"),
        "constructible_motif": pab.get("motif"),
        "constructible_libelle": pab.get("libelle"),
        "rien_a_batir": pab.get("rien_a_batir"),
        "sdp_restante_m2": pab.get("sdp_restante_m2"),
        "emprise_batie_m2": lb.get("emprise_batie_m2"),
        "emprise_source": lb.get("emprise_source"),
        "nb_batiments": lb.get("nb_batiments"),
        "surface_libre_m2": lb.get("surface_libre_m2"),
        "hauteur_faitage_m": lb.get("hauteur_faitage_m"),
        "hauteur_source": lb.get("hauteur_source"),
        "prix_ancien_median": pa.get("median"),
        "prix_ancien_type": pa.get("type_prix"),
        "prix_ancien_n": pa.get("n"),
        "prix_ancien_radius_m": pa.get("radius_m"),
        "prix_ancien_periode": pa.get("periode"),
        "prix_ancien_fiable": pa.get("fiable"),
        "marche_synthese": d.get("marche_synthese"),
        "taxe_taux_communal_pct": tx.get("taux_communal_pct"),
        "taxe_taux_departemental_pct": tx.get("taux_departemental_pct"),
        "taxe_total_eur": tx.get("total_eur"),
        "taxe_annee": tx.get("annee"),
        "score_tier": sv.get("tier"),
        "score_label": sv.get("label"),
        "score_declasse": sv.get("declasse"),
        "score_motif": sv.get("motif"),
        "aleas_n": al.get("n"),
        "aleas_synthese": al.get("synthese"),
        "rnu": bool(d.get("rnu")),
        "dvf_secteur_mediane_prix_m2": g(dv[0], "mediane_prix_m2") if dv else None,
        "valeur_terrain_secteur_eur": g(d, "dvf_parcelle", "valeur_terrain_secteur_eur"),
        "plu_fraicheur": d.get("plu_fraicheur"),
    }
    for k, v in facts.items():
        rows.append({"idu": idu, "fait": k, "valeur": "" if v is None else json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v})

man = Path(__file__).parent / "ref_faits.csv"
with man.open("w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["idu", "fait", "valeur"])
    w.writeheader(); w.writerows(rows)
print(f"ref_faits.csv → {len(rows)} lignes, {len(PARCELLES)} parcelles")
# echo a compact per-parcelle summary
for idu in PARCELLES:
    pr = {r["fait"]: r["valeur"] for r in rows if r["idu"] == idu}
    print(f"{idu} {pr.get('commune','?'):16} zone={pr.get('zone_lib','?'):8} constr={pr.get('constructible','?'):6} "
          f"sdp={pr.get('sdp_restante_m2','?'):>6} empr={pr.get('emprise_batie_m2','?'):>5} "
          f"prix={pr.get('prix_ancien_median','?'):>6} tier={pr.get('score_tier','?')}")
