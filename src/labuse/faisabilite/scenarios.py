"""FAISABILITE-3 (Vic 27/09/2026) — UNE fonction de faisabilité, DEUX scénarios.

`faisabilite_scenario(session, parcel_id, scenario, hyp_overrides, test)` assemble LE panneau de
la maquette validée à partir du MOTEUR EXISTANT, sans dupliquer aucun calcul :

  · **terrain_libere** (défaut) : l'enveloppe du terrain, bâti existant compté à 0 =
    `parcel_faisabilite` tel quel (SDP = min(zone d'implantation, emprise max) × niveaux × occupation).
    La surface à démolir (emprise bâtie BD TOPO × niveaux LiDAR) est renvoyée pour affichage.
  · **bati_garde** : le chemin du RÉSIDUEL SERVI (`compute_residuel`, DONNEES-FIX-1 — bâti conservé,
    SDP existante déduite, hauteur LiDAR). Golden 55 : la SDP possible == la vue `parcel_residuel`.

Sur une parcelle NUE, un seul scénario (`bati_present=False`). À CHEVAL, l'enveloppe est déjà
calculée sur la portion constructible (moteur GEOMETRIE-1) et la surface de la portion est renvoyée.
AU non ouverte → 0 partout, motif « zone AU non ouverte à l'urbanisation ». HABITAT INTERDIT →
`logement_autorise=False` + citation. Rien n'est deviné côté front : verdict, « ce qui limite »,
les 8 étapes, la section PLU et le test d'un projet viennent TOUS d'ici (aucun calcul dans le front).
"""
from __future__ import annotations

import math

from sqlalchemy.orm import Session

SCENARIOS = ("terrain_libere", "bati_garde")
_DEFAUT = "terrain_libere"


def _norm_scenario(s: str | None) -> str:
    return s if s in SCENARIOS else _DEFAUT


def _rng_bati_garde(log_enveloppe: list[int], sdp_residuelle: float,
                    sdp_enveloppe: float) -> tuple[int, int]:
    """Logements du scénario « bâti gardé » = ceux de l'enveloppe (déjà plafonnés densité ∩
    stationnement ∩ modulation par le moteur), mis à l'échelle du plancher RÉSIDUEL restant
    (`sdp_residuelle / sdp_enveloppe`). Toujours ≤ terrain libéré (on ne loge jamais PLUS en
    gardant un bâti) et sans dupliquer le pipeline de plafonds du moteur."""
    if sdp_enveloppe <= 0:
        return 0, 0
    ratio = max(0.0, min(1.0, sdp_residuelle / sdp_enveloppe))
    lo = math.floor(int(log_enveloppe[0]) * ratio)
    hi = math.ceil(int(log_enveloppe[1]) * ratio)
    return max(0, lo), max(0, hi)


def _fmt_range(lo: int, hi: int) -> str:
    return f"{lo}" if lo == hi else f"{lo}–{hi}"


def _fmt_m2(v) -> str:
    return f"{round(v):,}".replace(",", " ") + " m²" if v is not None else "—"


