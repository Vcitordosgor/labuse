"""Bloc « 8. Contexte communal ». Dispositifs fiscaux (ZFANG, FRR, zonage A/B/C, bande QPV),
parc social, taxe d'aménagement (taux communal « non renseigné » dit honnêtement, jamais un ◌),
fraîcheur du PLU."""
from __future__ import annotations

from ..lignes import a, pied, val
from ..nature import chip
from ..registre_fmt import fmt_eur, groupe
from ..rendu import chip_span, esc, ligne_kv, section, table_kv

IDS = ("perimetres_dispositifs_liste", "parc_social_rpls_logements",
       "taxe_amenagement_estimee_eur", "statut_plu")


def _taxe(t: dict) -> str:
    if t.get("total_eur"):
        taux = f" (taux communal {t.get('taux_communal_pct')} %)" if t.get("taux_communal_pct") else ""
        # TAXE-AMÉNAGEMENT-1 lot C — millésime du taux public affiché avec le chiffre.
        mil = t.get("taux_communal_millesime")
        src = f" — {mil}" if (t.get("taux_communal_source") == "public" and mil) else ""
        return f"De l'ordre de {fmt_eur(t['total_eur'])}{taux} pour {t.get('assiette_m2', '?')} m² de plancher{src}"
    dep = f", part départementale {fmt_eur(t['part_departementale_eur'])}" if t.get("part_departementale_eur") else ""
    return (f"Taux communal non renseigné pour cette commune — {t.get('assiette_m2', '?')} m² "
            f"d'assiette{dep}")


def rendu(valeurs) -> str:
    lignes = []
    fisc = val(valeurs, "perimetres_dispositifs_liste") or {}
    if isinstance(fisc, dict):
        dom = (fisc.get("dispositifs_dom") or [{}])[0]
        if dom.get("libelle"):
            lignes.append(ligne_kv("Zonage du logement", esc(dom["libelle"]), chip(valeurs["perimetres_dispositifs_liste"])))
        if (fisc.get("zfang") or {}).get("libelle"):
            lignes.append(ligne_kv("ZFANG", esc(fisc["zfang"]["libelle"]), chip_span("s", "sourcé")))
        if (fisc.get("frr") or {}).get("libelle"):
            lignes.append(ligne_kv("FRR (ex-ZRR)", esc(fisc["frr"]["libelle"]), chip_span("s", "sourcé")))
        per = (fisc.get("perimetres") or [{}])[0]
        if per.get("libelle"):
            lignes.append(ligne_kv("Périmètre fiscal", esc(per["libelle"]), chip_span("d", "dérivé")))
    if a(valeurs, "parc_social_rpls_logements"):
        lignes.append(ligne_kv("Parc social (commune)",
                      esc(f"{groupe(val(valeurs, 'parc_social_rpls_logements'))} logements sociaux (RPLS)"),
                      chip(valeurs["parc_social_rpls_logements"])))
    taxe = val(valeurs, "taxe_amenagement_estimee_eur")
    if isinstance(taxe, dict):
        lignes.append(ligne_kv("Taxe d'aménagement", esc(_taxe(taxe)), chip_span("e", "estimé")))
    plu = val(valeurs, "statut_plu")
    if isinstance(plu, dict) and plu.get("libelle"):
        lignes.append(ligne_kv("PLU", esc(plu["libelle"]), chip_span("s", "sourcé")))
    if not lignes:
        return ""
    commune = fisc.get("commune") if isinstance(fisc, dict) else None
    titre = f"8. Contexte communal — {commune}" if commune else "8. Contexte communal"
    return section(titre, table_kv(lignes) + pied(valeurs, IDS))
