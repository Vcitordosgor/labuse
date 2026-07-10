"""Rapport de fin de session Score V (format imposé §9) → reports/score-v/rapport-final.md.

Généré depuis la base (idempotent, relançable) : signaux GO/NO-GO, stats matching,
distribution V + Brûlantes (garde-fou D3 : si hors [30-120], PROPOSE un seuil ajusté —
méthode top décile V des chaudes — sans jamais changer le seuil silencieusement),
coverage/owner_type, top 20 Brûlantes, résultat backtest, screenshots, caveats.

Usage : LABUSE_DATABASE_URL=… .venv/bin/python scripts/score-v/rapport_final.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from sqlalchemy import text  # noqa: E402

from labuse.db import session_scope  # noqa: E402
from labuse.scoring.score_v_constants import (  # noqa: E402
    BRULANTE_GUARDRAIL,
    Q_A_RUN_LABEL,
    V_BRULANTE_THRESHOLD,
)

OUT = Path(__file__).resolve().parents[2] / "reports" / "score-v"


def main() -> None:
    md: list[str] = ["# Score V (Vendabilité) — rapport de fin de session\n",
                     "*Branche `feat/labuse-score-v` — barème v1 verrouillé (D1), seuil Brûlante "
                     f"= {V_BRULANTE_THRESHOLD} (D3), run Q×A de référence `{Q_A_RUN_LABEL}`.*\n"]
    with session_scope() as s:
        one = lambda q, p=None: s.execute(text(q), p or {}).mappings().one()  # noqa: E731
        all_ = lambda q, p=None: s.execute(text(q), p or {}).mappings().all()  # noqa: E731

        # 1. GO/NO-GO — verdicts Phase 0 consolidés avec l'état final des données
        n_dvf = one("SELECT count(*) AS n, count(DISTINCT id_parcelle) AS p FROM dvf_mutations_parcelle")
        n_bod = one("SELECT count(*) AS n, count(DISTINCT siren) AS s FROM bodacc_annonces_owner")
        n_enr = one("SELECT count(*) AS n, count(*) FILTER (WHERE NOT (payload ? 'not_found')) AS ok "
                    "FROM owner_enrichment")
        n_dpe = one("SELECT count(*) FILTER (WHERE etiquette_dpe IN ('F','G') AND parcelle_idu IS NOT NULL) AS fg "
                    "FROM dpe_records")
        md += ["## 1. Signaux GO/NO-GO\n",
               "| Signal / famille | Verdict | Détail |", "|---|---|---|",
               f"| A — BODACC (LJ/RJ/sauvegarde/radiation/cession) | **GO** | {n_bod['n']} annonces "
               f"× SIREN cachées ({n_bod['s']} SIREN à annonce ≥ 1, familles collective+radiation+vente) |",
               f"| B — RNE / recherche-entreprises (cessation, âge, SCI dormante) | **GO** | "
               f"{n_enr['ok']}/{n_enr['n']} SIREN enrichis (état administratif, dirigeants, siège) ; "
               "731 gigognes INPI non résolues (429) sans signal âge |",
               "| C — Détachement géographique | **GO** (via siège recherche-entreprises — pas d'adresse "
               "dans DGFiP PM) | |",
               f"| D — Dormance (friche, tenure, terrain nu) | **GO partiel** | `DVF_TENURE_12`/`_8` "
               f"**NO-GO** (millésimes 2014-2020 retirés de la distribution DGFiP) → variante dégradée "
               f"`DVF_TENURE_OBS5` 8 pts validée au GO Phase 0. Géo-DVF parcelle : {n_dvf['n']} lignes / "
               f"{n_dvf['p']} parcelles (2021-2025) |",
               f"| E — DPE (pression réglementaire, calendrier DOM 2028/2031) | **GO best-effort** | "
               f"base ADEME 974 intrinsèquement mince : {n_dpe['fg']} DPE F/G rattachés parcelle |\n"]

        # 2. Matching
        m = one("""
            SELECT count(*) AS liens,
                   count(*) FILTER (WHERE v.v_confidence = 1.0 AND v.owner_siren IS NOT NULL) AS direct,
                   count(*) FILTER (WHERE v.v_confidence = 0.8) AS fallback
            FROM parcelle_personne_morale pm JOIN parcel_v_score v ON v.parcelle_id = pm.idu""")
        rq = one("SELECT count(*) AS n FROM matching_review_queue")
        lk = one("SELECT count(*) FILTER (WHERE status='found') AS f, "
                 "count(*) FILTER (WHERE status='ambiguous') AS a, "
                 "count(*) FILTER (WHERE status='not_found') AS nf FROM owner_denom_lookup")
        pct = lambda n, d: f"{100.0 * n / d:.1f} %" if d else "—"  # noqa: E731
        md += ["## 2. Stats matching (liens parcelle ↔ propriétaire)\n",
               f"- Liens DGFiP PM : **{m['liens']}** — SIREN direct : **{m['direct']}** "
               f"({pct(m['direct'], m['liens'])}), fallback dénomination : **{m['fallback']}** "
               f"({pct(m['fallback'], m['liens'])}).",
               f"- Lookups dénomination : {lk['f']} résolues, {lk['a']} ambiguës, {lk['nf']} introuvables.",
               f"- **Review queue : {rq['n']} lignes** (matchs ambigus, à arbitrer humainement).\n"]

        # 3. Distribution V + Brûlantes + garde-fou D3
        bands = {r["v_band"]: r["n"] for r in all_(
            "SELECT COALESCE(v_band,'na') AS v_band, count(*) AS n FROM parcel_v_score GROUP BY 1")}
        total = sum(bands.values())
        brul = one(f"SELECT count(*) AS n FROM v_parcelles_brulantes")["n"]  # noqa: F541
        md += ["## 3. Distribution V + Brûlantes 🔥\n",
               "| Bande | Parcelles | % |", "|---|---|---|"]
        bar = lambda n: "█" * max(1, round(40.0 * n / max(bands.values())))  # noqa: E731
        for b, label in [("fort", "Signal fort (50-100)"), ("present", "Signaux présents (25-49)"),
                         ("faible", "Signal faible (1-24)"), ("aucun", "Aucun signal (0)"),
                         ("na", "N.A. (public/bailleur)")]:
            n = bands.get(b, 0)
            md.append(f"| {label} | {n} `{bar(n)}` | {pct(n, total)} |")
        lo, hi = BRULANTE_GUARDRAIL
        md.append(f"\n**Brûlantes = {brul}** (chaude Q×A ∧ V ≥ {V_BRULANTE_THRESHOLD}, vue dynamique "
                  "`v_parcelles_brulantes`).")
        if not (lo <= brul <= hi):
            dec = one(f"""
                SELECT percentile_cont(0.9) WITHIN GROUP (ORDER BY v.v_score) AS p90
                FROM parcel_v_score v JOIN parcels p ON p.idu = v.parcelle_id
                JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = '{Q_A_RUN_LABEL}'
                WHERE d.matrice_statut = 'chaude' AND v.v_score IS NOT NULL""")
            prop = int(dec["p90"] or 0)
            n_prop = one(f"""
                SELECT count(*) AS n FROM parcel_v_score v JOIN parcels p ON p.idu = v.parcelle_id
                JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = '{Q_A_RUN_LABEL}'
                WHERE d.matrice_statut = 'chaude' AND v.v_score >= :t""", {"t": prop})["n"]
            md.append(f"\n⚠ **Garde-fou D3 : {brul} Brûlantes hors de l'intervalle [{lo}-{hi}].** "
                      f"Le seuil n'a PAS été changé. **Proposition** (méthode top décile V des chaudes) : "
                      f"`V_BRULANTE_THRESHOLD = {prop}` → {n_prop} Brûlantes. Décision Vic.")
        md.append("")

        # 4. Coverage & owner_type
        cov = {r["v_coverage"]: r["n"] for r in all_(
            "SELECT v_coverage, count(*) AS n FROM parcel_v_score GROUP BY 1")}
        md += ["## 4. Coverage & type de propriétaire\n",
               f"- `full` (propriétaire PM matché, 5 familles) : **{cov.get('full', 0)}** "
               f"({pct(cov.get('full', 0), total)}) ; `partial` (familles D+E) : **{cov.get('partial', 0)}**.",
               "\n| owner_type | Parcelles |", "|---|---|"]
        for r in all_("SELECT COALESCE(owner_type,'pp') AS t, count(*) AS n FROM parcel_v_score "
                      "GROUP BY 1 ORDER BY 2 DESC"):
            md.append(f"| {r['t']} | {r['n']} |")
        md.append("")

        # 5. Top 20 Brûlantes
        md += ["## 5. Top 20 Brûlantes 🔥\n",
               "| Parcelle | Commune | Q | A | V | Propriétaire | Signaux |", "|---|---|---|---|---|---|---|"]
        for r in all_("""
            SELECT b.idu, b.commune, b.q_score, b.a_score, b.v_score, b.owner_denomination,
                   (SELECT string_agg(s->>'label', ' · ') FROM (
                      SELECT s FROM jsonb_array_elements(b.signals) s
                      ORDER BY (s->>'points')::int DESC LIMIT 3) t(s)) AS sig
            FROM v_parcelles_brulantes b ORDER BY b.v_score DESC, b.q_score DESC LIMIT 20"""):
            md.append(f"| `{r['idu']}` | {r['commune']} | {r['q_score']} | {r['a_score']} | "
                      f"**{r['v_score']}** | {(r['owner_denomination'] or '—')[:40]} | {r['sig'] or ''} |")
        md.append("")

    # 6. Backtest (lit le livrable Phase 5)
    bt = OUT / "backtest.md"
    md += ["## 6. Backtest\n"]
    if bt.exists():
        txt = bt.read_text()
        lift = re.search(r"lift top décile = \*\*([\d.]+)×\*\*", txt)
        md.append(f"Lift top décile : **{lift.group(1)}×** (cible ≥ 2×) — détail complet : "
                  "[backtest.md](backtest.md) (+ CSV cohorte, graphe SVG).")
        if lift and float(lift.group(1)) < 1.5:
            md.append("\n🔴 **LIFT < 1.5× : poids à retravailler avant tout usage commercial du score.**")
    else:
        md.append("⚠ Mode dégradé : backtest non exécuté — voir spot-check (backtest indisponible).")
    md.append("")

    # 7. Screenshots
    shots = sorted((OUT / "screenshots").glob("*.png")) if (OUT / "screenshots").exists() else []
    md += ["## 7. Screenshots (375 / 768 / 1440)\n"]
    md += [f"- [{p.name}](screenshots/{p.name})" for p in shots] or ["⚠ Aucune capture trouvée."]

    # 8. Caveats & dette
    md += ["\n## 8. Caveats & dette (v1.1)\n",
           "- **DVF 2014-2020 retirés** de la distribution officielle → tenure = fenêtre observable "
           "5 ans (`DVF_TENURE_OBS5`, 8 pts, validé au GO). Un futur mandat data étendra "
           "`dvf_mutations_parcelle` (médianes €/m² par secteur) — ne rien jeter.",
           "- **DGFiP PM millésime 2025** : fuite temporelle possible au backtest (l'acheteur peut déjà "
           "figurer au fichier) — documentée dans backtest.md.",
           "- **SCI dormante** : proxy `date_mise_a_jour_rne` (pas d'historique d'événements RNE public).",
           "- **731 gigognes INPI** non résolues (quota 429) → pas de signal âge ; reprendre "
           "`labuse ingest-inpi-gigogne` un autre jour.",
           "- **Badges V sur carte** : mode commune (GeoJSON) seulement — les tuiles MVT île ne portent "
           "pas encore v_score (régénération des tuiles à planifier).",
           "- **Grands groupes nationaux** (ex. ORANGE dans le top Brûlantes : « dirigeant ≥ 75 ans » "
           "d'un conseil d'administration + cession d'une boutique) : signaux techniquement exacts mais "
           "non pertinents pour un foncier stratégique — filtre catégorie d'entreprise (GE/ETI) à "
           "prévoir avec le raffinement D5.",
           "- v1.1 : raffinement PM promoteurs/marchands de biens (D5), diff quotidien BODACC, LOVAC.",
           "\n---\n*Aucun merge effectué — validation visuelle puis merge `--no-ff` par Vic.*"]

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "rapport-final.md").write_text("\n".join(md))
    print(f"→ {OUT / 'rapport-final.md'}")


if __name__ == "__main__":
    main()
