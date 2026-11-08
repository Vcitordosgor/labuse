"""EXPORTS-1 lot 3 (3.2/3.5) — LE bloc « Potentiel constructible » unique.

L'audit EXPORTS (A3) a mesuré quatre verdicts incompatibles sur la même parcelle : «127 m²»
(table orpheline `parcel_residuel_bati`, bâtisseur retiré du code le 24/07, données figées),
«SDP résiduelle 0» (run), «aucun droit à bâtir… surélévation ~6,6 m» (FAÎTAGE de la table
morte) et «635 m² vendables» (moteur commun, ÉGOUT). Ici : UNE fonction, trois lignes
(au sol / en hauteur / table rase) + une phrase de verdict, servie telle quelle à tous les
documents. La surélévation est recalculée au MOTEUR COMMUN — hauteur à l'ÉGOUT (`rules.he_m`),
repli faîtage SEULEMENT si l'égout est absent, avec avertissement (même doctrine que
`engine.estimate_capacity`, engine.py:285-297)."""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

#: un niveau habitable (même seuil que l'ancien bâtisseur — mandat segments, repris tel quel)
SURELEVATION_MARGE_MIN_M = 2.8
#: RECETTE-7 (E1) — toiture type ajoutée à une hauteur d'ÉGOUT pour l'estimer en FAÎTAGE (repli
#: quand la zone ne fixe pas de règle de faîtage) ; comble courant à La Réunion, à confirmer.
TOITURE_TYPIQUE_M = 2.5


# CIRCUIT-6 merge main — l'override « égout LiDAR d'abord » du lot 7 est RETIRÉ : main
# (RECETTE-10 T1) compare déjà égout mesuré↔règle d'égout et faîtage↔règle de faîtage via
# surelevation_mesuree (app.py) ; injecter l'égout ICI remettait l'égout face au faîtage.
def _hauteur_bati_m(session: Session, parcel_id: int) -> float | None:
    """Hauteur du bâti existant (BD TOPO, max des bâtiments intersectants) — même source que
    `residuel._niveaux_existants`."""
    h = session.execute(text(
        """SELECT max(NULLIF(b.attrs->>'hauteur','')::float)
           FROM spatial_layers b JOIN parcels p ON p.id = :pid
           WHERE b.kind='batiment' AND ST_Intersects(b.geom_2975, p.geom_2975)"""),
        {"pid": parcel_id}).scalar()
    return float(h) if h is not None else None


def surelevation(session: Session, parcel_id: int, rules=None,
                 ctx=None) -> dict:
    """Surélévation possible ? — moteur commun, ÉGOUT d'abord (3.2). Renvoie
    {possible, marge_m, base, hauteur_regle_m, hauteur_bati_m, avertissement|None} ;
    possible=None quand une des deux hauteurs manque (jamais un faux « non »)."""
    if rules is None or ctx is None:
        from .db import parcel_context
        from .zonage import resolve_zone
        ctx = ctx or parcel_context(session, parcel_id)
        if ctx is None or not ctx.zone:
            return {"possible": None, "marge_m": None, "base": None,
                    "hauteur_regle_m": None, "hauteur_bati_m": None,
                    "avertissement": "zone PLU non résolue — surélévation non évaluable"}
        rules = rules or resolve_zone(ctx.zone, ctx.commune)
    he = getattr(rules, "he_m", None) if rules else None
    hf = getattr(rules, "hf_m", None) if rules else None
    he_num = float(he) if isinstance(he, (int, float)) else None
    hf_num = float(hf) if isinstance(hf, (int, float)) else None
    avert = None
    # RECETTE-7 (E1) — LE BÂTI MESURÉ (BD TOPO, `_hauteur_bati_m`) est une hauteur au FAÎTAGE. On
    # le compare donc à la règle de FAÎTAGE de la zone (`hf_m`), jamais à l'égout : comparer un
    # faîtage mesuré à une règle d'égout (l'ancien défaut) sous-estimait la marge et concluait à
    # tort « non identifiée ». L'égout (`he_m`) ne sert que de repli, converti en faîtage estimé
    # (+ toiture type) AVEC avertissement — la marge est alors incertaine, pas un « non » ferme.
    if isinstance(hf, (int, float)):
        h_regle, base = float(hf), "faîtage"
    elif isinstance(he, (int, float)):
        h_regle, base = float(he) + TOITURE_TYPIQUE_M, "faîtage (estimé depuis l'égout)"
        avert = ("la zone ne fixe qu'une hauteur d'ÉGOUT ; la marge est estimée en ajoutant une "
                 f"toiture type (~{TOITURE_TYPIQUE_M:g} m) pour rester comparable au faîtage mesuré "
                 "(BD TOPO) — incertaine, à confirmer au règlement")
    else:
        return {"possible": None, "marge_m": None, "base": None,
                "hauteur_regle_m": None, "hauteur_bati_m": None,
                "avertissement": "aucune hauteur de zone exploitable — surélévation non évaluable"}
    h_bati = _hauteur_bati_m(session, parcel_id)
    if h_bati is None:
        return {"possible": None, "marge_m": None, "base": base,
                "hauteur_regle_m": h_regle, "hauteur_bati_m": None,
                "he_regle_m": he_num, "hf_regle_m": hf_num,
                "avertissement": "hauteur du bâti inconnue (BD TOPO) — surélévation non évaluable"}
    marge = round(h_regle - h_bati, 1)
    # RECETTE-7 (E1) — on ne conclut « non identifiée » (possible=False) que si la marge est nulle
    # sur la BONNE règle (faîtage). Quand la règle de faîtage est ESTIMÉE depuis l'égout (avert)
    # et que la marge est faible mais positive, le résultat est INCERTAIN (possible=None), jamais
    # un « non » ferme tiré d'une conversion approximative.
    if marge >= SURELEVATION_MARGE_MIN_M:
        possible: bool | None = True
    elif avert and marge > 0:
        possible = None
    else:
        possible = False
    return {"possible": possible, "marge_m": max(0.0, marge),
            "base": base, "hauteur_regle_m": h_regle, "hauteur_bati_m": h_bati,
            "he_regle_m": he_num, "hf_regle_m": hf_num,
            "avertissement": avert}


