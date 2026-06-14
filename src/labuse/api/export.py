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
_STATUS_LABEL = {
    "opportunite": "Opportunité vérifiée", "a_creuser": "À creuser",
    "faux_positif_probable": "Faux positif probable", "exclue": "Exclue",
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

    rv = fiche.get("resume") or {}
    if rv.get("synthese"):
        lines += ["## Résumé opportunité", "",
                  f"**{rv.get('statut_label', '')}** — {rv['synthese']}", ""]
        if rv.get("positifs"):
            lines.append("**Pourquoi elle ressort :**")
            lines += [f"- {x}" for x in rv["positifs"]]
            lines.append("")
        if rv.get("vigilance"):
            lines.append("**À vérifier :**")
            lines += [f"- {x}" for x in rv["vigilance"]]
            lines.append("")
        if rv.get("prochaine_action"):
            lines += [f"**Prochaine action :** {rv['prochaine_action']}", ""]

    bt = fiche.get("bati") or {}
    if bt:
        lines += ["## Occupation actuelle (bâti détecté)", "", f"**{bt.get('label', '—')}**"]
        if bt.get("disponible"):
            lines.append(f"- Couverture bâtie : {bt.get('ratio_pct')} % · {bt.get('nb_batiments')} bâtiment(s)"
                         + (f" · plus grand : {bt.get('plus_grand_m2')} m²" if bt.get("plus_grand_m2") else ""))
        lines += [f"- Source : {bt.get('source')} · confiance : {bt.get('confiance')}", ""]

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

    vz = fiche.get("voisinage") or {}
    if vz.get("voisines"):
        lines += ["## Parcelles voisines (contiguïté)", ""]
        if (vz.get("assemblage") or {}).get("note"):
            lines += [f"_{vz['assemblage']['note']}_", ""]
        lines += ["| Parcelle | Statut LA BUSE | Opp. | Zone PLU | Surface |", "|---|---|---|---|---|"]
        for v in vz["voisines"]:
            lines.append(f"| {v['idu']} | {_STATUS_LABEL.get(v.get('status'), v.get('status') or '—')} | "
                         f"{v.get('opportunity_score') if v.get('opportunity_score') is not None else '—'} | "
                         f"{v.get('plu_zone') or '—'} | {_m2(v.get('surface_m2'))} |")
        lines += ["", "_Adjacence géométrique uniquement — propriétaires, accords et faisabilité d'un "
                  "assemblage restent à vérifier._", ""]

    pv = _prospection_view(fiche)
    lines += ["## Prospection propriétaire", "",
              f"- **Statut propriétaire :** {pv['statut']}",
              f"- **Source :** {pv['source']}  ·  **Niveau de confiance :** {pv['confiance']}"]
    lines.append(f"- **Contact (saisi manuellement) :** {pv['contact']}" if pv["contact"]
                 else "- **Contact :** Propriétaire à identifier — aucune donnée nominative disponible dans LA BUSE.")
    if pv["action"]:
        lines.append(f"- **Prochaine action :** {pv['action']}")
    if pv["responsable"]:
        lines.append(f"- **Responsable :** {pv['responsable']}")
    if pv["notes"]:
        lines.append(f"- **Notes :** {pv['notes']}")
    lines += ["", f"_{pv['disclaimer']}_", ""]

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
    rv = fiche.get("resume") or {}
    resume_html = ""
    if rv.get("synthese"):
        pos = "".join(f"<li>{html.escape(x)}</li>" for x in rv.get("positifs", [])) or "<li>—</li>"
        vig = "".join(f"<li>{html.escape(x)}</li>" for x in rv.get("vigilance", [])) or "<li>—</li>"
        resume_html = (
            "<h2>Résumé opportunité</h2>"
            f"<p><strong>{html.escape(rv.get('statut_label', ''))}</strong> — {html.escape(rv['synthese'])}</p>"
            f"<p><strong>Pourquoi elle ressort :</strong></p><ul>{pos}</ul>"
            f"<p><strong>À vérifier :</strong></p><ul>{vig}</ul>"
            f"<p><strong>Prochaine action :</strong> {html.escape(rv.get('prochaine_action', ''))}</p>")
    bt = fiche.get("bati") or {}
    bati_html = ""
    if bt:
        figs = (f"<li>Couverture bâtie : {bt.get('ratio_pct')} % · {bt.get('nb_batiments')} bâtiment(s)"
                + (f" · plus grand : {bt.get('plus_grand_m2')} m²" if bt.get("plus_grand_m2") else "")
                + "</li>") if bt.get("disponible") else ""
        bati_html = ("<h2>Occupation actuelle (bâti détecté)</h2>"
                     f"<p><strong>{html.escape(bt.get('label', '—'))}</strong></p><ul>{figs}"
                     f"<li>Source : {html.escape(str(bt.get('source')))} · "
                     f"confiance : {html.escape(str(bt.get('confiance')))}</li></ul>")
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
    vz = fiche.get("voisinage") or {}
    vz_html = ""
    if vz.get("voisines"):
        note = (vz.get("assemblage") or {}).get("note")
        rows_vz = "".join(
            f"<tr><td>{html.escape(v['idu'])}</td>"
            f"<td>{html.escape(_STATUS_LABEL.get(v.get('status'), v.get('status') or '—'))}</td>"
            f"<td>{v.get('opportunity_score') if v.get('opportunity_score') is not None else '—'}</td>"
            f"<td>{html.escape(v.get('plu_zone') or '—')}</td>"
            f"<td>{_m2(v.get('surface_m2'))}</td></tr>"
            for v in vz["voisines"])
        vz_html = ("<h2>Parcelles voisines (contiguïté)</h2>"
                   + (f"<p class='disc'>{html.escape(note)}</p>" if note else "")
                   + "<table><tr><th>Parcelle</th><th>Statut LA BUSE</th><th>Opp.</th><th>Zone PLU</th><th>Surface</th></tr>"
                   + rows_vz + "</table>"
                   "<p class='disc'>Adjacence géométrique uniquement — propriétaires, accords et "
                   "faisabilité d'un assemblage restent à vérifier.</p>")
    pv = _prospection_view(fiche)
    contact_li = (f"<li><strong>Contact (saisi manuellement) :</strong> {html.escape(pv['contact'])}</li>"
                  if pv["contact"] else
                  "<li><strong>Contact :</strong> Propriétaire à identifier — aucune donnée nominative "
                  "disponible dans LA BUSE.</li>")
    prosp_html = (
        "<h2>Prospection propriétaire</h2><ul>"
        f"<li><strong>Statut propriétaire :</strong> {html.escape(pv['statut'])}</li>"
        f"<li><strong>Source :</strong> {html.escape(pv['source'])} · "
        f"<strong>Niveau de confiance :</strong> {html.escape(pv['confiance'])}</li>"
        + contact_li
        + (f"<li><strong>Prochaine action :</strong> {html.escape(pv['action'])}</li>" if pv["action"] else "")
        + (f"<li><strong>Responsable :</strong> {html.escape(pv['responsable'])}</li>" if pv["responsable"] else "")
        + (f"<li><strong>Notes :</strong> {html.escape(pv['notes'])}</li>" if pv["notes"] else "")
        + f"</ul><p class='disc'>{html.escape(pv['disclaimer'])}</p>")
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
{resume_html}
{bati_html}
<h2>Cascade — traçabilité</h2>
<table><tr><th>Couche</th><th>Verdict</th><th>Sévérité</th><th>Détail</th><th>Source</th></tr>{rows}</table>
<h2>Sources</h2>
<p><strong>Ont répondu :</strong> {html.escape(', '.join(fiche['sources_responded']) or '—')}</p>
<p><strong>Silencieuses :</strong> {html.escape(', '.join(fiche['sources_silent']) or '—')}</p>
{comp_html}
{vz_html}
{prosp_html}
{"<h2>Analyse LA BUSE (IA)</h2><p>" + html.escape(ai.get('executive_summary','')) + "</p>" if ai else ""}
</html>"""


def _score(x) -> str:
    return "—" if x is None else str(x)


def _m2(x) -> str:
    return "—" if x is None else f"{x:,.0f} m²".replace(",", " ")


def _eurm2(x) -> str:
    return "—" if x is None else f"{x:,.0f} €/m²".replace(",", " ")


def _eur(x) -> str:
    if x is None:
        return "—"
    ax = abs(x)
    if ax >= 1_000_000:
        return f"{x / 1_000_000:.1f} M€"
    if ax >= 1_000:
        return f"{x / 1_000:.0f} k€"
    return f"{x:.0f} €"


_SOURCE_LABEL = {"non_renseignee": "non renseignée", "saisi_utilisateur": "saisie utilisateur",
                 "deduit_manuellement": "déduit manuellement",
                 "document_externe_utilisateur": "document externe (utilisateur)", "autre": "autre"}
_CONF_LABEL = {"inconnu": "inconnu", "faible": "faible", "moyen": "moyen", "eleve": "élevé"}


def _prospection_view(fiche: dict) -> dict:
    """Vue d'affichage du bloc « Prospection propriétaire » (saisie MANUELLE, jamais externe)."""
    pr = fiche.get("prospection") or {}
    d = pr.get("data") or {}
    contact = " · ".join(x for x in (d.get("contact_nom"), d.get("contact_organisation"),
                                     d.get("contact_telephone"), d.get("contact_email"),
                                     d.get("contact_adresse")) if x)
    action = d.get("prochaine_action") or ""
    if action and d.get("date_prochaine_action"):
        action += f" (rappel {d['date_prochaine_action']})"
    return {
        "statut": pr.get("statut_label") or "Propriétaire inconnu",
        "source": _SOURCE_LABEL.get(d.get("source_statut"), "non renseignée"),
        "confiance": _CONF_LABEL.get(d.get("niveau_confiance"), "inconnu"),
        "contact": contact,
        "action": action,
        "responsable": d.get("responsable_interne") or "",
        "notes": d.get("notes_contact") or "",
        "disclaimer": pr.get("disclaimer") or
        ("Informations de contact renseignées manuellement par l'utilisateur ou issues d'une "
         "source autorisée. LA BUSE ne garantit pas l'identité du propriétaire."),
    }


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


# ─────────────────────────── One-pager (Lot D1) — document de comité ───────────────────────────

def _minimap(geojson: dict | None, lon, lat) -> str:
    """Mini-carte aérienne (IGN WMS ortho) + contour de la parcelle en overlay SVG. Auto-suffisante
    côté serveur (le navigateur charge la tuile à l'impression) ; dégrade proprement sans réseau."""
    if lon is None or lat is None:
        return ""
    ring = []
    try:
        g = geojson or {}
        coords = g.get("coordinates") or []
        if g.get("type") == "MultiPolygon":
            coords = coords[0]
        if g.get("type") in ("Polygon", "MultiPolygon") and coords:
            ring = coords[0]
    except Exception:  # noqa: BLE001
        ring = []
    # bbox carré (en degrés) centré sur la parcelle, avec marge → contour bien visible.
    if ring:
        xs = [c[0] for c in ring]
        ys = [c[1] for c in ring]
        cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        half = max(max(xs) - min(xs), max(ys) - min(ys)) * 0.9 or 0.0008
    else:
        cx, cy, half = float(lon), float(lat), 0.0008
    half = max(half, 0.0004)
    minx, maxx, miny, maxy = cx - half, cx + half, cy - half, cy + half
    W = H = 460
    wms = ("https://data.geopf.fr/wms-r/ows?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap"
           "&LAYERS=ORTHOIMAGERY.ORTHOPHOTOS&STYLES=&FORMAT=image/jpeg&CRS=EPSG:4326"
           f"&WIDTH={W}&HEIGHT={H}&BBOX={miny},{minx},{maxy},{maxx}")  # 1.3.0 EPSG:4326 = lat,lon
    overlay = ""
    if ring:
        pts = " ".join(f"{(c[0]-minx)/(maxx-minx)*W:.1f},{(maxy-c[1])/(maxy-miny)*H:.1f}" for c in ring)
        overlay = (f"<svg class='mm-svg' viewBox='0 0 {W} {H}' preserveAspectRatio='none'>"
                   f"<polygon points='{pts}' fill='rgba(201,168,106,.18)' "
                   "stroke='#c9a86a' stroke-width='2.5'/></svg>")
    return (f"<div class='mini'><img class='mm-img' src='{html.escape(wms)}' alt='vue aérienne' "
            f"width='{W}' height='{H}'>{overlay}"
            "<span class='mm-att'>© IGN — Géoplateforme (BD ORTHO)</span></div>")


def fiche_onepager(fiche: dict, geojson: dict | None = None) -> str:
    """Fiche 1 page A4 (impression → PDF) : le document qu'un promoteur met en comité.
    Verdict, capacité, résiduel, bilan, contraintes, « à vérifier », mini-carte aérienne."""
    p, v = fiche["parcel"], fiche["verdict"]
    fa = fiche.get("faisabilite") or {}
    res = fa.get("residuel") or {}
    bilan = fa.get("bilan") or {}
    rv = fiche.get("resume") or {}
    status = v.get("status") or "—"

    # Capacité (si constructible).
    cap = "—"
    if fa.get("constructible"):
        cap = html.escape(fa.get("verdict") or "—")
    elif fa.get("verdict"):
        cap = html.escape(fa["verdict"])

    def kv(label, value):
        return f"<div class='kv'><span class='kl'>{label}</span><span class='kvv'>{value}</span></div>"

    # Résiduel.
    res_html = ""
    if res.get("disponible"):
        res_html = kv("Potentiel résiduel",
                      f"bâtie à {res['taux_emprise_pct']} % de l'emprise · SDP résiduelle ~{_m2(res.get('sdp_residuelle_m2'))}"
                      + (" · <b>sous-densité</b>" if res.get("sous_densite") else ""))
    # Bilan.
    bil_html = ""
    if bilan.get("fiable"):
        ca = bilan.get("ca") or {}
        cf = bilan.get("charge_fonciere") or {}
        bil_html = kv("Bilan (indicatif)",
                      f"CA ~{_eur(ca.get('bas'))}–{_eur(ca.get('haut'))} · charge foncière médiane ~{_eur(cf.get('central'))}"
                      + (f" (~{cf.get('par_m2_terrain')} €/m² terrain)" if cf.get("par_m2_terrain") else ""))

    # Contraintes (HARD_EXCLUDE + SOFT_FLAG) et à-vérifier (UNKNOWN).
    contraintes = [c for c in fiche["cascade"] if c["result"] in ("HARD_EXCLUDE", "SOFT_FLAG")]
    cont_html = "".join(
        f"<li class='{'hard' if c['result']=='HARD_EXCLUDE' else 'soft'}'>{html.escape(c['detail'])}</li>"
        for c in contraintes[:7]) or "<li class='ok'>Aucune contrainte relevée sur les couches disponibles.</li>"
    verifs = list(rv.get("vigilance") or [])
    if not verifs:
        verifs = [c["detail"] for c in fiche["cascade"] if c["result"] == "UNKNOWN"][:4]
    verif_html = "".join(f"<li>{html.escape(x)}</li>" for x in verifs[:5]) or "<li>—</li>"

    synth = html.escape(rv.get("synthese") or "")
    action = html.escape(rv.get("prochaine_action") or "")
    loc = (f"{html.escape(p.get('commune') or '—')} · section {html.escape(p.get('section') or '—')} "
           f"{html.escape(p.get('numero') or '')} · {_m2(p.get('surface_m2'))}")
    cen = p.get("centroid") or {}
    today = _today()
    return f"""<!doctype html><html lang="fr"><meta charset="utf-8">
<title>LA BUSE — {html.escape(p['idu'])}</title>
<style>
 @page {{ size: A4 portrait; margin: 10mm; }}
 * {{ box-sizing: border-box; }}
 body {{ font: 11px/1.42 -apple-system,Segoe UI,Roboto,sans-serif; color:#1a1a1a; margin:0; }}
 .head {{ display:flex; justify-content:space-between; align-items:flex-start; border-bottom:2px solid #c9a86a; padding-bottom:6px; }}
 .brand {{ font-weight:800; letter-spacing:.06em; font-size:15px; }} .brand small {{ font-weight:400; color:#777; letter-spacing:0; }}
 .idu {{ font-size:16px; font-weight:700; }} .loc {{ color:#555; }}
 .date {{ color:#888; text-align:right; }}
 .grid {{ display:grid; grid-template-columns: 1fr 460px; gap:12px; margin-top:8px; }}
 .verdict {{ display:flex; align-items:center; gap:10px; margin:6px 0; }}
 .badge {{ display:inline-block; padding:3px 10px; border-radius:5px; color:#fff; font-weight:700; font-size:12px; }}
 .v-opportunite{{background:#37976a}} .v-a_creuser{{background:#c2913f}} .v-exclue{{background:#697079}} .v-faux_positif_probable{{background:#b85f4c}}
 .scores {{ font-weight:600; color:#333; }}
 .synth {{ margin:6px 0; }}
 .kv {{ display:flex; gap:8px; padding:3px 0; border-bottom:1px solid #f0f0f0; }}
 .kl {{ flex:0 0 120px; color:#777; font-weight:600; }} .kvv {{ flex:1; }}
 h3 {{ font-size:11px; text-transform:uppercase; letter-spacing:.05em; color:#c9a86a; margin:10px 0 4px; }}
 ul {{ margin:2px 0; padding-left:16px; }} li {{ margin:1px 0; }}
 li.hard {{ color:#a23; }} li.soft {{ color:#a76; }} li.ok {{ color:#393; }}
 .mini {{ position:relative; width:460px; height:300px; overflow:hidden; border:1px solid #ddd; border-radius:6px; }}
 .mm-img {{ width:460px; height:300px; object-fit:cover; display:block; }}
 .mm-svg {{ position:absolute; inset:0; width:100%; height:100%; }}
 .mm-att {{ position:absolute; right:3px; bottom:2px; font-size:8px; color:#fff; background:rgba(0,0,0,.45); padding:0 4px; border-radius:3px; }}
 .foot {{ margin-top:10px; border-top:1px solid #eee; padding-top:5px; color:#888; font-style:italic; font-size:9.5px; }}
 .action {{ margin-top:6px; padding:6px 9px; background:#faf6ec; border-left:3px solid #c9a86a; }}
</style>
<div class="head">
  <div><div class="brand">LA&nbsp;BUSE <small>· radar foncier La Réunion</small></div>
       <div class="idu">{html.escape(p['idu'])}</div><div class="loc">{loc}</div></div>
  <div class="date">Fiche de pré-qualification<br>{today}</div>
</div>
<div class="grid">
  <div>
    <div class="verdict"><span class="badge v-{html.escape(status)}">{html.escape(_STATUS_LABEL.get(status, status))}</span>
      <span class="scores">Opportunité {_score(v.get('opportunity_score'))}/100 · Complétude {_score(v.get('completeness_score'))}/100</span></div>
    {f'<p class="synth">{synth}</p>' if synth else ''}
    <h3>Capacité &amp; potentiel</h3>
    {kv("Zone PLU", html.escape(str(fa.get('zone') or '—')))}
    {kv("Capacité estimée", cap)}
    {res_html}
    {bil_html}
    <h3>Contraintes</h3>
    <ul>{cont_html}</ul>
    <h3>À vérifier avant de démarcher</h3>
    <ul>{verif_html}</ul>
    {f'<div class="action"><b>Prochaine action :</b> {action}</div>' if action else ''}
  </div>
  <div>
    {_minimap(geojson, cen.get('lon'), cen.get('lat'))}
    {_rlt_link(cen.get('lon'), cen.get('lat'))}
  </div>
</div>
<div class="foot">{html.escape(fiche.get('disclaimer') or '')} Document indicatif sur données publiques — pré-faisabilité et bilan ne valent pas étude réglementaire ni engagement.</div>
</html>"""


def _rlt_link(lon: float | None, lat: float | None) -> str:
    """3.B — lien « Remonter le temps » (IGN) sous la mini-carte du one-pager."""
    from .enrichment import remonter_le_temps
    rlt = remonter_le_temps(lon, lat)
    if not rlt.get("available"):
        return ""
    return (f'<p style="margin:5px 0 0;font-size:9.5px;color:#555">📜 Photos aériennes historiques : '
            f'<a href="{html.escape(rlt["url"])}">remonterletemps.ign.fr</a> '
            f'(comparer la parcelle, 1950 → aujourd\'hui)</p>')


def _today() -> str:
    from datetime import date
    return date.today().strftime("%d/%m/%Y")