def _plu_section(commune, zone_code, idu, rules):
    """Section « Ce que le PLU permet » — RÉUTILISE `resolve_reglement` (articles + pages cliquables),
    puis (Lot D) : hauteur au prospect → « non chiffrée (calculée par parcelle) » ; ligne mixité
    sociale ajoutée (validée → seuil/quota sourcés ; propose/absente → « non modélisée »)."""
    from ..plu_reglement import resolve_reglement
    idurba = None  # l'insee de l'annuaire se dérive du préfixe idu ci-dessous
    ref = resolve_reglement(commune, zone_code, idurba)
    if ref is None:
        return None
    # insee pour le deep-link annuaire (le front ouvre l'annuaire PLU sur la bonne commune/zone).
    if idu and len(idu) >= 5:
        ref.setdefault("annuaire", {})
        ref["annuaire"] = {"insee": idu[:5], "zone": zone_code}
    rv = ref.get("regles_valeurs") or []
    # Hauteur au PROSPECT (Ud/Uu) : la hauteur dépend de la voie desservante — non chiffrable au
    # niveau de la zone. On le DIT (jamais « non réglementé » qui laisserait croire à un silence).
    if rules is not None and getattr(rules, "hauteur_mode", None) == "prospect":
        for row in rv:
            if row.get("cle") == "hauteur":
                row["valeur"] = "au prospect L≥H (calculée par parcelle, selon la voie)"
                row["etat"] = "prospect"
    # Ligne MIXITÉ SOCIALE (Lot D) — validée : seuil + quota sourcés ; propose/absente : « non modélisée ».
    mx = getattr(rules, "mixite", None) if rules is not None else None
    if isinstance(mx, dict) and mx.get("statut") == "valide" and mx.get("quota_pct"):
        seuil = mx.get("seuil_logements")
        art = (mx.get("article") or "").strip()
        page = mx.get("page_pdf")
        _ref = (f"{art}" + (f" · p.{page}" if page else "")) if art else None
        rv.append({"cle": "mixite", "libelle": "Mixité sociale",
                   "valeur": f"{float(mx['quota_pct']):.0f} % de logements aidés"
                             + (f" dès {int(seuil)} logts" if seuil is not None else ""),
                   "etat": "chiffre", "reference": _ref, "url": ref.get("url_document")})
    elif isinstance(mx, dict) and mx.get("statut") == "propose":
        rv.append({"cle": "mixite", "libelle": "Mixité sociale",
                   "valeur": "non modélisée (clause détectée mais non validée)",
                   "etat": "non_modelisee", "reference": None, "url": None})
    else:
        rv.append({"cle": "mixite", "libelle": "Mixité sociale",
                   "valeur": "non modélisée pour cette zone", "etat": "non_modelisee",
                   "reference": None, "url": None})
    ref["regles_valeurs"] = rv
    return ref


def _cause_limite(f, zone: str) -> tuple[str, str, bool]:
    """(verdict, ce_qui_limite, logement_autorise) pour une parcelle NON constructible.
    La contrainte active est la CAUSE STRUCTURÉE du moteur — jamais devinée au front."""
    cause = f.cause
    z = (zone or "").strip()
    if cause == "habitat_interdit":
        return (f.verdict, "Habitat interdit dans cette zone (vocation économique/activités).", False)
    if cause == "zone_transition":
        if "AU" in z.upper():   # 2AU, 1AUc, AUst… — famille AU non ouverte à l'urbanisation
            return ("Zone AU non ouverte à l'urbanisation — rien de constructible en l'état "
                    f"(zone {z}).", "Zone AU non ouverte à l'urbanisation.", True)
        return (f.verdict, f"Construction neuve non autorisée en zone {z}.", True)
    if cause == "terrain_exigu":
        # RECETTE-1 A1 — « ce qui limite » suit la RAISON réelle du vidage (jamais « reculs » par
        # défaut sur une parcelle vidée par un PPR rouge / un emplacement réservé / une portion U/AU).
        _lim = {
            "ppr_rouge": "Parcelle en PPR zone rouge (inconstructible).",
            "emplacement_reserve": "Emplacement réservé couvrant la parcelle.",
            "ebc": "Espace boisé classé couvrant la parcelle.",
            "contraintes": "Contraintes géométriques certaines (PPR/PEB/ravine/50 pas).",
            "portion_reduite": "Portion constructible U/AU réduite (parcelle à cheval).",
        }.get(getattr(f, "exigu_raison", None) or "",
              "Terrain trop exigu compte tenu des reculs.")
        return (f.verdict, _lim, True)
    if cause == "redhibitoire":
        return (f.verdict, "Contrainte rédhibitoire (voir les modulations réunionnaises).", True)
    if cause == "hauteur_indispo":
        return (f.verdict, "Hauteur de zone non calibrée au règlement.", True)
    if cause == "regle_plu_non_validee":
        return (f.verdict, "Règle(s) PLU non validée(s) — capacité non calculable.", True)
    return (f.verdict, "Parcelle non constructible en l'état.", True)


