"""DOCS-1 (Lot C) — bloc « Enveloppe réglementaire (gabarit) », la page déjà rendue dans le Dossier /
Pré-dossier PC, SORTIE SEULE : plan 2D, zone d'implantation, plafond d'emprise, hauteur, règles
appliquées et règles non intégrées (nom · citation · source). 2D seulement, aucun calcul ici — on lit
le MÊME moteur que l'écran /outils/gabarit (build_gabarit_input + compute_gabarit). Si le calcul est
incomplet, le document NE se génère PAS (builder.construire_gabarit lève DocumentNonEtablissable)."""
from __future__ import annotations

from ..lignes import ligne
from ..registre_fmt import fmt_m, fmt_m2, fmt_pct
from ..rendu import esc, ligne_kv, note, section, table_kv, verdict

IDS = ("gabarit_zone_libere_m2", "gabarit_implantation_m2", "gabarit_bati_deduit_m2",
       "gabarit_emprise_plafond_m2", "gabarit_hauteur_m", "gabarit_couverture_verdict", "gabarit_plan_2d",
       # DOCS-1 — les SUP de la FICHE (même lecteur que le Dossier), pour ne jamais contredire « 1 PM1 ».
       "dispositifs_parcelle")


def _sup_fiche_ligne(valeurs) -> str:
    """DOCS-1 — la ligne « Servitudes d'utilité publique » du Gabarit, servie par la FICHE
    (dispositifs.sup), rendue avec le MÊME libellé que le Dossier (miroir._r_sup). Absente si la
    fiche n'a pas servi de SUP (on laisse alors le moteur dire la présence/absence géométrique)."""
    v = valeurs.get("dispositifs_parcelle")
    sup = getattr(v, "valeur", None) if v is not None else None
    if not sup:
        return ""
    try:
        from ..miroir import _r_sup
        return table_kv([ligne_kv("Servitudes d'utilité publique", _r_sup(sup))])
    except Exception:  # noqa: BLE001
        return ""


def _m2_ou_texte(v):
    return esc(v) if isinstance(v, str) else fmt_m2(v)


def _m_ou_texte(v):
    return esc(v) if isinstance(v, str) else fmt_m(v)


def _clean_src(b):
    """DOCS-1 — un fragment de source rendu au client : codes PPR/SUP bruts humanisés
    (« INONDATION_MOUVEMENT_DE_TERRAIN », « PM1_PPR_… »), notes techniques retirées, « édition non
    enregistrée » → « édition courante », date ISO → jj/mm/aaaa. Best-effort : jamais un 500 sur un PDF."""
    if not b:
        return None
    import re as _re
    s = str(b)
    try:
        from ...api.risques_arbitrage import libelle_client_detail
        s = libelle_client_detail(s) or s
    except Exception:  # noqa: BLE001
        pass
    try:
        from ...millesime_source import nettoyer_notes_internes
        s = nettoyer_notes_internes(s) or s
    except Exception:  # noqa: BLE001
        pass
    s = s.replace("édition non enregistrée", "édition courante")
    s = _re.sub(r"\b((?:19|20)\d{2})-(\d{2})-(\d{2})\b", lambda m: f"{m.group(3)}/{m.group(2)}/{m.group(1)}", s)
    return s


def _source(src) -> str:
    """RegulatorySource → « document · zone · article · date · fournisseur » (ce qui est renseigné),
    chaque fragment nettoyé pour le client (DOCS-1, cf. `_clean_src`)."""
    if src is None:
        return ""
    bits = [_clean_src(getattr(src, "document", None)), _clean_src(getattr(src, "zone", None)),
            _clean_src(getattr(src, "article", None)), _clean_src(getattr(src, "versionDate", None)),
            _clean_src(getattr(src, "provider", None))]
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
        nom = esc(_clean_src(getattr(r, "label", "")) or "")   # DOCS-1 — codes PPR bruts humanisés
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
        detail = _clean_src(getattr(r, "detail", None))   # DOCS-1 — codes PPR/SUP bruts humanisés
        det = f" — {esc(detail)}" if detail else ""
        src_html = getattr(r, "_src_html", None)   # D1 — sources déjà combinées (ligne « Recul voie » fusionnée)
        if src_html is None:
            src = _source(getattr(r, "source", None))
            src_html = f'<div class="src">{src}</div>' if src else ""
        out.append(f'<div class="r"><span class="nom">{nom}{chiffre}</span>{det}{src_html}</div>')
    cls = "regles" + ("" if appliquees else " nonint")
    return f'<div class="{cls}">{"".join(out)}</div>' if out else ""


