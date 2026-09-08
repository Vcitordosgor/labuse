"""SCORING-4 · Étape 5 — l'arène : LE tableau, les paliers, le top-50, les migrations.

Compare les QUATRE runs qui isolent ce qui vient du MODÈLE et ce qui vient des
DONNÉES :
  - q_v11_m137     : le SERVI (modèle m36, cascade servie) ;
  - q_v12          : gains de MODÈLE seuls (recette q_v12, cascade servie) ;
  - q_v13_sources1 : gains de DONNÉES seuls (modèle m36 servi, cascade + 4 378
                     exclusions neuves de SOURCES-1) ;
  - q_v14          : LES DEUX (recette q_v12 + variables as-of, cascade q_v13_sources1).

Produit (reports/q-v14/) :
  tableau5_le_tableau.csv/.md   — le tableau format SCORING-2, 4 colonnes ;
  tableau5_paliers.csv          — effectifs par palier, île + Saint-Paul ;
  tableau5_top50.csv            — 50 premières Priorité q_v14 vs servi, 3 raisons FR ;
  tableau5_migration.csv        — migrations de palier servi → q_v14 + « permis d'un pro » ;
  tableau5_ecarte.csv           — ce qui est écarté et pourquoi.

Lecture seule sur la base (les runs sont déjà calculés). AUCUN promote.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import engine, ROOT, SERVED_RUN  # noqa: E402
from labuse.scoring.tiers_client import court  # noqa: E402
from labuse.scoring.p_v2.qv14 import LIBELLES_QV14  # noqa: E402  (libellés à jour)

QDIR = ROOT / "reports/q-v14"
SAINT_PAUL = "97415"
RUNS = [(SERVED_RUN, "q_v11_m137 (servi)"), ("q_v12", "q_v12 (modèle seul)"),
        ("q_v13_sources1", "q_v13_sources1 (données seules)"), ("q_v14", "q_v14 (les deux)")]
#: palier client par tier servi (tiers_client.court) — Priorité = brulante,
#: À suivre = chaude ; les tiers déclassés/écartés ont leur propre libellé.
TETE_TIERS = ("brulante", "chaude")


def _tiers(eng, run_id: str) -> pd.DataFrame:
    return pd.read_sql(
        "SELECT parcelle_id AS idu, p_raw, rang, tier, copro, "
        "left(parcelle_id,5) AS insee FROM parcel_p_score_v2 WHERE run_id = %(r)s",
        eng, params={"r": run_id})


def le_tableau(eng) -> None:
    """LE tableau (format SCORING-2) : K0 modèle + distribution de paliers du run."""
    k0 = pd.read_csv(ROOT / "reports/score-v2-arene/k0_table.csv").set_index("candidat")
    # K0 modèle : servi = ligne_de_base ; q_v13_sources1 = MÊME modèle servi.
    k0map = {"q_v11_m137 (servi)": "ligne_de_base", "q_v12 (modèle seul)": "q_v12",
             "q_v13_sources1 (données seules)": "ligne_de_base", "q_v14 (les deux)": "q_v14"}
    def _casc(label: str) -> int:
        return int(pd.read_sql(
            "SELECT count(*) n FROM dryrun_parcel_evaluations WHERE run_label = %(r)s "
            "AND status IN ('exclue','faux_positif_probable')", eng,
            params={"r": label})["n"].iloc[0])

    # la cascade que CHAQUE run reflète : q_v14 a réutilisé (override) celle de
    # q_v13_sources1 — son propre dryrun est vide (scoring seul). Les autres = la leur.
    cascade_src = {"q_v14 (les deux)": "q_v13_sources1"}
    cols = {}
    for run_id, lib in RUNS:
        t = _tiers(eng, run_id)
        km = k0.loc[k0map[lib]]
        casc = _casc(cascade_src.get(lib, run_id))  # cascade DISPONIBLE (dryrun)
        ecartee_stored = int((t["tier"] == "ecartee").sum())  # écartées SERVIES par le run
        cols[lib] = {
            "AUC K0 (2025)": round(float(km["auc_global"]), 3),
            "préc@100 méd K0": round(float(km["prec@100_commune_mediane"]), 3),
            "lift décile K0": round(float(km["lift_decile_sup"]), 2),
            "Priorité préc K0": round(float(km["prec_priorite"]), 3),
            "ECE global K0": round(float(km["ece_global"]), 4),
            "ECE PM K0": round(float(km["ece_personne_morale"]), 4),
            "— run 2026 —": "",
            "brûlante (Priorité)": int((t["tier"] == "brulante").sum()),
            "chaude (À suivre)": int((t["tier"] == "chaude").sum()),
            "réserve foncière": int((t["tier"] == "reserve_fonciere").sum()),
            "à creuser": int((t["tier"] == "a_creuser").sum()),
            "cascade disponible (exclusions)": casc,
            "écartées servies par le run": ecartee_stored,
            "modèle K0 = ": k0map[lib],
        }
    tab = pd.DataFrame(cols)
    tab.to_csv(QDIR / "tableau5_le_tableau.csv")
    # markdown
    md = ["# LE tableau — SCORING-4 (format SCORING-2)", "",
          "Ce qui vient du **modèle** (q_v12) vs ce qui vient des **données** "
          "(q_v13_sources1), et les deux réunis (q_v14). K0 = banc 2025 (année "
          "vierge) ; run = distribution 2026.", "",
          "| métrique | " + " | ".join(lib for _, lib in RUNS) + " |",
          "|" + "---|" * (len(RUNS) + 1)]
    for metric in tab.index:
        md.append(f"| {metric} | " + " | ".join(str(tab.loc[metric, lib])
                                                 for _, lib in RUNS) + " |")
    md += ["",
           "**Lecture.** Le MODÈLE se lit sur les lignes K0 (AUC, préc@100, lift, "
           "Priorité préc, ECE) : q_v12 gagne sur le servi, q_v14 gagne encore. Les "
           "DONNÉES se lisent sur la *cascade disponible* : q_v13_sources1 porte les "
           "+4 378 exclusions neuves de SOURCES-1 (150 260 vs 145 882), que q_v14 "
           "réutilise. q_v14 combine les deux : meilleures métriques K0 ET la cascade "
           "élargie (écartées servies = 150 260).",
           "",
           "> Nuance de fidélité : le run `q_v13_sources1` a été scoré par SOURCES-1 "
           "sur l'étage 0 **servi** (145 882 écartées servies), sans l'override — sa "
           "cascade neuve (150 260) ne vivait que dans `dryrun_parcel_evaluations`. "
           "q_v14 l'a explicitement réutilisée (`LABUSE_ETAGE0_RUN=q_v13_sources1`) : "
           "ses écartées servies sont bien 150 260.",
           ]
    (QDIR / "tableau5_le_tableau.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


def paliers(eng) -> None:
    """Effectifs par palier (tête), île entière + Saint-Paul (97415)."""
    rows = []
    for run_id, lib in RUNS:
        t = _tiers(eng, run_id)
        for zone, sub in (("île", t), ("Saint-Paul (97415)", t[t["insee"] == SAINT_PAUL])):
            rows.append({"run": lib, "zone": zone,
                         "brûlante_Priorité": int((sub["tier"] == "brulante").sum()),
                         "chaude_À_suivre": int((sub["tier"] == "chaude").sum()),
                         "réserve_foncière": int((sub["tier"] == "reserve_fonciere").sum()),
                         "n_total": int(len(sub))})
    out = pd.DataFrame(rows)
    out.to_csv(QDIR / "tableau5_paliers.csv", index=False)
    print(out.to_string(index=False))


def _raisons_fr(top5_json) -> list[str]:
    """Les 3 premières contributions POSITIVES en français.

    Le libellé est relu de LIBELLES_QV14 par clé de feature (jamais du `libelle`
    gelé au run) : les corrections de libellé PALIERS-1 A0 (« terrain nu
    constructible », « secteur peu bâti ») s'affichent sans rescoring."""
    items = top5_json or []
    out = []
    for e in items:
        if e.get("signe") == "-" or e.get("log_hazard", 0) <= 0:
            continue
        lib = LIBELLES_QV14.get(e.get("feature"), e.get("libelle"))
        out.append(f"{lib} (+{e['log_hazard']:.2f})")
        if len(out) == 3:
            break
    while len(out) < 3:
        out.append("—")
    return out


