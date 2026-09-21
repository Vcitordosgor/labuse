"""DONNEES-1 lot 1 — génère la matrice données × surfaces (markdown, lecture seule).

Confronte le registre (donnees.py : 261 données sur main) aux robinets (robinets.py : les
endroits qui AFFICHENT) et aux lectures fines (lectures.py) — le graphe est le miroir
de ce que sert chaque écran. Colonnes = surfaces du mandat : fiche parcelle · fiche
commune · 17 outils · 4 documents · Copilote · carte, plus une colonne « autres écrans »
(Radar/veille, Projets, CRM, notifications, page client, admin) pour ne rien jeter.

Aucune écriture en base, aucune correction : sort du markdown sur stdout.
"""
from __future__ import annotations

import sys
from collections import defaultdict

from labuse.registre.donnees import DONNEES
from labuse.registre.robinets import ROBINETS
from labuse.registre.lectures import LECTURES
from labuse.registre.tables import RESERVOIR_TABLES, reservoirs_de
from labuse.circuit_garanties import (lecteurs_du_code, _REPERTOIRES_EXEMPTS_G6,
                                      _FICHIERS_EXEMPTS_G6)

# ── surfaces du mandat (ordre du registre front frontend/src/components/outils/registry.ts) ──
OUTILS_17 = [
    ("etudier", "Étudier un bien"), ("faisa", "Faisabilité"), ("taxe", "Taxe d'aménagement"),
    ("pieges", "Pièges et risques"), ("plu", "PLU"), ("comparer", "Comparer des parcelles"),
    ("assemblage", "Assemblage"), ("scan", "Scan patrimoine"), ("courrier", "Courrier propriétaire"),
    ("solaire", "Prospection solaire"), ("communes", "Communes"), ("permis", "Permis"),
    ("densifier", "Densifier l'existant"), ("etude_zone", "Étude de zone"),
    ("temps", "Remonter le temps"), ("blocs", "Blocs fonciers"), ("successions", "Successions à venir"),
]
DOCS_4 = [("doc_dossier", "Dossier"), ("doc_financier", "Financier"),
          ("doc_apporteur", "Apporteur"), ("doc_predossier", "Pré-dossier PC")]

# robinet id (top-level outil) -> clé outil du mandat
OUTIL_ROBINET = {
    "outil_etudier_bien": "etudier", "outil_faisabilite": "faisa",
    "bilan_cout_construction_ref": "faisa",           # bilan de coût = sous-calc de Faisabilité
    "outil_taxe_amenagement": "taxe", "outil_pieges": "pieges", "outil_plu": "plu",
    "outil_comparer_parcelles": "comparer", "outil_assemblage": "assemblage",
    "outil_scan_patrimoine": "scan", "outil_courrier": "courrier",
    "outil_prospection_solaire": "solaire", "outil_communes": "communes",
    "outil_permis": "permis", "outil_densifier": "densifier", "outil_etude_zone": "etude_zone",
    "outil_remonter_temps": "temps", "outil_blocs_fonciers": "blocs",
    "outil_successions": "successions",
}
# robinets pdf -> colonne document (banquier légal redirigé vers financier ; flash/lettre = autres)
PDF_ROBINET = {
    "pdf_dossier_expert": "doc_dossier", "pdf_financier": "doc_financier",
    "pdf_banquier": "doc_financier",                  # 308 → /financier (EXPORTS-2 lot 8)
    "pdf_argumentaire": "doc_apporteur", "pdf_pre_dossier_pc": "doc_predossier",
}


def surface_du_robinet(rid, r):
    """Rend la clé de colonne du mandat pour un robinet, ou 'autres' / None."""
    cat = r.categorie
    if cat in ("couche", "fond"):
        return "carte"
    if cat == "copilote":
        return "copilote"
    if cat == "fiche":
        if r.parent == "fiche_parcelle":
            return "fp"
        if r.parent == "fiche_commune":
            return "fc"
        return "autres"                               # fiche_annonce / _proprietaire / _soleil
    if cat == "outil":
        top = rid
        while ROBINETS[top].parent and ROBINETS[top].parent in ROBINETS:
            top = ROBINETS[top].parent
        return OUTIL_ROBINET.get(top, "autres")       # radar_client / panel_filtres → autres
    if cat == "pdf":
        return PDF_ROBINET.get(rid, "autres")         # flash / lettre_zonage → autres
    return "autres"                                   # veille projets crm notification page_client admin


COLS = (["fp", "fc"] + [k for k, _ in OUTILS_17] + [k for k, _ in DOCS_4]
        + ["copilote", "carte", "autres"])
