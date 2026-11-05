#!/usr/bin/env python3
"""NU5-E — harnais d'extraction des faits servis de la fiche commune (10 cartes × 24 communes).

Lit les 24 payloads servis (dump de commune_contexte_cache.payload, base LOCALE labuse q_v20,
cache calculé le 2026-11-05 — cf. RAPPORT §Méthode) et produit :
  - faits.csv : commune × champ (valeur, millésime, source) — relecture figure par figure ;
  - comparaison.csv : une ligne par commune, colonnes = chiffres clés — contrôle inter-communes
    (ordre de grandeur, signe, zéro) ;
  - structure.txt : clés top-level présentes/absentes par commune (détecte un bloc disparu).
LECTURE SEULE. Aucune écriture base.
"""
import csv, glob, json, os

HERE = os.path.dirname(__file__)
PAY = os.path.join(HERE, "..", "preuves", "payloads")


def load():
    out = {}
    for f in sorted(glob.glob(os.path.join(PAY, "*.json"))):
        d = json.load(open(f))
        out[d["insee"]] = d
    return out


def g(d, *path, default=None):
    cur = d
    for p in path:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return default
    return cur


# (carte, champ, chemin, champ_millésime, champ_source)
CHAMPS = [
    # Identité
    ("Identité", "epci", ("epci",), None, None),
    ("Identité", "epci_nom", ("epci_nom",), None, None),
    ("Identité", "mairie_nom", ("mairie", "nom"), ("mairie", "date_import"), ("mairie", "source")),
    ("Identité", "mairie_cp", ("mairie", "code_postal"), None, None),
    ("Identité", "mairie_site", ("mairie", "site_officiel"), None, None),
    ("Identité", "quartiers_n_iris", ("population", "quartiers", "n_iris"), None, None),
    # Population & logement
    ("Population", "habitants", ("population", "habitants"), ("population", "habitants_millesime"), ("population", "source")),
    ("Population", "habitants_etiquette", ("population", "habitants_etiquette"), None, None),
    ("Population", "menages", ("population", "menages"), ("population", "menages_millesime"), None),
    ("Population", "niveau_vie_moyen_eur", ("population", "niveau_vie_moyen_eur"), None, None),
    ("Population", "logements", ("population", "logements"), ("marche", "millesime"), None),
    ("Population", "vacants", ("population", "vacants"), None, None),
    ("Population", "vacance_pct", ("population", "vacance_pct"), None, None),
    ("Population", "parc_ancien_pct", ("population", "parc_ancien_pct"), None, None),
    ("Population", "parc_social_logements", ("parc_social", "logements"), ("parc_social", "millesime"), ("parc_social", "source")),
    ("Population", "parc_social_construct_median", ("parc_social", "construct_median"), None, None),
    ("Population", "res_principales", ("marche", "res_principales"), None, None),
    ("Population", "maisons_pct", ("marche", "maisons_pct"), None, None),
    ("Population", "apparts_pct", ("marche", "apparts_pct"), None, None),
    ("Population", "proprietaires_pct", ("marche", "proprietaires_pct"), None, None),
    ("Population", "locataires_pct", ("marche", "locataires_pct"), None, None),
    ("Population", "sru_taux_lls", ("sru", "taux_lls"), ("sru", "millesime"), ("sru", "source_nom")),
    ("Population", "sru_nb_lls", ("sru", "nb_lls"), None, None),
    ("Population", "sru_statut", ("sru", "statut"), None, None),
    # Prix
    ("Prix", "ancien_median_eur_m2", ("comparable", "ancien_median_eur_m2"), None, ("comparable", "source")),
    ("Prix", "ancien_n", ("comparable", "ancien_n"), None, None),
    ("Prix", "neuf_vefa_eur_m2", ("comparable", "neuf_eur_m2"), None, None),
    ("Prix", "neuf_observe_eur_m2", ("prix_neuf_observe", "eur_m2"), None, ("prix_neuf_observe", "source")),
    ("Prix", "neuf_observe_n", ("prix_neuf_observe", "n"), None, None),
    ("Prix", "loyer_median_eur_m2", ("loyer", "median_eur_m2"), None, ("loyer", "source")),
    ("Prix", "loyer_type", ("loyer", "type"), None, None),
    ("Prix", "terrain_nu_U_eur_m2", ("foncier", "prix_terrain_nu", "par_zone", "U", "median_eur_m2"), None, None),
    ("Prix", "terrain_nu_U_n", ("foncier", "prix_terrain_nu", "par_zone", "U", "n"), None, None),
    ("Prix", "terrain_nu_AU_eur_m2", ("foncier", "prix_terrain_nu", "par_zone", "AU", "median_eur_m2"), None, None),
    # Activité
    ("Activité", "radar_biens", ("marche_annonces", "biens"), ("marche_annonces", "derniere_collecte"), ("marche_annonces", "source")),
    ("Activité", "radar_sous_seuil", ("marche_annonces", "sous_seuil"), None, None),
    ("Activité", "prix_demande_median_eur_m2", ("marche_annonces", "prix_demande_median_eur_m2"), None, None),
    ("Activité", "ecart_demande_acte_pct", ("marche_annonces", "ecart_demande_acte_pct"), None, None),
    ("Activité", "prix_acte_eur_m2", ("marche_annonces", "prix_acte_eur_m2"), None, None),
    ("Activité", "mutations_12m", ("foncier", "mutations_12m"), None, None),
    # Permis
    ("Permis", "permis_12m", ("permis_bloc", "permis_12m"), None, ("permis_bloc", "source")),
    ("Permis", "permis_5a", ("permis_bloc", "permis_5a"), None, None),
    ("Permis", "logements_12m", ("permis_bloc", "logements_12m"), None, None),
    ("Permis", "delai_median_mois", ("permis_bloc", "delai_median_mois"), None, None),
    ("Permis", "point_mort", ("permis_bloc", "point_mort"), None, None),
    ("Permis", "permis_annules_12m", ("permis_bloc", "permis_annules_12m"), None, None),
    # Foncier & rareté
    ("Foncier", "n_parcelles", ("foncier", "n_parcelles"), None, None),
    ("Foncier", "surface_ha", ("foncier", "surface_ha"), None, None),
    ("Foncier", "zonage_U_pct", ("foncier", "repartition_zonage", "familles", "U", "pct"), None, None),
    ("Foncier", "zonage_AU_pct", ("foncier", "repartition_zonage", "familles", "AU", "pct"), None, None),
    ("Foncier", "zonage_A_pct", ("foncier", "repartition_zonage", "familles", "A", "pct"), None, None),
    ("Foncier", "zonage_N_pct", ("foncier", "repartition_zonage", "familles", "N", "pct"), None, None),
    ("Foncier", "zonage_total_ha", ("foncier", "repartition_zonage", "total_ha"), None, None),
    ("Foncier", "stock_opportunites_n", ("foncier", "stock_opportunites", "n"), None, None),
    ("Foncier", "densifiables", ("densifiables", "parcelles"), None, ("densifiables", "source")),
    ("Foncier", "sdp_residuelle_m2", ("densifiables", "sdp_residuelle_m2"), None, None),
    # Urbanisme
    ("Urbanisme", "plu_statut", ("plu_statut", "statut"), ("plu_statut", "source"), None),
    ("Urbanisme", "plu_libelle", ("plu_statut", "libelle"), None, None),
    ("Urbanisme", "plu_procedure", ("plu_statut", "procedure"), None, None),
    ("Urbanisme", "plu_proc_sudocuh_etat", ("plu_statut", "procedure_sudocuh", "etat"), ("plu_statut", "procedure_sudocuh", "millesime"), None),
    ("Urbanisme", "scot_nom", ("scot", "nom"), None, None),      # attendu ABSENT (bug E-1)
    ("Urbanisme", "rnu", ("rnu",), None, None),
    # Fiscalité & dispositifs
    ("Fiscalité", "tfpb_commune_pct", ("fiscalite", "tfpb_commune_pct"), ("fiscalite", "millesime"), ("fiscalite", "source")),
    ("Fiscalité", "tfpb_epci_pct", ("fiscalite", "tfpb_epci_pct"), None, None),
    ("Fiscalité", "tfpnb_commune_pct", ("fiscalite", "tfpnb_commune_pct"), None, None),
    ("Fiscalité", "teom_pct", ("fiscalite", "teom_pct"), None, None),
    ("Fiscalité", "taxe_amenagement_pct", ("taxe_amenagement", "part_communale_pct"), ("taxe_amenagement", "millesime"), None),
    ("Fiscalité", "zonage_abc", ("zonage_abc", "zone"), ("zonage_abc", "millesime"), ("zonage_abc", "source")),
    ("Fiscalité", "zfang_regime", ("zfang_frr", "zfang", "regime"), None, None),
    ("Fiscalité", "frr_classement", ("zfang_frr", "frr", "classement"), None, None),
    ("Fiscalité", "ort_statut", ("ort", "statut"), None, ("ort", "source")),
    # Risques
    ("Risques", "ppr_pct", ("risques", "ppr_pct"), None, ("risques", "source")),
    ("Risques", "mouvement_terrain_pct", ("risques", "mouvement_terrain_pct"), None, None),
    ("Risques", "catnat_arretes", ("risques", "catnat_arretes"), None, None),
    ("Risques", "parc_national", ("risques", "parc_national"), None, None),
]