def top50(eng) -> None:
    """Les 50 premières parcelles PAR RANG (p le plus fort) du candidat q_v14, chacune
    avec ses trois raisons en français, face à son rang/palier dans le servi.

    NB (PALIERS-1 A0, point 2) : c'est une liste PAR RANG, pas « les 50 premières
    Priorité ». Un rang de tête peut être DÉCLASSÉ (bâti saturé, etc.) : la colonne
    `palier_q_v14` le montre — ex. 97416000CS0269 (rang 3, p 0,60) reste « Faible »
    car la garde bâti saturé tient. C'est le cas exact que PALIERS-1 corrige (le
    déclassement devient un MOTIF, la parcelle garde son palier de probabilité)."""
    cand = pd.read_sql(
        "SELECT parcelle_id AS idu, rang, p_raw, tier, top5_contributions "
        "FROM parcel_p_score_v2 WHERE run_id = 'q_v14' AND NOT copro "
        "ORDER BY rang LIMIT 50", eng)
    servi = pd.read_sql(
        f"SELECT parcelle_id AS idu, rang AS rang_servi, tier AS tier_servi "
        f"FROM parcel_p_score_v2 WHERE run_id = '{SERVED_RUN}'", eng).set_index("idu")
    rows = []
    for _, r in cand.iterrows():
        t5 = r["top5_contributions"]
        if isinstance(t5, str):
            t5 = json.loads(t5)
        raisons = _raisons_fr(t5)
        s = servi.loc[r["idu"]] if r["idu"] in servi.index else None
        rows.append({
            "rang_q_v14": int(r["rang"]), "idu": r["idu"],
            "p_q_v14": round(float(r["p_raw"]), 5),
            "palier_q_v14": court(r["tier"]) or r["tier"],
            "rang_servi": int(s["rang_servi"]) if s is not None and pd.notna(s["rang_servi"]) else None,
            "palier_servi": court(s["tier_servi"]) or s["tier_servi"] if s is not None else "absent",
            "raison_1": raisons[0], "raison_2": raisons[1], "raison_3": raisons[2],
        })
    out = pd.DataFrame(rows)
    out.to_csv(QDIR / "tableau5_top50.csv", index=False)
    print(out.head(15).to_string(index=False))
    n_decl = int((out["palier_q_v14"] == "Faible").sum())
    n_pcpm = out[["raison_1", "raison_2", "raison_3"]].apply(
        lambda r: any("professionnel a déposé" in str(x) for x in r), axis=1).sum()
    print(f"\n… {n_pcpm}/50 des 50 premières par rang citent « un professionnel a "
          "déposé un permis sur cette parcelle détenue par un particulier ».")
    print(f"… {n_decl}/50 sont DÉCLASSÉES (palier « Faible ») malgré un p de tête — "
          "gardées hors Priorité par la garde actuelle (cas corrigé par PALIERS-1).")