def faisabilite_scenario(session: Session, parcel_id: int, scenario: str | None = None,
                         hyp_overrides: dict | None = None, test: dict | None = None) -> dict | None:
    """UNE fonction, deux scénarios. None si la parcelle est hors PLU (zone introuvable)."""
    from .db import parcel_faisabilite
    from .engine import Hypotheses, appliquer_overrides_hypotheses, hypotheses_modifiables
    from .residuel import compute_residuel
    from .zonage import reglement_source, resolve_zone

    from sqlalchemy import text

    scenario = _norm_scenario(scenario)
    res = parcel_faisabilite(session, parcel_id, hyp_overrides=hyp_overrides)
    if res is None:
        return None
    ctx, f = res
    fr = f.fourchette or {}
    zone = f.zone

    # ALGO-FIX-1 (point 3) — HORS SAISIE (aucun chiffre saisi par l'utilisateur), la SDP RÉSIDUELLE
    # montrée au client vient du RUN SERVI (vue `parcel_residuel`), PAS du moteur live : une seule
    # vérité, la MÊME que la fiche §Potentiel et le Dossier (garde + §10). Le moteur live ne recalcule
    # QUE sur des chiffres SAISIS (overrides d'hypothèses ou test d'un projet). `sdp_servie` None =
    # chaîne résiduel absente (base de test) → repli sur le calcul live, comme avant.
    sans_saisie = not test and not hyp_overrides
    sdp_servie = None
    if sans_saisie:
        try:
            sdp_servie = session.execute(text(
                "SELECT sdp_residuelle_m2 FROM parcel_residuel WHERE parcel_id = :p"),
                {"p": parcel_id}).scalar()
        except Exception:  # noqa: BLE001 — vue résiduel absente : on garde le calcul live
            sdp_servie = None

    # hypothèses EFFECTIVES (après overrides) — pour dériver les logements du scénario bâti gardé
    # avec EXACTEMENT la même convention que le moteur (aucune divergence).
    hyp = Hypotheses.charger(ctx.commune)
    if hyp_overrides:
        appliquer_overrides_hypotheses(hyp, hyp_overrides)
    logt_moyen = (hyp.logement_m2_bas + hyp.logement_m2_haut) / 2.0

    # ── Bâti existant (résiduel servi) — présence + numéros du scénario « bâti gardé » ──
    try:
        residuel = compute_residuel(session, parcel_id, faisa=res, assiette_clippee=True)
    except Exception:  # noqa: BLE001 — le résiduel ne casse jamais le panneau
        residuel = {"disponible": False}
    emprise_batie = residuel.get("emprise_batie_m2") if residuel.get("disponible") else None
    # « bâti présent » = la MÊME définition que le résiduel (taux d'emprise ≥ 2 % → plus « terrain nu ») :
    # sous ce seuil, quelques m² de bruit CoSIA/BD TOPO ne font pas un bâti à conserver (parcelle nue,
    # un seul scénario). `taux_emprise_pct` peut être None (non calculé) → repli sur l'emprise absolue.
    _taux = residuel.get("taux_emprise_pct")
    bati_present = bool(residuel.get("disponible")
                        and ((_taux is not None and _taux >= 2)
                             or (_taux is None and (emprise_batie or 0) > 10)))
    # pas de bâti → un seul scénario (le front masque la carte « En gardant le bâti »).
    if scenario == "bati_garde" and not bati_present:
        scenario = "terrain_libere"

    reg = reglement_source(ctx.commune) or {}
    rules_pan = resolve_zone(zone, ctx.commune) if zone else None
    plu = _plu_section(ctx.commune, zone, ctx.idu, rules_pan)

    # portion constructible (à cheval) — la surface de la portion U/AU sur laquelle l'enveloppe est calculée
    portion_m2 = None
    portion_zone = None
    if ctx.a_cheval and ctx.zone_parts:
        from .zone_servie import FAMILLES_CONSTRUCTIBLES
        cst = [p for p in ctx.zone_parts if p.get("fam") in FAMILLES_CONSTRUCTIBLES]
        if cst:
            pct = sum(float(p.get("pct") or 0) for p in cst)
            portion_m2 = round(ctx.surface_m2 * pct / 100.0)
            portion_zone = max(cst, key=lambda p: float(p.get("pct") or 0)).get("zone")

    badges = {
        "regles_sourcees": bool(f.calibree),
        "plancher_estime": True,   # occupation/rendement sont TOUJOURS des hypothèses (Estimé)
        "plu_approuve_le": reg.get("approbation") or None,
    }
    base = {
        "idu": ctx.idu, "zone": zone, "commune": ctx.commune,
        "surface_m2": round(ctx.surface_m2), "calibree": bool(f.calibree),
        "a_cheval": ctx.a_cheval, "portion_constructible_m2": portion_m2, "portion_zone": portion_zone,
        "scenario": scenario, "bati_present": bati_present,
        "bati_libelle": (f"{round(emprise_batie)} m² bâtis · {residuel.get('niveaux_existants')} niveau(x)"
                         f" ({residuel.get('hauteur_source')})" if bati_present else None),
        "constructible": bool(f.constructible),
        "cause": f.cause,
        "badges": badges, "bandeau": f.bandeau, "plu": plu,
        "hypotheses_modifiables": hypotheses_modifiables(hyp),
        "hypotheses_notes": f.hypotheses, "avertissements": f.avertissements, "modulation": f.modulation,
    }
    # CHASSE-FIX-1 (C06) — zone AU à ouverture bloquée : capacité servie mais JAMAIS présentée
    # disponible. Règle et libellé uniques (au_differe), les mêmes que la fiche §Potentiel.
    from .au_differe import libelle_differe, statut_differe
    _diff = statut_differe(session, parcel_id=parcel_id)
    base["capacite_differee"] = _diff is not None
    base["capacite_differee_detail"] = _diff
    if _diff is not None:
        base["avertissements"] = list(base.get("avertissements") or []) + [
            libelle_differe(sdp_servie)]

    # ── Cas NON constructible : 0 partout + motif, jamais un chiffre inventé ──
    if not f.constructible:
        verdict, limite, logement_ok = _cause_limite(f, zone)
        base.update({
            "logement_autorise": logement_ok, "verdict": verdict, "ce_qui_limite": limite,
            "sdp_possible_m2": 0, "logements": [0, 0], "stationnement_places": None,
            "surface_a_demolir_m2": None, "etapes": [],
            "test": _tester(test, 0, logement_ok, "terrain_libere", False, None, plu),
        })
        return base

    # ── Cas CONSTRUCTIBLE : valeurs des deux scénarios ──
    niveaux_max = fr.get("niveaux_max")
    niveaux_lbl = fr.get("niveaux")   # « R+2 »
    hauteur_m = fr.get("hauteur_m")
    sdp_enveloppe = fr.get("surface_plancher_m2") or 0.0
    zone_impl = fr.get("zone_implantation_m2")
    emprise_sol_max = fr.get("emprise_sol_max_m2")
    emprise_constructible = fr.get("emprise_constructible_m2")
    log_enveloppe = list(fr.get("logements_au_sol") or (0, 0))
    regime = fr.get("stationnement_regime")
    ppl = rules_pan.places_par_logement() if rules_pan is not None else None
    ppl_num = ppl if isinstance(ppl, (int, float)) else None

    sdp_existante = residuel.get("sdp_existante_m2") if bati_present else None
    sdp_residuelle = residuel.get("sdp_residuelle_m2") if bati_present else None
    # ALGO-FIX-1 (point 3) — hors saisie, la SDP résiduelle du scénario « bâti gardé » == la vue SERVIE
    # `parcel_residuel` (Golden 55 restauré : le moteur live avait dérivé, ex. EO0796 187 ≠ 179 servi).
    if sans_saisie and bati_present and sdp_servie is not None:
        sdp_residuelle = float(sdp_servie)

    if scenario == "bati_garde":
        sdp_possible = round(sdp_residuelle or 0)
        lo, hi = _rng_bati_garde([int(log_enveloppe[0]), int(log_enveloppe[1])],
                                 float(sdp_residuelle or 0), float(sdp_enveloppe or 0))
        logements = [lo, hi]
        surface_a_demolir = None
    else:  # terrain_libere
        if sans_saisie and not bati_present and sdp_servie is not None:
            # TERRAIN NU : « terrain libéré » EST le résiduel (rien à démolir) → la SDP SERVIE fait foi
            # (ex. AX0990 1 642 live → 1 619 servi), pas l'enveloppe recalculée à la volée.
            sdp_possible = round(float(sdp_servie))
            lo, hi = _rng_bati_garde([int(log_enveloppe[0]), int(log_enveloppe[1])],
                                     float(sdp_servie), float(sdp_enveloppe or 0))
            logements = [lo, hi]
        else:
            sdp_possible = round(sdp_enveloppe)
            logements = [int(log_enveloppe[0]), int(log_enveloppe[1])]
        surface_a_demolir = round(sdp_existante) if (bati_present and sdp_existante) else None

    log_max = max(logements) if logements else 0
    places = round(log_max * ppl_num) if ppl_num else None

    # Verdict + « ce qui limite »
    if scenario == "bati_garde":
        if log_max <= 0 or sdp_possible <= 30:
            verdict = f"Presque saturée : {_fmt_m2(sdp_possible)} de plancher encore possibles."
        else:
            verdict = (f"Encore {_fmt_m2(sdp_possible)} de plancher · "
                       f"{_fmt_range(logements[0], logements[1])} logement(s), bâti conservé.")
        limite = (f"le bâti existant conservé (~{_fmt_m2(sdp_existante)} de plancher déduits, "
                  f"{residuel.get('niveaux_existants')} niveau(x) au LiDAR).")
    else:
        if log_max <= 0:
            verdict = f"Jusqu'à {_fmt_m2(sdp_possible)} de plancher."
        else:
            verdict = (f"Jusqu'à {_fmt_m2(sdp_possible)} de plancher · "
                       f"{_fmt_range(logements[0], logements[1])} logement(s).")
        parts = []
        if emprise_sol_max is not None and rules_pan is not None and \
                isinstance(getattr(rules_pan, "emprise_sol_pct", None), (int, float)):
            parts.append(f"emprise au sol {rules_pan.emprise_sol_pct:g} %")
        if niveaux_lbl:
            parts.append(f"hauteur {hauteur_m:g} m ({niveaux_lbl})" if hauteur_m else f"hauteur ({niveaux_lbl})")
        if regime == "borne" and ppl_num:
            parts.append(f"stationnement {ppl_num:g} pl./logt")
        limite = " · ".join(parts) if parts else "les reculs, la hauteur et la pleine terre."
    if ctx.a_cheval and portion_m2:
        verdict += f" (sur les {_fmt_m2(portion_m2)} en {portion_zone})."

    # ── Les 8 ÉTAPES de la maquette (mêmes valeurs que le verdict — même appel) ──
    src = (rules_pan.sources if rules_pan is not None else {}) or {}
    if scenario == "bati_garde":
        e5_val = f"~{_fmt_m2(sdp_existante)} conservés"
        e6_val = f"~{_fmt_m2(sdp_possible)}"
    else:
        e5_val = ("~0 m²" if not bati_present
                  else f"0 m² (démolition de ~{_fmt_m2(surface_a_demolir)} à chiffrer)")
        e6_val = f"~{_fmt_m2(sdp_possible)}"
    if emprise_sol_max is not None:
        e2_val, e2_src = f"~{_fmt_m2(emprise_sol_max)}", src.get("emprise", "Art. 9")
        e2_prov = "sourcee"
    else:
        e2_val = f"~{_fmt_m2(emprise_constructible)} (non réglementée → bornée par les reculs)"
        e2_src, e2_prov = src.get("emprise", "Art. 9"), "absent"
    hauteur_src = src.get("hauteur", "Art. 10")
    bati_src = {"lidar": "égout LiDAR mesuré", "bdtopo": "BD TOPO (étages/hauteur)",
                "sans": "hauteur non ingérée — hypothèse prudente"}.get(residuel.get("hauteur_source"), "BD TOPO")
    etapes = [
        {"n": 1, "label": "Zone d'implantation après reculs", "valeur": f"~{_fmt_m2(zone_impl)}",
         "source": "reculs par côté (moteur gabarit) / géométrie réelle", "prov": "sourcee"},
        {"n": 2, "label": "Emprise au sol max", "valeur": e2_val, "source": e2_src, "prov": e2_prov},
        {"n": 3, "label": "Niveaux (hauteur)",
         "valeur": (f"{niveaux_max} · {niveaux_lbl}" if niveaux_max else niveaux_lbl or "—"),
         "source": hauteur_src, "prov": "sourcee"},
        {"n": 4, "label": "Plancher max (× occupation)", "valeur": f"~{_fmt_m2(sdp_enveloppe)}",
         "source": f"emprise bâtie × niveaux × occupation {hyp.coef_occupation:.0%}", "prov": "estimee"},
        {"n": 5, "label": "Bâti existant", "valeur": e5_val,
         "source": (bati_src if bati_present else "aucun bâti mesuré (terrain nu)"),
         "prov": "sourcee" if bati_present else "absent"},
        {"n": 6, "label": "Plancher possible", "valeur": e6_val,
         "source": ("plafond − bâti conservé" if scenario == "bati_garde"
                    else "enveloppe du terrain, bâti rasé"), "prov": "derive"},
        {"n": 7, "label": "Logements",
         "valeur": _fmt_range(logements[0], logements[1]) if log_max > 0 else "—",
         "source": f"plancher habitable ÷ {logt_moyen:g} m²/logt", "prov": "derive"},
        {"n": 8, "label": "Stationnement",
         "valeur": (f"~{places} place(s)" if places is not None else "non borné (non réglementé)"),
         "source": src.get("stationnement", "Art. 12") if regime == "borne" else "non réglementé",
         "prov": "sourcee" if regime == "borne" else "absent"},
    ]

    base.update({
        "logement_autorise": True, "verdict": verdict, "ce_qui_limite": limite,
        "sdp_possible_m2": sdp_possible, "logements": logements, "stationnement_places": places,
        "surface_a_demolir_m2": surface_a_demolir, "etapes": etapes,
        "test": _tester(test, sdp_possible, True, scenario, bati_present, ppl_num, plu,
                        demolition=surface_a_demolir),
    })
    return base