COL_LABEL = {"fp": "Fiche parcelle", "fc": "Fiche commune", "copilote": "Copilote",
             "carte": "Carte (couche)", "autres": "Autres écrans"}
COL_LABEL.update({k: v for k, v in OUTILS_17})
COL_LABEL.update({k: v for k, v in DOCS_4})
# codes de colonne courts pour l'entête de la grille
CODE = {"fp": "FP", "fc": "FC", "copilote": "Co", "carte": "Ca", "autres": "Au",
        "etudier": "Et", "faisa": "Fa", "taxe": "Tx", "pieges": "Pg", "plu": "PL",
        "comparer": "Cp", "assemblage": "As", "scan": "Sc", "courrier": "Cr",
        "solaire": "So", "communes": "Cm", "permis": "Pm", "densifier": "De",
        "etude_zone": "EZ", "temps": "Tp", "blocs": "Bl", "successions": "Su",
        "doc_dossier": "D1", "doc_financier": "D2", "doc_apporteur": "D3", "doc_predossier": "D4"}


def crosses_par_donnee():
    """donnée -> set(colonnes) où un robinet la sert."""
    out = defaultdict(set)
    for rid, r in ROBINETS.items():
        col = surface_du_robinet(rid, r)
        for cid in r.chiffres:
            out[cid].add(col)
    return out