def migration(eng) -> None:
    """Migrations de palier servi → q_v14 : combien changent, et lesquelles MONTENT
    en tête grâce au signal « permis d'un pro »."""
    servi = _tiers(eng, SERVED_RUN)[["idu", "tier"]].rename(columns={"tier": "tier_servi"})
    cand = pd.read_sql(
        "SELECT parcelle_id AS idu, tier, top5_contributions "
        "FROM parcel_p_score_v2 WHERE run_id = 'q_v14'", eng).rename(columns={"tier": "tier_q_v14"})
    m = cand.merge(servi, on="idu", how="left")
    m["palier_servi"] = m["tier_servi"].map(lambda t: court(t) or t)
    m["palier_q_v14"] = m["tier_q_v14"].map(lambda t: court(t) or t)
    change = m[m["palier_servi"] != m["palier_q_v14"]]

    # matrice de migration (têtes + écartée + à creuser)
    def cls(p):
        return p if p in ("Priorité", "À suivre") else (
            "écartée" if p == "ecartee" else "autre/à creuser")
    m["cs"] = m["palier_servi"].map(cls)
    m["cc"] = m["palier_q_v14"].map(cls)
    mat = pd.crosstab(m["cs"], m["cc"])
    mat.to_csv(QDIR / "tableau5_migration_matrice.csv")

    # montées en TÊTE (À suivre/autre → Priorité) portées par « permis d'un pro »
    def a_pcpm(t5):
        if isinstance(t5, str):
            t5 = json.loads(t5)
        return any(e.get("feature") == "pc_pm_sur_parcelle_pp_36m"
                   and e.get("log_hazard", 0) > 0 for e in (t5 or []))
    montees = m[(m["palier_q_v14"] == "Priorité") & (m["palier_servi"] != "Priorité")].copy()
    montees["porte_permis_pro"] = montees["top5_contributions"].map(a_pcpm)
    # détail GRANULAIRE des montées par palier servi (PALIERS-1 A0, point 2) : la
    # matrice repliée montre « autre/à creuser » ; ici on tranche — zéro depuis Faible
    # (les déclassées ne montent PAS en Priorité, la garde de tête tient).
    par_palier = (montees["palier_servi"].value_counts()
                  .rename_axis("palier_servi").reset_index(name="n"))
    resume = {
        "n_parcelles_changent_de_palier": int(len(change)),
        "montees_vers_Priorite": int(len(montees)),
        "dont_portees_par_permis_pro": int(montees["porte_permis_pro"].sum()),
        "montees_par_palier_servi": {str(r.palier_servi): int(r.n)
                                     for r in par_palier.itertuples()},
    }
    montees[montees["porte_permis_pro"]][["idu", "palier_servi"]].to_csv(
        QDIR / "tableau5_montees_permis_pro.csv", index=False)
    (QDIR / "tableau5_migration.json").write_text(
        json.dumps(resume, indent=2, ensure_ascii=False), encoding="utf-8")
    print(mat.to_string())
    print("\n" + json.dumps(resume, indent=2, ensure_ascii=False))


