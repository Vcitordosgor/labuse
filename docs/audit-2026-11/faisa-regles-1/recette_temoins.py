"""FAISA-REGLES-1 — recette des six témoins (+ témoins Gabarit) : état APRÈS correctifs.

Le moteur n'invente jamais une règle. Une règle absente/non validée BLOQUE le calcul concerné et le DIT ;
elle n'est jamais remplacée par une valeur par défaut.

Témoins (mandat) :
  · RNU            97417000AT1496 (Saint-Philippe) — E-055 : aucune zone PLU → étude hors périmètre.
  · zone N         97424000AN0072 (Cilaos)         — D-004 : 100 % N → aucun programme de logements.
  · Uh < 6 m       97411000IN0347 (Saint-Denis)    — D-005 : R+0 essayé (plus « Impossible » pour la hauteur)
                                                      + E-056 : 617 m d'un TCSP → plafond L151 (seuil 800 m).
  · à cheval       97424000AE0050 (Cilaos)         — D-004/D-025 : zone servie = part constructible (Ub).
  · > 1 ha         97415000CT2637 (Saint-Paul)     — D-003/E-057 : résultat dans la borne, pas de 503.
  · falaise        97411000EY0173 (Saint-Denis)    — A-006 : pente « très forte » (max 43,9°), pas « modérée ».

Témoins Gabarit :
  · D-024 recul h/2  97411000IE0241 (Um) : recul séparatif 4 → 5 m (max(4, h/2), h=faîtage 10).
  · D-025/026 à cheval 97424000AE0050 : surfaceNote « parcelle à cheval » (écran == PDF).
  · D-028 disparue    97411000DR0042 : l'outil le DIT, pas de gabarit complet.

Fiche hauteur/pente : A-004 (97411000HC0139 copro, badge même nature), A-005 (97411000AO0753 nb_bati=0).
"""
import json
import signal
import time

from labuse.db import session_scope


class _TO(Exception):
    pass


def _etude(s, idu, cap_s=70):
    from labuse.implantation import service
    signal.signal(signal.SIGALRM, lambda *a: (_ for _ in ()).throw(_TO()))
    signal.alarm(cap_s)
    t0 = time.time()
    try:
        p = service.etudier_payload(s, {"idus": [idu], "type_projet": "collectif", "objectif": "equilibre"})
        signal.alarm(0)
        cm = p.get("capacite_maximale") or {}
        return {
            "secondes": round(time.time() - t0, 1),
            "zone_servie": p["entrees"]["zone"],
            "verdict": p["verdict"], "statut_global": p["statut_global"],
            "hors_perimetre": p.get("hors_perimetre"), "motif": p.get("motif_hors_perimetre"),
            "logements_max": cm.get("logements"), "niveaux": cm.get("niveaux_label"),
            "facteur_limitant": p.get("facteur_limitant"),
            "grille_note_presente": bool(p.get("grille_note")),
            "message": (p.get("message") or "")[:160],
            "pas_de_503": True,
        }
    except _TO:
        signal.alarm(0)
        s.rollback()
        return {"secondes": f">{cap_s}", "verdict": "TIMEOUT", "pas_de_503": False}


def _gabarit(s, idu):
    from labuse.gabarit.builder import (appliquer_note_a_cheval, build_gabarit_input,
                                        deduire_bati_de_zone, rescale_zone_contenance)
    from labuse.gabarit.engine import compute_gabarit
    from labuse import cadastre_disparue as cd
    disp = cd.info_disparue(s, idu)
    if disp:
        return {"disparue": True, "message": cd.phrase_disparue(disp)[:120],
                "gabarit_complet_servi": False}
    b = build_gabarit_input(s, idu)
    if b is None or b.blocking:
        return {"blocking": b.blocking if b else "inconnue"}
    gr = compute_gabarit(b.input)
    gr.raccordement = b.raccordement
    rescale_zone_contenance(s, idu, gr)
    appliquer_note_a_cheval(s, idu, gr)
    deduire_bati_de_zone(gr)
    plu = (b.raccordement or {}).get("plu") or {}
    return {"recul_sep_m": plu.get("recul_sep_m"), "recul_sep_formule": plu.get("recul_sep_formule"),
            "zone_implantation_m2": gr.zoneImplantationM2, "plafond_emprise_m2": gr.plafondEmpriseM2,
            "surfaceNote": gr.surfaceNote, "pctPortionZone": gr.pctPortionZone}