# ── Part B — lignage des tables de réservoir (table → affichage réel) ────────────────
# Verdicts curatés (preuves : qa/lue_verdicts.py SOURCES-AUDIT-1 + traçage DONNEES-1 lot 1).
# DISPLAYED = la donnée servie ; DERIVE = servie via une table dérivée/cache ; MACHINERIE =
# lue par l'app mais pour une jointure/QC/scoring, jamais un champ montré ; DARK = ingérée,
# surveillée, n'atteint AUCUN écran ; RETIRE = orpheline documentée (tables.py), conservée.
VERDICT_TABLE = {
    # ── DARK — ingérée/surveillée, jamais affichée (cible du mandat) ──
    "bodacc_depots": ("DARK", "dépôts de comptes annuels des PM (14 k) — le frère bodacc_procedures "
                      "sert les événements ; les dépôts ne sont lus par aucun écran. → Lot 2 : signal PM."),
    "rp_logement_commune": ("DARK", "24 variables logement RP2022 par commune — « métadonnée » "
                            "(qa/lue_verdicts) ; l'égout passe par anc_maille_taux. → Lot 2."),
    "parcel_cosia_couverture": ("DARK", "couverture CoSIA par classe et par parcelle (1,9 M) — "
                                "précalcul « interne » (qa/lue_verdicts), aucun lecteur de service."),
    "vegetation_zonal_acc": ("DARK", "stats zonales végétation par parcelle (1,16 M) — étage "
                             "intermédiaire « interne » agrégé dans parcel_vegetation (lui affiché)."),
    "mobpro_commune": ("RETIRE", "MOBPRO domicile-travail — RETIRÉ 06/09 (code mort, maille "
                       "infra-communale absente INSEE) ; table VIDE (0 l.), remplacée par SIRENE."),
    "anc_office_eau_commune": ("RETIRE", "chroniques Office de l'eau (6 l.) — RETIRÉ 13/09, "
                               "supplanté par anc_maille_taux (RP2022 EGOUL), conservé sans lecteur."),
    "cadastre_historique": ("MACHINERIE", "fabricant : corrige sitadel_permits.geom à l'ingestion "
                            "(qa/lue_verdicts « non ») ; aucun endpoint ne la SELECT."),
    "sudocuh_procedures": ("MACHINERIE", "lue uniquement par le scoring du run CANDIDAT q_v14 "
                           "(anciennete_plu) ; run servi q_v11_m137 → 0 surface client (qa/lue_verdicts « non »)."),
    # ── MACHINERIE — lue par l'app, jamais un champ montré ──
    "qa_cosia_bati": ("MACHINERIE", "QA CoSIA vs BD TOPO (445 k) — « interne » (qa/lue_verdicts)."),
    "rnb_rattachement_bdtopo": ("MACHINERIE", "jointure spatiale RNB↔BD TOPO (817 k) + filtre QC ; "
                                "les identifiants RNB montrés viennent de rnb_batiments."),
    "ortho_tiles": ("MACHINERIE", "grille/checkpoint de tuiles pour la détection ML ; le fond ortho "
                    "vient du WMTS IGN, les piscines de parcel_equipements."),
    "ortho_detections": ("MACHINERIE", "détections ML brutes (QC) ; les piscines servies passent par "
                         "parcel_equipements."),
    "owner_enrichment": ("MACHINERIE", "cache enrichissement DINUM du Score V (9,7 k) — débranché de "
                         "l'affichage, réservé au Score V (lectures.py)."),
    "owner_denom_lookup": ("MACHINERIE", "cache résolution dénomination→SIREN du Score V (2,6 k)."),
    "pm_dirigeant_gigogne": ("MACHINERIE", "dirigeants gigogne (2,1 k) → v_pm_propension → contexte "
                             "cascade (drapeau 0 pt) ; le signal dirigeant montré vient de pm_dirigeants."),
    "bodacc_sondages": ("MACHINERIE", "journal de sondage BODACC (scoring/état interne)."),
    "dvf_mutation_detail": ("MACHINERIE", "détail de mutation — compagnon « interne » (qa/lue_verdicts) ; les prix montrés viennent de dvf_mutations/_parcelle."),
    "lidar_dalle_grille": ("MACHINERIE", "état batch des dalles LiDAR (reprise)."),
    "p_model_filo": ("MACHINERIE", "jointure Filosofi par parcelle — entrée du modèle de scoring."),
    "solar_grid": ("MACHINERIE", "grille PVGIS intermédiaire ; le productible vient de parcel_solar."),
    "pige_captures": ("MACHINERIE", "captures HTML brutes de la pige (interne)."),
    "pige_interets_agence": ("MACHINERIE", "intérêts d'agence de la pige (interne)."),
    "annonces": ("MACHINERIE", "trace admin d'annonces (chaîne 3) — CREATE/INSERT, jamais lue."),
    # ── DERIVE — brute lue par l'ingestion, servie via un cache/table dérivée (qa/lue_verdicts « oui ») ──
    "commune_rei": ("DERIVE", "→ fiche commune « Taxe foncière (REI) » (fiche_commune.py:fiscalite ; cache commune)."),
    "commune_ort": ("DERIVE", "→ fiche commune « ACV/PVD/ORT » (fiche_commune.py:ort) + filtre Denormandie."),
    "commune_zonage_abc": ("DERIVE", "→ fiche commune « Zonage A/B/C » (fiche_commune.py:zonage_abc)."),
    "azi_communes": ("DERIVE", "→ fiche commune Risques « AZI/TRI » (azi_tri.py:azi_tri_commune)."),
    "cout_construction_ref": ("DERIVE", "→ outil Faisabilité + bilan Financier (engine.py:_couts_construction_ref)."),
    "ocsge_sol": ("DERIVE", "→ « Le bien » (% artificialisé) via parcel_ocsge + couche artificialisation."),
    "ocsge_evolution": ("DERIVE", "→ « Enveloppe ZAN » (artificialisation 2017→2022) via moteurs/commune.py."),
    "oll_loyers": ("DERIVE", "→ fiche commune « Loyers » (marche_commune.py:ligne9_loyer)."),
    "oll_zonage": ("DERIVE", "→ zonage loyer OLL, support de « Loyers » (fiche commune)."),
    "plu_reglement_extrait": ("DERIVE", "→ fiche « Règlement d'urbanisme » (app.py:_reglement_plu_block) + outil PLU."),
    "rgealti_pente_5m": ("DERIVE", "→ fiche « Terrain » (pente) via parcel_terrain + couche pente + cascade."),
    "rgealti_mnt_5m": ("DERIVE", "→ altitude/MNT via parcel_enrichment (exposition, viabilisation)."),
    "annuaire_services": ("DERIVE", "436 services DILA → page admin « Contacts institutionnels » SEULEMENT "
                          "(hors surfaces client ; les 24 mairies passent par la table mairies)."),
}


def _counts():
    """Charge les count(*) réels (n_live_tup est périmé) depuis /tmp/reservoir_counts.txt."""
    out = {}
    try:
        for ln in open("/tmp/reservoir_counts.txt"):
            if "|" in ln:
                t, n = ln.strip().split("|")
                out[t] = int(n)
    except FileNotFoundError:
        pass
    return out


def _app_readers(files):
    return [f for f in files if not f.startswith(_REPERTOIRES_EXEMPTS_G6)
            and f not in _FICHIERS_EXEMPTS_G6]