def ecarte(eng) -> None:
    """Ce qui est écarté et pourquoi : l'étage 0 (cascade q_v13_sources1 réutilisée)
    et les tiers déclassés du run q_v14."""
    t = _tiers(eng, "q_v14")
    dist = t["tier"].value_counts().rename_axis("tier").reset_index(name="n")
    dist["famille"] = dist["tier"].map(lambda x: (
        "écartée étage 0 (cascade q_v13_sources1)" if x == "ecartee"
        else "déclassée (garde de tête)" if str(x).startswith("declasse")
        else "servie"))
    dist.to_csv(QDIR / "tableau5_ecarte.csv", index=False)
    print(dist.to_string(index=False))


def main() -> None:
    eng = engine()
    print("\n===== LE TABLEAU =====")
    le_tableau(eng)
    print("\n===== PALIERS (île + Saint-Paul) =====")
    paliers(eng)
    print("\n===== TOP-50 PRIORITÉ q_v14 =====")
    top50(eng)
    print("\n===== MIGRATIONS DE PALIER =====")
    migration(eng)
    print("\n===== ÉCARTÉ =====")
    ecarte(eng)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "main"
    {"main": main, "tableau": lambda: le_tableau(engine()),
     "paliers": lambda: paliers(engine()), "top50": lambda: top50(engine()),
     "migration": lambda: migration(engine()), "ecarte": lambda: ecarte(engine())}[cmd]()
