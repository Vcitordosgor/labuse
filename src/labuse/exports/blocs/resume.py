"""Bloc « Résumé » (document « Résumé », gabarit maquette-pdf-resume.html) — MÊMES ids que le
Dossier, sélection courte, présentation compacte (3 pages). Ajouts (RELECTURE) : la ligne du prix
d'achat historique (D-a) et le renvoi « version complète : Dossier · bilan chiffré : Financier ».
Remplace l'export brut de la fiche (retiré au lot 8). Une donnée absente → ligne OMISE (aucun ◌)."""
from __future__ import annotations

from ..lignes import a, ligne, pied, val
from ..nature import chip
from ..registre_fmt import fmt_eur, fmt_eur_m2, fmt_m, fmt_m2, groupe
from ..rendu import aside, chip_span, esc, ligne_kv, note, table_kv, tuiles
from ..verdicts import rendu_verdict, verdict_potentiel, verdict_zonage

IDS = (
    "surface_parcelle_m2",   # lu par l'en-tête compact
    "zone_plu_famille", "reglement_plu_bloc", "type_proprietaire", "prix_achat_historique_eur",
    "er_emplacement_reserve", "ebc_classe", "dpu_perimetre", "peb_zone",
    "potentiel_verdict", "emprise_batie_m2", "hauteur_bati_m", "n_batiments",
    "sdp_residuelle_m2", "capacite_logements", "marge_surelevation_m", "aleas_parcelle_liste",
    "prix_sortie_bati_eur_m2", "prix_terrain_secteur_eur_m2",
    "viabilisation_verdict", "distance_arret_m", "part_logements_egout_pct",
    "iris_quartier", "perimetres_dispositifs_liste", "taxe_amenagement_estimee_eur",
    "statut_plu", "run_label_servi",
)


def _verdict(valeurs) -> str:
    vz = verdict_zonage(valeurs)
    if vz and vz[1] == "warn":       # non constructible prime
        return rendu_verdict(vz)
    return rendu_verdict(verdict_potentiel(valeurs) or vz)


def _sur_place(valeurs) -> str:
    parts = []
    if a(valeurs, "n_batiments"):
        parts.append(f"{int(val(valeurs, 'n_batiments'))} bâtiments")
    if a(valeurs, "emprise_batie_m2"):
        parts.append(f"{fmt_m2(val(valeurs, 'emprise_batie_m2'))} au sol")
    if a(valeurs, "hauteur_bati_m"):
        parts.append(fmt_m(val(valeurs, "hauteur_bati_m")))
    return " · ".join(parts)


def _tete(valeurs) -> str:
    lignes = []
    z = val(valeurs, "reglement_plu_bloc") or {}
    fam = val(valeurs, "zone_plu_famille")
    if fam:
        plu = val(valeurs, "statut_plu")
        suite = (" — " + esc(plu["libelle"])) if isinstance(plu, dict) and plu.get("libelle") else ""
        lignes.append(ligne_kv("Zone", esc(str(fam)) + suite, chip_span("s", "sourcé")))
    sp = _sur_place(valeurs)
    if sp:
        lignes.append(ligne_kv("Sur place", esc(sp), chip_span("s", "sourcé")))
    lignes.append(ligne(valeurs, "Propriétaire", "type_proprietaire", str))
    lignes.append(ligne(valeurs, "Prix d'achat de la parcelle", "prix_achat_historique_eur",
                        lambda v: fmt_eur(v["valeur"]) if isinstance(v, dict) else fmt_eur(v)))
    return table_kv([x for x in lignes if x])


def _regle_valeur(z: dict, cle: str):
    for r in z.get("regles_valeurs") or []:
        if r.get("cle") == cle and r.get("valeur") not in (None, ""):
            return r["valeur"]
    return None


def _reglement(valeurs) -> str:
    z = val(valeurs, "reglement_plu_bloc") or {}
    if not isinstance(z, dict) or not z.get("regles_valeurs"):
        return ""
    lignes = []
    h = _regle_valeur(z, "hauteur")
    if h:
        lignes.append(ligne_kv("Hauteurs", esc(str(h)), chip_span("s", "sourcé")))
    d = z.get("destinations") or {}
    if d.get("autorisees") or d.get("interdites"):
        txt = ""
        if d.get("autorisees"):
            txt += "autorisées : " + esc(" · ".join(d["autorisees"][:4]))
        if d.get("interdites"):
            txt += " ; interdites : " + esc(" · ".join(d["interdites"]))
        lignes.append(ligne_kv("Destinations", txt, chip_span("s", "sourcé")))
    presc = []
    if a(valeurs, "dpu_perimetre"):
        presc.append("dans le périmètre de préemption")
    if a(valeurs, "er_emplacement_reserve"):
        presc.append("emplacement réservé")
    if a(valeurs, "ebc_classe"):
        presc.append("espace boisé classé")
    if presc:
        lignes.append(ligne_kv("Prescriptions", esc(" · ".join(presc)), chip_span("s", "sourcé")))
    return ("<h2>Ce que le règlement permet</h2>" + table_kv(lignes)) if lignes else ""