def main():
    data = load()
    insees = sorted(data)
    # faits.csv
    with open(os.path.join(HERE, "..", "faits.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["insee", "commune", "carte", "champ", "valeur", "millesime", "source"])
        for ins in insees:
            d = data[ins]
            comm = d.get("commune")
            for carte, champ, path, mpath, spath in CHAMPS:
                val = g(d, *path)
                mil = g(d, *mpath) if mpath else ""
                src = g(d, *spath) if spath else ""
                w.writerow([ins, comm, carte, champ, val, mil, src])
    # comparaison.csv (large) — chiffres clés par commune
    cols = ["habitants", "menages", "logements", "niveau_vie_moyen_eur", "sru_taux_lls",
            "ancien_median_eur_m2", "neuf_vefa_eur_m2", "neuf_observe_eur_m2", "loyer_median_eur_m2",
            "terrain_nu_U_eur_m2", "permis_12m", "permis_5a", "point_mort", "radar_biens",
            "ecart_demande_acte_pct", "n_parcelles", "surface_ha", "densifiables",
            "zonage_U_pct", "zonage_N_pct", "ppr_pct", "mouvement_terrain_pct", "catnat_arretes",
            "tfpb_commune_pct", "taxe_amenagement_pct", "zonage_abc", "plu_statut", "scot_nom"]
    champ_path = {c[1]: c[2] for c in CHAMPS}
    with open(os.path.join(HERE, "..", "comparaison.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["insee", "commune"] + cols)
        for ins in insees:
            d = data[ins]
            row = [ins, d.get("commune")]
            for c in cols:
                row.append(g(d, *champ_path[c]))
            w.writerow(row)
    # structure.txt
    all_keys = set()
    for d in data.values():
        all_keys |= set(d.keys())
    all_keys = sorted(all_keys)
    with open(os.path.join(HERE, "..", "structure.txt"), "w") as fh:
        fh.write("Clés top-level par commune (X=présent, .=absent)\n")
        fh.write("key".ljust(22) + " " + " ".join(i[-2:] for i in insees) + "\n")
        for k in all_keys:
            fh.write(k.ljust(22) + " " + " ".join("X" if k in data[i] else "." for i in insees) + "\n")
    print("faits.csv, comparaison.csv, structure.txt écrits.")
    print("communes:", len(insees))


if __name__ == "__main__":
    main()