def part_b():
    counts = _counts()
    lc = lecteurs_du_code()
    disp = {cid for r in ROBINETS.values() for cid in r.chiffres}
    tbl_ch = defaultdict(set)
    for L in LECTURES:
        if L.chiffre and L.chiffre in disp:
            tbl_ch[L.table].add(L.chiffre)
    lset = {L.table for L in LECTURES}
    tables = sorted({t for rt in RESERVOIR_TABLES.values() for t in rt.tables if t != "spatial_layers"})

    def verdict(t):
        if t in VERDICT_TABLE and VERDICT_TABLE[t][0]:
            return VERDICT_TABLE[t]
        if tbl_ch.get(t):
            return ("DISPLAYED", "sert " + ", ".join(sorted(tbl_ch[t])[:3])
                    + (" …" if len(tbl_ch[t]) > 3 else ""))
        ar = _app_readers(lc.get(t, set()))
        if ar:
            return ("DERIVE", "lue par l'app (" + ", ".join(x.split("/")[-1] for x in ar[:2])
                    + ") — sert via une table dérivée/donnée.fonction")
        return ("DARK", "aucun lecteur d'app — à instruire")

    n_by = defaultdict(int)
    rows = []
    for t in tables:
        slugs = reservoirs_de(t)
        v, why = verdict(t)
        n_by[v] += 1
        rows.append((t, ",".join(slugs), counts.get(t, "?"), v, why))
    print("\n## Partie B — lignage des tables de réservoir → affichage réel\n")
    print("Verdicts : "
          + " · ".join(f"**{k}** {n_by[k]}" for k in ("DISPLAYED", "DERIVE", "MACHINERIE", "DARK", "RETIRE") if n_by[k]))
    print()
    print("| table | réservoir | lignes | verdict | trace / raison |")
    print("|---|---|---:|---|---|")
    for t, slug, n, v, why in rows:
        print(f"| `{t}` | {slug} | {n if n=='?' else format(n, ',').replace(',', ' ')} | {v} | {why} |")


def part_c_autres():
    """Les données servies UNIQUEMENT hors des surfaces du mandat (écrans secondaires)."""
    cr = crosses_par_donnee()
    # robinet id -> categorie, pour dire QUEL écran secondaire
    cat_par_donnee = defaultdict(set)
    for rid, r in ROBINETS.items():
        if surface_du_robinet(rid, r) == "autres":
            for cid in r.chiffres:
                cat_par_donnee[cid].add(f"{r.categorie}:{r.nom}")
    mandat = set(COLS) - {"autres"}
    print("\n## Partie A bis — les 47 données servies UNIQUEMENT hors surfaces du mandat\n")
    print("| donnée | niveau | écran(s) secondaire(s) |")
    print("|---|---|---|")
    for cid, d in DONNEES.items():
        if d.en_attente:
            continue
        if not (cr.get(cid, set()) & mandat) and cr.get(cid, set()) == {"autres"}:
            ecr = "; ".join(sorted(cat_par_donnee.get(cid, {"?"})))
            print(f"| {cid} | {d.niveau} | {ecr} |")


def main():
    cr = crosses_par_donnee()
    mandat_cols = set(COLS) - {"autres"}
    n_affichees = sum(1 for cid, d in DONNEES.items()
                      if (cr.get(cid, set()) & mandat_cols) and not d.en_attente)
    n_autres_only = sum(1 for cid, d in DONNEES.items()
                        if not d.en_attente and cr.get(cid, set()) == {"autres"})
    n_attente = sum(1 for d in DONNEES.values() if d.en_attente)

    print("<!-- généré par scripts/donnees1_matrice.py — ne pas éditer à la main -->")
    print(f"- Données du registre : **{len(DONNEES)}**")
    print(f"- Affichées sur ≥1 surface du mandat (N) : **{n_affichees}**")
    print(f"- Affichées UNIQUEMENT hors mandat (autres écrans) : **{n_autres_only}**")
    print(f"- Déclarées en attente (servies par aucun robinet, par dessein) : **{n_attente}** "
          + ", ".join(cid for cid, d in DONNEES.items() if d.en_attente))
    print()
    # légende des codes
    print("Codes colonnes : " + " · ".join(f"`{CODE[c]}`={COL_LABEL[c]}" for c in COLS))
    print()
    # grille, groupée par niveau
    header = "| donnée | " + " | ".join(CODE[c] for c in COLS) + " |"
    sep = "|" + "---|" * (len(COLS) + 1)
    for niveau in ("parcelle", "commune", "zone", "proprietaire", "annonce", "global"):
        ids = [cid for cid, d in DONNEES.items() if d.niveau == niveau]
        if not ids:
            continue
        print(f"\n### niveau {niveau} ({len(ids)})\n")
        print(header)
        print(sep)
        for cid in ids:
            row = cr.get(cid, set())
            cells = ["✕" if c in row else "" for c in COLS]
            flag = " ⏳" if DONNEES[cid].en_attente else ""
            print(f"| {cid}{flag} | " + " | ".join(cells) + " |")
    part_b()
    part_c_autres()


if __name__ == "__main__":
    main()
