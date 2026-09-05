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
        from .plu_rules import resolve_zone
        ctx = ctx or parcel_context(session, parcel_id)
        if ctx is None or not ctx.zone:
            return {"possible": None, "marge_m": None, "base": None,
                    "hauteur_regle_m": None, "hauteur_bati_m": None,
                    "avertissement": "zone PLU non résolue — surélévation non évaluable"}
        rules = rules or resolve_zone(ctx.zone, ctx.commune)
    he = getattr(rules, "he_m", None) if rules else None
    hf = getattr(rules, "hf_m", None) if rules else None
    avert = None
    if isinstance(he, (int, float)):
        h_regle, base = float(he), "égout"
    elif isinstance(hf, (int, float)):
        h_regle, base = float(hf), "faîtage (repli)"
        avert = ("hauteur d'égout non calibrée pour cette zone — marge estimée depuis le "
                 "faîtage (majorant prudent à confirmer au règlement)")
    else:
        return {"possible": None, "marge_m": None, "base": None,
                "hauteur_regle_m": None, "hauteur_bati_m": None,
                "avertissement": "aucune hauteur de zone exploitable — surélévation non évaluable"}
    h_bati = _hauteur_bati_m(session, parcel_id)
    if h_bati is None:
        return {"possible": None, "marge_m": None, "base": base,
                "hauteur_regle_m": h_regle, "hauteur_bati_m": None,
                "avertissement": "hauteur du bâti inconnue (BD TOPO) — surélévation non évaluable"}
    marge = round(h_regle - h_bati, 1)
    return {"possible": marge >= SURELEVATION_MARGE_MIN_M, "marge_m": max(0.0, marge),
            "base": base, "hauteur_regle_m": h_regle, "hauteur_bati_m": h_bati,
            "avertissement": avert}


def bloc_potentiel(session: Session, parcel_id: int, fz=None) -> dict | None:
    """LE bloc Potentiel à trois lignes + verdict (3.5) — servi tel quel à tous les documents.

    - au_sol   : SDP résiduelle du run SERVI (`parcel_residuel`), passée par la garde de
      lecture ZONE-1 (dominante A/N → 0, cause dite) ;
    - en_hauteur : surélévation au moteur commun (égout — 3.2) ;
    - table_rase : le scénario du moteur commun (vendable, logements APRÈS plafond de
      densité et stationnement — 3.3).
    None si la parcelle est inconnue."""
    from .db import parcel_faisabilite
    from .plu_rules import resolve_zone
    from .zone_servie import garde_sdp_residuelle
    fz = fz or parcel_faisabilite(session, parcel_id)
    ctx = fz[0] if fz else None
    if ctx is None:
        from .db import parcel_context
        ctx = parcel_context(session, parcel_id)
        if ctx is None:
            return None
    # au sol — le chiffre du run servi, sous garde de lecture
    row = session.execute(text(
        "SELECT sdp_residuelle_m2, cause FROM parcel_residuel WHERE parcel_id = :p"),
        {"p": parcel_id}).mappings().first()
    sdp_brute = float(row["sdp_residuelle_m2"]) if row and row["sdp_residuelle_m2"] is not None else None
    sdp_servie, garde_cause = garde_sdp_residuelle(sdp_brute, ctx.zone_fam, ctx.zone)
    au_sol = {"sdp_residuelle_m2": sdp_servie,
              "cause": garde_cause or (row["cause"] if row else None),
              "source": "run résiduel servi (garde de lecture zone dominante)"}
    # en hauteur — moteur commun (égout)
    rules = resolve_zone(ctx.zone, ctx.commune) if ctx.zone else None
    en_hauteur = surelevation(session, parcel_id, rules=rules, ctx=ctx)
    # table rase — le scénario du moteur commun
    f = fz[1] if fz else None
    fo = (f.fourchette or {}) if f else {}
    table_rase = {"constructible": bool(f.constructible) if f else False,
                  "vendable_m2": fo.get("shab_vendable_m2"),
                  "plancher_m2": fo.get("surface_plancher_m2"),
                  "logements": fo.get("logements_au_sol"),
                  "mention": "après plafond de densité et stationnement"}
    # verdict — une phrase, composée des trois lignes
    morceaux: list[str] = []
    if sdp_servie is not None:
        morceaux.append("au sol : rien à construire" if sdp_servie <= 0
                        else f"au sol : ~{round(sdp_servie)} m² de SDP résiduelle")
        if garde_cause:
            morceaux[-1] += f" ({garde_cause})"
    if en_hauteur.get("possible"):
        morceaux.append(f"surélévation possible (~{en_hauteur['marge_m']:g} m sous "
                        f"la hauteur {en_hauteur['base']})")
    elif en_hauteur.get("possible") is False:
        morceaux.append("pas de marge de surélévation")
    if table_rase["constructible"] and table_rase["vendable_m2"]:
        lo, hi = (table_rase.get("logements") or (None, None))
        logts = f", {lo}–{hi} logements" if lo is not None else ""
        morceaux.append(f"en table rase : ~{round(table_rase['vendable_m2'])} m² "
                        f"vendables{logts} ({table_rase['mention']})")
    elif f is not None and not table_rase["constructible"]:
        morceaux.append(f"table rase non constructible ({f.cause or 'règles de zone'})")
    if not morceaux:
        # rien d'évaluable (base vide, zone non résolue) : section OMISE — jamais un bloc creux
        return None
    return {"au_sol": au_sol, "en_hauteur": en_hauteur, "table_rase": table_rase,
            "verdict": " · ".join(morceaux).capitalize()}
