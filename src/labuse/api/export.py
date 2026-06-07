"""Export « fiche premium » (brief §8/§12 étape 10) — Markdown & HTML.

Rend la fiche assemblée par l'API en un document sobre, B2B, prêt à transmettre.
Chaque information reste tracée à sa source ; la non-garantie est rappelée.
"""
from __future__ import annotations

import html

_RESULT_LABEL = {
    "HARD_EXCLUDE": "EXCLUSION", "SOFT_FLAG": "contrainte", "POSITIVE": "signal +",
    "PASS": "ok", "UNKNOWN": "donnée manquante",
}


def fiche_markdown(fiche: dict) -> str:
    p = fiche["parcel"]
    v = fiche["verdict"]
    lines = [
        f"# LA BUSE — Fiche parcelle {p['idu']}",
        "",
        f"> {fiche['disclaimer']}",
        "",
        f"**Commune :** {p.get('commune') or '—'}  ·  **Surface :** {_m2(p.get('surface_m2'))}  ·  "
        f"**Section/№ :** {p.get('section') or '—'} {p.get('numero') or ''}",
        "",
        "## Verdict",
        "",
        f"- **Statut :** {v['status'] or '—'}",
        f"- **Opportunité :** {_score(v['opportunity_score'])} / 100  ·  "
        f"**Complétude :** {_score(v['completeness_score'])} / 100",
        "",
    ]
    if v["reasons"]:
        lines.append("**Raisons (exclusion / réserve) :**")
        lines += [f"- _{_RESULT_LABEL.get(r['result'], r['result'])}"
                  f"{('/' + r['severity']) if r.get('severity') else ''}_ — {r['detail']}  "
                  f"({r['source'] or 'n/d'})" for r in v["reasons"]]
        lines.append("")

    lines += ["## Cascade — traçabilité complète", "",
              "| Couche | Verdict | Sévérité | Détail | Source |",
              "|---|---|---|---|---|"]
    for r in fiche["cascade"]:
        lines.append(
            f"| {r['layer_name']} | {_RESULT_LABEL.get(r['result'], r['result'])} | "
            f"{r['severity'] or ''} | {r['detail']} | {r['source'] or 'n/d'} |"
        )
    lines.append("")

    lines += ["## Sources", "",
              f"**Ont répondu :** {', '.join(fiche['sources_responded']) or '—'}", "",
              f"**Silencieuses (donnée manquante) :** {', '.join(fiche['sources_silent']) or '—'}", ""]

    ai = fiche.get("ai")
    if ai:
        lines += ["## Analyse LA BUSE (IA)", "",
                  f"_{ai.get('executive_summary', '')}_", "",
                  f"- **Statut recommandé :** {ai.get('recommended_status')}  ·  "
                  f"**Confiance :** {ai.get('confidence_level')}", ""]
        if ai.get("reunion_specific_flags"):
            lines.append("**Spécificités réunionnaises :** " + "; ".join(ai["reunion_specific_flags"]))
            lines.append("")
        if ai.get("must_check_before_showing_developer"):
            lines.append("**À vérifier avant de montrer à un promoteur :**")
            lines += [f"- {c}" for c in ai["must_check_before_showing_developer"]]
            lines.append("")
    return "\n".join(lines)


def fiche_html(fiche: dict) -> str:
    p, v = fiche["parcel"], fiche["verdict"]
    rows = "".join(
        f"<tr><td>{html.escape(r['layer_name'])}</td>"
        f"<td>{html.escape(_RESULT_LABEL.get(r['result'], r['result']))}</td>"
        f"<td>{html.escape(r['severity'] or '')}</td>"
        f"<td>{html.escape(r['detail'])}</td>"
        f"<td class='src'>{html.escape(r['source'] or 'n/d')}</td></tr>"
        for r in fiche["cascade"]
    )
    reasons = "".join(f"<li>{html.escape(r['detail'])} <span class='src'>({html.escape(r['source'] or 'n/d')})</span></li>"
                      for r in v["reasons"]) or "<li>—</li>"
    ai = fiche.get("ai") or {}
    return f"""<!doctype html><html lang="fr"><meta charset="utf-8">
<title>LA BUSE — {html.escape(p['idu'])}</title>
<style>
 body{{font:15px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;color:#1a1a1a;max-width:880px;margin:2rem auto;padding:0 1rem}}
 h1{{font-size:1.5rem;letter-spacing:.02em}} h2{{font-size:1.05rem;margin-top:1.8rem;border-bottom:1px solid #eee;padding-bottom:.3rem}}
 .disc{{color:#777;font-style:italic;font-size:.9rem}} .score{{font-weight:600}}
 table{{border-collapse:collapse;width:100%;font-size:.9rem}} td,th{{border:1px solid #e5e5e5;padding:.35rem .5rem;text-align:left;vertical-align:top}}
 .src{{color:#888;font-size:.85em}} .badge{{display:inline-block;padding:.15rem .6rem;border-radius:.4rem;background:#111;color:#fff;font-size:.85rem}}
</style>
<h1>LA BUSE — Fiche parcelle {html.escape(p['idu'])}</h1>
<p class="disc">{html.escape(fiche['disclaimer'])}</p>
<p><strong>Commune :</strong> {html.escape(p.get('commune') or '—')} ·
   <strong>Surface :</strong> {_m2(p.get('surface_m2'))} ·
   <strong>Section/№ :</strong> {html.escape((p.get('section') or '—'))} {html.escape(p.get('numero') or '')}</p>
<h2>Verdict</h2>
<p><span class="badge">{html.escape(v['status'] or '—')}</span></p>
<p class="score">Opportunité {_score(v['opportunity_score'])}/100 · Complétude {_score(v['completeness_score'])}/100</p>
<p><strong>Raisons :</strong></p><ul>{reasons}</ul>
<h2>Cascade — traçabilité</h2>
<table><tr><th>Couche</th><th>Verdict</th><th>Sévérité</th><th>Détail</th><th>Source</th></tr>{rows}</table>
<h2>Sources</h2>
<p><strong>Ont répondu :</strong> {html.escape(', '.join(fiche['sources_responded']) or '—')}</p>
<p><strong>Silencieuses :</strong> {html.escape(', '.join(fiche['sources_silent']) or '—')}</p>
{"<h2>Analyse LA BUSE (IA)</h2><p>" + html.escape(ai.get('executive_summary','')) + "</p>" if ai else ""}
</html>"""


def _score(x) -> str:
    return "—" if x is None else str(x)


def _m2(x) -> str:
    return "—" if x is None else f"{x:,.0f} m²".replace(",", " ")
