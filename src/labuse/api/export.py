"""Export « fiche premium » (brief §8/§12 étape 10) — Markdown & HTML.

Rend la fiche assemblée par l'API en un document sobre, B2B, prêt à transmettre.
Chaque information reste tracée à sa source ; la non-garantie est rappelée.
"""
from __future__ import annotations

import html

from ..ai.avis import AVIS_IA  # EXPRESS-01 · Volet B — avis IA (source unique)
# M34 (dette #14) : libellés du POINT DE TRADUCTION UNIQUE (tier servi) — plus de table
# locale de statuts legacy. Le verdict affiché ici est celui de verdict_servi.
from ..verdict_servi import TIER_LABELS

_RESULT_LABEL = {
    "HARD_EXCLUDE": "EXCLUSION", "SOFT_FLAG": "contrainte", "POSITIVE": "signal +",
    "PASS": "ok", "UNKNOWN": "donnée manquante",
}


def _verdict_label(v: dict | None) -> str:
    v = v or {}
    return v.get("label") or TIER_LABELS.get(v.get("status"), v.get("status") or "—")


def fiche_markdown(fiche: dict) -> str:
    p = fiche["parcel"]
    v = fiche["verdict"]
    lines = [
        f"# LABUSE — Fiche parcelle {p['idu']}",
        "",
        f"> {fiche['disclaimer']}",
        "",
        f"**Commune :** {p.get('commune') or '—'}  ·  **Surface :** {_m2(p.get('surface_m2'))}  ·  "
        f"**Section/№ :** {p.get('section') or '—'} {p.get('numero') or ''}",
        "",
        "## Verdict",
        "",
        f"- **Statut :** {_verdict_label(v)}"
        # M36 Lot C (Q3) : rang affiché sur brûlante/chaude UNIQUEMENT
        + (f" (rang {v['rang']})" if v.get("rang") and v.get("tier") in ("brulante", "chaude") else "")
        + ("  ·  **micro-opportunité** (≤ 500 m²)" if v.get("micro_opportunite") else ""),
        # M36 Lot B : scores Opportunité/Complétude RETIRÉS de l'affichage client (décorrélés
        # du tier / quasi-constants — arbitrage Vic M35 D2/D3). Calcul conservé en interne.
        "",
    ]
    if v.get("badge_division_libelle"):
        lines += [f"- **Nuance :** {v['badge_division_libelle']}", ""]
    if v.get("motif"):
        lines += [f"- **Motif ({'registre servi' if v.get('exception_registre') else 'filtre servi'}) :** {v['motif']}", ""]
    if v.get("micro_opportunite"):
        lines += ["> Petite parcelle : potentiel à analyser surtout en assemblage ou micro-opération.", ""]
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

    mb = fiche.get("mode_b") or {}
    if mb.get("disponible") and mb.get("trop_petit"):   # M59-P1 (Q4) — DIT, jamais un calcul muet
        lines += ["## Réhabilitation", "",
                  f"_{mb.get('motif', 'Bâti trop petit pour une thèse de réhabilitation.')}_", ""]
    elif mb.get("disponible"):
        c = mb["composantes"]
        lines += ["## Réhabilitation (Estimé)", ""]   # M59-P1 (Q5) — « Mode B » retiré de l'affichage
        # M59-P1 (Q1) — plus de « prix d'achat max » global ; hors valeur du terrain + comparaison
        # (la comparaison terrain + la phrase « portée par le terrain » DANS LES DEUX cas).
        if mb.get("negatif"):
            lines += [f"**{mb['message_negatif']}**"]
        else:
            _fonc = f" ({mb['surface_parcelle_m2']} m²)" if mb.get("surface_parcelle_m2") else ""
            lines += [f"- **Ce que la réhabilitation du bâti justifie (Estimé) :** ~{mb['achat_max_libelle']}",
                      f"- hors valeur du terrain — le foncier{_fonc} s'ajoute à ce montant"]
        tn = mb.get("terrain_nu")
        if tn:
            lines += [f"- terrain nu au prix du secteur : ~{tn['valeur_libelle']} "
                      f"({tn['prix_m2']} €/m² × {tn['surface_m2']} m² · Estimé)"]
        if mb.get("porte_par_terrain"):
            lines += ["- **À ces hypothèses, la valeur de cette parcelle est portée par le "
                      "terrain, pas par le bâti.**"]
        lines += [""]
        lines += [
            f"- Surface réhabilitable : ~{c['surface']['shab_rehabilitable_m2']} m² habitables "
            f"(emprise {c['surface']['emprise_bati_m2']} m² [Sourcé] × {c['surface']['niveaux']} niveau(x) "
            f"[{'Sourcé' if c['surface']['niveaux_reels'] else 'Estimé'}] ÷ 1,15)",
            f"- Prix de sortie : {c['prix_sortie']['prix_m2']} €/m² — {c['prix_sortie']['libelle']} "
            f"({c['prix_sortie'].get('perimetre', 'médiane secteur→commune, sans rayon adaptatif')}) [Sourcé DVF]",
            f"- {c['travaux']['libelle']}",
            f"- Frais & marge : {c['frais_marge']['libelle']}",
            "", f"_{mb['avertissement']}_", ""]

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
        lines += ["| Parcelle | Tier servi | Rang | Zone PLU | Surface |", "|---|---|---|---|---|"]
        for v in vz["voisines"]:
            lines.append(f"| {v['idu']} | {TIER_LABELS.get(v.get('status'), v.get('status') or '—')} | "
                         f"{v.get('rang') if v.get('rang') is not None and v.get('status') in ('brulante', 'chaude') else '—'} | "
                         f"{v.get('plu_zone') or '—'} | {_m2(v.get('surface_m2'))} |")
        lines += ["", "_Adjacence géométrique uniquement — propriétaires, accords et faisabilité d'un "
                  "assemblage restent à vérifier._", ""]

    pv = _prospection_view(fiche)
    lines += ["## Prospection propriétaire", "",
              f"- **Statut propriétaire :** {pv['statut']}",
              f"- **Source :** {pv['source']}  ·  **Niveau de confiance :** {pv['confiance']}"]
    lines.append(f"- **Contact (saisi manuellement) :** {pv['contact']}" if pv["contact"]
                 else "- **Contact :** Propriétaire à identifier — aucune donnée nominative disponible dans LABUSE.")
    if pv["action"]:
        lines.append(f"- **Prochaine action :** {pv['action']}")
    if pv["responsable"]:
        lines.append(f"- **Responsable :** {pv['responsable']}")
    if pv["notes"]:
        lines.append(f"- **Notes :** {pv['notes']}")
    lines += ["", f"_{pv['disclaimer']}_", ""]

    ai = fiche.get("ai")
    if ai:
        lines += ["## Analyse LABUSE (IA)", "",
                  f"> {AVIS_IA}", "",
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
    mb = fiche.get("mode_b") or {}
    mode_b_html = ""
    if mb.get("disponible") and mb.get("trop_petit"):   # M59-P1 (Q4)
        mode_b_html = ("<h2>Réhabilitation</h2><p class='disc'>"
                       + html.escape(mb.get("motif", "Bâti trop petit pour une thèse de réhabilitation."))
                       + "</p>")
    elif mb.get("disponible"):
        cmb = mb["composantes"]
        # M59-P1 (Q1) — plus « prix d'achat max » global ; comparaison terrain + phrase « portée par
        # le terrain » DANS LES DEUX cas (positif ou négatif).
        if mb.get("negatif"):
            tete = f"<p><strong>{html.escape(mb['message_negatif'])}</strong></p>"
        else:
            _fonc = f" ({mb['surface_parcelle_m2']} m²)" if mb.get("surface_parcelle_m2") else ""
            tete = (f"<p><strong>Ce que la réhabilitation du bâti justifie (Estimé) :</strong> "
                    f"~{html.escape(mb['achat_max_libelle'])}</p>"
                    f"<p class='disc'>hors valeur du terrain — le foncier{_fonc} s'ajoute à ce montant</p>")
        tn = mb.get("terrain_nu")
        if tn:
            tete += (f"<p class='disc'>terrain nu au prix du secteur : ~{html.escape(tn['valeur_libelle'])} "
                     f"({tn['prix_m2']} €/m² × {tn['surface_m2']} m² · Estimé)</p>")
        if mb.get("porte_par_terrain"):
            tete += ("<p><strong>À ces hypothèses, la valeur de cette parcelle est portée par le "
                     "terrain, pas par le bâti.</strong></p>")
        mode_b_html = (
            "<h2>Réhabilitation (Estimé)</h2>" + tete + "<ul>"
            f"<li>Surface réhabilitable : ~{cmb['surface']['shab_rehabilitable_m2']} m² habitables "
            f"(emprise {cmb['surface']['emprise_bati_m2']} m² [Sourcé] × {cmb['surface']['niveaux']} niveau(x) "
            f"[{'Sourcé' if cmb['surface']['niveaux_reels'] else 'Estimé'}])</li>"
            f"<li>Prix de sortie : {cmb['prix_sortie']['prix_m2']} €/m² — {html.escape(cmb['prix_sortie']['libelle'])} "
            f"({html.escape(cmb['prix_sortie'].get('perimetre', 'médiane secteur→commune, sans rayon adaptatif'))}) [Sourcé DVF]</li>"
            f"<li>{html.escape(cmb['travaux']['libelle'])}</li>"
            f"<li>Frais &amp; marge : {html.escape(cmb['frais_marge']['libelle'])}</li></ul>"
            f"<p class='disc'>{html.escape(mb['avertissement'])}</p>")
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
            f"<td>{html.escape(TIER_LABELS.get(v.get('status'), v.get('status') or '—'))}</td>"
            f"<td>{v.get('rang') if v.get('rang') is not None and v.get('status') in ('brulante', 'chaude') else '—'}</td>"
            f"<td>{html.escape(v.get('plu_zone') or '—')}</td>"
            f"<td>{_m2(v.get('surface_m2'))}</td></tr>"
            for v in vz["voisines"])
        vz_html = ("<h2>Parcelles voisines (contiguïté)</h2>"
                   + (f"<p class='disc'>{html.escape(note)}</p>" if note else "")
                   + "<table><tr><th>Parcelle</th><th>Tier servi</th><th>Rang</th><th>Zone PLU</th><th>Surface</th></tr>"
                   + rows_vz + "</table>"
                   "<p class='disc'>Adjacence géométrique uniquement — propriétaires, accords et "
                   "faisabilité d'un assemblage restent à vérifier.</p>")
    pv = _prospection_view(fiche)
    contact_li = (f"<li><strong>Contact (saisi manuellement) :</strong> {html.escape(pv['contact'])}</li>"
                  if pv["contact"] else
                  "<li><strong>Contact :</strong> Propriétaire à identifier — aucune donnée nominative "
                  "disponible dans LABUSE.</li>")
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
<title>LABUSE — {html.escape(p['idu'])}</title>
<style>
 body{{font:15px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;color:#1a1a1a;max-width:880px;margin:2rem auto;padding:0 1rem}}
 h1{{font-size:1.5rem;letter-spacing:.02em}} h2{{font-size:1.05rem;margin-top:1.8rem;border-bottom:1px solid #eee;padding-bottom:.3rem}}
 .disc{{color:#777;font-style:italic;font-size:.9rem}} .score{{font-weight:600}}
 table{{border-collapse:collapse;width:100%;font-size:.9rem}} td,th{{border:1px solid #e5e5e5;padding:.35rem .5rem;text-align:left;vertical-align:top}}
 .src{{color:#888;font-size:.85em}} .badge{{display:inline-block;padding:.15rem .6rem;border-radius:.4rem;background:#111;color:#fff;font-size:.85rem}}
 .badge-micro{{display:inline-block;margin-left:.4rem;padding:.15rem .6rem;border-radius:.4rem;background:#efe6cd;color:#6a5a1f;font-size:.85rem}}
 .micro-note{{color:#6a5a1f;font-size:.9rem;margin:.3rem 0 0}}
</style>
<h1>LABUSE — Fiche parcelle {html.escape(p['idu'])}</h1>
<p class="disc">{html.escape(fiche['disclaimer'])}</p>
<p><strong>Commune :</strong> {html.escape(p.get('commune') or '—')} ·
   <strong>Surface :</strong> {_m2(p.get('surface_m2'))} ·
   <strong>Section/№ :</strong> {html.escape((p.get('section') or '—'))} {html.escape(p.get('numero') or '')}</p>
<h2>Verdict</h2>
<p><span class="badge">{html.escape(_verdict_label(v))}</span>{f" <span class='src'>rang {v['rang']}</span>" if v.get('rang') and v.get('tier') in ('brulante', 'chaude') else ''}{' <span class="badge-micro">micro-opportunité</span>' if v.get('micro_opportunite') else ''}</p>
{f'<p class="micro-note">{html.escape(v["badge_division_libelle"])}</p>' if v.get('badge_division_libelle') else ''}
{f'<p class="disc">Motif ({"registre servi" if v.get("exception_registre") else "filtre servi"}) : {html.escape(v["motif"])}</p>' if v.get('motif') else ''}
{'<p class="micro-note">Petite parcelle (≤ 500 m²) : potentiel à analyser surtout en assemblage ou micro-opération.</p>' if v.get('micro_opportunite') else ''}
<p><strong>Raisons :</strong></p><ul>{reasons}</ul>
{resume_html}
{mode_b_html}
{bati_html}
<h2>Cascade — traçabilité</h2>
<table><tr><th>Couche</th><th>Verdict</th><th>Sévérité</th><th>Détail</th><th>Source</th></tr>{rows}</table>
<h2>Sources</h2>
<p><strong>Ont répondu :</strong> {html.escape(', '.join(fiche['sources_responded']) or '—')}</p>
<p><strong>Silencieuses :</strong> {html.escape(', '.join(fiche['sources_silent']) or '—')}</p>
{comp_html}
{vz_html}
{prosp_html}
{"<h2>Analyse LABUSE (IA)</h2><p class='disc avis-ia'>" + html.escape(AVIS_IA) + "</p><p>" + html.escape(ai.get('executive_summary','')) + "</p>" if ai else ""}
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
         "source autorisée. LABUSE ne garantit pas l'identité du propriétaire."),
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


def _today() -> str:
    from datetime import date
    return date.today().strftime("%d/%m/%Y")
