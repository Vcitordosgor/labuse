# COMMUNE-RANGEMENT-2 lot 5 — génère declarations/commune/*.yaml : chaque donnée maille commune servie
# sur la fiche (robinet fiche_commune_*) déclarée avec sa CARTE (section) et son groupe, sur le modèle de
# declarations/fiche/. Libellé + définition tirés du registre (donnees.py) — une seule vérité.
import pathlib
from labuse.registre import donnees

DON = donnees.DONNEES
# (chiffre, carte, format, pourquoi)
FMT_DEFAUT = "texte"
# groupes → fichier ; chaque entrée = (carte, [chiffres])
GROUPES = {
 "territoire": ("Le territoire", "/communes/{c}/contexte", [
   ("Identité", [
     ("mairie_coordonnees", "texte", "Le point de contact civique de la commune : mairie et service urbanisme."),
     ("iris_commune_quartiers", "liste", "La commune n'est pas homogène : les quartiers IRIS en donnent le grain."),
   ]),
   ("Population et logement", [
     ("habitants_n", "entier", "La taille du marché résidentiel : combien d'habitants."),
     ("vacance_pct", "pourcent", "La vacance mesure la tension (ou le desserrement) du parc de logements."),
     ("autres_loges_pct", "pourcent", "La structure d'occupation (part logés gratuitement) complète propriétaires/locataires."),
     ("parc_social_rpls_logements", "entier", "Le parc social existant (RPLS) — le débouché LLS et son ampleur."),
     ("taux_lls_pct", "pourcent", "Le taux SRU : l'obligation de production sociale de la commune."),
     ("deficit_sru_pts", "pourcent", "Le déficit SRU (objectif − taux) : la pression de rattrapage social."),
     ("lls_inventaire_n", "entier", "Le nombre de logements sociaux inventoriés (SRU) : la base du taux."),
   ]),
 ]),
 "marche": ("Le marché", "/communes/{c}/contexte", [
   ("Prix", [
     ("prix_ancien_median_eur_m2", "euro_m2", "Le prix de sortie de référence : la médiane de l'ancien, commune entière."),
     ("prix_neuf_vefa_acte_eur_m2", "euro_m2", "Le neuf VEFA à l'acte : le prix affiché à la vente sur plan."),
     ("prix_neuf_observe_eur_m2", "euro_m2", "Le neuf observé (ventes récentes) : notion scindée du VEFA, le prix constaté."),
     ("prix_terrain_zone_eur_m2", "euro_m2", "Le coût du sol par zone U/AU : l'entrée du bilan promoteur."),
     ("loyer_median_eur_m2", "euro_m2", "Le loyer médian : le rendement locatif de sortie."),
   ]),
   ("Activité", [
     ("mutations_12m_n", "entier", "Le volume de mutations sur 12 mois : la liquidité du marché."),
     ("annonces_actives_n", "entier", "Les biens en vente (Radar) : l'offre du moment."),
     ("prix_demande_median_eur_m2", "euro_m2", "Le prix demandé médian : ce que les vendeurs affichent."),
     ("ecart_demande_acte_pct", "pourcent", "L'écart demandé/acté : la marge de négociation, signal exclusif LABUSE."),
   ]),
 ]),
 "construction": ("La construction", "/communes/{c}/contexte", [
   ("Permis et rythme", [
     ("permis_12m_n", "entier", "Les permis autorisés sur 12 mois : le rythme de production."),
     ("velocite_delai_median_mois", "entier", "Le délai médian d'instruction : la vélocité administrative."),
     ("point_mort_n", "entier", "Les permis dormants (autorisés, non commencés) : le gisement latent."),
   ]),
   ("Foncier et rareté", [
     ("n_parcelles_commune", "entier", "L'assiette foncière : le nombre de parcelles de la commune."),
     ("stock_opportunites", "entier", "Le stock d'opportunités repérées (brûlantes + chaudes)."),
     ("n_densifiables", "entier", "Les parcelles densifiables : la capacité résiduelle."),
     ("zan_reste_ha", "entier", "L'enveloppe ZAN restante : le budget d'artificialisation."),
     ("zan_evolution_commune", "entier", "L'artificialisation récente (OCS GE) : la trajectoire ZAN."),
   ]),
 ]),
 "regles": ("Les règles", "/communes/{c}/contexte", [
   ("Urbanisme", [
     ("statut_plu", "classe", "Le document opposable et son état : la règle qui s'applique."),
     ("part_zone_U_pct", "pourcent", "La part urbanisée (zone U) du territoire."),
     ("part_zone_AU_pct", "pourcent", "La part à urbaniser (zone AU) : la réserve foncière ouverte."),
     ("part_zone_A_pct", "pourcent", "La part agricole (zone A) du territoire."),
     ("part_zone_N_pct", "pourcent", "La part naturelle (zone N) du territoire."),
     ("plh_objectif_logements_an", "entier", "L'objectif de production du PLH intercommunal."),
   ]),
   ("Fiscalité et dispositifs", [
     ("tfpb_taux_pct", "pourcent", "La taxe foncière sur le bâti (TFPB) : la charge portée par l'acquéreur."),
     ("tfpnb_taux_pct", "pourcent", "La taxe foncière sur le non bâti (TFPNB) : la charge du terrain."),
     ("zonage_abc_logement", "classe", "La zone A/B/C : la classe de tension du dispositif d'investissement."),
     ("zfang_regime_commune", "classe", "Le régime ZFANG : l'avantage fiscal d'implantation d'activité."),
     ("frr_classement_commune", "classe", "Le classement FRR (ex-ZRR) : le dispositif de revitalisation rurale."),
     ("ort_statut", "classe", "ACV / PVD / ORT : le dispositif de revitalisation, condition Denormandie."),
     ("qpv_n", "entier", "Les quartiers prioritaires (QPV) : le zonage politique de la ville."),
   ]),
 ]),
 "cadre_de_vie": ("Le cadre de vie", "/communes/{c}/contexte", [
   ("Risques et contraintes", [
     ("ppr_pct", "pourcent", "La part du territoire exposée à un risque (PPR) : la contrainte majeure."),
     ("catnat_n", "entier", "Le nombre d'arrêtés de catastrophe naturelle : l'historique du risque."),
     ("catnat_arretes_liste", "liste", "Le détail des arrêtés CatNat (péril, dates, code national)."),
     ("azi_tri_commune", "liste", "Les documents inondation (AZI / TRI) couvrant la commune."),
   ]),
 ]),
}