def _potentiel(valeurs) -> str:
    lignes = []
    if a(valeurs, "sdp_residuelle_m2"):
        p = val(valeurs, "potentiel_verdict") or {}
        pct = f" — {p.get('pct_consomme')} % consommés" if isinstance(p, dict) and p.get("pct_consomme") else ""
        lignes.append(ligne_kv("Au sol", f"<strong>{fmt_m2(val(valeurs, 'sdp_residuelle_m2'))}</strong> de plancher résiduel{pct}", ""))
    if a(valeurs, "capacite_logements"):
        lignes.append(ligne_kv("Reconstruction", f"<strong>{esc(str(val(valeurs, 'capacite_logements')))}</strong> — démolition à chiffrer", ""))
    return ("<h2>Potentiel</h2>" + table_kv(lignes)) if lignes else ""


def _risques(valeurs) -> str:
    liste = val(valeurs, "aleas_parcelle_liste") or []
    if not liste:
        return ""
    corps = "<h2>Risques et servitudes</h2>"
    tete = next((x for x in liste if isinstance(x, dict) and "bleue" in (x.get("libelle") or "").lower()), None)
    if tete:
        corps += aside(f"<strong>{esc(tete.get('libelle'))}</strong>", "blue")
    autres = [x.get("nature") for x in liste if isinstance(x, dict) and x is not tete and x.get("nature")]
    if autres:
        corps += table_kv([ligne_kv("Aléas", esc(" · ".join(dict.fromkeys(autres))), chip_span("s", "sourcé"))])
    return corps


def _marche(valeurs) -> str:
    items = []
    pa = val(valeurs, "prix_sortie_bati_eur_m2")
    if isinstance(pa, dict) and pa.get("median"):
        items.append((fmt_eur_m2(pa["median"]), f"ancien — {pa.get('n', '?')} ventes, secteur"))
    tn = val(valeurs, "prix_terrain_secteur_eur_m2")
    if isinstance(tn, dict) and tn.get("prix_m2"):
        lib = f"terrain nu — {fmt_eur(tn['valeur_eur'])}" if tn.get("valeur_eur") else "terrain nu — secteur"
        items.append((fmt_eur_m2(tn["prix_m2"]), lib))
    if not items:
        return ""
    corps = "<h2>Marché</h2>" + tuiles(items)
    if isinstance(pa, dict) and pa.get("tendance_pct") is not None:
        corps += table_kv([ligne_kv("Tendance du secteur",
                          esc(f"{'+' if pa.get('tendance') == 'hausse' else ''}{pa['tendance_pct']} % sur {pa.get('periode', '')}"),
                          chip_span("s", "sourcé"))])
    return corps


def _reseaux(valeurs) -> str:
    lignes = []
    viab = val(valeurs, "viabilisation_verdict")
    if isinstance(viab, dict) and viab.get("libelle"):
        lignes.append(ligne_kv("Viabilisation", esc(viab["libelle"]), chip_span("e", "estimé")))
    anc = val(valeurs, "part_logements_egout_pct")
    if isinstance(anc, dict) and anc.get("libelle"):
        lignes.append(ligne_kv("Assainissement", esc(anc["libelle"]), chip_span("s", "sourcé")))
    prox = val(valeurs, "distance_arret_m")
    if isinstance(prox, dict) and isinstance(prox.get("arret"), dict) and prox["arret"].get("distance_m") is not None:
        ar = prox["arret"]
        lignes.append(ligne_kv("Desserte", esc(f"Arrêt {ar.get('nom', '')} à {ar['distance_m']} m"), chip_span("s", "sourcé")))
    return ("<h2>Réseaux et desserte</h2>" + table_kv(lignes)) if lignes else ""


def _autour(valeurs) -> str:
    lignes = []
    iq = val(valeurs, "iris_quartier")
    if isinstance(iq, dict) and iq.get("habitants") is not None:
        lignes.append(ligne_kv(f"Quartier {iq.get('nom', '')} (maille IRIS)",
                      esc(f"{groupe(iq['habitants'])} habitants, {groupe(iq.get('menages', 0))} ménages"),
                      chip(valeurs["iris_quartier"])))
    fisc = val(valeurs, "perimetres_dispositifs_liste")
    if isinstance(fisc, dict):
        dom = (fisc.get("dispositifs_dom") or [{}])[0]
        bits = [x for x in [dom.get("libelle"), (fisc.get("zfang") or {}).get("libelle")] if x]
        if bits:
            lignes.append(ligne_kv("Commune", esc(" · ".join(bits)), chip_span("s", "sourcé")))
    return ("<h2>Autour et commune</h2>" + table_kv(lignes)) if lignes else ""


def rendu(valeurs) -> str:
    corps = (_verdict(valeurs) + _tete(valeurs) + _reglement(valeurs) + _potentiel(valeurs)
             + _risques(valeurs) + _marche(valeurs) + _reseaux(valeurs) + _autour(valeurs))
    corps += note("Ne dit pas : la constructibilité définitive (certificat d'urbanisme), la "
                  "valeur vénale (notaire), l'état du bâti et les servitudes privées (visite, "
                  "acte), la position du propriétaire.")
    corps += note("Version complète : Dossier parcelle · Bilan chiffré : Financier.")
    corps += pied(valeurs, IDS)
    return corps
