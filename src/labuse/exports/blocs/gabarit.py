"""DOCS-1 (Lot C) — bloc « Enveloppe réglementaire (gabarit) », la page déjà rendue dans le Dossier /
Pré-dossier PC, SORTIE SEULE : plan 2D, zone d'implantation, plafond d'emprise, hauteur, règles
appliquées et règles non intégrées (nom · citation · source). 2D seulement, aucun calcul ici — on lit
le MÊME moteur que l'écran /outils/gabarit (build_gabarit_input + compute_gabarit). Si le calcul est
incomplet, le document NE se génère PAS (builder.construire_gabarit lève DocumentNonEtablissable)."""
from __future__ import annotations

from ..lignes import ligne, pied
from ..registre_fmt import fmt_m, fmt_m2, fmt_pct
from ..rendu import esc, note, section, table_kv, verdict

IDS = ("gabarit_zone_libere_m2", "gabarit_implantation_m2", "gabarit_bati_deduit_m2",
       "gabarit_emprise_plafond_m2", "gabarit_hauteur_m", "gabarit_couverture_verdict", "gabarit_plan_2d")


def _m2_ou_texte(v):
    return esc(v) if isinstance(v, str) else fmt_m2(v)


def _m_ou_texte(v):
    return esc(v) if isinstance(v, str) else fmt_m(v)


def _source(src) -> str:
    """RegulatorySource → « document · zone · article · date · fournisseur » (ce qui est renseigné)."""
    if src is None:
        return ""
    bits = [getattr(src, "document", None), getattr(src, "zone", None), getattr(src, "article", None),
            getattr(src, "versionDate", None), getattr(src, "provider", None)]
    return " · ".join(esc(b) for b in bits if b)


def _fusion_voie(rules):
    """DOCS-COHERENCE-1 (D1) — UNE seule ligne « Recul voie 4 m » : les variantes du moteur (« Recul
    voie », « … (emprise publique) », « … (voie privée) »), de même recul, sont fusionnées et LEURS
    SOURCES citées ensemble sur la même ligne. Le moteur garde ses règles distinctes ; seul l'affichage
    du document les regroupe."""
    import types
    voies = [r for r in rules if (getattr(r, "label", "") or "").startswith("Recul voie")]
    if len(voies) <= 1:
        return rules
    base = voies[0]
    srcs = []
    for r in voies:
        s = _source(getattr(r, "source", None))
        if s and s not in srcs:
            srcs.append(s)
    merged = types.SimpleNamespace(label="Recul voie", value=getattr(base, "value", None),
                                   unit=getattr(base, "unit", None),
                                   detail=getattr(base, "detail", None), source=None)
    merged._src_html = "".join(f'<div class="src">{s}</div>' for s in srcs)
    result, done = [], False
    for r in rules:
        if (getattr(r, "label", "") or "").startswith("Recul voie"):
            if not done:
                result.append(merged)
                done = True
        else:
            result.append(r)
    return result


def _regles(rules, *, appliquees: bool) -> str:
    out = []
    for r in _fusion_voie(list(rules or [])):
        nom = esc(getattr(r, "label", "") or "")
        val = getattr(r, "value", None)
        unit = getattr(r, "unit", None)
        # CHASSE-DOCS-FIX-1 (E-12) — format FR par unité ; « % » passait en esc(str(val)) → « 40.0 »
        # (point décimal, sans unité). fmt_pct rend « 40 % ».
        if appliquees and val is not None:
            if unit in ("m", "m."):
                num = fmt_m(val)
            elif unit == "m²":
                num = fmt_m2(val)
            elif unit == "%":
                num = fmt_pct(val, 0 if float(val) == int(val) else 1)
            else:
                num = esc(str(val))
            chiffre = f" : {num}"
        else:
            chiffre = ""
        detail = getattr(r, "detail", None)
        det = f" — {esc(detail)}" if detail else ""
        src_html = getattr(r, "_src_html", None)   # D1 — sources déjà combinées (ligne « Recul voie » fusionnée)
        if src_html is None:
            src = _source(getattr(r, "source", None))
            src_html = f'<div class="src">{src}</div>' if src else ""
        out.append(f'<div class="r"><span class="nom">{nom}{chiffre}</span>{det}{src_html}</div>')
    cls = "regles" + ("" if appliquees else " nonint")
    return f'<div class="{cls}">{"".join(out)}</div>' if out else ""