def _tester(test: dict | None, sdp_possible: float, logement_autorise: bool, scenario: str,
            bati_present: bool, ppl_num: float | None, plu: dict | None,
            demolition: float | None = None) -> dict | None:
    """« Tester un projet » — le RÉSULTAT vient du moteur (jamais du front). Champs vides →
    « à compléter » (jamais un résultat) ; zone sans logement → « non autorisé » + citation."""
    if not test:
        return None
    n = test.get("n_logements")
    s = test.get("surface_par_logement")
    try:
        n = int(n) if n not in (None, "") else 0
        s = float(s) if s not in (None, "") else 0.0
    except (TypeError, ValueError):
        n, s = 0, 0.0
    if not n or not s:
        return {"statut": "a_completer", "message": "indiquez un nombre de logements et une surface."}
    if not logement_autorise:
        return {"statut": "non_autorise",
                "message": "Logement non autorisé dans cette zone (habitat interdit au règlement)."}
    besoin = n * s
    places = round(n * ppl_num) if ppl_num else None
    if besoin <= sdp_possible:
        return {"statut": "tient", "besoin_m2": round(besoin), "possible_m2": round(sdp_possible),
                "places": places, "demolition_m2": (round(demolition) if scenario == "terrain_libere"
                                                     and bati_present and demolition else None)}
    return {"statut": "ne_tient_pas", "besoin_m2": round(besoin), "possible_m2": round(sdp_possible),
            "manque_m2": round(besoin - sdp_possible), "places": places}