def surelevation_mesuree(he_regle, hf_regle, egout_mesure, faitage_mesure) -> dict | None:
    """RECETTE-10 T1 — surélévation quand le LiDAR HD a MESURÉ l'égout ET/OU le faîtage : on retient
    les DEUX contraintes de hauteur et on garde la PLUS SERRÉE (celle qui mord).

    L'invariant qui répare E1 (et son inverse, T1) : une règle d'ÉGOUT ne se compare QU'À une hauteur
    d'égout, une règle de FAÎTAGE QU'À une hauteur de faîtage. Comparer un égout mesuré à une règle de
    faîtage (le défaut T9→T1) gonflait la marge de plus du double ; l'inverse (E1) la sous-estimait.

    Exemple EL0157 : égout 7,0 (règle) − 3,0 (mesuré) = 4,0 m ; faîtage 10,0 (règle) − 6,9 (mesuré) =
    3,1 m → disponible réel 3,1 m, limité par le faîtage.

    Renvoie {marge_m, possible, contrainte, regle_m, mesure_m, contraintes[]} — `contrainte` nomme la
    hauteur qui mord (« égout »/« faîtage ») ; `contraintes` liste les deux calculs. None si aucune
    contrainte n'est calculable (aucune règle en regard d'une mesure)."""
    contraintes: list[dict] = []
    if isinstance(he_regle, (int, float)) and egout_mesure is not None:
        contraintes.append({"base": "égout", "regle_m": round(float(he_regle), 1),
                            "mesure_m": round(float(egout_mesure), 1),
                            "marge_m": round(float(he_regle) - float(egout_mesure), 1)})
    if isinstance(hf_regle, (int, float)) and faitage_mesure is not None:
        contraintes.append({"base": "faîtage", "regle_m": round(float(hf_regle), 1),
                            "mesure_m": round(float(faitage_mesure), 1),
                            "marge_m": round(float(hf_regle) - float(faitage_mesure), 1)})
    if not contraintes:
        return None
    mordante = min(contraintes, key=lambda c: c["marge_m"])   # la plus serrée décide
    return {"marge_m": mordante["marge_m"],
            "possible": mordante["marge_m"] >= SURELEVATION_MARGE_MIN_M,
            "contrainte": mordante["base"], "regle_m": mordante["regle_m"],
            "mesure_m": mordante["mesure_m"], "contraintes": contraintes}


