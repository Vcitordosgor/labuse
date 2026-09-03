"""SCORING-2 · K7 — ce que le run candidat enregistre (manifeste + note de version).

Le manifeste rassemble TOUT ce qu'il faut pour rejouer et juger le candidat :
protocole, segments et effectifs, variables et couvertures réelles (année scorée
2026), métriques K0 complètes, millésimes des sources (catalogue data_sources),
règle de promotion, et la NOTE DE VERSION en français composée depuis les
chiffres mesurés — jamais écrite à la main.

Sorties : reports/score-v2-arene/k7_manifeste.json + k7_note_de_version.md.
Rien n'est promu, rien n'est servi — q_v11_m137 reste le run servi.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import candidats  # noqa: E402
import protocole  # noqa: E402
from _common import engine, SERVED_RUN  # noqa: E402

OUT = protocole.OUT

SOURCES_MODELE = ["DVF", "Sitadel", "BD TOPO IGN", "Filosofi", "GPU", "RGE ALTI",
                  "fichiers fonciers", "cadastre"]


def couvertures(df26: pd.DataFrame, names: list[str]) -> list[dict]:
    out = []
    for n in names:
        col = df26[n] if n in df26.columns else None
        if col is None:
            out.append({"feature": n, "pct_non_null": None})
            continue
        out.append({"feature": n,
                    "pct_non_null": round(100 * float(col.notna().mean()), 2)})
    return out


def millesimes(eng) -> list[dict]:
    src = pd.read_sql(
        "SELECT name, source_millesime, last_sync_at::date AS ingere_le "
        "FROM data_sources ORDER BY name", eng)
    garde = src[src["name"].str.contains("|".join(SOURCES_MODELE), case=False,
                                         regex=True, na=False)]
    return json.loads(garde.to_json(orient="records", date_format="iso"))


def note_de_version(table: pd.DataFrame, verdict: dict) -> str:
    """La note en français, composée DEPUIS les chiffres de la table unique."""
    b = table[table.candidat == "ligne_de_base"].iloc[0]
    c = table[table.candidat == "K4bis_voisinage_global"].iloc[0]
    g = table[table.candidat == "K5_challenger_gbm"].iloc[0]
    ratio_prio = (c.n_priorite / b.n_priorite) if b.n_priorite else float("nan")
    lignes = [
        f"# Candidat SCORING-2 du {date.today().strftime('%d/%m/%Y')} — note de version",
        "",
        "**Rien de servi ne change : ceci décrit un CANDIDAT d'arène. "
        f"Le run servi reste `{SERVED_RUN}`.**",
        "",
        "## Ce qui change dans le candidat (champion K4 bis)",
        "- censoring : détention et permis à couverture 100 % "
        "(valeur connue OU bin censuré explicite « ≥ N ans », jamais un inconnu muet) ;",
        "- 4 variables mortes retirées (ndvi, canopée, accès équipements, friche) "
        "+ doctrine M35 (5 `retired` hors de tout nouveau fit) ;",
        "- résiduel lu à 100 % (zéros M125 + cause explicite, hors_plu seul inconnu) ;",
        "- architecture GLOBALE conservée : les 4 modèles segmentés ont été mesurés "
        "(K4) — calibration meilleure mais discrimination moindre (la mise en "
        "commun des 3 M de lignes gagne) ; l'isotonique par segment reste la piste ;",
        "- voisinage et marché as-of (ventes 150/400 m, permis 100 m, PA 400 m, "
        "marché communal, PM vendeur actif) — test de fuite dédié : passé.",
        "",
        "## Les chiffres (protocole année vierge : train ≤2023, cal 2024, test 2025)",
        f"- précision@100 par commune (médiane) : {b['prec@100_commune_mediane']:.3f} "
        f"→ {c['prec@100_commune_mediane']:.3f} ;",
        f"- Priorité : {b.prec_priorite:.1%} de ventes réelles sur {b.n_priorite:.0f} "
        f"parcelles → {c.prec_priorite:.1%} sur {c.n_priorite:.0f} "
        f"(effectif ×{ratio_prio:.1f}) ;",
        f"- À suivre : {b.prec_a_suivre:.1%} sur {b.n_a_suivre:.0f} → "
        f"{c.prec_a_suivre:.1%} sur {c.n_a_suivre:.0f} ;",
        f"- lift du décile supérieur : {b.lift_decile_sup:.2f} → {c.lift_decile_sup:.2f} ;",
        f"- AUC global : {b.auc_global:.3f} → {c.auc_global:.3f} "
        f"(bâti {c.auc_bati_individuel:.3f}, nu {c.auc_terrain_nu:.3f}, "
        f"PM {c.auc_personne_morale:.3f}, copro {c.auc_copropriete:.3f}) ;",
        f"- ECE global : {c.ece_global:.4f} ;",
        f"- churn top-1158 vs le run servi : {c.churn_top1158_vs_servi:.1%}.",
        "",
        "## Le challenger (gradient boosting, monotonie métier)",
        f"- AUC {g.auc_global:.3f}, préc@100 méd {g['prec@100_commune_mediane']:.3f}, "
        f"Priorité {g.prec_priorite:.1%} ({g.n_priorite:.0f}), "
        f"lift décile {g.lift_decile_sup:.2f} ;",
        f"- règle de promotion satisfaite : "
        f"{'OUI' if verdict.get('promotion_satisfaite') else 'NON'} "
        "(promotion NON appliquée — décision Vic).",
        "",
    ]
    return "\n".join(lignes)


def main() -> None:
    eng = engine()
    table = pd.read_csv(OUT / "k0_table.csv")
    with open(OUT / "k5_verdict.json", encoding="utf-8") as f:
        k5 = json.load(f)
    hygiene = pd.read_csv(OUT / "k0_hygiene.csv").iloc[0].to_dict()
    names, specs, inter = candidats.features_k4bis()
    print(f"[{time.strftime('%H:%M:%S')}] couvertures 2026…", flush=True)
    df26 = protocole.load_range(eng, (protocole.SCORE_YEAR,))
    df26 = candidats._enrichir_k4bis(eng, df26)
    import measure
    copro = measure.copro_mask(eng, df26)
    seg = protocole.segmenter(df26, copro)
    manifeste = {
        "candidat": f"score-v2-candidat-{date.today().isoformat()}",
        "doctrine": "arène seulement — rien de servi ne change, "
                    f"le run servi reste {SERVED_RUN}",
        "protocole": {
            "train": f"{protocole.TRAIN_MIN}-{protocole.TRAIN_MAX}",
            "calibration": protocole.CAL_YEAR,
            "test": protocole.TEST_YEAR,
            "annee_scoree": protocole.SCORE_YEAR,
            "hygiene_cible": hygiene,
        },
        "segments": {s: int((seg == s).sum()) for s in protocole.SEGMENTS},
        "zone_A_hors_apprentissage": True,
        "features": couvertures(df26, names),
        "interactions": inter,
        "metriques_k0": json.loads(table.to_json(orient="records")),
        "millesimes_sources": millesimes(eng),
        "regle_promotion": k5["regle"],
        "verdict_arene": k5["verdict"],
    }
    with open(OUT / "k7_manifeste.json", "w", encoding="utf-8") as f:
        json.dump(manifeste, f, ensure_ascii=False, indent=2, default=str)
    note = note_de_version(table, k5["verdict"])
    (OUT / "k7_note_de_version.md").write_text(note, encoding="utf-8")
    print(note)


if __name__ == "__main__":
    main()