def esc(s: str) -> str:
    return s.replace('"', "'")

out_dir = pathlib.Path("declarations/commune")
out_dir.mkdir(parents=True, exist_ok=True)
total = 0
for fname, (groupe, route, cartes) in GROUPES.items():
    lines = []
    lines.append(f"# COMMUNE-RANGEMENT-2 lot 5 — « {groupe} » : chaque ligne des cartes de la fiche commune,")
    lines.append(f"# déclarée avec sa CARTE (section). Modèle : declarations/fiche/. Libellé/définition = registre.")
    lines.append(f"surface:   fiche_commune_{fname}")
    lines.append(f'nom:       "{groupe}"')
    lines.append(f"categorie: fiche_commune")
    lines.append(f"parent:    fiche_commune")
    lines.append(f'route:     "{route}"')
    lines.append(f"rendu:     cartes")
    lines.append(f"donnees:")
    rang = 10
    for carte, chiffres in cartes:
        for cid, fmt, pourquoi in chiffres:
            d = DON.get(cid)
            libelle = esc(d.libelle if d else cid)
            defi = esc((d.definition if d else "")[:180]) or libelle
            etat = "en_tete" if rang == 10 else "replie"
            lines.append(f"  - quoi:  {cid}")
            lines.append(f'    ou:    {{ rang: {rang}, etat: {etat}, section: "{esc(carte)}" }}')
            lines.append(f'    comment: {{ libelle: "{libelle}", format: {fmt}, i: "{defi}" }}')
            lines.append(f'    absence: "{libelle} : donnée non disponible sur cette commune."')
            lines.append(f"    absence_type: absente_ici")
            lines.append(f'    pourquoi: "{esc(pourquoi)}"')
            rang += 10
            total += 1
    (out_dir / f"{fname}.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"écrit declarations/commune/{fname}.yaml")
print(f"TOTAL lignes déclarées : {total}")
