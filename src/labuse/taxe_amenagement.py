"""K3 (rattrapage KelFoncier) — CALCULETTE de la taxe d'aménagement.

Formule PUBLIQUE (code de l'urbanisme). Assiette = surface taxable × valeur forfaitaire au m²
(+ forfaits d'installations : piscine, PV au sol, stationnement extérieur, éoliennes) ;
abattement de 50 % sur les 100 premiers m² d'une résidence principale et sur les logements aidés ;
taxe = assiette × (part communale + part départementale).

DOCTRINE : aucun taux inventé. Le taux COMMUNAL vient des délibérations (ni en base ni devinable) →
si absent, `taux_communal_pct=None` et le total N'EST PAS calculé (l'appelant dit « taux communal non
renseigné, à saisir »). Le taux départemental sert le plafond légal 2,5 %, étiqueté « à confirmer ».
Les valeurs forfaitaires viennent d'une config DATÉE et SOURCÉE (config/taxe_amenagement.yaml).

Résultat DÉTAILLÉ ligne par ligne : un promoteur doit pouvoir vérifier chaque ligne, pas juste un total.
"""
from __future__ import annotations

from .config import load_yaml_config


def config() -> dict:
    """La config datée (valeurs forfaitaires + plafonds + source/année) — servie telle quelle à l'UI."""
    return load_yaml_config("taxe_amenagement")


def _eur(x: float) -> float:
    return round(float(x), 2)


def calculer(
    *,
    surface_taxable_m2: float = 0.0,
    residence_principale: bool = False,
    logement_aide: bool = False,
    piscine_m2: float = 0.0,
    pv_sol_m2: float = 0.0,
    stationnement_ext_places: int = 0,
    eoliennes_mats: int = 0,
    taux_communal_pct: float | None = None,
    taux_departemental_pct: float | None = None,
) -> dict:
    """Renvoie le détail LIGNE PAR LIGNE + total (None si le taux communal manque)."""
    cfg = config()
    vf = float(cfg["valeur_forfaitaire_m2"]["hors_idf"])   # La Réunion = hors IdF
    ab = cfg["abattement"]
    fo = cfg["forfaits"]
    taux = cfg["taux"]
    if taux_departemental_pct is None:
        taux_departemental_pct = taux.get("part_departementale_defaut")

    lignes: list[dict] = []
    seuil_exo = float(cfg.get("exoneration_surface_min_m2") or 0)

    # 1) surface de construction : valeur forfaitaire, avec abattement 50 % (100 premiers m² RP / aidé).
    surf = max(0.0, float(surface_taxable_m2 or 0))
    if surf > 0 and seuil_exo and surf < seuil_exo:
        # RV2-V2 — exonération de PLEIN DROIT des petites surfaces (CGI art. 1635 quater D, 1°) :
        # une construction < 5 m² de surface taxable n'est pas soumise à la part surface.
        assiette_surf = 0.0
        lignes.append({"poste": "Surface de construction",
                       "detail": f"{surf:g} m² < {seuil_exo:g} m² — exonérée (CGI 1635 quater D)",
                       "assiette_eur": 0.0})
    elif surf > 0:
        abattue = 0.0
        pleine = surf
        if residence_principale or logement_aide:
            # 100 premiers m² à −50 % (RP) ; les logements aidés bénéficient de l'abattement sur toute
            # leur surface. On applique le cas le plus favorable exprimable simplement.
            if logement_aide:
                abattue, pleine = surf, 0.0
            else:
                abattue = min(surf, float(ab["plafond_m2_residence_principale"]))
                pleine = surf - abattue
        taux_ab = float(ab["taux_pct"]) / 100.0
        assiette_surf = pleine * vf + abattue * vf * (1 - taux_ab)
        detail = f"{surf:g} m² × {vf:g} €/m²"
        if abattue:
            detail += f" (dont {abattue:g} m² à −{ab['taux_pct']}%)"
        lignes.append({"poste": "Surface de construction", "detail": detail, "assiette_eur": _eur(assiette_surf)})
    else:
        assiette_surf = 0.0

    # 2) installations à forfait spécifique (assiette propre, taxée aux mêmes taux).
    def _forfait(poste: str, qte: float, unit: float, unite: str):
        if qte and qte > 0:
            a = float(qte) * float(unit)
            lignes.append({"poste": poste, "detail": f"{qte:g} {unite} × {unit:g} €", "assiette_eur": _eur(a)})
            return a
        return 0.0

    assiette_forfaits = (
        _forfait("Piscine", piscine_m2, fo["piscine_m2"], "m²")
        + _forfait("Panneaux photovoltaïques au sol", pv_sol_m2, fo["panneau_pv_sol_m2"], "m²")
        + _forfait("Stationnement extérieur", stationnement_ext_places, fo["stationnement_ext_place"], "place(s)")
        + _forfait("Éolienne(s) (mât > 12 m)", eoliennes_mats, fo["eolienne_mat"], "mât(s)")
    )

    assiette = _eur(assiette_surf + assiette_forfaits)

    # 3) parts communale + départementale.
    taux_manquant = taux_communal_pct is None
    part_com = None if taux_manquant else _eur(assiette * float(taux_communal_pct) / 100.0)
    part_dep = None if taux_departemental_pct is None else _eur(assiette * float(taux_departemental_pct) / 100.0)
    total = None if (part_com is None or part_dep is None) else _eur((part_com or 0) + (part_dep or 0))

    return {
        "annee": cfg["meta"]["annee"],
        "source": cfg["meta"]["source"],
        "url": cfg["meta"]["url"],
        "note": cfg["meta"]["note"],
        "valeur_forfaitaire_m2": vf,
        "lignes": lignes,
        "assiette_eur": assiette,
        "taux_communal_pct": taux_communal_pct,
        "taux_departemental_pct": taux_departemental_pct,
        "part_departementale_confirmee": bool(taux.get("part_departementale_confirmee_974")),
        "part_communale_eur": part_com,
        "part_departementale_eur": part_dep,
        "total_eur": total,
        "taux_communal_manquant": taux_manquant,
        "message_taux_communal": (None if not taux_manquant else
            "Taux communal non renseigné pour cette commune — saisissez-le "
            "(il figure dans la délibération de la commune ; l'outil n'invente aucun taux)."),
    }