def bloc_potentiel(session: Session, parcel_id: int, fz=None) -> dict | None:
    """LE bloc Potentiel à trois lignes + verdict (3.5) — servi tel quel à tous les documents.

    - au_sol   : SDP résiduelle du run SERVI (`parcel_residuel`), lue TELLE QUELLE ;
    - en_hauteur : surélévation au moteur commun (égout — 3.2) ;
    - table_rase : le scénario du moteur commun (vendable APRÈS plafond de densité et
      stationnement — 3.3 ; le nombre de logements, lui, vit dans l'Étude de faisabilité).
    None si la parcelle est inconnue.

    FAISABILITE-clip (Vic 24/09/2026) — la garde de lecture « zone dominante A/N → 0 »
    (`garde_sdp_residuelle`) est RETIRÉE : elle appliquait l'ancien tout-ou-rien, contredit par
    l'assiette clippée (le run servi porte déjà la portion U/AU des parcelles à cheval)."""
    from .db import parcel_faisabilite
    from .zonage import resolve_zone
    fz = fz or parcel_faisabilite(session, parcel_id)
    ctx = fz[0] if fz else None
    if ctx is None:
        from .db import parcel_context
        ctx = parcel_context(session, parcel_id)
        if ctx is None:
            return None
    # au sol — le chiffre du run servi, LU TEL QUEL (assiette clippée : la portion U/AU est déjà
    # dans parcel_residuel ; plus de garde « dominante A/N → 0 »).
    row = session.execute(text(
        "SELECT sdp_residuelle_m2, cause FROM parcel_residuel WHERE parcel_id = :p"),
        {"p": parcel_id}).mappings().first()
    sdp_servie = float(row["sdp_residuelle_m2"]) if row and row["sdp_residuelle_m2"] is not None else None
    # CLASSEMENT-USAGE-1 — zone FERMÉE à l'urbanisation (règle unique `potentiel_batir`, verdict-driven :
    # cause résiduelle / constructibilité / statut AU — jamais la famille de zone nue, l'assiette clippée
    # des parcelles à cheval reste intacte). On BORNE la SDP au sol à 0 ET on ferme le scénario table rase,
    # même quand le run servi stocke un chiffre SANS cause et que le moteur live diverge du cache
    # (ex. 97422000AX1253, 2AUe declasse_zone_fermee = 25 426 m²). Le PDF ne sert aucun potentiel sur une
    # zone fermée — la ligne « potentiel à bâtir » dit « rien à bâtir », les scénarios suivent.
    from .potentiel_batir import est_ferme_parcel
    _ferme = est_ferme_parcel(session, parcel_id)
    if _ferme and sdp_servie is not None and sdp_servie > 0:
        sdp_servie = 0.0
    # DOCS-1 (décision Vic) — PPR-PARTIEL : parcelle que le run FERME (cause résiduelle présente) mais qui
    # est constructible sur la partie hors zone rouge. Le run ne chiffre PAS cette partie (il la disait
    # rédhibitoire) : AUCUNE ligne de capacité ne doit dire « rien à construire / capacité nulle / non
    # constructible ». On RENVOIE à l'Étude (qui découpe le rouge). Le gate `row.cause` est REQUIS : une
    # parcelle au run NON fermé (cause None) garde sa vraie capacité (jamais un renvoi abusif). SOURCE
    # UNIQUE verdict_ppr_partiel (touche du rouge partiel + hors-rouge exploitable + moteur constructible).
    _ppr_partiel = False
    if row is not None and row["cause"] is not None:
        from .db import verdict_ppr_partiel as _vpp
        try:
            _ppr_partiel = bool(_vpp(session, parcel_id))
        except Exception:  # noqa: BLE001 — best-effort, jamais une 500
            _ppr_partiel = False
    au_sol = {"sdp_residuelle_m2": None if _ppr_partiel else sdp_servie,
              "cause": row["cause"] if row else None,
              "renvoi_etude": _ppr_partiel,
              "source": "run résiduel servi (assiette clippée)"}
    # en hauteur — moteur commun (égout)
    rules = resolve_zone(ctx.zone, ctx.commune) if ctx.zone else None
    en_hauteur = surelevation(session, parcel_id, rules=rules, ctx=ctx)
    # DOCS-1 (décision Vic) — MÊME lecteur que la fiche/Dossier : quand le LiDAR HD a mesuré l'égout et/
    # ou le faîtage, la marge de surélévation est la MESURÉE (elle peut être NÉGATIVE — le bâti existant
    # dépasse déjà la règle), jamais celle, bornée à 0, déduite du bâti BD TOPO. Même calcul que la fiche
    # (app.py §surélévation → potentiel_transformation.hauteur_marge_m, lu par `marge_surelevation_m`).
    try:
        from .hauteur_lidar import hauteur_lidar_servie
        _idu = session.execute(text("SELECT idu FROM parcels WHERE id = :p"),
                               {"p": parcel_id}).scalar()
        _lid = hauteur_lidar_servie(session, _idu) if _idu else None
        if _lid and (_lid.get("egout_m") is not None or _lid.get("faitage_m") is not None):
            _sm = surelevation_mesuree(en_hauteur.get("he_regle_m"), en_hauteur.get("hf_regle_m"),
                                       _lid.get("egout_m"), _lid.get("faitage_m"))
            if _sm:
                en_hauteur = {**en_hauteur, "marge_m": _sm["marge_m"], "possible": _sm["possible"],
                              "base": f"{_sm['contrainte']} mesuré (LiDAR HD)",
                              "mesure_m": _sm["mesure_m"], "regle_m": _sm["regle_m"]}
    except Exception:  # noqa: BLE001 — LiDAR indisponible (dev/test) : on garde la marge BD TOPO
        pass
    # table rase — le scénario du moteur commun
    f = fz[1] if fz else None
    fo = (f.fourchette or {}) if f else {}
    # LOGEMENTS-SOURCE-UNIQUE — `logements` (fourchette de l'ancien calcul de capacité,
    # SDP ÷ logement moyen) RETIRÉ du bloc et du verdict : le nombre de logements ne se lit que
    # dans l'Étude de faisabilité (moteur d'implantation) — les lecteurs (Flash) impriment le renvoi.
    # CLASSEMENT-USAGE-1 — en zone fermée, le scénario « table rase » est lui aussi fermé (sinon le PDF
    # afficherait « ~N m² vendables » sous une parcelle dite « rien à bâtir » — contradiction interne).
    table_rase = {"constructible": True if _ppr_partiel
                  else (bool(f.constructible) if f else False) and not _ferme,
                  "vendable_m2": None if (_ferme or _ppr_partiel) else fo.get("shab_vendable_m2"),
                  "plancher_m2": None if (_ferme or _ppr_partiel) else fo.get("surface_plancher_m2"),
                  "renvoi_etude": _ppr_partiel,
                  "mention": "après plafond de densité et stationnement"}
    # verdict — une phrase, composée des trois lignes
    morceaux: list[str] = []
    # PPR-PARTIEL — jamais « au sol : rien à construire » ni « table rase non constructible » (voir plus
    # bas) : la capacité hors rouge est à l'Étude. On garde la marge de surélévation (si bâti), utile.
    if sdp_servie is not None and not _ppr_partiel:
        morceaux.append("au sol : rien à construire" if sdp_servie <= 0
                        else f"au sol : ~{round(sdp_servie)} m² de SDP restante")
    # RECETTE-11 A6 — plus de verdict de faisabilité (« possible »/« pas de marge ») : on énonce la
    # marge mesurée sous la règle de hauteur et la contrainte, le lecteur conclut.
    # DOCS-1 (décision Vic) — une marge NÉGATIVE n'est pas une « marge ~−3,3 m » : le bâti existant
    # DÉPASSE déjà la hauteur autorisée ; on le dit en clair.
    if en_hauteur.get("marge_m") is not None and en_hauteur.get("base"):
        _mg = float(en_hauteur["marge_m"])
        # DOCS-1 (décision Vic) — UNE décimale, virgule française : MÊME format que la ligne « Marge de
        # surélévation » du Dossier (« 11,0 m ») ; le `:g` d'avant servait « 11 » et divergeait d'« 11,0 »
        # sur les marges entières (un fait = une valeur = un format).
        _mg_fr = f"{abs(_mg):.1f}".replace(".", ",")
        if _mg < 0:
            morceaux.append(f"le bâti existant dépasse la hauteur autorisée de {_mg_fr} m")
        else:
            morceaux.append(f"marge en hauteur ~{_mg_fr} m sous la hauteur {en_hauteur['base']}")
    if _ppr_partiel:
        # la capacité hors zone rouge est celle de l'Étude (qui découpe le rouge) — jamais « nulle ».
        morceaux.append("capacité à l'Étude de faisabilité (zone rouge retirée)")
    elif table_rase["constructible"] and table_rase["vendable_m2"]:
        morceaux.append(f"en table rase : ~{round(table_rase['vendable_m2'])} m² "
                        f"vendables ({table_rase['mention']})")
    elif f is not None and not table_rase["constructible"]:
        # DOCS-1 (décision Vic) — jamais un code brut (« zone_transition ») dans un document client.
        _cause_clair = {
            "zone_transition": "zone de transition, fermée à l'urbanisation",
            "habitat_interdit": "habitat interdit par le règlement de la zone",
            "ppr_rouge": "zone rouge du PPR",
            "emprise_pleine": "emprise déjà saturée",
        }.get(f.cause, str(f.cause).replace("_", " ") if f.cause else "règles de zone")
        morceaux.append(f"table rase non constructible ({_cause_clair})")
    if not morceaux:
        # rien d'évaluable (base vide, zone non résolue) : section OMISE — jamais un bloc creux
        return None
    # DOCS-1 (décision Vic) — capitalise la 1ʳᵉ lettre SANS abaisser le reste (sinon « LiDAR HD » →
    # « lidar hd »). Le reste de la phrase garde sa casse d'origine.
    _verdict = " · ".join(morceaux)
    return {"au_sol": au_sol, "en_hauteur": en_hauteur, "table_rase": table_rase,
            "verdict": (_verdict[:1].upper() + _verdict[1:]) if _verdict else _verdict}
