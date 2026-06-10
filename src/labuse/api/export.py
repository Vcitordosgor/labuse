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

    cv = _comparables_view(fiche)
    if cv:
        lines += [
            "## Comparables de prix utilisés (transparence)", "",
            "_Prix de marché (DVF géolocalisé). **Simulation indicative** — le bilan complet reste "
            "à valider avec les hypothèses travaux, marge, frais, TVA, VRD, stationnement et aléas._", "",
            f"- **Prix retenu :** {cv['retenu']}",
            f"- **Médiane ancien :** {cv['ancien']}",
            f"- **Médiane neuf / VEFA :** {cv['vefa']}",
            f"- **Écart neuf vs ancien :** {cv['ecart']}",
            f"- **Fiabilité du prix :** {cv['fiabilite']}", "",
        ]

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
    cv = _comparables_view(fiche)
    comp_html = ("" if not cv else
                 "<h2>Comparables de prix utilisés (transparence)</h2>"
                 "<p class='disc'>Prix de marché (DVF géolocalisé). <strong>Simulation indicative</strong> — "
                 "le bilan complet reste à valider avec les hypothèses travaux, marge, frais, TVA, VRD, "
                 "stationnement et aléas.</p><ul>"
                 f"<li><strong>Prix retenu :</strong> {html.escape(cv['retenu'])}</li>"
                 f"<li><strong>Médiane ancien :</strong> {html.escape(cv['ancien'])}</li>"
                 f"<li><strong>Médiane neuf / VEFA :</strong> {html.escape(cv['vefa'])}</li>"
                 f"<li><strong>Écart neuf vs ancien :</strong> {html.escape(cv['ecart'])}</li>"
                 f"<li><strong>Fiabilité du prix :</strong> {html.escape(cv['fiabilite'])}</li></ul>")
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
{comp_html}
{"<h2>Analyse LA BUSE (IA)</h2><p>" + html.escape(ai.get('executive_summary','')) + "</p>" if ai else ""}
</html>"""


def _score(x) -> str:
    return "—" if x is None else str(x)


def _m2(x) -> str:
    return "—" if x is None else f"{x:,.0f} m²".replace(",", " ")


def _eurm2(x) -> str:
    return "—" if x is None else f"{x:,.0f} €/m²".replace(",", " ")


def _comparables_view(fiche: dict) -> dict | None:
    """Vue d'affichage du bloc « Comparables de prix utilisés » (transparence neuf/ancien).

    Reprend tel quel le moteur de prix (aucune invention) ; None si pas de bilan chiffré.
    Le bloc est volontairement formulé en « prix de marché » + « simulation indicative ».
    """
    b = ((fiche.get("faisabilite") or {}).get("bilan")) or {}
    c, px = b.get("comparables"), (b.get("prix_dvf") or {})
    if not c or not b.get("fiable"):
        return None
    fia = {"fiable": "Prix de marché fiable", "fragile": "Prix de marché fragile"}.get(
        c.get("fiabilite_prix"), "Prix de marché " + str(c.get("fiabilite_prix") or "—"))
    per = px.get("periode") or []
    rayon = "commune" if px.get("commune_fallback") else (
        f"{px['radius_m']:.0f} m" if px.get("radius_m") else "—")
    retenu = f"{_eurm2(px.get('median'))} · {px.get('type_prix', '')} · {px.get('n', '?')} ventes"
    if len(per) == 2:
        retenu += f" · {per[0]}-{per[1]} · {rayon}"
    ancien = (f"{_eurm2(c['mediane_ancien'])} ({c['n_ancien']} ventes)"
              if c.get("mediane_ancien") is not None
              else (f"{c['n_ancien']} vente(s), trop peu" if c.get("n_ancien") else "aucune"))
    vefa = (f"{_eurm2(c['mediane_vefa'])} ({c['n_vefa']} ventes)"
            if c.get("mediane_vefa") is not None
            else (c.get("note") or (f"{c['n_vefa']} vente(s), trop peu" if c.get("n_vefa") else "aucune")))
    ecart = (f"{'+' if (c['ecart_vefa_ancien_pct'] or 0) >= 0 else ''}{c['ecart_vefa_ancien_pct']} % (neuf vs ancien)"
             if c.get("exploitable") else (c.get("note") or "non exploitable"))
    return {"retenu": retenu, "ancien": ancien, "vefa": vefa, "ecart": ecart, "fiabilite": fia}