def _bloc_coupes_pilote(scene: dict) -> str:
    """GABARIT-3D-1 (pilote) — plan-clé + deux coupes du terrain réel depuis la scène (SVG serveur)."""
    try:
        from ...gabarit.coupe_svg import coupe_svg, plan_cle_svg
    except Exception:  # noqa: BLE001 — la section pilote ne doit jamais bloquer un document
        return ""
    if not scene.get("disponible") or not scene.get("coupes"):
        return ""
    # PDF = thème CLAIR ; largeur imprimée maîtrisée (contenu A4 ≈ 170 mm) → échelle chiffrée possible.
    plan = plan_cle_svg(scene, theme="clair") or ""
    figures = [coupe_svg(c, theme="clair", largeur_mm=170) for c in scene["coupes"]]
    figures = [f for f in figures if f]
    if not figures:
        return ""
    corps = ('<div class="coupes3d" style="page-break-before:always">'
             '<h3>Terrain réel — coupes (pilote 3D)</h3>'
             f'<div class="plan2d">{plan}</div>')
    for fig in figures:
        corps += f'<div class="plan2d" style="margin-top:8px">{fig}</div>'
    corps += ('</div>' + note(
        "Cotes indicatives issues du MNT LiDAR HD IGN à 1 m (REUN89). Échelle horizontale = verticale "
        "(aucune exagération). Une coupe s'interrompt au droit d'une lacune. Aucun plafond de hauteur "
        "n'est dessiné. Précision locale à établir."))
    return corps


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
    # FAISA-REGLES-1 (D-026) — parcelle à cheval : le PDF GARDE la mise en garde (contenance, zone
    # constructible servie, part NON constructible). Sans elle, le document imprimé — celui qui circule —
    # masquait que l'essentiel du terrain est inconstructible (le gabarit n'est calculé que sur la part
    # constructible). `surfaceNote` est calculée au back (api/gabarit), identique à l'écran.
    _note_cheval = getattr(gr, "surfaceNote", None) if gr is not None else None
    if _note_cheval:
        _pct_c = getattr(gr, "pctPortionZone", None)
        _txt = esc(_note_cheval)
        if isinstance(_pct_c, (int, float)) and _pct_c < 100:
            _txt += f" Part NON constructible (zone A/N) : ~{round(100 - _pct_c)} % de la parcelle — hors gabarit."
        corps += verdict(_txt, "warn")
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
    # DOCS-1 — la SUP vient de la FICHE (même lecteur que le Dossier). Quand la fiche en sert une,
    # on l'affiche ET on retire la règle « Servitudes d'utilité publique » du moteur (qui ne voit que
    # la géométrie modélisée et écrirait « Aucune SUP » — la contradiction que le banc refusait).
    sup_html = _sup_fiche_ligne(valeurs)
    corps += sup_html
    _sup_servie = bool(sup_html)

    def _sans_sup(rules):
        if not _sup_servie or not rules:
            return rules
        return [r for r in rules
                if not str(getattr(r, "label", "") or "").startswith("Servitudes d'utilité publique")]

    ra = _regles(_sans_sup(getattr(gr, "appliedRules", None)), appliquees=True) if gr is not None else ""
    if ra:
        corps += "<h3>Règles appliquées</h3>" + ra
    rni = _regles(_sans_sup(getattr(gr, "nonIntegratedRules", None)), appliquees=False) if gr is not None else ""
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
    # GABARIT-3D-1 (pilote) — l'export reprend la SCÈNE (terrain réel) : plan-clé + deux coupes
    # vectorielles (SVG serveur, sans réseau ni GPU). GATÉ sur ctx['scene3d'] : absent dans le
    # document par défaut → PDF inchangé pour tous (interrupteur réservé au pilote admin).
    scene3d = (ctx or {}).get("scene3d") if isinstance(ctx, dict) else None
    if scene3d:
        corps += _bloc_coupes_pilote(scene3d)
    corps += note("Gabarit réglementaire 2D, pré-faisabilité sur règlement public. Une étude par un "
                  "professionnel peut modifier ces valeurs.")
    # DOCS-DA-1 (V10) — plus de ligne « Sources : » sous la section (comme le Dossier) ; les sources
    # restent portées par les badges de nature et le pied légal du document.
    return section("Enveloppe réglementaire (gabarit)", corps)