def rendu(valeurs, ctx=None) -> str:
    gr = (ctx or {}).get("gabarit") if isinstance(ctx, dict) else ctx
    corps = ""
    cv = valeurs.get("gabarit_couverture_verdict")
    if cv is not None and cv.valeur:
        corps += verdict(esc(cv.valeur), "neutral")
    plan = valeurs.get("gabarit_plan_2d")
    if plan is not None and plan.valeur:
        # le plan 2D est un fragment SVG déjà composé par le moteur (gabarit_svg) — embarqué tel quel.
        corps += f'<div class="plan2d">{plan.valeur}</div>'
    lignes = [
        # RECETTE-OUTILS-3 (S7) — « Zone d'implantation » = valeur APRÈS déduction du bâti ; juste en
        # dessous, l'emprise de bâti retranchée (ligne omise s'il n'y a rien à déduire).
        # RECETTE-OUTILS-4 (U4) — libellé « bâti existant déduit » (sans « dont » : la zone affichée est
        # DÉJÀ la valeur après déduction ; « dont » laissait croire que le bâti en faisait partie), même
        # formulation qu'à l'écran.
        # DOCS-COHERENCE-1 (A3) — DEUX valeurs nommées partout : « terrain libéré » (X, avant déduction
        # du bâti) et « bâti existant déduit » (Y, après). X − Y = emprise du bâti dans la zone. La ligne
        # « bâti existant déduit » est omise s'il n'y a rien à retrancher (X = Y).
        ligne(valeurs, "Zone d'implantation, terrain libéré", "gabarit_zone_libere_m2", _m2_ou_texte),
        (ligne(valeurs, "Zone d'implantation, bâti existant déduit", "gabarit_implantation_m2", _m2_ou_texte)
         if (valeurs.get("gabarit_bati_deduit_m2") and valeurs["gabarit_bati_deduit_m2"].valeur) else None),
        ligne(valeurs, "Plafond d'emprise", "gabarit_emprise_plafond_m2", _m2_ou_texte),
        ligne(valeurs, "Hauteur réglementaire", "gabarit_hauteur_m", _m_ou_texte),
    ]
    lignes = [x for x in lignes if x]
    if lignes:
        corps += table_kv(lignes)
    ra = _regles(getattr(gr, "appliedRules", None), appliquees=True) if gr is not None else ""
    if ra:
        corps += "<h3>Règles appliquées</h3>" + ra
    rni = _regles(getattr(gr, "nonIntegratedRules", None), appliquees=False) if gr is not None else ""
    if rni:
        corps += "<h3>Règles non intégrées</h3>" + rni
    # CHASSE-FIX-1 (C06) — zone AU à ouverture bloquée : l'enveloppe est « après ouverture »
    # (drapeau posé par l'API gabarit, règle unique faisabilite.au_differe).
    _au = (getattr(gr, "raccordement", None) or {}).get("au_differe") if gr is not None else None
    if _au:
        corps += verdict(esc(_au.get("libelle") or "Potentiel différé — ouverture de la zone requise"),
                         "warn")
    # RECETTE-OUTILS-2 (R16) — page « Vue 3D » : axonométrie du MÊME volume que l'outil (enveloppe
    # extrudée à la hauteur sourcée + bâti existant), rendue en SVG serveur (l'écran la fait en WebGL,
    # non reproductible ici). Sol plat → légende « Volume indicatif — terrain supposé plat ». Absente si
    # la hauteur n'est pas chiffrée (prospect) : pas de volume, comme l'outil dit « 3D indisponible ».
    try:
        from ...gabarit.plan_svg import gabarit_svg_3d
        svg3d = gabarit_svg_3d(gr) if gr is not None else None
    except Exception:  # noqa: BLE001 — la vue 3D est un plus, jamais un bloqueur du document
        svg3d = None
    if svg3d:
        corps += ('<div class="vue3d" style="page-break-before:always">'
                  '<h3>Vue 3D du gabarit</h3>'
                  f'<div class="plan3d">{svg3d}</div></div>')
    corps += note("Gabarit réglementaire 2D, pré-faisabilité sur règlement public. Une étude par un "
                  "professionnel peut modifier ces valeurs.")
    corps += pied(valeurs, IDS)
    return section("Enveloppe réglementaire (gabarit)", corps)