def _fiche_pente_hauteur(s, idu):
    from labuse import bati
    from labuse.api.app import _pente_bande
    row = s.execute(__import__("sqlalchemy").text(
        "SELECT pente_moy_deg, pente_max_deg, flag_terrassement_lourd FROM parcel_terrain WHERE idu=:i"),
        {"i": idu}).mappings().first()
    pente = None
    if row and row["pente_moy_deg"] is not None:
        pente = {"moy_deg": float(row["pente_moy_deg"]),
                 "max_deg": float(row["pente_max_deg"]) if row["pente_max_deg"] is not None else None,
                 "flag_terrassement": bool(row["flag_terrassement_lourd"]),
                 "bande": _pente_bande(float(row["pente_moy_deg"]),
                                       float(row["pente_max_deg"]) if row["pente_max_deg"] is not None else None,
                                       bool(row["flag_terrassement_lourd"]))}
    b = bati.le_bien_block(s, idu) or {}
    return {"pente": pente,
            "nb_batiments": b.get("nb_batiments"), "hauteur_bati_m": b.get("hauteur_bati_m"),
            "hauteur_nature": b.get("hauteur_nature"), "hauteur_note": b.get("hauteur_note"),
            "hauteur_discordante": b.get("hauteur_discordante"),
            "hauteur_discordance_motif": b.get("hauteur_discordance_motif"),
            "ecart_faitage_bdtopo_m": b.get("ecart_faitage_bdtopo_m"),
            "ecart_egout_bdtopo_m": b.get("ecart_egout_bdtopo_m")}


def _stationnement_800(s, idu):
    from labuse.implantation import service
    reg = service.stationnement_payload(s, [idu], "collectif")
    pf = reg["regimes"]["plafond_national"]
    return {"zone": reg["zone"],
            "plafond_national": None if pf is None else {
                "reference": pf["reference"], "ratio_plafond": pf["ratio_plafond"],
                "rayon_tcsp_m": pf.get("rayon_tcsp_m"), "distance_tcsp_m": pf.get("distance_tcsp_m"),
                "condition_remplie": pf.get("condition_tcsp_sous_500m"),
                "citation": pf["citation"][:200]}}


def main():
    out = {}
    with session_scope() as s:
        out["etude"] = {
            "RNU_AT1496": _etude(s, "97417000AT1496"),
            "zoneN_AN0072": _etude(s, "97424000AN0072"),
            "Uh_IN0347": _etude(s, "97411000IN0347"),
            "a_cheval_AE0050": _etude(s, "97424000AE0050"),
            "grande_CT2637": _etude(s, "97415000CT2637"),
            "falaise_EY0173": _etude(s, "97411000EY0173"),
        }
    with session_scope() as s:
        out["gabarit"] = {
            "D024_recul_IE0241_Um": _gabarit(s, "97411000IE0241"),
            "D025_026_a_cheval_AE0050": _gabarit(s, "97424000AE0050"),
            "D028_disparue_DR0042": _gabarit(s, "97411000DR0042"),
        }
    with session_scope() as s:
        out["fiche_hauteur_pente"] = {
            "A006_falaise_EY0173": _fiche_pente_hauteur(s, "97411000EY0173"),
            "A005_micro_AO0753": _fiche_pente_hauteur(s, "97411000AO0753"),
            "A004_copro_HC0139": _fiche_pente_hauteur(s, "97411000HC0139"),
        }
    with session_scope() as s:
        out["stationnement_800m_E056"] = {
            "Uh_IN0347_617m": _stationnement_800(s, "97411000IN0347"),  # 617 m : ancien 500 m = aucun plafond
            "IE0241_247m": _stationnement_800(s, "97411000IE0241"),
        }
    dst = "docs/audit-2026-11/faisa-regles-1/recette_temoins_resultat.json"
    with open(dst, "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(json.dumps(out, indent=2, ensure_ascii=False))
    print("\nécrit →", dst)


if __name__ == "__main__":
    main()
