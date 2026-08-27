# MANDAT — RATTRAPAGE KELFONCIER 1/2 : EXPOSER CE QU'ON A DÉJÀ
Régime AUTONOME. Commits par lot (K1→K3). RÈGLES COMMUNES. Findings KF-001→.

## POURQUOI
Comparatif KelFoncier vs LABUSE (27/08/2026) : KF garde trois avantages qui ne tiennent PAS à une supériorité de données mais à une absence d'interface ou à un calcul qu'on n'a pas encore écrit. Les trois chantiers ci-dessous ferment ces écarts sans aucune ingestion nouvelle.
Doctrine inchangée : Sourcé/Estimé/Absent · zéro faux positif · fraîcheur = date source amont · aucun chiffre inventé · un chiffre servi = un point de calcul unique.

## K1 — FILTRES PROPRIÉTAIRE (la donnée est en base, l'interface manque)
LABUSE a ingéré les fichiers des personnes morales DGFiP : ~82 701 liens parcelle↔PM. Rien n'est exposé en recherche. KelFoncier, lui, laisse filtrer par SIREN, code APE, forme juridique, nombre de dirigeants.
Commence par l'INVENTAIRE : quelles tables et colonnes existent réellement (dénomination, SIREN, forme juridique, code APE, dirigeants via INPI RNE si présent, millésime), quelle couverture (combien de parcelles portent un lien PM, sur combien au total), quelle fraîcheur. Écris-le au rapport AVANT de coder — si un champ n'existe pas, il ne devient pas un filtre.
Puis expose dans le panneau de recherche existant, en respectant sa logique actuelle :
- Propriétaire personne morale : oui / non / indifférent
- Recherche par dénomination (autocomplétion sur les noms réellement en base)
- SIREN (un ou plusieurs)
- Forme juridique (liste alimentée par les valeurs distinctes réelles, pas une liste écrite à la main)
- Code APE / activité (idem)
- Nombre de dirigeants, âge du dirigeant SI et seulement SI la donnée existe déjà en base — ATTENTION : l'âge du dirigeant est un point RGPD identifié comme question ouverte pour l'avocat. Si le champ existe, expose-le derrière un drapeau de configuration désactivé par défaut, et dis-le au rapport. Ne l'active pas.
Chaque filtre affiche le nombre de résultats et le millésime de la source. Un filtre sans donnée pour une commune dit « non couvert », il ne renvoie pas zéro silencieusement.

## K2 — CONTACTS MAIRIES DANS LES FICHES COMMUNE
L'outil Communes n'a pas les coordonnées des mairies ; KF les affiche (adresse, téléphone, e-mail, site).
Source : annuaire de l'administration (API Découpage administratif / annuaire service-public, données ouvertes). 24 communes seulement — le volume est trivial.
Ingère les 24 fiches dans une table dédiée avec leur date de récupération, et affiche dans la fiche commune : adresse de la mairie, téléphone, e-mail, site officiel, et le lien vers la page urbanisme si l'annuaire la donne. Fraîcheur affichée comme partout. Si un champ manque pour une commune, il est marqué ABSENT, jamais inventé.
Prévoir la commande de rafraîchissement (les coordonnées changent) et la déclarer dans EXPLOITATION-CRON.md sans forcément l'automatiser.

## K3 — CALCULETTE DE TAXE D'AMÉNAGEMENT (nouvel outil)
KF propose une calculette sérieuse ; LABUSE n'a rien. La formule est publique et documentée (code de l'urbanisme) : assiette = surface taxable × valeur forfaitaire au m² (actualisée chaque année, distincte en Île-de-France et hors IdF) ; part communale et part départementale à leurs taux ; abattements de 50 % pour certains locaux (100 premiers m² de résidence principale, logements aidés, locaux industriels…) ; exonérations de plein droit ; valeurs forfaitaires spécifiques (piscine, panneaux photovoltaïques au sol, stationnement extérieur, éoliennes).
Exigences :
- Les TAUX COMMUNAUX viennent des délibérations : ils ne sont PAS uniformes et pas devinables. Cherche s'ils sont déjà quelque part en base ou dans les configs PLU calibrées. Si tu ne les as pas pour une commune, l'outil dit « taux communal non renseigné pour cette commune » et permet à l'utilisateur de le saisir — il n'invente JAMAIS un taux par défaut silencieux.
- Les valeurs forfaitaires et le taux départemental de l'année en cours sont dans une config datée, avec la source et l'année écrites à l'écran.
- L'outil s'ouvre depuis une parcelle (surface et zone pré-remplies quand on les a) ou à vide.
- Le résultat détaille le calcul ligne par ligne (assiette, part communale, part départementale, abattements, total) — un promoteur doit pouvoir vérifier chaque ligne, pas juste lire un total.
- Mention claire : estimation indicative, le montant officiel est notifié par l'administration après dépôt du permis. Cohérente avec la clause boussole.
- L'outil rejoint le menu Outils (menu aplati, pas de catégorie), DA LABUSE, mauve absent.

## FIN
Critères : inventaire PM écrit au rapport avant tout code · filtres propriétaire opérationnels, alimentés par les valeurs réelles, avec compteurs et millésimes · âge du dirigeant non activé (drapeau désactivé, noté) · 24 mairies ingérées et affichées, champs manquants marqués ABSENT · calculette livrée, détail ligne par ligne, aucun taux inventé · gardées vertes · tsc/build verts · suite au niveau de la base (prouvé par worktree) · objets de test [KF-TEST] purgés.
Captures des trois livrables dans le rapport (390 et 1440). Compte-rendu « Demandé → traité » par lot + commande de merge en dernier élément isolé (git merge --no-ff feat/rattrapage-kf-1). Tu ne merges pas.
